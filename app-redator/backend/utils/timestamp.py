"""Parsing de timestamps de corte de vídeo.

Aceita os formatos usados no pipeline:
- 'HH:MM:SS.mmm' (BO v2 — precisão de ms)
- 'MM:SS.mmm'
- 'MM:SS' (legado RC/BO v1 — precisão de segundos)
"""
from __future__ import annotations


def parse_timestamp_to_seconds(ts: str) -> float:
    """Converte 'HH:MM:SS.mmm', 'MM:SS.mmm' ou 'MM:SS' para segundos (float).

    Raises ValueError se o formato não for reconhecido.
    """
    if ts is None:
        raise ValueError("timestamp vazio")
    s = ts.strip()
    if not s:
        raise ValueError("timestamp vazio")
    parts = s.split(":")
    if len(parts) == 3:
        h, m, sec = parts
        return int(h) * 3600 + int(m) * 60 + float(sec)
    if len(parts) == 2:
        m, sec = parts
        return int(m) * 60 + float(sec)
    raise ValueError(f"formato de timestamp inválido: {ts!r}")
