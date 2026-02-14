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


async def transcrever_guiado_completo(
    audio_completo_path: str, letra_original: str, idioma: str, metadados: dict
) -> list:
    """Envia áudio COMPLETO + letra ao Gemini para obter timestamps."""
    genai = _get_client()
    model = genai.GenerativeModel("gemini-2.5-pro")

    audio_file = genai.upload_file(audio_completo_path)

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
Ouça o áudio COMPLETO e marque os TIMESTAMPS de cada verso da letra.

REGRAS:
1. Use EXATAMENTE o texto da letra original fornecida
2. NÃO modifique nenhuma palavra
3. Marque QUANDO cada frase começa e termina no áudio
4. Timestamps relativos ao INÍCIO do áudio (00:00:00 = início do vídeo)
5. Ignore trechos instrumentais, aplausos e silêncios
6. Se uma frase NÃO APARECE no áudio, OMITA-a
7. Se há repetições não escritas na letra, adicione com [REPETIÇÃO]
8. Se não tem certeza do alinhamento, adicione [?]
9. Marque [TEXTO NÃO IDENTIFICADO] se ouvir algo fora da letra

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
