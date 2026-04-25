"""Tests para bo_youtube_service — validador V-H-27 (recomputa) + V-I-05 (tags única fonte)."""
from __future__ import annotations

import pytest

from backend.services.bo.bo_youtube_service import validate_youtube_schema


def _valid() -> dict:
    return {
        "title": "Pavarotti em Nessun Dorma — performance histórica de 1989",
        "tags_list": [
            "BestOfOpera", "Pavarotti", "Nessun Dorma", "Puccini", "Turandot",
            "Lyric Tenor", "Italian Opera", "Classical Music", "Aria",
        ],
    }


def test_validator_aceita_payload_canonico():
    errors, warnings = validate_youtube_schema(_valid())
    assert errors == []


def test_validator_recomputa_title_chars():
    """V-H-27: LLM declara title_chars=50 mas texto tem 150 → error."""
    data = _valid()
    data["title"] = "x" * 150
    data["title_chars"] = 50  # LLM mente
    errors, _ = validate_youtube_schema(data)
    assert any("title.chars=150" in e for e in errors)


def test_validator_tags_list_unica_fonte():
    """V-I-05: schema só tem tags_list (não tags CSV nem tags_chars)."""
    data = _valid()
    # NÃO há campos 'tags' ou 'tags_chars' — tudo é derivado de tags_list
    errors, _ = validate_youtube_schema(data)
    assert errors == []


def test_validator_tags_count_abaixo_de_8():
    data = _valid()
    data["tags_list"] = data["tags_list"][:5]  # 5 tags
    errors, _ = validate_youtube_schema(data)
    assert any("count=5" in e for e in errors)


def test_validator_tags_count_acima_de_15():
    data = _valid()
    data["tags_list"] = [f"tag{i}" for i in range(20)]
    errors, _ = validate_youtube_schema(data)
    assert any("count=20" in e for e in errors)


def test_validator_title_sem_hashtag_nem_emoji_nem_exclamacao():
    data = _valid()
    data["title"] = "Pavarotti! #incredible 🎵"
    errors, _ = validate_youtube_schema(data)
    assert any("title.contains_emoji" in e for e in errors)
    assert any("title.contains_exclamation" in e for e in errors)
    assert any("title.contains_hashtag" in e for e in errors)


def test_validator_warning_tag_individual_acima_40():
    data = _valid()
    data["tags_list"][0] = "x" * 50  # tag individual longa
    errors, warnings = validate_youtube_schema(data)
    # Não bloqueia — só warning
    assert any(">40_recomendado" in w for w in warnings) or \
           any("len=50" in w for w in warnings)


def test_validator_csv_acima_de_450_chars():
    data = _valid()
    # 15 tags de 35c cada = 525c + separadores
    data["tags_list"] = ["x" * 35 for _ in range(15)]
    errors, _ = validate_youtube_schema(data)
    assert any("tags_csv_chars" in e and ">450" in e for e in errors)
