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
            logger.info(f"[worker] Pegou task edicao_id={edicao_id} queue={task_queue.qsize()}")
            try:
                await task_func(edicao_id)
                logger.info(f"[worker] Terminou task edicao_id={edicao_id}")
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
    """No startup, marca como erro TODAS as edições presas em status ativo.

    NÃO reenfileira automaticamente — evita tasks fantasma que competem
    com tasks novas disparadas pelo usuário. O usuário pode re-disparar
    manualmente via botão Desbloquear na UI.
    """
    from app.database import SessionLocal
    from app.models import Edicao

    with SessionLocal() as db:
        candidatos = db.query(Edicao).filter(
            Edicao.status.in_(["baixando", "transcricao", "traducao", "renderizando", "preview"])
        ).all()

        marcados = 0
        for edicao in candidatos:
            eid, status = edicao.id, edicao.status
            edicao.status = "erro"
            edicao.erro_msg = "Interrompido por restart do servidor. Use Desbloquear para retomar."
            edicao.task_heartbeat = None
            edicao.progresso_detalhe = {}
            db.commit()
            marcados += 1
            logger.info(
                f"[worker] startup: edicao_id={eid} status={status} → erro "
                f"(interrompido por restart)"
            )

    logger.info(f"[worker] requeue_stale_tasks: {marcados} edição(ões) marcada(s) como erro")


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
