from backend.prompts.hook_helper import build_hook_text, build_language_reinforcement


def _field(label: str, value) -> str:
    """Return '- Label: value' if value is non-empty, else empty string."""
    v = str(value).strip() if value else ""
    if not v:
        return ""
    return f"- {label}: {v}\n"


def _brand_block(brand_config: dict) -> str:
    parts = []
    identity = brand_config.get("identity_prompt_redator", "")
    tom = brand_config.get("tom_de_voz_redator", "")
    escopo = brand_config.get("escopo_conteudo", "")
    if identity:
        parts.append(f"**Brand Identity:** {identity}")
    if tom:
        parts.append(f"**Tone of Voice:** {tom}")
    if escopo:
        parts.append(f"**Content Scope:** {escopo}")
    if not parts:
        return ""
    return "\n\n═══════════════════════════════\nBRAND INSTRUCTIONS (follow these as PRIMARY rules)\n═══════════════════════════════\n" + "\n".join(parts) + "\n"


def _custom_structure(custom_post_structure: str) -> str:
    """Estrutura customizada definida pelo perfil da marca."""
    return f"""═══════════════════════════════
POST STRUCTURE (brand-specific)
═══════════════════════════════

{custom_post_structure}
"""


def _build_fields(project) -> str:
    """Monta os campos de input do projeto."""
    fields = ""
    fields += _field("Artist", project.artist)
    fields += _field("Work", project.work)
    fields += _field("Composer", project.composer)
    fields += _field("Category", project.category)
    fields += _field("Hook/angle", build_hook_text(project))
    fields += _field("Highlights", project.highlights)
    fields += _field("Composition year", project.composition_year)
    fields += _field("Nationality", project.nationality)
    fields += _field("Nationality flag emoji", project.nationality_flag or "")
    fields += _field("Voice type", project.voice_type)
    fields += _field("Birth date", project.birth_date)
    fields += _field("Death date", project.death_date)
    fields += _field("Album/Opera", project.album_opera)
    return fields.rstrip("\n")


def build_post_prompt(project, brand_config=None) -> str:
    bc = brand_config or {}
    brand_name = bc.get("brand_name", "")
    opening_line = bc.get("brand_opening_line", "")
    custom_post = bc.get("custom_post_structure", "")
    fields = _build_fields(project)
    brand_block = _brand_block(bc)

    structure_section = ""
    if custom_post:
        structure_section = _custom_structure(custom_post)

    return f"""You are a world-class storyteller who writes viral social media content for "{brand_name}"{f' — {opening_line}' if opening_line else ''}.

Your posts don't describe performances. They make people FEEL something they didn't expect to feel today.

The reader is scrolling fast. You have 3 lines to stop them. Then you have one job: make them read every single word until the end.

Write an Instagram/Facebook post for a video clip featuring:
{fields}

{brand_block}{structure_section}═══════════════════════════════
CRITICAL RULES
═══════════════════════════════

- MISSING DATA: If any field was NOT provided in the input, do NOT include it anywhere in the post. Do not invent data, use placeholders, or leave labels empty. The post must read naturally with only the available information.
- Write ALL content in the SAME LANGUAGE as the Hook/angle field.
- Return ONLY the post text. No explanations, no commentary, no preamble.
- Follow ALL instructions from the Brand Identity, Tone of Voice, and Content Scope sections above. They define the structure, formatting, character limits, and rules for this brand.
{build_language_reinforcement(project)}"""


def build_post_prompt_with_custom(project, custom_prompt: str, brand_config=None) -> str:
    base = build_post_prompt(project, brand_config=brand_config)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}{build_language_reinforcement(project)}"""
