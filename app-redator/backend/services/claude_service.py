from __future__ import annotations
import json
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
    """Use Claude to extract opera metadata from YouTube title and description."""
    prompt = f"""You are an opera and classical music expert. Based on the YouTube video title and description below, extract the metadata for this performance.

YouTube Title: {title}
YouTube Description:
{description}
{"YouTube URL: " + youtube_url if youtube_url else ""}

STEP 1: From the title and description, identify:
- The EXACT title of the piece/aria being performed
- ALL performers/artists (singers, musicians — NOT the composer)

STEP 2: Determine the performance type:
- SOLO: One performer
- DUET: Two performers — you MUST list BOTH names
- ENSEMBLE/CHORUS: Multiple performers — list ALL names or ensemble name

STEP 3: Use YOUR KNOWLEDGE of classical music and opera to fill in biographical fields (composer, voice_type, nationality, birth_date, death_date, composition_year, album_opera). You are an expert — you know composers, operas, voice types, biographies. DO NOT leave biographical fields empty if you can determine them.

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece/aria that is EXPLICITLY written in the title or description of the video. If the exact name of the aria or piece is NOT clearly stated in the title or description, return "work" as an EMPTY STRING "". Do NOT guess, infer, or deduce the work name based on melody, performer repertoire, or any other indirect clue. It is better to leave it empty than to guess wrong.

FORMATTING for multiple artists: separate with " & " for artists, " / " for voice_type, nationality, birth_date, death_date.

Return ONLY a JSON object with these exact keys:
- "artist": Performer name(s)
- "work": The EXACT name of the piece/aria (EMPTY STRING if not explicitly in title/description)
- "composer": The composer's full name
- "composition_year": Year composed (e.g. "1832")
- "nationality": Artist nationality/ies separated by " / "
- "nationality_flag": Flag emoji(s) separated by space
- "voice_type": Voice type(s) separated by " / "
- "birth_date": Birth date(s) in dd/mm/yyyy separated by " / "
- "death_date": Death date(s) in dd/mm/yyyy or "" if alive, separated by " / "
- "album_opera": The opera or album this belongs to
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
    """Use Claude to extract opera metadata from a YouTube screenshot and/or URL."""
    prompt_text = """Look at this screenshot of a YouTube video page about an opera or classical music performance.

STEP 1: Read CAREFULLY the video title, description, channel name, and ALL visible text. Identify:
- The EXACT title of the piece/aria being performed (read it precisely from the screenshot, do not guess)
- ALL performers/artists visible (singers, musicians — NOT the composer)

STEP 2: Determine the performance type:
- SOLO: One performer (aria, recital, etc.)
- DUET: Two performers singing together — you MUST list BOTH names
- ENSEMBLE/TRIO: Multiple performers — list ALL names
- CHORUS: A choir — use the choir/ensemble name as artist, conductor if visible

STEP 3: Use YOUR KNOWLEDGE of classical music and opera to fill in biographical fields (composer, voice_type, nationality, birth_date, death_date, composition_year, album_opera). You are an expert — you know composers, operas, voice types, biographies. DO NOT leave biographical fields empty if you can determine them.

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece/aria that is EXPLICITLY visible in the screenshot title or description. If the exact name of the aria or piece is NOT clearly stated in the visible text, return "work" as an EMPTY STRING "". Do NOT guess, infer, or deduce the work name based on melody, performer repertoire, or any other indirect clue. It is better to leave it empty than to guess wrong.

FORMATTING RULES FOR MULTIPLE ARTISTS:
- Separate multiple artist names with " & " (e.g. "Nicolai Gedda & Mirella Freni")
- For voice_type, list each voice type matching each artist, separated by " / " (e.g. "Tenor / Soprano")
- For nationality, list each nationality separated by " / " (e.g. "Sweden / Italy")
- For nationality_flag, list each flag separated by " " (e.g. "🇸🇪 🇮🇹")
- For birth_date and death_date, list each separated by " / " matching artist order
- For choruses: voice_type = "Choir" or "Choir & [Conductor voice/role]"

EXAMPLE for a duet — if you see "Nicolai Gedda & Mirella Freni - Là ci darem la mano":
{{"artist": "Nicolai Gedda & Mirella Freni", "work": "Là ci darem la mano", "composer": "Wolfgang Amadeus Mozart", "composition_year": "1787", "nationality": "Sweden / Italy", "nationality_flag": "🇸🇪 🇮🇹", "voice_type": "Tenor / Soprano", "birth_date": "11/07/1925 / 27/02/1935", "death_date": "08/01/2017 / 09/02/2020", "album_opera": "Don Giovanni", "confidence": "high"}}

Return ONLY a JSON object with these exact keys:
- "artist": Performer name(s) — use " & " for multiple
- "work": The EXACT name of the piece/aria (EMPTY STRING if not explicitly visible in screenshot)
- "composer": The composer's full name
- "composition_year": Year composed (e.g. "1832")
- "nationality": Artist nationality/ies separated by " / "
- "nationality_flag": Flag emoji(s) separated by space
- "voice_type": Voice type(s) separated by " / "
- "birth_date": Birth date(s) in dd/mm/yyyy separated by " / "
- "death_date": Death date(s) in dd/mm/yyyy separated by " / ", "" if alive
- "album_opera": The opera or album this belongs to
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
            
    # Validation: Last subtitle timing (ERR-054)
    if parsed:
        duration_secs = 0
        if project.cut_start and project.cut_end:
            try:
                s_parts = project.cut_start.split(":")
                e_parts = project.cut_end.split(":")
                s_total = int(s_parts[0]) * 60 + int(s_parts[1])
                e_total = int(e_parts[0]) * 60 + int(e_parts[1])
                duration_secs = e_total - s_total
            except (ValueError, IndexError):
                pass
        elif project.original_duration:
            try:
                parts = project.original_duration.split(":")
                duration_secs = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                pass

        if duration_secs > 10:  # Only validate if we have a reasonable duration
            last_leg = parsed[-1]
            try:
                ts_parts = last_leg["timestamp"].split(":")
                ts_secs = int(ts_parts[0]) * 60 + int(ts_parts[1])
                limit = duration_secs - 5
                if ts_secs > limit:
                    new_ts = max(0, duration_secs - 8)
                    mins = new_ts // 60
                    secs = new_ts % 60
                    last_leg["timestamp"] = f"{mins:02d}:{secs:02d}"
                    print(f"[generate_overlay] Adjusted last subtitle timestamp to {last_leg['timestamp']} (duration: {duration_secs}s)")
            except (ValueError, IndexError, KeyError):
                pass

    # Check language leak on subtitle texts
    all_text = " ".join(item.get("text", "") for item in parsed)
    _check_language_leak(all_text, lang)
    return parsed


def generate_post(project, custom_prompt: Optional[str] = None, brand_config=None) -> str:
    lang = detect_hook_language(project)
    system = _build_language_system_prompt(lang)
    if custom_prompt:
        prompt = build_post_prompt_with_custom(project, custom_prompt, brand_config=brand_config)
    else:
        prompt = build_post_prompt(project, brand_config=brand_config)
    result = _call_claude(prompt, system=system)
    _check_language_leak(result, lang)
    return result


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
