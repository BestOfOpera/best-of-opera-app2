from __future__ import annotations


def timestamp_to_srt_time(ts: str) -> str:
    """Convert MM:SS to SRT format 00:MM:SS,000."""
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return f"00:{minutes.zfill(2)}:{seconds.zfill(2)},000"
    return f"00:{ts},000"


def generate_srt(overlay_json: list[dict]) -> str:
    """Generate SRT content from overlay JSON."""
    lines = []
    for i, entry in enumerate(overlay_json):
        start = timestamp_to_srt_time(entry["timestamp"])
        # End time: next entry's timestamp or +4 seconds
        if i + 1 < len(overlay_json):
            end = timestamp_to_srt_time(overlay_json[i + 1]["timestamp"])
        else:
            # Add 4 seconds to the last entry
            parts = entry["timestamp"].split(":")
            minutes = int(parts[0])
            seconds = int(parts[1]) + 4
            if seconds >= 60:
                minutes += 1
                seconds -= 60
            end = f"00:{str(minutes).zfill(2)}:{str(seconds).zfill(2)},000"

        lines.append(str(i + 1))
        lines.append(f"{start} --> {end}")
        lines.append(entry["text"])
        lines.append("")

    return "\n".join(lines)
