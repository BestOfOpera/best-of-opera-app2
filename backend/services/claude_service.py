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


def generate_overlay(project, custom_prompt: Optional[str] = None) -> list[dict]:
    if custom_prompt:
        prompt = build_overlay_prompt_with_custom(project, custom_prompt)
    else:
        prompt = build_overlay_prompt(project)
    raw = _call_claude(prompt)
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    return json.loads(raw)


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
