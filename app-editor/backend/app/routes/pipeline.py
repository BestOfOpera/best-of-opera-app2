"""Rotas do pipeline de edição (passos 1-9)."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path as FilePath
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)
from app.models import Edicao, Overlay, Alinhamento, TraducaoLetra, Render
from app.models.perfil import Perfil
from app.schemas import AlinhamentoOut, AlinhamentoValidar, LetraAprovar
from app.services.ffmpeg_service import extrair_audio_completo, cortar_na_janela_overlay
from app.services.gemini import buscar_letra as gemini_buscar_letra
from app.services.regua import extrair_janela_do_overlay, reindexar_timestamps, recortar_lyrics_na_janela, normalizar_segmentos
import os
import shutil
from app.config import STORAGE_PATH, IDIOMAS_ALVO, EXPORT_PATH, REDATOR_API_URL, CURADORIA_API_URL, COBALT_API_URL
from shared.storage_service import storage, lang_prefix, check_conflict, save_youtube_marker

router = APIRouter(prefix="/api/v1/editor", tags=["pipeline"])


def _capture_sentry(e: BaseException, edicao_id: int, etapa: str, extra: dict = None):
    if isinstance(e, asyncio.CancelledError):
        return
    try:
        import sentry_sdk
        sentry_sdk.set_context("edicao", {"id": edicao_id, "etapa": etapa, **(extra or {})})
        sentry_sdk.capture_exception(e)
    except Exception:
        pass


async def _download_via_cobalt(youtube_url: str, output_path: str) -> bool:
    """Baixa vídeo usando cobalt.tools API. Retorna True se ok, False se falhar."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=15)) as client:
            resp = await client.post(
                COBALT_API_URL,
                json={"url": youtube_url, "videoQuality": "1080"},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            logger.warning(f"[cobalt] HTTP {resp.status_code}: {resp.text[:300]}")
            return False
        data = resp.json()
        status = data.get("status")
        if status not in ("tunnel", "redirect"):
            logger.warning(f"[cobalt] Status inesperado: {status} — {data}")
            return False
        download_url = data.get("url")
        if not download_url:
            logger.warning(f"[cobalt] URL ausente na resposta")
            return False

        # Baixar o vídeo
        async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=15)) as client:
            async with client.stream("GET", download_url) as r:
                if r.status_code != 200:
                    logger.warning(f"[cobalt] Download falhou HTTP {r.status_code}")
                    return False
                with open(output_path, "wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=1024 * 1024):
                        f.write(chunk)
        logger.info(f"[cobalt] Download concluído → {output_path}")
        return True
    except Exception as e:
        logger.warning(f"[cobalt] Falha: {e}")
        return False


async def _download_via_ytdlp(youtube_url: str, output_path: str) -> bool:
    """Baixa vídeo usando yt-dlp como último fallback. Retorna True se ok."""
    try:
        cmd = (
            f'yt-dlp "{youtube_url}" '
            f'-o "{output_path}" '
            f'-f "bv[ext=mp4][height<=1080]+ba[ext=m4a]/best[ext=mp4]/best" '
            f'--merge-output-format mp4 '
            f'--no-playlist '
            f'--quiet'
        )
        processo = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            _, stderr_out = await asyncio.wait_for(processo.communicate(), timeout=300)
        except asyncio.TimeoutError:
            processo.kill()
            await processo.wait()
            logger.warning("[yt-dlp] Timeout após 300s")
            return False
        if processo.returncode != 0:
            logger.warning(f"[yt-dlp] Falhou: {stderr_out.decode()[-500:]}")
            return False
        logger.info(f"[yt-dlp] Download concluído → {output_path}")
        return True
    except Exception as e:
        logger.warning(f"[yt-dlp] Falha: {e}")
        return False


def _sanitize_filename(s: str) -> str:
    """Remove caracteres proibidos em nomes de arquivo (Windows + Unix)."""
    import re as _re
    # Remove: / \ : * ? " < > |  e controles ASCII
    sanitized = _re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', s)
    return sanitized.strip('. ')


def _nome_arquivo_render(artista: str, musica: str, idioma: str) -> str:
    """Gera nome padronizado: '{Artista} — {Musica} - {Idioma}.mp4'.

    Exemplo: 'Olga Peretyatko — Casta Diva - En.mp4'
    """
    safe_artista = _sanitize_filename(artista)
    safe_musica = _sanitize_filename(musica)
    idioma_cap = idioma.capitalize()
    return f"{safe_artista} \u2014 {safe_musica} - {idioma_cap}.mp4"


def _get_r2_base(edicao) -> str:
    """Retorna r2_base da edição, computando se necessário."""
    if edicao.r2_base:
        return edicao.r2_base
    from shared.storage_service import project_base
    return project_base(edicao.artista, edicao.musica)


def _get_perfil_r2_prefix(edicao, db=None):
    """Busca r2_prefix do Perfil vinculado à edição."""
    if not edicao.perfil_id:
        return ""
    if db:
        perfil = db.get(Perfil, edicao.perfil_id)
        return perfil.r2_prefix if perfil else ""
    return ""


class CorteParams(BaseModel):
    janela_inicio: Optional[float] = None
    janela_fim: Optional[float] = None


_STATUS_PERMITIDOS_DOWNLOAD = {"aguardando", "baixando", "letra", "erro"}


# --- Passo 1: Garantir vídeo ---
@router.post("/edicoes/{edicao_id}/garantir-video")
async def garantir_video(edicao_id: int, db: Session = Depends(get_db)):
    from app.worker import task_queue

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Idempotência: se já tem vídeo no R2, não baixar de novo
    if edicao.arquivo_video_completo and storage.exists(edicao.arquivo_video_completo):
        return {"status": "já disponível", "arquivo": edicao.arquivo_video_completo}

    # Check-and-set atômico: só aceitar se status permite
    result = db.execute(
        update(Edicao)
        .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_DOWNLOAD))
        .values(status="baixando", erro_msg=None, passo_atual=1)
    )
    db.commit()

    if result.rowcount == 0:
        db.refresh(edicao)
        raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar download")

    logger.info(f"[download] Enfileirando edicao_id={edicao_id} queue={task_queue.qsize()}")
    task_queue.put_nowait((_download_task, edicao_id))
    return {"status": "download enfileirado"}


@router.post("/edicoes/{edicao_id}/upload-video")
async def upload_video(edicao_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Salvar localmente primeiro
    output_dir = FilePath(STORAGE_PATH) / str(edicao_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = str(output_dir / "original.mp4")

    with open(local_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    # Upload para R2: {r2_prefix}/{Artista} - {Musica}/video/original.mp4
    prefix = _get_perfil_r2_prefix(edicao, db)
    base = check_conflict(edicao.artista, edicao.musica, edicao.youtube_video_id or "", r2_prefix=prefix)
    full_base = f"{prefix}/{base}" if prefix else base
    r2_key = f"{full_base}/video/original.mp4"
    storage.upload_file(local_path, r2_key)
    if edicao.youtube_video_id:
        save_youtube_marker(base, edicao.youtube_video_id, r2_prefix=prefix)

    edicao.arquivo_video_completo = r2_key
    edicao.r2_base = base  # BARE no DB
    edicao.status = "letra"
    edicao.passo_atual = 2
    edicao.erro_msg = None
    db.commit()
    return {"status": "ok", "arquivo": r2_key}


def _find_video_in_export(edicao):
    """Procura vídeo já baixado na pasta EXPORT_PATH (ex: iCloud do APP1)."""
    if not EXPORT_PATH:
        return None
    pasta_projeto = FilePath(EXPORT_PATH) / f"{edicao.artista} - {edicao.musica}"
    if not pasta_projeto.exists():
        return None
    mp4s = [f for f in pasta_projeto.iterdir() if f.suffix == '.mp4' and f.is_file()]
    if mp4s:
        mp4s.sort(key=lambda f: f.stat().st_size, reverse=True)
        logger.info(f"Vídeo encontrado na pasta local: {mp4s[0]}")
        return str(mp4s[0])
    return None


async def _download_task(edicao_id: int):
    try:
        logger.info(f"[download_task] INÍCIO edicao_id={edicao_id}")
        from app.database import SessionLocal
        from shared.storage_service import (
            check_conflict as _check_conflict,
            save_youtube_marker as _save_youtube_marker,
        )

        # PASSO A — Ler estado (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                logger.error(f"[{edicao_id}] Edição não encontrada, abortando task")
                return

            # Idempotência: se já tem vídeo no R2, não baixar de novo
            if edicao.arquivo_video_completo and storage.exists(edicao.arquivo_video_completo):
                logger.info(f"[{edicao_id}] Vídeo já existe no R2 ({edicao.arquivo_video_completo}), pulando download")
                edicao.status = "letra"
                edicao.passo_atual = 2
                edicao.erro_msg = None
                db.commit()
                return

            # Check local file (fast filesystem I/O, ok dentro da sessão)
            video_local = _find_video_in_export(edicao)

            # Copiar dados necessários para fora da sessão
            artista = edicao.artista
            musica = edicao.musica
            youtube_video_id = edicao.youtube_video_id or ""
            _prefix = _get_perfil_r2_prefix(edicao, db)

            # Setar heartbeat inicial
            edicao.status = "baixando"
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "etapa": "download",
                "passo": "inicializando",
            }
            db.commit()

        # PASSO B — Tentar vídeo local (banco FECHADO durante upload R2)
        if video_local:
            base = _check_conflict(artista, musica, youtube_video_id, r2_prefix=_prefix)
            full_base = f"{_prefix}/{base}" if _prefix else base
            r2_key = f"{full_base}/video/original.mp4"

            # Heartbeat antes de upload
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "download",
                        "passo": "upload_local_r2",
                    }
                    db.commit()

            storage.upload_file(video_local, r2_key)
            if youtube_video_id:
                _save_youtube_marker(base, youtube_video_id, r2_prefix=_prefix)

            # Salvar resultado (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.arquivo_video_completo = r2_key
                    edicao.r2_base = base
                    edicao.status = "letra"
                    edicao.passo_atual = 2
                    edicao.erro_msg = None
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {}
                    db.commit()

            logger.info(f"[{edicao_id}] Download concluído via local: {r2_key}")
            return

        # PASSO C — Verificar se vídeo já existe no R2 (upload prévio da curadoria)
        base = _check_conflict(artista, musica, youtube_video_id, r2_prefix=_prefix)
        full_base = f"{_prefix}/{base}" if _prefix else base
        r2_key = f"{full_base}/video/original.mp4"

        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "etapa": "download",
                    "passo": "verificando_r2",
                }
                db.commit()

        if storage.exists(r2_key):
            # Vídeo já está no R2 (provavelmente upload da curadoria)
            if youtube_video_id:
                _save_youtube_marker(base, youtube_video_id, r2_prefix=_prefix)

            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.arquivo_video_completo = r2_key
                    edicao.r2_base = base
                    edicao.status = "letra"
                    edicao.passo_atual = 2
                    edicao.erro_msg = None
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {}
                    db.commit()

            logger.info(f"[{edicao_id}] Vídeo encontrado no R2 (curadoria): {r2_key}")
            return

        # PASSO D — Pedir à curadoria para baixar do YouTube e salvar no R2
        if youtube_video_id and CURADORIA_API_URL:
            logger.info(f"[{edicao_id}] Vídeo não está no R2, pedindo à curadoria para baixar...")
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "download",
                        "passo": "curadoria_baixando",
                    }
                    db.commit()

            try:
                import httpx
                async with httpx.AsyncClient(timeout=httpx.Timeout(300, connect=15)) as client:
                    resp = await client.post(
                        f"{CURADORIA_API_URL}/api/prepare-video/{youtube_video_id}",
                        params={"artist": artista, "song": musica},
                    )
                if resp.status_code == 200:
                    result = resp.json()
                    cur_r2_key = result.get("r2_key", r2_key)
                    cur_r2_base = result.get("r2_base", base)

                    with SessionLocal() as db:
                        edicao = db.get(Edicao, edicao_id)
                        if edicao:
                            edicao.arquivo_video_completo = cur_r2_key
                            edicao.r2_base = cur_r2_base
                            edicao.status = "letra"
                            edicao.passo_atual = 2
                            edicao.erro_msg = None
                            edicao.task_heartbeat = datetime.now(timezone.utc)
                            edicao.progresso_detalhe = {}
                            db.commit()

                    logger.info(f"[{edicao_id}] Vídeo baixado via curadoria: {cur_r2_key}")
                    return
                else:
                    logger.warning(f"[{edicao_id}] Curadoria retornou {resp.status_code}: {resp.text[:300]}")
            except Exception as e:
                logger.warning(f"[{edicao_id}] Falha ao chamar curadoria: {e}")

        # PASSO E — cobalt.tools (download direto, antes do yt-dlp)
        if youtube_video_id and COBALT_API_URL:
            logger.info(f"[{edicao_id}] Tentando cobalt.tools para {youtube_video_id}...")
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {"etapa": "download", "passo": "cobalt"}
                    db.commit()

            cobalt_dir = FilePath(STORAGE_PATH) / str(edicao_id)
            cobalt_dir.mkdir(parents=True, exist_ok=True)
            cobalt_local = str(cobalt_dir / "original.mp4")
            youtube_url_full = f"https://www.youtube.com/watch?v={youtube_video_id}"
            cobalt_ok = await _download_via_cobalt(youtube_url_full, cobalt_local)

            if cobalt_ok:
                base2 = _check_conflict(artista, musica, youtube_video_id, r2_prefix=_prefix)
                full_base2 = f"{_prefix}/{base2}" if _prefix else base2
                r2_key2 = f"{full_base2}/video/original.mp4"
                storage.upload_file(cobalt_local, r2_key2)
                if youtube_video_id:
                    _save_youtube_marker(base2, youtube_video_id, r2_prefix=_prefix)
                try:
                    import os as _os
                    _os.unlink(cobalt_local)
                except Exception:
                    pass
                with SessionLocal() as db:
                    edicao = db.get(Edicao, edicao_id)
                    if edicao:
                        edicao.arquivo_video_completo = r2_key2
                        edicao.r2_base = base2
                        edicao.status = "letra"
                        edicao.passo_atual = 2
                        edicao.erro_msg = None
                        edicao.task_heartbeat = datetime.now(timezone.utc)
                        edicao.progresso_detalhe = {}
                        db.commit()
                logger.info(f"[{edicao_id}] Download concluído via cobalt: {r2_key2}")
                return

        # PASSO F — yt-dlp (último fallback antes de erro)
        if youtube_video_id:
            logger.info(f"[{edicao_id}] Tentando yt-dlp para {youtube_video_id}...")
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {"etapa": "download", "passo": "yt_dlp"}
                    db.commit()

            ytdlp_dir = FilePath(STORAGE_PATH) / str(edicao_id)
            ytdlp_dir.mkdir(parents=True, exist_ok=True)
            ytdlp_local = str(ytdlp_dir / "original.mp4")
            youtube_url_full = f"https://www.youtube.com/watch?v={youtube_video_id}"
            ytdlp_ok = await _download_via_ytdlp(youtube_url_full, ytdlp_local)

            if ytdlp_ok:
                base3 = _check_conflict(artista, musica, youtube_video_id, r2_prefix=_prefix)
                full_base3 = f"{_prefix}/{base3}" if _prefix else base3
                r2_key3 = f"{full_base3}/video/original.mp4"
                storage.upload_file(ytdlp_local, r2_key3)
                if youtube_video_id:
                    _save_youtube_marker(base3, youtube_video_id, r2_prefix=_prefix)
                try:
                    import os as _os
                    _os.unlink(ytdlp_local)
                except Exception:
                    pass
                with SessionLocal() as db:
                    edicao = db.get(Edicao, edicao_id)
                    if edicao:
                        edicao.arquivo_video_completo = r2_key3
                        edicao.r2_base = base3
                        edicao.status = "letra"
                        edicao.passo_atual = 2
                        edicao.erro_msg = None
                        edicao.task_heartbeat = datetime.now(timezone.utc)
                        edicao.progresso_detalhe = {}
                        db.commit()
                logger.info(f"[{edicao_id}] Download concluído via yt-dlp: {r2_key3}")
                return

        # Vídeo não encontrado em nenhum lugar — erro com orientação
        erro_msg = (
            f"Vídeo não encontrado no R2 (key: {r2_key}). "
            "Tentativas: curadoria, cobalt.tools e yt-dlp falharam. "
            "Faça upload manual."
        )
        logger.warning(f"[{edicao_id}] {erro_msg}")
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.status = "erro"
                edicao.erro_msg = erro_msg
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {}
                db.commit()
        return

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        else:
            _capture_sentry(e, edicao_id, "download")
            erro_msg = f"Erro inesperado: {str(e)[:500]}"
        logger.error(f"[{edicao_id}] _download_task erro inesperado: {e}", exc_info=True)
        try:
            from app.database import SessionLocal
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = erro_msg
                    db.commit()
        except Exception:
            logger.error(f"[{edicao_id}] Não conseguiu salvar erro no banco")
        if isinstance(e, asyncio.CancelledError):
            raise


