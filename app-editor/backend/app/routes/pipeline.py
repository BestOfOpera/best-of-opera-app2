"""Rotas do pipeline de edição (passos 1-9)."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path as FilePath
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)
from app.models import Edicao, Overlay, Alinhamento, TraducaoLetra, Render
from app.schemas import AlinhamentoOut, AlinhamentoValidar, LetraAprovar
from app.services.youtube import download_video
from app.services.ffmpeg_service import extrair_audio_completo, cortar_na_janela_overlay
from app.services.gemini import buscar_letra as gemini_buscar_letra, transcrever_guiado_completo, transcrever_cego, mapear_estrutura_audio, completar_transcricao, _detect_mime_type, _get_client
from app.services.genius import buscar_letra_genius
from app.services.alinhamento import alinhar_letra_com_timestamps, merge_transcricoes
from app.services.regua import extrair_janela_do_overlay, reindexar_timestamps, recortar_lyrics_na_janela, normalizar_segmentos
import os
import shutil
from app.config import STORAGE_PATH, IDIOMAS_ALVO, EXPORT_PATH, REDATOR_API_URL
from shared.storage_service import storage, lang_prefix, check_conflict, save_youtube_marker

router = APIRouter(prefix="/api/v1/editor", tags=["pipeline"])


def _get_r2_base(edicao) -> str:
    """Retorna r2_base da edição, computando se necessário."""
    if edicao.r2_base:
        return edicao.r2_base
    from shared.storage_service import project_base
    return project_base(edicao.artista, edicao.musica)


class CorteParams(BaseModel):
    janela_inicio: Optional[float] = None
    janela_fim: Optional[float] = None


# --- Passo 1: Garantir vídeo ---
@router.post("/edicoes/{edicao_id}/garantir-video")
async def garantir_video(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if edicao.arquivo_video_completo and storage.exists(edicao.arquivo_video_completo):
        return {"status": "já disponível", "arquivo": edicao.arquivo_video_completo}

    edicao.status = "baixando"
    edicao.passo_atual = 1
    db.commit()

    background_tasks.add_task(_download_video_task, edicao_id, edicao.youtube_url)
    return {"status": "download iniciado"}


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

    # Upload para R2: {Artista} - {Musica}/video/original.mp4
    base = check_conflict(edicao.artista, edicao.musica, edicao.youtube_video_id or "")
    r2_key = f"{base}/video/original.mp4"
    storage.upload_file(local_path, r2_key)
    if edicao.youtube_video_id:
        save_youtube_marker(base, edicao.youtube_video_id)

    edicao.arquivo_video_completo = r2_key
    edicao.r2_base = base
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


async def _download_video_task(edicao_id: int, youtube_url: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        edicao = db.get(Edicao, edicao_id)

        # 1) Tentar usar vídeo já existente na pasta local (APP1/iCloud)
        video_local = _find_video_in_export(edicao)
        if video_local:
            base = check_conflict(edicao.artista, edicao.musica, edicao.youtube_video_id or "")
            r2_key = f"{base}/video/original.mp4"
            storage.upload_file(video_local, r2_key)
            if edicao.youtube_video_id:
                save_youtube_marker(base, edicao.youtube_video_id)
            edicao.arquivo_video_completo = r2_key
            edicao.r2_base = base
            edicao.status = "letra"
            edicao.passo_atual = 2
            db.commit()
            return

        # 2) Fallback: baixar do YouTube (youtube.py já faz upload para R2)
        resultado = await download_video(
            youtube_url, edicao_id, STORAGE_PATH,
            artista=edicao.artista, musica=edicao.musica,
            youtube_video_id=edicao.youtube_video_id or "",
        )
        edicao.arquivo_video_completo = resultado["arquivo_original"]
        edicao.r2_base = resultado.get("r2_base", "")
        edicao.duracao_total_sec = resultado.get("duracao_total")
        edicao.status = "letra"
        edicao.passo_atual = 2
        db.commit()
    except Exception as e:
        edicao.status = "erro"
        edicao.erro_msg = str(e)
        db.commit()
    finally:
        db.close()


# --- Passo 2: Letra ---
@router.post("/edicoes/{edicao_id}/letra")
async def buscar_letra_endpoint(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if edicao.eh_instrumental:
        edicao.passo_atual = 5
        edicao.status = "corte"
        db.commit()
        return {"status": "instrumental — passo de letra pulado"}

    # Buscar no banco primeiro
    from app.models import Letra
    letra_existente = db.query(Letra).filter(
        Letra.musica.ilike(f"%{edicao.musica}%"),
    ).first()

    if letra_existente:
        letra_existente.vezes_utilizada += 1
        db.commit()
        return {"fonte": "banco", "letra": letra_existente.letra, "letra_id": letra_existente.id}

    # Buscar no Genius primeiro (fonte confiável)
    letra_genius = buscar_letra_genius(edicao.musica)
    if letra_genius:
        return {"fonte": "genius", "letra": letra_genius}

    # Fallback: Gemini
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
    db.commit()
    db.refresh(letra)
    return {"ok": True, "letra_id": letra.id}


# --- Passo 3: Transcrição ---
@router.post("/edicoes/{edicao_id}/transcricao")
async def iniciar_transcricao(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if not edicao.arquivo_video_completo:
        raise HTTPException(
            409, "Vídeo ainda não foi baixado. Aguarde o download completar."
        )

    # Verificar se vídeo existe no R2 (não mais no disco local)
    if not storage.exists(edicao.arquivo_video_completo):
        if edicao.youtube_url:
            logger.info(f"[{edicao_id}] Vídeo não encontrado no storage, re-baixando...")
            resultado_dl = await download_video(
                edicao.youtube_url, edicao_id, STORAGE_PATH,
                artista=edicao.artista, musica=edicao.musica,
                youtube_video_id=edicao.youtube_video_id or "",
            )
            edicao.arquivo_video_completo = resultado_dl["arquivo_original"]
            edicao.r2_base = resultado_dl.get("r2_base", edicao.r2_base)
            edicao.arquivo_audio_completo = None
            db.commit()
        else:
            raise HTTPException(409, "Vídeo não encontrado no storage e sem URL para re-baixar.")

    # Extrair áudio se necessário
    if not edicao.arquivo_audio_completo or not storage.exists(edicao.arquivo_audio_completo):
        audio_key = await extrair_audio_completo(
            edicao.arquivo_video_completo, edicao_id, STORAGE_PATH,
            r2_base=_get_r2_base(edicao),
        )
        edicao.arquivo_audio_completo = audio_key
        db.commit()

    edicao.status = "transcricao"
    db.commit()

    background_tasks.add_task(_transcricao_task, edicao_id)
    return {"status": "transcrição iniciada"}


async def _transcricao_task(edicao_id: int):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        edicao = db.get(Edicao, edicao_id)

        # Garantir que o áudio existe no storage
        r2_base = _get_r2_base(edicao)
        if not edicao.arquivo_audio_completo or not storage.exists(edicao.arquivo_audio_completo):
            if edicao.arquivo_video_completo and storage.exists(edicao.arquivo_video_completo):
                audio_key = await extrair_audio_completo(
                    edicao.arquivo_video_completo, edicao_id, STORAGE_PATH,
                    r2_base=r2_base,
                )
                edicao.arquivo_audio_completo = audio_key
                db.commit()
            elif edicao.youtube_url:
                logger.info(f"[{edicao_id}] Vídeo e áudio não encontrados no storage, re-baixando...")
                resultado_dl = await download_video(
                    edicao.youtube_url, edicao_id, STORAGE_PATH,
                    artista=edicao.artista, musica=edicao.musica,
                    youtube_video_id=edicao.youtube_video_id or "",
                )
                edicao.arquivo_video_completo = resultado_dl["arquivo_original"]
                edicao.r2_base = resultado_dl.get("r2_base", edicao.r2_base)
                r2_base = _get_r2_base(edicao)
                audio_key = await extrair_audio_completo(
                    edicao.arquivo_video_completo, edicao_id, STORAGE_PATH,
                    r2_base=r2_base,
                )
                edicao.arquivo_audio_completo = audio_key
                db.commit()
            else:
                edicao.status = "erro"
                edicao.erro_msg = "Áudio e vídeo não encontrados. Faça upload novamente."
                db.commit()
                return

        # Garantir áudio local para envio ao Gemini
        audio_local = storage.ensure_local(edicao.arquivo_audio_completo)

        # Buscar letra associada
        from app.models import Letra
        letra = db.query(Letra).filter(
            Letra.musica == edicao.musica,
            Letra.idioma == edicao.idioma,
        ).first()

        if not letra:
            edicao.status = "erro"
            edicao.erro_msg = "Letra não encontrada. Aprove a letra primeiro."
            db.commit()
            return

        metadados = {
            "artista": edicao.artista,
            "musica": edicao.musica,
            "compositor": edicao.compositor,
        }

        versos_esperados = len([v for v in letra.letra.split("\n") if v.strip()])

        # ============================================================
        # ESTRATÉGIA: CEGA PRIMEIRO → captura repetições naturalmente
        # ============================================================

        # Passo 1: MAPEAMENTO ESTRUTURAL
        logger.info(f"[{edicao_id}] Passo 1: Mapeamento estrutural do áudio...")
        genai = _get_client()
        mime_type = _detect_mime_type(audio_local)
        audio_file_ref = genai.upload_file(audio_local, mime_type=mime_type)

        melhor_cega = None
        melhor_n_cega = 0
        for tentativa in range(1, 3):
            segmentos_cegos = await mapear_estrutura_audio(
                audio_file_ref, edicao.idioma, metadados, letra.letra
            )
            n = len(segmentos_cegos)
            logger.info(f"[{edicao_id}] Cega tentativa {tentativa}: {n} segmentos")
            if n > melhor_n_cega:
                melhor_n_cega = n
                melhor_cega = segmentos_cegos
            if n >= versos_esperados * 0.8:
                break

        segmentos_cegos = normalizar_segmentos(melhor_cega or [])
        logger.info(f"[{edicao_id}] Cega final: {len(segmentos_cegos)} segmentos")

        # Passo 2: Transcrição GUIADA
        logger.info(f"[{edicao_id}] Passo 2: Transcrição GUIADA (texto fiel à letra)...")
        segmentos_guiados = await transcrever_guiado_completo(
            audio_local, letra.letra, edicao.idioma, metadados,
        )
        segmentos_guiados = normalizar_segmentos(segmentos_guiados)
        logger.info(f"[{edicao_id}] Guiada: {len(segmentos_guiados)} segmentos")

        # Passo 3: MERGE
        logger.info(f"[{edicao_id}] Passo 3: Merge (cega {len(segmentos_cegos)} × guiada {len(segmentos_guiados)})...")
        resultado = merge_transcricoes(segmentos_cegos, segmentos_guiados, letra.letra)
        logger.info(
            f"[{edicao_id}] Merge: rota={resultado['rota']} "
            f"confiança={resultado['confianca_media']}"
        )

        # Passo 4: Se merge fraco, tentar alinhar guiada direta como fallback
        if resultado["rota"] == "C":
            logger.info(f"[{edicao_id}] Merge fraco (rota C), tentando alinhamento guiada direta...")
            resultado_guiada = alinhar_letra_com_timestamps(letra.letra, segmentos_guiados)
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
            try:
                segmentos_completados = await completar_transcricao(
                    audio_local, letra.letra,
                    resultado["segmentos"], edicao.idioma, metadados,
                )
                if len(segmentos_completados) > n_resultado:
                    logger.info(f"[{edicao_id}] Completação: {n_resultado} → {len(segmentos_completados)}")
                    segmentos_completados = normalizar_segmentos(segmentos_completados)
                    resultado_completado = alinhar_letra_com_timestamps(letra.letra, segmentos_completados)
                    if resultado_completado["confianca_media"] >= resultado["confianca_media"]:
                        resultado = resultado_completado
            except Exception as e:
                logger.warning(f"[{edicao_id}] Completação falhou: {e}")

        resultado["segmentos"] = normalizar_segmentos(resultado["segmentos"])

        alinhamento = Alinhamento(
            edicao_id=edicao_id,
            letra_id=letra.id,
            segmentos_completo=resultado["segmentos"],
            confianca_media=resultado["confianca_media"],
            rota=resultado["rota"],
        )
        db.add(alinhamento)

        edicao.rota_alinhamento = resultado["rota"]
        edicao.confianca_alinhamento = resultado["confianca_media"]
        edicao.status = "alinhamento"
        edicao.passo_atual = 4
        db.commit()
        logger.info(
            f"[{edicao_id}] Transcrição concluída: "
            f"rota={resultado['rota']} confiança={resultado['confianca_media']}"
        )
    except Exception as e:
        edicao.status = "erro"
        edicao.erro_msg = f"Transcrição falhou: {e}"
        db.commit()
        logger.error(f"[{edicao_id}] Transcrição falhou: {e}")
    finally:
        db.close()


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

    # Cortar vídeo — usar R2 storage (ensure_local garante disponibilidade)
    r2_base = _get_r2_base(edicao)
    video_key = edicao.arquivo_video_completo
    if not video_key or not storage.exists(video_key):
        if edicao.youtube_url:
            logger.info(f"Vídeo não encontrado no storage — re-baixando...")
            try:
                resultado_dl = await download_video(
                    edicao.youtube_url, edicao_id, STORAGE_PATH,
                    artista=edicao.artista, musica=edicao.musica,
                    youtube_video_id=edicao.youtube_video_id or "",
                )
                edicao.arquivo_video_completo = resultado_dl["arquivo_original"]
                edicao.r2_base = resultado_dl.get("r2_base", edicao.r2_base)
                r2_base = _get_r2_base(edicao)
                video_key = resultado_dl["arquivo_original"]
            except Exception as e:
                logger.error(f"Falha ao re-baixar vídeo: {e}")
                video_key = None

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

    edicao.passo_atual = 6
    edicao.status = "traducao"
    db.commit()

    return {
        "janela": janela,
        "video_cortado": edicao.arquivo_video_cortado,
    }


# Statuses que permitem (re)iniciar tradução
_STATUS_PERMITIDOS_TRADUCAO = {"traducao", "montagem", "erro"}


# --- Passo 6: Tradução lyrics ---
@router.post("/edicoes/{edicao_id}/traducao-lyrics")
async def traduzir_lyrics(edicao_id: int, db: Session = Depends(get_db)):
    from app.worker import task_queue

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if edicao.eh_instrumental:
        edicao.passo_atual = 7
        edicao.status = "montagem"
        db.commit()
        return {"status": "instrumental — tradução pulada"}

    # Check-and-set atômico: só aceitar se status permite
    result = db.execute(
        update(Edicao)
        .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_TRADUCAO))
        .values(status="traducao")
    )
    db.commit()

    if result.rowcount == 0:
        db.refresh(edicao)
        raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar tradução")

    task_queue.put_nowait((_traducao_task, edicao_id))
    return {"status": "tradução enfileirada"}


async def _traducao_task(edicao_id: int):
    try:
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
            faltantes = [
                idioma for idioma in IDIOMAS_ALVO
                if idioma != idioma_origem and idioma not in ja_traduzidos
            ]
            total = len([i for i in IDIOMAS_ALVO if i != idioma_origem])
            concluidos = total - len(faltantes)

            # Copiar dados necessários para fora da sessão
            segmentos_cortado = alinhamento.segmentos_cortado
            metadados = {"musica": edicao.musica, "compositor": edicao.compositor}

            # Setar status e heartbeat inicial
            edicao.status = "traducao"
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "etapa": "traducao",
                "total": total,
                "concluidos": concluidos,
                "atual": None,
                "erros": [],
            }
            db.commit()

        # PASSO B — Loop de tradução (banco FECHADO durante I/O externo)
        falhas = []
        for idioma in faltantes:
            # Heartbeat antes de cada chamada de tradução (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "traducao",
                        "total": total,
                        "concluidos": concluidos,
                        "atual": idioma,
                        "erros": falhas,
                    }
                    db.commit()

            # I/O externo com timeout (banco FECHADO)
            try:
                logger.info(f"[{edicao_id}] Traduzindo para {idioma}...")
                resultado = await asyncio.wait_for(
                    traduzir_letra(segmentos_cortado, idioma_origem, idioma, metadados),
                    timeout=180,
                )

                # Salvar resultado (sessão curta)
                with SessionLocal() as db:
                    trad = TraducaoLetra(
                        edicao_id=edicao_id,
                        idioma=idioma,
                        segmentos=resultado,
                    )
                    db.add(trad)
                    db.commit()

                concluidos += 1
                logger.info(f"[{edicao_id}] Tradução {idioma} OK ({concluidos}/{total})")

            except asyncio.TimeoutError:
                falhas.append(f"{idioma}: timeout (180s)")
                logger.warning(f"[{edicao_id}] Tradução {idioma} timeout após 180s")
            except Exception as e:
                falhas.append(f"{idioma}: {e}")
                logger.warning(f"[{edicao_id}] Tradução {idioma} falhou: {e}")

        # PASSO C — Finalização (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.passo_atual = 7
                edicao.status = "montagem"
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "etapa": "traducao",
                    "total": total,
                    "concluidos": concluidos,
                    "atual": None,
                    "erros": falhas,
                }
                if falhas:
                    edicao.erro_msg = f"Traduções com falha ({len(falhas)}): {'; '.join(falhas)}"
                    logger.warning(f"[{edicao_id}] {len(falhas)} traduções falharam")
                else:
                    edicao.erro_msg = None
                db.commit()

        logger.info(f"[{edicao_id}] Tradução concluída: {concluidos} OK, {len(falhas)} falhas")

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        else:
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
async def renderizar(edicao_id: int):
    from app.database import SessionLocal
    from app.worker import task_queue

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_RENDER))
            .values(status="renderizando")
        )
        db.commit()

        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar renderização")

    task_queue.put_nowait((_render_task, edicao_id))
    return {"status": "renderização iniciada"}


async def _render_task(edicao_id: int, idiomas_renderizar: list = None, is_preview: bool = False):
    try:
        from app.database import SessionLocal
        from app.services.legendas import gerar_ass
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

            idiomas = idiomas_renderizar if idiomas_renderizar else IDIOMAS_ALVO

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
                db.commit()
                logger.info(f"[{edicao_id}] Todos os idiomas já renderizados, nada a fazer")
                return

            # Copiar dados necessários para variáveis locais (fora da sessão)
            arquivo_video = edicao.arquivo_video_cortado
            idioma_musica = edicao.idioma
            r2_base_val = _get_r2_base(edicao)
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
                traducao = db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == edicao_id,
                    TraducaoLetra.idioma == idioma,
                ).first()
                dados_idiomas[idioma] = {
                    "overlay_segs": overlay.segmentos_reindexado if overlay else [],
                    "traducao_segs": traducao.segmentos if traducao else None,
                }

            # Setar status e heartbeat inicial
            status_inicial = "preview" if is_preview else "renderizando"
            edicao.status = status_inicial
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "etapa": "render",
                "total": total,
                "concluidos": concluidos,
                "atual": None,
                "erros": [],
            }
            db.commit()

        # PASSO B — Loop de render (banco FECHADO durante FFmpeg)
        renders_ok = 0
        falhas = []

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

        for idioma in faltantes:
            # Heartbeat antes de cada render (sessão curta)
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "render",
                        "total": total,
                        "concluidos": concluidos,
                        "atual": idioma,
                        "erros": falhas,
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

                # Gerar ASS (sync, rápido — banco já fechado)
                ass_obj = gerar_ass(
                    overlay=d["overlay_segs"] or [],
                    lyrics=lyrics_segs or [],
                    traducao=d["traducao_segs"],
                    idioma_versao=idioma,
                    idioma_musica=idioma_musica,
                )

                output_dir = _Path(STORAGE_PATH) / str(edicao_id) / "renders" / idioma
                output_dir.mkdir(parents=True, exist_ok=True)
                ass_path = str(output_dir / f"legendas_{idioma}.ass")
                ass_obj.save(ass_path)

                output_video = str(output_dir / f"video_{idioma}.mp4")

                # FFmpeg com timeout — banco FECHADO
                ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
                cmd = (
                    f'ffmpeg -y -i "{local_video}" '
                    f'-vf "scale=1080:1920:force_original_aspect_ratio=decrease,'
                    f'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,'
                    f"ass='{ass_escaped}'\" "
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
                    r2_key = f"editor/{r2_base_val}/{idioma}/video_{idioma}.mp4"
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
                try:
                    _Path(ass_path).unlink(missing_ok=True)
                except Exception as cleanup_err:
                    logger.warning(f"[{edicao_id}] Falha ao deletar ASS {ass_path}: {cleanup_err}")

                # 7. Salvar resultado (sessão curta)
                with SessionLocal() as db:
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
                    "etapa": "render",
                    "total": total,
                    "concluidos": concluidos,
                    "atual": None,
                    "erros": falhas,
                }
                if renders_ok > 0:
                    if is_preview:
                        edicao.status = "preview_pronto"
                        edicao.passo_atual = 8
                    else:
                        edicao.status = "concluido"
                        edicao.passo_atual = 9
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
async def renderizar_preview(edicao_id: int):
    from app.database import SessionLocal
    from app.worker import task_queue, _make_preview_wrapper

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        # Preview sempre em PT para mostrar overlay + lyrics originais + tradução PT.
        # Se a música já for em PT, renderizar em PT é o correto (sem tradução, pois
        # idioma_versao == idioma_musica). Para todos os outros idiomas, PT garante
        # que precisa_traducao=True e a tradução aparece na linha inferior.
        idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma

        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_PREVIEW))
            .values(status="preview")
        )
        db.commit()

        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar preview")

    task_queue.put_nowait((_make_preview_wrapper(edicao_id, idioma_preview), edicao_id))
    return {"status": "preview iniciado", "idioma": idioma_preview}


@router.post("/edicoes/{edicao_id}/aprovar-preview")
async def aprovar_preview(edicao_id: int, body: AprovarPreviewParams):
    from app.database import SessionLocal
    from app.worker import task_queue

    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")

        if body.aprovado:
            # Determinar idioma do preview (mesma lógica de renderizar-preview)
            idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
            idiomas_renderizar = [i for i in IDIOMAS_ALVO if i != idioma_preview]

            # Check-and-set atômico: só aceitar se preview_pronto
            result = db.execute(
                update(Edicao)
                .where(Edicao.id == edicao_id, Edicao.status == "preview_pronto")
                .values(status="renderizando", notas_revisao=None)
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
        async def _render_remaining(_eid: int):
            await _render_task(_eid, idiomas_renderizar=idiomas_renderizar)

        task_queue.put_nowait((_render_remaining, edicao_id))
        return {"status": "renderização dos demais idiomas iniciada", "idiomas": idiomas_renderizar}


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
            destino = pasta_projeto / f"{edicao.artista} - {edicao.musica} [{render.idioma.upper()}].mp4"
            shutil.copy2(local_file, str(destino))
            logger.info(f"Exportado: {destino}")
        except Exception as e:
            logger.warning(f"Erro ao exportar {render.idioma}: {e}")

    # Incluir textos do Redator (do R2, na estrutura {base}/{base} - {IDIOMA}/)
    r2_base = _get_r2_base(edicao)
    if r2_base:
        for idioma_dir in IDIOMAS_ALVO:
            prefix = lang_prefix(r2_base, idioma_dir)
            for filename in ["post.txt", "subtitles.srt", "youtube.txt"]:
                r2_key = f"{prefix}/{filename}"
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


# --- Passo 9: Pacote final (renders + textos do Redator) ---
class PacoteParams(BaseModel):
    redator_project_id: Optional[int] = None


@router.post("/edicoes/{edicao_id}/pacote")
def gerar_pacote(edicao_id: int, body: PacoteParams = PacoteParams(), db: Session = Depends(get_db)):
    """Monta pacote final: renders do Editor + textos do Redator (do R2).

    Estrutura do ZIP:
      {artista} - {musica}/
        {idioma}/
          video_{idioma}.mp4   (render do Editor)
          post.txt             (texto do Redator)
          subtitles.srt        (overlay do Redator)
          youtube.txt          (título/tags do Redator)
    """
    import io
    import zipfile
    import tempfile

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    slug = f"{edicao.artista} - {edicao.musica}"
    r2_base = _get_r2_base(edicao)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        # Adicionar renders
        renders = db.query(Render).filter(
            Render.edicao_id == edicao_id, Render.status == "concluido"
        ).all()

        for render in renders:
            if not render.arquivo:
                continue
            try:
                local_file = storage.ensure_local(render.arquivo)
                arcname = f"{slug}/{render.idioma}/video_{render.idioma}.mp4"
                zf.write(local_file, arcname)
            except Exception as e:
                logger.warning(f"Pacote: não conseguiu incluir render {render.idioma}: {e}")

        # Adicionar textos do Redator (do R2, na estrutura {base}/{base} - {IDIOMA}/)
        if r2_base:
            for idioma_dir in IDIOMAS_ALVO:
                prefix = lang_prefix(r2_base, idioma_dir)
                for filename in ["post.txt", "subtitles.srt", "youtube.txt"]:
                    r2_key = f"{prefix}/{filename}"
                    if storage.exists(r2_key):
                        try:
                            local_file = storage.ensure_local(r2_key)
                            arcname = f"{slug}/{idioma_dir}/{filename}"
                            zf.write(local_file, arcname)
                        except Exception as e:
                            logger.warning(f"Pacote: falha ao incluir {r2_key}: {e}")

    zip_bytes = buffer.getvalue()

    # Upload pacote para R2: {base}/export/pacote.zip
    r2_key = f"{r2_base}/export/pacote.zip" if r2_base else f"exports/{edicao_id}/pacote.zip"
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp_path = tmp.name
    try:
        storage.upload_file(tmp_path, r2_key)
    finally:
        os.unlink(tmp_path)

    safe_slug = slug.replace('"', "'")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_slug}.zip"'},
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
    filename = f"{edicao.artista} - {edicao.musica} [{render.idioma.upper()}].mp4" if edicao else FilePath(local_path).name

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
_ACTIVE_STATUSES = {"traducao", "renderizando", "preview"}


@router.get("/fila/status")
async def fila_status():
    """Verifica se o worker está ocupado processando alguma edição."""
    from app.worker import is_worker_busy
    return is_worker_busy()


@router.post("/edicoes/{edicao_id}/desbloquear")
async def desbloquear_edicao(edicao_id: int):
    """Recovery manual: infere o status correto e desbloqueia uma edição travada.

    Só permitido se:
    - status == "erro", OU
    - status é um status ativo E o heartbeat está stale (> 5 min / NULL)

    Retorna 409 se a edição está em processamento ativo.
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

        if not is_erro and not (is_active and is_stale):
            raise HTTPException(
                409,
                f"Edição não pode ser desbloqueada: status='{edicao.status}'"
                + (" (processamento ativo)" if is_active and not is_stale else ""),
            )

        # Contar traduções e renders concluídos para inferir status
        n_traducoes = db.query(TraducaoLetra).filter(
            TraducaoLetra.edicao_id == edicao_id
        ).count()
        n_renders = db.query(Render).filter(
            Render.edicao_id == edicao_id,
            Render.status == "concluido",
        ).count()

        if n_renders > 0:
            novo_status = "preview_pronto"
        elif n_traducoes > 0:
            novo_status = "montagem"
        else:
            novo_status = "alinhamento"

        edicao.status = novo_status
        edicao.erro_msg = None
        edicao.progresso_detalhe = {}
        db.commit()

    logger.info(
        f"[desbloquear] edicao_id={edicao_id} desbloqueada → status='{novo_status}' "
        f"(renders={n_renders}, traducoes={n_traducoes})"
    )
    return {"novo_status": novo_status, "renders_concluidos": n_renders, "traducoes": n_traducoes}
