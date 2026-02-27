"""Serviço de download de vídeos do YouTube via yt-dlp."""
import asyncio
import base64
import json
import os
from pathlib import Path

from shared.storage_service import storage, check_conflict, save_youtube_marker

_COOKIES_PATH = "/tmp/yt_cookies.txt"


def _ensure_cookies_file() -> str | None:
    """Decodifica YOUTUBE_COOKIES_BASE64 para arquivo temporário se disponível."""
    b64 = os.environ.get("YOUTUBE_COOKIES_BASE64")
    if not b64:
        return None
    try:
        data = base64.b64decode(b64)
        Path(_COOKIES_PATH).write_bytes(data)
        return _COOKIES_PATH
    except Exception:
        return None


async def download_video(youtube_url: str, video_id: int, storage_path: str,
                         artista: str = "", musica: str = "",
                         youtube_video_id: str = "") -> dict:
    """Baixa vídeo do YouTube em 1080p e envia para R2.

    Args:
        youtube_url: URL do YouTube
        video_id: ID da edição (para pasta local temporária)
        storage_path: diretório local temporário
        artista: nome do artista (para key R2)
        musica: nome da música (para key R2)
        youtube_video_id: ID do vídeo no YouTube (para desambiguação)
    """
    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    local_file = str(output_dir / "original.mp4")

    cookies_file = _ensure_cookies_file()

    cmd = [
        "yt-dlp",
        "-f", "bv*[height<=1080]+ba/bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", local_file,
        "--write-info-json",
        "--sub-langs", "all",
        "--write-subs",
        "--no-warnings",
        "--no-progress",
    ]
    if cookies_file:
        cmd.extend(["--cookies", cookies_file])
    cmd.append(youtube_url)

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

    # Upload para R2: {Artista} - {Musica}/video/original.mp4
    base = check_conflict(artista, musica, youtube_video_id)
    r2_key = f"{base}/video/original.mp4"
    storage.upload_file(local_file, r2_key)
    save_youtube_marker(base, youtube_video_id)

    return {
        "arquivo_original": r2_key,
        "r2_base": base,
        "duracao_total": info.get("duration", 0),
        "resolucao": f"{info.get('width', '?')}x{info.get('height', '?')}",
    }
