from __future__ import annotations
import html
import re
import requests
from typing import List

from backend.config import GOOGLE_TRANSLATE_API_KEY

ALL_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]

# CTAs fixos para RC (Reels Classics) por idioma — overlay (com \n para legendas)
RC_CTA = {
    "pt": "Siga, o melhor da música clássica,\ndiariamente no seu feed. ❤️",
    "en": "Follow for the best of classical music,\ndaily on your feed. ❤️",
    "es": "Sigue, lo mejor de la música clásica,\na diario en tu feed. ❤️",
    "de": "Folge uns für die beste klassische Musik,\ntäglich in deinem Feed. ❤️",
    "fr": "Suis-nous pour le meilleur\nde la musique classique. ❤️",
    "it": "Seguici per il meglio della musica classica,\nogni giorno nel tuo feed. ❤️",
    "pl": "Obserwuj nas, najlepsza muzyka klasyczna\ncodziennie na Twoim feedzie. ❤️",
}

# CTAs fixos para RC posts (com 👉, sem \n de legenda)
RC_POST_CTA = {
    "pt": "👉 Siga, o melhor da música clássica, diariamente no seu feed.",
    "en": "👉 Follow for the best of classical music, daily on your feed.",
    "es": "👉 Sigue, lo mejor de la música clásica, a diario en tu feed.",
    "de": "👉 Folge uns für die beste klassische Musik, täglich in deinem Feed.",
    "fr": "👉 Suis-nous pour le meilleur de la musique classique.",
    "it": "👉 Seguici per il meglio della musica classica, ogni giorno nel tuo feed.",
    "pl": "👉 Obserwuj nas, najlepsza muzyka klasyczna codziennie na Twoim feedzie.",
}

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
        # Novos labels (Correção 2 / INV-3)
        "nationality:", "nacionalidade:", "nacionalidad:", "nationalität:", "nationalité:", "nazionalità:", "narodowość:",
        "date of death:", "data de falecimento:", "fecha de fallecimiento:", "todesdatum:", "date de décès:", "data di morte:", "data śmierci:",
        "type:", "tipo:", "typ:",
        "artistic director:", "diretor artístico:", "director artístico:", "künstlerischer leiter:", "directeur artistique:", "direttore artistico:", "dyrektor artystyczny:",
        "from:", "de:", "aus:", "da:", "z:",
        "libretto/text:", "libreto/texto:", "livret/texte:", "libretto/testo:", "libretto/tekst:",
        "original language:", "idioma original:", "originalsprache:", "langue originale:", "lingua originale:", "język oryginalny:",
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
    "en": {
        "Tipo de voz": "Voice type", "Data de nascimento": "Date of Birth", "Compositor": "Composer", "Data de composição": "Composition date",
        "Voice type": "Voice type", "Date of Birth": "Date of Birth", "Composer": "Composer", "Composition date": "Composition date",
        "Nacionalidade": "Nationality", "Data de falecimento": "Date of Death", "Tipo": "Type",
        "Diretor artístico": "Artistic Director", "De": "From", "Libreto/Texto": "Libretto/Text", "Idioma original": "Original language",
        "Nationality": "Nationality", "Date of Death": "Date of Death", "Type": "Type",
        "Artistic Director": "Artistic Director", "From": "From", "Libretto/Text": "Libretto/Text", "Original language": "Original language",
    },
    "pt": {
        "Voice type": "Tipo de voz", "Date of Birth": "Data de nascimento", "Composer": "Compositor", "Composition date": "Data de composição",
        "Tipo de voz": "Tipo de voz", "Data de nascimento": "Data de nascimento", "Compositor": "Compositor", "Data de composição": "Data de composição",
        "Nationality": "Nacionalidade", "Date of Death": "Data de falecimento", "Type": "Tipo",
        "Artistic Director": "Diretor artístico", "From": "De", "Libretto/Text": "Libreto/Texto", "Original language": "Idioma original",
        "Nacionalidade": "Nacionalidade", "Data de falecimento": "Data de falecimento", "Tipo": "Tipo",
        "Diretor artístico": "Diretor artístico", "De": "De", "Libreto/Texto": "Libreto/Texto", "Idioma original": "Idioma original",
    },
    "es": {
        "Voice type": "Tipo de voz", "Date of Birth": "Fecha de nacimiento", "Composer": "Compositor", "Composition date": "Fecha de composición",
        "Tipo de voz": "Tipo de voz", "Data de nascimento": "Fecha de nacimiento", "Compositor": "Compositor", "Data de composição": "Fecha de composición",
        "Nationality": "Nacionalidad", "Date of Death": "Fecha de fallecimiento", "Type": "Tipo",
        "Artistic Director": "Director artístico", "From": "De", "Libretto/Text": "Libreto/Texto", "Original language": "Idioma original",
        "Nacionalidade": "Nacionalidad", "Data de falecimento": "Fecha de fallecimiento", "Tipo": "Tipo",
        "Diretor artístico": "Director artístico", "De": "De", "Libreto/Texto": "Libreto/Texto", "Idioma original": "Idioma original",
    },
    "de": {
        "Voice type": "Stimmtyp", "Date of Birth": "Geburtsdatum", "Composer": "Komponist", "Composition date": "Kompositionsdatum",
        "Tipo de voz": "Stimmtyp", "Data de nascimento": "Geburtsdatum", "Compositor": "Komponist", "Data de composição": "Kompositionsdatum",
        "Nationality": "Nationalität", "Date of Death": "Todesdatum", "Type": "Typ",
        "Artistic Director": "Künstlerischer Leiter", "From": "Aus", "Libretto/Text": "Libretto/Text", "Original language": "Originalsprache",
        "Nacionalidade": "Nationalität", "Data de falecimento": "Todesdatum", "Tipo": "Typ",
        "Diretor artístico": "Künstlerischer Leiter", "De": "Aus", "Libreto/Texto": "Libretto/Text", "Idioma original": "Originalsprache",
    },
    "fr": {
        "Voice type": "Type de voix", "Date of Birth": "Date de naissance", "Composer": "Compositeur", "Composition date": "Date de composition",
        "Tipo de voz": "Type de voix", "Data de nascimento": "Date de naissance", "Compositor": "Compositeur", "Data de composição": "Date de composition",
        "Nationality": "Nationalité", "Date of Death": "Date de décès", "Type": "Type",
        "Artistic Director": "Directeur artistique", "From": "De", "Libretto/Text": "Livret/Texte", "Original language": "Langue originale",
        "Nacionalidade": "Nationalité", "Data de falecimento": "Date de décès", "Tipo": "Type",
        "Diretor artístico": "Directeur artistique", "De": "De", "Libreto/Texto": "Livret/Texte", "Idioma original": "Langue originale",
    },
    "it": {
        "Voice type": "Tipo di voce", "Date of Birth": "Data di nascita", "Composer": "Compositore", "Composition date": "Data di composizione",
        "Tipo de voz": "Tipo di voce", "Data de nascimento": "Data di nascita", "Compositor": "Compositore", "Data de composição": "Data di composizione",
        "Nationality": "Nazionalità", "Date of Death": "Data di morte", "Type": "Tipo",
        "Artistic Director": "Direttore artistico", "From": "Da", "Libretto/Text": "Libretto/Testo", "Original language": "Lingua originale",
        "Nacionalidade": "Nazionalità", "Data de falecimento": "Data di morte", "Tipo": "Tipo",
        "Diretor artístico": "Direttore artistico", "De": "Da", "Libreto/Texto": "Libretto/Testo", "Idioma original": "Lingua originale",
    },
    "pl": {
        "Voice type": "Typ głosu", "Date of Birth": "Data urodzenia", "Composer": "Kompozytor", "Composition date": "Data kompozycji",
        "Tipo de voz": "Typ głosu", "Data de nascimento": "Data urodzenia", "Compositor": "Kompozytor", "Data de composição": "Data kompozycji",
        "Nationality": "Narodowość", "Date of Death": "Data śmierci", "Type": "Typ",
        "Artistic Director": "Dyrektor artystyczny", "From": "Z", "Libretto/Text": "Libretto/Tekst", "Original language": "Język oryginalny",
        "Nacionalidade": "Narodowość", "Data de falecimento": "Data śmierci", "Tipo": "Typ",
        "Diretor artístico": "Dyrektor artystyczny", "De": "Z", "Libreto/Texto": "Libretto/Tekst", "Idioma original": "Język oryginalny",
    },
}


