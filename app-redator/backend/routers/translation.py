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
    translate_project_parallel,
    translate_one_claude,
    RC_CTA,
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
    import time as _time
    _t0 = _time.time()

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
        _names = [n for n in [project.artist, project.work, project.composer] if n and len(n) >= 2]

        # Idiomas que precisam tradução (excluindo source)
        langs_to_translate = [l for l in target_langs if l != source_lang]

        # Traduzir overlay + post via Claude em paralelo (6 idiomas simultâneos)
        # Fallback automático para Google se Claude falhar
        claude_results = {}
        if project.overlay_json or project.post_text:
            claude_results = translate_project_parallel(
                project=project,
                overlay_json=project.overlay_json or [],
                post_text=project.post_text or "",
                brand_slug=project.brand_slug or "",
                target_languages=langs_to_translate,
            )

        for lang in target_langs:
            if lang == source_lang:
                # Cópia do original para idioma fonte
                translated_overlay = project.overlay_json
                translated_post = project.post_text
                translated_title = project.youtube_title
                translated_tags_val = project.youtube_tags
            else:
                cr = claude_results.get(lang)
                if cr and cr.get("data"):
                    # Claude/fallback já traduziu overlay + post
                    translated_overlay = cr["data"].get("overlay")
                    translated_post = cr["data"].get("post", "")
                    logger.info(f"[{project_id}] {lang}: {cr.get('source', '?')} para overlay+post")
                else:
                    # Sem resultado — fallback Google direto
                    translated_overlay = (
                        translate_overlay_json(project.overlay_json, lang,
                                              brand_slug=project.brand_slug,
                                              protected_names=_names)
                        if project.overlay_json else None
                    )
                    translated_post = (
                        translate_post_text(project.post_text, lang, protected_names=_names)
                        if project.post_text else None
                    )

                # Tags e YouTube: SEMPRE Google (conteúdo simples, rápido, barato)
                translated_title = (
                    translate_text(project.youtube_title, lang)
                    if project.youtube_title else None
                )
                translated_tags_val = (
                    translate_tags(project.youtube_tags, lang)
                    if project.youtube_tags else None
                )

            translation = Translation(
                project_id=project_id,
                language=lang,
                overlay_json=translated_overlay,
                post_text=translated_post,
                youtube_title=translated_title,
                youtube_tags=translated_tags_val,
            )
            db.add(translation)

        project.status = "export_ready"
    except Exception as e:
        project.status = "awaiting_approval"
        db.commit()
        raise HTTPException(500, f"Translation failed: {e}")

    db.commit()
    db.refresh(project)
    print(f"[TIMING] translate_project projeto={project_id}: {_time.time() - _t0:.1f}s", flush=True)

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
    _names = [n for n in [project.artist, project.work, project.composer] if n and len(n) >= 2]

    # Tentar Claude para overlay + post (1 idioma)
    translated_overlay = None
    translated_post = None
    if project.overlay_json or project.post_text:
        from backend.services.claude_service import _enforce_line_breaks_rc, _enforce_line_breaks_bo
        claude_result = translate_one_claude(
            overlay_json=project.overlay_json or [],
            post_text=project.post_text or "",
            target_lang=lang,
            brand_slug=project.brand_slug or "",
            project=project,
        )
        if claude_result and claude_result.get("overlay") and claude_result.get("post"):
            is_rc = getattr(project, "brand_slug", "") == "reels-classics"
            safe_overlay = []
            for i, orig_entry in enumerate(project.overlay_json or []):
                ce = next((e for e in claude_result["overlay"] if e.get("index") == i + 1), None)
                t_text = ce.get("text", "") if ce else orig_entry.get("text", "")
                if orig_entry.get("_is_cta") and is_rc:
                    t_text = RC_CTA.get(lang, RC_CTA.get("en", t_text))
                elif not orig_entry.get("_is_cta"):
                    if is_rc:
                        tipo = orig_entry.get("type", "corpo")
                        t_text = _enforce_line_breaks_rc(t_text, tipo, 33, lang=lang)
                    elif len(t_text) > 70:
                        t_text = _enforce_line_breaks_bo(t_text, max_chars_linha=35, max_linhas=2)
                item = {"timestamp": orig_entry.get("timestamp", ""), "text": t_text}
                if orig_entry.get("_is_cta"):
                    item["_is_cta"] = True
                if "end" in orig_entry:
                    item["end"] = orig_entry["end"]
                if "type" in orig_entry:
                    item["type"] = orig_entry["type"]
                safe_overlay.append(item)
            translated_overlay = safe_overlay
            translated_post = claude_result["post"]
            logger.info(f"[{project_id}] retranslate {lang}: Claude OK")

    # Fallback Google se Claude não retornou
    if translated_overlay is None and project.overlay_json:
        translated_overlay = translate_overlay_json(
            project.overlay_json, lang, brand_slug=project.brand_slug, protected_names=_names
        )
    if translated_post is None and project.post_text:
        translated_post = translate_post_text(project.post_text, lang, protected_names=_names)
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
