import base64
import logging
from fastapi import APIRouter, Depends, HTTPException, File, Form, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project

logger = logging.getLogger("rc_pipeline")
from backend.schemas import ProjectOut, RegenerateRequest, DetectMetadataResponse, SelectHookRequest  # noqa: F401
from backend.config import load_brand_config
from backend.services.claude_service import (
    generate_overlay, generate_post, generate_youtube, generate_hooks,
    generate_research_bo,
    detect_metadata, detect_metadata_from_text,
    detect_metadata_rc, detect_metadata_from_text_rc,
    generate_research_rc, generate_hooks_rc,
    generate_overlay_rc, generate_post_rc, generate_automation_rc,
)

router = APIRouter(prefix="/api/projects", tags=["generation"])


def _validate_project_metadata(project: Project):
    """Valida campos obrigatórios antes de gerar conteúdo."""
    missing = []
    if not (project.artist or "").strip():
        missing.append("artist")
    if not (project.work or "").strip():
        missing.append("work")
    if not (project.composer or "").strip():
        missing.append("composer")
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Campos obrigatórios vazios: {', '.join(missing)}. "
                   f"Preencha os dados do projeto antes de gerar conteúdo.",
        )


class DetectFromTextRequest(BaseModel):
    youtube_url: str = ""
    title: str = ""
    description: str = ""
    brand_slug: str = ""


@router.post("/detect-metadata-text", response_model=DetectMetadataResponse)
async def detect_metadata_text_endpoint(body: DetectFromTextRequest):
    logger.info(f"[Detect Text] brand_slug='{body.brand_slug}' title='{body.title[:80]}' url='{body.youtube_url[:60]}'")
    try:
        if body.brand_slug == "reels-classics":
            logger.info("[Detect Text] Usando prompt RC")
            result = detect_metadata_from_text_rc(body.youtube_url, body.title, body.description)
        else:
            logger.info("[Detect Text] Usando prompt BO")
            result = detect_metadata_from_text(body.youtube_url, body.title, body.description)
        logger.info(f"[Detect Text] Resultado: {list(result.keys())}")
        return DetectMetadataResponse(**result)
    except Exception as e:
        logger.error(f"[Detect Text] ERROR: {e}")
        raise HTTPException(500, f"Detection failed: {e}")


@router.post("/detect-metadata", response_model=DetectMetadataResponse)
async def detect_metadata_endpoint(
    file: UploadFile = File(...),
    youtube_url: str = Form(""),
    brand_slug: str = Form(""),
):
    try:
        image_bytes = await file.read()
        if not image_bytes:
            raise HTTPException(400, "Empty screenshot file")
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        media_type = file.content_type or "image/png"
        logger.info(f"[Detect Screenshot] file={file.filename} size={len(image_bytes)} type={media_type} url='{youtube_url[:60]}' brand='{brand_slug}'")
        if brand_slug == "reels-classics":
            result = detect_metadata_rc(youtube_url, image_b64, media_type)
        else:
            result = detect_metadata(youtube_url, image_b64, media_type)
        logger.info(f"[Detect Screenshot] Resultado: {list(result.keys())}")
        return DetectMetadataResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Detect Screenshot] ERROR: {e}")
        raise HTTPException(500, f"Detection failed: {e}")


@router.post("/{project_id}/generate", response_model=ProjectOut)
def generate_all(project_id: int, db: Session = Depends(get_db)):
    import time as _time
    _t0 = _time.time()

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    _validate_project_metadata(project)

    project.status = "generating"
    db.commit()

    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido. Recrie o projeto selecionando uma marca.")
    brand_config = load_brand_config(brand_slug)

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
    print(f"[TIMING] generate_all projeto={project_id}: {_time.time() - _t0:.1f}s", flush=True)
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


class RegenerateEntryRequest(BaseModel):
    instruction: str = ""
    brand_slug: str = ""


