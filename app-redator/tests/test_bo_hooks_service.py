"""Tests para bo_hooks_service — validador V-I-08 + choose_hook persistência."""
from __future__ import annotations

import pytest

from backend.services.bo.bo_hooks_service import (
    HooksSchemaError,
    choose_hook,
    validate_hooks,
)


def _hook(line_1: str = "Sob a paz aparente,", line_2: str = "uma traição se prepara",
          ranking: int = 1) -> dict:
    return {
        "hook_text": f"{line_1}\n{line_2}",
        "ranking": ranking,
        "categoria": "tensao_dramatica",
    }


def _valid_payload() -> dict:
    return {"hooks": [_hook(ranking=i) for i in range(1, 6)]}


def test_validator_aceita_5_hooks_validos():
    errors = validate_hooks(_valid_payload())
    assert errors == []


def test_validator_rejeita_count_diferente_de_5():
    payload = {"hooks": [_hook() for _ in range(3)]}
    errors = validate_hooks(payload)
    assert any("count=3" in e for e in errors)


def test_validator_rejeita_l1_acima_38():
    """V-I-08: recomputa do texto real — LLM 'mente' sobre line_1_chars."""
    long_line = "x" * 45
    payload = {
        "hooks": [
            {
                "hook_text": f"{long_line}\nlinha 2 ok",
                "line_1_chars": 20,  # LLM mente
            }
            for _ in range(5)
        ]
    }
    errors = validate_hooks(payload)
    assert any("text_line_1=45c>38" in e for e in errors)


def test_validator_rejeita_total_acima_76():
    payload = {
        "hooks": [
            {"hook_text": ("a" * 38) + "\n" + ("b" * 39)}
            for _ in range(5)
        ]
    }
    errors = validate_hooks(payload)
    assert any("total=77c>76" in e for e in errors)


def test_validator_rejeita_hook_sem_segunda_linha():
    payload = {
        "hooks": [
            {"hook_text": "só linha 1"}  # sem \n
            for _ in range(5)
        ]
    }
    errors = validate_hooks(payload)
    assert any("2_linhas_obrigatorias" in e for e in errors)


def test_choose_hook_persiste_em_hook_escolhido_json(mock_project, in_memory_db):
    """choose_hook usa hook_escolhido_json (NÃO selected_hook RC v1)."""
    project = mock_project()
    chosen = {"hook_text": "Sob a paz\naparente", "ranking": 1, "categoria": "x"}

    result = choose_hook(project.id, chosen, db_session=in_memory_db)

    assert result == chosen
    in_memory_db.refresh(project)
    assert project.hook_escolhido_json == chosen
    # Garante que selected_hook (RC v1) NÃO foi tocado
    assert project.selected_hook in (None, "")


def test_choose_hook_rejeita_input_nao_dict(mock_project, in_memory_db):
    project = mock_project()
    with pytest.raises(ValueError, match="chosen_hook deve ser dict"):
        choose_hook(project.id, "string nao eh dict", db_session=in_memory_db)
