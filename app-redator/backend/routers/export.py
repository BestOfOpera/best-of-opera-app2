from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.config import EXPORT_PATH
from backend.database import get_db
from backend.models import Project, Translation
from backend.services.srt_service import generate_srt
from backend.services.export_service import build_export_zip, export_to_folder, save_texts_to_r2

router = APIRouter(prefix="/api/projects", tags=["export"])


@router.get("/export-config")
def get_export_config():
    """Return export configuration (whether folder export is available)."""
    return {"export_path": EXPORT_PATH or None}


@router.get("/{project_id}/export/{lang}")
def export_language(project_id: int, lang: str, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # "original" means the project's own content (whatever language the hook was in)
    if lang == "original":
        return {
            "language": "original",
            "overlay_json": project.overlay_json,
            "post_text": project.post_text,
            "youtube_title": project.youtube_title,
            "youtube_tags": project.youtube_tags,
            "srt": generate_srt(project.overlay_json, project.cut_end) if project.overlay_json else "",
        }

    translation = (
        db.query(Translation)
        .filter(Translation.project_id == project_id, Translation.language == lang)
        .first()
    )
    if not translation:
        raise HTTPException(404, f"Translation for {lang} not found")

    return {
        "language": lang,
        "overlay_json": translation.overlay_json,
        "post_text": translation.post_text,
        "youtube_title": translation.youtube_title,
        "youtube_tags": translation.youtube_tags,
        "srt": generate_srt(translation.overlay_json, project.cut_end) if translation.overlay_json else "",
    }


@router.post("/{project_id}/save-to-r2")
def save_to_r2(project_id: int, db: Session = Depends(get_db)):
    """Salva todos os textos do projeto no R2 para o Editor consumir."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    save_texts_to_r2(project)
    from shared.storage_service import project_base
    base = project_base(project.artist, project.work)
    return {"ok": True, "r2_base": base}


@router.get("/{project_id}/export-zip")
def export_zip(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Também salva no R2 ao gerar ZIP
    try:
        save_texts_to_r2(project)
    except Exception:
        pass  # Non-critical

    zip_bytes = build_export_zip(project)
    slug = f"{project.artist}_{project.work}".replace(" ", "_")

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{slug}.zip"'},
    )


@router.post("/{project_id}/export-to-folder")
def export_to_folder_route(project_id: int, db: Session = Depends(get_db)):
    if not EXPORT_PATH:
        raise HTTPException(400, "EXPORT_PATH not configured")

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Também salva no R2
    try:
        save_texts_to_r2(project)
    except Exception:
        pass  # Non-critical

    folder = export_to_folder(project, EXPORT_PATH)
    return {"path": folder}