@router.post("/{project_id}/regenerate-overlay-entry/{entry_index}")
def regenerate_overlay_entry(
    project_id: int,
    entry_index: int,
    body: RegenerateEntryRequest = RegenerateEntryRequest(),
    db: Session = Depends(get_db),
):
    """Regenera UMA legenda específica do overlay, mantendo as demais."""
    from backend.services.claude_service import _call_claude, _enforce_line_breaks_rc

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    overlay = project.overlay_json or []
    if entry_index < 0 or entry_index >= len(overlay):
        raise HTTPException(422, f"Índice {entry_index} fora do range (0-{len(overlay) - 1})")

    entry = overlay[entry_index]
    instruction = body.instruction
    brand_slug = body.brand_slug or getattr(project, "brand_slug", "")
    is_rc = brand_slug == "reels-classics"

    research_data = project.research_data or ""
    research_str = ""
    if isinstance(research_data, dict):
        import json as _json
        research_str = _json.dumps(research_data, ensure_ascii=False)[:2000]
    elif isinstance(research_data, str):
        research_str = research_data[:2000]

    overlay_context = ""
    for i, e in enumerate(overlay):
        marker = " ← REGENERAR ESTA" if i == entry_index else ""
        overlay_context += f"\n[{i + 1}] ({e.get('type', e.get('tipo', 'corpo'))}): {e.get('text', e.get('texto', ''))}{marker}"

    if is_rc:
        limits = "Máximo 33 caracteres por linha. Use \\n para quebras de linha. Máximo 3 linhas (2 para gancho/fechamento)."
    else:
        limits = "Máximo 70 caracteres total. Se > 35 chars, divida em 2 linhas balanceadas com \\n."

    prompt = f"""Reescreva UMA legenda específica de um overlay de vídeo de música clássica.

CONTEXTO — Overlay completo (para coerência narrativa):
{overlay_context}

{f"PESQUISA: {research_str}" if research_str else ""}

LEGENDA A REESCREVER:
Tipo: {entry.get('type', entry.get('tipo', 'corpo'))}
Texto atual: {entry.get('text', entry.get('texto', ''))}

{f'INSTRUÇÃO DO OPERADOR: {instruction}' if instruction else ''}

REGRAS:
{limits}
- Mantenha coerência narrativa com as legendas adjacentes
- Mantenha o tom e estilo do overlay existente
- Seja específico a ESTA performance (use fatos da pesquisa)
- NÃO use emojis, reticências excessivas ou frases genéricas

RESPONDA COM APENAS O NOVO TEXTO (nada mais). Inclua \\n para quebras de linha."""

    try:
        new_text = _call_claude(prompt, temperature=0.8)
    except Exception as e:
        error_str = str(e)
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado.")
        raise HTTPException(500, f"Falha ao regenerar legenda: {error_str}")

    new_text = new_text.strip().strip('"').strip("'")

    if is_rc:
        tipo = entry.get("type", entry.get("tipo", "corpo"))
        new_text = _enforce_line_breaks_rc(new_text, tipo)

    old_text = entry.get("text", entry.get("texto", ""))
    overlay[entry_index]["text"] = new_text
    if "texto" in overlay[entry_index]:
        overlay[entry_index]["texto"] = new_text
    project.overlay_json = overlay
    db.commit()

    return {
        "index": entry_index,
        "old_text": old_text,
        "new_text": new_text,
        "overlay_json": overlay,
    }


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

    _validate_project_metadata(project)

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


@router.post("/{project_id}/generate-research-bo")
def generate_research_bo_endpoint(project_id: int, db: Session = Depends(get_db)):
    """BO: pesquisa aprofundada sobre a obra/artista. Salva em research_data."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    _validate_project_metadata(project)
    brand_slug = getattr(project, 'brand_slug', None)
    if not brand_slug:
        raise HTTPException(400, "Projeto sem brand_slug definido.")
    brand_config = load_brand_config(brand_slug)
    try:
        result = generate_research_bo(project, brand_config=brand_config)
        db.commit()
        logger.info(f"[BO Endpoint] generate-research-bo OK project={project_id}")
        return {"status": "research_complete", "research_data": result}
    except Exception as e:
        db.rollback()
        error_str = str(e)
        logger.error(f"[BO Endpoint] generate-research-bo ERRO project={project_id}: {error_str}")
        if "overloaded" in error_str.lower() or "529" in error_str:
            raise HTTPException(503, "O serviço de IA está temporariamente sobrecarregado. Tente novamente em alguns segundos.")
        raise HTTPException(500, f"Erro na pesquisa BO: {error_str}")


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
        logger.info(f"[RC Endpoint] generate-research-rc OK project={project_id}")
        return {"status": "research_complete", "research_data": result}
    except ValueError as e:
        logger.error(f"[RC Endpoint] generate-research-rc ValueError project={project_id}: {e}")
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        logger.error(f"[RC Endpoint] generate-research-rc ERRO project={project_id}: {error_str}")
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
    brand_config = load_brand_config("reels-classics")
    try:
        result = generate_hooks_rc(project, brand_config=brand_config)
        db.commit()
        logger.info(f"[RC Endpoint] generate-hooks-rc OK project={project_id}")
        return {"status": "hooks_complete", "hooks_json": result}
    except ValueError as e:
        logger.error(f"[RC Endpoint] generate-hooks-rc ValueError project={project_id}: {e}")
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        logger.error(f"[RC Endpoint] generate-hooks-rc ERRO project={project_id}: {error_str}")
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
    brand_config = load_brand_config("reels-classics")
    try:
        result = generate_overlay_rc(project, brand_config=brand_config)
        db.commit()
        logger.info(f"[RC Endpoint] generate-overlay-rc OK project={project_id} legendas={len(result)}")
        return {"status": "overlay_complete", "overlay_json": result}
    except ValueError as e:
        logger.error(f"[RC Endpoint] generate-overlay-rc ValueError project={project_id}: {e}")
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        logger.error(f"[RC Endpoint] generate-overlay-rc ERRO project={project_id}: {error_str}")
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
    brand_config = load_brand_config("reels-classics")
    try:
        result = generate_post_rc(project, brand_config=brand_config)
        db.commit()
        logger.info(f"[RC Endpoint] generate-post-rc OK project={project_id} len={len(result)}")
        return {"status": "post_complete", "post_text": result}
    except ValueError as e:
        logger.error(f"[RC Endpoint] generate-post-rc ValueError project={project_id}: {e}")
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        logger.error(f"[RC Endpoint] generate-post-rc ERRO project={project_id}: {error_str}")
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
        logger.info(f"[RC Endpoint] generate-automation-rc OK project={project_id}")
        return {"status": "automation_complete", "automation_json": result}
    except ValueError as e:
        logger.error(f"[RC Endpoint] generate-automation-rc ValueError project={project_id}: {e}")
        raise HTTPException(502, f"Resposta inválida do Claude: {str(e)}")
    except Exception as e:
        db.rollback()
        error_str = str(e)
        logger.error(f"[RC Endpoint] generate-automation-rc ERRO project={project_id}: {error_str}")
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
