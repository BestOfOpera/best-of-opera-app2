from __future__ import annotations
import html
import requests
from typing import List

from backend.config import GOOGLE_TRANSLATE_API_KEY

ALL_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]

TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
DETECT_URL = "https://translation.googleapis.com/language/translate/v2/detect"


def detect_language(text: str) -> str:
    """Detect the language of text using Google Translate API."""
    if not text or not text.strip():
        return "en"
    resp = requests.post(DETECT_URL, data={
        "q": text[:200],
        "key": GOOGLE_TRANSLATE_API_KEY,
    })
    resp.raise_for_status()
    detections = resp.json()["data"]["detections"][0]
    return detections[0]["language"] if detections else "en"


def get_target_languages(source_lang: str) -> list[str]:
    """Return all 7 target languages (source language included — will be copied, not translated)."""
    return list(ALL_LANGUAGES)


def translate_text(text: str, target_lang: str) -> str:
    if not text or not text.strip():
        return ""
    resp = requests.post(TRANSLATE_URL, data={
        "q": text,
        "target": target_lang,
        "format": "text",
        "key": GOOGLE_TRANSLATE_API_KEY,
    })
    resp.raise_for_status()
    translated = resp.json()["data"]["translations"][0]["translatedText"]
    return html.unescape(translated)


def extract_post_section2(post_text: str) -> tuple:
    """Split post into (before_section2, section2, after_section2).

    Section 2 is the storytelling block between the emoji intro (Section 1)
    and the metadata block (Section 3).
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
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().lower()
                if next_line.startswith("voice type:") or next_line.startswith("tipo de voz:"):
                    section2_end = i
                    break

    if section2_start is None or section2_end is None:
        return post_text, "", ""

    before = "\n".join(lines[:section2_start])
    section2 = "\n".join(lines[section2_start:section2_end])
    after = "\n".join(lines[section2_end:])
    return before, section2, after


CREDIT_LABELS = {
    "en": {"Tipo de voz": "Voice type", "Data de nascimento": "Date of Birth", "Compositor": "Composer", "Data de composição": "Composition date",
           "Voice type": "Voice type", "Date of Birth": "Date of Birth", "Composer": "Composer", "Composition date": "Composition date"},
    "pt": {"Voice type": "Tipo de voz", "Date of Birth": "Data de nascimento", "Composer": "Compositor", "Composition date": "Data de composição",
           "Tipo de voz": "Tipo de voz", "Data de nascimento": "Data de nascimento", "Compositor": "Compositor", "Data de composição": "Data de composição"},
    "es": {"Voice type": "Tipo de voz", "Date of Birth": "Fecha de nacimiento", "Composer": "Compositor", "Composition date": "Fecha de composición",
           "Tipo de voz": "Tipo de voz", "Data de nascimento": "Fecha de nacimiento", "Compositor": "Compositor", "Data de composição": "Fecha de composición"},
    "de": {"Voice type": "Stimmtyp", "Date of Birth": "Geburtsdatum", "Composer": "Komponist", "Composition date": "Kompositionsdatum",
           "Tipo de voz": "Stimmtyp", "Data de nascimento": "Geburtsdatum", "Compositor": "Komponist", "Data de composição": "Kompositionsdatum"},
    "fr": {"Voice type": "Type de voix", "Date of Birth": "Date de naissance", "Composer": "Compositeur", "Composition date": "Date de composition",
           "Tipo de voz": "Type de voix", "Data de nascimento": "Date de naissance", "Compositor": "Compositeur", "Data de composição": "Date de composition"},
    "it": {"Voice type": "Tipo di voce", "Date of Birth": "Data di nascita", "Composer": "Compositore", "Composition date": "Data di composizione",
           "Tipo de voz": "Tipo di voce", "Data de nascimento": "Data di nascita", "Compositor": "Compositore", "Data de composição": "Data di composizione"},
    "pl": {"Voice type": "Typ głosu", "Date of Birth": "Data urodzenia", "Composer": "Kompozytor", "Composition date": "Data kompozycji",
           "Tipo de voz": "Typ głosu", "Data de nascimento": "Data urodzenia", "Compositor": "Kompozytor", "Data de composição": "Data kompozycji"},
}


def _translate_credit_labels(section3_and_rest: str, target_lang: str) -> str:
    """Translate credit labels in Section 3 using hardcoded translations."""
    label_map = CREDIT_LABELS.get(target_lang)
    if not label_map:
        return section3_and_rest
    for en_label, translated_label in label_map.items():
        section3_and_rest = section3_and_rest.replace(f"{en_label}:", f"{translated_label}:")
    return section3_and_rest


def translate_post_text(post_text: str, target_lang: str) -> str:
    """Translate Section 2 (storytelling) and credit labels in Section 3."""
    before, section2, after = extract_post_section2(post_text)
    if not section2:
        return post_text
    translated_section2 = translate_text(section2, target_lang)
    translated_after = _translate_credit_labels(after, target_lang)
    return f"{before}\n{translated_section2}\n{translated_after}"


def translate_overlay_json(overlay_json: list, target_lang: str) -> list:
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
