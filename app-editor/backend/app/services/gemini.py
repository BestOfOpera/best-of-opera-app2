"""Serviço de integração com Gemini 2.5 Pro."""
import asyncio
import json
import logging
import re
from app.config import GEMINI_API_KEY
from shared.retry import async_retry

_logger = logging.getLogger(__name__)


class SafetyFilterError(Exception):
    """Gemini blocked the response due to safety filter."""
    pass


# Lazy init do client
_client = None


def _get_client():
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY not configured. Set it in .env or environment variables."
            )
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


def _extract_response_text(response) -> str:
    """Extrai texto da resposta do Gemini, tratando bloqueio por safety filter."""
    try:
        text = response.text
    except ValueError:
        # Safety filter bloqueou a resposta
        block_reason = None
        if hasattr(response, "prompt_feedback") and response.prompt_feedback:
            block_reason = getattr(response.prompt_feedback, "block_reason", None)
        if hasattr(response, "candidates") and response.candidates:
            for c in response.candidates:
                ratings = getattr(c, "safety_ratings", [])
                blocked = [r for r in ratings if getattr(r, "blocked", False)]
                if blocked:
                    block_reason = f"safety_ratings: {blocked}"
        raise SafetyFilterError(
            f"Gemini bloqueou a resposta (safety filter). "
            f"Motivo: {block_reason or 'desconhecido'}. "
            f"Tente novamente ou ajuste o conteúdo."
        )
    # Resposta vazia — Gemini às vezes retorna conteúdo vazio sem erro explícito
    if not text or not text.strip():
        raise RuntimeError("Gemini retornou resposta vazia — retry")
    return text


def _detect_mime_type(path: str) -> str:
    if path.endswith(".wav"):
        return "audio/wav"
    elif path.endswith(".ogg"):
        return "audio/ogg"
    elif path.endswith(".flac"):
        return "audio/flac"
    return "audio/mpeg"


# Exceções transientes da API Gemini que justificam retry
_GEMINI_TRANSIENT = (RuntimeError, ConnectionError, OSError)


async def mapear_estrutura_audio(
    audio_file_ref, idioma: str, metadados: dict, letra_original: str = ""
) -> list:
    """Fase 1: Mapear a estrutura temporal do áudio.

    Pede ao Gemini para identificar QUANDO cada frase é cantada,
    avançando cronologicamente pelo áudio. Foco em timestamps, não em texto.
    """
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

    contexto_letra = ""
    if letra_original:
        contexto_letra = f"""
LETRA DE REFERÊNCIA (para ajudar a identificar o texto cantado):
---
{letra_original}
---
ATENÇÃO: A cantora pode repetir estrofes inteiras. Cada repetição = segmento novo.
"""

    prompt = f"""
Ouça este áudio de ópera do INÍCIO ao FIM com atenção máxima aos MOMENTOS em que cada frase é cantada.

CONTEXTO:
- Artista: {metadados.get("artista", "Desconhecido")}
- Música: {metadados.get("musica", "Desconhecida")}
- Idioma: {nome_idioma}
- Compositor: {metadados.get("compositor", "N/A")}
{contexto_letra}
TAREFA: Avance pelo áudio CRONOLOGICAMENTE. A cada frase cantada, registre:
- O MOMENTO EXATO (MM:SS,mmm) em que a frase COMEÇA
- O MOMENTO EXATO em que a frase TERMINA
- O texto cantado

MÉTODO — faça assim:
1. Avance do segundo 0 até o fim do áudio
2. Quando ouvir canto começar, marque o timestamp de início
3. Quando a frase terminar (pausa ou próxima frase), marque o fim
4. Se a MESMA frase é cantada novamente mais tarde, crie um NOVO segmento
5. NÃO pule nenhum trecho cantado, mesmo que seja repetição

IMPORTANTE SOBRE ÓPERA:
- Cantores repetem estrofes inteiras (com ornamentações)
- Se "Casta Diva" é cantada em 01:55 e DE NOVO em 03:10, são 2 segmentos
- O resultado deve ter 30-50 segmentos para uma ária completa
- Timestamps em MM:SS,mmm (ex: 01:25,300)

REGRA DE FORMATAÇÃO: Cada segmento de texto deve ter NO MÁXIMO 43 caracteres.
Se uma frase for mais longa que 43 caracteres, divida em dois segmentos com timestamps proporcionais.
Quebre em pausas naturais: vírgulas, pontos, ou pausas na música.
Exemplos:
- BOM: "Tempra ancora lo zelo audace." (31 chars) → 1 segmento
- BOM: "Casta diva, che inargenti" (25 chars) → 1 segmento
- RUIM: "La donna è mobile qual piuma al vento muta d'accento" (52 chars) → dividir em 2
- CORRETO: "La donna è mobile qual piuma" + "al vento muta d'accento" → 2 segmentos

FORMATO JSON (retorne APENAS isto):
[
  {{"index": 1, "start": "01:25,300", "end": "01:29,800", "text": "Casta Diva, che inargenti"}},
  {{"index": 2, "start": "01:30,200", "end": "01:35,400", "text": "queste sacre antiche piante"}}
]
"""
    loop = asyncio.get_running_loop()

    @async_retry(max_attempts=3, backoff_base=2.0, exceptions=(*_GEMINI_TRANSIENT, asyncio.TimeoutError))
    async def _call():
        response = await asyncio.wait_for(
            loop.run_in_executor(None, model.generate_content, [audio_file_ref, prompt]),
            timeout=300,
        )
        return parse_json_response(_extract_response_text(response))

    return await _call()


