"""Tests para bo_research_service — validador + retry + persistência."""
from __future__ import annotations

import logging

import pytest

from backend.services.bo.bo_research_service import (
    ResearchSchemaError,
    validate_research_schema,
)


def _valid_payload(**overrides) -> dict:
    """Helper: payload mínimo válido."""
    base = {
        "classificacao_refinada": {"dimensao_1": "solo"},
        "metadados_obra": {"titulo": "Test"},
        "metadados_interprete": {"nome": "Test"},
        "contexto_dramatico_cena": "x",
        "fatos_surpreendentes": [
            {"texto": f"fato {i}", "fonte_url": f"https://x.com/{i}"}
            for i in range(6)
        ],
        "sources": [
            {"tipo": "web", "url": "https://a.com"},
            {"tipo": "web", "url": "https://b.com"},
            {"tipo": "web", "url": "https://c.com"},
        ],
        "verificacoes": {"v_antipadroes": "ok"},
    }
    base.update(overrides)
    return base


def test_validator_aceita_payload_canonico():
    """Payload com todos os campos válidos não levanta."""
    validate_research_schema(_valid_payload())


def test_validator_rejeita_chaves_obrigatorias_ausentes():
    payload = _valid_payload()
    del payload["sources"]
    with pytest.raises(ResearchSchemaError, match="chaves_obrigatorias_ausentes"):
        validate_research_schema(payload)


def test_validator_rejeita_sources_vazias_sem_conhecimento_interno():
    """V-I-21: sources < 3 e sem 'conhecimento_interno' → erro."""
    payload = _valid_payload(sources=[])
    with pytest.raises(ResearchSchemaError, match="sources.count=0<3"):
        validate_research_schema(payload)


def test_validator_aceita_com_conhecimento_interno():
    """V-I-21: sources com tipo='conhecimento_interno' bypassa exigência ≥3."""
    payload = _valid_payload(sources=[{"tipo": "conhecimento_interno"}])
    validate_research_schema(payload)  # não deve levantar


def test_validator_rejeita_fatos_abaixo_de_5():
    payload = _valid_payload(fatos_surpreendentes=[
        {"texto": "x", "fonte_url": "u"} for _ in range(3)
    ])
    with pytest.raises(ResearchSchemaError, match="fatos_surpreendentes.count=3"):
        validate_research_schema(payload)


def test_validator_rejeita_fatos_acima_de_8():
    payload = _valid_payload(fatos_surpreendentes=[
        {"texto": "x", "fonte_url": "u"} for _ in range(10)
    ])
    with pytest.raises(ResearchSchemaError, match="fatos_surpreendentes.count=10"):
        validate_research_schema(payload)


def test_validator_warning_majoritariamente_sem_fontes(caplog):
    """Mais de 50% dos fatos sem fonte_url/fonte_id → warning (não bloqueia)."""
    payload = _valid_payload(fatos_surpreendentes=[
        {"texto": f"fato {i}"} for i in range(6)  # nenhum tem fonte
    ])
    with caplog.at_level(logging.WARNING):
        validate_research_schema(payload)  # não levanta
    assert any("sem fonte_url" in rec.message for rec in caplog.records)


def test_branch_b_levanta_not_implemented(monkeypatch):
    """USE_ANTHROPIC_WEB_SEARCH=False → NotImplementedError (stub Branch B)."""
    monkeypatch.setattr(
        "backend.services.bo.bo_research_service.USE_ANTHROPIC_WEB_SEARCH",
        False,
    )
    from backend.services.bo.bo_research_service import run_bo_research

    with pytest.raises(NotImplementedError, match="Branch B"):
        run_bo_research(project_id=999)
