from backend.prompts.hook_helper import build_hook_text, build_language_reinforcement


def _field(label: str, value) -> str:
    """Return '- Label: value' if value is non-empty, else empty string."""
    v = str(value).strip() if value else ""
    if not v:
        return ""
    return f"- {label}: {v}\n"


def _calc_subtitle_count(project, interval_secs: int = 15) -> str:
    """Calculate approximate number of subtitles based on cut duration."""
    try:
        if project.cut_start and project.cut_end:
            start_parts = project.cut_start.split(":")
            end_parts = project.cut_end.split(":")
            start_secs = int(start_parts[0]) * 60 + int(start_parts[1])
            end_secs = int(end_parts[0]) * 60 + int(end_parts[1])
            duration_secs = end_secs - start_secs
        elif project.original_duration:
            parts = project.original_duration.split(":")
            duration_secs = int(parts[0]) * 60 + int(parts[1])
        else:
            return "Create approximately 4-6 subtitle entries. Use the interval as a flexible guide — cluster subtitles around context-rich moments and space them out during purely musical passages."

        # -1 para reservar espaço para o CTA (injetado automaticamente pelo sistema)
        count = max(3, round(duration_secs / interval_secs) - 1)
        min_count = max(3, count - 2)
        max_count = count + 2
        return (
            f"The video is {duration_secs} seconds long. "
            f"Target around {count} subtitle entries ({min_count}-{max_count} is acceptable), "
            f"using ~{interval_secs}s as a flexible reference interval. "
            f"IMPORTANT: This interval is a GUIDE, not a rigid rule. "
            f"Cluster subtitles closer together during context-rich moments "
            f"(introductions, revelations, emotional peaks) and space them further apart "
            f"during purely musical passages where the performance speaks for itself. "
            f"The system adds a CTA at the end automatically."
        )
    except (ValueError, IndexError):
        return "Create approximately 4-6 subtitle entries. Use the interval as a flexible guide — cluster subtitles around context-rich moments and space them out during purely musical passages."


def _extract_narrative(post_text: str, max_chars: int = 500) -> str:
    """Extrai parágrafos narrativos do post (Section 2), sem ficha técnica/hashtags.

    Retorna texto truncado em max_chars.
    """
    if not post_text or not post_text.strip():
        return ""
    lines = post_text.split("\n")
    # Pular primeira linha (emoji intro)
    start = None
    for i, line in enumerate(lines):
        if line.strip():
            start = i + 1
            break
    if start is None:
        return ""
    # Coletar até encontrar linha com label de créditos (emoji + ":" pattern)
    narrative_lines = []
    for line in lines[start:]:
        stripped = line.strip().lower()
        if any(stripped.startswith(m) for m in (
            "voice type:", "tipo de voz:", "nationality:", "nacionalidade:",
            "composer:", "compositor:", "date of birth:", "data de nascimento:",
            "#",
        )):
            break
        # Parar se linha começa com emoji seguido de label (padrão ficha técnica)
        if len(stripped) > 2 and stripped[0] not in "abcdefghijklmnopqrstuvwxyz\"'" and ":" in stripped[:40]:
            break
        narrative_lines.append(line)
    narrative = "\n".join(narrative_lines).strip()
    if len(narrative) > max_chars:
        narrative = narrative[:max_chars].rsplit(" ", 1)[0] + "..."
    return narrative


