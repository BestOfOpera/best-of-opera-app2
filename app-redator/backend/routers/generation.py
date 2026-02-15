import base64
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import ProjectOut, RegenerateRequest, DetectMetadataResponse  # noqa: F401
from backend.services.claude_service import generate_overlay, generate_post, generate_youtube, detect_metadata

router = APIRouter(prefix="/api/projects", tags=["generation"])


@router.post("/detect-metadata", response_model=DetectMetadataResponse)
async def detect_metadata_endpoint(
    screenshot: UploadFile = File(...),
    youtube_url: str = Form(""),
):
    try:
        image_bytes = await screenshot.read()
        if not image_bytes:
            raise HTTPException(400, "Empty screenshot file")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        media_type = screenshot.content_type or "image/png"
        print(f"[detect-metadata] file={screenshot.filename} size={len(image_bytes)} type={media_type} url={youtube_url}")
        result = detect_metadata(youtube_url, image_b64, media_type)
        print(f"[detect-metadata] result={result}")
        return DetectMetadataResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[detect-metadata] ERROR: {e}")
        raise HTTPException(500, f"Detection failed: {e}")


@router.post("/{project_id}/generate", response_model=ProjectOut)
def generate_all(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.status = "generating"
    db.commit()

    try:
        project.overlay_json = generate_overlay(project)
        project.post_text = generate_post(project)
        title, tags = generate_youtube(project)
        project.youtube_title = title
        project.youtube_tags = tags
        project.status = "awaiting_approval"
        project.overlay_approved = False
        project.post_approved = False
        project.youtube_approved = False
    except Exception as e:
        project.status = "input_complete"
        db.commit()
        raise HTTPException(500, f"Generation failed: {e}")

    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/regenerate-overlay", response_model=ProjectOut)
def regenerate_overlay(
    project_id: int, body: RegenerateRequest = RegenerateRequest(), db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.overlay_json = generate_overlay(project, body.custom_prompt)
    project.overlay_approved = False
    if project.status == "export_ready":
        project.status = "awaiting_approval"
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/regenerate-post", response_model=ProjectOut)
def regenerate_post(
    project_id: int, body: RegenerateRequest = RegenerateRequest(), db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    project.post_text = generate_post(project, body.custom_prompt)
    project.post_approved = False
    if project.status == "export_ready":
        project.status = "awaiting_approval"
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/regenerate-youtube", response_model=ProjectOut)
def regenerate_youtube(
    project_id: int, body: RegenerateRequest = RegenerateRequest(), db: Session = Depends(get_db)
):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    title, tags = generate_youtube(project, body.custom_prompt)
    project.youtube_title = title
    project.youtube_tags = tags
    project.youtube_approved = False
    if project.status == "export_ready":
        project.status = "awaiting_approval"
    db.commit()
    db.refresh(project)
    return project
