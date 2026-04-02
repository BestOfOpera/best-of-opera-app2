"""CRUD de edições."""
import io
import json
import logging
import re
import zipfile
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Edicao, Overlay, Post, Seo
from app.models.perfil import Perfil
from app.schemas import EdicaoCreate, EdicaoUpdate, EdicaoOut
from shared.storage_service import storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/editor", tags=["edicoes"])


@router.get("/edicoes", response_model=list[EdicaoOut])
def listar_edicoes(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    perfil_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    if perfil_id is None:
        return []
    q = db.query(Edicao).filter(
        Edicao.perfil_id == perfil_id
    ).order_by(Edicao.id.desc())
    if status:
        q = q.filter(Edicao.status == status)
    if categoria:
        q = q.filter(Edicao.categoria == categoria)
    return q.all()


@router.post("/edicoes", response_model=EdicaoOut)
def criar_edicao(data: EdicaoCreate, db: Session = Depends(get_db)):
    edicao = Edicao(
        youtube_url=data.youtube_url,
        youtube_video_id=data.youtube_video_id,
        artista=data.artista,
        musica=data.musica,
        compositor=data.compositor,
        opera=data.opera,
        categoria=data.categoria,
        idioma=data.idioma,
        eh_instrumental=data.eh_instrumental,
        sem_lyrics=data.eh_instrumental,
        perfil_id=data.perfil_id,
    )
    db.add(edicao)
    db.flush()

    # Salvar overlays se fornecidos
    if data.overlays:
        for idioma, segmentos in data.overlays.items():
            overlay = Overlay(
                edicao_id=edicao.id,
                idioma=idioma,
                segmentos_original=segmentos,
            )
            db.add(overlay)

    # Salvar posts se fornecidos
    if data.posts:
        for idioma, texto in data.posts.items():
            post = Post(edicao_id=edicao.id, idioma=idioma, texto=texto)
            db.add(post)

    # Salvar SEO se fornecido
    if data.seo:
        for idioma, seo_data in data.seo.items():
            seo = Seo(
                edicao_id=edicao.id,
                idioma=idioma,
                titulo=seo_data.get("titulo"),
                descricao=seo_data.get("descricao"),
                tags=seo_data.get("tags"),
            )
            db.add(seo)

    db.commit()
    db.refresh(edicao)
    return edicao


@router.get("/edicoes/{edicao_id}", response_model=EdicaoOut)
def obter_edicao(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    return edicao


@router.patch("/edicoes/{edicao_id}", response_model=EdicaoOut)
def atualizar_edicao(edicao_id: int, data: EdicaoUpdate, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(edicao, key, value)
    db.commit()
    db.refresh(edicao)
    return edicao


@router.delete("/edicoes/{edicao_id}")
def remover_edicao(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Limpar arquivos R2 da edição
    r2_deleted = 0
    if edicao.r2_base:
        r2_prefix = "editor"  # default
        if edicao.perfil_id:
            perfil = db.get(Perfil, edicao.perfil_id)
            if perfil and perfil.r2_prefix:
                r2_prefix = perfil.r2_prefix
        prefix = f"{r2_prefix}/{edicao.r2_base}"
        try:
            files = storage.list_files(prefix)
            for key in files:
                try:
                    storage.delete(key)
                    r2_deleted += 1
                except Exception:
                    pass
        except Exception:
            logger.warning(f"Erro listando R2 prefix={prefix}")

    db.delete(edicao)
    db.commit()
    return {"ok": True, "r2_files_deleted": r2_deleted}


@router.post("/edicoes/{edicao_id}/upload-overlays")
async def upload_overlays(
    edicao_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload de arquivo ZIP contendo overlays por idioma.

    Formato esperado do ZIP:
      pt.json, en.json, es.json, ...
    Cada JSON é um array de segmentos:
      [{"text": "...", "start": 0.0, "end": 3.0, "type": "corpo"}, ...]
    Campo 'type' aceita: "gancho", "corpo" (default), "cta".
    Se type=="cta", seta _is_cta=True (usado por legendas.py para posicionamento).
    """
    logger.info(
        f"[upload-overlays] Recebido: edicao_id={edicao_id} "
        f"filename='{file.filename}' content_type='{file.content_type}' "
        f"size_header={file.size}"
    )

    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")

    # Ler conteúdo do arquivo e validar pelo CONTEÚDO (não pelo filename,
    # que pode variar entre browsers/OS)
    content = await file.read()
    if not content:
        logger.error(f"[upload-overlays] edicao={edicao_id}: arquivo vazio (0 bytes)")
        raise HTTPException(400, "Arquivo vazio")

    logger.info(f"[upload-overlays] edicao={edicao_id}: {len(content)} bytes lidos")

    try:
        zf = zipfile.ZipFile(io.BytesIO(content))
    except zipfile.BadZipFile:
        logger.error(
            f"[upload-overlays] edicao={edicao_id}: ZIP inválido "
            f"(filename='{file.filename}', {len(content)} bytes, "
            f"primeiros bytes={content[:20]!r})"
        )
        raise HTTPException(
            400,
            f"Arquivo ZIP inválido (filename='{file.filename}', {len(content)} bytes). "
            f"Verifique se o arquivo é um .zip válido."
        )

    namelist = zf.namelist()
    logger.info(f"[upload-overlays] edicao={edicao_id}: ZIP namelist={namelist}")

    salvos = []
    erros = {}
    total_segmentos = 0
    _IDIOMA_RE = re.compile(r"^[a-z]{2}$")

    for name in namelist:
        if not name.lower().endswith(".json"):
            continue
        # Ignorar metadata do macOS
        if name.startswith("__MACOSX") or "/." in name:
            logger.info(f"[upload-overlays] Ignorando metadata: {name}")
            continue
        # Extrair idioma do nome do arquivo (ex: "pt.json" → "pt")
        basename = name.rsplit("/", 1)[-1]  # suporta subpastas no ZIP
        idioma = basename.replace(".json", "").lower().strip()
        if not _IDIOMA_RE.match(idioma):
            logger.warning(f"[upload-overlays] Ignorando {name}: idioma '{idioma}' não é código de 2 letras")
            continue

        # Processar cada JSON independentemente — erro em um não bloqueia os outros
        try:
            raw = zf.read(name)
            segmentos = json.loads(raw)

            if not isinstance(segmentos, list):
                raise ValueError(f"esperado array JSON, recebeu {type(segmentos).__name__}")

            # Validar e normalizar segmentos
            for idx, seg in enumerate(segmentos):
                if not isinstance(seg, dict) or not seg.get("text"):
                    raise ValueError(f"item {idx}: deve ter campo 'text' não vazio")
                # Derivar _is_cta de type=="cta"
                seg_type = seg.pop("type", "corpo")
                if seg_type == "cta":
                    seg["_is_cta"] = True

            # Upsert: atualizar se já existe overlay para este (edicao_id, idioma)
            existing = db.query(Overlay).filter(
                Overlay.edicao_id == edicao_id, Overlay.idioma == idioma
            ).first()
            if existing:
                existing.segmentos_original = segmentos
                existing.segmentos_reindexado = None
                logger.info(f"[upload-overlays] edicao={edicao_id} idioma={idioma}: ATUALIZADO {len(segmentos)} segmentos")
            else:
                db.add(Overlay(
                    edicao_id=edicao_id,
                    idioma=idioma,
                    segmentos_original=segmentos,
                ))
                logger.info(f"[upload-overlays] edicao={edicao_id} idioma={idioma}: CRIADO {len(segmentos)} segmentos")

            salvos.append(idioma)
            total_segmentos += len(segmentos)

        except (json.JSONDecodeError, ValueError, Exception) as e:
            erro_msg = str(e)
            erros[idioma] = erro_msg
            logger.warning(f"[upload-overlays] edicao={edicao_id} idioma={idioma}: IGNORADO — {erro_msg}")
            continue

    if not salvos:
        logger.error(
            f"[upload-overlays] edicao={edicao_id}: nenhum JSON válido no ZIP. "
            f"namelist={namelist}, erros={erros}"
        )
        raise HTTPException(
            400,
            {
                "erro": "Nenhum JSON válido no ZIP",
                "detalhes": erros,
                "arquivos": namelist,
            },
        )

    db.commit()
    status = "parcial" if erros else "ok"
    logger.info(
        f"[upload-overlays] edicao={edicao_id}: {status.upper()} "
        f"salvos={salvos} erros={erros} total={total_segmentos}"
    )
    return {
        "status": status,
        "salvos": salvos,
        "erros": erros,
        "total_segmentos": total_segmentos,
    }
