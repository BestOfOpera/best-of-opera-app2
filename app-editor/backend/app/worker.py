"""Worker sequencial com asyncio.Queue para tasks longas.

Substitui BackgroundTasks do FastAPI. Roda uma task por vez no mesmo container.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Fila global — itens: (async_callable, edicao_id)
task_queue: asyncio.Queue = asyncio.Queue()

# Flag real do worker — edicao_id da task em execução (None = idle)
_current_task_edicao_id: int | None = None

# Rastreamento de edicao_ids pendentes na fila (proteção contra enqueue duplicado)
_pending_edicao_ids: set[int] = set()

_STALE_THRESHOLD = timedelta(minutes=5)


async def worker_loop():
    """Consome tasks da fila uma por vez. Roda como asyncio.Task no lifespan."""
    global _current_task_edicao_id
    logger.info("[worker] Worker sequencial iniciado")
    while True:
        try:
            logger.info("[worker] Aguardando próxima task na fila...")
            task_func, edicao_id = await task_queue.get()
            _pending_edicao_ids.discard(edicao_id)
            logger.info(f"[worker] Pegou task edicao_id={edicao_id} queue={task_queue.qsize()} pending={len(_pending_edicao_ids)}")
            _current_task_edicao_id = edicao_id
            try:
                logger.info(f"[worker] Chamando task_func para edicao_id={edicao_id}")
                await task_func(edicao_id)
                logger.info(f"[worker] task_func RETORNOU para edicao_id={edicao_id}")
            except asyncio.CancelledError:
                # Propagar para o shutdown — não engolir CancelledError da task
                raise
            except Exception as e:
                logger.error(
                    f"[worker] Task edicao_id={edicao_id} falhou com exceção não tratada: {e}",
                    exc_info=True,
                )
                # Reportar ao Sentry se configurado
                try:
                    import sentry_sdk
                    sentry_sdk.set_context("edicao", {"id": edicao_id})
                    sentry_sdk.capture_exception(e)
                except Exception:
                    pass
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
                _current_task_edicao_id = None
                task_queue.task_done()
                logger.info(f"[worker] task_done() chamado, fila tem {task_queue.qsize()} items")
        except asyncio.CancelledError:
            logger.info("[worker] CancelledError — encerrando cleanly")
            raise
        except Exception as e:
            # Proteção contra crash inesperado no próprio loop (ex: falha em task_queue.get)
            # O loop NUNCA deve morrer — continuar consumindo a próxima task
            logger.error(f"[worker] Erro inesperado no loop principal: {e}", exc_info=True)


def enqueue_safe(task_func, edicao_id: int) -> bool:
    """Enfileira task com proteção contra duplicatas.

    Retorna True se enfileirou, False se edicao_id já estava pendente ou em execução.
    """
    if edicao_id == _current_task_edicao_id:
        logger.info(f"[worker] enqueue_safe: edicao_id={edicao_id} já em execução — ignorando")
        return False
    if edicao_id in _pending_edicao_ids:
        logger.info(f"[worker] enqueue_safe: edicao_id={edicao_id} já na fila — ignorando")
        return False
    _pending_edicao_ids.add(edicao_id)
    task_queue.put_nowait((task_func, edicao_id))
    logger.info(f"[worker] enqueue_safe: edicao_id={edicao_id} enfileirado queue={task_queue.qsize()}")
    return True


def _make_preview_wrapper(eid: int, idioma: str, sem_legendas: bool = False):
    """Cria wrapper para _render_task com is_preview=True e idioma fixo."""
    async def _preview_task(_ignored_id: int):
        from app.routes.pipeline import _render_task
        await _render_task(eid, idiomas_renderizar=[idioma], is_preview=True, sem_legendas=sem_legendas)
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
    """Verifica se o worker está executando uma task.

    Usa a flag real _current_task_edicao_id (setada pelo worker_loop)
    em vez de consultar o banco, evitando falsos positivos quando o
    status no banco ainda não foi limpo.
    """
    if _current_task_edicao_id is not None:
        from app.database import SessionLocal
        from app.models import Edicao

        with SessionLocal() as db:
            edicao = db.get(Edicao, _current_task_edicao_id)
            if edicao:
                return {
                    "ocupado": True,
                    "edicao_id": edicao.id,
                    "etapa": edicao.status,
                    "progresso": edicao.progresso_detalhe or {},
                }
        # Flag set mas edição não encontrada — inconsistência, reportar idle
        return {"ocupado": False}

    return {"ocupado": False}
