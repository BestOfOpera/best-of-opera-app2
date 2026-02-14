"""CRUD de letras."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Letra
from app.schemas import LetraCreate, LetraUpdate, LetraOut

router = APIRouter(prefix="/api/v1/editor", tags=["letras"])


@router.get("/letras", response_model=list[LetraOut])
def listar_letras(db: Session = Depends(get_db)):
    return db.query(Letra).order_by(Letra.id.desc()).all()


@router.get("/letras/buscar", response_model=list[LetraOut])
def buscar_letras(
    musica: Optional[str] = None,
    compositor: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Letra)
    if musica:
        q = q.filter(Letra.musica.ilike(f"%{musica}%"))
    if compositor:
        q = q.filter(Letra.compositor.ilike(f"%{compositor}%"))
    return q.all()


@router.post("/letras", response_model=LetraOut)
def criar_letra(data: LetraCreate, db: Session = Depends(get_db)):
    letra = Letra(**data.model_dump())
    db.add(letra)
    db.commit()
    db.refresh(letra)
    return letra


@router.put("/letras/{letra_id}", response_model=LetraOut)
def atualizar_letra(letra_id: int, data: LetraUpdate, db: Session = Depends(get_db)):
    letra = db.get(Letra, letra_id)
    if not letra:
        raise HTTPException(404, "Letra não encontrada")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(letra, key, value)
    db.commit()
    db.refresh(letra)
    return letra
