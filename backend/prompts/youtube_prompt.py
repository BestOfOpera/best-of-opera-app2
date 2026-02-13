def build_youtube_prompt(project) -> str:
    return f"""You are a YouTube SEO expert for "Best of Opera", a channel sharing short opera clips.

Generate a YouTube title and tags for a video featuring:
- Artist: {project.artist}
- Work: {project.work}
- Composer: {project.composer}
- Category: {project.category}
- Hook/angle: {project.hook}
- Voice type: {project.voice_type}

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

Nothing else."""


def build_youtube_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_youtube_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER:
{custom_prompt}"""
