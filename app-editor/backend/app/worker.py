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
            logger.info("[worker] Aguardando próxima task na fila...")
            task_func, edicao_id = await task_queue.get()
            logger.info(f"[worker] Task retirada da fila: edicao_id={edicao_id}")
            try:
                await task_func(edicao_id)
            except asyncio.CancelledError:
                # Propagar para o shutdown — não engolir CancelledError da task
                raise
            except Exception as e:
                logger.error(
                    f"[worker] Task edicao_id={edicao_id} falhou com exceção não tratada: {e}",
                    exc_info=True,
                )
                # Garantir que o status não fique preso — a própria task deveria
                # fazer isso, mas se crashou antes do try-except interno, fazemos aqui
                try:
                    from app.database import SessionLocal
                    from app.models import Edicao
                    with SessionLocal() as db:
                        edicao = db.get(Edicao, edicao_id)
                        if edicao and edicao.status not in ("erro", "concluido", "preview_pronto"):
                            edicao.status = "erro"
                            edicao.erro_msg = f"Falha no worker: {str(e)[:500]}"
                            db.commit()
                            logger.info(f"[worker] Status da edicao_id={edicao_id} marcado como 'erro'")
                except Exception:
                    logger.error(f"[worker] Não conseguiu salvar status 'erro' para edicao_id={edicao_id}")
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            logger.info("[worker] CancelledError — encerrando cleanly")
            raise
        except Exception as e:
            # Proteção contra crash inesperado no próprio loop (ex: falha em task_queue.get)
            # O loop NUNCA deve morrer — continuar consumindo a próxima task
            logger.error(f"[worker] Erro inesperado no loop principal: {e}", exc_info=True)


def _make_preview_wrapper(eid: int, idioma: str):
    """Cria wrapper para _render_task com is_preview=True e idioma fixo."""
    async def _preview_task(_ignored_id: int):
        from app.routes.pipeline import _render_task
        await _render_task(eid, idiomas_renderizar=[idioma], is_preview=True)
    return _preview_task


def requeue_stale_tasks():
    """Recoloca na fila TODAS as edições em status de processamento no startup.

    No startup, qualquer edição presa em "traducao"/"renderizando"/"preview"
    é reagendada incondicionalmente — sem verificar heartbeat.
    NÃO atualiza o heartbeat — a própria task faz isso quando começa a rodar.
    """
    from app.database import SessionLocal
    from app.models import Edicao
    from app.routes.pipeline import _traducao_task, _render_task

    with SessionLocal() as db:
        candidatos = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).all()

        requeued = 0
        dead_lettered = 0
        for edicao in candidatos:
            eid, status = edicao.id, edicao.status
            tentativas = edicao.tentativas_requeue or 0

            # Dead-letter: após 3 tentativas, não reenfileirar
            if tentativas >= 3:
                edicao.status = "erro"
                edicao.erro_msg = (
                    "Falha após 3 tentativas de recovery automático. "
                    "Use Desbloquear para retry manual."
                )
                db.commit()
                dead_lettered += 1
                logger.warning(
                    f"[worker] dead-letter: edicao_id={eid} status={status} "
                    f"tentativas={tentativas} — movida para erro"
                )
                continue

            # Incrementar contador e reenfileirar
            edicao.tentativas_requeue = tentativas + 1
            db.commit()

            if status == "traducao":
                task_queue.put_nowait((_traducao_task, eid))
            elif status == "renderizando":
                task_queue.put_nowait((_render_task, eid))
            elif status == "preview":
                idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
                task_queue.put_nowait((_make_preview_wrapper(eid, idioma_preview), eid))

            requeued += 1
            logger.info(
                f"[worker] requeue: edicao_id={eid} status={status} "
                f"tentativa={tentativas + 1}/3 reagendada"
            )

    logger.info(
        f"[worker] requeue_stale_tasks: {requeued} reagendada(s), "
        f"{dead_lettered} dead-letter(s)"
    )


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
