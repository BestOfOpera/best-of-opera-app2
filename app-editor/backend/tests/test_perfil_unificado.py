"""Testes — Prompt 1.5: Perfil unificado editor+curadoria.

Estratégia: testes leves sem importar app.main (evita dependência de shared/).
Testa diretamente modelos, helper functions e banco SQLite in-memory.
"""
import pytest
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.perfil import Perfil
from app.services.perfil_service import build_curadoria_config


# ---------------------------------------------------------------------------
# Fixture de banco in-memory isolado para estes testes
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Teste 1 — Criar perfil com campos de curadoria → salva e retorna corretamente
# ---------------------------------------------------------------------------

def test_criar_perfil_com_campos_curadoria(db):
    """Perfil com campos de curadoria deve persistir e ser recuperável."""
    perfil = Perfil(
        nome="Marca Curadoria Test",
        sigla="CT",
        slug="marca-curadoria-test",
        curadoria_categories={"icones": {"name": "Ícones", "seeds": ["pavarotti opera"]}},
        elite_hits=["Nessun Dorma", "Ave Maria"],
        power_names=["Pavarotti"],
        voice_keywords=["live", "aria"],
        institutional_channels=["met opera"],
        category_specialty={"icones": ["pavarotti"]},
        scoring_weights={"elite_hit": 15, "power_name": 10},
        curadoria_filters={"duracao_max": 600},
        anti_spam_terms="-karaoke -tutorial",
        playlist_id="PLtest123",
    )
    db.add(perfil)
    db.commit()
    db.refresh(perfil)

    assert perfil.id is not None
    assert perfil.curadoria_categories["icones"]["name"] == "Ícones"
    assert "Nessun Dorma" in perfil.elite_hits
    assert perfil.scoring_weights["elite_hit"] == 15
    assert perfil.curadoria_filters["duracao_max"] == 600
    assert perfil.playlist_id == "PLtest123"


# ---------------------------------------------------------------------------
# Teste 2 — Duplicar perfil → campos de curadoria são copiados
# ---------------------------------------------------------------------------

def test_duplicar_perfil_copia_campos_curadoria(db):  # noqa: unused-parameter (db é a fixture)
    """Perfil duplicado deve herdar campos de curadoria; playlist_id deve ser vazio."""
    original = Perfil(
        nome="Original Dup",
        sigla="OD",
        slug="original-dup",
        curadoria_categories={"hits": {"name": "Hits", "seeds": ["nessun dorma"]}},
        elite_hits=["Nessun Dorma"],
        power_names=["Pavarotti"],
        voice_keywords=["soprano"],
        institutional_channels=["met opera"],
        category_specialty={"hits": ["nessun dorma"]},
        scoring_weights={"elite_hit": 15},
        curadoria_filters={"duracao_max": 900},
        anti_spam_terms="-karaoke",
        playlist_id="PLoriginal",
    )
    db.add(original)
    db.commit()
    db.refresh(original)

    # Simula duplicação (espelha o que duplicar_perfil faz)
    copia = Perfil(
        nome="Original Dup (copia)",
        sigla="OD2",
        slug="original-dup-copia",
        curadoria_categories=original.curadoria_categories,
        elite_hits=original.elite_hits,
        power_names=original.power_names,
        voice_keywords=original.voice_keywords,
        institutional_channels=original.institutional_channels,
        category_specialty=original.category_specialty,
        scoring_weights=original.scoring_weights,
        curadoria_filters=original.curadoria_filters,
        anti_spam_terms=original.anti_spam_terms,
        playlist_id="",  # nova marca começa sem playlist
    )
    db.add(copia)
    db.commit()
    db.refresh(copia)

    assert copia.elite_hits == ["Nessun Dorma"]
    assert copia.scoring_weights == {"elite_hit": 15}
    assert copia.curadoria_categories["hits"]["name"] == "Hits"
    assert copia.playlist_id == ""  # playlist não copiada


# ---------------------------------------------------------------------------
# Teste 3 — build_curadoria_config retorna formato correto (endpoint interno)
# ---------------------------------------------------------------------------

def testbuild_curadoria_config_retorna_formato_correto(db):
    """build_curadoria_config deve retornar payload no formato que a curadoria espera."""
    perfil = Perfil(
        nome="Best of Opera Config",
        sigla="BC",
        slug="best-of-opera-config",
        curadoria_categories={"icones": {"name": "Ícones", "seeds": ["pav opera"]}},
        elite_hits=["Nessun Dorma", "Ave Maria"],
        power_names=["Pavarotti", "Callas"],
        voice_keywords=["live"],
        institutional_channels=["met opera"],
        category_specialty={"icones": ["pavarotti"]},
        scoring_weights={"elite_hit": 15, "power_name": 10, "specialty": 25},
        curadoria_filters={"duracao_max": 900},
        anti_spam_terms="-karaoke",
        playlist_id="PLbo",
    )
    db.add(perfil)
    db.commit()
    db.refresh(perfil)

    config = build_curadoria_config(perfil)

    # Campos obrigatórios para o formato da curadoria
    assert config["name"] == "Best of Opera Config"
    assert config["project_id"] == "best-of-opera-config"
    assert "categories" in config
    assert "elite_hits" in config
    assert "power_names" in config
    assert "voice_keywords" in config
    assert "institutional_channels" in config
    assert "category_specialty" in config
    assert "scoring_weights" in config
    assert "filters" in config

    assert "Nessun Dorma" in config["elite_hits"]
    assert config["scoring_weights"]["elite_hit"] == 15
    assert config["filters"]["duracao_max"] == 900


# ---------------------------------------------------------------------------
# Teste 4 — Perfil sem campos de curadoria → retorna defaults vazios (não quebra)
# ---------------------------------------------------------------------------

def test_perfil_sem_curadoria_retorna_defaults_vazios(db):
    """build_curadoria_config com campos None não deve quebrar — retorna dicts/lists vazios."""
    perfil_vazio = Perfil(
        nome="Marca Vazia",
        sigla="MV",
        slug="marca-vazia",
        # Todos os campos de curadoria omitidos — devem usar defaults do modelo
    )
    db.add(perfil_vazio)
    db.commit()
    db.refresh(perfil_vazio)

    config = build_curadoria_config(perfil_vazio)

    assert isinstance(config["categories"], dict)
    assert isinstance(config["elite_hits"], list)
    assert isinstance(config["power_names"], list)
    assert isinstance(config["voice_keywords"], list)
    assert isinstance(config["institutional_channels"], list)
    assert isinstance(config["category_specialty"], dict)
    assert isinstance(config["scoring_weights"], dict)
    assert isinstance(config["filters"], dict)
    assert config["anti_spam"] == "-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords"
    assert config["playlist_id"] == ""
