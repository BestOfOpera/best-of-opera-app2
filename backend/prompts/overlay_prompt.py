def _calc_subtitle_count(project) -> str:
    """Calculate approximate number of subtitles based on cut duration (~1 every 15s)."""
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
            return "Create approximately 4-6 subtitle entries."

        count = max(3, round(duration_secs / 15))
        return f"The video is {duration_secs} seconds long. Create approximately {count} subtitle entries (averaging ~1 every 15 seconds)."
    except (ValueError, IndexError):
        return "Create approximately 4-6 subtitle entries."


def build_overlay_prompt(project) -> str:
    duration_info = ""
    if project.cut_start and project.cut_end:
        duration_info = f"The video clip runs from {project.cut_start} to {project.cut_end}."
    elif project.original_duration:
        duration_info = f"The video duration is {project.original_duration}."

    count_info = _calc_subtitle_count(project)

    return f"""You are a creative copywriter for "Best of Opera", a social media channel that shares short clips of opera performances.

Generate overlay subtitles (captions that appear on screen) for a video featuring:
- Artist: {project.artist}
- Work: {project.work}
- Composer: {project.composer}
- Category: {project.category}
- Hook/angle: {project.hook}
- Highlights: {project.highlights}
- Composition year: {project.composition_year}
- Nationality: {project.nationality}
- Voice type: {project.voice_type}
{duration_info}

RULES:
1. Each subtitle must be maximum 70 characters.
2. {count_info} The spacing does NOT need to be uniform — the first subtitle can appear quickly to grab attention, then subsequent ones can be more spread out. Use your judgment for dramatic pacing.
3. Subtitles should tell a mini-story: hook the viewer, build intrigue, deliver emotional payoff.
4. First subtitle MUST be a short, punchy attention-grabbing hook (ideally under 30 characters).
5. Use simple, powerful language.
6. NEVER use generic phrases like "beautiful performance", "amazing voice", "stunning rendition", "incredible talent". Be SPECIFIC and evocative.
7. NEVER use technical opera jargon (no "bel canto", "coloratura", "tessitura", "libretto", etc). Write for a general audience.
8. Timestamps should be distributed across the video duration with natural dramatic pacing.

Return ONLY a JSON array with objects having "timestamp" (in "MM:SS" format) and "text" fields.
Example: [{{"timestamp": "00:00", "text": "This voice changed everything"}}, {{"timestamp": "00:05", "text": "Maria Callas in 1958"}}]

Write ALL subtitle text in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.

Return the JSON array and nothing else."""


def build_overlay_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_overlay_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}"""