# --- Passo 2: Letra ---
@router.post("/edicoes/{edicao_id}/letra")
async def buscar_letra_endpoint(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Buscar no banco primeiro
    from app.models import Letra
    letra_existente = db.query(Letra).filter(
        Letra.musica.ilike(f"%{edicao.musica}%"),
    ).first()

    if letra_existente:
        letra_existente.vezes_utilizada += 1
        db.commit()
        return {"fonte": "banco", "letra": letra_existente.letra, "letra_id": letra_existente.id}

    # Buscar via Gemini
    try:
        metadados = {
            "artista": edicao.artista,
            "musica": edicao.musica,
            "opera": edicao.opera,
            "compositor": edicao.compositor,
            "idioma": edicao.idioma,
        }
        letra_text = await gemini_buscar_letra(metadados)
        return {"fonte": "gemini", "letra": letra_text}
    except Exception as e:
        return {"fonte": "erro", "erro": str(e), "letra": ""}


@router.put("/edicoes/{edicao_id}/letra")
def aprovar_letra(edicao_id: int, body: LetraAprovar, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    from app.models import Letra

    letra = db.query(Letra).filter(
        Letra.musica == edicao.musica,
        Letra.idioma == edicao.idioma,
    ).first()

    if letra:
        letra.letra = body.letra
        letra.fonte = body.fonte
        letra.validado_por = body.validado_por
    else:
        letra = Letra(
            musica=edicao.musica,
            compositor=edicao.compositor,
            opera=edicao.opera,
            idioma=edicao.idioma,
            letra=body.letra,
            fonte=body.fonte,
            validado_por=body.validado_por,
        )
        db.add(letra)

    edicao.passo_atual = 3
    edicao.status = "transcricao"
    edicao.erro_msg = None
    db.commit()
    db.refresh(letra)
    return {"ok": True, "letra_id": letra.id}


# Statuses que permitem (re)iniciar transcrição
_STATUS_PERMITIDOS_TRANSCRICAO = {"letra", "transcricao", "alinhamento", "erro"}


# --- Passo 3: Transcrição ---
@router.post("/edicoes/{edicao_id}/transcricao")
async def iniciar_transcricao(edicao_id: int, db: Session = Depends(get_db)):
    from app.worker import task_queue

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if not edicao.arquivo_video_completo:
        raise HTTPException(
            409, "Vídeo ainda não foi baixado. Aguarde o download completar."
        )

    # Verificar se vídeo existe no R2
    if not storage.exists(edicao.arquivo_video_completo):
        raise HTTPException(
            409,
            "Vídeo não encontrado no R2. Faça upload manual ou verifique se a curadoria já processou este vídeo.",
        )

    # Extrair áudio se necessário
    if not edicao.arquivo_audio_completo or not storage.exists(edicao.arquivo_audio_completo):
        audio_key = await extrair_audio_completo(
            edicao.arquivo_video_completo, edicao_id, STORAGE_PATH,
            r2_base=_get_r2_base(edicao),
        )
        edicao.arquivo_audio_completo = audio_key
        db.commit()

    # Check-and-set atômico: só aceitar se status permite
    result = db.execute(
        update(Edicao)
        .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_TRANSCRICAO))
        .values(status="transcricao", erro_msg=None)
    )
    db.commit()

    if result.rowcount == 0:
        db.refresh(edicao)
        raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar transcrição")

    logger.info(f"[transcricao] Enfileirando edicao_id={edicao_id} queue={task_queue.qsize()}")
    task_queue.put_nowait((_transcricao_task, edicao_id))
    return {"status": "transcrição enfileirada"}


