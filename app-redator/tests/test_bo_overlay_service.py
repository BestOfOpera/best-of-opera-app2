"""Tests para bo_overlay_service — validador crítico recomputa chars + tol float."""
from __future__ import annotations

import pytest

from backend.services.bo.bo_ctas import get_cta_overlay
from backend.services.bo.bo_overlay_service import (
    OverlaySchemaError,
    run_bo_overlay,
    validate_overlay_schema,
)


def _cta_pt() -> dict:
    """CTA canônica PT (deve bater byte-a-byte por V-I-14)."""
    l1, l2 = get_cta_overlay("pt")
    return {
        "text_line_1": l1,
        "text_line_2": l2,
        "start_seconds": 21.0,
        "end_seconds": 28.0,
    }


def _caption(i: int, start: float, end: float, l1: str = "Sob a paz aparente,",
             l2: str = "uma traição se prepara") -> dict:
    return {
        "index": i,
        "text_line_1": l1,
        "text_line_2": l2,
        "start_seconds": start,
        "end_seconds": end,
    }


def _valid_overlay() -> dict:
    """Overlay canônico — 3 captions de 7s + CTA de 7s = 28s total."""
    return {
        "captions": [
            _caption(1, 0.0, 7.0),
            _caption(2, 7.0, 14.0),
            _caption(3, 14.0, 21.0),
        ],
        "cta": _cta_pt(),
    }


def test_validator_aceita_overlay_canonico():
    errors, warnings = validate_overlay_schema(_valid_overlay())
    assert errors == []


def test_validator_rejeita_captions_count_abaixo_3():
    overlay = _valid_overlay()
    overlay["captions"] = overlay["captions"][:2]
    overlay["cta"]["start_seconds"] = 14.0
    overlay["cta"]["end_seconds"] = 21.0
    errors, _ = validate_overlay_schema(overlay)
    assert any("count=2<3" in e for e in errors)


def test_validator_recomputa_chars_l1_acima_38():
    """V-I-08: LLM declara line_1_chars=20 mas texto real tem 45 → erro."""
    overlay = _valid_overlay()
    overlay["captions"][0]["text_line_1"] = "x" * 45
    overlay["captions"][0]["line_1_chars"] = 20  # LLM mente
    errors, _ = validate_overlay_schema(overlay)
    assert any("text_line_1=45c>38" in e for e in errors)


def test_validator_rejeita_total_acima_76():
    overlay = _valid_overlay()
    overlay["captions"][0]["text_line_1"] = "a" * 38
    overlay["captions"][0]["text_line_2"] = "b" * 39
    errors, _ = validate_overlay_schema(overlay)
    assert any("total=77" in e for e in errors)


def test_validator_rejeita_travessao_em_caption():
    overlay = _valid_overlay()
    overlay["captions"][0]["text_line_1"] = "texto — com dash"
    errors, _ = validate_overlay_schema(overlay)
    assert any("contains_dash" in e for e in errors)


def test_gap_zero_tolera_float_noise():
    """V-I-09: 6.0 vs 6.0000001 deve ser aceito (math.isclose abs_tol=0.001)."""
    overlay = _valid_overlay()
    # Introduz ruído float
    overlay["captions"][1]["start_seconds"] = 7.0000001  # vs end_seconds[0] = 7.0
    errors, _ = validate_overlay_schema(overlay)
    assert not any("gap" in e for e in errors)


def test_gap_real_quebra_validacao():
    """Gap > tolerance → erro detectado."""
    overlay = _valid_overlay()
    overlay["captions"][1]["start_seconds"] = 7.5  # gap real de 0.5s
    errors, _ = validate_overlay_schema(overlay)
    assert any("gap.between_0_and_1" in e for e in errors)


def test_first_caption_deve_comecar_em_zero():
    overlay = _valid_overlay()
    overlay["captions"][0]["start_seconds"] = 0.5
    errors, _ = validate_overlay_schema(overlay)
    assert any("first_caption_start=0.5" in e for e in errors)


def test_cta_warning_quando_maior_15s():
    """V-I-06: CTA > 15s → warning (não erro)."""
    overlay = _valid_overlay()
    overlay["cta"]["end_seconds"] = 50.0  # CTA = 50 - 21 = 29s
    errors, warnings = validate_overlay_schema(overlay)
    # Warning não bloqueia validação
    assert any(">15s_recomendado" in w for w in warnings) or \
           any(">15.0s_recomendado" in w for w in warnings)


def test_cta_texto_diferente_canonico_levanta_erro():
    """V-I-14: CTA com texto diferente do bo_ctas.py PT → erro."""
    overlay = _valid_overlay()
    overlay["cta"]["text_line_1"] = "TEXTO ERRADO"
    errors, _ = validate_overlay_schema(overlay)
    assert any("cta.text_not_matching_canonical_pt" in e for e in errors)


def test_run_rejeita_video_menor_que_28s(mock_project, in_memory_db):
    """V-C-02: vídeo < 28s rejeitado antes de qualquer chamada LLM."""
    project = mock_project(video_duration_seconds=25.0)
    with pytest.raises(ValueError, match=r"<.*28"):
        run_bo_overlay(project.id, db_session=in_memory_db)


def test_run_rejeita_video_duration_none(mock_project, in_memory_db):
    """V-I-07: video_duration_seconds=None → ValueError."""
    project = mock_project(video_duration_seconds=None)
    with pytest.raises(ValueError, match="video_duration_seconds ausente"):
        run_bo_overlay(project.id, db_session=in_memory_db)
