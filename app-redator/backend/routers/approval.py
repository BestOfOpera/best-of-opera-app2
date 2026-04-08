from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import (
    ProjectOut,
    ApproveOverlayRequest,
    ApprovePostRequest,
    ApproveYoutubeRequest,
)

router = APIRouter(prefix="/api/projects", tags=["approval"])


def _check_and_transition(db: Session, project_id: int) -> None:
    """Transiciona atomicamente para export_ready se todos os campos estiverem aprovados."""
    db.execute(
        update(Project)
        .where(
            Project.id == project_id,
            Project.overlay_approved == True,
            Project.post_approved == True,
            Project.youtube_approved == True,
            Project.status != "export_ready",
        )
        .values(status="export_ready")
    )


@router.put("/{project_id}/approve-overlay", response_model=ProjectOut)
def approve_overlay(
    project_id: int, body: ApproveOverlayRequest, db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.overlay_json = body.overlay_json
    project.overlay_approved = True
    db.flush()

    _check_and_transition(db, project_id)
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/approve-post", response_model=ProjectOut)
def approve_post(
    project_id: int, body: ApprovePostRequest, db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.post_text = body.post_text
    project.post_approved = True
    db.flush()

    _check_and_transition(db, project_id)
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}/approve-youtube", response_model=ProjectOut)
def approve_youtube(
    project_id: int, body: ApproveYoutubeRequest, db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.youtube_title = body.youtube_title
    project.youtube_tags = body.youtube_tags
    project.youtube_approved = True
    db.flush()

    _check_and_transition(db, project_id)
    db.commit()
    db.refresh(project)
    return project
