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


@router.get("/dashboard/visao-geral")
def dashboard_visao_geral(db: Session = Depends(get_db)) -> dict:
    """Visão geral consolidada — formato esperado pelo frontend DashboardVisaoGeral."""
    total = db.query(func.count(Edicao.id)).scalar() or 0

    status_rows = (
        db.query(Edicao.status, func.count(Edicao.id))
        .group_by(Edicao.status)
        .all()
    )
    por_status = {row[0]: row[1] for row in status_rows}

    em_andamento = por_status.get("processando", 0) + por_status.get("renderizando", 0)
    concluidos = por_status.get("concluido", 0)
    em_erro = por_status.get("erro", 0)

    try:
        info = is_worker_busy()
        worker_status = "ocupado" if info.get("ocupado") else "ocioso"
        if info.get("etapa"):
            worker_status += f" — {info['etapa']}"
    except Exception:
        worker_status = "desconhecido"

    # Projetos (todas as edições, mais recentes primeiro)
    edicoes = db.query(Edicao).order_by(Edicao.updated_at.desc()).all()
    projetos = []
    for e in edicoes:
        projetos.append({
            "id": e.id,
            "youtube_url": e.youtube_url or "",
            "youtube_video_id": e.youtube_video_id or "",
            "artista": e.artista or "",
            "musica": e.musica or "",
            "compositor": e.compositor or "",
            "opera": e.opera or "",
            "idioma": e.idioma or "",
            "categoria": e.categoria or "",
            "eh_instrumental": e.eh_instrumental or False,
            "sem_lyrics": e.sem_lyrics or False,
            "status": e.status or "aguardando",
            "cut_start": e.corte_original_inicio,
            "cut_end": e.corte_original_fim,
            "rota_alinhamento": e.rota_alinhamento,
            "confianca_alinhamento": float(e.confianca_alinhamento) if e.confianca_alinhamento else None,
            "duracao_corte_sec": float(e.duracao_corte_sec) if e.duracao_corte_sec else None,
            "janela_inicio_sec": float(e.janela_inicio_sec) if e.janela_inicio_sec else None,
            "janela_fim_sec": float(e.janela_fim_sec) if e.janela_fim_sec else None,
            "letra": None,  # omitido por peso
            "letra_fonte": None,
            "notas_revisao": e.notas_revisao,
            "arquivo_video_completo": bool(e.arquivo_video_completo),
            "arquivo_audio_completo": bool(e.arquivo_audio_completo),
            "passo_atual": e.passo_atual or 1,
            "erro_msg": e.erro_msg,
            "progresso_detalhe": e.progresso_detalhe,
            "task_heartbeat": e.task_heartbeat.isoformat() if e.task_heartbeat else None,
            "created_at": e.created_at.isoformat() if e.created_at else "",
            "updated_at": e.updated_at.isoformat() if e.updated_at else "",
            "link_direto": f"/editor/{e.id}",
        })

    return {
        "resumo": {
            "total": total,
            "em_andamento": em_andamento,
            "concluidos": concluidos,
            "em_erro": em_erro,
            "worker_status": worker_status,
        },
        "projetos": projetos,
    }


