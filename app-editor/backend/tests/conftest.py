"""Fixtures de teste para o app-editor."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base


@pytest.fixture(scope="session")
def engine_mem():
    """Engine SQLite in-memory para testes."""
    _engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=_engine)
    yield _engine
    _engine.dispose()


@pytest.fixture
def db_session(engine_mem):
    """Sessão de banco isolada por teste (rollback no teardown)."""
    Session = sessionmaker(bind=engine_mem)
    session = Session()
    yield session
    session.rollback()
    session.close()
