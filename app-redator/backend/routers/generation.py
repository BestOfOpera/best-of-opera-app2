import base64
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import ProjectOut, RegenerateRequest, DetectMetadataResponse, SelectHookRequest  # noqa: F401
from backend.config import load_brand_config
from backend.services.claude_service import (
    generate_overlay, generate_post, generate_youtube, generate_hooks,
    detect_metadata, detect_metadata_from_text,
    generate_research_rc, generate_hooks_rc,
    generate_overlay_rc, generate_post_rc, generate_automation_rc,
)

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
    print(f"[generate] project={project_id} brand_slug={brand_slug} "
          f"identity={brand_config.get('identity_prompt_redator', '')[:60]}... "
          f"brand_name={brand_config.get('brand_name', 'N/A')}")

    warnings = []
    try:
        # Post PRIMEIRO: fornece material narrativo para o overlay via fallback
        post_result = generate_post(project, brand_config=brand_config)
        project.post_text = post_result["text"]
        if post_result.get("warning"):
            warnings.append(post_result["warning"])
        project.overlay_json = generate_overlay(project, brand_config=brand_config)
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
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Generation failed: {e}")

    db.commit()
    db.refresh(project)
    out = ProjectOut.model_validate(project)
    out.warnings = warnings
    return out


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
    try:
        project.overlay_json = generate_overlay(project, body.custom_prompt, brand_config=brand_config)
    except Exception as e:
        if "overloaded" in str(e).lower() or "529" in str(e):
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise
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
    try:
        post_result = generate_post(project, body.custom_prompt, brand_config=brand_config)
    except Exception as e:
        if "overloaded" in str(e).lower() or "529" in str(e):
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise
    project.post_text = post_result["text"]
    project.post_approved = False
    if project.status == "export_ready":
        project.status = "awaiting_approval"
    db.commit()
    db.refresh(project)
    out = ProjectOut.model_validate(project)
    if post_result.get("warning"):
        out.warnings = [post_result["warning"]]
    return out


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
    try:
        title, tags = generate_youtube(project, body.custom_prompt, brand_config=brand_config)
    except Exception as e:
        if "overloaded" in str(e).lower() or "529" in str(e):
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise
    project.youtube_title = title
    project.youtube_tags = tags
    project.youtube_approved = False
    if project.status == "export_ready":
        project.status = "awaiting_approval"
    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/generate-hooks")
def generate_hooks_endpoint(project_id: int, db: Session = Depends(get_db)):
    """Gera 5 hooks específicos ao vídeo para o operador escolher.
    Retorna JSON array sem alterar o Project."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido.")
    brand_config = load_brand_config(brand_slug)

    try:
        hooks = generate_hooks(project, brand_config=brand_config)
        return {"hooks": hooks}
    except Exception as e:
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Hook generation failed: {e}")


# ── RC (Reels Classics) endpoints ──────────────────────────────

@router.post("/{project_id}/generate-research-rc")
def generate_research_rc_endpoint(project_id: int, db: Session = Depends(get_db)):
    """RC: pesquisa aprofundada sobre a obra/artista."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if getattr(project, 'brand_slug', '') != "reels-classics":
        raise HTTPException(400, "Este endpoint é exclusivo para Reels Classics")
    try:
        result = generate_research_rc(project)
        db.commit()
        return {"status": "research_complete", "research_data": result}
    except ValueError as e:
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Erro na geração RC: {error_str}")


@router.post("/{project_id}/generate-hooks-rc")
def generate_hooks_rc_endpoint(project_id: int, db: Session = Depends(get_db)):
    """RC: gera hooks baseados na pesquisa."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if getattr(project, 'brand_slug', '') != "reels-classics":
        raise HTTPException(400, "Este endpoint é exclusivo para Reels Classics")
    if not project.research_data:
        raise HTTPException(400, "Gere a pesquisa primeiro (generate-research-rc)")
    try:
        result = generate_hooks_rc(project)
        db.commit()
        return {"status": "hooks_complete", "hooks_json": result}
    except ValueError as e:
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Erro na geração RC: {error_str}")


@router.put("/{project_id}/select-hook", response_model=ProjectOut)
def select_hook(
    project_id: int,
    body: SelectHookRequest,
    db: Session = Depends(get_db),
):
    """RC: seleciona um hook do hooks_json ou define um custom."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if body.hook_index is not None:
        if not project.hooks_json or "ganchos" not in project.hooks_json:
            raise HTTPException(400, "Gere os ganchos primeiro (generate-hooks-rc)")
        if body.hook_index >= len(project.hooks_json["ganchos"]):
            raise HTTPException(400, f"hook_index {body.hook_index} fora do range (max: {len(project.hooks_json['ganchos']) - 1})")
        texto = project.hooks_json["ganchos"][body.hook_index]["texto"]
        project.selected_hook = texto
        project.hook = texto
    elif body.custom_hook:
        project.selected_hook = body.custom_hook
        project.hook = body.custom_hook

    db.commit()
    db.refresh(project)
    return project


@router.post("/{project_id}/generate-overlay-rc")
def generate_overlay_rc_endpoint(project_id: int, db: Session = Depends(get_db)):
    """RC: gera overlay baseado no hook selecionado."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if getattr(project, 'brand_slug', '') != "reels-classics":
        raise HTTPException(400, "Este endpoint é exclusivo para Reels Classics")
    if not project.selected_hook:
        raise HTTPException(400, "Selecione um gancho primeiro (select-hook)")
    try:
        result = generate_overlay_rc(project)
        db.commit()
        return {"status": "overlay_complete", "overlay_json": result}
    except ValueError as e:
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Erro na geração RC: {error_str}")


@router.post("/{project_id}/generate-post-rc")
def generate_post_rc_endpoint(project_id: int, db: Session = Depends(get_db)):
    """RC: gera post/caption baseado no hook selecionado."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if getattr(project, 'brand_slug', '') != "reels-classics":
        raise HTTPException(400, "Este endpoint é exclusivo para Reels Classics")
    if not project.overlay_json:
        raise HTTPException(400, "Gere o overlay primeiro (generate-overlay-rc)")
    try:
        result = generate_post_rc(project)
        db.commit()
        return {"status": "post_complete", "post_text": result}
    except ValueError as e:
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Erro na geração RC: {error_str}")


@router.post("/{project_id}/generate-automation-rc")
def generate_automation_rc_endpoint(project_id: int, db: Session = Depends(get_db)):
    """RC: gera automation JSON."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    if getattr(project, 'brand_slug', '') != "reels-classics":
        raise HTTPException(400, "Este endpoint é exclusivo para Reels Classics")
    if not project.post_text:
        raise HTTPException(400, "Gere a descrição primeiro (generate-post-rc)")
    try:
        result = generate_automation_rc(project)
        db.commit()
        return {"status": "automation_complete", "automation_json": result}
    except ValueError as e:
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Erro na geração RC: {error_str}")


@router.put("/{project_id}/approve-automation", response_model=ProjectOut)
def approve_automation(project_id: int, db: Session = Depends(get_db)):
    """RC: aprova o automation_json gerado."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    if not project.automation_json:
        raise HTTPException(400, "No automation_json to approve")

    project.automation_approved = True
    db.commit()
    db.refresh(project)
    return project