async def _transcricao_task(edicao_id: int):
    try:
        logger.info(f"[transcricao_task] INÍCIO edicao_id={edicao_id}")
        from app.database import SessionLocal
        from app.models import Letra
        from app.services.gemini import (
            transcrever_guiado_completo as _transcrever_guiado_completo,
            mapear_estrutura_audio as _mapear_estrutura_audio,
            completar_transcricao as _completar_transcricao,
            _detect_mime_type as _detect_mime,
            _get_client as _get_gemini_client,
            SafetyFilterError,
        )
        from app.services.alinhamento import (
            alinhar_letra_com_timestamps as _alinhar_letra,
            merge_transcricoes as _merge_transcricoes,
        )
        from app.services.regua import normalizar_segmentos as _normalizar_segmentos

        async def _retry_on_safety(fn):
            """Retry on SafetyFilterError up to 3 times with heartbeat."""
            for attempt in range(1, 4):
                try:
                    return await fn()
                except SafetyFilterError:
                    logger.warning(
                        f"[transcricao] Safety filter tentativa {attempt}/3 "
                        f"para edicao_id={edicao_id}"
                    )
                    if attempt == 3:
                        raise SafetyFilterError(
                            "Gemini bloqueou a transcrição por safety filter "
                            "após 3 tentativas. Música pode conter conteúdo sensível."
                        )
                    with SessionLocal() as db:
                        edicao_hb = db.get(Edicao, edicao_id)
                        if edicao_hb:
                            edicao_hb.task_heartbeat = datetime.now(timezone.utc)
                            db.commit()
                    await asyncio.sleep(5)

        # PASSO A — Ler estado e inicializar (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                logger.error(f"[{edicao_id}] Edição não encontrada, abortando task")
                return

            # Idempotência: se já passou para alinhamento ou posterior, não refazer
            _STATUS_JA_PASSOU = {"alinhamento", "corte", "traducao", "montagem",
                                 "preview", "preview_pronto", "revisao",
                                 "renderizando", "concluido"}
            if edicao.status in _STATUS_JA_PASSOU:
                logger.info(f"[{edicao_id}] Transcrição já concluída (status={edicao.status}), pulando")
                return

            # Garantir que o áudio existe no storage
            r2_base = _get_r2_base(edicao)
            arquivo_audio = edicao.arquivo_audio_completo
            arquivo_video = edicao.arquivo_video_completo
            artista = edicao.artista
            musica = edicao.musica
            compositor = edicao.compositor
            idioma = edicao.idioma

            # Setar status e heartbeat inicial
            edicao.status = "transcricao"
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "etapa": "transcricao",
                "passo": "inicializando",
            }
            db.commit()

        # PASSO B — Garantir áudio (banco FECHADO durante I/O)
        if not arquivo_audio or not storage.exists(arquivo_audio):
            if arquivo_video and storage.exists(arquivo_video):
                arquivo_audio = await extrair_audio_completo(
                    arquivo_video, edicao_id, STORAGE_PATH, r2_base=r2_base,
                )
                with SessionLocal() as db:
                    edicao = db.get(Edicao, edicao_id)
                    if edicao:
                        edicao.arquivo_audio_completo = arquivo_audio
                        db.commit()
            else:
                with SessionLocal() as db:
                    edicao = db.get(Edicao, edicao_id)
                    if edicao:
                        edicao.status = "erro"
                        edicao.erro_msg = "Áudio e vídeo não encontrados. Faça upload novamente."
                        db.commit()
                return

        # Garantir áudio local para envio ao Gemini
        audio_local = storage.ensure_local(arquivo_audio)

        # Buscar letra (sessão curta)
        with SessionLocal() as db:
            letra = db.query(Letra).filter(
                Letra.musica == musica,
                Letra.idioma == idioma,
            ).first()
            if not letra:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = "Letra não encontrada. Aprove a letra primeiro."
                    db.commit()
                return
            letra_texto = letra.letra
            letra_id = letra.id

        metadados = {"artista": artista, "musica": musica, "compositor": compositor}
        versos_esperados = len([v for v in letra_texto.split("\n") if v.strip()])

        # ============================================================
        # ESTRATÉGIA: CEGA PRIMEIRO → captura repetições naturalmente
        # ============================================================

        # Heartbeat antes do Gemini (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "etapa": "transcricao",
                    "passo": "mapeamento_estrutural",
                }
                db.commit()

        # Passo 1: MAPEAMENTO ESTRUTURAL (banco FECHADO)
        logger.info(f"[{edicao_id}] Passo 1: Mapeamento estrutural do áudio...")
        genai = _get_gemini_client()
        mime_type = _detect_mime(audio_local)
        audio_file_ref = genai.upload_file(audio_local, mime_type=mime_type)

        melhor_cega = None
        melhor_n_cega = 0
        for tentativa in range(1, 3):
            segmentos_cegos = await _retry_on_safety(
                lambda: _mapear_estrutura_audio(
                    audio_file_ref, idioma, metadados, letra_texto
                )
            )
            n = len(segmentos_cegos)
            logger.info(f"[{edicao_id}] Cega tentativa {tentativa}: {n} segmentos")
            if n > melhor_n_cega:
                melhor_n_cega = n
                melhor_cega = segmentos_cegos
            if n >= versos_esperados * 0.8:
                break

        segmentos_cegos = _normalizar_segmentos(melhor_cega or [])
        logger.info(f"[{edicao_id}] Cega final: {len(segmentos_cegos)} segmentos")

        # Heartbeat antes da guiada (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "etapa": "transcricao",
                    "passo": "transcricao_guiada",
                }
                db.commit()

        # Passo 2: Transcrição GUIADA (banco FECHADO)
        logger.info(f"[{edicao_id}] Passo 2: Transcrição GUIADA (texto fiel à letra)...")
        guiada_falhou = False
        try:
            segmentos_guiados = await _retry_on_safety(
                lambda: _transcrever_guiado_completo(
                    audio_local, letra_texto, idioma, metadados,
                )
            )
            segmentos_guiados = _normalizar_segmentos(segmentos_guiados)
            logger.info(f"[{edicao_id}] Guiada: {len(segmentos_guiados)} segmentos")
        except Exception as e_guiada:
            guiada_falhou = True
            segmentos_guiados = []
            logger.warning(
                f"[transcricao] Guiada falhou para edicao_id={edicao_id}: {e_guiada}"
            )
            # Se a cega também não tem resultado, propagar o erro
            if not segmentos_cegos:
                raise

        # Se a guiada falhou mas a cega tem resultado, usar cega como fallback
        if guiada_falhou and segmentos_cegos:
            logger.info(
                f"[transcricao] Guiada falhou, usando resultado da cega como "
                f"fallback para edicao_id={edicao_id} "
                f"({len(segmentos_cegos)} segmentos)"
            )
            resultado = _alinhar_letra(letra_texto, segmentos_cegos)
            resultado["rota"] = resultado.get("rota", "cega_fallback")
            # Marcar fallback no progresso
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "transcricao",
                        "passo": "fallback_cega",
                        "fallback": "cega",
                    }
                    db.commit()
        else:
            # Heartbeat antes do merge (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "transcricao",
                        "passo": "merge_alinhamento",
                    }
                    db.commit()

            # Passo 3: MERGE
            logger.info(f"[{edicao_id}] Passo 3: Merge (cega {len(segmentos_cegos)} × guiada {len(segmentos_guiados)})...")
            resultado = _merge_transcricoes(segmentos_cegos, segmentos_guiados, letra_texto)
            logger.info(
                f"[{edicao_id}] Merge: rota={resultado['rota']} "
                f"confiança={resultado['confianca_media']}"
            )

            # Passo 4: Se merge fraco, tentar alinhar guiada direta como fallback
            if resultado["rota"] == "C":
                logger.info(f"[{edicao_id}] Merge fraco (rota C), tentando alinhamento guiada direta...")
                resultado_guiada = _alinhar_letra(letra_texto, segmentos_guiados)
                if resultado_guiada["confianca_media"] > resultado["confianca_media"]:
                    logger.info(
                        f"[{edicao_id}] Guiada direta melhor: {resultado['confianca_media']:.3f} → "
                        f"{resultado_guiada['confianca_media']:.3f}"
                    )
                    resultado = resultado_guiada

        # Passo 5: Se ainda incompleto, tentar completação
        n_resultado = len(resultado.get("segmentos", []))
        if n_resultado < versos_esperados * 0.7:
            logger.info(
                f"[{edicao_id}] Resultado incompleto ({n_resultado}/{versos_esperados}). "
                f"Tentando completação..."
            )
            # Heartbeat antes da completação (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "transcricao",
                        "passo": "completacao",
                    }
                    db.commit()
            try:
                segmentos_completados = await _retry_on_safety(
                    lambda: _completar_transcricao(
                        audio_local, letra_texto,
                        resultado["segmentos"], idioma, metadados,
                    )
                )
                if len(segmentos_completados) > n_resultado:
                    logger.info(f"[{edicao_id}] Completação: {n_resultado} → {len(segmentos_completados)}")
                    segmentos_completados = _normalizar_segmentos(segmentos_completados)
                    resultado_completado = _alinhar_letra(letra_texto, segmentos_completados)
                    if resultado_completado["confianca_media"] >= resultado["confianca_media"]:
                        resultado = resultado_completado
            except Exception as e:
                if "safety filter" in str(e).lower() and not guiada_falhou:
                    raise  # propagate safety filter only if we don't have cega fallback
                logger.warning(f"[{edicao_id}] Completação falhou: {e}")

        resultado["segmentos"] = _normalizar_segmentos(resultado["segmentos"])

        # PASSO C — Salvar resultado e finalizar (sessão curta)
        with SessionLocal() as db:
            alinhamento = Alinhamento(
                edicao_id=edicao_id,
                letra_id=letra_id,
                segmentos_completo=resultado["segmentos"],
                confianca_media=resultado["confianca_media"],
                rota=resultado["rota"],
            )
            db.add(alinhamento)

            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.rota_alinhamento = resultado["rota"]
                edicao.confianca_alinhamento = resultado["confianca_media"]
                edicao.status = "alinhamento"
                edicao.passo_atual = 4
                edicao.erro_msg = None
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = (
                    {"fallback": "cega"} if guiada_falhou else {}
                )
            db.commit()

        logger.info(
            f"[{edicao_id}] Transcrição concluída: "
            f"rota={resultado['rota']} confiança={resultado['confianca_media']}"
        )
        logger.info(f"[{edicao_id}] _transcricao_task FINALIZOU COMPLETAMENTE")

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        elif "safety filter" in str(e).lower():
            erro_msg = (
                "Gemini bloqueou a transcrição por safety filter após 3 tentativas. "
                "Música pode conter conteúdo sensível."
            )
        else:
            _capture_sentry(e, edicao_id, "transcricao")
            erro_msg = f"Transcrição falhou: {repr(e)[:500]}"
        logger.error(f"[{edicao_id}] _transcricao_task erro: {e}", exc_info=True)
        try:
            from app.database import SessionLocal
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = erro_msg
                    db.commit()
        except Exception:
            logger.error(f"[{edicao_id}] Não conseguiu salvar erro no banco")
        if isinstance(e, asyncio.CancelledError):
            raise


# --- Passo 4: Alinhamento ---
@router.get("/edicoes/{edicao_id}/alinhamento")
def obter_alinhamento(edicao_id: int, db: Session = Depends(get_db)):
    alinhamento = db.query(Alinhamento).filter(
        Alinhamento.edicao_id == edicao_id
    ).order_by(Alinhamento.id.desc()).first()
    if not alinhamento:
        raise HTTPException(404, "Alinhamento não encontrado")

    edicao = db.get(Edicao, edicao_id)
    return {
        "alinhamento": {
            "id": alinhamento.id,
            "segmentos": alinhamento.segmentos_completo,
            "segmentos_cortado": alinhamento.segmentos_cortado,
            "confianca_media": alinhamento.confianca_media,
            "rota": alinhamento.rota,
            "validado": alinhamento.validado,
        },
        "janela": {
            "inicio": edicao.janela_inicio_sec,
            "fim": edicao.janela_fim_sec,
            "duracao": edicao.duracao_corte_sec,
        } if edicao.janela_inicio_sec else None,
    }


@router.put("/edicoes/{edicao_id}/alinhamento")
def validar_alinhamento(edicao_id: int, body: AlinhamentoValidar, db: Session = Depends(get_db)):
    alinhamento = db.query(Alinhamento).filter(
        Alinhamento.edicao_id == edicao_id
    ).order_by(Alinhamento.id.desc()).first()
    if not alinhamento:
        raise HTTPException(404, "Alinhamento não encontrado")

    alinhamento.segmentos_completo = body.segmentos
    alinhamento.validado = True
    alinhamento.validado_por = body.validado_por

    edicao = db.get(Edicao, edicao_id)
    edicao.passo_atual = 5
    edicao.status = "corte"
    edicao.erro_msg = None
    db.commit()
    return {"ok": True}


async def _buscar_corte_do_redator(edicao) -> tuple:
    """Busca cut_start/cut_end do Redator (APP2) para projetos importados sem esses campos."""
    import httpx
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{REDATOR_API_URL}/api/projects")
            resp.raise_for_status()
        for p in resp.json():
            if (p.get("artist", "").lower() == edicao.artista.lower()
                    and p.get("work", "").lower() == edicao.musica.lower()):
                cs = p.get("cut_start")
                ce = p.get("cut_end")
                if cs and ce:
                    logger.info(f"[{edicao.id}] Corte do Redator: {cs} → {ce}")
                    return cs, ce
    except Exception as e:
        logger.warning(f"[{edicao.id}] Falha ao buscar corte do Redator: {e}")
    return None, None


# --- Passo 5: Aplicar corte (régua do overlay) ---
@router.post("/edicoes/{edicao_id}/aplicar-corte")
async def aplicar_corte(
    edicao_id: int,
    body: CorteParams = CorteParams(),
    db: Session = Depends(get_db),
):
    import traceback as _tb
    try:
        return await _aplicar_corte_impl(edicao_id, body, db)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"aplicar_corte ERRO: {exc}\n{_tb.format_exc()}")
        raise HTTPException(500, f"Erro interno: {exc}")


