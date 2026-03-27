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


def _default_structure(hashtags, hashtags_str, hashtag_count: int = 4) -> str:
    """Estrutura padrão de 5 seções — usada quando custom_post_structure está vazio."""
    return f"""
═══════════════════════════════
POST STRUCTURE (5 sections, separated by blank lines)
═══════════════════════════════

──────────────────────
SECTION 1 — OPENING (exactly 1 line)
──────────────────────
[Fun/playful emoji] [Artist Name] — [Work Name]
Example: "🎭 Maria Callas — Casta Diva"

──────────────────────
SECTION 2 — STORYTELLING (3–5 paragraphs)
──────────────────────
This is the soul of the post. It's the only section that will be translated to other languages.

TARGET: 1000–1200 characters in this section alone.

Your mission: make someone who has never watched opera in their life feel like they just discovered something rare and precious.

NARRATIVE ARC to follow:
→ Paragraph 1: Drop the reader into a scene or a tension. Don't introduce — IMMERSE.
→ Paragraph 2: Build the backstory. Who is this person? What was at stake? What did the world not know yet?
→ Paragraph 3: The turning point. The moment this performance or this voice became something else entirely.
→ Paragraph 4: The emotional truth. What does this music ACTUALLY feel like? What does it do to a listener?
→ Paragraph 5 (optional): The legacy, the mystery, or the open question that lingers.

WRITING PRINCIPLES:

**Write in scenes, not summaries.**
Bad: "This was an emotional performance recorded in 1965."
Good: "The recording booth was freezing. She asked for one more take. What happened next has never been explained."

**Use contrast to create electricity.**
Bad: "Critics were divided about her style."
Good: "Half the audience walked out. The other half gave her a 10-minute standing ovation."

**Make the reader feel the sound without hearing it.**
Bad: "Her voice was powerful and moving."
Good: "There's a note around the 1:40 mark that sounds like something breaking open."

**Anchor emotion in specific, physical detail.**
Bad: "This aria is about loss."
Good: "He wrote this the year his daughter died. You can hear it in every bar."

**Use strategic emojis** at the start of some paragraphs (not every one) to create visual breathing room and rhythm.

FORBIDDEN — never write these phrases:
"beautiful performance", "amazing voice", "stunning rendition", "incredible talent",
"breathtaking", "timeless masterpiece", "legendary performance", "moved to tears",
"one of the greatest", "truly remarkable", "unforgettable experience".
These are empty. Replace them with a SPECIFIC detail that earns the emotion.

──────────────────────
SECTION 3 — CREDITS (exact format, labels in the SAME LANGUAGE as the post)
──────────────────────
CRITICAL RULE: Only include a credit line if the data was provided in the input above. If a field (voice type, birth date, death date, composer, composition year, album/opera) was NOT listed in the input or is empty, OMIT that line entirely. Never show a label with an empty value, a placeholder, or "unknown". Just skip the line.

For EACH artist (if multiple artists separated by " & ", create a block for EACH):

If post is in Portuguese:
[Fun emoji] [Artist Full Name] [flag emoji]
Tipo de voz: [voice type]          ← only if voice type was provided
Data de nascimento: [dd/mm/yyyy]   ← only if birth date was provided

Then the work:
[Fun emoji] [Work Name] — [Album or Opera name]   ← omit " — [Album or Opera name]" if not provided
Compositor: [Composer name]        ← only if composer was provided
Data de composição: [year]         ← only if composition year was provided

If post is in English:
[Fun emoji] [Artist Full Name] [flag emoji]
Voice type: [voice type]           ← only if voice type was provided
Date of Birth: [dd/mm/yyyy]       ← only if birth date was provided

Then the work:
[Fun emoji] [Work Name] — [Album or Opera name]   ← omit " — [Album or Opera name]" if not provided
Composer: [Composer name]          ← only if composer was provided
Composition date: [year]           ← only if composition year was provided

EXAMPLE — single artist (Portuguese post):
🎤 Maria Callas 🇬🇷
Tipo de voz: Soprano
Data de nascimento: 02/12/1923

🎼 Casta Diva — Norma
Compositor: Vincenzo Bellini
Data de composição: 1831

──────────────────────
SECTION 4 — SENSORY CTA (1–2 lines)
──────────────────────
A short, playful call-to-action using contrasting emojis that invites the audience to react.
Example: "Does this give you 🔥 or ❄️? Tell us below!"

──────────────────────
SECTION 5 — HASHTAGS (exactly 1 line)
──────────────────────
Exactly {hashtag_count} hashtags. You MUST include ALL of these: {hashtags_str}.{"" if len(hashtags) >= hashtag_count else f" Add {hashtag_count - len(hashtags)} more relevant ones."}
"""


