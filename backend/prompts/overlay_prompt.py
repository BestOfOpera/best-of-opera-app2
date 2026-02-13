def build_overlay_prompt(project) -> str:
    duration_info = ""
    if project.cut_start and project.cut_end:
        duration_info = f"The video clip runs from {project.cut_start} to {project.cut_end}."
    elif project.original_duration:
        duration_info = f"The video duration is {project.original_duration}."

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
1. Each subtitle must be SHORT — maximum 8 words per line, ideally 4-6 words.
2. Create 6-12 subtitle entries depending on video duration.
3. Subtitles should tell a mini-story: hook the viewer, build intrigue, deliver emotional payoff.
4. First subtitle should be an attention-grabbing hook.
5. Use simple, powerful language. No jargon.
6. Timestamps should be evenly spaced across the video duration.

Return ONLY a JSON array with objects having "timestamp" (in "MM:SS" format) and "text" fields.
Example: [{{"timestamp": "00:00", "text": "This voice changed everything"}}, {{"timestamp": "00:05", "text": "Maria Callas in 1958"}}]

Return the JSON array and nothing else."""


def build_overlay_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_overlay_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER:
{custom_prompt}"""
