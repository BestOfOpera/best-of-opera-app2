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

STEP 3: Use YOUR KNOWLEDGE of classical music to fill in biographical fields (composer, voice_type, nationality, birth_date, death_date, composition_year, album_opera). You are an expert — you know composers, works, voice types, instruments, biographies. DO NOT leave biographical fields empty if you can determine them. Note: voice_type may be an instrument (e.g. "Piano", "Violin", "Guitar") for instrumental performances.

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece that is EXPLICITLY written in the title or description of the video. If the exact name is NOT clearly stated, return "work" as an EMPTY STRING "". Do NOT guess or infer. It is better to leave it empty than to guess wrong.

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

STEP 3: Use YOUR KNOWLEDGE of classical music to fill in biographical fields (composer, voice_type, nationality, birth_date, death_date, composition_year, album_opera). You are an expert — you know composers, works, voice types, instruments, biographies. DO NOT leave biographical fields empty if you can determine them. Note: voice_type may be an instrument (e.g. "Piano", "Violin", "Guitar") for instrumental performances.

CRITICAL RULE FOR "work": The "work" field MUST contain ONLY the name of the piece that is EXPLICITLY visible in the screenshot title or description. If the exact name is NOT clearly stated in the visible text, return "work" as an EMPTY STRING "". Do NOT guess or infer. It is better to leave it empty than to guess wrong.

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
        Range: 6.0s a 10.0s.
        - Texto curto (1-4 palavras): 6-7s
        - Texto médio (5-8 palavras): 7-9s
        - Texto longo (9+ palavras): 9-10s
        """
        palavras = len(text.split())
        duracao = (palavras * 0.5) + 5.0
        return max(6.0, min(10.0, duracao))

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
        parsed.append({"timestamp": cta_ts, "text": cta_text.strip(), "_is_cta": True})
        print(f"[generate_overlay] CTA fixo: '{cta_text.strip()[:50]}' @ {cta_ts} (video={vid_duration}s)")

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
