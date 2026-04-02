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
🎶 [Work Name] — [Artist Name(s)]

The emoji 🎶 is FIXED. The em dash (—) separates Work from Artist. This is the ONLY place where the em dash (—) is allowed in the entire post.
Example: "🎶 Nessun dorma — Luciano Pavarotti"

──────────────────────
SECTION 2 — STORYTELLING (3–5 paragraphs)
──────────────────────
This is the soul of the post. It's the only section that will be translated to other languages.

TARGET: 1000–1200 characters in this section alone. 4–6 sentences per paragraph, grounded in verifiable facts.

Your mission: make someone who has never paid attention to this kind of music feel like they just discovered something rare and precious. Write like someone telling a story, NOT like Instagram copy.

NARRATIVE ARC to follow:
→ Paragraph 1: Drop the reader into a scene or a tension. Don't introduce. IMMERSE.
→ Paragraph 2: Build the backstory. Who is this person? What was at stake? What did the world not know yet?
→ Paragraph 3: The turning point. The moment this performance or this voice became something else entirely.
→ Paragraph 4: The emotional truth. What does this music ACTUALLY feel like? What does it do to a listener?
→ Paragraph 5 (optional): The legacy, the mystery, or the open question that lingers.

EMOJI RULE: EVERY paragraph MUST begin with a themed emoji that is DIFFERENT from all other paragraphs. Choose from: 🔍 🕊️ 🎭 🌟 🎬 ✝️ 🗝️ 🌍 ✨ 🎪 🏛️ 💫 🌊 🕯️. Each emoji may appear only ONCE in the entire post.

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

FORBIDDEN WORDS AND PHRASES — never write any of these:
"beautiful performance", "amazing voice", "stunning rendition", "incredible talent",
"breathtaking", "timeless masterpiece", "legendary performance", "moved to tears",
"one of the greatest", "truly remarkable", "unforgettable experience",
"dive into", "journey", "uncover", "fascinating", "spectacular",
"iconic" (as empty adjective), "timeless" (as empty adjective),
"incredible", "legendary", "unforgettable", "masterpiece" (without a concrete fact backing it).
These are empty. Replace them with a SPECIFIC detail that earns the emotion.

FORBIDDEN PUNCTUATION in Section 2: The em dash (—) is PROHIBITED in storytelling paragraphs. Use periods, commas, colons, or semicolons instead. The em dash is reserved exclusively for the Section 1 header.

FORBIDDEN PATTERN: Generic sentences that could apply to any video. Every sentence must be specific to THIS artist, THIS work, THIS moment.

──────────────────────
SECTION 3 — CREDITS (exact format below)
──────────────────────
CRITICAL RULE: Only include a credit line if the data was provided in the input above OR if you can determine it with certainty from the artist/work/composer names. If you cannot determine a field with confidence, OMIT that line entirely. Never show a label with an empty value, a placeholder, or "unknown". Just skip the line.

Credit labels MUST be in the SAME LANGUAGE as the rest of the post (matching the Hook/angle language).

ARTIST BLOCK(S) — create one 🎤 block for EACH performer:
If the input contains multiple artists (separated by " & " or similar), create a SEPARATE 🎤 block for each one with their individual details. If the video features both a soloist AND an ensemble/choir, create blocks for both.

For a solo artist:
🎤 [Artist Full Name] [country flag emoji]
Nationality: [Country name]           ← include if known from input or inferable from artist name
Voice type: [voice classification]     ← only if voice type was provided
Date of Birth: [DD/MM/YYYY]           ← only if birth date was provided
Date of Death: [DD/MM/YYYY]           ← ONLY if the artist is deceased AND death date was provided

For a choir or ensemble:
🎤 [Ensemble Name] [country flag emoji]
Type: [Mixed choir / Chamber ensemble / etc.]
Artistic Director: [Name]             ← only if known

WORK BLOCK — exactly one 🎼 block:
🎼 [Work Name]
From: [Opera or larger work name]     ← ONLY if this is an excerpt from a larger work (aria from opera, movement from requiem, etc.). Omit if the work is standalone.
Composer: [Composer name] [country flag emoji]   ← include flag if inferable from composer name
Composition date: [Year or c. Year]   ← only if composition year was provided
Libretto/Text: [Librettist name or text source]  ← include if inferable from the opera/work (e.g., "Piave" for La Traviata, "Da Ponte" for Don Giovanni). Omit if unknown.
Original language: [Language]         ← include if inferable from the work (e.g., Italian for Verdi, German for Wagner). Omit if uncertain.

Portuguese labels: Nacionalidade, Tipo de voz, Data de nascimento, Data de falecimento, Tipo, Diretor artístico, De, Compositor, Data de composição, Libreto/Texto, Idioma original.

──────────────────────
SECTION 4 — ENGAGEMENT QUESTION (1 line)
──────────────────────
Write a thought-provoking question naturally connected to the story you just told. It should feel like the final thought of a conversation, not a marketing prompt. End with a single emoji.

Good examples:
"What do you hear in her silence that most covers miss? 🕯️"
"How does it feel knowing this voice no longer exists? 🎙️"
"Which surprises you more: how the melody was born or how the Oscar was won? 🎬"

Bad examples (too generic):
"What do you think? 🤔"
"Does this give you chills? 🔥"

──────────────────────
SECTION 5 — HASHTAGS (exactly 1 line)
──────────────────────
Exactly {hashtag_count} hashtags. #BestOfOpera MUST be first. Format: #BestOfOpera #[VoiceType] #[Composer] #[RelevantTopic].{" You MUST also include: " + hashtags_str + "." if len(hashtags) > 1 else ""}{" Add " + str(hashtag_count - len(hashtags)) + " more relevant ones." if len(hashtags) < hashtag_count else ""}
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
- Section 1 header: 🎶 emoji is FIXED, order is Work — Artist. The em dash (—) is ONLY allowed here.
- Section 2 paragraphs: EVERY paragraph starts with a UNIQUE themed emoji. No em dashes (—) anywhere in the storytelling.
- Section 3 credits: use EXACTLY the format specified (🎤 for artists, 🎼 for work). Labels in the SAME LANGUAGE as the post. Portuguese post → Portuguese labels. English post → English labels.
- Section 3 inferable fields: For Nationality, Composer flag, Libretto/Text, and Original language, you MAY infer the value from well-known facts about the artist or work. Only include if you are confident. If uncertain, omit the line.
- MISSING DATA: If any field was NOT provided in the input AND you cannot infer it with confidence, do NOT include it. Do not invent data, use placeholders, or leave labels empty. In Section 2, do not reference missing information. In Section 3, omit the entire line. The post must read naturally with only the available information.
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
