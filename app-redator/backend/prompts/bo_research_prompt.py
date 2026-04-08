"""
BO Research Prompt — Pesquisa Profunda para Best of Opera
=========================================================
Análogo ao rc_research_prompt.py, adaptado para ópera/vocal.
Alimenta: hooks, overlay, post, youtube.

Método: Kephart (Role → Context → Task → Constraints → Format → Self-check)
"""


def build_bo_research_prompt(
    artist: str,
    work: str,
    composer: str,
    category: str = "",
    highlights: str = "",
    brand_config: dict | None = None,
) -> str:
    """
    Constrói prompt de pesquisa profunda para Best of Opera.
    Retorna texto livre (NÃO JSON) para flexibilidade.
    """
    bc = brand_config or {}
    identity = bc.get("identity_prompt_redator", "")
    brand_name = bc.get("brand_name", "Best of Opera")

    brand_section = ""
    if identity:
        brand_section = f"\nBRAND CONTEXT:\n{identity}\n"

    return f"""<role>
You are an expert researcher in opera, classical vocal music, and performance history.
Your mission: produce a rich, factual brief that a social media team will use to create
scroll-stopping content for "{brand_name}" (6M+ followers).{brand_section}

You excel at finding the SURPRISING, the EMOTIONAL, and the SPECIFIC — the details
that make someone stop scrolling and think "I didn't know that."
</role>

<context>
ARTIST/PERFORMER: {artist or "(not specified)"}
WORK: {work or "(not specified)"}
COMPOSER: {composer or "(not specified)"}
CATEGORY: {category or "(not specified)"}
{f"HIGHLIGHTS/NOTES: {highlights}" if highlights else ""}
</context>

<task>
Conduct deep research and produce a comprehensive brief covering ALL of the following.
Skip any section where you have no reliable information — never invent facts.

1. THE WORK
   - Full name, catalogue number, language, librettist (if opera/vocal)
   - When and where composed; what period in the composer's life
   - Original context: commission, premiere, reception
   - The story/libretto (if opera): what happens in this scene/aria
   - Why this moment in the work is musically or dramatically significant

2. THE SPECIFIC ARIA/SCENE (if identifiable)
   - Who is singing, to whom, and why
   - The emotional arc of this passage
   - What makes it technically or emotionally demanding
   - Famous interpretations and how they differ

3. THE COMPOSER ({composer or "unknown"})
   - Key biographical facts RELEVANT to this work
   - Artistic philosophy and compositional style
   - Relationship with the performer (if known)
   - Any controversy, scandal, or surprising personal detail

4. THE PERFORMER ({artist or "unknown"})
   - Why this performer stands out in this repertoire
   - Signature vocal/interpretive qualities
   - Career milestones and turning points
   - Personal story that resonates with audiences

5. SURPRISING DETAILS (prioritize these — they make the best hooks)
   - Premiere disasters or triumphs
   - Censorship, political scandal, or cultural impact
   - Technical feats (extreme notes, unusual techniques)
   - Connections to pop culture, film, or modern life
   - Records broken, traditions defied
   - Little-known facts that would astonish a general audience

6. EMOTIONAL/SENSORY HOOKS
   - What makes this music viscerally moving
   - Physical/emotional reactions it provokes
   - Universal human experiences it connects to
   - Why someone scrolling Instagram should STOP and LISTEN
</task>

<constraints>
- Write 1500–3000 words. Be THOROUGH but concise.
- Every fact must be verifiable. Mark uncertain claims with "(unverified)".
- Prioritize SURPRISING over comprehensive — we need scroll-stoppers.
- Include specific names, dates, numbers, and quotes where possible.
- Write in the same language as the work title. Default to Portuguese if ambiguous.
- Do NOT pad with generic praise ("masterpiece", "legendary", "iconic").
  Replace adjectives with FACTS.
</constraints>

<self-check>
Before returning, verify:
1. Does the brief contain at least 3 facts that would make someone say "I didn't know that"?
2. Is every claim grounded in real information (not hallucinated)?
3. Could a writer create 5 DIFFERENT hooks from this brief alone?
If any answer is NO, add more specific detail before returning.
</self-check>"""
