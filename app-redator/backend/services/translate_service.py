from __future__ import annotations
import html
import logging
import re
import requests
from backend.config import GOOGLE_TRANSLATE_API_KEY

_logger = logging.getLogger(__name__)

ALL_LANGUAGES = ["en", "pt", "es", "de", "fr", "it", "pl"]


def _protect_proper_names(text: str, names: list[str]) -> tuple[str, dict[str, str]]:
    """Replace proper names with placeholders before translation.
    Uses word boundary regex to avoid corrupting words that contain the name
    (e.g. "Ana" must not match inside "analisar")."""
    replacements: dict[str, str] = {}
    for i, name in enumerate(names):
        if not name or len(name) < 2:
            continue
        pattern = r'\b' + re.escape(name) + r'\b'
        if re.search(pattern, text, flags=re.IGNORECASE):
            placeholder = f"PROPERNAME{i:02d}"
            text = re.sub(pattern, placeholder, text, flags=re.IGNORECASE)
            replacements[placeholder] = name
    return text, replacements


def _restore_proper_names(text: str, replacements: dict[str, str]) -> str:
    """Restore proper names after translation.
    Uses case-insensitive match because Google Translate may alter placeholder case."""
    for placeholder, name in replacements.items():
        text = re.sub(re.escape(placeholder), name, text, flags=re.IGNORECASE)
    return text

# CTAs fixos para RC (Reels Classics) por idioma — overlay (com \n para legendas)
# Tabela canônica v3 (F6.8 Opção A — pronome explícito em DE/FR/IT/PL)
RC_CTA = {
    "pt": "Siga, o melhor da música clássica,\ndiariamente no seu feed. ❤️",
    "en": "Follow for the best of\nclassical music on your feed ❤️",
    "es": "Síguenos para lo mejor de\nla música clásica en tu feed ❤️",
    "de": "Folge uns für das Beste der\nklassischen Musik in deinem Feed ❤️",
    "fr": "Suis-nous pour le meilleur de\nla musique classique dans ton feed ❤️",
    "it": "Seguici per il meglio della\nmusica classica nel tuo feed ❤️",
    "pl": "Obserwuj nas, by poznać najlepsze\nz muzyki klasycznej ❤️",
}

# CTAs fixos para BO (Best of Opera) por idioma — overlay
BO_CTA = {
    "pt": "Siga para mais Best of Opera!",
    "en": "Follow for more Best of Opera!",
    "es": "¡Sigue para más Best of Opera!",
    "de": "Folge für mehr Best of Opera!",
    "fr": "Suivez pour plus de Best of Opera !",
    "it": "Segui per più Best of Opera!",
    "pl": "Obserwuj Best of Opera po więcej!",
}

