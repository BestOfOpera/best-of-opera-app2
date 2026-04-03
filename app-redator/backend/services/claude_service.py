from __future__ import annotations
import json
import re
from typing import Optional
import anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.prompts.hook_helper import detect_hook_language
from backend.prompts.overlay_prompt import (
    build_overlay_prompt,
    build_overlay_prompt_with_custom,
)
from backend.prompts.post_prompt import build_post_prompt, build_post_prompt_with_custom
from backend.prompts.youtube_prompt import (
    build_youtube_prompt,
    build_youtube_prompt_with_custom,
)

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
MODEL = "claude-sonnet-4-6"

# Common Portuguese words for post-generation leak detection
_PT_COMMON_WORDS = {"e", "de", "do", "da", "que", "com", "para", "uma", "um", "os", "as"}

import re

def _limpar_texto_overlay(texto: str) -> str:
    """Fix common orthographic issues: stuck words and missing spaces after punctuation."""
    if not texto:
        return texto
    # Normalizar TODOS os tipos de quebra de linha para espaço:
    # 1. Newlines reais (1 char) — quando Claude escreve \n no JSON e json.loads converte para newline real
    # 2. Literal \n e \N (2 chars: barra+letra) — quando Claude escreve \\n no JSON
    # Sem isso, "nunca\nse" vira "nuncasetocam" no frontend (ERR-056 v2)
    texto = texto.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    texto = texto.replace("\\n", " ").replace("\\N", " ")
    # Espaço após pontuação colada a palavra
    texto = re.sub(r'([,;:!?])([A-ZÀ-Úa-zà-ú])', r'\1 \2', texto)
    # Espaço após ponto colado a letra maiúscula (ex: "fim.Começo")
    texto = re.sub(r'([.])([A-ZÁÀÃÂÉÊÍÓÕÔÚÇ])', r'\1 \2', texto)
    # Espaço após aspas/apóstrofo fechando colado a palavra (ex: Marquis'para → Marquis' para)
    texto = re.sub(r"(['\"\u2019\u201D\)\]])([A-Za-záàãâéêíóõôúçÁÀÃÂÉÊÍÓÕÔÚÇ])", r"\1 \2", texto)
    # Espaço antes de maiúscula colada após minúscula (palavras unidas ex: "elaFez")
    texto = re.sub(r'([a-záàãâéêíóõôúç])([A-ZÁÀÃÂÉÊÍÓÕÔÚÇ])', r'\1 \2', texto)
    # Espaço entre número e letra / letra e número (ex: "3vezes", "anos1842")
    texto = re.sub(r'(\d)([A-Za-záàãâéêíóõôúçÁÀÃÂÉÊÍÓÕÔÚÇ])', r'\1 \2', texto)
    texto = re.sub(r'([A-Za-záàãâéêíóõôúçÁÀÃÂÉÊÍÓÕÔÚÇ])(\d)', r'\1 \2', texto)
    # Múltiplos espaços → um espaço
    texto = re.sub(r' {2,}', ' ', texto)
    return texto.strip()


def _build_language_system_prompt(language: str) -> str:
    """Build system-level language enforcement instruction."""
    if language == "português":
        return "You must write ALL output exclusively in português. Never switch languages mid-text."
    return (
        f"You must write ALL output exclusively in {language}. "
        "Never switch to Portuguese, even in the final sentence."
    )


def _check_language_leak(text: str, target_language: str) -> None:
    """Log warning if the last sentence of generated text appears to contain Portuguese."""
    if target_language == "português":
        return
    # Get last meaningful sentence
    sentences = [s.strip() for s in text.replace("\n", " ").split(".") if s.strip()]
    if not sentences:
        return
    last = sentences[-1].lower()
    words = set(last.split())
    found = words & _PT_COMMON_WORDS
    if len(found) >= 3:
        print(
            f"ALERTA: possível trecho em português detectado na geração — revisar manualmente. "
            f"Idioma alvo: {target_language}. Palavras PT encontradas: {found}"
        )


