"""Serviço de processamento de vídeo via FFmpeg."""
import asyncio
import shutil
from pathlib import Path


async def run_ffmpeg(cmd: str):
    """Executa comando FFmpeg assíncrono."""
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        raise Exception(f"FFmpeg falhou: {stderr.decode()}")
    return stdout.decode()


async def extrair_audio_completo(video_path: str, video_id: int, storage_path: str) -> str:
    """Extrai áudio do vídeo COMPLETO para enviar ao Gemini."""
    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = output_dir / "audio_completo.ogg"

    await run_ffmpeg(
        f'ffmpeg -y -i "{video_path}" -vn -acodec libopus -b:a 128k "{audio}"'
    )
    return str(audio)


async def cortar_na_janela_overlay(
    video_path: str,
    janela_inicio_sec: float,
    janela_fim_sec: float,
    video_id: int,
    storage_path: str,
) -> dict:
    """Corta o vídeo na janela definida pelo overlay."""
    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    cortado = output_dir / "video_cortado.mp4"
    cru = output_dir / "video_cru.mp4"

    await run_ffmpeg(
        f'ffmpeg -y -i "{video_path}" '
        f"-ss {janela_inicio_sec} -to {janela_fim_sec} "
        f'-c copy "{cortado}"'
    )

    shutil.copy(str(cortado), str(cru))

    return {
        "arquivo_cortado": str(cortado),
        "arquivo_cru": str(cru),
        "duracao_corte": janela_fim_sec - janela_inicio_sec,
    }


async def renderizar_video(video_cortado: str, ass_file: str, output_path: str) -> dict:
    """Renderiza vídeo com legendas ASS em formato 9:16."""
    # Escapar path do ASS para filtro FFmpeg (: e \ precisam de escape)
    ass_escaped = ass_file.replace("\\", "/").replace(":", "\\:")

    await run_ffmpeg(
        f'ffmpeg -y -i "{video_cortado}" '
        f"-vf \"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        f"ass='{ass_escaped}'\" "
        f"-c:v libx264 -preset medium -crf 23 "
        f'-c:a aac -b:a 128k "{output_path}"'
    )

    size = Path(output_path).stat().st_size
    return {"arquivo": output_path, "tamanho_bytes": size}
