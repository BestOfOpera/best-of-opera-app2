from backend.prompts.hook_helper import build_hook_text


def build_post_prompt(project) -> str:
    flag = project.nationality_flag or ""

    return f"""You are a creative copywriter for "Best of Opera", a social media channel. Write an Instagram/Facebook post for a video clip featuring:

- Artist: {project.artist}
- Work: {project.work}
- Composer: {project.composer}
- Category: {project.category}
- Hook/angle: {build_hook_text(project)}
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

SECTION 2 — STORYTELLING (3-5 rich paragraphs)
The heart of the post. Tell a compelling, DETAILED mini-story about this performance/artist.
Use strategic emojis at the start of some paragraphs to add visual rhythm.
This is the ONLY section that will be translated to other languages.
Keep it emotional, vivid, and accessible to non-opera fans.
This section should be the BULK of the post — aim for 1000-1200 characters in this section alone.
Include historical context, emotional details, what makes this performance unique, and vivid sensory descriptions.

SECTION 3 — CREDITS (exact format below, line by line)
For EACH artist/performer (if multiple artists separated by " & ", create a credit block for EACH one):
[Fun emoji] [Artist Full Name] [their flag emoji]
Voice type: [their voice type]
Date of Birth: [their birth date in dd/mm/yyyy format]

Then the work credits:
[Fun emoji] [Work Name] — [Album or Opera name]
Composer: [Composer name]
Composition date: [composition year]

EXAMPLE for a single artist:
🎤 Maria Callas 🇬🇷
Voice type: Soprano
Date of Birth: 02/12/1923

🎼 Casta Diva — Norma
Composer: Vincenzo Bellini
Composition date: 1831

EXAMPLE for a duet (TWO artist blocks + work block):
🎤 Nicolai Gedda 🇸🇪
Voice type: Tenor
Date of Birth: 11/07/1925

🎤 Mirella Freni 🇮🇹
Voice type: Soprano
Date of Birth: 27/02/1935

🎼 Là ci darem la mano — Don Giovanni
Composer: Wolfgang Amadeus Mozart
Composition date: 1787

SECTION 4 — SENSORY CTA (1-2 lines)
A sensory call-to-action using contrasting emojis.
Example: "Does this give you 🔥 or ❄️? Tell us below!"

SECTION 5 — HASHTAGS (exactly 1 line)
Exactly 4 hashtags. Always include #BestOfOpera. Add 3 more relevant ones.
Example: "#BestOfOpera #MariaCallas #Opera #CastaDiva"

CRITICAL RULES:
- The TOTAL post text MUST be between 1600 and 1800 characters. This is NON-NEGOTIABLE. Count your characters carefully. If the text is under 1600, expand the storytelling section with more vivid details. If over 1800, trim.
- Each section must be separated by a blank line.
- Section 3 credits must use the EXACT format shown above (with "Voice type:", "Date of Birth:", "Composer:", "Composition date:" labels in English).
- Write ALL content in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.
- Section 3 credit labels (Voice type, Date of Birth, Composer, Composition date) must always be in English regardless of hook language, as they will be translated separately.
- Return ONLY the post text, no explanations or commentary."""


def build_post_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_post_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}"""