async def _aplicar_corte_impl(edicao_id: int, body: CorteParams, db: Session):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    overlays = db.query(Overlay).filter(Overlay.edicao_id == edicao_id).all()
    if not overlays:
        raise HTTPException(400, "Nenhum overlay encontrado. Adicione overlays primeiro.")

    if body and body.janela_inicio is not None and body.janela_fim is not None:
        janela = {
            "janela_inicio_sec": body.janela_inicio,
            "janela_fim_sec": body.janela_fim,
            "duracao_corte_sec": body.janela_fim - body.janela_inicio,
        }
    else:
        corte_inicio_ov = edicao.corte_original_inicio
        corte_fim_ov = edicao.corte_original_fim
        if not corte_inicio_ov or not corte_fim_ov:
            corte_inicio_ov, corte_fim_ov = await _buscar_corte_do_redator(edicao)
            if corte_inicio_ov and corte_fim_ov:
                edicao.corte_original_inicio = corte_inicio_ov
                edicao.corte_original_fim = corte_fim_ov

        primeiro = overlays[0]
        janela = extrair_janela_do_overlay(
            primeiro.segmentos_original,
            corte_inicio_override=corte_inicio_ov,
            corte_fim_override=corte_fim_ov,
        )

    edicao.janela_inicio_sec = janela["janela_inicio_sec"]
    edicao.janela_fim_sec = janela["janela_fim_sec"]
    edicao.duracao_corte_sec = janela["duracao_corte_sec"]

    # Overlays do Redator têm timestamps clip-relativos (começam em "00:00").
    # Apenas normalizar o formato — NÃO subtrair janela_inicio (isso zeraria tudo).
    for ov in overlays:
        ov.segmentos_reindexado = normalizar_segmentos(ov.segmentos_original)
        # Log para rastreabilidade: confirmar que texto não foi alterado
        textos_orig = [s.get("text", "") for s in (ov.segmentos_original or [])]
        textos_reind = [s.get("text", "") for s in (ov.segmentos_reindexado or [])]
        if textos_orig != textos_reind:
            logger.warning(
                f"[{edicao_id}] ALERTA: overlay {ov.idioma} texto mudou na normalização! "
                f"original={textos_orig} reindexado={textos_reind}"
            )

    # Cortar vídeo — usar R2 storage (ensure_local garante disponibilidade)
    r2_base = _get_r2_base(edicao)
    video_key = edicao.arquivo_video_completo
    if not video_key or not storage.exists(video_key):
        raise HTTPException(
            409,
            "Vídeo não encontrado no R2. Faça upload manual ou verifique se a curadoria já processou este vídeo.",
        )

    if video_key and storage.exists(video_key):
        resultado = await cortar_na_janela_overlay(
            video_key,
            janela["janela_inicio_sec"],
            janela["janela_fim_sec"],
            edicao_id,
            STORAGE_PATH,
            r2_base=r2_base,
        )
        edicao.arquivo_video_cortado = resultado["arquivo_cortado"]
        edicao.arquivo_video_cru = resultado["arquivo_cru"]

    # Recortar lyrics se houver alinhamento
    alinhamento = db.query(Alinhamento).filter(
        Alinhamento.edicao_id == edicao_id, Alinhamento.validado == True
    ).order_by(Alinhamento.id.desc()).first()
    if alinhamento:
        alinhamento.segmentos_cortado = recortar_lyrics_na_janela(
            alinhamento.segmentos_completo,
            janela["janela_inicio_sec"],
            janela["janela_fim_sec"],
        )

    # Se instrumental, pular tradução direto para montagem
    edicao.passo_atual = 6
    edicao.status = "traducao"
    edicao.erro_msg = None
    edicao.task_heartbeat = None
    edicao.progresso_detalhe = {}
    db.commit()

    # Enfileirar tradução automática no worker (evita deadlock silencioso).
    # Se o enqueue falhar, reverter status para evitar deadlock.
    from app.worker import task_queue
    try:
        task_queue.put_nowait((_traducao_task, edicao_id))
        logger.info(f"[aplicar_corte] Tradução enfileirada edicao_id={edicao_id} queue={task_queue.qsize()}")
    except Exception as enqueue_err:
        logger.error(f"[aplicar_corte] Falha ao enfileirar tradução edicao_id={edicao_id}: {enqueue_err}")
        edicao.status = "erro"
        edicao.erro_msg = f"Falha ao enfileirar tradução: {enqueue_err}"
        db.commit()
        raise HTTPException(500, f"Corte aplicado mas falha ao enfileirar tradução: {enqueue_err}")

    return {
        "janela": janela,
        "video_cortado": edicao.arquivo_video_cortado,
        "traducao": "tradução enfileirada automaticamente",
    }


# Statuses que permitem (re)iniciar tradução
_STATUS_PERMITIDOS_TRADUCAO = {"corte", "traducao", "montagem", "erro"}


# --- Passo 6: Tradução lyrics ---
@router.post("/edicoes/{edicao_id}/traducao-lyrics")
async def traduzir_lyrics(edicao_id: int, db: Session = Depends(get_db)):
    from app.worker import task_queue

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")


    # Check-and-set atômico: só aceitar se status permite
    # Zerar heartbeat e progresso para que desbloquear funcione se a task travar
    result = db.execute(
        update(Edicao)
        .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_TRADUCAO))
        .values(status="traducao", task_heartbeat=None, progresso_detalhe={})
    )
    db.commit()

    if result.rowcount == 0:
        db.refresh(edicao)
        raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar tradução")

    logger.info(f"[traducao] Enfileirando edicao_id={edicao_id} queue={task_queue.qsize()}")
    task_queue.put_nowait((_traducao_task, edicao_id))
    return {"status": "tradução enfileirada"}


async def _traducao_task(edicao_id: int):
    try:
        logger.info(f"[traducao_task] INÍCIO edicao_id={edicao_id}")
        from app.database import SessionLocal
        from app.services.translate_service import traduzir_letra_cloud as traduzir_letra

        # PASSO A — Ler estado e inicializar (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                logger.error(f"[{edicao_id}] Edição não encontrada, abortando task")
                return

            alinhamento = db.query(Alinhamento).filter(
                Alinhamento.edicao_id == edicao_id
            ).order_by(Alinhamento.id.desc()).first()

            if not alinhamento or not alinhamento.segmentos_cortado:
                edicao.status = "erro"
                edicao.erro_msg = "Alinhamento cortado não encontrado"
                db.commit()
                return

            # Idempotência: calcular idiomas faltantes
            ja_traduzidos = {
                t.idioma for t in db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == edicao_id
                ).all()
            }
            idioma_origem = edicao.idioma

            # Carregar idiomas do perfil (fallback: IDIOMAS_ALVO)
            _perfil_trad = db.get(Perfil, edicao.perfil_id) if edicao.perfil_id else None
            _idiomas_trad = (_perfil_trad.idiomas_alvo or IDIOMAS_ALVO) if _perfil_trad else IDIOMAS_ALVO

            faltantes = [
                idioma for idioma in _idiomas_trad
                if idioma != idioma_origem and idioma not in ja_traduzidos
            ]
            total = len([i for i in _idiomas_trad if i != idioma_origem])
            concluidos = total - len(faltantes)

            # Copiar dados necessários para fora da sessão
            segmentos_cortado = alinhamento.segmentos_cortado
            metadados = {"musica": edicao.musica, "compositor": edicao.compositor}

            # Setar status e heartbeat inicial
            edicao.status = "traducao"
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "traducao": {
                    "etapa": "traducao",
                    "total": total,
                    "concluidos": concluidos,
                    "atual": None,
                    "erros": [],
                }
            }
            db.commit()

        # PASSO B — Loop de tradução, passada 1 (banco FECHADO durante I/O externo)
        falhou_primeira_vez = []
        for idioma in faltantes:
            # Heartbeat antes de cada chamada de tradução (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "traducao": {
                            "etapa": "traducao",
                            "total": total,
                            "concluidos": concluidos,
                            "atual": idioma,
                            "erros": [f"{i}: falhou" for i in falhou_primeira_vez],
                        }
                    }
                    db.commit()

            # I/O externo com timeout (banco FECHADO)
            try:
                logger.info(f"[{edicao_id}] Traduzindo para {idioma}...")
                resultado = await asyncio.wait_for(
                    traduzir_letra(segmentos_cortado, idioma_origem, idioma, metadados),
                    timeout=180,
                )

                # Upsert: atualiza se já existe, insere se não
                with SessionLocal() as db:
                    existing_trad = db.query(TraducaoLetra).filter(
                        TraducaoLetra.edicao_id == edicao_id,
                        TraducaoLetra.idioma == idioma,
                    ).first()
                    if existing_trad:
                        existing_trad.segmentos = resultado
                    else:
                        db.add(TraducaoLetra(edicao_id=edicao_id, idioma=idioma, segmentos=resultado))
                    db.commit()

                concluidos += 1
                logger.info(f"[{edicao_id}] Tradução {idioma} OK ({concluidos}/{total})")

            except asyncio.TimeoutError:
                falhou_primeira_vez.append(idioma)
                logger.warning(f"[{edicao_id}] Tradução {idioma} timeout após 180s (1ª passada)")
            except Exception as e:
                falhou_primeira_vez.append(idioma)
                logger.warning(f"[{edicao_id}] Tradução {idioma} falhou: {e} (1ª passada)")

        # PASSO B2 — Segunda passada: retry dos idiomas que falharam
        falhas_finais = []
        if falhou_primeira_vez:
            logger.info(f"[{edicao_id}] Retry de {len(falhou_primeira_vez)} tradução(ões): {falhou_primeira_vez}")
            for idioma in falhou_primeira_vez:
                with SessionLocal() as db:
                    edicao = db.get(Edicao, edicao_id)
                    if edicao:
                        edicao.task_heartbeat = datetime.now(timezone.utc)
                        edicao.progresso_detalhe = {
                            "traducao": {
                                "etapa": "traducao",
                                "total": total,
                                "concluidos": concluidos,
                                "atual": f"{idioma} (retry)",
                                "erros": [f"{i}: retry" for i in falhou_primeira_vez],
                            }
                        }
                        db.commit()

                try:
                    logger.info(f"[{edicao_id}] Retry tradução {idioma}...")
                    resultado = await asyncio.wait_for(
                        traduzir_letra(segmentos_cortado, idioma_origem, idioma, metadados),
                        timeout=180,
                    )
                    with SessionLocal() as db:
                        existing_trad = db.query(TraducaoLetra).filter(
                            TraducaoLetra.edicao_id == edicao_id,
                            TraducaoLetra.idioma == idioma,
                        ).first()
                        if existing_trad:
                            existing_trad.segmentos = resultado
                        else:
                            db.add(TraducaoLetra(edicao_id=edicao_id, idioma=idioma, segmentos=resultado))
                        db.commit()
                    concluidos += 1
                    logger.info(f"[{edicao_id}] Retry {idioma} OK ({concluidos}/{total})")
                except asyncio.TimeoutError:
                    falhas_finais.append(f"{idioma}: timeout (retry)")
                    logger.warning(f"[{edicao_id}] Retry {idioma} timeout após 180s")
                except Exception as e:
                    falhas_finais.append(f"{idioma}: {e}")
                    logger.warning(f"[{edicao_id}] Retry {idioma} falhou: {e}")

        # PASSO C — Finalização (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.passo_atual = 7
                edicao.tentativas_requeue = 0
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "traducao": {
                        "etapa": "traducao",
                        "total": total,
                        "concluidos": concluidos,
                        "atual": None,
                        "erros": falhas_finais,
                    }
                }
                if falhas_finais:
                    edicao.status = "erro"
                    edicao.erro_msg = f"Traduções com falha após retry ({len(falhas_finais)}): {'; '.join(falhas_finais)}"
                    logger.warning(f"[{edicao_id}] {len(falhas_finais)} traduções falharam após retry")
                else:
                    edicao.status = "montagem"
                    edicao.erro_msg = None
                db.commit()

        logger.info(f"[{edicao_id}] Tradução concluída: {concluidos} OK, {len(falhas_finais)} falhas")
        logger.info(f"[{edicao_id}] _traducao_task FINALIZOU COMPLETAMENTE")

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        else:
            _capture_sentry(e, edicao_id, "traducao")
            erro_msg = f"Erro inesperado: {str(e)[:500]}"
        logger.error(f"[{edicao_id}] _traducao_task erro inesperado: {e}", exc_info=True)
        try:
            from app.database import SessionLocal
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = erro_msg
                    db.commit()
        except Exception:
            logger.error(f"[{edicao_id}] Não conseguiu salvar erro no banco")
        if isinstance(e, asyncio.CancelledError):
            raise


# --- Reset de status travado ---
@router.post("/edicoes/{edicao_id}/limpar-traducoes")
def limpar_traducoes(edicao_id: int, db: Session = Depends(get_db)):
    """Apaga todas as traduções e volta o status para 'corte', forçando retradução completa."""
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    deletados = db.query(TraducaoLetra).filter(
        TraducaoLetra.edicao_id == edicao_id
    ).delete()
    edicao.status = "montagem"
    edicao.passo_atual = 7
    edicao.erro_msg = None
    db.commit()

    return {"ok": True, "traducoes_deletadas": deletados, "status": "montagem"}


