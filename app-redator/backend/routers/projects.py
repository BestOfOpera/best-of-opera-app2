from typing import List
from fastapi import APIRouter, Depends, HTTPException
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
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.get("/r2-available", response_model=List[R2AvailableItem])
def list_r2_available(db: Session = Depends(get_db)):
    """Lista projetos no R2 (video/original.mp4) sem projeto correspondente no Redator."""
    try:
        from shared.storage_service import storage
        keys = storage.list_files("")
    except Exception:
        return []

    originals = [k for k in keys if k.endswith("/video/original.mp4")]

    existing = db.query(Project.artist, Project.work).all()
    existing_set = {(p.artist.lower().strip(), p.work.lower().strip()) for p in existing}

    result = []
    for key in originals:
        folder = key[: -len("/video/original.mp4")]
        if " - " in folder:
            artist, work = folder.split(" - ", 1)
        else:
            artist, work = folder, ""
        artist, work = artist.strip(), work.strip()
        if (artist.lower(), work.lower()) not in existing_set:
            result.append(R2AvailableItem(folder=folder, artist=artist, work=work))

    return result


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
