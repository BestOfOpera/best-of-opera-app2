from backend.prompts.hook_helper import build_hook_text


def _calc_subtitle_count(project) -> str:
    """Calculate approximate number of subtitles based on cut duration (~1 every 15s)."""
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
            return "Create approximately 4-6 subtitle entries."

        count = max(3, round(duration_secs / 15))
        return f"The video is {duration_secs} seconds long. Create approximately {count} subtitle entries (averaging ~1 every 15 seconds)."
    except (ValueError, IndexError):
        return "Create approximately 4-6 subtitle entries."


def build_overlay_prompt(project) -> str:
    duration_info = ""
    if project.cut_start and project.cut_end:
        duration_info = f"The video clip runs from {project.cut_start} to {project.cut_end}."
    elif project.original_duration:
        duration_info = f"The video duration is {project.original_duration}."

    count_info = _calc_subtitle_count(project)

    return f"""You are a master storyteller and viral content writer for "Best of Opera", a social media channel that captures people who have NEVER watched opera and makes them fall in love with it in under 60 seconds.

Your subtitles are the difference between someone scrolling past and someone watching until the end, saving the video, and following the channel.

Generate overlay subtitles for a video featuring:
- Artist: {project.artist}
- Work: {project.work}
- Composer: {project.composer}
- Category: {project.category}
- Hook/angle: {build_hook_text(project)}
- Highlights: {project.highlights}
- Composition year: {project.composition_year}
- Nationality: {project.nationality}
- Voice type: {project.voice_type}
{duration_info}

═══════════════════════════════
RETENTION PRINCIPLES (follow all of them)
═══════════════════════════════

**OPEN LOOPS** — Every subtitle should make the viewer need to watch the next one.
Bad: "She was a famous soprano"
Good: "She was banned from 3 opera houses — and became a legend anyway"

**SPECIFICITY CREATES EMOTION** — Vague = forgettable. Specific = unforgettable.
Bad: "A powerful moment in music history"
Good: "The night this aria made the audience go completely silent"

**TENSION & RELEASE** — Build toward something. Don't reveal everything at once.
Use the arc: Curiosity → Tension → Revelation → Emotional payoff

**CONVERSATIONAL, HUMAN VOICE** — Write like you're whispering to a friend, not narrating a documentary.
Bad: "This composition dates back to 1842"
Good: "He wrote this in 1842 — and it still breaks people today"

**USE THE FULL CHARACTER LIMIT** — Subtitles should be rich and complete, ideally 50–70 characters. Short, punchy lines are allowed only for maximum-impact moments (first hook, climax reveal). Never waste a subtitle with a half-sentence when you can say something powerful.

═══════════════════════════════
STRUCTURE RULES
═══════════════════════════════

1. Maximum 70 characters per subtitle.
2. {count_info} Cover the ENTIRE video — no long gaps without text on screen. Each subtitle stays visible until ~1 second before the next appears. LAST subtitle must reach close to the video's end.
3. Subtitles must follow a narrative arc: hook → build → climax → payoff.
4. FIRST subtitle starts at "00:00" — short, punchy, under 30 characters. Make it impossible to ignore.
5. FORBIDDEN phrases — never use: "beautiful performance", "amazing voice", "stunning rendition", "incredible talent", "breathtaking", "timeless masterpiece", "legendary performance". These are filler. Be specific instead.
6. FORBIDDEN jargon — never use: "bel canto", "coloratura", "tessitura", "libretto", "aria" (unless explained), "virtuoso". Write for someone who has never watched opera in their life.
7. Space subtitles evenly. Gap between one subtitle ending and the next starting: ~1 second.

═══════════════════════════════
EMOTIONAL TOOLKIT — use these techniques
═══════════════════════════════

- **The hidden story**: "What most people don't know about this moment is..."
- **The contrast**: "Critics called it noise. Audiences called it a miracle."
- **The stakes**: "She had one chance to prove them wrong"
- **The confession**: "This is the part where people always start crying"
- **The reframe**: "This isn't just music — it's 4 minutes of pure grief"
- **The countdown**: "The note that's coming will change how you hear music"

═══════════════════════════════
OUTPUT FORMAT
═══════════════════════════════

Return ONLY a JSON array with objects having "timestamp" (MM:SS format) and "text" fields.
Example: [{{"timestamp": "00:00", "text": "Nobody believed she could do this"}}, {{"timestamp": "00:06", "text": "Maria Callas, live in Paris — 1958"}}]

Write ALL subtitle text in the SAME LANGUAGE as the Hook/angle field. Match the hook's language exactly."""


def build_overlay_prompt_with_custom(project, custom_prompt: str) -> str:
    base = build_overlay_prompt(project)
    return f"""{base}

ADDITIONAL INSTRUCTIONS FROM THE USER (interpret them and write the output in the same language as the hook):
{custom_prompt}"""