@router.post("/edicoes/{edicao_id}/reset-traducao")
def reset_traducao(edicao_id: int, db: Session = Depends(get_db)):
    """Reseta status preso em 'traducao' para permitir retry.

    Mantém traduções já concluídas — só limpa o status travado.
    """
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if edicao.status not in ("traducao", "erro"):
        raise HTTPException(400, f"Status atual é '{edicao.status}', não precisa de reset")

    # Contar traduções já feitas
    traducoes_existentes = db.query(TraducaoLetra).filter(
        TraducaoLetra.edicao_id == edicao_id
    ).count()

    # Setar para "montagem" para destravar — permite retrigger tradução
    edicao.status = "montagem"
    edicao.passo_atual = 7
    edicao.erro_msg = None
    db.commit()

    return {
        "ok": True,
        "traducoes_existentes": traducoes_existentes,
        "msg": f"Status resetado para montagem. {traducoes_existentes} traduções já existem e serão mantidas.",
    }


# Statuses que permitem iniciar renderização final
_STATUS_PERMITIDOS_RENDER = {"montagem", "preview_pronto", "erro"}

# Statuses que permitem iniciar preview
_STATUS_PERMITIDOS_PREVIEW = {"montagem", "revisao", "erro"}


# --- Passos 7-8: Renderização ---
@router.post("/edicoes/{edicao_id}/renderizar")
async def renderizar(edicao_id: int, sem_legendas: bool = False):
    from app.database import SessionLocal
    from app.worker import task_queue

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_RENDER))
            .values(status="renderizando", task_heartbeat=None, progresso_detalhe={})
        )
        db.commit()

        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar renderização")

    if sem_legendas:
        _sem = True
        async def _render_sem_legendas(_eid: int):
            await _render_task(_eid, sem_legendas=_sem)
        task_queue.put_nowait((_render_sem_legendas, edicao_id))
    else:
        task_queue.put_nowait((_render_task, edicao_id))
    return {"status": "renderização iniciada", "sem_legendas": sem_legendas}


async def _render_task(edicao_id: int, idiomas_renderizar: list = None, is_preview: bool = False, sem_legendas: bool = False):
    try:
        from app.database import SessionLocal
        from app.services.legendas import (
            gerar_ass, OVERLAY_MAX_CHARS_LINHA, LYRICS_MAX_CHARS, TRADUCAO_MAX_CHARS
        )
        from pathlib import Path as _Path

        # PASSO A — Ler estado (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                logger.error(f"[{edicao_id}] Edição não encontrada, abortando task")
                return

            if not edicao.arquivo_video_cortado:
                edicao.status = "erro"
                edicao.erro_msg = "Vídeo cortado não disponível"
                db.commit()
                return

            # Carregar perfil da edição (fallback: IDIOMAS_ALVO se sem perfil)
            perfil = db.get(Perfil, edicao.perfil_id) if edicao.perfil_id else None
            idiomas_do_perfil = (perfil.idiomas_alvo or IDIOMAS_ALVO) if perfil else IDIOMAS_ALVO
            idiomas = idiomas_renderizar if idiomas_renderizar else idiomas_do_perfil

            # Idempotência: calcular idiomas faltantes
            ja_concluidos = {
                r.idioma for r in db.query(Render).filter(
                    Render.edicao_id == edicao_id,
                    Render.status == "concluido",
                ).all()
            }
            faltantes = [i for i in idiomas if i not in ja_concluidos]
            total = len(idiomas)
            concluidos = total - len(faltantes)

            # Se não há faltantes, marcar como concluído e sair
            if not faltantes:
                if is_preview:
                    edicao.status = "preview_pronto"
                    edicao.passo_atual = 8
                else:
                    edicao.status = "concluido"
                    edicao.passo_atual = 9
                edicao.erro_msg = None
                edicao.tentativas_requeue = 0
                db.commit()
                logger.info(f"[{edicao_id}] Todos os idiomas já renderizados, nada a fazer")
                return

            # Copiar dados necessários para variáveis locais (fora da sessão)
            arquivo_video = edicao.arquivo_video_cortado
            idioma_musica = edicao.idioma
            artista_val = edicao.artista
            musica_val = edicao.musica
            sem_lyrics_val = bool(edicao.sem_lyrics)
            r2_base_val = _get_r2_base(edicao)

            # Extrair campos do perfil antes de fechar a sessão
            if perfil:
                from types import SimpleNamespace as _SN
                perfil_data = _SN(
                    overlay_style=perfil.overlay_style,
                    lyrics_style=perfil.lyrics_style,
                    traducao_style=perfil.traducao_style,
                    overlay_max_chars_linha=perfil.overlay_max_chars_linha or OVERLAY_MAX_CHARS_LINHA,
                    lyrics_max_chars=perfil.lyrics_max_chars or LYRICS_MAX_CHARS,
                    traducao_max_chars=perfil.traducao_max_chars or TRADUCAO_MAX_CHARS,
                    video_width=perfil.video_width or 1080,
                    video_height=perfil.video_height or 1920,
                )
                r2_prefix_val = perfil.r2_prefix or "editor"
                video_width_val = perfil.video_width or 1080
                video_height_val = perfil.video_height or 1920
                font_file_r2_key_val = perfil.font_file_r2_key or None
            else:
                perfil_data = None
                r2_prefix_val = "editor"
                video_width_val = 1080
                video_height_val = 1920
                font_file_r2_key_val = None
            # Persistir r2_base se não estava setado
            if not edicao.r2_base and r2_base_val:
                edicao.r2_base = r2_base_val

            alinhamento = db.query(Alinhamento).filter(
                Alinhamento.edicao_id == edicao_id
            ).order_by(Alinhamento.id.desc()).first()
            lyrics_segs = alinhamento.segmentos_cortado if alinhamento else []

            dados_idiomas = {}
            for idioma in faltantes:
                overlay = db.query(Overlay).filter(
                    Overlay.edicao_id == edicao_id, Overlay.idioma == idioma
                ).first()
                if not overlay:
                    logger.error(
                        f"[{edicao_id}] Overlay não encontrado para idioma={idioma}. "
                        f"Reimporte o projeto do Redator."
                    )
                    falhas_pre = dados_idiomas.get("_falhas_pre", [])
                    falhas_pre.append(idioma)
                    dados_idiomas["_falhas_pre"] = falhas_pre
                    continue

                # Prioridade: segmentos_reindexado (pós aplicar-corte),
                # fallback: segmentos_original (congelado na importação)
                overlay_segs = overlay.segmentos_reindexado
                if not overlay_segs:
                    overlay_segs = overlay.segmentos_original
                if not overlay_segs:
                    logger.error(
                        f"[{edicao_id}] Overlay {idioma} existe mas sem segmentos. "
                        f"Reimporte o projeto."
                    )
                    falhas_pre = dados_idiomas.get("_falhas_pre", [])
                    falhas_pre.append(idioma)
                    dados_idiomas["_falhas_pre"] = falhas_pre
                    continue

                # Log explícito: texto exato do overlay que será renderizado
                overlay_textos = [s.get("text", "") for s in overlay_segs if s.get("text")]
                logger.info(
                    f"[{edicao_id}] OVERLAY RENDER {idioma}: "
                    f"{len(overlay_segs)} segmentos, textos={overlay_textos}"
                )

                traducao = db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == edicao_id,
                    TraducaoLetra.idioma == idioma,
                ).first()
                dados_idiomas[idioma] = {
                    "overlay_segs": overlay_segs,
                    "traducao_segs": traducao.segmentos if traducao else None,
                }

            # Remover idiomas sem overlay da lista de faltantes
            idiomas_sem_overlay = dados_idiomas.pop("_falhas_pre", [])
            if idiomas_sem_overlay:
                faltantes = [i for i in faltantes if i not in idiomas_sem_overlay]

            # Setar status e heartbeat inicial
            status_inicial = "preview" if is_preview else "renderizando"
            edicao.status = status_inicial
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "render": {
                    "etapa": "render",
                    "total": total,
                    "concluidos": concluidos,
                    "atual": None,
                    "erros": [],
                }
            }
            db.commit()

        # Registrar falhas de overlay ausente
        falhas = []
        if idiomas_sem_overlay:
            for idioma_falta in idiomas_sem_overlay:
                msg = f"{idioma_falta}: Overlay não encontrado — reimporte o projeto"
                falhas.append(msg)
                with SessionLocal() as db:
                    db.add(Render(
                        edicao_id=edicao_id, idioma=idioma_falta, tipo="9:16",
                        status="erro", erro_msg="Overlay não encontrado — reimporte o projeto",
                    ))
                    db.commit()

        # PASSO B — Loop de render (banco FECHADO durante FFmpeg)
        renders_ok = 0

        # Limpeza preventiva de /tmp: remover *.mp4 e *.ass residuais de execuções anteriores
        import glob as _glob
        for _tmp in _glob.glob("/tmp/*.mp4") + _glob.glob("/tmp/*.ass"):
            try:
                os.remove(_tmp)
                logger.info(f"[{edicao_id}] Limpeza preventiva: removido {_tmp}")
            except Exception:
                pass

        # Garantir que o vídeo cortado está disponível localmente (baixa do R2 se necessário)
        local_video = storage.ensure_local(arquivo_video)

        # Garantir fonte customizada disponível para o FFmpeg (se a marca tiver uma)
        if font_file_r2_key_val:
            try:
                from app.services.font_service import ensure_font_local as _ensure_font
                _ensure_font(font_file_r2_key_val)
                logger.info(f"[{edicao_id}] Fonte customizada carregada: {font_file_r2_key_val}")
            except BaseException as font_err:
                logger.warning(f"[{edicao_id}] Falha ao carregar fonte customizada ({font_file_r2_key_val}): {font_err} — usando fonte padrão")
                font_file_r2_key_val = None

        for idioma in faltantes:
            # Heartbeat antes de cada render (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "render": {
                            "etapa": "render",
                            "total": total,
                            "concluidos": concluidos,
                            "atual": idioma,
                            "erros": falhas,
                        }
                    }
                    db.commit()

            ass_path = None
            output_video = None
            try:
                # Verificar espaço em disco antes do FFmpeg (threshold: 200MB)
                _uso = shutil.disk_usage("/")
                _livre_mb = _uso.free / (1024 * 1024)
                if _livre_mb < 200:
                    # Tentar limpar lixo antes de desistir
                    for _f in _glob.glob("/tmp/*.mp4") + _glob.glob("/tmp/*.ass"):
                        try:
                            os.remove(_f)
                        except Exception:
                            pass
                    _uso = shutil.disk_usage("/")
                    _livre_mb = _uso.free / (1024 * 1024)
                    if _livre_mb < 200:
                        raise RuntimeError(f"Espaço em disco insuficiente: {_livre_mb:.0f}MB livre")
                    logger.info(f"[{edicao_id}] Limpeza de emergência liberou disco: {_livre_mb:.0f}MB livre")

                d = dados_idiomas[idioma]

                nome_render = _nome_arquivo_render(artista_val, musica_val, idioma)

                output_dir = _Path(STORAGE_PATH) / str(edicao_id) / "renders" / idioma
                output_dir.mkdir(parents=True, exist_ok=True)
                output_video = str(output_dir / nome_render)

                vw = video_width_val
                vh = video_height_val

                if sem_legendas:
                    # Sem legendas: só escalar/pad, sem ASS
                    cmd = (
                        f'ffmpeg -y -i "{local_video}" '
                        f'-vf "scale={vw}:{vh}:force_original_aspect_ratio=decrease,'
                        f'pad={vw}:{vh}:(ow-iw)/2:(oh-ih)/2:black" '
                        f'-c:v libx264 -preset medium -crf 23 '
                        f'-c:a aac -b:a 128k "{output_video}"'
                    )
                else:
                    # Gerar ASS (sync, rápido — banco já fechado)
                    ass_obj = gerar_ass(
                        overlay=d["overlay_segs"] or [],
                        lyrics=lyrics_segs or [],
                        traducao=d["traducao_segs"],
                        idioma_versao=idioma,
                        idioma_musica=idioma_musica,
                        sem_lyrics=sem_lyrics_val,
                        perfil=perfil_data,
                    )

                    ass_path = str(output_dir / f"legendas_{idioma}.ass")
                    ass_obj.save(ass_path)

                    # FFmpeg com timeout — banco FECHADO
                    ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
                    _fontsdir = "/usr/local/share/fonts/custom" if font_file_r2_key_val else None
                    _ass_filter = (
                        f"ass='{ass_escaped}':fontsdir={_fontsdir}"
                        if _fontsdir else
                        f"ass='{ass_escaped}'"
                    )
                    cmd = (
                        f'ffmpeg -y -i "{local_video}" '
                        f'-vf "scale={vw}:{vh}:force_original_aspect_ratio=decrease,'
                        f'pad={vw}:{vh}:(ow-iw)/2:(oh-ih)/2:black,'
                        f'{_ass_filter}" '
                        f'-c:v libx264 -preset medium -crf 23 '
                        f'-c:a aac -b:a 128k "{output_video}"'
                    )
                processo = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    _, stderr_out = await asyncio.wait_for(processo.communicate(), timeout=600)
                except asyncio.TimeoutError:
                    processo.kill()
                    await processo.wait()
                    raise

                if processo.returncode != 0:
                    raise Exception(f"FFmpeg falhou: {stderr_out.decode()[-1000:]}")

                tamanho = _Path(output_video).stat().st_size

                # 4. Upload render para R2
                arquivo_render = output_video  # fallback: path local (sem R2)
                if r2_base_val:
                    r2_key = f"{r2_prefix_val}/{r2_base_val}/{idioma}/{nome_render}"
                    try:
                        storage.upload_file(output_video, r2_key)
                        arquivo_render = r2_key
                    except Exception as upload_err:
                        logger.warning(
                            f"[{edicao_id}] Upload R2 render {idioma} falhou: {upload_err}, "
                            f"mantendo path local"
                        )

                # 5. Cleanup: deletar vídeo local (liberar disco antes do próximo idioma)
                # REGRA: nunca 2 vídeos renderizados no disco ao mesmo tempo
                try:
                    _Path(output_video).unlink(missing_ok=True)
                    logger.info(f"[{edicao_id}] Vídeo local deletado: {output_video}")
                except Exception as cleanup_err:
                    logger.warning(f"[{edicao_id}] Falha ao deletar vídeo local {output_video}: {cleanup_err}")

                # 6. Cleanup: deletar ASS temporário
                if ass_path:
                    try:
                        _Path(ass_path).unlink(missing_ok=True)
                    except Exception as cleanup_err:
                        logger.warning(f"[{edicao_id}] Falha ao deletar ASS {ass_path}: {cleanup_err}")

                # 7. Salvar resultado — upsert (sessão curta)
                with SessionLocal() as db:
                    existing_render = db.query(Render).filter(
                        Render.edicao_id == edicao_id, Render.idioma == idioma
                    ).first()
                    if existing_render:
                        existing_render.tipo = "9:16"
                        existing_render.arquivo = arquivo_render
                        existing_render.tamanho_bytes = tamanho
                        existing_render.status = "concluido"
                        existing_render.erro_msg = None
                    else:
                        db.add(Render(
                            edicao_id=edicao_id,
                            idioma=idioma,
                            tipo="9:16",
                            arquivo=arquivo_render,
                            tamanho_bytes=tamanho,
                            status="concluido",
                        ))
                    db.commit()

                renders_ok += 1
                concluidos += 1
                logger.info(f"[{edicao_id}] Render {idioma} OK ({concluidos}/{total})")

            except asyncio.TimeoutError:
                falhas.append(f"{idioma}: timeout (600s)")
                logger.warning(f"[{edicao_id}] Render {idioma} timeout após 600s")
                # Cleanup de arquivos temporários em caso de timeout
                for tmp_file in [output_video, ass_path]:
                    if tmp_file:
                        try:
                            _Path(tmp_file).unlink(missing_ok=True)
                        except Exception as cleanup_err:
                            logger.warning(f"[{edicao_id}] Falha ao limpar {tmp_file}: {cleanup_err}")
                with SessionLocal() as db:
                    db.add(Render(
                        edicao_id=edicao_id, idioma=idioma, tipo="9:16",
                        status="erro", erro_msg="timeout (600s)",
                    ))
                    db.commit()
            except Exception as e:
                falhas.append(f"{idioma}: {str(e)[:200]}")
                logger.warning(f"[{edicao_id}] Render {idioma} falhou: {e}")
                # Cleanup de arquivos temporários em caso de erro
                for tmp_file in [output_video, ass_path]:
                    if tmp_file:
                        try:
                            _Path(tmp_file).unlink(missing_ok=True)
                        except Exception as cleanup_err:
                            logger.warning(f"[{edicao_id}] Falha ao limpar {tmp_file}: {cleanup_err}")
                with SessionLocal() as db:
                    db.add(Render(
                        edicao_id=edicao_id, idioma=idioma, tipo="9:16",
                        status="erro", erro_msg=str(e)[:500],
                    ))
                    db.commit()

        # PASSO C — Finalização (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "render": {
                        "etapa": "render",
                        "total": total,
                        "concluidos": concluidos,
                        "atual": None,
                        "erros": falhas,
                    }
                }
                if renders_ok > 0:
                    if is_preview:
                        edicao.status = "preview_pronto"
                        edicao.passo_atual = 8
                    else:
                        edicao.status = "concluido"
                        edicao.passo_atual = 9
                    edicao.tentativas_requeue = 0
                    edicao.erro_msg = (
                        f"Renders com falha ({len(falhas)}): {'; '.join(falhas)}"
                        if falhas else None
                    )
                else:
                    edicao.status = "erro"
                    edicao.erro_msg = f"Nenhum render concluído. Falhas: {'; '.join(falhas)}"
                db.commit()

                if not is_preview and renders_ok > 0:
                    _exportar_renders(edicao, db)

        logger.info(f"[{edicao_id}] _render_task concluída: {renders_ok} OK, {len(falhas)} falhas")

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        else:
            _capture_sentry(e, edicao_id, "render")
            erro_msg = f"Erro inesperado: {str(e)[:500]}"
        logger.error(f"[{edicao_id}] _render_task erro inesperado: {e}", exc_info=True)
        try:
            from app.database import SessionLocal
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = erro_msg
                    db.commit()
        except Exception:
            logger.error(f"[{edicao_id}] Não conseguiu salvar erro no banco")
        if isinstance(e, asyncio.CancelledError):
            raise


