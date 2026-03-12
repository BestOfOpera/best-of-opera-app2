"""Worker sequencial para tarefas de background da curadoria."""
import asyncio
import logging

logger = logging.getLogger(__name__)

# Fila de tarefas
task_queue: asyncio.Queue = asyncio.Queue()


async def worker_loop():
    """Processa tarefas da fila sequencialmente."""
    logger.info("Curadoria worker started")
    while True:
        try:
            coro = await task_queue.get()
            logger.info("Processing background task: %s", coro.__name__ if hasattr(coro, '__name__') else str(coro))
            try:
                if asyncio.iscoroutine(coro):
                    await coro
                elif asyncio.iscoroutinefunction(coro):
                    await coro()
                else:
                    coro()
            except Exception:
                logger.exception("Background task failed")
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            logger.info("Curadoria worker cancelled")
            break
        except BaseException:
            logger.exception("Unexpected error in curadoria worker")
