"""Tests para bo_post_service — schema rígido + emoji-first + hashtags."""
from __future__ import annotations

import pytest

from backend.services.bo.bo_post_service import validate_post_schema


CANONICAL_POST = """🎶 Nessun Dorma — Pavarotti

🎭 Puccini escreveu Nessun Dorma com câncer na garganta. Morreu antes da estreia.

✨ A ária acontece no ato 3. Calaf prevê sua vitória sobre Turandot.

🕊 Pavarotti estreou em 1976. Tinha 41 anos.

Qual momento mais te marca?

🎤 Pavarotti
Nationality: Italian

🎼 Nessun Dorma
Composer: Puccini

#BestOfOpera #Puccini #Turandot #LyricTenor"""


def test_post_canonico_zero_erros():
    """Post canônico com header, 3 narrativos, ficha, hashtags corretas."""
    errors, warnings = validate_post_schema({"post_text": CANONICAL_POST})
    assert errors == [], f"esperado zero erros, recebido: {errors}"


def test_post_hashtag_bestofopera_nao_primeira():
    """V-H-26: primeira hashtag != #BestOfOpera → erro."""
    bad_post = CANONICAL_POST.replace(
        "#BestOfOpera #Puccini #Turandot #LyricTenor",
        "#Puccini #BestOfOpera #Turandot #LyricTenor",
    )
    errors, _ = validate_post_schema({"post_text": bad_post})
    assert any("first_not_BestOfOpera" in e for e in errors)


def test_post_hashtags_count_diferente_de_4():
    """4 hashtags exatas é regra; 3 ou 5 → erro."""
    bad_post = CANONICAL_POST.replace(
        "#BestOfOpera #Puccini #Turandot #LyricTenor",
        "#BestOfOpera #Puccini #Turandot",  # 3 hashtags
    )
    errors, _ = validate_post_schema({"post_text": bad_post})
    assert any("count=3≠4" in e for e in errors)


def test_post_emoji_repetido_warning():
    """V-H-25: 2 parágrafos narrativos com mesmo emoji → warning (não erro)."""
    repeated_emoji_post = """🎶 Header — header

🎭 Primeiro narrativo aqui contando uma história.

🎭 Segundo narrativo com mesmo emoji repetido.

🕊 Terceiro com emoji distinto.

Qual momento te marca?

🎤 Pavarotti

🎼 Nessun Dorma

#BestOfOpera #Puccini #Turandot #LyricTenor"""
    errors, warnings = validate_post_schema({"post_text": repeated_emoji_post})
    assert any("not_distinct" in w for w in warnings), f"warnings: {warnings}"


def test_post_travessao_em_narrativa_proibido():
    """Travessão em parágrafo narrativo (não header) → erro."""
    bad_post = CANONICAL_POST.replace(
        "🎭 Puccini escreveu Nessun Dorma com câncer na garganta.",
        "🎭 Puccini — escreveu Nessun Dorma com câncer.",
    )
    errors, _ = validate_post_schema({"post_text": bad_post})
    assert any("contains_dash" in e for e in errors)


def test_post_sem_emoji_teatro_no_primeiro_narrativo():
    """Primeiro narrativo deve começar com 🎭."""
    bad_post = CANONICAL_POST.replace("🎭 Puccini", "✨ Puccini", 1)
    errors, _ = validate_post_schema({"post_text": bad_post})
    assert any("no_theatre_emoji" in e for e in errors)
