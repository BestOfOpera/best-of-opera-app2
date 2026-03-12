"""CRUD de reports de bugs e qualidade."""
import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.edicao import Edicao
from app.models.report import Report
from app.schemas import ReportCreate, ReportUpdate, ReportOut
from shared.storage_service import storage

router = APIRouter(prefix="/api/v1/editor", tags=["reports"])

_MAX_SCREENSHOT_BYTES = 10 * 1024 * 1024  # 10MB


def _report_to_dict(report: Report) -> dict:
    """Converte Report ORM em dict compatível com ReportOut, gerando URLs presigned."""
    keys: list[str] = json.loads(report.screenshots_json or "[]")
    screenshots: list[str] = []
    for key in keys:
        try:
            screenshots.append(storage.get_presigned_url(key, expires_in=7200))
        except Exception:
            pass  # ignora chave inválida

    return {
        "id": report.id,
        "colaborador": report.colaborador or "",
        "titulo": report.titulo,
        "descricao": report.descricao,
        "tipo": report.tipo,
        "prioridade": report.prioridade,
        "status": report.status,
        "projeto_id": report.projeto_id,
        "screenshots": screenshots,
        "resolucao": report.resolucao,
        "resolvido_por": report.resolvido_por,
        "codigo_err": report.codigo_err,
        "created_at": report.created_at,
    }


@router.get("/reports", response_model=list[ReportOut])
def listar_reports(
    status: Optional[str] = Query(None),
    tipo: Optional[str] = Query(None),
    edicao_id: Optional[int] = Query(None),
    perfil_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Report)
    if perfil_id is not None:
        q = q.join(Edicao, Report.edicao_id == Edicao.id).filter(Edicao.perfil_id == perfil_id)
    if status:
        q = q.filter(Report.status == status)
    if tipo:
        q = q.filter(Report.tipo == tipo)
    if edicao_id is not None:
        q = q.filter(Report.edicao_id == edicao_id)
    reports = q.order_by(Report.created_at.desc()).limit(limit).all()
    return [_report_to_dict(r) for r in reports]


@router.post("/reports", response_model=ReportOut, status_code=201)
def criar_report(data: ReportCreate, db: Session = Depends(get_db)):
    report = Report(
        edicao_id=data.edicao_id,
        projeto_id=data.projeto_id,
        colaborador=data.colaborador,
        tipo=data.tipo,
        titulo=data.titulo,
        descricao=data.descricao,
        prioridade=data.prioridade or "media",
        status="novo",
        screenshots_json="[]",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_to_dict(report)


@router.get("/reports/resumo")
def resumo_reports(
    perfil_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Retorna contagens por status compatíveis com o frontend."""
    q = db.query(Report.status, func.count(Report.id))
    if perfil_id is not None:
        q = q.join(Edicao, Report.edicao_id == Edicao.id).filter(Edicao.perfil_id == perfil_id)
    counts = q.group_by(Report.status).all()
    by_status: dict[str, int] = {row[0]: row[1] for row in counts}
    return {
        "novos": by_status.get("novo", 0),
        "em_analise": by_status.get("analise", 0),
        "resolvidos": by_status.get("resolvido", 0),
    }


@router.get("/reports/{report_id}", response_model=ReportOut)
def obter_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report não encontrado")
    return _report_to_dict(report)


@router.patch("/reports/{report_id}", response_model=ReportOut)
def atualizar_report(report_id: int, data: ReportUpdate, db: Session = Depends(get_db)):
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
    return _report_to_dict(report)


@router.post("/reports/{report_id}/screenshot")
async def upload_screenshot(
    report_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
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

    filename = file.filename or "screenshot.png"
    local_path = f"/tmp/report_{report_id}_{filename}"

    try:
        with open(local_path, "wb") as f:
            f.write(conteudo)

        r2_key = f"reports/{report_id}/{filename}"
        storage.upload_file(local_path, r2_key)

        keys: list[str] = json.loads(report.screenshots_json or "[]")
        keys.append(r2_key)
        report.screenshots_json = json.dumps(keys)
        db.commit()
        db.refresh(report)

    finally:
        if os.path.exists(local_path):
            os.remove(local_path)

    return {"r2_key": r2_key, "report_id": report_id}


@router.delete("/reports/resolvidos")
def deletar_reports_resolvidos(
    perfil_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Deleta reports com status 'resolvido' + screenshots R2. Filtra por perfil_id se fornecido."""
    q = db.query(Report).filter(Report.status == "resolvido")
    if perfil_id is not None:
        q = q.join(Edicao, Report.edicao_id == Edicao.id).filter(Edicao.perfil_id == perfil_id)
    reports = q.all()
    if not reports:
        return {"deleted": 0}

    count = 0
    for report in reports:
        keys: list[str] = json.loads(report.screenshots_json or "[]")
        for key in keys:
            try:
                storage.delete(key)
            except Exception:
                pass
        db.delete(report)
        count += 1

    db.commit()
    return {"deleted": count}


@router.delete("/reports/{report_id}", status_code=204)
def deletar_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(Report, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report não encontrado")

    keys: list[str] = json.loads(report.screenshots_json or "[]")
    for key in keys:
        try:
            storage.delete(key)
        except Exception:
            pass

    db.delete(report)
    db.commit()
    return Response(status_code=204)
