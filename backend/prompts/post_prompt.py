def build_post_prompt(project) -> str:
    return f"""You are a creative copywriter for "Best of Opera", a social media channel. Write an Instagram/Facebook post for a video clip featuring:

- Artist: {project.artist}
- Work: {project.work}
- Composer: {project.composer}
- Category: {project.category}
- Hook/angle: {project.hook}
- Highlights: {project.highlights}
- Composition year: {project.composition_year}
- Nationality: {project.nationality}
- Voice type: {project.voice_type}
- Birth date: {project.birth_date}
- Death date: {project.death_date}
- Album/Opera: {project.album_opera}

The post MUST follow this EXACT 5-section structure:

SECTION 1 — EMOJI INTRO (1 line)
A single line with 1-2 relevant emojis + the artist name + a short descriptor.
Example: "🎭 Maria Callas — The voice that defined an era"

SECTION 2 — STORYTELLING (2-4 short paragraphs)
The heart of the post. Tell a compelling mini-story about this performance/artist.
This is the ONLY section that will be translated to other languages.
Keep it emotional, vivid, and accessible to non-opera fans.

SECTION 3 — METADATA BLOCK
Format exactly like this:
🎵 [Work name]
🎼 [Composer name] ([year])
🎤 [Artist name] ([voice type])
📀 [Album/Opera name]

SECTION 4 — CALL TO ACTION (1-2 lines)
Engage the audience. Ask a question or invite them to share.
Example: "Which Callas performance moves you the most? Tell us below 👇"

SECTION 5 — HASHTAGS (1 line)
8-12 relevant hashtags. Always include #BestOfOpera #Opera #ClassicalMusic
Add artist-specific and work-specific hashtags.

Return ONLY the post text, no explanations."""


def build_post_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_post_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER:
{custom_prompt}"""
