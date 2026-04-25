"""
BO Post Service v2 — Geração de descrição/caption Instagram (Tarefa 1.5)
========================================================================

Consome research + hook escolhido + overlay aprovado, gera post Instagram
com:
- Header (1 linha com 🎶 — pode ter travessão)
- 2 a 4 parágrafos narrativos (cada um inicia com emoji distinto, primeiro
  começa com 🎭)
- CTA pergunta
- Ficha técnica (linhas iniciadas por 🎤/🎼)
- 4 hashtags (primeira é #BestOfOpera)

Achados V-* cobertos:
- V-I-22: validação rigorosa de schema com regex e splits explícitos
- V-H-25: emojis distintos entre parágrafos narrativos (warning se duplicados)
- V-H-26: primeira hashtag = #BestOfOpera (error se não)

Decisão sync-first.
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.services.bo.antipadroes_loader import format_banned_terms_for_prompt
from backend.services.bo.prompts.bo_post_prompt_v1 import build_bo_post_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_VALIDATION_RETRIES = 2
MAX_TOKENS = 4096
TEMPERATURE = 0.7

HASHTAG_RE = re.compile(r"#([A-Za-z0-9_]+)")
PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
# Emojis que indicam ficha técnica (não parágrafo narrativo)
FICHA_EMOJIS = ("🎤", "🎼")


class PostSchemaError(RuntimeError):
    """Schema do post retornado pelo LLM está inválido após todas as tentativas."""


def _assert_test_mock_configured(client) -> None:
    if os.environ.get("TESTING_MODE") == "1":
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado FakeAnthropicClient)."
            )


def _first_emoji(text: str) -> str:
    """Retorna o primeiro caractere do texto se for emoji-like, senão ''."""
    if not text:
        return ""
    first = text.lstrip()[:2]  # alguns emojis ocupam 2 chars (surrogate pair)
    # Heurística simples: se primeiro char não é ascii nem letra Unicode comum, é emoji
    if first and not first[0].isascii() and not first[0].isalpha():
        return first[0] if not (len(first) == 2 and ord(first[0]) >= 0xD800) else first
    return ""


def validate_post_schema(data: dict) -> tuple[list[str], list[str]]:
    """Valida post JSON. Retorna (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    post_text = data.get("post_text", "")
    if not isinstance(post_text, str) or not post_text.strip():
        errors.append("post_text.vazio_ou_invalido")
        return errors, warnings

    # Tamanho total
    if len(post_text) > 1900:
        errors.append(f"post_text.len={len(post_text)}>1900")

    # Split em parágrafos
    paragraphs = [p.strip() for p in PARAGRAPH_SPLIT_RE.split(post_text) if p.strip()]
    if len(paragraphs) < 4:
        errors.append(f"post_text.paragraphs={len(paragraphs)}<4_minimo")

    # Identifica parágrafos narrativos (não-ficha) e ficha técnica
    narrative_paragraphs: list[str] = []
    ficha_paragraphs: list[str] = []
    hashtag_paragraph: str | None = None
    header_paragraph: str | None = None

    for i, p in enumerate(paragraphs):
        first_line = p.split("\n", 1)[0].strip()
        if HASHTAG_RE.search(first_line) and "#" in first_line[:2]:
            hashtag_paragraph = p
        elif any(first_line.startswith(e) for e in FICHA_EMOJIS):
            ficha_paragraphs.append(p)
        elif i == 0 and first_line.startswith("🎶"):
            header_paragraph = p
        else:
            narrative_paragraphs.append(p)

    # Narrativos: 2 a 4
    if not (2 <= len(narrative_paragraphs) <= 4):
        errors.append(f"narrative_paragraphs={len(narrative_paragraphs)}∉[2,4]")

    # Primeiro narrativo deve começar com 🎭
    if narrative_paragraphs:
        first_narrative_line = narrative_paragraphs[0].split("\n", 1)[0].strip()
        if not first_narrative_line.startswith("🎭"):
            errors.append(f"first_narrative.no_theatre_emoji: {first_narrative_line[:30]!r}")

    # Travessão proibido em parágrafos não-header
    for i, p in enumerate(narrative_paragraphs):
        if "—" in p or "–" in p:
            errors.append(f"narrative[{i}].contains_dash")
    for i, p in enumerate(ficha_paragraphs):
        if "—" in p or "–" in p:
            errors.append(f"ficha[{i}].contains_dash")

    # V-H-25: emojis narrativos distintos (warning, não error)
    narrative_emojis = []
    for p in narrative_paragraphs:
        first = p.split("\n", 1)[0].strip()
        # pega primeiro caractere emoji (geralmente é primeiro char Unicode não-ASCII)
        if first and not first[0].isascii():
            narrative_emojis.append(first[0])

    if len(narrative_emojis) != len(set(narrative_emojis)):
        warnings.append(
            f"emojis_not_distinct_in_narratives: {narrative_emojis}"
        )

    # V-H-26: hashtags
    if hashtag_paragraph is None:
        errors.append("post.no_hashtag_paragraph")
    else:
        hashtags = HASHTAG_RE.findall(hashtag_paragraph)
        if len(hashtags) != 4:
            errors.append(f"hashtags.count={len(hashtags)}≠4")
        if hashtags and hashtags[0] != "BestOfOpera":
            errors.append(f"hashtags.first_not_BestOfOpera: {hashtags[0]}")

    return errors, warnings


def _call_anthropic_post(prompt: str, client) -> dict:
    _assert_test_mock_configured(client)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise PostSchemaError("anthropic.no_text_block_in_response")
    text = text_blocks[-1].text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise PostSchemaError(f"json.decode_error: {exc}")


def run_bo_post(project_id: int, db_session=None) -> dict:
    """Gera post BO V2. Persiste em project.post_text."""
    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")
        if not project.research_data:
            raise ValueError(f"projeto {project_id} sem research_data")
        if not project.hook_escolhido_json:
            raise ValueError(f"projeto {project_id} sem hook_escolhido_json")
        if not project.overlay_json:
            raise ValueError(f"projeto {project_id} sem overlay_json aprovado")

        antipadroes_pt = format_banned_terms_for_prompt("pt")
        base_prompt = build_bo_post_prompt(
            research_data=project.research_data,
            hook_escolhido=project.hook_escolhido_json,
            overlay_aprovado=project.overlay_json,
            antipadroes_pt=antipadroes_pt,
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=120.0)
        last_errors: list[str] = []

        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            current_prompt = base_prompt
            if last_errors:
                current_prompt = (
                    base_prompt
                    + "\n\nERROS DA TENTATIVA ANTERIOR:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                )

            data = _call_anthropic_post(current_prompt, client)
            errors, warnings = validate_post_schema(data)

            if not errors:
                project.post_text = data.get("post_text", "")
                db.commit()
                logger.info(
                    "bo_post: projeto %d sucesso na tentativa %d (warnings=%d)",
                    project_id, attempt + 1, len(warnings),
                )
                for w in warnings:
                    logger.warning("bo_post.warning: %s", w)
                return data

            last_errors = errors
            logger.warning(
                "bo_post: tentativa %d falhou — %d erros: %s",
                attempt + 1, len(errors), errors[:3],
            )

        raise PostSchemaError(
            f"esgotou {MAX_VALIDATION_RETRIES + 1} tentativas. Erros: {last_errors[:5]}"
        )
    finally:
        if own_session:
            db.close()
