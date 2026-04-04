from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.config import SENTRY_ORG_URL
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


@router.get("/dashboard/visao-geral")
def dashboard_visao_geral(perfil_id: Optional[int] = None, db: Session = Depends(get_db)) -> dict:
    """Visão geral consolidada — formato esperado pelo frontend DashboardVisaoGeral."""
    base_q = db.query(Edicao)
    if perfil_id is not None:
        base_q = base_q.filter(Edicao.perfil_id == perfil_id)

    total = base_q.with_entities(func.count(Edicao.id)).scalar() or 0

    status_rows = (
        base_q.with_entities(Edicao.status, func.count(Edicao.id))
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
    edicoes = base_q.order_by(Edicao.updated_at.desc()).all()
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
def dashboard_producao(perfil_id: Optional[int] = None, db: Session = Depends(get_db)) -> dict:
    """Métricas de produção — formato esperado pelo frontend DashboardProducao."""
    agora = datetime.now(timezone.utc)

    base_q = db.query(Edicao)
    if perfil_id is not None:
        base_q = base_q.filter(Edicao.perfil_id == perfil_id)

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
        base_q
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
        base_q.with_entities(Edicao.passo_atual, func.count(Edicao.id))
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
def dashboard_saude(perfil_id: Optional[int] = None, db: Session = Depends(get_db)) -> dict:
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
    ultimo_erro_q = db.query(Edicao).filter(Edicao.status == "erro", Edicao.erro_msg.isnot(None))
    if perfil_id is not None:
        ultimo_erro_q = ultimo_erro_q.filter(Edicao.perfil_id == perfil_id)
    ultimo_erro_edicao = ultimo_erro_q.order_by(Edicao.updated_at.desc()).first()
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
        "sentry_url": SENTRY_ORG_URL,
    }
