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
Você é um transcritor profissional de ópera com ouvido absoluto.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma cantado: {nome_idioma}
- Compositor: {metadados.get("compositor", "N/A")}

TAREFA OBRIGATÓRIA:
Ouça o áudio do PRIMEIRO ao ÚLTIMO segundo. Transcreva CADA FRASE cantada com timestamps EXATOS.

REGRA FUNDAMENTAL SOBRE REPETIÇÕES:
Em ópera, é COMUM o cantor repetir a mesma estrofe inteira (às vezes 2 ou 3 vezes, com ornamentações diferentes).
Você DEVE transcrever CADA repetição como segmentos separados com seus próprios timestamps.
Se "Casta Diva, che inargenti" é cantada em 01:55 e repetida em 03:10, são DOIS segmentos distintos.
NUNCA pule uma repetição — cada vez que um verso é cantado, ele precisa de seu próprio segmento.

REGRAS:
1. Transcreva exatamente o que ouve no idioma original ({nome_idioma}) — não invente texto
2. CADA FRASE cantada = 1 segmento, incluindo repetições do mesmo verso
3. Timestamps no formato MM:SS,mmm (minutos:segundos,milissegundos). Ex: 01:25,300
4. Precisão: ±0.5 segundo
5. Se há introdução instrumental, comece quando o CANTO inicia
6. NÃO agrupe múltiplos versos num único segmento
7. Ouça o áudio INTEIRO até o final — os últimos versos são tão importantes quanto os primeiros
8. Espere pelo menos 20-40 segmentos para uma ária completa com repetições

FORMATO JSON (retorne APENAS isto, sem markdown):
[
  {{"index": 1, "start": "01:25,300", "end": "01:29,800", "text": "Nessun dorma! Nessun dorma!"}},
  {{"index": 2, "start": "01:30,200", "end": "01:35,400", "text": "Tu pure, o Principessa,"}}
]
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

    # Contar versos na letra para dar referência ao Gemini
    versos = [v.strip() for v in letra_original.split("\n") if v.strip()]
    n_versos = len(versos)

    prompt = f"""
Você é um transcritor profissional de ópera com ouvido absoluto.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma: {idioma}
- Compositor: {metadados.get("compositor", "N/A")}

LETRA ORIGINAL ({n_versos} versos — TODOS devem aparecer no resultado):
---
{letra_original}
---

TAREFA OBRIGATÓRIA:
Ouça o áudio do PRIMEIRO ao ÚLTIMO segundo. A letra acima está sendo cantada neste áudio.
Marque o timestamp EXATO de CADA verso.

REGRA FUNDAMENTAL — REPETIÇÕES EM ÓPERA:
Em árias de ópera, o cantor frequentemente REPETE a mesma estrofe inteira (com ornamentações).
Exemplo: "Casta Diva, che inargenti" pode ser cantada uma primeira vez em 01:55 e REPETIDA em 03:10.
Você DEVE criar segmentos separados para CADA repetição. A letra acima pode ter cada verso uma vez,
mas no áudio ele pode ser cantado 2 ou 3 vezes. Marque TODAS as ocorrências.
Espere retornar MAIS segmentos do que versos na letra ({n_versos} versos, mas provavelmente 30-50 segmentos com repetições).

REGRAS:
1. Use EXATAMENTE o texto da letra original — não modifique nenhuma palavra
2. CADA vez que um verso é cantado = 1 segmento (mesmo verso repetido = segmentos separados)
3. Timestamps no formato MM:SS,mmm (minutos:segundos,milissegundos). Ex: 01:25,300
4. Precisão: ±0.5 segundo
5. Se há introdução instrumental, comece quando o CANTO inicia
6. Para repetições, use o mesmo texto do verso + marque [REPETIÇÃO] no final
7. NÃO agrupe versos — cada frase separada
8. Ouça até o FINAL do áudio

FORMATO JSON (retorne APENAS isto, sem markdown):
[
  {{"index": 1, "start": "01:25,300", "end": "01:29,800", "text": "Nessun dorma! Nessun dorma!"}},
  {{"index": 2, "start": "01:30,200", "end": "01:35,400", "text": "Tu pure, o Principessa,"}}
]
"""
    response = model.generate_content([audio_file, prompt])
    return parse_json_response(response.text)


async def completar_transcricao(
    audio_completo_path: str,
    letra_original: str,
    resultado_parcial: list,
    idioma: str,
    metadados: dict,
    audio_file_ref=None,
) -> list:
    """Passo de correção: recebe resultado incompleto e pede ao Gemini para completar.

    Estratégia: mostra ao Gemini quais versos já foram encontrados e pede para
    localizar os que faltam no áudio.
    """
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

    # Formatar resultado parcial para mostrar ao Gemini
    parcial_json = json.dumps(resultado_parcial, ensure_ascii=False, indent=2)

    # Identificar versos da letra que NÃO foram cobertos
    versos = [v.strip() for v in letra_original.split("\n") if v.strip()]

    prompt = f"""
Você é um transcritor profissional de ópera revisando uma transcrição INCOMPLETA.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma: {idioma}
- Compositor: {metadados.get("compositor", "N/A")}

LETRA COMPLETA ({len(versos)} versos):
---
{letra_original}
---

TRANSCRIÇÃO ANTERIOR (incompleta — apenas {len(resultado_parcial)} segmentos encontrados):
{parcial_json}

PROBLEMA: A transcrição anterior está INCOMPLETA. Faltam versos.
Compare a letra completa com os segmentos acima e identifique quais versos estão faltando.

TAREFA:
Ouça o áudio NOVAMENTE do início ao fim. Produza uma transcrição COMPLETA com TODOS os {len(versos)} versos da letra.
Use os timestamps da transcrição anterior como referência para os segmentos que já estão corretos,
mas CORRIJA timestamps imprecisos e ADICIONE os segmentos que faltam.

REGRAS:
1. Use EXATAMENTE o texto da letra original
2. Timestamps no formato MM:SS,mmm (ex: 01:25,300)
3. TODOS os {len(versos)} versos DEVEM aparecer
4. Mantenha os timestamps bons da transcrição anterior, corrija os ruins
5. ADICIONE os versos que estavam faltando com seus timestamps reais do áudio

FORMATO JSON (retorne APENAS isto, sem markdown):
[
  {{"index": 1, "start": "01:25,300", "end": "01:29,800", "text": "primeiro verso..."}},
  ...todos os {len(versos)} versos...
]
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
