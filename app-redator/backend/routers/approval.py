from fastapi import APIRouter, Depends, HTTPException
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


@router.put("/{project_id}/approve-overlay", response_model=ProjectOut)
def approve_overlay(
    project_id: int, body: ApproveOverlayRequest, db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.overlay_json = body.overlay_json
    project.overlay_approved = True
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

    # If all approved, mark as export_ready
    if project.overlay_approved and project.post_approved and project.youtube_approved:
        project.status = "export_ready"

    db.commit()
    db.refresh(project)
    return project
