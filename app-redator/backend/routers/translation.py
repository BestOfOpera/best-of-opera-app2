from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project, Translation
from backend.schemas import ProjectOut
from backend.schemas import RegenerateRequest
from backend.services.translate_service import (
    get_target_languages,
    translate_overlay_json,
    translate_post_text,
    translate_text,
    translate_tags,
)
from backend.services.export_service import save_texts_to_r2
from pydantic import BaseModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class UpdateTranslationRequest(BaseModel):
    overlay_json: Optional[list] = None
    post_text: Optional[str] = None
    youtube_title: Optional[str] = None
    youtube_tags: Optional[str] = None

router = APIRouter(prefix="/api/projects", tags=["translation"])


@router.post("/{project_id}/translate", response_model=ProjectOut)
def translate_project(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    is_rc = getattr(project, 'brand_slug', '') == "reels-classics"
    if is_rc:
        if not (project.overlay_approved and project.post_approved):
            raise HTTPException(400, "Overlay and post must be approved before translation")
    else:
        if not (project.overlay_approved and project.post_approved and project.youtube_approved):
            raise HTTPException(400, "Overlay, post, and YouTube must be approved before translation")

    project.status = "translating"
    db.commit()

    try:
        # Remove existing translations
        db.query(Translation).filter(Translation.project_id == project_id).delete()

        # Original content is always generated in Portuguese (hook categories are in PT).
        # Using detect_language on the hook is unreliable — short hooks with proper
        # nouns (aria names, composers) often get misdetected as another language,
        # causing the source-language copy to land on the wrong slot (e.g. EN gets
        # the untranslated PT overlay).
        source_lang = "pt"
        target_langs = get_target_languages(source_lang)

        # Nomes próprios a preservar durante tradução (artist, work, composer)
        _names = [n for n in [project.artist, project.work, project.composer] if n and len(n) >= 3]

        for lang in target_langs:
            # For the source language, copy original content instead of translating
            if lang == source_lang:
                translated_overlay = project.overlay_json
                translated_post = project.post_text
                translated_title = project.youtube_title
                translated_tags = project.youtube_tags
            else:
                translated_overlay = (
                    translate_overlay_json(project.overlay_json, lang, brand_slug=project.brand_slug,
                                          protected_names=_names)
                    if project.overlay_json
                    else None
                )
                translated_post = (
                    translate_post_text(project.post_text, lang, protected_names=_names)
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

    # Salvar textos no R2 para o Editor consumir
    try:
        save_texts_to_r2(project)
    except Exception as e:
        logger.warning(f"[{project_id}] Falha ao salvar textos no R2: {e}")

    return project


@router.post("/{project_id}/retranslate/{lang}")
def retranslate_language(project_id: int, lang: str, db: Session = Depends(get_db)):
    """Retranslate a single language from the original content."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Remove existing translation for this language
    db.query(Translation).filter(
        Translation.project_id == project_id, Translation.language == lang
    ).delete()

    # Nomes próprios a preservar durante tradução
    _names = [n for n in [project.artist, project.work, project.composer] if n and len(n) >= 3]

    translated_overlay = (
        translate_overlay_json(project.overlay_json, lang, brand_slug=project.brand_slug,
                               protected_names=_names)
        if project.overlay_json
        else None
    )
    translated_post = (
        translate_post_text(project.post_text, lang, protected_names=_names)
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
    db.commit()

    return {
        "language": lang,
        "overlay_json": translation.overlay_json,
        "post_text": translation.post_text,
        "youtube_title": translation.youtube_title,
        "youtube_tags": translation.youtube_tags,
    }


@router.put("/{project_id}/translation/{lang}")
def update_translation(
    project_id: int, lang: str, body: UpdateTranslationRequest, db: Session = Depends(get_db)
):
    """Manually update a translation for a specific language."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    translation = (
        db.query(Translation)
        .filter(Translation.project_id == project_id, Translation.language == lang)
        .first()
    )
    if not translation:
        raise HTTPException(404, f"Translation for {lang} not found")

    if body.overlay_json is not None:
        translation.overlay_json = body.overlay_json
    if body.post_text is not None:
        translation.post_text = body.post_text
    if body.youtube_title is not None:
        translation.youtube_title = body.youtube_title
    if body.youtube_tags is not None:
        translation.youtube_tags = body.youtube_tags

    db.commit()
    return {
        "language": lang,
        "overlay_json": translation.overlay_json,
        "post_text": translation.post_text,
        "youtube_title": translation.youtube_title,
        "youtube_tags": translation.youtube_tags,
    }
