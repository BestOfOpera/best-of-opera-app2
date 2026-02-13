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


def detect_metadata(youtube_url: str) -> dict:
    """Use Claude to extract opera metadata from a YouTube URL."""
    prompt = f"""Given this YouTube video URL, analyze the title, description, and any metadata you can infer to extract information about this opera/classical music performance.

URL: {youtube_url}

Extract the following fields. If you cannot determine a field with confidence, leave it as an empty string "".

Return ONLY a JSON object with these exact keys:
- "artist": The performer's full name
- "work": The name of the piece/aria/song being performed
- "composer": The composer's full name
- "composition_year": Year the piece was composed (just the year, e.g. "1831")
- "nationality": The artist's nationality/country (e.g. "Greece", "Italy")
- "nationality_flag": The flag emoji for the artist's country (e.g. "🇬🇷", "🇮🇹")
- "voice_type": Voice type or instrument (e.g. "Soprano", "Tenor", "Piano")
- "birth_date": Artist's date of birth in dd/mm/yyyy format if known, otherwise just the year
- "death_date": Artist's date of death in dd/mm/yyyy format if known, empty string if still alive
- "album_opera": The album or opera this piece belongs to
- "confidence": "high" if you are confident in most fields, "low" if you had to guess significantly

Return the JSON object and nothing else."""

    raw = _call_claude(prompt)
    text = _strip_json_fences(raw)
    return json.loads(text)


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
    title = lines[0] if lines else ""
    tags = lines[1] if len(lines) > 1 else ""
    return title, tags
