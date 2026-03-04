"""Serviço de processamento de vídeo via FFmpeg."""
import asyncio
import shutil
from pathlib import Path

from shared.storage_service import storage, lang_prefix


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


async def extrair_audio_completo(video_key: str, video_id: int, storage_path: str,
                                  r2_base: str = "") -> str:
    """Extrai áudio do vídeo COMPLETO para enviar ao Gemini.

    Args:
        video_key: R2 key do vídeo
        video_id: ID da edição (para pasta local temporária)
        storage_path: diretório local temporário
        r2_base: chave-base no R2 (ex: "Pavarotti - Nessun Dorma")
    Returns:
        R2 key do áudio extraído
    """
    local_video = storage.ensure_local(video_key)

    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_local = str(output_dir / "audio_completo.ogg")

    await run_ffmpeg(
        f'ffmpeg -y -i "{local_video}" -vn -acodec libopus -b:a 128k "{audio_local}"'
    )

    # Upload: {base}/video/audio_completo.ogg
    r2_key = f"{r2_base}/video/audio_completo.ogg" if r2_base else f"videos/{video_id}/audio_completo.ogg"
    storage.upload_file(audio_local, r2_key)
    return r2_key


async def cortar_na_janela_overlay(
    video_key: str,
    janela_inicio_sec: float,
    janela_fim_sec: float,
    video_id: int,
    storage_path: str,
    r2_base: str = "",
) -> dict:
    """Corta o vídeo na janela definida pelo overlay."""
    local_video = storage.ensure_local(video_key)

    output_dir = Path(storage_path) / str(video_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    cortado_local = str(output_dir / "video_cortado.mp4")
    cru_local = str(output_dir / "video_cru.mp4")

    # Bug A Fix: Usar busca precisa com re-encode para garantir que o corte 
    # comece exatamente no frame solicitado, sem depender de keyframes próximos.
    await run_ffmpeg(
        f'ffmpeg -y -ss {janela_inicio_sec} -to {janela_fim_sec} -i "{local_video}" '
        f'-avoid_negative_ts make_zero '
        f'-vf "setpts=PTS-STARTPTS" -af "asetpts=PTS-STARTPTS" '
        f'-c:v libx264 -preset ultrafast -crf 18 '
        f'-c:a aac -b:a 192k "{cortado_local}"'
    )

    shutil.copy(cortado_local, cru_local)

    # Upload: {base}/video/video_cortado.mp4 e video_cru.mp4
    prefix = f"{r2_base}/video" if r2_base else f"videos/{video_id}"
    r2_key_cortado = f"{prefix}/video_cortado.mp4"
    r2_key_cru = f"{prefix}/video_cru.mp4"
    storage.upload_file(cortado_local, r2_key_cortado)
    storage.upload_file(cru_local, r2_key_cru)

    return {
        "arquivo_cortado": r2_key_cortado,
        "arquivo_cru": r2_key_cru,
        "duracao_corte": janela_fim_sec - janela_inicio_sec,
    }


async def renderizar_video(video_cortado_key: str, ass_file: str, output_path: str,
                            r2_base: str = "", idioma: str = "") -> dict:
    """Renderiza vídeo com legendas ASS em formato 9:16.

    Args:
        video_cortado_key: R2 key do vídeo cortado
        ass_file: path local do arquivo .ass
        output_path: path local de saída
        r2_base: chave-base no R2
        idioma: código do idioma (para key R2)
    """
    local_video = storage.ensure_local(video_cortado_key)

    ass_escaped = ass_file.replace("\\", "/").replace(":", "\\:")

    await run_ffmpeg(
        f'ffmpeg -y -i "{local_video}" '
        f"-vf \"scale=1080:1920:force_original_aspect_ratio=decrease,"
        f"pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,"
        f"ass='{ass_escaped}'\" "
        f"-c:v libx264 -preset medium -crf 23 "
        f'-c:a aac -b:a 128k "{output_path}"'
    )

    size = Path(output_path).stat().st_size

    # Upload: {base}/{base} - {IDIOMA}/final.mp4
    if r2_base and idioma:
        r2_key = f"{lang_prefix(r2_base, idioma)}/final.mp4"
    else:
        r2_key = f"renders/{Path(output_path).name}"
    storage.upload_file(output_path, r2_key)

    return {"arquivo": r2_key, "tamanho_bytes": size}