def _custom_structure(custom_post_structure: str) -> str:
    """Estrutura customizada definida pelo perfil da marca."""
    return f"""
═══════════════════════════════
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
    hashtags = bc.get("hashtags_fixas", [])
    hashtag_count = bc.get("hashtag_count", 4)
    fields = _build_fields(project)

    # 1. Brand prompts — sempre primeiro como instrução principal
    brand_block = _brand_block(bc)

    # 2. Estrutura do post:
    #    - custom_post_structure preenchido → usa ele (pula estrutura padrão)
    #    - vazio → injeta estrutura padrão de 5 seções
    if custom_post:
        structure = _custom_structure(custom_post)
    else:
        hashtags_str = " ".join(hashtags)
        structure = _default_structure(hashtags, hashtags_str, hashtag_count=hashtag_count)

    # 3. Critical rules — genéricas quando tem custom, completas com estrutura padrão
    if custom_post:
        critical_rules = """═══════════════════════════════
CRITICAL RULES
═══════════════════════════════

- MISSING DATA: If any field was NOT provided in the input, do NOT include it anywhere in the post. Do not invent data, use placeholders, or leave labels empty. The post must read naturally with only the available information.
- Write ALL content in the SAME LANGUAGE as the Hook/angle field.
- Return ONLY the post text. No explanations, no commentary, no preamble.
- Follow ALL instructions from the Brand Identity, Tone of Voice, and Content Scope sections above. They define the structure, formatting, character limits, and rules for this brand."""
    else:
        critical_rules = """═══════════════════════════════
CRITICAL RULES
═══════════════════════════════

- TOTAL post: 1600–1800 characters. NON-NEGOTIABLE. Count carefully. Under 1600? Deepen the story with another specific detail or scene. Over 1800? Cut adjectives and summaries, never cut specificity.
- Blank line between every section.
- Section 3 credit labels MUST be in the SAME LANGUAGE as the rest of the post (matching the Hook/angle language). Portuguese post → Portuguese labels (Tipo de voz, Data de nascimento, Compositor, Data de composição). English post → English labels (Voice type, Date of Birth, Composer, Composition date).
- MISSING DATA: If any field was NOT provided in the input, do NOT include it anywhere in the post. Do not invent data, use placeholders, or leave labels empty. In Section 2 storytelling, do not write sentences that reference missing information. In Section 3 credits, omit the entire line. The post must read naturally with only the available information.
- Write ALL content in the SAME LANGUAGE as the Hook/angle field.
- Return ONLY the post text. No explanations, no commentary, no preamble."""

    return f"""You are a world-class storyteller who writes viral social media content for "{brand_name}"{f' — {opening_line}' if opening_line else ''}.

Your posts don't describe performances. They make people FEEL something they didn't expect to feel today.

The reader is scrolling fast. You have 3 lines to stop them. Then you have one job: make them read every single word until the end.

Write an Instagram/Facebook post for a video clip featuring:
{fields}

{brand_block}{structure}
{critical_rules}
{build_language_reinforcement(project)}"""


def build_post_prompt_with_custom(project, custom_prompt: str, brand_config=None) -> str:
    base = build_post_prompt(project, brand_config=brand_config)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}{build_language_reinforcement(project)}"""