def _translate_credit_labels(section3_and_rest: str, target_lang: str) -> str:
    """Translate credit labels in Section 3 using hardcoded translations."""
    label_map = CREDIT_LABELS.get(target_lang)
    if not label_map:
        return section3_and_rest
    for en_label, translated_label in label_map.items():
        section3_and_rest = section3_and_rest.replace(f"{en_label}:", f"{translated_label}:")
    return section3_and_rest


_FLAG_RE = re.compile(r"[\U0001F1E0-\U0001F1FF]{2}")


def _translate_credit_values(credits: str, target_lang: str) -> str:
    """Traduz apenas os VALORES das linhas de crédito (após o ':').

    Pula linhas que contêm emoji de bandeira — são nomes próprios/entidades.
    """
    lines = credits.split("\n")
    result: list[str] = []
    for line in lines:
        if ":" not in line or _FLAG_RE.search(line):
            result.append(line)
            continue
        label, value = line.split(":", 1)
        value_stripped = value.strip()
        if not value_stripped:
            result.append(line)
            continue
        translated_value = translate_text(value_stripped, target_lang)
        result.append(f"{label}: {translated_value}")
    return "\n".join(result)


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
        # Novos labels (Correção 2 / INV-3)
        "nationality:", "nacionalidade:", "nacionalidad:", "nationalität:", "nationalité:", "nazionalità:", "narodowość:",
        "date of death:", "data de falecimento:", "fecha de fallecimiento:", "todesdatum:", "date de décès:", "data di morte:", "data śmierci:",
        "type:", "tipo:", "typ:",
        "artistic director:", "diretor artístico:", "director artístico:", "künstlerischer leiter:", "directeur artistique:", "direttore artistico:", "dyrektor artystyczny:",
        "from:", "de:", "aus:", "da:", "z:",
        "libretto/text:", "libreto/texto:", "livret/texte:", "libretto/testo:", "libretto/tekst:",
        "original language:", "idioma original:", "originalsprache:", "langue originale:", "lingua originale:", "język oryginalny:",
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
        # Preserve brand hashtags (don't translate known brand names)
        brand_hashtags = {"bestofopera", "reelsclassics"}
        if word.lower() in brand_hashtags:
            result.append(tag)
            continue
        translated = translate_text(word, target_lang)
        # Hashtags can't have spaces — collapse
        translated = translated.replace(" ", "")
        result.append(f"#{translated}")
    return " ".join(result)


