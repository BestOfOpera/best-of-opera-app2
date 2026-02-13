from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, Translation
from backend.schemas import ProjectOut
from backend.services.translate_service import (
    LANGUAGES,
    translate_overlay_json,
    translate_post_text,
    translate_text,
    translate_tags,
)

router = APIRouter(prefix="/api/projects", tags=["translation"])


@router.post("/{project_id}/translate", response_model=ProjectOut)
def translate_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if not (project.overlay_approved and project.post_approved and project.youtube_approved):
        raise HTTPException(400, "Overlay, post, and YouTube must be approved before translation")

    project.status = "translating"
    db.commit()

    try:
        # Remove existing translations
        db.query(Translation).filter(Translation.project_id == project_id).delete()

        for lang in LANGUAGES:
            translated_overlay = (
                translate_overlay_json(project.overlay_json, lang)
                if project.overlay_json
                else None
            )
            translated_post = (
                translate_post_text(project.post_text, lang)
                if project.post_text
                else None
            )
            translated_title = (
                translate_text(project.youtube_title, lang)
                if project.youtube_title
                else None
            )
            translated_tags = (
                translate_tags(project.youtube_tags, lang)
                if project.youtube_tags
                else None
            )

            translation = Translation(
                project_id=project_id,
                language=lang,
                overlay_json=translated_overlay,
                post_text=translated_post,
                youtube_title=translated_title,
                youtube_tags=translated_tags,
            )
            db.add(translation)

        project.status = "export_ready"
    except Exception as e:
        project.status = "awaiting_approval"
        db.commit()
        raise HTTPException(500, f"Translation failed: {e}")

    db.commit()
    db.refresh(project)
    return project
