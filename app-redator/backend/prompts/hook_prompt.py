import logging

from backend.prompts.hook_helper import build_hook_text, build_language_reinforcement

logger = logging.getLogger(__name__)


def _field(label: str, value) -> str:
    v = str(value).strip() if value else ""
    if not v:
        return ""
    return f"- {label}: {v}\n"


def build_hook_generation_prompt(project, brand_config=None) -> str:
    bc = brand_config or {}
    brand_name = bc.get("brand_name", "")
    max_chars = bc.get("overlay_max_chars", 70)
    identity = bc.get("identity_prompt_redator", "")
    tom_de_voz = bc.get("tom_de_voz_redator", "")
    escopo = bc.get("escopo_conteudo", "")

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

    # Research data for richer, more specific hooks
    # Sprint 2A P4-005: abordagem conservadora (decisão 3) — log antes de truncar,
    # manter limite de 3000 chars como defesa (Princípio 4).
    research_block = ""
    research_data = getattr(project, "research_data", None)
    if research_data:
        import json
        if isinstance(research_data, dict):
            research_full = json.dumps(research_data, ensure_ascii=False)
        else:
            research_full = str(research_data)
        if len(research_full) > 3000:
            logger.warning(
                f"[Hook Research Truncate] research_data excede 3000 chars "
                f"({len(research_full)} chars): '{research_full[:80]}...'"
            )
        research_str = research_full[:3000]
        research_block = f"""
═══════════════════════════════
RESEARCH DATA (use for specific, factual hooks)
═══════════════════════════════
{research_str}

Use concrete facts from this research to make hooks SPECIFIC and UNFORGETTABLE.
Hooks that could apply to any classical music video are FAILURES.

"""

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

    # Passar o hook_category/complemento para contexto de ângulo preferido
    hook_context = build_hook_text(project, brand_config=brand_config)
    angle_block = ""
    if hook_context.strip():
        angle_block = f"""
The operator selected this angle direction:
{hook_context}

Use this as a STARTING POINT for hook #1. The other 4 hooks MUST explore DIFFERENT angles.
"""

    return f"""You are generating scroll-stopping hooks for a short-form music video on "{brand_name}".

A hook is the FIRST subtitle that appears on screen. It must stop the scroll in under 2 seconds of reading.
{brand_block}═══════════════════════════════
VIDEO DATA
═══════════════════════════════

{fields}
{research_block}{angle_block}
═══════════════════════════════
RULES
═══════════════════════════════

Generate exactly 5 hooks. Each must:
1. Be SPECIFIC to THIS video. Swapping the artist or work name must make the hook FALSE or meaningless.
2. Maximum {max_chars} characters (this is a hard technical limit).
3. Maximum 2 lines (use \\n for line break if needed).
4. Be grounded in verifiable facts. You MAY use well-known facts about the artist, work, or composer. NEVER invent facts.
5. Use a DIFFERENT angle from each other:
   - One based on a surprising FACT about the music itself
   - One based on the PERFORMER's story or biography
   - One based on historical CONTEXT, controversy, or cultural impact
   - One based on what the VIEWER can hear or see in the video
   - One based on an emotional PARADOX, contrast, or irony

═══════════════════════════════
ANTI-PATTERNS (never do this)
═══════════════════════════════

- "This will change how you hear music forever" (works for anything)
- "The most beautiful voice you'll ever hear" (empty adjective)
- "You won't believe what happens next" (clickbait)
- "One of the greatest performances ever" (generic superlative)
- Any hook that works equally well for Pavarotti singing Nessun Dorma AND a random choir singing Ave Maria. If it fits both, it's too generic.

═══════════════════════════════
GOOD EXAMPLES (specific, factual)
═══════════════════════════════

- "The high C in this piece was never in Allegri's score"
- "She was 17. She chose the hardest aria in opera."
- "The premiere flopped. The audience booed Verdi."
- "This melody existed 14 years before The Godfather."
- "Listen to what happens at 0:47. That note shouldn't exist."

═══════════════════════════════
OUTPUT FORMAT
═══════════════════════════════

Return ONLY a JSON array of exactly 5 objects:
[
  {{"angle": "fact", "hook": "The exact hook text here", "thread": "Brief description of where the overlay narrative goes after this hook (1-2 sentences)"}},
  {{"angle": "performer", "hook": "...", "thread": "..."}},
  {{"angle": "context", "hook": "...", "thread": "..."}},
  {{"angle": "visual", "hook": "...", "thread": "..."}},
  {{"angle": "paradox", "hook": "...", "thread": "..."}}
]

The "thread" field helps the operator understand what story the overlays would tell if this hook is chosen.

Write ALL hook text in the SAME LANGUAGE as the Highlights field. If Highlights is empty, write in Portuguese.{build_language_reinforcement(project)}"""
