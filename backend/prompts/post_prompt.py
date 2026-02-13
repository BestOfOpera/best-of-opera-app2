def build_post_prompt(project) -> str:
    flag = project.nationality_flag or ""

    return f"""You are a creative copywriter for "Best of Opera", a social media channel. Write an Instagram/Facebook post for a video clip featuring:

- Artist: {project.artist}
- Work: {project.work}
- Composer: {project.composer}
- Category: {project.category}
- Hook/angle: {project.hook}
- Highlights: {project.highlights}
- Composition year: {project.composition_year}
- Nationality: {project.nationality}
- Nationality flag emoji: {flag}
- Voice type: {project.voice_type}
- Birth date: {project.birth_date}
- Death date: {project.death_date}
- Album/Opera: {project.album_opera}

The post MUST follow this EXACT 5-section structure with blank lines separating each section:

SECTION 1 — OPENING (exactly 1 line)
[Fun/playful emoji] [Artist Name] — [Work Name]
Example: "🎭 Maria Callas — Casta Diva"

SECTION 2 — STORYTELLING (2-4 short paragraphs)
The heart of the post. Tell a compelling mini-story about this performance/artist.
Use strategic emojis at the start of some paragraphs to add visual rhythm.
This is the ONLY section that will be translated to other languages.
Keep it emotional, vivid, and accessible to non-opera fans.

SECTION 3 — CREDITS (exact format below, line by line)
[Fun emoji] [Artist Full Name] {flag}
Tipo de voz: [voice type]
Nascimento: [birth date in dd/mm/yyyy format]

[Fun emoji] [Work Name] — [Album or Opera name]
Compositor: [Composer name]
Data da composição: [composition year]

SECTION 4 — SENSORY CTA (1-2 lines)
A sensory call-to-action using contrasting emojis.
Example: "Does this give you 🔥 or ❄️? Tell us below!"

SECTION 5 — HASHTAGS (exactly 1 line)
Exactly 4 hashtags. Always include #BestOfOpera. Add 3 more relevant ones.
Example: "#BestOfOpera #MariaCallas #Opera #CastaDiva"

CRITICAL RULES:
- The TOTAL post text must be between 1600 and 1800 characters.
- Each section must be separated by a blank line.
- Section 3 credits must use the EXACT format shown above (with "Tipo de voz:", "Nascimento:", "Compositor:", "Data da composição:" labels).
- Return ONLY the post text, no explanations or commentary."""


def build_post_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_post_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER:
{custom_prompt}"""
