"""Tests para bo_translate_service_v2 — validador timestamps + CTA + dispatcher."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.services.bo.bo_ctas import get_cta_overlay
from backend.services.bo.bo_translate_service_v2 import (
    _substitute_cta_post_llm,
    validate_translation_schema,
)


def _overlay_pt() -> dict:
    return {
        "captions": [
            {"index": 1, "text_line_1": "linha 1", "text_line_2": "linha 2",
             "start_seconds": 0.0, "end_seconds": 6.0},
            {"index": 2, "text_line_1": "linha 3", "text_line_2": "linha 4",
             "start_seconds": 6.0, "end_seconds": 12.0},
        ],
    }


def _parsed_translation(target_lang: str = "en", **overrides) -> dict:
    base = {
        "overlay": {
            "captions": [
                {"index": 1, "text_line_1": "Beneath the calm,",
                 "text_line_2": "a betrayal forms",
                 "start_seconds": 0.0, "end_seconds": 6.0},
                {"index": 2, "text_line_1": "Two voices fade",
                 "text_line_2": "into shadow",
                 "start_seconds": 6.0, "end_seconds": 12.0},
            ],
            "cta": {"text_line_1": "x", "text_line_2": "y"},
        },
        "post_text": "Translated post body in target language.",
        "youtube": {
            "title": "Translated title under 100 chars",
            "tags_list": [
                "BestOfOpera", "Pavarotti", "Opera", "Classical",
                "Aria", "Italian", "Tenor", "Vocal",
            ],
        },
    }
    base.update(overrides)
    return base


def test_validator_aceita_traducao_valida():
    errors, _ = validate_translation_schema(_parsed_translation(), "en", _overlay_pt())
    assert errors == []


def test_validator_detecta_end_seconds_alterado():
    """V-I-19: timestamps preservados — math.isclose para floats."""
    parsed = _parsed_translation()
    parsed["overlay"]["captions"][0]["end_seconds"] = 12.5  # alterado
    errors, _ = validate_translation_schema(parsed, "en", _overlay_pt())
    assert any("end_seconds_altered" in e for e in errors)


def test_validator_detecta_index_alterado():
    """V-I-19: index é int — comparação direta `==`, NÃO math.isclose."""
    parsed = _parsed_translation()
    parsed["overlay"]["captions"][0]["index"] = 2  # alterado (era 1)
    errors, _ = validate_translation_schema(parsed, "en", _overlay_pt())
    assert any("index_altered" in e for e in errors)


def test_validator_tolera_float_noise_em_end_seconds():
    """V-I-09: 6.0 vs 6.0000001 deve ser aceito (math.isclose abs_tol=0.001)."""
    parsed = _parsed_translation()
    parsed["overlay"]["captions"][0]["end_seconds"] = 6.0000001
    errors, _ = validate_translation_schema(parsed, "en", _overlay_pt())
    assert not any("end_seconds_altered" in e for e in errors)


def test_validator_recomputa_chars_l1_acima_38_em_traducao():
    """V-I-08 aplicado a tradução: l1 > 38c em texto traduzido → erro."""
    parsed = _parsed_translation()
    parsed["overlay"]["captions"][0]["text_line_1"] = "x" * 45
    errors, _ = validate_translation_schema(parsed, "en", _overlay_pt())
    assert any("text_line_1(en)=45c>38" in e for e in errors)


def test_cta_substituido_pos_llm_byte_a_byte():
    """LLM retorna CTA errado propositalmente — _substitute_cta_post_llm corrige."""
    parsed = {
        "overlay": {
            "captions": [],
            "cta": {"text_line_1": "ERRADO", "text_line_2": "TAMBÉM ERRADO"},
        },
    }
    result = _substitute_cta_post_llm(parsed, "de")

    expected_l1, expected_l2 = get_cta_overlay("de")
    assert result["overlay"]["cta"]["text_line_1"] == expected_l1
    assert result["overlay"]["cta"]["text_line_2"] == expected_l2


def test_validator_detecta_count_mismatch_de_captions():
    parsed = _parsed_translation()
    parsed["overlay"]["captions"] = parsed["overlay"]["captions"][:1]  # só 1 (esperava 2)
    errors, _ = validate_translation_schema(parsed, "en", _overlay_pt())
    assert any("count_mismatch" in e for e in errors)


# === Dispatcher tests ===

class _FakeProject:
    def __init__(self, brand_slug, pipeline_version):
        self.brand_slug = brand_slug
        self.pipeline_version = pipeline_version
        self.id = 1


def test_dispatcher_route_bo_v2():
    """brand_slug=best-of-opera + v2 → chama translate_project_bo_v2(project.id)."""
    from backend.services.translate_service import translate_project_dispatched

    project = _FakeProject("best-of-opera", "v2")
    with patch(
        "backend.services.bo.bo_translate_service_v2.translate_project_bo_v2"
    ) as mock_bo, patch(
        "backend.services.translate_service.translate_project_parallel"
    ) as mock_parallel:
        mock_bo.return_value = "bo_v2_result"
        result = translate_project_dispatched(project, [], "")

    mock_bo.assert_called_once_with(1)
    mock_parallel.assert_not_called()
    assert result == "bo_v2_result"


def test_dispatcher_route_bo_v1_legacy():
    """brand_slug=best-of-opera + v1 → chama translate_project_parallel (legacy)."""
    from backend.services.translate_service import translate_project_dispatched

    project = _FakeProject("best-of-opera", "v1")
    with patch(
        "backend.services.bo.bo_translate_service_v2.translate_project_bo_v2"
    ) as mock_bo, patch(
        "backend.services.translate_service.translate_project_parallel"
    ) as mock_parallel:
        mock_parallel.return_value = "parallel_result"
        result = translate_project_dispatched(project, [], "post text")

    mock_bo.assert_not_called()
    mock_parallel.assert_called_once()
    assert result == "parallel_result"


def test_dispatcher_route_rc():
    """brand_slug=reels-classics → chama translate_project_parallel (RC)."""
    from backend.services.translate_service import translate_project_dispatched

    project = _FakeProject("reels-classics", "v1")
    with patch(
        "backend.services.bo.bo_translate_service_v2.translate_project_bo_v2"
    ) as mock_bo, patch(
        "backend.services.translate_service.translate_project_parallel"
    ) as mock_parallel:
        mock_parallel.return_value = "rc_result"
        result = translate_project_dispatched(project, [], "post text")

    mock_bo.assert_not_called()
    mock_parallel.assert_called_once()
    assert result == "rc_result"
