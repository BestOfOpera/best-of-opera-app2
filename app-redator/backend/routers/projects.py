from math import ceil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
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


ALLOWED_SORT_PROJECTS = {"created_at", "updated_at", "artist", "work"}


@router.get("")
def list_projects(
    brand_slug: Optional[str] = Query(None),
    search: str = Query(""),
    status: str = Query(""),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    q = db.query(Project)
    if brand_slug is not None:
        q = q.filter(Project.brand_slug == brand_slug)
    if search:
        term = f"%{search}%"
        q = q.filter(or_(
            Project.artist.ilike(term),
            Project.work.ilike(term),
            Project.composer.ilike(term),
        ))
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            q = q.filter(Project.status == statuses[0])
        elif statuses:
            q = q.filter(Project.status.in_(statuses))

    if sort_by not in ALLOWED_SORT_PROJECTS:
        sort_by = "created_at"
    if sort_order not in ("asc", "desc"):
        sort_order = "desc"

    col = getattr(Project, sort_by)
    q = q.order_by(col.asc() if sort_order == "asc" else col.desc())

    total = q.count()

    if limit > 0:
        offset = (page - 1) * limit
        q = q.offset(offset).limit(limit)

    projects = q.all()
    return {
        "projects": [ProjectOut.model_validate(p) for p in projects],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": ceil(total / limit) if limit > 0 else 1,
    }


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
        files_meta = storage.list_files_with_metadata(r2_prefix or "")
    except Exception:
        return []

    # Filtrar apenas video/original.mp4 e por r2_prefix
    originals = [fm for fm in files_meta if fm["key"].endswith("/video/original.mp4")]
    if r2_prefix:
        originals = [fm for fm in originals if fm["key"].startswith(f"{r2_prefix}/")]

    # Mapear folder → last_modified para lookup rápido
    folder_dates: dict[str, str] = {}
    for fm in originals:
        folder_key = fm["key"][: -len("/video/original.mp4")]
        if folder_key not in folder_dates:
            folder_dates[folder_key] = fm.get("last_modified", "")

    existing_q = db.query(Project.artist, Project.work)
    if brand_slug is not None:
        existing_q = existing_q.filter(Project.brand_slug == brand_slug)
    existing = existing_q.all()
    existing_set = {(p.artist.lower().strip(), p.work.lower().strip()) for p in existing}

    result = []
    for fm in originals:
        key = fm["key"]
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
            result.append(R2AvailableItem(
                folder=full_folder, artist=artist, work=work,
                prepared_at=folder_dates.get(full_folder),
            ))

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


class BulkDeleteRequest(BaseModel):
    ids: List[int]

@router.delete("/bulk")
def delete_projects_bulk(body: BulkDeleteRequest, db: Session = Depends(get_db)):
    """Deleta múltiplos projetos por ID."""
    projects = db.query(Project).filter(Project.id.in_(body.ids)).all()
    for p in projects:
        db.delete(p)
    db.commit()
    return {"deleted": len(projects)}


@router.post("/{project_id}/reset")
def reset_project(project_id: int, db: Session = Depends(get_db)):
    """Reseta projeto para input_complete. Limpa traduções e flags de aprovação."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Projeto não encontrado")

    from backend.models import Translation
    db.query(Translation).filter(Translation.project_id == project_id).delete()

    project.overlay_approved = False
    project.post_approved = False
    project.youtube_approved = False
    project.status = "input_complete"

    db.commit()
    return {"ok": True, "message": f"Projeto {project_id} resetado para input_complete."}


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    r2_deleted = 0
    if project.r2_folder:
        try:
            from shared.storage_service import storage
            files = storage.list_files(project.r2_folder)
            for f in files:
                storage.delete(f)
            r2_deleted = len(files)
        except Exception as e:
            print(f"[DELETE] Aviso: erro ao limpar R2 {project.r2_folder}: {e}", flush=True)

    db.delete(project)
    db.commit()
    return {"ok": True, "r2_files_deleted": r2_deleted}


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