class AprovarPreviewParams(BaseModel):
    aprovado: bool
    notas_revisao: Optional[str] = None


# --- Preview: Renderizar 1 vídeo para aprovação ---
@router.post("/edicoes/{edicao_id}/renderizar-preview")
async def renderizar_preview(edicao_id: int, sem_legendas: bool = False):
    from app.database import SessionLocal
    from app.worker import task_queue, _make_preview_wrapper

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        # Idioma do preview: usa perfil.idioma_preview se disponível, senão "pt"
        _perfil_prev = db.get(Perfil, edicao.perfil_id) if edicao.perfil_id else None
        if _perfil_prev and _perfil_prev.idioma_preview:
            idioma_preview = _perfil_prev.idioma_preview if edicao.idioma != _perfil_prev.idioma_preview else edicao.idioma
        else:
            idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma

        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_PREVIEW))
            .values(status="preview", task_heartbeat=None, progresso_detalhe={})
        )
        db.commit()

        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar preview")

    task_queue.put_nowait((_make_preview_wrapper(edicao_id, idioma_preview, sem_legendas=sem_legendas), edicao_id))
    return {"status": "preview iniciado", "idioma": idioma_preview, "sem_legendas": sem_legendas}


@router.post("/edicoes/{edicao_id}/aprovar-preview")
async def aprovar_preview(edicao_id: int, body: AprovarPreviewParams, sem_legendas: bool = False):
    from app.database import SessionLocal
    from app.worker import task_queue

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        if body.aprovado:
            # Determinar idioma do preview e idiomas restantes (mesma lógica de renderizar-preview)
            _perfil_apr = db.get(Perfil, edicao.perfil_id) if edicao.perfil_id else None
            _idiomas_apr = (_perfil_apr.idiomas_alvo or IDIOMAS_ALVO) if _perfil_apr else IDIOMAS_ALVO
            if _perfil_apr and _perfil_apr.idioma_preview:
                idioma_preview = _perfil_apr.idioma_preview if edicao.idioma != _perfil_apr.idioma_preview else edicao.idioma
            else:
                idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
            idiomas_renderizar = [i for i in _idiomas_apr if i != idioma_preview]

            # Check-and-set atômico: só aceitar se preview_pronto
            result = db.execute(
                update(Edicao)
                .where(Edicao.id == edicao_id, Edicao.status == "preview_pronto")
                .values(status="renderizando", notas_revisao=None,
                        task_heartbeat=None, progresso_detalhe={})
            )
            db.commit()

            if result.rowcount == 0:
                db.refresh(edicao)
                raise HTTPException(409, f"Status atual '{edicao.status}' não permite aprovar preview")

        else:
            edicao.status = "revisao"
            edicao.notas_revisao = body.notas_revisao
            db.commit()
            return {"status": "revisão solicitada", "notas": body.notas_revisao}

    # Enfileirar render dos idiomas restantes (fora da sessão de banco)
    if body.aprovado:
        _sem = sem_legendas
        async def _render_remaining(_eid: int):
            await _render_task(_eid, idiomas_renderizar=idiomas_renderizar, sem_legendas=_sem)

        task_queue.put_nowait((_render_remaining, edicao_id))
        return {"status": "renderização dos demais idiomas iniciada", "idiomas": idiomas_renderizar}


# --- Re-render individual por idioma ---
_STATUS_PERMITIDOS_RERENDER = {"concluido", "preview_pronto", "erro"}


@router.post("/edicoes/{edicao_id}/re-renderizar/{idioma}")
async def re_renderizar_idioma(edicao_id: int, idioma: str):
    """Re-renderiza um único idioma sem refazer todos os demais.

    Deleta o render anterior e enfileira render só desse idioma.
    Status da edição deve ser 'concluido', 'preview_pronto' ou 'erro'.
    """
    from app.database import SessionLocal
    from app.worker import task_queue

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        # Validar idioma contra perfil ou IDIOMAS_ALVO
        perfil_re = db.get(Perfil, edicao.perfil_id) if edicao.perfil_id else None
        idiomas_validos = (perfil_re.idiomas_alvo or IDIOMAS_ALVO) if perfil_re else IDIOMAS_ALVO
        if idioma not in idiomas_validos:
            raise HTTPException(400, f"Idioma '{idioma}' não está nos idiomas válidos: {idiomas_validos}")

        # Check-and-set atômico
        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_RERENDER))
            .values(
                status="renderizando",
                task_heartbeat=None,
                progresso_detalhe={"re_render": {"idioma": idioma, "status": "em_andamento"}},
            )
        )
        db.commit()

        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite re-renderizar")

        status_anterior = edicao.status

        # Deletar render anterior
        render_existente = db.query(Render).filter(
            Render.edicao_id == edicao_id, Render.idioma == idioma
        ).first()
        if render_existente:
            db.delete(render_existente)
            db.commit()

    async def _re_render_wrapper(_eid: int):
        await _render_task(_eid, idiomas_renderizar=[idioma])
        # Restaurar status anterior se render concluir com sucesso
        from app.database import SessionLocal as _SL
        with _SL() as _db:
            _edicao = _db.get(Edicao, _eid)
            if _edicao and _edicao.status == "concluido" and status_anterior == "preview_pronto":
                _edicao.status = "preview_pronto"
                _db.commit()

    task_queue.put_nowait((_re_render_wrapper, edicao_id))
    return {"status": "re-render enfileirado", "idioma": idioma}


