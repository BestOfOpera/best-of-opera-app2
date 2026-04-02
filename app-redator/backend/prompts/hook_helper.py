from backend.config import HOOK_CATEGORIES


def build_hook_text(project, brand_config=None) -> str:
    """Monta o texto do hook combinando categoria + complemento do usuário.

    Prioridade:
    1. Se project.hook contém um hook concreto (gerado por LLM ou escrito pelo usuário),
       retorna o texto direto — é o valor usado como Hook/angle no overlay prompt.
    2. Se project.hook está vazio e hook_category é uma categoria pré-definida,
       monta instrução genérica da categoria (fallback para projetos sem hooks gerados).
    """
    cat_key = getattr(project, "hook_category", "") or ""
    hook = getattr(project, "hook", "") or ""

    # Se o hook contém texto concreto E não é uma categoria predefinida (ou é "prefiro_escrever"),
    # retornar direto — é um hook específico já gerado/escolhido
    if hook.strip() and (not cat_key or cat_key == "prefiro_escrever"):
        return hook.strip()

    # Se hook tem texto E categoria: hook é complemento da categoria
    # Usar categorias da marca se disponível, senão fallback global
    categories = HOOK_CATEGORIES
    if brand_config and brand_config.get("hook_categories_redator"):
        categories = brand_config["hook_categories_redator"]

    if cat_key and cat_key != "prefiro_escrever" and cat_key in categories:
        cat = categories[cat_key]
        text = f"[Categoria: {cat['label']}] {cat['prompt']}"
        if hook.strip():
            text += f" Complemento do usuario: {hook.strip()}"
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


def build_language_reinforcement(project, brand_config=None) -> str:
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
