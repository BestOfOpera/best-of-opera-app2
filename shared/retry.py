"""Decorators de retry com backoff exponencial e jitter.

Uso:
    from shared.retry import async_retry, sync_retry

    @async_retry(max_attempts=3, backoff_base=2, exceptions=(httpx.HTTPError,))
    async def call_api():
        ...

    @sync_retry(max_attempts=3, backoff_base=2, exceptions=(ConnectionError,))
    def call_r2():
        ...

    # Com jitter desativado (para testes):
    @async_retry(max_attempts=3, backoff_base=2, jitter=False)
    async def call_r2():
        ...
"""
import asyncio
import logging
import random
import time
from typing import Tuple, Type

logger = logging.getLogger(__name__)


def async_retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    backoff_max: float = 30.0,
    jitter: bool = True,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """Decorator async com backoff exponencial e jitter opcional.

    Args:
        max_attempts: Número máximo de tentativas (inclui a primeira).
        backoff_base: Base do backoff exponencial em segundos.
                      Espera = backoff_base ** (attempt - 1), limitado a backoff_max.
        backoff_max: Teto do intervalo de espera em segundos.
        jitter: Se True, adiciona ruído aleatório de ±25% ao intervalo.
        exceptions: Tupla de exceções que disparam retry.
                    Exceções fora desta tupla propagam imediatamente.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = min(backoff_base ** (attempt - 1), backoff_max)
                    if jitter:
                        delay *= random.uniform(0.75, 1.25)
                    logger.warning(
                        f"{func.__qualname__} tentativa {attempt}/{max_attempts} falhou "
                        f"({type(exc).__name__}: {exc}) — retry em {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
            logger.error(
                f"{func.__qualname__} falhou após {max_attempts} tentativas: {last_exc}"
            )
            raise last_exc
        wrapper.__wrapped__ = func
        return wrapper
    return decorator


def sync_retry(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    backoff_max: float = 30.0,
    jitter: bool = True,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
):
    """Decorator síncrono com backoff exponencial e jitter opcional.

    Args:
        max_attempts: Número máximo de tentativas (inclui a primeira).
        backoff_base: Base do backoff exponencial em segundos.
        backoff_max: Teto do intervalo de espera em segundos.
        jitter: Se True, adiciona ruído aleatório de ±25% ao intervalo.
        exceptions: Tupla de exceções que disparam retry.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        break
                    delay = min(backoff_base ** (attempt - 1), backoff_max)
                    if jitter:
                        delay *= random.uniform(0.75, 1.25)
                    logger.warning(
                        f"{func.__qualname__} tentativa {attempt}/{max_attempts} falhou "
                        f"({type(exc).__name__}: {exc}) — retry em {delay:.1f}s"
                    )
                    time.sleep(delay)
            logger.error(
                f"{func.__qualname__} falhou após {max_attempts} tentativas: {last_exc}"
            )
            raise last_exc
        wrapper.__wrapped__ = func
        return wrapper
    return decorator