def _call_claude(prompt: str, system: str | None = None) -> str:
    kwargs: dict = dict(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
    if system:
        kwargs["system"] = system
    message = client.messages.create(**kwargs)
    return message.content[0].text.strip()


def _strip_json_fences(raw: str) -> str:
    """Remove markdown code fences from JSON response."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if "```" in text:
            text = text[: text.rfind("```")]
    return text.strip()


def detect_metadata_from_text(youtube_url: str, title: str, description: str) -> dict:
    """Use Claude to extract music metadata from YouTube title and description."""
    prompt = f"""You are a classical music expert (opera, instrumental, orchestral, choral, and all subgenres). Based on the YouTube video title and description below, extract the metadata for this performance.

YouTube Title: {title}
YouTube Description:
{description}
{"YouTube URL: " + youtube_url if youtube_url else ""}

STEP 1: From the title and description, identify:
- The EXACT title of the piece being performed
- ALL performers/artists (singers, musicians, ensembles — NOT the composer)

STEP 2: Determine the performance type:
- SOLO: One performer
- DUET: Two performers — you MUST list BOTH names
- ENSEMBLE/CHORUS: Multiple performers — list ALL names or ensemble name

STEP 3: Use YOUR KNOWLEDGE of classical music to fill in biographical fields (composer, voice_type, nationality, composition_year, album_opera). You are an expert — you know composers, works, voice types, instruments. DO NOT leave these fields empty if you can determine them. Note: voice_type may be an instrument (e.g. "Piano", "Violin", "Guitar") for instrumental performances.

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece that is EXPLICITLY written in the title or description of the video. If the exact name is NOT clearly stated, return "work" as an EMPTY STRING "". Do NOT guess or infer. It is better to leave it empty than to guess wrong.

CRITICAL RULE FOR DATES: For birth_date and death_date, ONLY fill if the EXACT date appears explicitly in the YouTube title or description text above. If the date is NOT written in the input text, return an empty string "". Do NOT use your training knowledge for dates — they may be outdated or wrong. If you know only the year from the text, use "01/01/YYYY".

FORMATTING for multiple artists: separate with " & " for artists, " / " for voice_type, nationality, birth_date, death_date.

Return ONLY a JSON object with these exact keys:
- "artist": Performer name(s)
- "work": The EXACT name of the piece (EMPTY STRING if not explicitly in title/description)
- "composer": The composer's full name
- "composition_year": Year composed (e.g. "1832")
- "nationality": Artist nationality/ies separated by " / "
- "nationality_flag": Flag emoji(s) separated by space
- "voice_type": Voice type or instrument(s) separated by " / "
- "birth_date": Birth date(s) in dd/mm/yyyy separated by " / "
- "death_date": Death date(s) in dd/mm/yyyy or "" if alive, separated by " / "
- "album_opera": The parent work, album, or opera this belongs to
- "confidence": "high" if you identified artist and work clearly, "medium" if work was left empty because not explicitly in title/description

Return the JSON object and nothing else."""

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    return json.loads(_strip_json_fences(raw))


def detect_metadata(youtube_url: str, screenshot_base64: Optional[str] = None, screenshot_media_type: str = "image/png") -> dict:
    """Use Claude to extract music metadata from a YouTube screenshot and/or URL."""
    prompt_text = """Look at this screenshot of a YouTube video page about a classical music performance (opera, instrumental, orchestral, choral, or any subgenre).

STEP 1: Read CAREFULLY the video title, description, channel name, and ALL visible text. Identify:
- The EXACT title of the piece being performed (read it precisely from the screenshot, do not guess)
- ALL performers/artists visible (singers, musicians, ensembles — NOT the composer)

STEP 2: Determine the performance type:
- SOLO: One performer (recital, concerto soloist, etc.)
- DUET: Two performers — you MUST list BOTH names
- ENSEMBLE/TRIO: Multiple performers — list ALL names
- CHORUS: A choir — use the choir/ensemble name as artist, conductor if visible

STEP 3: Use YOUR KNOWLEDGE of classical music to fill in biographical fields (composer, voice_type, nationality, composition_year, album_opera). You are an expert — you know composers, works, voice types, instruments. DO NOT leave these fields empty if you can determine them. Note: voice_type may be an instrument (e.g. "Piano", "Violin", "Guitar") for instrumental performances.

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece that is EXPLICITLY visible in the screenshot title or description. If the exact name is NOT clearly stated in the visible text, return "work" as an EMPTY STRING "". Do NOT guess or infer. It is better to leave it empty than to guess wrong.

CRITICAL RULE FOR DATES: For birth_date and death_date, ONLY fill if the EXACT date appears explicitly in the visible text (title or description). If the date is NOT written in the visible text, return an empty string "". Do NOT use your training knowledge for dates — they may be outdated or wrong. If you know only the year from the text, use "01/01/YYYY".

FORMATTING RULES FOR MULTIPLE ARTISTS:
- Separate multiple artist names with " & " (e.g. "Nicolai Gedda & Mirella Freni")
- For voice_type, list each type/instrument matching each artist, separated by " / " (e.g. "Tenor / Soprano" or "Violin / Piano")
- For nationality, list each nationality separated by " / " (e.g. "Sweden / Italy")
- For nationality_flag, list each flag separated by " " (e.g. "🇸🇪 🇮🇹")
- For birth_date and death_date, list each separated by " / " matching artist order
- For choruses: voice_type = "Choir" or "Choir & [Conductor voice/role]"

EXAMPLE for a duet — if you see "Nicolai Gedda & Mirella Freni - Là ci darem la mano":
{{"artist": "Nicolai Gedda & Mirella Freni", "work": "Là ci darem la mano", "composer": "Wolfgang Amadeus Mozart", "composition_year": "1787", "nationality": "Sweden / Italy", "nationality_flag": "🇸🇪 🇮🇹", "voice_type": "Tenor / Soprano", "birth_date": "11/07/1925 / 27/02/1935", "death_date": "08/01/2017 / 09/02/2020", "album_opera": "Don Giovanni", "confidence": "high"}}

Return ONLY a JSON object with these exact keys:
- "artist": Performer name(s) — use " & " for multiple
- "work": The EXACT name of the piece (EMPTY STRING if not explicitly visible in screenshot)
- "composer": The composer's full name
- "composition_year": Year composed (e.g. "1832")
- "nationality": Artist nationality/ies separated by " / "
- "nationality_flag": Flag emoji(s) separated by space
- "voice_type": Voice type or instrument(s) separated by " / "
- "birth_date": Birth date(s) in dd/mm/yyyy separated by " / "
- "death_date": Death date(s) in dd/mm/yyyy separated by " / ", "" if alive
- "album_opera": The parent work, album, or opera this belongs to
- "confidence": "high" if you identified artist and work clearly from screenshot, "medium" if work was left empty because not explicitly visible

Return the JSON object and nothing else."""

    if youtube_url:
        prompt_text += f"\n\nYouTube URL for additional context: {youtube_url}"

    if screenshot_base64:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": screenshot_media_type, "data": screenshot_base64}},
            {"type": "text", "text": prompt_text},
        ]
    else:
        content = prompt_text

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )
    raw = message.content[0].text.strip()
    return json.loads(_strip_json_fences(raw))


def _build_rc_detect_prompt_text(youtube_url: str, title: str, description: str) -> str:
    """Prompt de detecção de metadata para RC (instrumental/orquestral)."""
    return f"""You are a classical music expert specializing in instrumental, orchestral, chamber, and all non-vocal classical music. Based on the YouTube video title and description below, extract the metadata for this performance.

YouTube Title: {title}
YouTube Description:
{description}
{"YouTube URL: " + youtube_url if youtube_url else ""}

STEP 1: From the title and description, identify:
- The EXACT title of the piece being performed (include catalogue number if present: BWV, Op., K., etc.)
- ALL performers: soloists, orchestra/ensemble, conductor

STEP 2: Determine the formation:
- SOLO: One performer with one instrument (e.g. "Piano Solo", "Violin Solo")
- DUO/TRIO/QUARTET: Small ensemble — list instrument combination (e.g. "String Quartet", "Piano Trio")
- ORCHESTRA: Full orchestra — identify the orchestra name and conductor
- CHAMBER: Chamber ensemble — identify the ensemble name

STEP 3: Use YOUR KNOWLEDGE of classical music to fill in:
- Composer's full name and nationality
- Year of composition (approximate decade if exact year unknown)
- Whether the piece belongs to a larger work (symphony, suite, ballet, opera)
- The instrument/formation type
- The category that best fits

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece that is EXPLICITLY written in the title or description. Include catalogue numbers (BWV, Op., K., etc.) if present. If the exact name is NOT clearly stated, return "work" as an EMPTY STRING "". Do NOT guess.

Return ONLY a JSON object with these exact keys:
- "artist": Performer name(s) — soloists separated by " & "
- "work": The EXACT name of the piece with catalogue number (EMPTY STRING if not explicit)
- "composer": The composer's full name
- "composition_year": Year composed (e.g. "1832")
- "nationality": Composer's nationality
- "nationality_flag": Flag emoji of composer's nationality
- "voice_type": "" (not applicable for instrumental)
- "birth_date": "" (not extracted for RC)
- "death_date": "" (not extracted for RC)
- "album_opera": The parent work if this is a movement/excerpt (symphony, suite, ballet, opera name)
- "instrument_formation": The instrument or formation type (e.g. "Piano solo", "String Quartet", "Orquestra sinfônica")
- "orchestra": Orchestra or ensemble name (empty string if not applicable)
- "conductor": Conductor name (empty string if not applicable)
- "category": One of: "Orchestral", "Chamber", "Piano Solo", "Strings", "Winds", "Choral/Sacred", "Ballet", "Contemporary", "Crossover", "Opera", "Other"
- "confidence": "high" if you identified work and artist clearly, "medium" if work was left empty

Return the JSON object and nothing else."""


def _build_rc_detect_prompt_screenshot(youtube_url: str) -> str:
    """Prompt de detecção de metadata por screenshot para RC."""
    return f"""Look at this screenshot of a YouTube video page about a classical music performance (instrumental, orchestral, chamber, or any non-vocal classical genre).

STEP 1: Read CAREFULLY the video title, description, channel name, and ALL visible text. Identify:
- The EXACT title of the piece (include catalogue numbers like BWV, Op., K. if visible)
- ALL performers: soloists, orchestra/ensemble, conductor

STEP 2: Determine the formation:
- SOLO: One performer with one instrument
- DUO/TRIO/QUARTET: Small ensemble
- ORCHESTRA: Full orchestra — identify orchestra name and conductor
- CHAMBER: Chamber ensemble

STEP 3: Use YOUR KNOWLEDGE of classical music to fill in composer, nationality, year, category, formation.

CRITICAL RULE FOR "work": ONLY use the name EXPLICITLY visible in the screenshot. Include catalogue numbers if visible. EMPTY STRING if not clearly stated.

Return ONLY a JSON object with these exact keys:
- "artist": Performer name(s) — soloists separated by " & "
- "work": The EXACT name with catalogue number (EMPTY STRING if not explicit)
- "composer": The composer's full name
- "composition_year": Year composed
- "nationality": Composer's nationality
- "nationality_flag": Flag emoji
- "voice_type": ""
- "birth_date": ""
- "death_date": ""
- "album_opera": Parent work if this is a movement/excerpt
- "instrument_formation": Instrument or formation type (e.g. "Piano solo", "String Quartet")
- "orchestra": Orchestra/ensemble name (empty if N/A)
- "conductor": Conductor name (empty if N/A)
- "category": One of: "Orchestral", "Chamber", "Piano Solo", "Strings", "Winds", "Choral/Sacred", "Ballet", "Contemporary", "Crossover", "Opera", "Other"
- "confidence": "high" or "medium"

{"YouTube URL for additional context: " + youtube_url if youtube_url else ""}

Return the JSON object and nothing else."""


def detect_metadata_from_text_rc(youtube_url: str, title: str, description: str) -> dict:
    """RC: extract metadata from YouTube title/description for instrumental music."""
    prompt = _build_rc_detect_prompt_text(youtube_url, title, description)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    return json.loads(_strip_json_fences(raw))


def detect_metadata_rc(youtube_url: str, screenshot_base64: Optional[str] = None, screenshot_media_type: str = "image/png") -> dict:
    """RC: extract metadata from screenshot for instrumental music."""
    prompt_text = _build_rc_detect_prompt_screenshot(youtube_url)

    if screenshot_base64:
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": screenshot_media_type, "data": screenshot_base64}},
            {"type": "text", "text": prompt_text},
        ]
    else:
        content = prompt_text

    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": content}],
    )
    raw = message.content[0].text.strip()
    return json.loads(_strip_json_fences(raw))


def generate_overlay(project, custom_prompt: Optional[str] = None, brand_config=None) -> list[dict]:
    lang = detect_hook_language(project)
    system = _build_language_system_prompt(lang)
    if custom_prompt:
        prompt = build_overlay_prompt_with_custom(project, custom_prompt, brand_config=brand_config)
    else:
        prompt = build_overlay_prompt(project, brand_config=brand_config)
    raw = _call_claude(prompt, system=system)
    parsed = json.loads(_strip_json_fences(raw))

    # Apply orthographic cleaning (ERR-056) — char limit enforced by prompt + human review
    for leg in parsed:
        if "text" in leg:
            leg["text"] = _limpar_texto_overlay(leg["text"])

    # --- Validação de timestamps + CTA fixo ---
    # Claude gera timestamps flexíveis. Este script CORRIGE problemas sem
    # forçar intervalos iguais. Limites vêm do perfil da marca (brand_config).
    bc = brand_config or {}
    interval_secs = bc.get("overlay_interval_secs", 6)

    def _ts_to_secs(ts: str) -> int:
        try:
            p = ts.split(":")
            return int(p[0]) * 60 + int(p[1])
        except (ValueError, IndexError):
            return 0

    def _secs_to_ts(s: int) -> str:
        s = max(0, s)
        return f"{s // 60:02d}:{s % 60:02d}"

    # Calcular duração do vídeo
    vid_duration = 0
    if project.cut_start and project.cut_end:
        try:
            s_parts = project.cut_start.split(":")
            e_parts = project.cut_end.split(":")
            vid_duration = (int(e_parts[0]) * 60 + int(e_parts[1])) - (int(s_parts[0]) * 60 + int(s_parts[1]))
        except (ValueError, IndexError):
            pass
    elif project.original_duration:
        try:
            parts = project.original_duration.split(":")
            vid_duration = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            pass

    # Posição fixa do CTA: duração - intervalo
    cta_secs = max(0, vid_duration - interval_secs) if vid_duration > 0 else 0
    narrative_ceiling = max(0, cta_secs - 2) if cta_secs > 0 else 0

    def _calcular_duracao_leitura(text: str) -> float:
        """Duração de exibição baseada no tempo de leitura.
        Viés para leitura lenta (público contemplativo).
        Range: 5.0s a 8.0s.
        - Texto curto (2 palavras): 4.7 → 5.0s (clamp)
        - Texto médio (5 palavras): 5.75s
        - Texto longo (8 palavras): 6.8s
        - Texto longo (10+ palavras): 7.5-8.0s (clamp)
        """
        palavras = len(text.split())
        duracao = (palavras * 0.35) + 4.0
        return max(5.0, min(8.0, duracao))

    if parsed and vid_duration > 10:
        # Timing variável por tempo de leitura (substitui banda fixa min/max gap)
        current_ts = 0.0
        prev_ts = 0.0
        for i, entry in enumerate(parsed):
            if i == 0:
                # Primeira legenda sempre em 00:00
                current_ts = 0.0
            else:
                # Duração baseada no texto da legenda ANTERIOR
                duracao = _calcular_duracao_leitura(parsed[i - 1].get("text", ""))
                current_ts += duracao

            # Respeitar ceiling narrativo (espaço reservado pro CTA)
            if narrative_ceiling > 0 and current_ts > narrative_ceiling:
                current_ts = max(prev_ts + 1, narrative_ceiling)

            entry["timestamp"] = _secs_to_ts(int(round(current_ts)))
            prev_ts = current_ts

        print(f"[generate_overlay] Timestamps por leitura: {len(parsed)} legendas, "
              f"ceiling={narrative_ceiling}s, cta_pos={cta_secs}s, video={vid_duration}s")

    # Anexar CTA fixo da marca como última legenda (SPEC-010)
    # Posição fixa: vid_duration - interval (garante tempo de tela)
    cta_text = bc.get("overlay_cta", "") or ""
    if isinstance(cta_text, str) and cta_text.strip():
        if vid_duration > 0:
            cta_ts = _secs_to_ts(cta_secs)
        elif parsed:
            # Fallback sem duração: após última narrativa + intervalo
            cta_ts = _secs_to_ts(_ts_to_secs(parsed[-1]["timestamp"]) + interval_secs)
        else:
            cta_ts = "00:00"
        cta_entry = {"timestamp": cta_ts, "text": cta_text.strip(), "_is_cta": True}
        if vid_duration > 0:
            cta_entry["end"] = _secs_to_ts(vid_duration)
        parsed.append(cta_entry)
        print(f"[generate_overlay] CTA fixo: '{cta_text.strip()[:50]}' @ {cta_ts} end={cta_entry.get('end', 'auto')} (video={vid_duration}s)")

    # Check language leak on subtitle texts
    all_text = " ".join(item.get("text", "") for item in parsed)
    _check_language_leak(all_text, lang)
    return parsed


def generate_hooks(project, brand_config=None) -> list:
    """Gera 5 hooks específicos ao vídeo para o operador escolher."""
    from backend.prompts.hook_prompt import build_hook_generation_prompt

    lang = detect_hook_language(project)
    system = _build_language_system_prompt(lang)
    prompt = build_hook_generation_prompt(project, brand_config=brand_config)
    raw = _call_claude(prompt, system=system)
    parsed = json.loads(_strip_json_fences(raw))

    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON array, got {type(parsed).__name__}")

    # Validar e limpar cada hook
    max_chars = (brand_config or {}).get("overlay_max_chars", 70)
    result = []
    for item in parsed[:5]:
        hook_text = item.get("hook", "").strip()
        if len(hook_text) > max_chars:
            # Truncar no último espaço antes do limite
            hook_text = hook_text[:max_chars].rsplit(" ", 1)[0]
        result.append({
            "angle": item.get("angle", ""),
            "hook": hook_text,
            "thread": item.get("thread", ""),
        })

    return result


# Padrões de engajamento genérico que o LLM insiste em gerar (pre-compilados)
_ENGAGEMENT_BAIT_PATTERNS = [
    re.compile(r'.*🔥.*❄️.*', re.IGNORECASE),
    re.compile(r'.*❄️.*🔥.*', re.IGNORECASE),
    re.compile(r'.*isso (te )?dá.*\?', re.IGNORECASE),
    re.compile(r'.*does this (give|make).*\?', re.IGNORECASE),
    re.compile(r'.*conta nos comentários.*', re.IGNORECASE),
    re.compile(r'.*tell us in the comments.*', re.IGNORECASE),
]

# Separadores markdown que o LLM adiciona entre seções
_MARKDOWN_SEPARATORS = frozenset(('---', '___', '***', '—', '——', '———'))


def _sanitize_post(text: str) -> str:
    """Remove padrões de engajamento genérico e artefatos de formatação do LLM."""
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        # Remover separadores markdown
        if line.strip() in _MARKDOWN_SEPARATORS:
            continue
        # Remover linhas de engajamento genérico
        if any(p.search(line) for p in _ENGAGEMENT_BAIT_PATTERNS):
            continue
        cleaned.append(line)
    result = re.sub(r'\n{3,}', '\n\n', '\n'.join(cleaned))
    # Corrigir emoji do header: 🎵→🎶 (prompt diz 🎶 fixo, LLM às vezes usa 🎵)
    if result and result[0] == '🎵':
        result = '🎶' + result[1:]
    return result.strip()


def generate_post(project, custom_prompt: Optional[str] = None, brand_config=None) -> dict:
    custom_post = (brand_config or {}).get("custom_post_structure", "")
    warning = None
    if not custom_post:
        warning = "Estrutura de post não configurada para esta marca. Usando estrutura padrão de 5 seções."

    lang = detect_hook_language(project)
    system = _build_language_system_prompt(lang)
    if custom_prompt:
        prompt = build_post_prompt_with_custom(project, custom_prompt, brand_config=brand_config)
    else:
        prompt = build_post_prompt(project, brand_config=brand_config)
    result = _call_claude(prompt, system=system)
    _check_language_leak(result, lang)
    result = _sanitize_post(result)
    return {"text": result, "warning": warning}


def _strip_markdown_preamble(text: str) -> str:
    """Remove markdown headers and label-only lines from LLM response."""
    cleaned = []
    for line in text.strip().splitlines():
        stripped = line.strip()
        # Skip markdown headers (# Title, ## Resposta, etc.)
        if re.match(r'^#{1,3}\s', stripped):
            continue
        # Skip label-only lines like "**Title:**" or "Title:" or "Resposta:"
        label = re.sub(r'[*_`]', '', stripped).strip()
        if label.lower().rstrip(':') in ('title', 'tags', 'resposta', 'titulo', 'título', 'response'):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def generate_youtube(project, custom_prompt: Optional[str] = None, brand_config=None) -> tuple[str, str]:
    lang = detect_hook_language(project)
    system = _build_language_system_prompt(lang)
    if custom_prompt:
        prompt = build_youtube_prompt_with_custom(project, custom_prompt, brand_config=brand_config)
    else:
        prompt = build_youtube_prompt(project, brand_config=brand_config)
    raw = _call_claude(prompt, system=system)
    raw = _strip_markdown_preamble(raw)
    _check_language_leak(raw, lang)
    lines = [l.strip() for l in raw.strip().splitlines() if l.strip()]
    if not lines:
        return "", ""
    title = lines[0]
    # Tags are the last line if multiple lines, or second line
    tags = lines[-1] if len(lines) > 1 else ""
    # If title and tags ended up the same (single line), try splitting by comma count
    if title == tags:
        tags = ""
    return title, tags


# ═══════════════════════════════════════════════════════════════
# RC (Reels Classics) — Funções de geração
# ═══════════════════════════════════════════════════════════════

import logging
import time as _time

_rc_logger = logging.getLogger("rc_pipeline")


def _call_claude_json(prompt: str, max_tokens: int = 2000, temperature: float = 0.5) -> dict:
    """Chama Claude e parseia resposta JSON. Limpeza agressiva antes de retry."""
    print(f"[RC _call_claude_json] Enviando {len(prompt)} chars, max_tokens={max_tokens}, temp={temperature}", flush=True)
    system = "Respond in valid JSON only. No markdown fences, no preamble, no explanation outside the JSON."
    start = _time.time()
    message = client.messages.create(
        model=MODEL, max_tokens=max_tokens, temperature=temperature,
        system=system, messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    elapsed = _time.time() - start
    print(f"[RC _call_claude_json] Resposta: {len(raw)} chars em {elapsed:.1f}s", flush=True)

    # Tentativa 1: parse direto com strip_json_fences
    cleaned = _strip_json_fences(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        print(f"[RC _call_claude_json] JSON inválido. Primeiros 200: {raw[:200]}", flush=True)
        print(f"[RC _call_claude_json] JSON inválido. Últimos 200: {raw[-200:]}", flush=True)

    # Tentativa 2: extrair JSON por braces (limpeza agressiva, sem nova chamada)
    first_brace = raw.find('{')
    last_brace = raw.rfind('}')
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        extracted = raw[first_brace:last_brace + 1]
        try:
            result = json.loads(extracted)
            print(f"[RC _call_claude_json] JSON extraído por braces OK", flush=True)
            return result
        except json.JSONDecodeError:
            pass

    # Tentativa 3: extrair por brackets (caso seja array)
    first_bracket = raw.find('[')
    last_bracket = raw.rfind(']')
    if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
        extracted = raw[first_bracket:last_bracket + 1]
        try:
            result = json.loads(extracted)
            print(f"[RC _call_claude_json] JSON extraído por brackets OK", flush=True)
            return result
        except json.JSONDecodeError:
            pass

    # Tentativa 4: retry com nova chamada ao Claude (último recurso)
    print(f"[RC _call_claude_json] Limpeza falhou. Fazendo retry com nova chamada...", flush=True)
    start2 = _time.time()
    message2 = client.messages.create(
        model=MODEL, max_tokens=max_tokens, temperature=temperature,
        system=system + " CRITICAL: Your previous response was not valid JSON. Return ONLY the JSON object, nothing else.",
        messages=[{"role": "user", "content": prompt}],
    )
    raw2 = message2.content[0].text.strip()
    elapsed2 = _time.time() - start2
    print(f"[RC _call_claude_json] Retry: {len(raw2)} chars em {elapsed2:.1f}s", flush=True)

    cleaned2 = _strip_json_fences(raw2)
    try:
        return json.loads(cleaned2)
    except json.JSONDecodeError:
        # Última tentativa: braces no retry também
        fb = raw2.find('{')
        lb = raw2.rfind('}')
        if fb != -1 and lb != -1 and lb > fb:
            try:
                return json.loads(raw2[fb:lb + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(
            f"Claude retornou JSON inválido após 2 tentativas. "
            f"Últimos 500 chars: {raw2[-500:]}"
        )


def _extract_rc_metadata(project) -> dict:
    """Extrai metadata do projeto no formato esperado pelos prompts RC."""
    return {
        "artist": project.artist or "",
        "work": project.work or "",
        "composer": project.composer or "",
        "composition_year": project.composition_year or "",
        "nationality": project.nationality or "",
        "instrument_formation": getattr(project, 'instrument_formation', '') or "",
        "orchestra": getattr(project, 'orchestra', '') or "",
        "conductor": getattr(project, 'conductor', '') or "",
        "category": project.category or "",
        "album_opera": project.album_opera or "",
        "cut_start": project.cut_start or "00:00",
        "cut_end": project.cut_end or "01:00",
    }


def _sanitize_rc(texto: str) -> str:
    """Pós-processamento determinístico para RC."""
    if not texto:
        return texto

    # Remove travessões (marca de IA mais comum)
    texto = texto.replace(" — ", ". ")
    texto = texto.replace("— ", ". ")
    texto = texto.replace(" —", ".")
    texto = texto.replace("—", ".")
    texto = texto.replace(" – ", ", ")
    texto = texto.replace("–", ",")

    # Remove metadados vazados
    texto = re.sub(r'\d+px', '', texto)
    texto = re.sub(
        r'\b(GANCHO|CORPO|CLÍMAX|FECHAMENTO|CTA|CONSTRUÇÃO|DESENVOLVIMENTO)\b\s*',
        '', texto, flags=re.IGNORECASE
    )

    # Remove markdown
    texto = texto.replace('**', '')
    texto = texto.replace('__', '')
    texto = texto.replace('---', '')
    texto = texto.replace('___', '')
    texto = texto.replace('***', '')

    # Remove emojis de overlay (exceto ❤️ no CTA)
    for emoji in ['🎵', '🎶', '🎼', '💫', '🌟', '⭐', '🎭', '🎪']:
        texto = texto.replace(emoji, '')

    # Limpa espaços extras e linhas vazias
    texto = re.sub(r' +', ' ', texto)
    texto = re.sub(r'\n\s*\n\s*\n', '\n\n', texto)
    texto = texto.strip()

    return texto


def _calc_duracao_video(cut_start: str, cut_end: str) -> float:
    """Converte MM:SS para segundos e retorna duração."""
    def to_sec(t):
        if not t:
            return 0
        parts = str(t).strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        return 0
    return max(0, to_sec(cut_end) - to_sec(cut_start))


def _process_overlay_rc(response: dict, project) -> list:
    """Converte output do LLM em overlay_json compatível com o editor.
    Calcula timestamps deterministicamente. Aplica sanitização."""
    legendas = response.get("legendas", [])

    duracao_video = _calc_duracao_video(project.cut_start, project.cut_end)
    cta_duracao = max(5.0, duracao_video * 0.13)
    tempo_narrativo = duracao_video - cta_duracao

    overlay_json = []
    timestamp_sec = 0.0

    for leg in legendas:
        texto = leg.get("texto", "")
        tipo = leg.get("tipo", "corpo")

        texto = _sanitize_rc(texto)

        if not texto:
            continue

        # Calcular duração desta legenda
        if tipo == "cta":
            dur = cta_duracao
        else:
            palavras = len(texto.split())
            dur = palavras / 2.5  # ~2.5 palavras/segundo
            dur = max(4.0, min(7.0, round(dur, 1)))

        # Ajustar se estourar o tempo narrativo
        if tipo != "cta" and tempo_narrativo > 0 and timestamp_sec + dur > tempo_narrativo:
            dur = max(4.0, tempo_narrativo - timestamp_sec)

        # Formatar timestamp MM:SS
        mins = int(timestamp_sec // 60)
        secs = int(timestamp_sec % 60)
        ts = f"{mins:02d}:{secs:02d}"

        overlay_json.append({
            "text": texto,
            "timestamp": ts,
            "type": "gancho" if tipo == "gancho" else ("cta" if tipo == "cta" else "corpo"),
            "_is_cta": tipo == "cta",
        })

        # Gap ZERO
        timestamp_sec += dur

    return overlay_json


def _format_post_rc(response: dict) -> str:
    """Monta post_text formatado a partir do JSON do LLM."""
    h1 = response.get("header_linha1", "")
    h2 = response.get("header_linha2", "")
    h3 = response.get("header_linha3", "")
    p1 = response.get("paragrafo1", "")
    p2 = response.get("paragrafo2", "")
    p3 = response.get("paragrafo3", "")
    cta = response.get("cta", "👉 Siga, o melhor da música clássica, diariamente no seu feed.")
    hashtags = response.get("hashtags", [])

    lines = [h1, h2]
    if h3:
        lines.append(h3)
    lines.append("•")
    lines.append(p1)
    lines.append("•")
    lines.append(p2)
    lines.append("•")
    lines.append(p3)
    lines.append("•")
    lines.append(cta)
    lines.append("•")
    lines.append("•")
    lines.append("•")
    lines.append(" ".join(hashtags))

    return "\n".join(lines)


# ── RC Generation Functions ──────────────────────────────

def generate_research_rc(project, brand_config=None) -> dict:
    """Gera pesquisa profunda para RC. Salva em project.research_data."""
    from backend.prompts.rc_research_prompt import build_rc_research_prompt

    print(f"[RC Research] Iniciando para project {project.id}", flush=True)
    _rc_logger.info(f"[RC Research] Iniciando para project {project.id}")
    metadata = _extract_rc_metadata(project)
    prompt = build_rc_research_prompt(metadata)
    print(f"[RC Research] Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)", flush=True)
    _rc_logger.info(f"[RC Research] Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")

    result = _call_claude_json(prompt, max_tokens=8192, temperature=0.7)
    _rc_logger.info(f"[RC Research] Completo, {len(json.dumps(result))} chars resultado")
    project.research_data = result
    return result


def generate_hooks_rc(project, brand_config=None) -> dict:
    """Gera ganchos para RC usando pesquisa como base. Salva em project.hooks_json."""
    from backend.prompts.rc_hook_prompt import build_rc_hook_prompt

    _rc_logger.info(f"[RC Hooks] Iniciando para project {project.id}")
    metadata = _extract_rc_metadata(project)
    prompt = build_rc_hook_prompt(metadata, project.research_data or {})
    _rc_logger.info(f"[RC Hooks] Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")

    result = _call_claude_json(prompt, max_tokens=2000, temperature=0.7)
    n_ganchos = len(result.get("ganchos", []))
    _rc_logger.info(f"[RC Hooks] Completo, {n_ganchos} ganchos gerados")
    project.hooks_json = result
    return result


def generate_overlay_rc(project, brand_config=None) -> list:
    """Gera overlay para RC. Calcula timestamps. Salva em project.overlay_json."""
    from backend.prompts.rc_overlay_prompt import build_rc_overlay_prompt

    _rc_logger.info(f"[RC Overlay] Iniciando para project {project.id}, hook='{(project.selected_hook or '')[:50]}'")
    metadata = _extract_rc_metadata(project)

    # Buscar fio narrativo do hook selecionado
    hook_fio = ""
    if project.hooks_json and project.selected_hook:
        for h in (project.hooks_json or {}).get("ganchos", []):
            if h.get("texto") == project.selected_hook:
                hook_fio = h.get("fio_narrativo", "")
                break

    prompt = build_rc_overlay_prompt(
        metadata, project.research_data or {},
        project.selected_hook or "", hook_fio
    )
    _rc_logger.info(f"[RC Overlay] Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")

    response = _call_claude_json(prompt, max_tokens=3000, temperature=0.5)
    overlay_json = _process_overlay_rc(response, project)
    _rc_logger.info(f"[RC Overlay] Completo, {len(overlay_json)} legendas")

    project.overlay_json = overlay_json
    return overlay_json


def generate_post_rc(project, brand_config=None) -> str:
    """Gera descrição Instagram para RC. Salva em project.post_text."""
    from backend.prompts.rc_post_prompt import build_rc_post_prompt

    _rc_logger.info(f"[RC Post] Iniciando para project {project.id}")
    metadata = _extract_rc_metadata(project)
    prompt = build_rc_post_prompt(
        metadata, project.research_data or {}, project.overlay_json or []
    )
    _rc_logger.info(f"[RC Post] Prompt: {len(prompt)} chars (~{len(prompt)//4} tokens)")

    response = _call_claude_json(prompt, max_tokens=2500, temperature=0.5)
    post_text = _format_post_rc(response)
    post_text = _sanitize_rc(post_text)
    _rc_logger.info(f"[RC Post] Completo, {len(post_text)} chars texto final")

    project.post_text = post_text
    return post_text


def generate_automation_rc(project, brand_config=None) -> dict:
    """Gera automação para RC. Salva em project.automation_json."""
    from backend.prompts.rc_automation_prompt import build_rc_automation_prompt

    _rc_logger.info(f"[RC Automation] Iniciando para project {project.id}")
    metadata = _extract_rc_metadata(project)
    prompt = build_rc_automation_prompt(
        metadata, project.overlay_json or [], project.post_text or ""
    )
    _rc_logger.info(f"[RC Automation] Prompt: {len(prompt)} chars")

    result = _call_claude_json(prompt, max_tokens=1000, temperature=0.5)
    _rc_logger.info(f"[RC Automation] Completo")
    project.automation_json = result
    return result
