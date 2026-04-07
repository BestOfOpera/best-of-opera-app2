import json

from backend.prompts.hook_helper import build_hook_text, build_language_reinforcement


def _field(label: str, value) -> str:
    v = str(value).strip() if value else ""
    if not v:
        return ""
    return f"- {label}: {v}\n"


def build_hook_generation_prompt(project, brand_config=None, research_data=None) -> str:
    bc = brand_config or {}
    brand_name = bc.get("brand_name", "")
    max_chars = bc.get("overlay_max_chars", 70)

    fields = (
        f"{_field('Artist', project.artist)}"
        f"{_field('Work', project.work)}"
        f"{_field('Composer', project.composer)}"
        f"{_field('Category', project.category)}"
        f"{_field('Highlights', project.highlights)}"
        f"{_field('Composition year', project.composition_year)}"
        f"{_field('Nationality', project.nationality)}"
        f"{_field('Voice type', project.voice_type)}"
        f"{_field('Album/Opera', project.album_opera)}"
    )

    # Passar o hook_category/complemento para contexto de angulo preferido
    hook_context = build_hook_text(project, brand_config=brand_config)
    angle_block = ""
    if hook_context.strip():
        angle_block = f"""
The operator selected this angle direction:
{hook_context}

Use this as a STARTING POINT for hook #1. The other 4 hooks MUST explore DIFFERENT angles.
"""

    # Research data block (optional — BO may not have research phase)
    if research_data:
        research_block = f"""DEEP RESEARCH AVAILABLE:
{json.dumps(research_data, ensure_ascii=False, indent=2)}

Use this research as your PRIMARY source. Identify the 5-7 facts/events with the strongest emotional potential."""
    else:
        research_block = "RESEARCH: not available. Use the video data and highlights above. Identify the strongest angles from what you have."

    return f"""You are a scriptwriter for viral short-form opera and classical vocal music videos on "{brand_name}".

Your only skill that matters now: writing the FIRST PHRASE that appears on screen — the phrase that decides if the person leaves or stops scrolling.

A hook works when it triggers a PHYSICAL reaction — the thumb stops moving. This does NOT happen with trivia or data. It happens with EMOTION.

You are NOT a copywriter. You do NOT sell anything. You find the angle of a story that makes it IMPOSSIBLE not to want to know the rest.

===============================
VIDEO DATA
===============================

{fields}
{angle_block}
{research_block}

===============================
TASK — 7 mandatory steps
===============================

STEP 1 — SELECT MATERIAL
Scan all available data (video metadata, highlights, research if available).
Identify the 5-7 facts, events, or moments with the strongest emotional potential.

STEP 2 — GENERATE CANDIDATES
For each strong fact/event, formulate a hook. Generate at least 10 candidates internally.
Do NOT show the 10 — they are drafts.

STEP 3 — FEEL vs PROCESS FILTER
For each candidate ask: "Does the viewer FEEL something in 1 second, or need to PROCESS information?"

FEEL = reaction in the body (chills, curiosity, contradiction, emotional surprise)
PROCESS = reaction in the head (calculate a number, absorb trivia, understand a reference)

If PROCESS: discard or reformulate.

HOOKS THAT MAKE YOU PROCESS (eliminate):
- Numbers/statistics as the main element
- Trivia disconnected from emotion
- Verifiable superlatives with no consequence
- Technical information (opus numbers, keys, catalog numbers)

HOOKS THAT MAKE YOU FEEL (keep):
- Emotional paradox: "The most beautiful aria in opera tells the story of a murder."
- Provocation: "You know this melody. But you never knew what it really says."
- Universal connection: "If longing had a voice, it would sing exactly like this."
- Performer moment: "She sang with a 39C fever. The audience wept standing."
- Inversion: "This opera was banned because the audience laughed at the wrong moment."
- Extreme zoom: "One note. A single note separated triumph from disaster at this premiere."

STEP 4 — SPECIFICITY FILTER
"Would this hook work for ANOTHER aria/opera if I swapped names?"
If YES: too generic. Reformulate or discard.
EXCEPTION: emotional/sensory hooks may be general IF the second subtitle immediately anchors specificity.

STEP 5 — NARRATIVE THREAD CHECK
"Can I write 8+ overlay subtitles from this hook WITHOUT repeating the same point?"
If NO: dead end. Discard.
If YES: write in 1-2 sentences what the narrative thread would be.

A good thread has a CHAIN OF EVENTS. A bad hook has an ISOLATED FACT that exhausts itself in 2 subtitles.

STEP 6 — SELECT THE 5 BEST
Ensure diversity:
- At least 2 different emotional angles
- At least 1 specific to the performer or THIS performance
- No two hooks that lead to the SAME narrative thread
- At least 1 that anchors in something audible or visible in the video

STEP 7 — RANK
Order from strongest to weakest.
Criterion: "Which of these would make MORE people stop their scroll?"

===============================
CONSTRAINTS
===============================

FORBIDDEN in hook text:
- Em-dash (—)
- Numbers as the main element
- Superlatives without consequence ("the most beautiful", "the most famous")
- Empty rhetorical questions ("Have you ever heard of...?")
- Aggressive commands ("Stop everything!", "Listen now!")
- Telling the viewer what to feel ("Prepare to cry")
- Technical information (opus, catalogs, keys)
- Forbidden words: dive into, journey, uncover, fascinating, masterpiece (without concrete fact), iconic, timeless, dazzling, spectacular, masterful, breathtaking (as empty adjective)

REQUIRED:
- Maximum {max_chars} characters per hook (hard technical limit)
- Maximum 2 lines (use \\n for line break if needed)
- Each hook understandable by someone who has NEVER heard opera
- Each hook MUST have a viable narrative thread of 8+ subtitles

===============================
OUTPUT FORMAT
===============================

Return ONLY a JSON array of exactly 5 objects:
[
  {{"rank": 1, "angle": "descriptive angle name", "hook": "The exact hook text", "thread": "Brief description of the narrative thread (1-2 sentences)", "type": "emotional|cultural|structural|specific", "why": "Why this hook works (1 sentence)"}},
  ...5 hooks total...
]

The "angle" field should be a SHORT descriptive name (e.g. "fever-performance", "forbidden-laughter", "one-note-disaster").
The "thread" field helps the operator understand what story the overlays would tell.
The "type" field classifies: emotional (paradox/feeling), cultural (history/impact), structural (music/composition), specific (performer/this video).
The "why" field explains in 1 sentence why this hook stops the scroll.

===============================
SELF-CHECK (execute before delivering)
===============================

For EACH hook, before outputting:
1. SCROLL: Person aged 25, 11pm, scrolling Instagram. Does their thumb STOP? If not, cut.
2. FEEL: Reaction in body or in head? If head, reformulate.
3. THREAD: 8 different subtitles without repeating? If forced, it's a dead end.
4. AI: Sounds like a human in a bar or Instagram copy? If copy, reformulate.
5. DIVERSITY: 5 hooks lead to 5 DIFFERENT stories? If 2 overlap, replace one.

Write ALL hook text in the SAME LANGUAGE as the Highlights field. If Highlights is empty, write in Portuguese.{build_language_reinforcement(project)}"""
