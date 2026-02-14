"""Serviço de download de vídeos do YouTube via yt-dlp."""
import asyncio
import json
from pathlib import Path


async def download_video(youtube_url: str, video_id: int, storage_path: str) -> dict:
    """Baixa vídeo do YouTube em 1080p."""
    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "-o", str(output_dir / "original.mp4"),
        "--write-info-json",
        "--sub-langs", "all",
        "--write-subs",
        "--no-warnings",
        "--no-progress",
        youtube_url,
    ]

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise Exception(f"yt-dlp falhou: {stderr.decode()}")

    info_file = output_dir / "original.info.json"
    info = json.loads(info_file.read_text()) if info_file.exists() else {}

    return {
        "arquivo_original": str(output_dir / "original.mp4"),
        "duracao_total": info.get("duration", 0),
        "resolucao": f"{info.get('width', '?')}x{info.get('height', '?')}",
    }
