"""Serviço de integração com Gemini 2.5 Pro."""
import json
import re
from app.config import GEMINI_API_KEY

# Lazy init do client
_client = None


def _get_client():
    global _client
    if _client is None:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        _client = genai
    return _client


def parse_json_response(text: str) -> list:
    """Parse JSON do Gemini, removendo markdown se presente."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _detect_mime_type(path: str) -> str:
    if path.endswith(".wav"):
        return "audio/wav"
    elif path.endswith(".ogg"):
        return "audio/ogg"
    elif path.endswith(".flac"):
        return "audio/flac"
    return "audio/mpeg"


async def transcrever_cego(
    audio_file_ref, idioma: str, metadados: dict
) -> list:
    """Transcrição cega: Gemini recebe apenas o áudio, sem letra.
    Timestamps mais precisos pois o modelo precisa ouvir de verdade.
    audio_file_ref: arquivo já uploaded via genai.upload_file."""
    genai = _get_client()
    model = genai.GenerativeModel(
        "gemini-2.5-pro",
        generation_config=genai.GenerationConfig(temperature=0),
    )

    nomes_idiomas = {
        "en": "inglês", "pt": "português", "es": "espanhol",
        "de": "alemão", "fr": "francês", "it": "italiano", "pl": "polonês",
    }
    nome_idioma = nomes_idiomas.get(idioma, idioma)

    prompt = f"""
Você é um assistente de legendagem de vídeos de ópera.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma cantado: {nome_idioma}
- Compositor: {metadados.get("compositor", "N/A")}

TAREFA:
Ouça o áudio COMPLETO do início ao fim e transcreva TUDO que é cantado, com timestamps PRECISOS.
Preste atenção especial ao MOMENTO EXATO em que cada frase começa e termina.

REGRAS:
1. Transcreva exatamente o que ouve — não invente texto
2. Marque QUANDO cada frase começa e termina no áudio com precisão
3. Timestamps relativos ao INÍCIO do áudio (00:00:00 = início)
4. Inclua TODAS as frases cantadas, mesmo repetições
5. Se há trechos instrumentais, pule o intervalo
6. NÃO omita versos — ouça o áudio inteiro com atenção
7. Foque na PRECISÃO dos timestamps acima de tudo

FORMATO JSON:
[
  {{"index": 1, "start": "00:01:25,300", "end": "00:01:29,800", "text": "Nessun dorma! Nessun dorma!"}},
  {{"index": 2, "start": "00:01:30,200", "end": "00:01:35,400", "text": "Tu pure, o Principessa,"}}
]

Retorne APENAS o JSON, sem markdown, sem explicação.
"""
    response = model.generate_content([audio_file_ref, prompt])
    return parse_json_response(response.text)


async def transcrever_guiado_completo(
    audio_completo_path: str, letra_original: str, idioma: str, metadados: dict,
    audio_file_ref=None,
) -> list:
    """Envia áudio COMPLETO + letra ao Gemini para obter timestamps."""
    genai = _get_client()
    model = genai.GenerativeModel(
        "gemini-2.5-pro",
        generation_config=genai.GenerationConfig(temperature=0),
    )

    if audio_file_ref is not None:
        audio_file = audio_file_ref
    else:
        mime_type = _detect_mime_type(audio_completo_path)
        audio_file = genai.upload_file(audio_completo_path, mime_type=mime_type)

    prompt = f"""
Você é um assistente de legendagem de vídeos de ópera.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma: {idioma}
- Compositor: {metadados.get("compositor", "N/A")}

LETRA ORIGINAL (texto correto e oficial):
---
{letra_original}
---

TAREFA:
Ouça o áudio COMPLETO do início ao fim e marque os TIMESTAMPS de CADA verso da letra.
TODOS os versos da letra devem aparecer no resultado — a música está sendo cantada neste áudio.

