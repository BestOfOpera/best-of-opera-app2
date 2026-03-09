"""CRUD de reports de bugs e qualidade."""
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.report import Report
from app.schemas import ReportCreate, ReportUpdate, ReportOut
from shared.storage_service import storage

router = APIRouter(prefix="/api/v1/editor", tags=["reports"])

_MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024  # 10MB


@router.get("/reports", response_model=list[ReportOut])
def listar_reports(
    status: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    edicao_id: Optional[int] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Lista todos os reports com filtros opcionais, ordenados por created_at DESC."""
    q = db.query(Report)
    if status:
        q = q.filter(Report.status == status)
    if tipo:
        q = q.filter(Report.tipo == tipo)
    if edicao_id is not None:
        q = q.filter(Report.edicao_id == edicao_id)
    return q.order_by(Report.created_at.desc()).limit(limit).all()


@router.post("/reports", response_model=ReportOut, status_code=201)
def criar_report(data: ReportCreate, db: Session = Depends(get_db)):
    """Cria um novo report."""
    report = Report(**data.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports/{report_id}", response_model=ReportOut)
def obter_report(report_id: int, db: Session = Depends(get_db)):
    """Retorna um report pelo ID."""
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report não encontrado")
    return report


@router.patch("/reports/{report_id}", response_model=ReportOut)
def atualizar_report(report_id: int, data: ReportUpdate, db: Session = Depends(get_db)):
    """Atualiza status, prioridade e/ou descrição de um report."""
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report não encontrado")

    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(report, key, value)

    if updates.get("status") == "resolvido" and not report.resolvido_em:
        report.resolvido_em = datetime.now(timezone.utc)

    db.commit()
    db.refresh(report)
    return report


@router.post("/reports/{report_id}/screenshot")
async def upload_screenshot(
    report_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Faz upload de screenshot (PNG/JPG) para R2 e atualiza o report."""
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report não encontrado")

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo deve ser uma imagem. Recebido: {file.content_type}",
        )

    conteudo = await file.read()
    if len(conteudo) > _MAX_SCREENSHOT_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Screenshot excede o limite de 10MB ({len(conteudo) / 1024 / 1024:.1f}MB enviado)",
        )

    filename = file.filename or f"screenshot.png"
    local_path = f"/tmp/report_{report_id}_{filename}"

    try:
        with open(local_path, "wb") as f:
            f.write(conteudo)

        r2_key = f"reports/{report_id}/{filename}"
        storage.upload_file(local_path, r2_key)

        report.screenshot_r2_key = r2_key
        db.commit()
        db.refresh(report)

    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

    return {"r2_key": r2_key, "report_id": report_id}


@router.delete("/reports/{report_id}", status_code=204)
def deletar_report(report_id: int, db: Session = Depends(get_db)):
    """Deleta um report. Se tiver screenshot no R2, tenta deletar também."""
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report não encontrado")

    if report.screenshot_r2_key:
        try:
            storage.delete(report.screenshot_r2_key)
        except Exception:
            pass  # Não falha se R2 der erro

    db.delete(report)
    db.commit()
    return Response(status_code=204)
