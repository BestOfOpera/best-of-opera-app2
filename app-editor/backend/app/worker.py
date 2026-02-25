"""Worker sequencial com asyncio.Queue para tasks longas.

Substitui BackgroundTasks do FastAPI. Roda uma task por vez no mesmo container.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Fila global — itens: (async_callable, edicao_id)
task_queue: asyncio.Queue = asyncio.Queue()

_STALE_THRESHOLD = timedelta(minutes=5)


async def worker_loop():
    """Consome tasks da fila uma por vez. Roda como asyncio.Task no lifespan."""
    logger.info("[worker] Worker sequencial iniciado")
    while True:
        try:
            task_func, edicao_id = await task_queue.get()
            logger.info(f"[worker] Iniciando task edicao_id={edicao_id}")
            try:
                await task_func(edicao_id)
            except Exception as e:
                logger.error(
                    f"[worker] Task edicao_id={edicao_id} falhou com exceção não tratada: {e}",
                    exc_info=True,
                )
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            logger.info("[worker] CancelledError — encerrando cleanly")
            raise


def _make_preview_wrapper(eid: int, idioma: str):
    """Cria wrapper para _render_task com is_preview=True e idioma fixo."""
    async def _preview_task(_ignored_id: int):
        from app.routes.pipeline import _render_task
        await _render_task(eid, idiomas_renderizar=[idioma], is_preview=True)
    return _preview_task


def requeue_stale_tasks():
    """Detecta edições travadas no startup (heartbeat expirado ou NULL) e recoloca na fila.

    NÃO atualiza o heartbeat — a própria task faz isso quando começa a rodar.
    """
    from app.database import SessionLocal
    from app.models import Edicao
    from app.routes.pipeline import _traducao_task, _render_task

    now = datetime.now(timezone.utc)

    with SessionLocal() as db:
        candidatos = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).all()

        requeued = 0
        for edicao in candidatos:
            hb = edicao.task_heartbeat
            if hb is None:
                is_stale = True
            else:
                # Normalizar para UTC se sem tzinfo (PostgreSQL pode retornar naive)
                if hb.tzinfo is None:
                    hb = hb.replace(tzinfo=timezone.utc)
                is_stale = (now - hb) > _STALE_THRESHOLD

            if not is_stale:
                logger.info(
                    f"[worker] requeue: edicao_id={edicao.id} status={edicao.status} "
                    "heartbeat recente, ignorando"
                )
                continue

            eid, status, idioma = edicao.id, edicao.status, edicao.idioma

            if status == "traducao":
                task_queue.put_nowait((_traducao_task, eid))
            elif status == "renderizando":
                task_queue.put_nowait((_render_task, eid))
            elif status == "preview":
                task_queue.put_nowait((_make_preview_wrapper(eid, idioma), eid))

            requeued += 1
            logger.info(f"[worker] requeue: edicao_id={eid} status={status} reagendada")

    logger.info(f"[worker] requeue_stale_tasks: {requeued} task(s) reagendada(s)")


def is_worker_busy() -> dict:
    """Verifica se há edição sendo processada ativamente."""
    from app.database import SessionLocal
    from app.models import Edicao

    with SessionLocal() as db:
        em_proc = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).first()

        if em_proc:
            resultado = {
                "ocupado": True,
                "edicao_id": em_proc.id,
                "etapa": em_proc.status,
                "progresso": em_proc.progresso_detalhe or {},
            }
        else:
            resultado = {"ocupado": False}

    return resultado