def _build_overlay_fields(project) -> str:
    """Monta os campos de input do projeto para overlay."""
    highlights = getattr(project, "highlights", "") or ""
    # Fallback: se highlights vazio, usar research_data ou narrativa do post
    if not highlights.strip():
        research_data = getattr(project, "research_data", None)
        if research_data and isinstance(research_data, dict):
            angulos = research_data.get("angulos_narrativos", [])
            if angulos and isinstance(angulos, list):
                highlights = "; ".join(
                    a.get("nome", "") for a in angulos[:5]
                    if isinstance(a, dict) and a.get("nome")
                )
        if not highlights.strip():
            post_text = getattr(project, "post_text", "") or ""
            highlights = _extract_narrative(post_text)
    return (
        f"{_field('Artist', project.artist)}"
        f"{_field('Work', project.work)}"
        f"{_field('Composer', project.composer)}"
        f"{_field('Category', project.category)}"
        f"{_field('Hook/angle', build_hook_text(project))}"
        f"{_field('Highlights', highlights)}"
        f"{_field('Composition year', project.composition_year)}"
        f"{_field('Nationality', project.nationality)}"
        f"{_field('Voice type', project.voice_type)}"
    )


def build_overlay_prompt(project, brand_config=None) -> str:
    bc = brand_config or {}
    brand_name = bc.get("brand_name", "")
    max_chars = bc.get("overlay_max_chars", 70)
    max_chars_line = bc.get("overlay_max_chars_linha", 35)
    interval_secs = bc.get("overlay_interval_secs", 6)
    opening_line = bc.get("brand_opening_line", "")
    identity = bc.get("identity_prompt_redator", "")
    tom_de_voz = bc.get("tom_de_voz_redator", "")
    escopo = bc.get("escopo_conteudo", "")

    duration_info = ""
    if project.cut_start and project.cut_end:
        duration_info = f"The video clip runs from {project.cut_start} to {project.cut_end}."
    elif project.original_duration:
        duration_info = f"The video duration is {project.original_duration}."

    count_info = _calc_subtitle_count(project, interval_secs=interval_secs)
    fields = _build_overlay_fields(project)

    # Research data: usar pesquisa profunda se disponível, fallback para post_text
    research_block = ""
    research_data = getattr(project, "research_data", None)
    if research_data and isinstance(research_data, dict):
        # Extrair fatos surpreendentes e ângulos da pesquisa
        fatos = research_data.get("fatos_surpreendentes", [])
        fatos_text = "\n".join(f"- {f.get('fato', '')}" for f in fatos[:8] if isinstance(f, dict) and f.get("fato"))
        angulos = research_data.get("angulos_narrativos", [])
        angulos_text = "\n".join(f"- {a.get('nome', '')}: {a.get('fio_narrativo', '')}" for a in angulos[:5] if isinstance(a, dict) and a.get("nome"))
        interprete = research_data.get("interprete", {}) if isinstance(research_data.get("interprete"), dict) else {}
        interp_parts = [interprete.get("diferencial", ""), interprete.get("relacao_com_esta_peca", "")]
        interp_text = " ".join(p for p in interp_parts if p).strip()

        parts = []
        if fatos_text:
            parts.append(f"SURPRISING FACTS:\n{fatos_text}")
        if angulos_text:
            parts.append(f"NARRATIVE ANGLES:\n{angulos_text}")
        if interp_text:
            parts.append(f"PERFORMER INSIGHT:\n- {interp_text}")

        if parts:
            research_block = f"""
RESEARCH DATA (use for specific facts in your HOOK and throughout the overlay):
{chr(10).join(parts)}

HOOK RULE: Your FIRST subtitle (hook) MUST reference a specific fact from the research data above. Generic hooks like 'this will give you chills', 'you won't believe this', or 'what's about to happen will...' are STRICTLY PROHIBITED. The hook must contain a concrete, surprising detail about THIS specific artist, work, or performance.
"""
    else:
        # Fallback: post_text (para regeneração quando post já existe)
        post_text = getattr(project, "post_text", "") or ""
        if post_text.strip():
            narrative = _extract_narrative(post_text, max_chars=300)
            if narrative:
                research_block = f"""
RESEARCH DATA (use for specific facts in your HOOK):
{narrative}

HOOK RULE: Your FIRST subtitle (hook) MUST reference a specific fact from the research data above. Generic hooks are STRICTLY PROHIBITED. The hook must contain a concrete, surprising detail about THIS specific artist, work, or performance.
"""

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

    return f"""You are writing overlay captions for a short-form music video on "{brand_name}"{f' — {opening_line}' if opening_line else ''}. Your text appears ON SCREEN while the viewer listens. The music is the protagonist. Your words serve the music.

Your subtitles are the difference between someone scrolling past and someone watching until the end, saving the video, and following the channel.

═══════════════════════════════
CONTEXT
═══════════════════════════════

Generate overlay subtitles for a video featuring:
{fields}{duration_info}

Ground your facts in the research data provided. You MAY supplement with well-known, verifiable facts about the composer, work, or performer. For video anchoring captions, reference what the viewer can hear or see. NEVER invent facts. If uncertain, omit.
{research_block}{brand_block}
═══════════════════════════════
NARRATIVE RULES
═══════════════════════════════

RULE 1 — HOOK AS DOOR, NOT CEILING:
The Hook/angle is your ENTRY POINT, not your only topic. The first subtitle uses the hook to stop the scroll. After that, open 3-4 narrative threads the hook did NOT promise. The body must SURPRISE, not just explain the hook.
ANTI-PATTERN: every subtitle elaborates the same theme as the hook. If your overlays only talk about one idea, you have failed.

RULE 2 — VIDEO ANCHORING (minimum 2 captions):
Include at least 2 captions that anchor to the actual video. These connect your text to what the viewer SEES or HEARS right now. Use verbs: "Listen to", "Notice how", "Watch", "Hear". Place them in the middle and near the end, never as the hook.
Examples:
- "Listen to how she holds 'verita.' That word means the truth."
- "Notice how his voice doesn't push. It asks."
- "That note right there. That's the one Mendelssohn transcribed wrong."

RULE 3 — BLOCK STRUCTURE:
HOOK (subtitle 1): Stop the scroll. Maximum 2 lines. The strongest, most surprising fact or image.
CONSTRUCTION (subtitles 2-3): Immediate context. Concrete facts: who, when, where, what happened.
DEVELOPMENT (subtitles 4-6): Open new threads. Connect to the sound. At least 1 video anchoring here.
CLIMAX (subtitle 7+): The strongest fact or revelation. Time it to coincide with the musical peak.
CLOSING (second-to-last): Return to the hook with a twist or new perspective. Video anchoring if possible.
The system adds a CTA as the final subtitle automatically. Your LAST subtitle must be the final NARRATIVE one (the closing).

RULE 4 — PROGRESSIVE TENSION:
Every subtitle must deliver NEW information AND end with micro-tension (a question, a contradiction, an unresolved thread). Shuffling the subtitles should BREAK the narrative. If the order doesn't matter, the writing has failed.
Use active verbs: sang, booed, wept, refused, stripped, won, escaped, silenced, played, wrote, held, waited.

RULE 5 — TONE AND RHYTHM:
Write like a whisper in a theater, not a documentary narrator. Alternate short sentences with medium ones.
Examples: "The film disappeared. The melody waited." / "A printing error. It became the standard."
When the music reaches its climax, the overlay PULLS BACK (shorter sentence, fewer words). Let the music speak.

═══════════════════════════════
PROHIBITIONS
═══════════════════════════════

NEVER use:
- The em dash (—) anywhere in overlay text. Use periods or commas instead.
- Empty adjectives: "beautiful", "stunning", "incredible", "legendary", "iconic", "timeless", "spectacular", "breathtaking", "unforgettable", "masterpiece" (without a concrete fact).
- Repeating the hook's idea in subsequent subtitles. The hook opens the door; the body walks through it.
- More than 1 setup/reveal pair per subtitle. One fact, one surprise. Not two.
- More than 1 sensory metaphor every 3-4 subtitles. Overuse dilutes impact.
- Generic sentences that could apply to any video. Every subtitle must be specific to THIS artist, THIS work, THIS moment.
- "Dive into", "journey", "uncover", "fascinating", "explore".

═══════════════════════════════
EXAMPLE (Miserere mei, Deus — Allegri)
═══════════════════════════════

Hook angle: "The high C was never in the score"
[
  {{"timestamp": "00:00", "text": "The high C in this piece was never\\nin Allegri's score"}},
  {{"timestamp": "00:06", "text": "Allegri wrote this in 1638\\nfor the Sistine Chapel"}},
  {{"timestamp": "00:12", "text": "Listen to the choir beneath him.\\nThat part is 400 years old."}},
  {{"timestamp": "00:18", "text": "In 1831, Mendelssohn\\ntranscribed it a fourth higher"}},
  {{"timestamp": "00:24", "text": "That version landed in\\nGrove's Dictionary in 1880"}},
  {{"timestamp": "00:30", "text": "A printing error.\\nIt became the standard."}},
  {{"timestamp": "00:36", "text": "That mistake is what this boy\\nis singing right now."}}
]
Notice: the hook opens with the high C, then the body goes to 1638, choir texture, Mendelssohn, Grove's Dictionary, printing error. Each subtitle is a NEW thread. Two anchoring captions ("Listen to the choir", "singing right now"). The closing returns to the hook with a twist.

═══════════════════════════════
EXAMPLE 2 — GOOD (Vissi d'arte — Puccini/Tosca)
═══════════════════════════════

Hook angle: "Tosca kills to save love. Puccini almost cut this aria."
[
  {{"timestamp": "00:00", "text": "Tosca kills to save love.\\nPuccini almost cut this aria."}},
  {{"timestamp": "00:06", "text": "Rome, 1900. The premiere\\nwas nearly sabotaged."}},
  {{"timestamp": "00:12", "text": "Puccini thought this aria\\nstopped the drama cold."}},
  {{"timestamp": "00:18", "text": "Listen to that first phrase.\\nShe's not singing. She's pleading."}},
  {{"timestamp": "00:24", "text": "Sardou wrote the play in 1887\\nfor Sarah Bernhardt."}},
  {{"timestamp": "00:30", "text": "Notice how the orchestra\\npulls back. Only her voice."}},
  {{"timestamp": "00:36", "text": "The aria he wanted to cut\\nbecame the most recorded."}}
]
Notice: hook pairs two acts of destruction (Tosca's killing and Puccini's cut), then branches into 4 threads: sabotage, doubt, Sardou's play, orchestration. Two anchoring captions ("Listen to that first phrase", "Notice how the orchestra pulls back"). Closing echoes the hook's irony: what he wanted to destroy became immortal.

═══════════════════════════════
EXAMPLE 3 — BAD (common failures)
═══════════════════════════════

[
  {{"timestamp": "00:00", "text": "This performance will\\ngive you chills"}},
  {{"timestamp": "00:06", "text": "The singer delivers\\nan incredible performance"}},
  {{"timestamp": "00:12", "text": "Every note is filled\\nwith raw emotion"}},
  {{"timestamp": "00:18", "text": "This is what true\\nartistry sounds like"}},
  {{"timestamp": "00:24", "text": "A voice that defines\\na generation"}}
]
PROBLEMS:
1. GENERIC HOOK: "give you chills" works for ANY video. No specific fact.
2. SATURATED: every subtitle says "this is amazing" in different words. One idea repeated 5 times.
3. NO ANCHORING: zero references to what the viewer sees or hears in the video.
4. MONOTONE RHYTHM: all subtitles are exactly 2 lines with similar length.
5. DISCONNECTED CLOSING: "defines a generation" has no relation to "give you chills."
6. EMPTY ADJECTIVES: "incredible", "raw", "true" — all prohibited.
SWAP TEST: replace singer name — text still works for anyone. GENERIC. FAIL.

═══════════════════════════════
VERIFY (execute BEFORE delivering output)
═══════════════════════════════

Run ALL 6 checks. If ANY fails, fix BEFORE outputting.

CHECK 1 — ANCHORING:
Count subtitles that reference something AUDIBLE or VISIBLE in the video.
Good anchoring: "Listen to the clarinet opening" / "That high note you hear is not in the score"
Bad anchoring: "A beautiful melody" / "The sound is moving"
Minimum: 2 anchored subtitles. If fewer, rewrite weakest to anchor.

CHECK 2 — ANTI-SATURATION:
Does the hook's angle dominate more than 40% of subtitles?
If yes: the hook is the DOOR, not the SUBJECT. Diversify development.

CHECK 3 — NARRATIVE ARC:
Read ONLY first subtitle (hook) and last narrative subtitle (closing) side by side.
Do they form a pair? Does closing REFRAME, COMPLETE, or ECHO the hook?
If not: rewrite closing so it resonates with the opening.

CHECK 4 — ANTI-REPETITION:
Summarize each subtitle in 5 words.
If any two summaries overlap: one is redundant. Rewrite with a NEW angle.

CHECK 5 — RHYTHM:
Check subtitle lengths. If 3+ consecutive subtitles have similar character count (within 5 chars): vary them. Alternate short punchy (30-45 chars) with fuller (55-70 chars).

CHECK 6 — AI DETECTION:
Read all subtitles aloud mentally.
- Repeated parallelism ("X. Y. Z." in more than 1 subtitle)? Rewrite one.
- Sounds like Instagram copy or documentary voiceover? Rewrite conversationally.
- Cascade of sensory metaphors (more than 1 per 3 subtitles)? Cut extras.
- Em-dash (—) anywhere? REMOVE, use period or comma.
- Forbidden words from PROHIBITIONS section? REMOVE.

Only after ALL 6 checks pass: output.

═══════════════════════════════
TECHNICAL RULES
═══════════════════════════════

1. Write concise subtitles — each should be brief and punchy. See EXAMPLES for ideal length. The system handles formatting automatically.
2. {count_info} Cover the video with no long gaps without text on screen. Each subtitle stays visible until ~1 second before the next appears. Your LAST narrative subtitle should end at around 80% of the video duration — leave the final ~20% free for the CTA that the system adds automatically. Vary the spacing organically: tighter intervals for context-rich moments, wider intervals when the music speaks for itself.
3. FIRST subtitle starts at "00:00".
4. OVERLAY FORMATTING:
   - Split subtitles into 2 balanced lines using \\n.
   - The 2 lines must be BALANCED in length (maximum 30% difference between them).
5. WORD SPACING — CRITICAL: Every word MUST be separated by exactly one space character. NEVER concatenate two words without a space. Do NOT use newline characters (\\n) as word separators — use them ONLY for intentional line breaks.
   WRONG: "nuncasetocam" / "harmoniaé" / "comoum"
   CORRECT: "nunca se tocam" / "harmonia é" / "como um"
6. Follow ALL instructions from the Brand Identity, Tone of Voice, and Content Scope sections above for narrative arc, hook style, forbidden phrases, and writing rules.
7. Do NOT generate a CTA (call-to-action) subtitle. The system adds the CTA automatically. Your LAST subtitle must be the final NARRATIVE subtitle.

═══════════════════════════════
OUTPUT FORMAT
═══════════════════════════════

Return ONLY a JSON array with objects having "timestamp" (MM:SS format) and "text" fields.
Example: [{{"timestamp": "00:00", "text": "Nobody believed she could do this"}}, {{"timestamp": "00:06", "text": "Maria Callas, live in Paris, 1958"}}]

Write ALL subtitle text in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly.{build_language_reinforcement(project)}"""


def build_overlay_prompt_with_custom(project, custom_prompt: str, brand_config=None) -> str:
    base = build_overlay_prompt(project, brand_config=brand_config)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}{build_language_reinforcement(project)}"""
