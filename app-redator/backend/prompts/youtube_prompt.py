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
    return "\n\n═══════════════════════════════\nBRAND CUSTOMIZATION\n═══════════════════════════════\n" + "\n".join(parts) + "\n"


def build_youtube_prompt(project, brand_config=None) -> str:
    brand_name = (brand_config or {}).get("brand_name", "Best of Opera")
    fields = ""
    fields += _field("Artist", project.artist)
    fields += _field("Work", project.work)
    fields += _field("Composer", project.composer)
    fields += _field("Category", project.category)
    fields += _field("Hook/angle", build_hook_text(project))
    fields += _field("Voice type", project.voice_type)
    fields = fields.rstrip("\n")

    return f"""You are a YouTube SEO expert for "{brand_name}", a channel sharing short opera clips.

Generate a YouTube title and tags for a video featuring:
{fields}

TITLE RULES:
1. Maximum 100 characters
2. Must include the artist name and work/composer
3. Should be compelling and searchable
4. Use power words that drive clicks
5. Format: "[Hook/Emotional angle] — [Artist] in [Work] by [Composer]" or similar

TAGS RULES:
1. Comma-separated tags
2. The TOTAL tags string must be under 450 characters
3. Mix of broad (opera, classical music) and specific (artist name, work name)
4. Include common misspellings of artist/composer names if applicable
5. Include genre tags, era tags, and voice type tags
6. Pack as many relevant tags as possible within the 450-character limit

Return EXACTLY two lines:
Line 1: The title
Line 2: The tags (comma-separated)

Write the title and tags in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.
Only use information that was provided above. If a field (composer, voice type, etc.) was not listed, do not include it in the title or tags.

Nothing else.
{_brand_block(brand_config or {})}{build_language_reinforcement(project)}"""


def build_youtube_prompt_with_custom(project, custom_prompt: str, brand_config=None) -> str:
    base = build_youtube_prompt(project, brand_config=brand_config)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}{build_language_reinforcement(project)}"""
