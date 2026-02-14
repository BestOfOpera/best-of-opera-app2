"""CRUD de edições."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Edicao, Overlay, Post, Seo
from app.schemas import EdicaoCreate, EdicaoUpdate, EdicaoOut

router = APIRouter(prefix="/api/v1/editor", tags=["edicoes"])


@router.get("/edicoes", response_model=list[EdicaoOut])
def listar_edicoes(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Edicao).order_by(Edicao.id.desc())
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
    db.delete(edicao)
    db.commit()
    return {"ok": True}
