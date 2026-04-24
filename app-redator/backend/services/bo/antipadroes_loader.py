"""Loader da lista de anti-padrões do Best of Opera.

Fonte única (`config/BO_ANTIPADROES.json`) consumida em runtime pelos prompts v2.
Cache de módulo: carrega do disco apenas na primeira chamada.
"""
from __future__ import annotations

import json
from pathlib import Path

_ANTIPADROES_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "BO_ANTIPADROES.json"
_ANTIPADROES_CACHE: dict | None = None


def load_antipadroes() -> dict:
    global _ANTIPADROES_CACHE
    if _ANTIPADROES_CACHE is None:
        with open(_ANTIPADROES_PATH, encoding="utf-8") as f:
            _ANTIPADROES_CACHE = json.load(f)
    return _ANTIPADROES_CACHE


def get_banned_terms(language: str) -> list[dict]:
    data = load_antipadroes()
    return data["idiomas"].get(language, {}).get("termos", [])


def format_banned_terms_for_prompt(language: str) -> str:
    termos = get_banned_terms(language)
    linhas = []
    for t in termos:
        if isinstance(t, str):
            linhas.append(f"- {t}")
            continue
        nota = f" ({t['nota']})" if t.get("nota") else ""
        linhas.append(f"- {t['termo']}{nota}")
    return "\n".join(linhas)
