from __future__ import annotations


def timestamp_to_srt_time(ts: str) -> str:
    """Convert MM:SS to SRT format 00:MM:SS,000."""
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return f"00:{minutes.zfill(2)}:{seconds.zfill(2)},000"
    return f"00:{ts},000"


def generate_srt(overlay_json: list[dict], cut_end: str = None) -> str:
    """Generate SRT content from overlay JSON.

    Cada overlay dura até 1s antes do próximo.
    O último overlay vai até cut_end (fim do corte) ou +10s.
    """
    lines = []
    for i, entry in enumerate(overlay_json):
        start = timestamp_to_srt_time(entry["timestamp"])
        if i + 1 < len(overlay_json):
            # End = 1s antes do próximo overlay
            next_parts = overlay_json[i + 1]["timestamp"].split(":")
            next_minutes = int(next_parts[0])
            next_seconds = int(next_parts[1]) - 1
            if next_seconds < 0:
                next_minutes -= 1
                next_seconds += 60
            end = f"00:{str(next_minutes).zfill(2)}:{str(max(0, next_seconds)).zfill(2)},000"
        else:
            # Último overlay: até o fim do corte
            if cut_end:
                end = timestamp_to_srt_time(cut_end)
            else:
                # Fallback: +10 segundos
                parts = entry["timestamp"].split(":")
                minutes = int(parts[0])
                seconds = int(parts[1]) + 10
                if seconds >= 60:
                    minutes += 1
                    seconds -= 60
                end = f"00:{str(minutes).zfill(2)}:{str(seconds).zfill(2)},000"

        lines.append(str(i + 1))
        lines.append(f"{start} --> {end}")
        lines.append(entry["text"])
        lines.append("")

    return "\n".join(lines)
