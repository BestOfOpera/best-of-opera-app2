from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import ProjectCreate, ProjectUpdate, ProjectOut, R2AvailableItem

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=ProjectOut)
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**data.model_dump(), status="input_complete")
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=List[ProjectOut])
def list_projects(
    brand_slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Project)
    if brand_slug is not None:
        q = q.filter(Project.brand_slug == brand_slug)
    return q.order_by(Project.created_at.desc()).all()


@router.get("/r2-available", response_model=List[R2AvailableItem])
def list_r2_available(
    brand_slug: Optional[str] = Query(None),
    r2_prefix: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Lista projetos no R2 (video/original.mp4) sem projeto correspondente no Redator.

    r2_prefix — prefixo R2 da marca (ex: 'best-of-opera'). Filtra arquivos por marca.
    """
    try:
        from shared.storage_service import storage
        keys = storage.list_files(r2_prefix or "")
    except Exception:
        return []

    originals = [k for k in keys if k.endswith("/video/original.mp4")]

    existing_q = db.query(Project.artist, Project.work)
    if brand_slug is not None:
        existing_q = existing_q.filter(Project.brand_slug == brand_slug)
    existing = existing_q.all()
    existing_set = {(p.artist.lower().strip(), p.work.lower().strip()) for p in existing}

    result = []
    for key in originals:
        # Remover prefixo da marca do caminho antes de extrair artist/work
        relative = key.removeprefix(f"{r2_prefix}/") if r2_prefix else key
        folder_relative = relative[: -len("/video/original.mp4")]
        full_folder = key[: -len("/video/original.mp4")]
        if " - " in folder_relative:
            artist, work = folder_relative.split(" - ", 1)
        else:
            artist, work = folder_relative, ""
        artist, work = artist.strip(), work.strip()
        if (artist.lower(), work.lower()) not in existing_set:
            result.append(R2AvailableItem(folder=full_folder, artist=artist, work=work))

    return result


class R2DeleteRequest(BaseModel):
    folders: List[str]

@router.delete("/r2-available")
def delete_r2_items(body: R2DeleteRequest):
    """Deleta pastas selecionadas do R2 (remove video/original.mp4 de cada folder)."""
    try:
        from shared.storage_service import storage
    except Exception:
        raise HTTPException(500, "Storage não configurado")

    deleted = []
    for folder in body.folders:
        key = f"{folder}/video/original.mp4"
        try:
            storage.delete(key)
            deleted.append(folder)
        except Exception:
            pass

    return {"deleted": deleted}


@router.delete("/by-brand/{brand_slug}")
def delete_projects_by_brand(brand_slug: str, db: Session = Depends(get_db)):
    """Deleta todos os projetos de uma marca. CASCADE limpa translations."""
    projects = db.query(Project).filter(Project.brand_slug == brand_slug).all()
    if not projects:
        return {"deleted": 0}

    count = len(projects)
    for p in projects:
        db.delete(p)

    db.commit()
    return {"deleted": count}


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project