# --- Re-tradução individual por idioma ---
_STATUS_PERMITIDOS_RETRAD = {"montagem", "preview_pronto", "concluido", "erro"}


@router.post("/edicoes/{edicao_id}/re-traduzir/{idioma}")
async def re_traduzir_idioma(edicao_id: int, idioma: str):
    """Re-traduz um único idioma sem refazer os demais.

    Deleta a tradução anterior e enfileira tradução só desse idioma.
    """
    from app.database import SessionLocal
    from app.worker import task_queue

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        # Validar idioma
        perfil_ret = db.get(Perfil, edicao.perfil_id) if edicao.perfil_id else None
        idiomas_validos = (perfil_ret.idiomas_alvo or IDIOMAS_ALVO) if perfil_ret else IDIOMAS_ALVO
        if idioma not in idiomas_validos:
            raise HTTPException(400, f"Idioma '{idioma}' não está nos idiomas válidos: {idiomas_validos}")

        # Check-and-set atômico
        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_RETRAD))
            .values(
                status="traducao",
                task_heartbeat=None,
                progresso_detalhe={"re_traducao": {"idioma": idioma, "status": "em_andamento"}},
            )
        )
        db.commit()

        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite re-traduzir")

        status_anterior = edicao.status

        # Deletar tradução anterior
        trad_existente = db.query(TraducaoLetra).filter(
            TraducaoLetra.edicao_id == edicao_id, TraducaoLetra.idioma == idioma
        ).first()
        if trad_existente:
            db.delete(trad_existente)
            db.commit()

    async def _re_trad_wrapper(_eid: int):
        """Traduz apenas o idioma alvo e restaura o status anterior."""
        try:
            from app.database import SessionLocal as _SL
            from app.services.translate_service import traduzir_letra_cloud as _traduzir

            with _SL() as _db:
                _edicao = _db.get(Edicao, _eid)
                if not _edicao:
                    return
                _alin = _db.query(Alinhamento).filter(
                    Alinhamento.edicao_id == _eid
                ).order_by(Alinhamento.id.desc()).first()
                if not _alin or not _alin.segmentos_cortado:
                    _edicao.status = "erro"
                    _edicao.erro_msg = "Alinhamento não encontrado para re-tradução"
                    _db.commit()
                    return
                segmentos = _alin.segmentos_cortado
                idioma_origem = _edicao.idioma
                metadados = {"musica": _edicao.musica, "compositor": _edicao.compositor}
                _edicao.task_heartbeat = datetime.now(timezone.utc)
                _db.commit()

            resultado = await asyncio.wait_for(
                _traduzir(segmentos, idioma_origem, idioma, metadados),
                timeout=180,
            )

            with _SL() as _db:
                existing = _db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == _eid, TraducaoLetra.idioma == idioma
                ).first()
                if existing:
                    existing.segmentos = resultado
                else:
                    _db.add(TraducaoLetra(edicao_id=_eid, idioma=idioma, segmentos=resultado))
                _edicao = _db.get(Edicao, _eid)
                if _edicao:
                    _edicao.status = status_anterior
                    _edicao.erro_msg = None
                    _edicao.task_heartbeat = datetime.now(timezone.utc)
                    _edicao.progresso_detalhe = {"re_traducao": {"idioma": idioma, "status": "concluido"}}
                _db.commit()

            logger.info(f"[{_eid}] Re-tradução {idioma} OK → status={status_anterior}")

        except BaseException as exc:
            if isinstance(exc, asyncio.CancelledError):
                raise
            logger.error(f"[{_eid}] Re-tradução {idioma} falhou: {exc}", exc_info=True)
            try:
                from app.database import SessionLocal as _SL2
                with _SL2() as _db2:
                    _e = _db2.get(Edicao, _eid)
                    if _e:
                        _e.status = "erro"
                        _e.erro_msg = f"Re-tradução {idioma} falhou: {str(exc)[:300]}"
                        _db2.commit()
            except Exception:
                pass

    task_queue.put_nowait((_re_trad_wrapper, edicao_id))
    return {"status": "re-tradução enfileirada", "idioma": idioma}


def _exportar_renders(edicao, db):
    """Copia renders concluídos para EXPORT_PATH/{Artista - Música}/."""
    if not EXPORT_PATH:
        return
    export_base = FilePath(EXPORT_PATH)
    if not export_base.exists():
        logger.warning(f"EXPORT_PATH não existe: {EXPORT_PATH}")
        return

    pasta_projeto = export_base / f"{edicao.artista} - {edicao.musica}"
    pasta_projeto.mkdir(parents=True, exist_ok=True)

    renders = db.query(Render).filter(
        Render.edicao_id == edicao.id, Render.status == "concluido"
    ).all()

    for render in renders:
        if not render.arquivo:
            continue
        try:
            local_file = storage.ensure_local(render.arquivo)
            nome_video = _nome_arquivo_render(edicao.artista, edicao.musica, render.idioma)
            destino = pasta_projeto / nome_video
            shutil.copy2(local_file, str(destino))
            logger.info(f"Exportado: {destino}")
        except Exception as e:
            logger.warning(f"Erro ao exportar {render.idioma}: {e}")

    # Incluir textos do Redator (do R2, na estrutura {r2_prefix}/{base}/{base} - {IDIOMA}/)
    r2_base = _get_r2_base(edicao)
    _pfx = _get_perfil_r2_prefix(edicao, db)
    if r2_base:
        for idioma_dir in IDIOMAS_ALVO:
            lp = lang_prefix(r2_base, idioma_dir)
            prefix_path = f"{_pfx}/{lp}" if _pfx else lp
            for filename in ["post.txt", "subtitles.srt", "youtube.txt"]:
                r2_key = f"{prefix_path}/{filename}"
                if storage.exists(r2_key):
                    try:
                        local_file = storage.ensure_local(r2_key)
                        lang_dir = pasta_projeto / idioma_dir
                        lang_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(local_file, str(lang_dir / filename))
                    except Exception as e:
                        logger.warning(f"Erro ao exportar texto {r2_key}: {e}")


@router.post("/edicoes/{edicao_id}/exportar")
def exportar_renders(edicao_id: int, db: Session = Depends(get_db)):
    """Exporta renders para EXPORT_PATH manualmente."""
    if not EXPORT_PATH:
        raise HTTPException(400, "EXPORT_PATH não configurado. Defina a variável de ambiente.")
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    _exportar_renders(edicao, db)

    pasta = FilePath(EXPORT_PATH) / f"{edicao.artista} - {edicao.musica}"
    arquivos = list(pasta.glob("*.mp4")) if pasta.exists() else []
    return {
        "pasta": str(pasta),
        "arquivos_exportados": len(arquivos),
        "nomes": [f.name for f in arquivos],
    }


# --- Passo 9: Pacote final assíncrono (renders + textos do Redator) ---

def _set_pacote_status(edicao_id: int, status: str, url: str = None, erro: str = None, r2_key: str = None):
    """Persiste status do pacote no campo progresso_detalhe da edição."""
    from app.database import SessionLocal
    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if edicao:
            edicao.progresso_detalhe = {
                "pacote": {
                    "etapa": "pacote",
                    "status": status,
                    "url": url,
                    "erro": erro,
                    "r2_key": r2_key,
                }
            }
            db.commit()


def _get_pacote_status(edicao_id: int, db: Session) -> dict:
    """Lê status do pacote do campo progresso_detalhe (namespace 'pacote', compat. formato antigo)."""
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        return {"status": "nenhum", "url": None, "erro": None}
    p = edicao.progresso_detalhe
    if not isinstance(p, dict):
        return {"status": "nenhum", "url": None, "erro": None}
    # Novo formato: {"pacote": {...}}
    if "pacote" in p:
        inner = p["pacote"]
        return {
            "status": inner.get("status", "nenhum"),
            "url": inner.get("url"),
            "erro": inner.get("erro"),
            "r2_key": inner.get("r2_key"),
        }
    # Formato antigo (compat. retroativa): {"etapa": "pacote", ...}
    if p.get("etapa") == "pacote":
        return {
            "status": p.get("status", "nenhum"),
            "url": p.get("url"),
            "erro": p.get("erro"),
            "r2_key": p.get("r2_key"),
        }
    return {"status": "nenhum", "url": None, "erro": None}


async def _pacote_task(edicao_id: int):
    """Task assíncrona no worker que gera o ZIP e faz upload pro R2."""
    try:
        import zipfile
        import tempfile
        from app.database import SessionLocal

        logger.info(f"[pacote_task] INÍCIO edicao_id={edicao_id}")
        _set_pacote_status(edicao_id, "gerando")

        # PASSO A — Ler estado (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                _set_pacote_status(edicao_id, "erro", erro="Edição não encontrada")
                return

            slug = f"{edicao.artista} - {edicao.musica}"
            r2_base = _get_r2_base(edicao)
            _pfx = _get_perfil_r2_prefix(edicao, db)
            artista = edicao.artista
            musica = edicao.musica
            edicao.task_heartbeat = datetime.now(timezone.utc)
            db.commit()

            renders = db.query(Render).filter(
                Render.edicao_id == edicao_id, Render.status == "concluido"
            ).all()
            render_data = [(r.arquivo, r.idioma) for r in renders if r.arquivo]

        # Heartbeat antes da operação pesada (banco FECHADO)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.task_heartbeat = datetime.now(timezone.utc)
                db.commit()

        # PASSO B — Gerar ZIP e upload (banco FECHADO durante I/O pesado)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for arquivo, idioma in render_data:
                    try:
                        local_file = storage.ensure_local(arquivo)
                        nome_video = _nome_arquivo_render(artista, musica, idioma)
                        arcname = f"{slug}/{idioma}/{nome_video}"
                        zf.write(local_file, arcname)
                        logger.info(f"[pacote] Incluído render {idioma}")
                    except Exception as e:
                        logger.warning(f"Pacote: não conseguiu incluir render {idioma}: {e}")

                if r2_base:
                    for idioma_dir in IDIOMAS_ALVO:
                        lp = lang_prefix(r2_base, idioma_dir)
                        prefix_path = f"{_pfx}/{lp}" if _pfx else lp
                        for filename in ["post.txt", "subtitles.srt", "youtube.txt"]:
                            r2_key = f"{prefix_path}/{filename}"
                            if storage.exists(r2_key):
                                try:
                                    local_file = storage.ensure_local(r2_key)
                                    arcname = f"{slug}/{idioma_dir}/{filename}"
                                    zf.write(local_file, arcname)
                                except Exception as e:
                                    logger.warning(f"Pacote: falha ao incluir {r2_key}: {e}")

            # Upload ZIP para R2
            full_base_zip = f"{_pfx}/{r2_base}" if _pfx and r2_base else r2_base
            r2_key = f"{full_base_zip}/export/pacote.zip" if full_base_zip else f"exports/{edicao_id}/pacote.zip"
            storage.upload_file(tmp_path, r2_key)
            logger.info(f"[pacote] ZIP uploaded to R2: {r2_key}")

            # Gerar URL presigned para download direto
            download_url = storage.get_presigned_url(r2_key, expires_in=7200)

            _set_pacote_status(edicao_id, "pronto", url=download_url, r2_key=r2_key)
            logger.info(f"[pacote] Pacote pronto para edicao_id={edicao_id}")

        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        logger.info(f"[pacote_task] FINALIZOU edicao_id={edicao_id}")

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            _set_pacote_status(edicao_id, "erro", erro="Interrompido por reinício do servidor")
            raise
        _capture_sentry(e, edicao_id, "pacote")
        logger.error(f"[pacote_task] Erro edicao_id={edicao_id}: {e}", exc_info=True)
        _set_pacote_status(edicao_id, "erro", erro=str(e)[:500])


