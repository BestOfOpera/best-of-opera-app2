from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Edicao, Render
from app.worker import is_worker_busy, task_queue

router = APIRouter(prefix="/api/v1/editor", tags=["dashboard"])

PASSO_LABELS = {
    1: "Download",
    2: "Validar Letra",
    3: "Transcrição",
    4: "Alinhamento",
    5: "Corte",
    6: "Tradução",
    7: "Preview",
    8: "Render Final",
    9: "Concluído",
}


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)) -> dict:
    """Retorna resumo geral do sistema."""
    total_edicoes = db.query(func.count(Edicao.id)).scalar() or 0

    status_rows = (
        db.query(Edicao.status, func.count(Edicao.id))
        .group_by(Edicao.status)
        .all()
    )
    por_status = {row[0]: row[1] for row in status_rows}

    renders_concluidos = (
        db.query(func.count(Render.id))
        .filter(Render.status == "concluido")
        .scalar()
        or 0
    )
    renders_com_erro = (
        db.query(func.count(Render.id))
        .filter(Render.status == "erro")
        .scalar()
        or 0
    )

    total_tamanho = (
        db.query(func.sum(Render.tamanho_bytes))
        .filter(Render.status == "concluido")
        .scalar()
        or 0
    )

    media_confianca = (
        db.query(func.avg(Edicao.confianca_alinhamento))
        .filter(Edicao.confianca_alinhamento.isnot(None))
        .scalar()
    )
    if media_confianca is not None:
        media_confianca = round(float(media_confianca), 4)

    agora = datetime.now(timezone.utc)
    h24 = agora - timedelta(hours=24)
    d7 = agora - timedelta(days=7)

    edicoes_24h = (
        db.query(func.count(Edicao.id))
        .filter(Edicao.created_at >= h24)
        .scalar()
        or 0
    )
    edicoes_7d = (
        db.query(func.count(Edicao.id))
        .filter(Edicao.created_at >= d7)
        .scalar()
        or 0
    )

    return {
        "total_edicoes": total_edicoes,
        "por_status": por_status,
        "renders_concluidos": renders_concluidos,
        "renders_com_erro": renders_com_erro,
        "total_tamanho_bytes": total_tamanho,
        "media_confianca_alinhamento": media_confianca,
        "edicoes_ultimas_24h": edicoes_24h,
        "edicoes_ultimas_7d": edicoes_7d,
    }


@router.get("/dashboard/edicoes-recentes")
def dashboard_edicoes_recentes(
    limit: int = 10,
    db: Session = Depends(get_db),
) -> list:
    """Retorna últimas N edições com resumo de renders."""
    limit = min(max(1, limit), 50)

    edicoes = (
        db.query(Edicao)
        .order_by(Edicao.created_at.desc())
        .limit(limit)
        .all()
    )

    edicao_ids = [e.id for e in edicoes]

    renders_ok_rows = (
        db.query(Render.edicao_id, func.count(Render.id).label("cnt"))
        .filter(Render.edicao_id.in_(edicao_ids), Render.status == "concluido")
        .group_by(Render.edicao_id)
        .all()
    )
    renders_ok_map = {row.edicao_id: row.cnt for row in renders_ok_rows}

    renders_total_rows = (
        db.query(Render.edicao_id, func.count(Render.id).label("cnt"))
        .filter(Render.edicao_id.in_(edicao_ids))
        .group_by(Render.edicao_id)
        .all()
    )
    renders_total_map = {row.edicao_id: row.cnt for row in renders_total_rows}

    resultado = []
    for e in edicoes:
        resultado.append(
            {
                "id": e.id,
                "artista": e.artista,
                "musica": e.musica,
                "status": e.status,
                "passo_atual": e.passo_atual,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
                "renders_ok": renders_ok_map.get(e.id, 0),
                "renders_total": renders_total_map.get(e.id, 0),
            }
        )

    return resultado


@router.get("/dashboard/fila")
def dashboard_fila() -> dict:
    """Retorna estado atual do worker e fila de tarefas."""
    info = is_worker_busy()
    return {
        "worker_ocupado": info.get("ocupado", False),
        "edicao_processando": info.get("edicao_id"),
        "etapa_atual": info.get("etapa"),
        "fila_tamanho": task_queue.qsize(),
        "progresso": info.get("progresso") or None,
    }


@router.get("/dashboard/pipeline")
def dashboard_pipeline(db: Session = Depends(get_db)) -> dict:
    """Retorna breakdown por etapa do pipeline."""
    por_passo_total = (
        db.query(Edicao.passo_atual, func.count(Edicao.id).label("total"))
        .group_by(Edicao.passo_atual)
        .all()
    )

    por_passo_erro = (
        db.query(Edicao.passo_atual, func.count(Edicao.id).label("total"))
        .filter(Edicao.status == "erro")
        .group_by(Edicao.passo_atual)
        .all()
    )

    total_map = {row.passo_atual: row.total for row in por_passo_total}
    erro_map = {row.passo_atual: row.total for row in por_passo_erro}

    por_passo = {}
    for passo, label in PASSO_LABELS.items():
        por_passo[str(passo)] = {
            "label": label,
            "total": total_map.get(passo, 0),
            "com_erro": erro_map.get(passo, 0),
        }

    limite_stale = datetime.now(timezone.utc) - timedelta(minutes=5)

    em_processamento_rows = (
        db.query(Edicao.id, Edicao.artista, Edicao.musica, Edicao.passo_atual)
        .filter(Edicao.status == "processando")
        .all()
    )
    em_processamento = [
        {"id": r.id, "artista": r.artista, "musica": r.musica, "passo_atual": r.passo_atual}
        for r in em_processamento_rows
    ]

    stale_rows = (
        db.query(Edicao.id, Edicao.artista, Edicao.musica, Edicao.passo_atual, Edicao.task_heartbeat)
        .filter(
            Edicao.task_heartbeat.isnot(None),
            Edicao.task_heartbeat < limite_stale,
        )
        .all()
    )
    com_heartbeat_stale = [
        {
            "id": r.id,
            "artista": r.artista,
            "musica": r.musica,
            "passo_atual": r.passo_atual,
            "task_heartbeat": r.task_heartbeat.isoformat() if r.task_heartbeat else None,
        }
        for r in stale_rows
    ]

    return {
        "por_passo": por_passo,
        "em_processamento": em_processamento,
        "com_heartbeat_stale": com_heartbeat_stale,
    }


@router.get("/dashboard/saude")
def dashboard_saude(db: Session = Depends(get_db)) -> dict:
    """Verifica saúde dos componentes do sistema."""
    # Banco de dados
    banco_status = "ok"
    total_edicoes = 0
    try:
        db.execute(text("SELECT 1"))
        total_edicoes = db.query(func.count(Edicao.id)).scalar() or 0
    except Exception:
        banco_status = "degraded"

    # Worker
    try:
        info = is_worker_busy()
        worker_status = "busy" if info.get("ocupado") else "idle"
    except Exception:
        worker_status = "unknown"

    # R2
    r2_status = "ok"
    try:
        from shared.storage_service import StorageService

        s = StorageService()
        s.list_files(prefix="")
    except Exception:
        r2_status = "degraded"

    status_geral = "ok"
    if banco_status != "ok" or r2_status != "ok":
        status_geral = "degraded"

    return {
        "banco": banco_status,
        "worker": worker_status,
        "r2": r2_status,
        "total_edicoes": total_edicoes,
        "status": status_geral,
    }
