"""
Conftest GARANTE zero chamadas reais à API Anthropic durante testes.
Não desabilitar fixtures autouse.

Estratégia (belt-and-suspenders) contra cobrança Anthropic acidental:

1. **Variável `TESTING_MODE=1`** setada ANTES de qualquer import de service.
   - Lida no topo deste módulo e propagada via `os.environ`.
   - Services BO V2 leem esta var e abortam com `RuntimeError` se chamarem
     a API real sem mock configurado.

2. **Mock autouse** de `anthropic.Anthropic` substitui o client em todos os
   testes via `monkeypatch`. Cada teste pega o `FakeAnthropicMessages` via
   fixture `anthropic_response` para configurar JSON canned.

3. **Guard nos services**: cada service novo pode chamar
   `_assert_test_mock_configured()` antes da chamada Anthropic — se
   `TESTING_MODE=1` mas o mock não foi configurado, o service para com
   erro claro em vez de bater na API real.

Belt-and-suspenders: mesmo se o monkeypatch falhar, o guard nos services
para a execução. Mesmo se o guard falhar, o monkeypatch retorna fake.
"""
from __future__ import annotations

import os

# Defensivo: setar antes de qualquer import dos services
os.environ.setdefault("TESTING_MODE", "1")

import json  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

import pytest  # noqa: E402


class FakeAnthropicMessages:
    """Substitui `client.messages.create(...)` — retorna JSON canned configurado pelo teste."""

    def __init__(self) -> None:
        self._next_response: tuple[str, str] | None = None
        self._call_count = 0
        self._last_kwargs: dict | None = None

    def set_response(self, content_text: str, stop_reason: str = "end_turn") -> None:
        """Configura a próxima resposta. Chamado por cada teste antes do exercise."""
        self._next_response = (content_text, stop_reason)

    def set_json_response(self, payload: dict, stop_reason: str = "end_turn") -> None:
        """Atalho — empacota dict em JSON e configura."""
        self.set_response(json.dumps(payload, ensure_ascii=False), stop_reason)

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_kwargs(self) -> dict | None:
        return self._last_kwargs

    def create(self, **kwargs):
        self._call_count += 1
        self._last_kwargs = kwargs
        if self._next_response is None:
            raise RuntimeError(
                "Mock Anthropic chamado sem set_response prévio. "
                "Configure via fixture anthropic_response.set_json_response(...) "
                "antes de exercer o código sob teste."
            )
        text, stop = self._next_response
        msg = MagicMock()
        msg.content = [MagicMock(text=text, type="text")]
        msg.stop_reason = stop
        msg.usage = MagicMock(
            input_tokens=100,
            output_tokens=200,
            server_tool_use=MagicMock(web_search_requests=0),
        )
        return msg


class FakeAnthropicClient:
    """Substitui `anthropic.Anthropic(...)` — retorna fake messages."""

    def __init__(self, *args, **kwargs) -> None:
        self.messages = FakeAnthropicMessages()


# Singleton compartilhado entre fixtures (uma instância por sessão)
_FAKE_CLIENT: FakeAnthropicClient | None = None


def _get_fake_client() -> FakeAnthropicClient:
    global _FAKE_CLIENT
    if _FAKE_CLIENT is None:
        _FAKE_CLIENT = FakeAnthropicClient()
    return _FAKE_CLIENT


@pytest.fixture(autouse=True, scope="session")
def _set_testing_mode():
    """Garante `TESTING_MODE=1` ao longo da session.

    Setado no import do conftest (linha topo) — esta fixture é redundante
    propositalmente (belt-and-suspenders).
    """
    prev = os.environ.get("TESTING_MODE")
    os.environ["TESTING_MODE"] = "1"
    yield
    if prev is None:
        os.environ.pop("TESTING_MODE", None)
    else:
        os.environ["TESTING_MODE"] = prev


@pytest.fixture(autouse=True)
def mock_anthropic(monkeypatch):
    """Intercepta TODAS as chamadas a `anthropic.Anthropic(...)`.

    Substitui o constructor para retornar um `FakeAnthropicClient` singleton.
    Reseta o estado do fake (call_count, last_kwargs, _next_response) entre
    testes para evitar vazamento de estado.
    """
    fake = _get_fake_client()
    # Resetar estado entre testes
    fake.messages._call_count = 0
    fake.messages._last_kwargs = None
    fake.messages._next_response = None

    monkeypatch.setattr("anthropic.Anthropic", lambda *a, **kw: fake)
    yield fake


@pytest.fixture
def anthropic_response(mock_anthropic):
    """Retorna o `FakeAnthropicMessages` para o teste configurar resposta canned."""
    return mock_anthropic.messages


@pytest.fixture
def in_memory_db():
    """Cria um banco SQLite in-memory para testes que precisam persistir Project/Translation.

    Importante: importar `backend.models` ANTES de `create_all` para registrar
    as tabelas Project/Translation no Base.metadata. Sem esse import, o Base
    está vazio e `create_all` não cria nada.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from backend.database import Base
    # Side-effect import: registra Project + Translation no Base.metadata
    from backend import models  # noqa: F401

    engine = create_engine("sqlite:///:memory:", echo=False, future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def mock_project(in_memory_db):
    """Factory de `Project` em SQLite in-memory.

    Defaults BO V2 canônicos: `brand_slug='best-of-opera'`, `pipeline_version='v2'`.
    NUNCA usar 'bo' como slug — valor canônico é 'best-of-opera' (verificado em
    routers/projects.py:22 e main.py:39).
    """
    from backend.models import Project

    def _factory(**kwargs):
        defaults = {
            "youtube_url": "https://youtube.com/watch?v=test",
            "artist": "Test Artist",
            "work": "Test Work",
            "composer": "Test Composer",
            "brand_slug": "best-of-opera",
            "pipeline_version": "v2",
        }
        defaults.update(kwargs)
        p = Project(**defaults)
        in_memory_db.add(p)
        in_memory_db.commit()
        in_memory_db.refresh(p)
        return p

    return _factory
