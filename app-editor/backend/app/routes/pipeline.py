"""Rotas do pipeline de edição (passos 1-9)."""
import logging
from pathlib import Path as FilePath
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db

logger = logging.getLogger(__name__)
from app.models import Edicao, Overlay, Alinhamento, TraducaoLetra, Render
from app.schemas import AlinhamentoOut, AlinhamentoValidar, LetraAprovar
from app.services.youtube import download_video
from app.services.ffmpeg_service import extrair_audio_completo, cortar_na_janela_overlay
from app.services.gemini import buscar_letra as gemini_buscar_letra, transcrever_guiado_completo, transcrever_cego, _detect_mime_type, _get_client
from app.services.genius import buscar_letra_genius
from app.services.alinhamento import alinhar_letra_com_timestamps, merge_transcricoes
from app.services.regua import extrair_janela_do_overlay, reindexar_timestamps, recortar_lyrics_na_janela, normalizar_segmentos
import shutil
from app.config import STORAGE_PATH, IDIOMAS_ALVO, EXPORT_PATH, REDATOR_API_URL

router = APIRouter(prefix="/api/v1/editor", tags=["pipeline"])


class CorteParams(BaseModel):
    janela_inicio: Optional[float] = None
    janela_fim: Optional[float] = None


# --- Passo 1: Garantir vídeo ---
@router.post("/edicoes/{edicao_id}/garantir-video")
async def garantir_video(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if edicao.arquivo_video_completo:
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

    output_dir = FilePath(STORAGE_PATH) / str(edicao_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    destino = output_dir / "original.mp4"

    with open(str(destino), "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)

    edicao.arquivo_video_completo = str(destino)
    edicao.status = "letra"
    edicao.passo_atual = 2
    edicao.erro_msg = None
    db.commit()
    return {"status": "ok", "arquivo": str(destino)}


def _find_video_in_export(edicao):
    """Procura vídeo já baixado na pasta EXPORT_PATH (ex: iCloud do APP1)."""
    if not EXPORT_PATH:
        return None
    pasta_projeto = FilePath(EXPORT_PATH) / f"{edicao.artista} - {edicao.musica}"
    if not pasta_projeto.exists():
        return None
    # Procurar qualquer .mp4 na raiz da pasta (vídeo original do APP1)
    mp4s = [f for f in pasta_projeto.iterdir() if f.suffix == '.mp4' and f.is_file()]
    if mp4s:
        # Pegar o maior arquivo (provavelmente o vídeo completo)
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
            # Copiar para storage do editor
            output_dir = FilePath(STORAGE_PATH) / str(edicao_id)
            output_dir.mkdir(parents=True, exist_ok=True)
            destino = output_dir / "original.mp4"
            shutil.copy2(video_local, str(destino))
            edicao.arquivo_video_completo = str(destino)
            edicao.status = "letra"
            edicao.passo_atual = 2
            db.commit()
            return

        # 2) Fallback: baixar do YouTube
        resultado = await download_video(youtube_url, edicao_id, STORAGE_PATH)
        edicao.arquivo_video_completo = resultado["arquivo_original"]
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

    # Verificar se já existe letra para esta música (evitar duplicatas)
    letra = db.query(Letra).filter(
        Letra.musica == edicao.musica,
        Letra.idioma == edicao.idioma,
    ).first()

    if letra:
        # Atualizar letra existente
        letra.letra = body.letra
        letra.fonte = body.fonte
        letra.validado_por = body.validado_por
    else:
        # Criar nova
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

    # Verificar se o vídeo já foi baixado
    if not edicao.arquivo_video_completo:
        raise HTTPException(
            409, "Vídeo ainda não foi baixado. Aguarde o download completar."
        )

    # Extrair áudio se necessário
    if not edicao.arquivo_audio_completo:
        audio_path = await extrair_audio_completo(
            edicao.arquivo_video_completo, edicao_id, STORAGE_PATH
        )
        edicao.arquivo_audio_completo = audio_path
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
        # Buscar letra associada (match exato por musica + idioma)
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

        # Estratégia: guiada primeiro (comprovadamente funciona bem)
        # Upload próprio — não reutilizar file ref (funciona melhor assim)

        # Passo 1: Transcrição guiada (texto + timestamps)
        logger.info(f"[{edicao_id}] Iniciando transcrição GUIADA (upload próprio)...")
        segmentos_guiados = await transcrever_guiado_completo(
            edicao.arquivo_audio_completo, letra.letra, edicao.idioma, metadados,
        )
        logger.info(f"[{edicao_id}] Transcrição guiada: {len(segmentos_guiados)} segmentos")

        # Normalizar timestamps do Gemini (formato canônico + validação)
        segmentos_guiados = normalizar_segmentos(segmentos_guiados)

        # Passo 2: Alinhar guiada com letra original (método comprovado)
        resultado = alinhar_letra_com_timestamps(letra.letra, segmentos_guiados)
        logger.info(
            f"[{edicao_id}] Alinhamento guiado: rota={resultado['rota']} "
            f"confiança={resultado['confianca_media']}"
        )

        # Passo 3: Se resultado fraco, tentar refinar com transcrição cega
        if resultado["rota"] == "C":
            logger.info(f"[{edicao_id}] Rota C detectada, tentando merge com transcrição cega...")
            try:
                genai = _get_client()
                mime_type = _detect_mime_type(edicao.arquivo_audio_completo)
                audio_file_ref = genai.upload_file(edicao.arquivo_audio_completo, mime_type=mime_type)
                segmentos_cegos = await transcrever_cego(
                    audio_file_ref, edicao.idioma, metadados
                )
                logger.info(f"[{edicao_id}] Transcrição cega: {len(segmentos_cegos)} segmentos")
                resultado_merge = merge_transcricoes(segmentos_cegos, segmentos_guiados, letra.letra)
                # Usar merge só se melhorou
                if resultado_merge["confianca_media"] > resultado["confianca_media"]:
                    logger.info(
                        f"[{edicao_id}] Merge melhorou: {resultado['confianca_media']:.3f} → "
                        f"{resultado_merge['confianca_media']:.3f}"
                    )
                    resultado = resultado_merge
                else:
                    logger.info(f"[{edicao_id}] Merge não melhorou, mantendo guiada direta")
            except Exception as e:
                logger.warning(f"[{edicao_id}] Cega falhou, mantendo guiada: {e}")

        # Normalizar resultado final antes de salvar
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
            # Match por artista + obra
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
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Buscar overlays
    overlays = db.query(Overlay).filter(Overlay.edicao_id == edicao_id).all()
    if not overlays:
        raise HTTPException(400, "Nenhum overlay encontrado. Adicione overlays primeiro.")

    # Se body fornecido com valores explícitos, usar diretamente
    if body and body.janela_inicio is not None and body.janela_fim is not None:
        janela = {
            "janela_inicio_sec": body.janela_inicio,
            "janela_fim_sec": body.janela_fim,
            "duracao_corte_sec": body.janela_fim - body.janela_inicio,
        }
    else:
        # Se não tem corte_original, tentar buscar do Redator em tempo real
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

    # Reindexar overlays
    for ov in overlays:
        ov.segmentos_reindexado = reindexar_timestamps(
            ov.segmentos_original, janela["janela_inicio_sec"]
        )

    # Cortar vídeo se disponível
    if edicao.arquivo_video_completo:
        resultado = await cortar_na_janela_overlay(
            edicao.arquivo_video_completo,
            janela["janela_inicio_sec"],
            janela["janela_fim_sec"],
            edicao_id,
            STORAGE_PATH,
        )
        edicao.arquivo_video_cortado = resultado["arquivo_cortado"]
        edicao.arquivo_video_cru = resultado["arquivo_cru"]

    # Recortar lyrics se houver alinhamento (usar o mais recente validado)
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


# --- Passo 6: Tradução lyrics ---
@router.post("/edicoes/{edicao_id}/traducao-lyrics")
async def traduzir_lyrics(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    if edicao.eh_instrumental:
        edicao.passo_atual = 7
        edicao.status = "montagem"
        db.commit()
        return {"status": "instrumental — tradução pulada"}

    edicao.status = "traducao"
    db.commit()

    background_tasks.add_task(_traducao_task, edicao_id)
    return {"status": "tradução iniciada"}


async def _traducao_task(edicao_id: int):
    from app.database import SessionLocal
    from app.services.gemini import traduzir_letra
    db = SessionLocal()
    try:
        edicao = db.get(Edicao, edicao_id)
        alinhamento = db.query(Alinhamento).filter(
            Alinhamento.edicao_id == edicao_id
        ).order_by(Alinhamento.id.desc()).first()

        if not alinhamento or not alinhamento.segmentos_cortado:
            edicao.status = "erro"
            edicao.erro_msg = "Alinhamento cortado não encontrado"
            db.commit()
            return

        idiomas_alvo = IDIOMAS_ALVO
        metadados = {"musica": edicao.musica, "compositor": edicao.compositor}

        for idioma in idiomas_alvo:
            if idioma == edicao.idioma:
                continue
            try:
                resultado = await traduzir_letra(
                    alinhamento.segmentos_cortado, edicao.idioma, idioma, metadados
                )
                trad = TraducaoLetra(
                    edicao_id=edicao_id,
                    idioma=idioma,
                    segmentos=resultado,
                )
                db.add(trad)
            except Exception as e:
                logger.warning(f"Tradução para {idioma} falhou: {e}")

        edicao.passo_atual = 7
        edicao.status = "montagem"
        db.commit()
    except Exception as e:
        edicao.status = "erro"
        edicao.erro_msg = f"Tradução falhou: {e}"
        db.commit()
    finally:
        db.close()


# --- Passos 7-8: Renderização ---
@router.post("/edicoes/{edicao_id}/renderizar")
async def renderizar(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    edicao.status = "renderizando"
    db.commit()

    background_tasks.add_task(_render_task, edicao_id)
    return {"status": "renderização iniciada"}


async def _render_task(edicao_id: int):
    from app.database import SessionLocal
    from app.services.legendas import gerar_ass
    from app.services.ffmpeg_service import renderizar_video
    from pathlib import Path
    db = SessionLocal()
    try:
        edicao = db.get(Edicao, edicao_id)
        if not edicao.arquivo_video_cortado:
            edicao.status = "erro"
            edicao.erro_msg = "Vídeo cortado não disponível"
            db.commit()
            return

        idiomas = IDIOMAS_ALVO
        for idioma in idiomas:
            try:
                # Buscar overlay reindexado
                overlay = db.query(Overlay).filter(
                    Overlay.edicao_id == edicao_id, Overlay.idioma == idioma
                ).first()
                overlay_segs = overlay.segmentos_reindexado if overlay else []

                # Buscar lyrics cortados
                alinhamento = db.query(Alinhamento).filter(
                    Alinhamento.edicao_id == edicao_id
                ).order_by(Alinhamento.id.desc()).first()
                lyrics_segs = alinhamento.segmentos_cortado if alinhamento else []

                # Buscar tradução
                traducao = db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == edicao_id,
                    TraducaoLetra.idioma == idioma,
                ).first()
                traducao_segs = traducao.segmentos if traducao else None

                # Gerar ASS
                ass_file = gerar_ass(
                    overlay=overlay_segs or [],
                    lyrics=lyrics_segs or [],
                    traducao=traducao_segs,
                    idioma_versao=idioma,
                    idioma_musica=edicao.idioma,
                )

                output_dir = Path(STORAGE_PATH) / str(edicao_id) / "renders" / idioma
                output_dir.mkdir(parents=True, exist_ok=True)
                ass_path = str(output_dir / f"legendas_{idioma}.ass")
                ass_file.save(ass_path)

                # Renderizar
                output_video = str(output_dir / f"video_{idioma}.mp4")
                resultado = await renderizar_video(
                    edicao.arquivo_video_cortado, ass_path, output_video
                )

                render = Render(
                    edicao_id=edicao_id,
                    idioma=idioma,
                    tipo="9:16",
                    arquivo=resultado["arquivo"],
                    tamanho_bytes=resultado["tamanho_bytes"],
                    status="concluido",
                )
                db.add(render)
            except Exception as e:
                render = Render(
                    edicao_id=edicao_id,
                    idioma=idioma,
                    tipo="9:16",
                    status="erro",
                    erro_msg=str(e),
                )
                db.add(render)

        edicao.status = "concluido"
        edicao.passo_atual = 9
        db.commit()

        # Exportar para pasta local (se configurado)
        _exportar_renders(edicao, db)
    except Exception as e:
        edicao.status = "erro"
        edicao.erro_msg = f"Renderização falhou: {e}"
        db.commit()
    finally:
        db.close()


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
        origem = FilePath(render.arquivo)
        if not origem.exists():
            continue
        destino = pasta_projeto / f"{edicao.artista} - {edicao.musica} [{render.idioma.upper()}].mp4"
        try:
            shutil.copy2(str(origem), str(destino))
            logger.info(f"Exportado: {destino}")
        except Exception as e:
            logger.warning(f"Erro ao exportar {render.idioma}: {e}")


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


# --- Passo 9: Pacote ---
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

    path = FilePath(render.arquivo)
    if not path.exists():
        raise HTTPException(
            404,
            "Arquivo não encontrado no servidor. O Railway usa storage efêmero — "
            "os arquivos são perdidos quando o container reinicia. "
            "Re-renderize para gerar novamente."
        )

    edicao = db.get(Edicao, edicao_id)
    filename = f"{edicao.artista} - {edicao.musica} [{render.idioma.upper()}].mp4" if edicao else path.name

    return FileResponse(
        path=str(path),
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
    path = FilePath(edicao.arquivo_audio_completo)
    if not path.exists():
        raise HTTPException(404, "Arquivo de áudio não encontrado no servidor.")
    return FileResponse(
        path=str(path),
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