# CTAs fixos para RC posts (com 👉, sem \n de legenda)
# Tabela canônica v3 (F6.8 Opção A — pronome explícito em DE/FR/IT/PL)
RC_POST_CTA = {
    "pt": "👉 Siga, o melhor da música clássica, diariamente no seu feed.",
    "en": "👉 Follow for the best of classical music daily on your feed.",
    "es": "👉 Síguenos para lo mejor de la música clásica en tu feed.",
    "de": "👉 Folge uns für das Beste der klassischen Musik in deinem Feed.",
    "fr": "👉 Suis-nous pour le meilleur de la musique classique dans ton feed.",
    "it": "👉 Seguici per il meglio della musica classica nel tuo feed.",
    "pl": "👉 Obserwuj nas po najlepsze utwory muzyki klasycznej.",
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


def translate_text(text: str, target_lang: str, _max_retries: int = 3) -> str:
    """Traduz texto via Google Translate v2 com retry e backoff."""
    if not text or not text.strip():
        return ""
    for attempt in range(_max_retries):
        try:
            resp = requests.post(TRANSLATE_URL, data={
                "q": text,
                "target": target_lang,
                "format": "text",
                "key": GOOGLE_TRANSLATE_API_KEY,
            })
            resp.raise_for_status()
            translated = resp.json()["data"]["translations"][0]["translatedText"]
            return html.unescape(translated)
        except Exception as e:
            if attempt < _max_retries - 1:
                import time
                wait = (attempt + 1) * 5
                _logger.warning(f"[TRANSLATE] Retry {attempt+1}/{_max_retries} '{text[:30]}...' "
                               f"→ {target_lang}: {e}. Aguardando {wait}s...")
                time.sleep(wait)
            else:
                _logger.error(f"[TRANSLATE] FALHA DEFINITIVA '{text[:30]}...' "
                              f"→ {target_lang}: {e}")
                raise


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


def _translate_header_rc(header_lines: list, target_lang: str) -> list:
    """Traduz seletivamente o header RC.
    L1: [emojis] Compositor – Obra → NÃO traduzir (nomes próprios)
    L2: Artista – instrumento [emoji] → traduzir APENAS instrumento
    L3: Orquestra – Regente → NÃO traduzir (nomes próprios)
    """
    if not header_lines or target_lang == "pt":
        return list(header_lines)

    result = list(header_lines)

    if len(result) >= 2:
        line2 = result[1]

        # Aceitar en-dash, vírgula ou hífen (_sanitize_rc converte – para ,)
        sep_found = None
        for sep in [" – ", ", ", " - "]:
            if sep in line2:
                sep_found = sep
                break

        if sep_found:
            parts = line2.split(sep_found, 1)
            artist_name = parts[0].strip()
            instrument_part = parts[1].strip()

            # Separar emoji final se houver
            emoji_suffix = ""
            clean_instrument = instrument_part
            if instrument_part:
                last_char = instrument_part[-1]
                if ord(last_char) > 8000:
                    emoji_suffix = " " + last_char
                    clean_instrument = instrument_part[:-1].strip()
                elif len(instrument_part) >= 2 and ord(instrument_part[-2]) > 8000:
                    emoji_suffix = " " + instrument_part[-2:]
                    clean_instrument = instrument_part[:-2].strip()

            if clean_instrument:
                translated_instrument = translate_text(clean_instrument, target_lang)
                if translated_instrument:
                    result[1] = f"{artist_name}{sep_found}{translated_instrument.strip()}{emoji_suffix}"

    return result


def _translate_post_fallback(post_text: str, target_lang: str,
                             protected_names: list[str] | None = None) -> str:
    """Fallback para posts sem bloco de créditos (ex: RC).

    Formato: \\n simples entre todas as linhas, • como delimitador de blocos.
    Estrutura: header, •, p1, •, p2, •, p3, •, CTA, •, •, •, hashtags
    """
    if not post_text or not post_text.strip():
        return post_text

    lines = post_text.split("\n")

    # Encontrar índices de todas as linhas que são apenas "•"
    bullet_indices = [i for i, line in enumerate(lines) if line.strip() == "•"]

    if len(bullet_indices) < 4:
        # Formato não reconhecido — extrair hashtags antes de traduzir
        lines_all = post_text.split("\n")
        hashtag_lines = []
        text_lines = []
        for line in lines_all:
            if line.strip().startswith("#"):
                hashtag_lines.append(line.strip())
            else:
                text_lines.append(line)
        translated_text = translate_text("\n".join(text_lines), target_lang)
        if hashtag_lines:
            translated_ht = _translate_hashtags(" ".join(hashtag_lines), target_lang)
            return translated_text.rstrip() + "\n" + translated_ht
        return translated_text

    # Header: tudo ANTES do primeiro •
    header_lines = lines[:bullet_indices[0]]

    # Parágrafos: conteúdo entre pares de • consecutivos
    paragraphs = []
    for i in range(len(bullet_indices) - 1):
        start = bullet_indices[i] + 1
        end = bullet_indices[i + 1]
        block = "\n".join(lines[start:end]).strip()
        if block:
            paragraphs.append(block)

    # Hashtags: tudo APÓS o último •
    last_bullet = bullet_indices[-1]
    hashtag_lines = lines[last_bullet + 1:]
    hashtags_text = "\n".join(hashtag_lines).strip()

    # Classificar: CTA (contém 👉) vs storytelling
    cta_text = ""
    story_paragraphs = []
    for para in paragraphs:
        if "👉" in para:
            cta_text = para
        else:
            story_paragraphs.append(para)

    # Traduzir seletivamente
    translated_header = _translate_header_rc(header_lines, target_lang)

    translated_paragraphs = []
    for para in story_paragraphs:
        src = para
        repl = {}
        if protected_names:
            src, repl = _protect_proper_names(src, protected_names)
        translated = translate_text(src, target_lang)
        if repl:
            translated = _restore_proper_names(translated, repl)
        if translated and translated.strip():
            translated_paragraphs.append(translated.strip())

    translated_cta = RC_POST_CTA.get(target_lang, RC_POST_CTA.get("en", cta_text))

    translated_hashtags = _translate_hashtags(hashtags_text, target_lang) if hashtags_text else ""

    # Reassemblar com \n simples e • como separadores
    result_lines = list(translated_header)

    for para in translated_paragraphs:
        result_lines.append("•")
        result_lines.append(para)

    result_lines.append("•")
    result_lines.append(translated_cta)

    result_lines.append("•")
    result_lines.append("•")
    result_lines.append("•")
    if translated_hashtags:
        result_lines.append(translated_hashtags)

    return "\n".join(result_lines)


def translate_post_text(post_text: str, target_lang: str,
                        protected_names: list[str] | None = None) -> str:
    """Translate Section 2 (storytelling), CTA (Section 4), and hashtags (Section 5).

    Credit labels in Section 3 are translated via hardcoded mappings.
    If the post has no credit block (e.g. RC brand), falls back to translating
    the entire storytelling body (everything between intro line and CTA/hashtags).
    protected_names: nomes próprios (artist, work, composer) a preservar na tradução.
    """
    before, section2, after = extract_post_section2(post_text)
    if not section2:
        # Fallback: post sem bloco de créditos (ex: RC).
        # Traduzir tudo exceto a primeira linha (intro com emojis) e hashtags.
        return _translate_post_fallback(post_text, target_lang, protected_names=protected_names)

    repl = {}
    if protected_names:
        section2, repl = _protect_proper_names(section2, protected_names)
    translated_section2 = translate_text(section2, target_lang)
    if repl:
        translated_section2 = _restore_proper_names(translated_section2, repl)

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


def translate_overlay_json(overlay_json: list, target_lang: str,
                           brand_slug: str | None = None,
                           max_chars: int = 70,
                           protected_names: list[str] | None = None) -> list:
    """Translate the text field of each overlay subtitle.
    Para RC, usa CTA fixo traduzido ao invés de tradução automática.
    RC: aplica re-wrap pós-tradução (≤33 chars/linha).
    BO/outros: valida limite total de caracteres (default 70).
    protected_names: nomes próprios (artist, work, composer) a preservar na tradução."""
    from backend.services.claude_service import _enforce_line_breaks_rc, _enforce_line_breaks_bo

    is_rc = brand_slug == "reels-classics"
    result = []
    for i, entry in enumerate(overlay_json):
        if entry.get("_is_cta"):
            if is_rc:
                translated_text = RC_CTA.get(target_lang, RC_CTA["en"])
            else:
                translated_text = BO_CTA.get(target_lang, BO_CTA["en"])
        else:
            src_text = entry.get("text", "")
            replacements = {}
            if protected_names:
                src_text, replacements = _protect_proper_names(src_text, protected_names)
            translated_text = translate_text(src_text, target_lang)
            if replacements:
                translated_text = _restore_proper_names(translated_text, replacements)
            if is_rc:
                # RC v3.1: re-wrap com limite de 38 chars/linha (margens por idioma aplicadas dentro da função)
                tipo = entry.get("type", "corpo")
                translated_text = _enforce_line_breaks_rc(translated_text, tipo, 38, lang=target_lang)
            elif max_chars and len(translated_text) > max_chars:
                # BO/outros: re-wrap em 2 linhas em vez de truncar
                max_linha = max_chars // 2
                translated_text = _enforce_line_breaks_bo(translated_text, max_chars_linha=max_linha, max_linhas=2)
        item = {"timestamp": entry["timestamp"], "text": translated_text}
        if entry.get("_is_cta"):
            item["_is_cta"] = True
        if "end" in entry:
            item["end"] = entry["end"]
        result.append(item)
    return result


def translate_tags(tags: str, target_lang: str) -> str:
    """Translate comma-separated tags."""
    if not tags:
        return ""
    tag_list = [t.strip() for t in tags.split(",")]
    translated = [translate_text(t, target_lang) for t in tag_list if t]
    return ", ".join(translated)


# ═══════════════════════════════════════════════════════════════════════════════
# Tradução via Claude — overlay + post com contexto narrativo
# ═══════════════════════════════════════════════════════════════════════════════

import json as _json
import logging as _logging
from concurrent.futures import ThreadPoolExecutor, as_completed

_translate_logger = _logging.getLogger("translate_claude")

_LANG_NAMES = {
    "en": "English", "es": "Spanish", "de": "German",
    "fr": "French", "it": "Italian", "pl": "Polish",
}


def _build_translation_prompt(
    overlay_entries: list,
    post_text: str,
    target_lang: str,
    brand_slug: str,
    brand_config: dict | None,
    research_data: str = "",
    protected_names: list | None = None,
) -> str:
    """Monta prompt de tradução para o Claude.
    Traduz overlay + post storytelling juntos para manter coerência narrativa."""
    lang_name = _LANG_NAMES.get(target_lang, target_lang)
    is_rc = brand_slug == "reels-classics"

    if is_rc:
        overlay_rules = (
            "OVERLAY RULES:\n"
            "- Maximum 38 characters per line (counting spaces) — hard limit\n"
            "- 'gancho' and 'fechamento': exactly 2 lines, separated by \\n\n"
            "- 'corpo': 2 or 3 lines, separated by \\n\n"
            "- 'cta': DO NOT translate — return EXACTLY as given\n"
            "- Balance line lengths (similar length per line)\n"
            "- German/Polish: maximum 43 characters per line (ceiling)\n"
            "- French/Italian/Spanish: maximum 41 characters per line (ceiling)"
        )
    else:
        overlay_rules = (
            "OVERLAY RULES:\n"
            "- Maximum 70 characters total per subtitle\n"
            "- If subtitle > 35 characters: split into 2 lines with \\n\n"
            "- Balance 2 lines (max 30% length difference)\n"
            "- German/Polish: maximum 40 characters per line\n"
            "- French/Italian/Spanish: maximum 38 characters per line"
        )

    # Montar overlay como lista legível
    overlay_text = ""
    for i, entry in enumerate(overlay_entries):
        tipo = entry.get("type", "corpo")
        text = entry.get("text", "")
        is_cta = entry.get("_is_cta", False)
        if is_cta:
            overlay_text += f"\n[{i+1}] (CTA — DO NOT TRANSLATE): {text}"
        else:
            overlay_text += f"\n[{i+1}] ({tipo}): {text}"

    names_instruction = ""
    if protected_names:
        names_instruction = (
            "\nPROTECTED NAMES (keep exactly as-is, do NOT translate):\n"
            + ", ".join(protected_names)
        )

    identity = (brand_config or {}).get("identity_prompt_redator", "")
    tom = (brand_config or {}).get("tom_de_voz_redator", "")

    prompt = f"""You are a professional translator specializing in classical music content for social media.

BRAND VOICE:
{identity[:500] if identity else "Poetic, evocative, respectful of classical music tradition."}

TONE:
{tom[:300] if tom else "Elegant, emotional, culturally informed."}

TASK:
Translate the following content from Portuguese to {lang_name}.
Translate BOTH the overlay subtitles AND the post description as a SINGLE coherent piece.
The overlay tells a narrative story that connects with the post — maintain narrative coherence across both.
{names_instruction}

MUSICAL CONTEXT:
{str(research_data)[:1500] if research_data else "Classical music performance."}

{overlay_rules}

POST RULES:
- Maintain the EXACT same structure (line breaks, bullet separators •, emojis)
- Translate narrative/storytelling sections naturally
- Translate hashtags to the target language (keep # prefix, no spaces inside)
- Keep emoji positions unchanged
- CTA lines with 👉: use culturally appropriate translation
- Credit labels (Voice type:, Compositor:, etc.): keep the label format, translate only values

═══════════════════════════════════════════
OVERLAY SUBTITLES TO TRANSLATE:
{overlay_text}

═══════════════════════════════════════════
POST DESCRIPTION TO TRANSLATE:
{post_text or "(no post)"}

═══════════════════════════════════════════
RESPOND IN JSON FORMAT ONLY:
{{
  "overlay": [
    {{ "index": 1, "text": "translated text with\\nline breaks" }},
    {{ "index": 2, "text": "..." }}
  ],
  "post": "full translated post text preserving structure"
}}

CRITICAL: Respect character limits per line. Use \\n for line breaks in overlay.
Each overlay entry MUST match the index from the input (1-based).
CTA entries must be returned EXACTLY as given (not translated)."""

    return prompt


def translate_one_claude(
    overlay_json: list,
    post_text: str,
    target_lang: str,
    brand_slug: str,
    project,
) -> dict | None:
    """Traduz overlay + post para 1 idioma via Claude.
    Retorna {"overlay": [...], "post": "..."} ou None se falhar."""
    from backend.services.claude_service import _call_claude_json
    from backend.config import load_brand_config

    try:
        brand_config = None
        try:
            brand_config = load_brand_config(brand_slug) if brand_slug else None
        except Exception:
            pass

        protected_names = []
        if project:
            for field in ("artist", "work", "composer"):
                val = getattr(project, field, None)
                if val and len(val) >= 2:
                    protected_names.append(val)

        research_data = ""
        if project and hasattr(project, "research_data") and project.research_data:
            research_data = (
                _json.dumps(project.research_data, ensure_ascii=False)
                if isinstance(project.research_data, dict)
                else str(project.research_data)
            )

        prompt = _build_translation_prompt(
            overlay_entries=overlay_json or [],
            post_text=post_text or "",
            target_lang=target_lang,
            brand_slug=brand_slug or "",
            brand_config=brand_config,
            research_data=research_data,
            protected_names=protected_names,
        )

        result = _call_claude_json(prompt=prompt, max_tokens=2048, temperature=0.3)

        if not result or "overlay" not in result:
            _translate_logger.warning(
                f"[CLAUDE] Resposta inválida para {target_lang}: {str(result)[:100]}"
            )
            return None

        return result

    except Exception as e:
        _translate_logger.warning(f"[CLAUDE] Erro para {target_lang}: {e}")
        return None


def translate_project_parallel(
    project,
    overlay_json: list,
    post_text: str,
    brand_slug: str,
    target_languages: list[str],
) -> dict:
    """Traduz overlay + post para TODOS os idiomas em paralelo via Claude.
    Idiomas que falharem no Claude caem para Google Translate (fallback).

    Retorna: { "en": {"data": {...}, "source": "claude"|"google"}, ... }
    """
    from backend.services.claude_service import _enforce_line_breaks_rc, _enforce_line_breaks_bo

    is_rc = brand_slug == "reels-classics"

    protected_names = []
    if project:
        for field in ("artist", "work", "composer"):
            val = getattr(project, field, None)
            if val and len(val) >= 2:
                protected_names.append(val)

    def _translate_one(lang: str) -> tuple[str, dict | None, str]:
        """Traduz 1 idioma: tenta Claude, fallback Google."""
        # Tentar Claude
        claude_result = translate_one_claude(
            overlay_json=overlay_json,
            post_text=post_text,
            target_lang=lang,
            brand_slug=brand_slug,
            project=project,
        )

        if claude_result and claude_result.get("overlay") and claude_result.get("post"):
            # Aplicar safety net enforce nos overlays do Claude
            safe_overlay = []
            for i, orig_entry in enumerate(overlay_json or []):
                claude_entry = next(
                    (e for e in claude_result["overlay"] if e.get("index") == i + 1),
                    None,
                )
                if claude_entry:
                    t_text = claude_entry.get("text", "")
                else:
                    t_text = orig_entry.get("text", "")

                if orig_entry.get("_is_cta"):
                    if is_rc:
                        t_text = RC_CTA.get(lang, RC_CTA.get("en", t_text))
                    else:
                        t_text = BO_CTA.get(lang, BO_CTA.get("en", t_text))

                if not orig_entry.get("_is_cta"):
                    if is_rc:
                        tipo = orig_entry.get("type", "corpo")
                        t_text = _enforce_line_breaks_rc(t_text, tipo, 38, lang=lang)
                    elif len(t_text) > 70:
                        t_text = _enforce_line_breaks_bo(t_text, max_chars_linha=35, max_linhas=2)

                item = {"timestamp": orig_entry.get("timestamp", ""), "text": t_text}
                if orig_entry.get("_is_cta"):
                    item["_is_cta"] = True
                if "end" in orig_entry:
                    item["end"] = orig_entry["end"]
                if "type" in orig_entry:
                    item["type"] = orig_entry["type"]
                safe_overlay.append(item)

            _translate_logger.info(f"[TRANSLATE] {lang}: Claude OK")
            return lang, {"overlay": safe_overlay, "post": claude_result["post"]}, "claude"

        # Fallback Google
        _translate_logger.info(f"[TRANSLATE] {lang}: Claude falhou, usando Google")
        try:
            g_overlay = translate_overlay_json(
                overlay_json, lang, brand_slug, max_chars=70, protected_names=protected_names
            )
            g_post = translate_post_text(post_text, lang, protected_names=protected_names)
            return lang, {"overlay": g_overlay, "post": g_post}, "google"
        except Exception as e2:
            _translate_logger.error(f"[TRANSLATE] {lang}: Google também falhou: {e2}")
            return lang, None, "failed"

    results: dict = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(_translate_one, lang): lang for lang in target_languages}
        for future in as_completed(futures):
            lang = futures[future]
            try:
                r_lang, r_data, r_source = future.result()
                results[r_lang] = {"data": r_data, "source": r_source} if r_data else None
            except Exception as e:
                _translate_logger.error(f"[TRANSLATE] {lang}: exceção thread: {e}")
                results[lang] = None

    return results
