"""
BO Sanitize — Limpeza de outputs do LLM (Tarefa 1.8 da Fase 1)
==============================================================

Função `_sanitize_bo(text, artifact_type, language)` aplica:
1. Remoção de markdown (`**`, `*`, `__`, `_`, `---`, `###`)
2. Tratamento de travessões POR `artifact_type`:
   - `overlay_caption`/`post_body`/`hook`: substitui `—` e `–` por `.`
     (gera warning `"dash_removed"`)
   - `post_header`/`youtube_title`: preserva travessões
3. Detecção de antipadrões via `get_banned_terms(language)` (warning
   apenas — não remove)
4. Normalização de espaços e quebras

CRÍTICO: NÃO confundir com `_sanitize_rc` (que serve RC). São funções
INDEPENDENTES — esta função é exclusiva do pipeline BO V2.

Decisão sync-first.
"""
from __future__ import annotations

import logging
import re
from typing import Literal

from backend.services.bo.antipadroes_loader import get_banned_terms

logger = logging.getLogger(__name__)


# Tipos de artifact suportados
ArtifactType = Literal[
    "overlay_caption",  # legenda narrativa do overlay
    "post_body",        # parágrafos narrativos do post
    "hook",             # hook narrativo
    "post_header",      # primeira linha do post (🎶 Obra — Intérprete)
    "youtube_title",    # title do YouTube
]

# Artifacts onde travessão é REMOVIDO (substituído por '.')
DASH_FORBIDDEN_ARTIFACTS = {"overlay_caption", "post_body", "hook"}

# Artifacts onde travessão é PRESERVADO
DASH_ALLOWED_ARTIFACTS = {"post_header", "youtube_title"}

# Markdown patterns a remover
_MD_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_MD_ITALIC_STAR = re.compile(r"(?<!\*)\*([^*]+?)\*(?!\*)")
_MD_BOLD_UNDERSCORE = re.compile(r"__([^_]+?)__")
_MD_ITALIC_UNDERSCORE = re.compile(r"(?<!_)_([^_]+?)_(?!_)")
_MD_HR = re.compile(r"(?m)^---+\s*$")
_MD_HEADING = re.compile(r"(?m)^#{1,6}\s+")

# Espaços múltiplos
_MULTI_SPACE = re.compile(r"[ \t]+")


def _sanitize_bo(
    text: str,
    artifact_type: ArtifactType,
    language: str = "pt",
) -> tuple[str, list[str]]:
    """Sanitiza texto BO V2.

    Args:
        text: texto a sanitizar.
        artifact_type: tipo de artefato (define se travessão é removido).
        language: idioma para lookup de antipadrões (default 'pt').

    Returns:
        (cleaned_text, warnings_list). Warnings são strings descritivas
        — não bloqueiam, apenas alertam.
    """
    if text is None:
        return "", []
    if artifact_type not in DASH_FORBIDDEN_ARTIFACTS and artifact_type not in DASH_ALLOWED_ARTIFACTS:
        raise ValueError(
            f"artifact_type '{artifact_type}' não suportado. "
            f"Válidos: {sorted(DASH_FORBIDDEN_ARTIFACTS | DASH_ALLOWED_ARTIFACTS)}"
        )

    warnings: list[str] = []
    cleaned = text

    # 1. Remove markdown
    cleaned = _MD_BOLD.sub(r"\1", cleaned)
    cleaned = _MD_BOLD_UNDERSCORE.sub(r"\1", cleaned)
    cleaned = _MD_ITALIC_STAR.sub(r"\1", cleaned)
    cleaned = _MD_ITALIC_UNDERSCORE.sub(r"\1", cleaned)
    cleaned = _MD_HR.sub("", cleaned)
    cleaned = _MD_HEADING.sub("", cleaned)
    # Remove ## e ### residuais (heading sem espaço após)
    cleaned = re.sub(r"#{2,}", "", cleaned)

    # 2. Tratamento de travessões por artifact_type
    if artifact_type in DASH_FORBIDDEN_ARTIFACTS:
        had_dash = "—" in cleaned or "–" in cleaned
        if had_dash:
            cleaned = cleaned.replace("—", ".").replace("–", ".")
            warnings.append(f"dash_removed_in_{artifact_type}")
    # Para DASH_ALLOWED_ARTIFACTS: travessões preservados, sem ação

    # 3. Detecção de antipadrões (warning apenas, não remove)
    try:
        banned_terms = get_banned_terms(language)
    except (KeyError, FileNotFoundError):
        banned_terms = []
    cleaned_lower = cleaned.lower()
    for entry in banned_terms:
        if isinstance(entry, str):
            term = entry
        else:
            term = entry.get("termo", "")
        if not term:
            continue
        # Word-boundary match para evitar falsos positivos (ex: "sublime"
        # dentro de "sublimes" — mas se quisermos pegar plurais, usar substring)
        if term.lower() in cleaned_lower:
            warnings.append(f"antipadrao_detectado_{language}: {term!r}")

    # 4. Normaliza espaços (mantém quebras de linha)
    # Substitui múltiplos espaços/tabs por um espaço (preserva \n)
    lines = cleaned.split("\n")
    lines = [_MULTI_SPACE.sub(" ", line).strip() for line in lines]
    cleaned = "\n".join(lines)

    # Remove linhas em branco múltiplas consecutivas (mais de 2 \n seguidos)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    return cleaned, warnings
