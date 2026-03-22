import base64
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import ProjectOut, RegenerateRequest, DetectMetadataResponse  # noqa: F401
from backend.config import load_brand_config
from backend.services.claude_service import generate_overlay, generate_post, generate_youtube, detect_metadata, detect_metadata_from_text

router = APIRouter(prefix="/api/projects", tags=["generation"])


class DetectFromTextRequest(BaseModel):
    youtube_url: str = ""
    title: str = ""
    description: str = ""


@router.post("/detect-metadata-text", response_model=DetectMetadataResponse)
async def detect_metadata_text_endpoint(body: DetectFromTextRequest):
    try:
        result = detect_metadata_from_text(body.youtube_url, body.title, body.description)
        return DetectMetadataResponse(**result)
    except Exception as e:
        print(f"[detect-metadata-text] ERROR: {e}")
        raise HTTPException(500, f"Detection failed: {e}")


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

    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido. Recrie o projeto selecionando uma marca.")
    brand_config = load_brand_config(brand_slug)

    try:
        project.overlay_json = generate_overlay(project, brand_config=brand_config)
        project.post_text = generate_post(project, brand_config=brand_config)
        title, tags = generate_youtube(project, brand_config=brand_config)
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

    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido. Recrie o projeto selecionando uma marca.")
    brand_config = load_brand_config(brand_slug)
    project.overlay_json = generate_overlay(project, body.custom_prompt, brand_config=brand_config)
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

    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido. Recrie o projeto selecionando uma marca.")
    brand_config = load_brand_config(brand_slug)
    project.post_text = generate_post(project, body.custom_prompt, brand_config=brand_config)
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

    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido. Recrie o projeto selecionando uma marca.")
    brand_config = load_brand_config(brand_slug)
    title, tags = generate_youtube(project, body.custom_prompt, brand_config=brand_config)
    project.youtube_title = title
    project.youtube_tags = tags
    project.youtube_approved = False
    if project.status == "export_ready":
        project.status = "awaiting_approval"
    db.commit()
    db.refresh(project)
    return project