@router.post("/edicoes/{edicao_id}/pacote")
async def iniciar_pacote(edicao_id: int, db: Session = Depends(get_db)):
    """Inicia geração do pacote ZIP via worker sequencial. Retorna imediatamente.
    Use GET /pacote/status para acompanhar."""
    from app.worker import task_queue

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Check-and-set atômico: não enfileirar se já está gerando
    current = _get_pacote_status(edicao_id, db)
    if current["status"] == "gerando":
        return {"status": "gerando_pacote", "mensagem": "Pacote já está sendo gerado"}

    _set_pacote_status(edicao_id, "gerando")
    task_queue.put_nowait((_pacote_task, edicao_id))
    logger.info(f"[pacote] Enfileirado edicao_id={edicao_id} queue={task_queue.qsize()}")

    return {"status": "gerando_pacote", "mensagem": "Geração do pacote iniciada"}


@router.get("/edicoes/{edicao_id}/pacote/status")
def status_pacote(edicao_id: int, db: Session = Depends(get_db)):
    """Retorna status da geração do pacote ZIP."""
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    return _get_pacote_status(edicao_id, db)


@router.get("/edicoes/{edicao_id}/pacote/download")
def download_pacote(edicao_id: int, db: Session = Depends(get_db)):
    """Download direto do pacote ZIP (baixa do R2 e serve via FileResponse)."""
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    status = _get_pacote_status(edicao_id, db)
    if status["status"] != "pronto":
        raise HTTPException(404, "Pacote não está pronto para download")

    r2_key = status.get("r2_key")
    if not r2_key:
        # Fallback: tentar reconstruir key
        r2_base = _get_r2_base(edicao)
        _pfx = _get_perfil_r2_prefix(edicao, db)
        full_base_zip = f"{_pfx}/{r2_base}" if _pfx and r2_base else r2_base
        r2_key = f"{full_base_zip}/export/pacote.zip" if full_base_zip else f"exports/{edicao_id}/pacote.zip"

    try:
        local_path = storage.ensure_local(r2_key)
    except FileNotFoundError:
        raise HTTPException(404, "Arquivo do pacote não encontrado no storage. Gere novamente.")

    slug = _sanitize_filename(f"{edicao.artista} - {edicao.musica}")
    return FileResponse(
        path=local_path,
        media_type="application/zip",
        filename=f"{slug}.zip",
    )


@router.get("/edicoes/{edicao_id}/renders")
def listar_renders(edicao_id: int, db: Session = Depends(get_db)):
    renders = db.query(Render).filter(Render.edicao_id == edicao_id).all()
    return [
        {
            "id": r.id,
            "idioma": r.idioma,
            "tipo": r.tipo,
            "arquivo": r.arquivo,
            "tamanho_bytes": r.tamanho_bytes,
            "status": r.status,
            "erro_msg": r.erro_msg,
        }
        for r in renders
    ]


@router.get("/edicoes/{edicao_id}/renders/{render_id}/download")
def download_render(edicao_id: int, render_id: int, db: Session = Depends(get_db)):
    render = db.query(Render).filter(
        Render.id == render_id, Render.edicao_id == edicao_id
    ).first()
    if not render:
        raise HTTPException(404, "Render não encontrado")
    if render.status != "concluido" or not render.arquivo:
        raise HTTPException(400, "Render não está disponível para download")

    try:
        local_path = storage.ensure_local(render.arquivo)
    except FileNotFoundError:
        raise HTTPException(
            404,
            "Arquivo não encontrado no storage. Re-renderize para gerar novamente."
        )

    edicao = db.get(Edicao, edicao_id)
    filename = _nome_arquivo_render(edicao.artista, edicao.musica, render.idioma) if edicao else FilePath(local_path).name

    return FileResponse(
        path=local_path,
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/edicoes/{edicao_id}/audio")
def servir_audio(edicao_id: int, db: Session = Depends(get_db)):
    """Serve o arquivo de áudio completo (OGG/Opus) para player HTML5."""
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    if not edicao.arquivo_audio_completo:
        raise HTTPException(404, "Áudio não disponível. Execute a transcrição primeiro.")
    try:
        local_path = storage.ensure_local(edicao.arquivo_audio_completo)
    except FileNotFoundError:
        raise HTTPException(404, "Arquivo de áudio não encontrado no storage.")
    return FileResponse(
        path=local_path,
        media_type="audio/ogg",
        filename=f"{edicao.artista} - {edicao.musica}.ogg",
    )


@router.get("/edicoes/{edicao_id}/video/status")
def status_video(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    return {
        "video_completo": edicao.arquivo_video_completo,
        "video_cortado": edicao.arquivo_video_cortado,
        "audio_completo": edicao.arquivo_audio_completo,
        "duracao_total": edicao.duracao_total_sec,
        "status": edicao.status,
    }


@router.get("/edicoes/{edicao_id}/corte")
def info_corte(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    return {
        "janela_inicio_sec": edicao.janela_inicio_sec,
        "janela_fim_sec": edicao.janela_fim_sec,
        "duracao_corte_sec": edicao.duracao_corte_sec,
    }


@router.get("/edicoes/{edicao_id}/traducao-lyrics")
def obter_traducoes(edicao_id: int, db: Session = Depends(get_db)):
    traducoes = db.query(TraducaoLetra).filter(
        TraducaoLetra.edicao_id == edicao_id
    ).all()
    return [
        {"idioma": t.idioma, "segmentos": t.segmentos}
        for t in traducoes
    ]


# --- Fila / Worker ---

_STALE_THRESHOLD = timedelta(minutes=5)
_ACTIVE_STATUSES = {"baixando", "letra", "transcricao", "alinhamento", "corte", "traducao", "montagem", "preview", "renderizando"}


@router.get("/fila/status")
async def fila_status():
    """Verifica se o worker está ocupado processando alguma edição."""
    from app.worker import is_worker_busy
    return is_worker_busy()


@router.post("/edicoes/{edicao_id}/desbloquear")
async def desbloquear_edicao(edicao_id: int, force: bool = False):
    """Recovery manual: infere o status correto e desbloqueia uma edição travada.

    Só permitido se:
    - force=true (ignora check de heartbeat), OU
    - status == "erro", OU
    - status é um status ativo E o heartbeat está stale (> 5 min / NULL)

    Retorna 409 se a edição está em processamento ativo (e force=false).
    """
    from app.database import SessionLocal

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        is_erro = edicao.status == "erro"
        is_active = edicao.status in _ACTIVE_STATUSES

        # Verificar se heartbeat está stale
        hb = edicao.task_heartbeat
        if hb is not None and hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        is_stale = hb is None or (datetime.now(timezone.utc) - hb) > _STALE_THRESHOLD

        if not force and not is_erro and not (is_active and is_stale):
            raise HTTPException(
                409,
                f"Edição não pode ser desbloqueada: status='{edicao.status}'"
                + (" (processamento ativo)" if is_active and not is_stale else ""),
            )

        # Consultar dados reais do banco para inferir status correto
        n_renders = db.query(Render).filter(
            Render.edicao_id == edicao_id,
            Render.status == "concluido",
        ).count()
        n_traducoes = db.query(TraducaoLetra).filter(
            TraducaoLetra.edicao_id == edicao_id
        ).count()
        alinhamento = db.query(Alinhamento).filter(
            Alinhamento.edicao_id == edicao_id,
        ).first()
        tem_alinhamento_validado = bool(alinhamento and alinhamento.validado)
        tem_corte = bool(edicao.arquivo_video_cortado)

        # Verificar se existe letra aprovada para esta edição
        from app.models import Letra
        tem_letra = bool(db.query(Letra).filter(
            Letra.musica == edicao.musica,
            Letra.idioma == edicao.idioma,
        ).first())

        tem_video = bool(
            edicao.arquivo_video_completo
            and storage.exists(edicao.arquivo_video_completo)
        )

        # Inferir status do mais avançado para o mais básico
        if n_renders > 0:
            novo_status = "preview_pronto"
            base = "renders"
        elif n_traducoes > 0:
            novo_status = "montagem"
            base = "traducoes"
        elif tem_corte:
            novo_status = "montagem"
            base = "corte_existente"
        elif tem_alinhamento_validado:
            novo_status = "corte"
            base = "alinhamento_validado"
        elif tem_letra:
            novo_status = "transcricao"
            base = "letra_aprovada"
        elif tem_video:
            novo_status = "letra"
            base = "video_r2"
        else:
            novo_status = "aguardando"
            base = "nenhum_dado"

        edicao.status = novo_status
        edicao.erro_msg = None
        edicao.progresso_detalhe = {}
        edicao.tentativas_requeue = 0
        db.commit()

    logger.info(
        f"[desbloquear] edicao_id={edicao_id} inferido status='{novo_status}' "
        f"baseado em: renders={n_renders}, traducoes={n_traducoes}, "
        f"alinhamento={'validado' if tem_alinhamento_validado else ('existe' if alinhamento else 'nao')}, "
        f"corte={'sim' if tem_corte else 'nao'}, letra={'sim' if tem_letra else 'nao'}, "
        f"video={'sim' if tem_video else 'nao'} → razao={base}"
        f"{', force=True' if force else ''}"
    )
    return {
        "novo_status": novo_status,
        "razao": base,
        "renders_concluidos": n_renders,
        "traducoes": n_traducoes,
        "alinhamento_validado": tem_alinhamento_validado,
        "tem_corte": tem_corte,
        "tem_letra": tem_letra,
        "tem_video": tem_video,
    }


# --- Limpar Edição ---

_STATUS_PROTEGIDOS_LIMPAR = {"concluido", "preview_pronto"}
_STATUS_PROCESSANDO_LIMPAR = {"traducao", "renderizando", "preview"}


def _limpar_edicao_dados(db: Session, edicao_id: int) -> None:
    """Deleta traduções, renders (+ R2) e reseta campos da edição para 'aguardando'.

    Reutilizável — não faz validação de status nem commit.
    O chamador deve validar status antes e fazer db.commit() depois.
    """
    # 1. Deletar renders (e arquivos do R2)
    renders = db.query(Render).filter(Render.edicao_id == edicao_id).all()
    for r in renders:
        if r.arquivo:
            try:
                storage.delete(r.arquivo)
            except Exception:
                logger.warning(f"[limpar] Falha ao deletar R2: {r.arquivo}")
        db.delete(r)

    # 2. Deletar traduções
    db.query(TraducaoLetra).filter(TraducaoLetra.edicao_id == edicao_id).delete()

    # 3. Resetar campos da edição
    edicao = db.get(Edicao, edicao_id)
    if edicao:
        edicao.status = "aguardando"
        edicao.passo_atual = 1
        edicao.erro_msg = None
        edicao.task_heartbeat = None
        edicao.progresso_detalhe = {}
        edicao.arquivo_video_cortado = None
        edicao.arquivo_audio_completo = None
        edicao.rota_alinhamento = None
        edicao.confianca_alinhamento = None
        edicao.notas_revisao = None
        edicao.tentativas_requeue = 0


@router.post("/edicoes/{edicao_id}/limpar-edicao")
async def limpar_edicao(edicao_id: int):
    """Reseta uma edição travada para 'aguardando', apagando todo o progresso intermediário.

    Protege edições concluídas e edições com processamento ativo recente.
    """
    from app.database import SessionLocal

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        # Status protegidos nunca podem ser limpos
        if edicao.status in _STATUS_PROTEGIDOS_LIMPAR:
            raise HTTPException(
                400,
                f"Edição com status '{edicao.status}' não pode ser limpa.",
            )

        # Se está processando E heartbeat é recente (< 5 min), bloquear
        if edicao.status in _STATUS_PROCESSANDO_LIMPAR:
            hb = edicao.task_heartbeat
            if hb is not None:
                if hb.tzinfo is None:
                    hb = hb.replace(tzinfo=timezone.utc)
                if (datetime.now(timezone.utc) - hb) < _STALE_THRESHOLD:
                    raise HTTPException(
                        409,
                        "Edição está sendo processada agora. Aguarde terminar ou use Desbloquear primeiro.",
                    )

        _limpar_edicao_dados(db, edicao_id)
        db.commit()

    logger.info(f"[limpar] edicao_id={edicao_id} limpa com sucesso → status='aguardando'")
    return {"status": "ok", "mensagem": "Edição limpa com sucesso"}
