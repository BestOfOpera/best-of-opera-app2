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
    # Section 3 starts with an emoji line followed by any credit label on the next line.
    # All possible credit labels across all supported languages:
    _CREDIT_MARKERS = (
        "voice type:", "tipo de voz:", "date of birth:", "data de nascimento:",
        "composer:", "compositor:", "composition date:", "data de composição:",
        "stimmtyp:", "geburtsdatum:", "komponist:", "kompositionsdatum:",
        "type de voix:", "date de naissance:", "compositeur:", "date de composition:",
        "tipo di voce:", "data di nascita:", "compositore:", "data di composizione:",
        "typ głosu:", "data urodzenia:", "kompozytor:", "data kompozycji:",
        "fecha de nacimiento:", "fecha de composición:",
    )
    section2_end = None
    if section2_start is not None:
        for i in range(section2_start, len(lines)):
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip().lower()
                if any(next_line.startswith(marker) for marker in _CREDIT_MARKERS):
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


def _split_credits_cta_hashtags(after_text: str) -> tuple[str, str, str]:
    """Split after-Section2 text into (credits, cta, hashtags).

    Post structure after the storytelling:
    - Section 3: Credits block (artist info, composer, dates)
    - Section 4: CTA — short call-to-action line(s)
    - Section 5: Hashtags — line starting with #
    """
    paragraphs = after_text.split("\n\n")

    # Find hashtag paragraph (last one starting with #)
    hashtags = ""
    for i in range(len(paragraphs) - 1, -1, -1):
        if paragraphs[i].strip().startswith("#"):
            hashtags = paragraphs.pop(i).strip()
            break

    if not paragraphs:
        return "", "", hashtags

    # The last remaining paragraph that does NOT contain credit labels is the CTA
    credit_markers = [
        "voice type:", "tipo de voz:", "date of birth:", "data de nascimento:",
        "composer:", "compositor:", "composition date:", "data de composição:",
        "stimmtyp:", "geburtsdatum:", "komponist:", "kompositionsdatum:",
        "type de voix:", "date de naissance:", "compositeur:", "date de composition:",
        "tipo di voce:", "data di nascita:", "compositore:", "data di composizione:",
        "typ głosu:", "data urodzenia:", "kompozytor:", "data kompozycji:",
        "fecha de nacimiento:", "fecha de composición:",
    ]

    cta = ""
    if paragraphs:
        last = paragraphs[-1].strip()
        is_credit = any(marker in last.lower() for marker in credit_markers)
        if not is_credit and last:
            cta = paragraphs.pop().strip()

    credits = "\n\n".join(paragraphs)
    return credits, cta, hashtags


def _translate_hashtags(hashtag_line: str, target_lang: str) -> str:
    """Translate hashtags while preserving # prefix and brand tags."""
    if not hashtag_line or not hashtag_line.strip():
        return hashtag_line
    tags = hashtag_line.strip().split()
    result = []
    for tag in tags:
        if not tag.startswith("#"):
            result.append(tag)
            continue
        word = tag[1:]
        # Preserve brand hashtag
        if word.lower() == "bestofopera":
            result.append(tag)
            continue
        translated = translate_text(word, target_lang)
        # Hashtags can't have spaces — collapse
        translated = translated.replace(" ", "")
        result.append(f"#{translated}")
    return " ".join(result)


def translate_post_text(post_text: str, target_lang: str) -> str:
    """Translate Section 2 (storytelling), CTA (Section 4), and hashtags (Section 5).

    Credit labels in Section 3 are translated via hardcoded mappings.
    """
    before, section2, after = extract_post_section2(post_text)
    if not section2:
        return post_text

    translated_section2 = translate_text(section2, target_lang)

    # Split after into credits, CTA, and hashtags
    credits, cta, hashtags = _split_credits_cta_hashtags(after)

    # Translate each part
    translated_credits = _translate_credit_labels(credits, target_lang)
    translated_cta = translate_text(cta, target_lang) if cta else ""
    translated_hashtags = _translate_hashtags(hashtags, target_lang) if hashtags else ""

    # Reassemble — strip each part to avoid double blank lines
    parts = [before.strip("\n"), translated_section2.strip("\n"), translated_credits.strip("\n")]
    if translated_cta:
        parts.append(translated_cta.strip("\n"))
    if translated_hashtags:
        parts.append(translated_hashtags.strip("\n"))

    return "\n\n".join(p for p in parts if p)


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
