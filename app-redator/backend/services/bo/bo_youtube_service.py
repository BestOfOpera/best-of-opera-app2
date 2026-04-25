"""
BO YouTube Service v2 — Geração de title + tags YouTube (Tarefa 1.6)
====================================================================

Consome research + hook + overlay + post aprovados, gera title (≤100c) e
tags_list (8-15 itens, csv ≤450c) para o vídeo do YouTube.

Persistência:
- project.youtube_title ← title
- project.youtube_tags_list ← tags_list (JSON list, models.py:94)
- NÃO usar project.youtube_tags (campo legacy v1, Text)

Achados V-* cobertos:
- V-I-05: tags_list é única fonte da verdade; CSV derivado em runtime
- V-H-27: validador RECOMPUTA len(title) — ignora title_chars do LLM
- V-I-15: retry NÃO-acumulativo

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
from backend.services.bo.prompts.bo_youtube_prompt_v1 import build_bo_youtube_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_VALIDATION_RETRIES = 2
MAX_TOKENS = 2048
TEMPERATURE = 0.6

MAX_TITLE_CHARS = 100
MAX_TAGS_CSV_CHARS = 450
MIN_TAGS = 8
MAX_TAGS = 15
MAX_TAG_INDIVIDUAL_CHARS = 40  # warning, não error

# Caracteres proibidos no title
EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")


class YoutubeSchemaError(RuntimeError):
    """Schema do youtube retornado pelo LLM está inválido após todas as tentativas."""


def _assert_test_mock_configured(client) -> None:
    if os.environ.get("TESTING_MODE") == "1":
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado FakeAnthropicClient)."
            )


def validate_youtube_schema(data: dict) -> tuple[list[str], list[str]]:
    """Valida youtube JSON. Retorna (errors, warnings).

    V-H-27: RECOMPUTA len(title) do texto real, ignora title_chars do LLM.
    V-I-05: tags_list é única fonte; tags_csv derivado em runtime.
    """
    errors: list[str] = []
    warnings: list[str] = []

    title = data.get("title", "")
    if not isinstance(title, str) or not title.strip():
        errors.append("title.vazio_ou_invalido")

    # V-H-27: recomputa do texto REAL
    actual_title_chars = len(title)
    if actual_title_chars > MAX_TITLE_CHARS:
        errors.append(f"title.chars={actual_title_chars}>{MAX_TITLE_CHARS}")

    # Title sem emoji, sem !, sem #
    if EMOJI_RE.search(title):
        errors.append("title.contains_emoji")
    if "!" in title:
        errors.append("title.contains_exclamation")
    if "#" in title:
        errors.append("title.contains_hashtag")

    # Tags
    tags_list = data.get("tags_list", [])
    if not isinstance(tags_list, list):
        errors.append(f"tags_list.tipo={type(tags_list).__name__}≠list")
        return errors, warnings

    if not (MIN_TAGS <= len(tags_list) <= MAX_TAGS):
        errors.append(f"tags_list.count={len(tags_list)}∉[{MIN_TAGS},{MAX_TAGS}]")

    # CSV derivado em runtime (V-I-05)
    tags_csv_chars = len(", ".join(tags_list)) if tags_list else 0
    if tags_csv_chars > MAX_TAGS_CSV_CHARS:
        errors.append(f"tags_csv_chars={tags_csv_chars}>{MAX_TAGS_CSV_CHARS}")

    # Cada tag sem # nem emoji; warning se > 40c
    for i, tag in enumerate(tags_list):
        if not isinstance(tag, str):
            errors.append(f"tags_list[{i}].tipo={type(tag).__name__}≠str")
            continue
        if "#" in tag:
            errors.append(f"tags_list[{i}].contains_hashtag: {tag!r}")
        if EMOJI_RE.search(tag):
            errors.append(f"tags_list[{i}].contains_emoji: {tag!r}")
        if len(tag) > MAX_TAG_INDIVIDUAL_CHARS:
            warnings.append(f"tags_list[{i}].len={len(tag)}>{MAX_TAG_INDIVIDUAL_CHARS}_recomendado")

    return errors, warnings


def _call_anthropic_youtube(prompt: str, client) -> dict:
    _assert_test_mock_configured(client)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise YoutubeSchemaError("anthropic.no_text_block_in_response")
    text = text_blocks[-1].text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise YoutubeSchemaError(f"json.decode_error: {exc}")


def run_bo_youtube(project_id: int, db_session=None) -> dict:
    """Gera title + tags YouTube. Persiste em project.youtube_title e youtube_tags_list."""
    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")
        if not project.research_data or not project.hook_escolhido_json or not project.overlay_json or not project.post_text:
            raise ValueError(
                f"projeto {project_id} sem prerequisitos (research/hook/overlay/post aprovados)"
            )

        antipadroes_pt = format_banned_terms_for_prompt("pt")
        base_prompt = build_bo_youtube_prompt(
            research_data=project.research_data,
            hook_escolhido=project.hook_escolhido_json,
            overlay_aprovado=project.overlay_json,
            post_aprovado=project.post_text,
            antipadroes_pt=antipadroes_pt,
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=60.0)
        last_errors: list[str] = []

        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            current_prompt = base_prompt
            if last_errors:
                current_prompt = (
                    base_prompt
                    + "\n\nERROS DA TENTATIVA ANTERIOR:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                )

            data = _call_anthropic_youtube(current_prompt, client)
            errors, warnings = validate_youtube_schema(data)

            if not errors:
                # Persistência: youtube_title + youtube_tags_list (NÃO youtube_tags legacy)
                project.youtube_title = data["title"]
                project.youtube_tags_list = data["tags_list"]
                db.commit()
                logger.info(
                    "bo_youtube: projeto %d sucesso na tentativa %d (warnings=%d)",
                    project_id, attempt + 1, len(warnings),
                )
                for w in warnings:
                    logger.warning("bo_youtube.warning: %s", w)
                return data

            last_errors = errors
            logger.warning(
                "bo_youtube: tentativa %d falhou — %d erros: %s",
                attempt + 1, len(errors), errors[:3],
            )

        raise YoutubeSchemaError(
            f"esgotou {MAX_VALIDATION_RETRIES + 1} tentativas. Erros: {last_errors[:5]}"
        )
    finally:
        if own_session:
            db.close()