async def transcrever_cego(
    audio_file_ref, idioma: str, metadados: dict
) -> list:
    """Transcrição cega simplificada — redireciona para mapear_estrutura_audio."""
    return await mapear_estrutura_audio(audio_file_ref, idioma, metadados)


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
        loop = asyncio.get_running_loop()
        mime_type = _detect_mime_type(audio_completo_path)

        @async_retry(max_attempts=3, backoff_base=2.0, exceptions=(ConnectionError, OSError, asyncio.TimeoutError))
        async def _upload():
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: genai.upload_file(audio_completo_path, mime_type=mime_type)
                ),
                timeout=120,
            )

        audio_file = await _upload()

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

REGRA DE FORMATAÇÃO: Cada segmento de texto deve ter NO MÁXIMO 43 caracteres.
Se uma frase for mais longa que 43 caracteres, divida em dois segmentos com timestamps proporcionais.
Quebre em pausas naturais: vírgulas, pontos, ou pausas na música.
Exemplos:
- BOM: "Tempra ancora lo zelo audace." (31 chars) → 1 segmento
- BOM: "Casta diva, che inargenti" (25 chars) → 1 segmento
- RUIM: "La donna è mobile qual piuma al vento muta d'accento" (52 chars) → dividir em 2
- CORRETO: "La donna è mobile qual piuma" + "al vento muta d'accento" → 2 segmentos

FORMATO JSON (retorne APENAS isto, sem markdown):
[
  {{"index": 1, "start": "01:25,300", "end": "01:29,800", "text": "Nessun dorma! Nessun dorma!"}},
  {{"index": 2, "start": "01:30,200", "end": "01:35,400", "text": "Tu pure, o Principessa,"}}
]
"""
    loop = asyncio.get_running_loop()

    @async_retry(max_attempts=3, backoff_base=2.0, exceptions=(*_GEMINI_TRANSIENT, asyncio.TimeoutError))
    async def _call():
        response = await asyncio.wait_for(
            loop.run_in_executor(None, model.generate_content, [audio_file, prompt]),
            timeout=300,
        )
        return parse_json_response(_extract_response_text(response))

    return await _call()


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
        loop = asyncio.get_running_loop()
        mime_type = _detect_mime_type(audio_completo_path)

        @async_retry(max_attempts=3, backoff_base=2.0, exceptions=(ConnectionError, OSError, asyncio.TimeoutError))
        async def _upload():
            return await asyncio.wait_for(
                loop.run_in_executor(
                    None, lambda: genai.upload_file(audio_completo_path, mime_type=mime_type)
                ),
                timeout=120,
            )

        audio_file = await _upload()

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

REGRA DE FORMATAÇÃO: Cada segmento de texto deve ter NO MÁXIMO 43 caracteres.
Se uma frase for mais longa que 43 caracteres, divida em dois segmentos com timestamps proporcionais.
Quebre em pausas naturais: vírgulas, pontos, ou pausas na música.
Exemplos:
- BOM: "Tempra ancora lo zelo audace." (31 chars) → 1 segmento
- BOM: "Casta diva, che inargenti" (25 chars) → 1 segmento
- RUIM: "La donna è mobile qual piuma al vento muta d'accento" (52 chars) → dividir em 2
- CORRETO: "La donna è mobile qual piuma" + "al vento muta d'accento" → 2 segmentos

FORMATO JSON (retorne APENAS isto, sem markdown):
[
  {{"index": 1, "start": "01:25,300", "end": "01:29,800", "text": "primeiro verso..."}},
  ...todos os {len(versos)} versos...
]
"""
    loop = asyncio.get_running_loop()

    @async_retry(max_attempts=3, backoff_base=2.0, exceptions=(*_GEMINI_TRANSIENT, asyncio.TimeoutError))
    async def _call():
        response = await asyncio.wait_for(
            loop.run_in_executor(None, model.generate_content, [audio_file, prompt]),
            timeout=300,
        )
        return parse_json_response(_extract_response_text(response))

    return await _call()


async def traduzir_letra(
    segmentos_alinhados: list,
    idioma_original: str,
    idioma_alvo: str,
    metadados: dict,
    timeout_seconds: int = 120,
    max_retries: int = 2,
) -> list:
    """Traduz letra cantada mantendo a segmentação.

    Inclui timeout e retry para evitar travamento em chamadas longas.
    """
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
    loop = asyncio.get_running_loop()

    @async_retry(
        max_attempts=max_retries + 1,
        backoff_base=2.0,
        exceptions=(*_GEMINI_TRANSIENT, asyncio.TimeoutError, json.JSONDecodeError),
    )
    async def _call():
        response = await asyncio.wait_for(
            loop.run_in_executor(None, model.generate_content, prompt),
            timeout=timeout_seconds,
        )
        return parse_json_response(_extract_response_text(response))

    return await _call()


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
    loop = asyncio.get_running_loop()

    @async_retry(max_attempts=3, backoff_base=2.0, exceptions=(*_GEMINI_TRANSIENT, asyncio.TimeoutError))
    async def _call():
        response = await asyncio.wait_for(
            loop.run_in_executor(None, model.generate_content, prompt),
            timeout=120,
        )
        return _extract_response_text(response).strip()

    return await _call()
