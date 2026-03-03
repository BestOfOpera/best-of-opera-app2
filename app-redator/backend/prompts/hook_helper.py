from backend.config import HOOK_CATEGORIES


def build_hook_text(project) -> str:
    """Monta o texto do hook combinando categoria + complemento do usuário."""
    cat_key = getattr(project, "hook_category", "") or ""
    hook = getattr(project, "hook", "") or ""

    if cat_key and cat_key != "prefiro_escrever" and cat_key in HOOK_CATEGORIES:
        cat = HOOK_CATEGORIES[cat_key]
        text = f"[Categoria: {cat['label']}] {cat['prompt']}"
        if hook.strip():
            text += f" Complemento do usuário: {hook.strip()}"
        return text

    return hook


def detect_hook_language(project) -> str:
    """Detect the target output language based on the hook text.

    Predefined categories are always in Portuguese. For custom hooks
    ("prefiro_escrever"), uses simple word-frequency heuristic.
    """
    cat_key = getattr(project, "hook_category", "") or ""

    # Predefined categories are always in Portuguese
    if cat_key and cat_key != "prefiro_escrever" and cat_key in HOOK_CATEGORIES:
        return "português"

    hook = getattr(project, "hook", "") or ""
    if not hook.strip():
        return "português"

    # Pad text for whole-word boundary matching
    text = f" {hook.lower()} "

    lang_markers = {
        "English": [" the ", " this ", " how ", " what ", " she ", " he ",
                    " was ", " is ", " and ", " that ", " with ", " for "],
        "Deutsch": [" der ", " die ", " das ", " und ", " ist ", " ein ",
                    " eine ", " wie ", " auf ", " mit ", " sich ", " auch "],
        "italiano": [" il ", " che ", " una ", " della ", " nel ", " questo ",
                     " sono ", " questa ", " nella ", " degli "],
        "français": [" le ", " les ", " des ", " une ", " est ", " dans ",
                     " cette ", " qui ", " avec ", " pour "],
        "español": [" el ", " los ", " las ", " una ", " esta ", " como ",
                    " por ", " con ", " más ", " pero "],
        "polski": [" jest ", " nie ", " jak ", " ten ", " przez ", " się ",
                   " oraz ", " jako ", " ale "],
        "português": [" do ", " da ", " ao ", " não ", " uma ", " nas ",
                      " nos ", " pela ", " pelo ", " também "],
    }

    scores = {}
    for lang, markers in lang_markers.items():
        scores[lang] = sum(1 for m in markers if m in text)

    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best

    return "português"


def build_language_reinforcement(project) -> str:
    """Build language reinforcement text to append at the end of prompts."""
    lang = detect_hook_language(project)
    if lang == "português":
        return (
            "\n\nATENÇÃO FINAL: Todo o texto acima deve estar 100% em português. "
            "A última frase, assim como todas as outras, "
            "deve estar obrigatoriamente em português."
        )
    return (
        f"\n\nATENÇÃO FINAL: Todo o texto acima deve estar 100% em {lang}. "
        f"A última frase, assim como todas as outras, "
        f"deve estar obrigatoriamente em {lang}. "
        "Não finalize em português."
    )