@router.get("/dashboard/producao")
def dashboard_producao(db: Session = Depends(get_db)) -> dict:
    """Métricas de produção — formato esperado pelo frontend DashboardProducao."""
    agora = datetime.now(timezone.utc)

    # Gráfico: últimos 30 dias — renders concluídos vs erros por dia
    grafico = []
    for i in range(29, -1, -1):
        dia = (agora - timedelta(days=i)).date()
        dia_inicio = datetime(dia.year, dia.month, dia.day, tzinfo=timezone.utc)
        dia_fim = dia_inicio + timedelta(days=1)

        sucesso = (
            db.query(func.count(Render.id))
            .filter(Render.status == "concluido", Render.created_at >= dia_inicio, Render.created_at < dia_fim)
            .scalar() or 0
        )
        erro = (
            db.query(func.count(Render.id))
            .filter(Render.status == "erro", Render.created_at >= dia_inicio, Render.created_at < dia_fim)
            .scalar() or 0
        )
        grafico.append({"data": dia.isoformat(), "sucesso": sucesso, "erro": erro})

    # Métricas gerais
    total_concluidos = db.query(func.count(Render.id)).filter(Render.status == "concluido").scalar() or 0
    total_erro = db.query(func.count(Render.id)).filter(Render.status == "erro").scalar() or 0
    total_renders = total_concluidos + total_erro
    taxa_sucesso = f"{round(total_concluidos / total_renders * 100)}%" if total_renders > 0 else "0%"

    # Tempo médio (baseado em edições concluídas)
    edicoes_concluidas = (
        db.query(Edicao)
        .filter(Edicao.status == "concluido", Edicao.created_at.isnot(None), Edicao.updated_at.isnot(None))
        .all()
    )
    if edicoes_concluidas:
        tempos = [(e.updated_at - e.created_at).total_seconds() / 3600 for e in edicoes_concluidas]
        media_h = sum(tempos) / len(tempos)
        tempo_medio = f"{media_h:.1f}h" if media_h >= 1 else f"{media_h * 60:.0f}min"
    else:
        tempo_medio = "N/A"

    # Gargalo: etapa com mais erros
    erro_por_passo = (
        db.query(Edicao.passo_atual, func.count(Edicao.id))
        .filter(Edicao.status == "erro")
        .group_by(Edicao.passo_atual)
        .order_by(func.count(Edicao.id).desc())
        .first()
    )
    gargalo = PASSO_LABELS.get(erro_por_passo[0], f"Passo {erro_por_passo[0]}") if erro_por_passo else "Nenhum"

    # Etapas com tempo médio (simplificado: edições que passaram por cada passo)
    etapas = [{"etapa": label, "tempo_medio": "—"} for _, label in sorted(PASSO_LABELS.items())]

    return {
        "grafico": grafico,
        "metricas": {
            "taxa_sucesso": taxa_sucesso,
            "tempo_medio": tempo_medio,
            "gargalo": gargalo,
        },
        "etapas": etapas,
    }


@router.get("/dashboard/saude")
def dashboard_saude(db: Session = Depends(get_db)) -> dict:
    """Saúde do sistema — formato esperado pelo frontend DashboardSaude."""
    # Banco de dados
    banco_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        banco_ok = False

    # Worker
    worker_status = "desconhecido"
    worker_progresso = 0
    try:
        info = is_worker_busy()
        if info.get("ocupado"):
            worker_status = "processando"
            prog = info.get("progresso") or {}
            if isinstance(prog, dict):
                total = prog.get("total", 0)
                concluidos = prog.get("concluidos", 0)
                worker_progresso = round(concluidos / total * 100) if total > 0 else 0
        else:
            worker_status = "ocioso"
    except Exception:
        pass

    # R2
    r2_ok = True
    try:
        from shared.storage_service import StorageService
        s = StorageService()
        s.list_files(prefix="")
    except Exception:
        r2_ok = False

    # Semáforo
    if not banco_ok:
        semaforo = "vermelho"
    elif worker_status == "desconhecido" or not r2_ok:
        semaforo = "amarelo"
    else:
        semaforo = "verde"

    # Fila
    try:
        fila_quantidade = task_queue.qsize()
    except Exception:
        fila_quantidade = 0

    # Próxima task (simplificado)
    proxima_task = None
    if fila_quantidade > 0:
        proxima_task = f"{fila_quantidade} tarefa(s) na fila"

    # Último erro
    ultimo_erro_edicao = (
        db.query(Edicao)
        .filter(Edicao.status == "erro", Edicao.erro_msg.isnot(None))
        .order_by(Edicao.updated_at.desc())
        .first()
    )
    ultimo_erro = None
    if ultimo_erro_edicao:
        ts = ultimo_erro_edicao.updated_at
        if ts:
            delta = datetime.now(timezone.utc) - ts.replace(tzinfo=timezone.utc) if ts.tzinfo is None else datetime.now(timezone.utc) - ts
            minutos = int(delta.total_seconds() / 60)
            if minutos < 60:
                timestamp_str = f"{minutos}min"
            elif minutos < 1440:
                timestamp_str = f"{minutos // 60}h"
            else:
                timestamp_str = f"{minutos // 1440}d"
        else:
            timestamp_str = "?"
        ultimo_erro = {
            "edicao_id": ultimo_erro_edicao.id,
            "msg": ultimo_erro_edicao.erro_msg,
            "timestamp": timestamp_str,
        }

    return {
        "semaforo": semaforo,
        "worker": {
            "status": worker_status,
            "progresso": worker_progresso,
            "uptime": "—",
        },
        "fila": {
            "quantidade": fila_quantidade,
            "proxima_task": proxima_task,
        },
        "ultimo_erro": ultimo_erro,
        "sentry_url": "https://sentry.io",
    }
