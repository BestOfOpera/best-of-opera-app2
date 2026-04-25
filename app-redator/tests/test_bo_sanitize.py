"""Tests para _sanitize_bo — markdown + travessões + antipadrões."""
from __future__ import annotations

import pytest

from backend.services.bo.sanitize import _sanitize_bo


def test_sanitize_remove_markdown_bold_e_italico():
    cleaned, warnings = _sanitize_bo("**bold** e *italico* e __sub__", "overlay_caption", "pt")
    assert "**" not in cleaned
    assert "*" not in cleaned
    assert "__" not in cleaned
    assert "bold" in cleaned and "italico" in cleaned and "sub" in cleaned


def test_sanitize_remove_dash_em_overlay_caption():
    cleaned, warnings = _sanitize_bo("texto — com dash – e en-dash", "overlay_caption", "pt")
    assert "—" not in cleaned
    assert "–" not in cleaned
    assert "." in cleaned
    assert any("dash_removed" in w for w in warnings)


def test_sanitize_remove_dash_em_post_body():
    cleaned, warnings = _sanitize_bo("Pavarotti — gigante — voz incrível", "post_body", "pt")
    assert "—" not in cleaned
    assert any("dash_removed" in w for w in warnings)


def test_sanitize_remove_dash_em_hook():
    cleaned, warnings = _sanitize_bo("hook — com dash", "hook", "pt")
    assert "—" not in cleaned


def test_sanitize_preserva_dash_em_youtube_title():
    cleaned, warnings = _sanitize_bo("Obra — Intérprete", "youtube_title", "pt")
    assert "—" in cleaned
    assert not any("dash_removed" in w for w in warnings)


def test_sanitize_preserva_dash_em_post_header():
    cleaned, warnings = _sanitize_bo("🎶 Nessun Dorma — Pavarotti", "post_header", "pt")
    assert "—" in cleaned


def test_sanitize_detecta_antipadrao_pt():
    """Antipadrão 'sublime' (frequente em pt) deve gerar warning."""
    cleaned, warnings = _sanitize_bo("uma performance sublime", "overlay_caption", "pt")
    # palavra preservada, mas warning emitido
    assert "sublime" in cleaned.lower()
    assert any("antipadrao_detectado_pt" in w for w in warnings) or \
           any("sublime" in w.lower() for w in warnings)


def test_sanitize_normaliza_espacos_multiplos():
    cleaned, _ = _sanitize_bo("texto    com    espacos", "overlay_caption", "pt")
    assert "    " not in cleaned
    assert "texto com espacos" == cleaned


def test_sanitize_remove_horizontal_rule():
    cleaned, _ = _sanitize_bo("antes\n---\ndepois", "post_body", "pt")
    assert "---" not in cleaned


def test_sanitize_remove_heading_markdown():
    cleaned, _ = _sanitize_bo("## Heading 2\nconteudo", "post_body", "pt")
    assert "##" not in cleaned
    assert "Heading 2" in cleaned


def test_sanitize_artifact_type_invalido_levanta():
    with pytest.raises(ValueError, match="não suportado"):
        _sanitize_bo("texto", "tipo_inventado", "pt")


def test_sanitize_texto_none_retorna_vazio():
    cleaned, warnings = _sanitize_bo(None, "overlay_caption", "pt")
    assert cleaned == ""
    assert warnings == []