def _translate_post_fallback(post_text: str, target_lang: str) -> str:
    """Fallback para posts sem bloco de créditos (ex: RC).

    Estrutura esperada: intro (1ª linha) + storytelling + CTA + hashtags.
    Traduz tudo exceto a intro line e preserva hashtags com tradução individual.
    """
    lines = post_text.split("\n")

    # Separar intro (primeira linha não-vazia)
    intro_end = 0
    for i, line in enumerate(lines):
        if line.strip():
            intro_end = i + 1
            break

    intro = "\n".join(lines[:intro_end])
    rest = "\n".join(lines[intro_end:])

    # Separar hashtags (última linha que começa com #)
    paragraphs = rest.split("\n\n")
    hashtags = ""
    for i in range(len(paragraphs) - 1, -1, -1):
        if paragraphs[i].strip().startswith("#"):
            hashtags = paragraphs.pop(i).strip()
            break

    # Separar CTA RC (bloco que contém 👉) do storytelling
    cta_block = ""
    story_paragraphs = []
    for para in paragraphs:
        if "👉" in para:
            cta_block = para
        else:
            story_paragraphs.append(para)

    # Traduzir storytelling
    body = "\n\n".join(story_paragraphs).strip()
    translated_body = translate_text(body, target_lang) if body else ""

    # CTA: usar versão fixa se RC (detectado por 👉), senão traduzir normalmente
    if cta_block:
        translated_cta = RC_POST_CTA.get(target_lang, RC_POST_CTA["en"])
    else:
        translated_cta = ""

    translated_hashtags = _translate_hashtags(hashtags, target_lang) if hashtags else ""

    parts = [intro, translated_body]
    if translated_cta:
        parts.append("•\n" + translated_cta)
    if translated_hashtags:
        parts.append(translated_hashtags)

    return "\n\n".join(p for p in parts if p.strip())


def translate_post_text(post_text: str, target_lang: str) -> str:
    """Translate Section 2 (storytelling), CTA (Section 4), and hashtags (Section 5).

    Credit labels in Section 3 are translated via hardcoded mappings.
    If the post has no credit block (e.g. RC brand), falls back to translating
    the entire storytelling body (everything between intro line and CTA/hashtags).
    """
    before, section2, after = extract_post_section2(post_text)
    if not section2:
        # Fallback: post sem bloco de créditos (ex: RC).
        # Traduzir tudo exceto a primeira linha (intro com emojis) e hashtags.
        return _translate_post_fallback(post_text, target_lang)

    translated_section2 = translate_text(section2, target_lang)

    # Split after into credits, CTA, and hashtags
    credits, cta, hashtags = _split_credits_cta_hashtags(after)

    # Translate each part: labels via hardcoded map, values via Google Translate
    label_translated = _translate_credit_labels(credits, target_lang)
    translated_credits = _translate_credit_values(label_translated, target_lang)
    translated_cta = translate_text(cta, target_lang) if cta else ""
    translated_hashtags = _translate_hashtags(hashtags, target_lang) if hashtags else ""

    # Reassemble — strip each part to avoid double blank lines
    parts = [before.strip("\n"), translated_section2.strip("\n"), translated_credits.strip("\n")]
    if translated_cta:
        parts.append(translated_cta.strip("\n"))
    if translated_hashtags:
        parts.append(translated_hashtags.strip("\n"))

    return "\n\n".join(p for p in parts if p)


def translate_overlay_json(overlay_json: list, target_lang: str, brand_slug: str | None = None) -> list:
    """Translate the text field of each overlay subtitle.
    Para RC, usa CTA fixo traduzido ao invés de tradução automática."""
    result = []
    for entry in overlay_json:
        if entry.get("_is_cta") and brand_slug == "reels-classics":
            translated_text = RC_CTA.get(target_lang, RC_CTA["en"])
        else:
            translated_text = translate_text(entry.get("text", ""), target_lang)
        item = {"timestamp": entry["timestamp"], "text": translated_text}
        if entry.get("_is_cta"):
            item["_is_cta"] = True
        result.append(item)
    return result


def translate_tags(tags: str, target_lang: str) -> str:
    """Translate comma-separated tags."""
    if not tags:
        return ""
    tag_list = [t.strip() for t in tags.split(",")]
    translated = [translate_text(t, target_lang) for t in tag_list if t]
    return ", ".join(translated)
