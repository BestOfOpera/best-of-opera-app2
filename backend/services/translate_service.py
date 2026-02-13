from __future__ import annotations
import re
from typing import Dict, List, Tuple

LANGUAGES = ["pt", "es", "de", "fr", "it", "pl"]

_client = None


def _get_client():
    global _client
    if _client is None:
        from google.cloud import translate_v2 as translate
        _client = translate.Client()
    return _client


def translate_text(text: str, target_lang: str) -> str:
    if not text:
        return ""
    client = _get_client()
    result = client.translate(text, target_language=target_lang, source_language="en")
    return result["translatedText"]


def extract_post_section2(post_text: str) -> tuple[str, str, str]:
    """Split post into (before_section2, section2, after_section2).

    Section 2 is the storytelling block between the emoji intro (Section 1)
    and the metadata block (Section 3 starting with 🎵).
    """
    lines = post_text.split("\n")

    # Find section 2 start: after first non-empty line (the emoji intro)
    section2_start = None
    found_intro = False
    for i, line in enumerate(lines):
        if not found_intro and line.strip():
            found_intro = True
            continue
        if found_intro and section2_start is None and line.strip():
            section2_start = i
            break

    # Find section 2 end: look for the credit block (Section 3).
    # Section 3 starts with an emoji line followed by "Voice type:" on the next line.
    section2_end = None
    if section2_start is not None:
        for i in range(section2_start, len(lines)):
            stripped = lines[i].strip()
            # Check if next line contains a credit label
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().lower()
                if next_line.startswith("voice type:") or next_line.startswith("tipo de voz:"):
                    # This line is the artist credit line — start of Section 3
                    section2_end = i
                    break

    if section2_start is None or section2_end is None:
        return post_text, "", ""

    before = "\n".join(lines[:section2_start])
    section2 = "\n".join(lines[section2_start:section2_end])
    after = "\n".join(lines[section2_end:])
    return before, section2, after


def translate_post_text(post_text: str, target_lang: str) -> str:
    """Translate only Section 2 (storytelling) of the post, keep rest in English."""
    before, section2, after = extract_post_section2(post_text)
    if not section2:
        return post_text
    translated_section2 = translate_text(section2, target_lang)
    return f"{before}\n{translated_section2}\n{after}"


def translate_overlay_json(overlay_json: list[dict], target_lang: str) -> list[dict]:
    """Translate the text field of each overlay subtitle."""
    result = []
    for entry in overlay_json:
        translated_text = translate_text(entry.get("text", ""), target_lang)
        result.append({"timestamp": entry["timestamp"], "text": translated_text})
    return result


def translate_tags(tags: str, target_lang: str) -> str:
    """Translate comma-separated tags."""
    if not tags:
        return ""
    tag_list = [t.strip() for t in tags.split(",")]
    translated = [translate_text(t, target_lang) for t in tag_list if t]
    return ", ".join(translated)