REGRAS:
1. Use EXATAMENTE o texto da letra original fornecida
2. NÃO modifique nenhuma palavra
3. Marque QUANDO cada frase começa e termina no áudio com a MAIOR PRECISÃO possível (erro máximo tolerado: 0.5 segundos)
4. Timestamps relativos ao INÍCIO do áudio (00:00:00,000 = primeiro milissegundo do arquivo de áudio)
5. TODOS os versos da letra DEVEM ter timestamps — ouça o áudio inteiro com atenção
6. Se há trechos instrumentais ENTRE versos, pule o intervalo mas continue marcando os versos seguintes
7. Se há repetições não escritas na letra, adicione com [REPETIÇÃO]
8. Se não tem certeza do timestamp exato, marque sua melhor estimativa com [?]
9. Se ouvir algo cantado que não está na letra, marque como [TEXTO NÃO IDENTIFICADO]
10. NÃO omita versos — se um verso está na letra, ele está no áudio. Ouça com atenção.
11. Em trechos de CORO ou ENSEMBLE (várias vozes cantando juntas), preste atenção redobrada ao INÍCIO EXATO de cada verso — muitas vezes o coro começa uma fração de segundo depois do solista
12. Ouça o áudio pelo menos DUAS VEZES mentalmente antes de responder para garantir precisão nos timestamps

FORMATO JSON:
[
  {{"index": 1, "start": "00:01:25,300", "end": "00:01:29,800", "text": "Nessun dorma! Nessun dorma!"}},
  {{"index": 2, "start": "00:01:30,200", "end": "00:01:35,400", "text": "Tu pure, o Principessa,"}}
]

Retorne APENAS o JSON, sem markdown, sem explicação.
"""
    response = model.generate_content([audio_file, prompt])
    return parse_json_response(response.text)


async def traduzir_letra(
    segmentos_alinhados: list,
    idioma_original: str,
    idioma_alvo: str,
    metadados: dict,
) -> list:
    """Traduz letra cantada mantendo a segmentação."""
    genai = _get_client()
    model = genai.GenerativeModel("gemini-2.5-pro")

    letra_formatada = "\n".join(
        f"{s.get('index', i+1)}. {s.get('texto_final', s.get('text', ''))}"
        for i, s in enumerate(segmentos_alinhados)
    )

    nomes_idiomas = {
        "en": "inglês", "pt": "português", "es": "espanhol",
        "de": "alemão", "fr": "francês", "it": "italiano", "pl": "polonês",
    }

    prompt = f"""
Traduza a seguinte letra de ópera para {nomes_idiomas.get(idioma_alvo, idioma_alvo)}.

Música: {metadados.get("musica", "")}
Compositor: {metadados.get("compositor", "")}
Idioma original: {idioma_original}

Letra:
---
{letra_formatada}
---

Regras:
1. Tradução LITERÁRIA (não literal)
2. Para árias famosas, use traduções consagradas
3. MANTENHA A MESMA NUMERAÇÃO
4. Cada segmento traduzido deve ter comprimento similar ao original

Retorne APENAS JSON:
[
  {{"index": 1, "original": "...", "traducao": "..."}},
  ...
]
"""
    response = model.generate_content(prompt)
    return parse_json_response(response.text)


async def buscar_letra(metadados: dict) -> str:
    """Pede ao Gemini para fornecer a letra de uma ária."""
    genai = _get_client()
    model = genai.GenerativeModel("gemini-2.5-pro")

    prompt = f"""
Forneça a letra COMPLETA e ORIGINAL da seguinte música/ária:

Artista/Personagem: {metadados.get("artista", "N/A")}
Música/Ária: {metadados["musica"]}
Ópera: {metadados.get("opera", "N/A")}
Compositor: {metadados.get("compositor", "N/A")}
Idioma original: {metadados["idioma"]}

Regras:
1. Retorne APENAS a letra no idioma original
2. Mantenha a grafia exata
3. Separe os versos em linhas
4. NÃO invente texto

Retorne APENAS a letra, sem explicação ou markdown.
"""
    response = model.generate_content(prompt)
    return response.text.strip()
