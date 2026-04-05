"""CRUD de edições."""
import io
import json
import logging
import re
import zipfile
from math import ceil
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Edicao, Overlay, Post, Seo
from app.models.perfil import Perfil
from app.schemas import EdicaoCreate, EdicaoUpdate, EdicaoOut
from shared.storage_service import storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/editor", tags=["edicoes"])


ALLOWED_SORT_EDICOES = {"created_at", "updated_at", "artista", "musica"}


@router.get("/edicoes")
def listar_edicoes(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    perfil_id: Optional[int] = Query(None),
    search: str = Query(""),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if perfil_id is None:
        return {"edicoes": [], "total": 0, "page": 1, "limit": limit, "total_pages": 0}
    q = db.query(Edicao).filter(Edicao.perfil_id == perfil_id)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            q = q.filter(Edicao.status == statuses[0])
        elif statuses:
            q = q.filter(Edicao.status.in_(statuses))
    if categoria:
        q = q.filter(Edicao.categoria == categoria)
    if search:
        term = f"%{search}%"
        q = q.filter(or_(
            Edicao.artista.ilike(term),
            Edicao.musica.ilike(term),
            Edicao.compositor.ilike(term),
        ))

    if sort_by not in ALLOWED_SORT_EDICOES:
        sort_by = "created_at"
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    col = getattr(Edicao, sort_by)
    q = q.order_by(col.asc() if sort_order == "asc" else col.desc())

    total = q.count()

    if limit > 0:
        offset = (page - 1) * limit
        q = q.offset(offset).limit(limit)

    edicoes = q.all()
    return {
        "edicoes": [EdicaoOut.model_validate(e) for e in edicoes],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": ceil(total / limit) if limit > 0 else 1,
    }


@router.post("/edicoes", response_model=EdicaoOut)
def criar_edicao(data: EdicaoCreate, db: Session = Depends(get_db)):
    # Vocal: artista, musica e idioma são obrigatórios (necessários para busca de letra)
    if not data.eh_instrumental:
        if not data.artista or not data.musica:
            raise HTTPException(400, "Artista e música são obrigatórios para edição vocal")
        if not data.idioma:
            raise HTTPException(400, "Idioma é obrigatório para edição vocal (necessário para transcrição)")

    # Instrumental: defaults para campos opcionais
    artista = data.artista or "Instrumental"
    musica = data.musica or data.youtube_url
    idioma = data.idioma or "und"

    edicao = Edicao(
        youtube_url=data.youtube_url,
        youtube_video_id=data.youtube_video_id,
        artista=artista,
        musica=musica,
        compositor=data.compositor,
        opera=data.opera,
        categoria=data.categoria,
        idioma=idioma,
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
