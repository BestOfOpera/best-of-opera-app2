from backend.prompts.hook_helper import build_hook_text, build_language_reinforcement


def _field(label: str, value) -> str:
    """Return '- Label: value' if value is non-empty, else empty string."""
    v = str(value).strip() if value else ""
    if not v:
        return ""
    return f"- {label}: {v}\n"


def _calc_subtitle_count(project, interval_secs: int = 15) -> str:
    """Calculate approximate number of subtitles based on cut duration."""
    try:
        if project.cut_start and project.cut_end:
            start_parts = project.cut_start.split(":")
            end_parts = project.cut_end.split(":")
            start_secs = int(start_parts[0]) * 60 + int(start_parts[1])
            end_secs = int(end_parts[0]) * 60 + int(end_parts[1])
            duration_secs = end_secs - start_secs
        elif project.original_duration:
            parts = project.original_duration.split(":")
            duration_secs = int(parts[0]) * 60 + int(parts[1])
        else:
            return "Create approximately 4-6 subtitle entries. Use the interval as a flexible guide — cluster subtitles around context-rich moments and space them out during purely musical passages."

        # -1 para reservar espaço para o CTA (injetado automaticamente pelo sistema)
        count = max(3, round(duration_secs / interval_secs) - 1)
        min_count = max(3, count - 2)
        max_count = count + 2
        return (
            f"The video is {duration_secs} seconds long. "
            f"Target around {count} NARRATIVE subtitle entries ({min_count}-{max_count} is acceptable). "
            f"The system will add a CTA after your last subtitle, so leave ~15 seconds of space at the end. "
            f"Your last subtitle should appear no later than {duration_secs - 15} seconds into the video."
        )
    except (ValueError, IndexError):
        return "Create approximately 4-6 subtitle entries with consistent spacing of 6 seconds between each subtitle."


def _build_overlay_fields(project) -> str:
    """Monta os campos de input do projeto para overlay."""
    return (
        f"{_field('Artist', project.artist)}"
        f"{_field('Work', project.work)}"
        f"{_field('Composer', project.composer)}"
        f"{_field('Category', project.category)}"
        f"{_field('Hook/angle', build_hook_text(project))}"
        f"{_field('Highlights', project.highlights)}"
        f"{_field('Composition year', project.composition_year)}"
        f"{_field('Nationality', project.nationality)}"
        f"{_field('Voice type', project.voice_type)}"
    )


def build_overlay_prompt(project, brand_config=None) -> str:
    bc = brand_config or {}
    brand_name = bc.get("brand_name", "")
    max_chars = bc.get("overlay_max_chars", 70)
    max_chars_line = bc.get("overlay_max_chars_linha", 35)
    interval_secs = bc.get("overlay_interval_secs", 6)
    opening_line = bc.get("brand_opening_line", "")
    identity = bc.get("identity_prompt_redator", "")
    tom_de_voz = bc.get("tom_de_voz_redator", "")
    escopo = bc.get("escopo_conteudo", "")

    duration_info = ""
    if project.cut_start and project.cut_end:
        duration_info = f"The video clip runs from {project.cut_start} to {project.cut_end}."
    elif project.original_duration:
        duration_info = f"The video duration is {project.original_duration}."

    count_info = _calc_subtitle_count(project, interval_secs=interval_secs)
    fields = _build_overlay_fields(project)

    brand_block_parts = []
    if identity:
        brand_block_parts.append(f"**Brand Identity:** {identity}")
    if tom_de_voz:
        brand_block_parts.append(f"**Tone of Voice:** {tom_de_voz}")
    if escopo:
        brand_block_parts.append(f"**Content Scope:** {escopo}")

    brand_block = ""
    if brand_block_parts:
        brand_block = f"""
═══════════════════════════════
BRAND INSTRUCTIONS (follow these as PRIMARY rules)
═══════════════════════════════
{chr(10).join(brand_block_parts)}
"""

    return f"""You are a master storyteller and viral content writer for "{brand_name}"{f' — {opening_line}' if opening_line else ''}.

Your subtitles are the difference between someone scrolling past and someone watching until the end, saving the video, and following the channel.

Generate overlay subtitles for a video featuring:
{fields}{duration_info}
Only use information that was provided above. Do not reference or invent data for fields that were not listed.
{brand_block}
═══════════════════════════════
TECHNICAL RULES
═══════════════════════════════

1. Maximum {max_chars} characters per subtitle.
2. {count_info} Cover the ENTIRE video — no long gaps without text on screen. LAST subtitle must reach close to the video's end.
3. FIRST subtitle starts at "00:00".
4. OVERLAY FORMATTING:
   - Maximum {max_chars} characters in total per subtitle.
   - If a subtitle has more than {max_chars_line} characters, split it into 2 lines using \\n.
   - Each line: maximum {max_chars_line} characters.
   - The 2 lines must be BALANCED in length (maximum 30% difference between them).
5. WORD SPACING — CRITICAL: Every word MUST be separated by exactly one space character. NEVER concatenate two words without a space. Do NOT use newline characters (\\n) as word separators — use them ONLY for intentional line breaks.
   WRONG: "nuncasetocam" / "harmoniaé" / "comoum"
   CORRECT: "nunca se tocam" / "harmonia é" / "como um"
6. Follow ALL instructions from the Brand Identity, Tone of Voice, and Content Scope sections above for narrative arc, hook style, forbidden phrases, and writing rules.
7. Do NOT generate a CTA (call-to-action) subtitle. The system adds the CTA automatically. Your LAST subtitle must be the final NARRATIVE subtitle.

═══════════════════════════════
OUTPUT FORMAT
═══════════════════════════════

Return ONLY a JSON array with objects having "timestamp" (MM:SS format) and "text" fields.
Example: [{{"timestamp": "00:00", "text": "Nobody believed she could do this"}}, {{"timestamp": "00:06", "text": "Maria Callas, live in Paris, 1958"}}]

Write ALL subtitle text in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.{build_language_reinforcement(project)}"""


def build_overlay_prompt_with_custom(project, custom_prompt: str, brand_config=None) -> str:
    base = build_overlay_prompt(project, brand_config=brand_config)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}{build_language_reinforcement(project)}"""
