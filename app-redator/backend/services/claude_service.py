from __future__ import annotations
import json
from typing import Optional
import anthropic

from backend.config import ANTHROPIC_API_KEY
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
MODEL = "claude-sonnet-4-5-20250929"


def _call_claude(prompt: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )
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


def generate_overlay(project, custom_prompt: Optional[str] = None) -> list[dict]:
    if custom_prompt:
        prompt = build_overlay_prompt_with_custom(project, custom_prompt)
    else:
        prompt = build_overlay_prompt(project)
    raw = _call_claude(prompt)
    return json.loads(_strip_json_fences(raw))


def generate_post(project, custom_prompt: Optional[str] = None) -> str:
    if custom_prompt:
        prompt = build_post_prompt_with_custom(project, custom_prompt)
    else:
        prompt = build_post_prompt(project)
    return _call_claude(prompt)


def generate_youtube(project, custom_prompt: Optional[str] = None) -> tuple[str, str]:
    if custom_prompt:
        prompt = build_youtube_prompt_with_custom(project, custom_prompt)
    else:
        prompt = build_youtube_prompt(project)
    raw = _call_claude(prompt)
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
