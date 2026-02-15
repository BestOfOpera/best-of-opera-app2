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
