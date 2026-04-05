"""Endpoints do calendário de produção."""
from datetime import date, datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Project
from backend.schemas import ProjectOut, ScheduleRequest

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


@router.get("")
def get_calendar(
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    brand_slug: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de data inválido. Use YYYY-MM-DD.")

    base_q = db.query(Project)
    if brand_slug:
        base_q = base_q.filter(Project.brand_slug == brand_slug)

    scheduled = (
        base_q.filter(
            Project.scheduled_date.isnot(None),
            Project.scheduled_date >= start,
            Project.scheduled_date <= end,
        )
        .order_by(Project.scheduled_date.asc(), Project.brand_slug.asc())
        .all()
    )

    unscheduled = (
        base_q.filter(Project.scheduled_date.is_(None))
        .order_by(Project.created_at.desc())
        .all()
    )

    return {
        "scheduled": [ProjectOut.model_validate(p) for p in scheduled],
        "unscheduled": [ProjectOut.model_validate(p) for p in unscheduled],
    }


@router.put("/{project_id}/schedule", response_model=ProjectOut)
def schedule_project(
    project_id: int,
    data: ScheduleRequest,
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    project.scheduled_date = data.scheduled_date
    db.commit()
    db.refresh(project)
    return ProjectOut.model_validate(project)
