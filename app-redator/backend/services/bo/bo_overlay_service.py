"""
BO Overlay Service v2 — Geração de overlay narrativo (Tarefa 1.4 da Fase 1)
==========================================================================

SERVIÇO MAIS CRÍTICO DO PIPELINE BO V2.

Consome `project.research_data` + `project.hook_escolhido_json` e gera o
overlay completo (sequência de captions + CTA). Validação rigorosa pós-LLM
recomputa todos os chars do texto real, garante gap zero entre captions
(com tolerância float), valida CTA byte-a-byte contra `bo_ctas.py`, e
levanta erros sem confiar em campos declarados pelo LLM.

Achados V-* cobertos:
- V-C-02: rejeita vídeo < 28s antes de qualquer chamada LLM
- V-I-06: warning não-bloqueante se CTA > 15s
- V-I-07: rejeita video_duration_seconds=None (backend deveria popular)
- V-I-08: RECOMPUTA len(text_line_1)/len(text_line_2) do texto real,
  ignora line_1_chars/line_2_chars declarados pelo LLM
- V-I-09: gap zero usa math.isclose(abs_tol=0.001), NUNCA != para floats
- V-I-14: CTA texto byte-a-byte igual a get_cta_overlay("pt")
- V-I-15: retry NÃO-acumulativo

Decisão sync-first.
"""
from __future__ import annotations

import json
import logging
import math
import os
from typing import Any

import anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.services.bo.antipadroes_loader import format_banned_terms_for_prompt
from backend.services.bo.bo_ctas import get_cta_overlay
from backend.services.bo.prompts.bo_overlay_prompt_v1 import build_bo_overlay_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_VALIDATION_RETRIES = 2
MAX_TOKENS = 4096
TEMPERATURE = 0.7

FLOAT_TOL = 0.001
MIN_VIDEO_DURATION = 28.0  # V-C-02
MAX_LINE_CHARS = 38
MAX_TOTAL_CHARS = 76
NARRATIVE_DUR_MIN = 5.0
NARRATIVE_DUR_MAX = 7.0
CTA_DUR_MIN = 5.0
CTA_DUR_WARNING_MAX = 15.0  # V-I-06


class OverlaySchemaError(RuntimeError):
    """Schema do overlay retornado pelo LLM está inválido após todas as tentativas."""


def _assert_test_mock_configured(client) -> None:
    if os.environ.get("TESTING_MODE") == "1":
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado FakeAnthropicClient)."
            )


def validate_overlay_schema(data: dict) -> tuple[list[str], list[str]]:
    """Valida overlay JSON. Retorna (errors, warnings).

    Recomputa chars do texto real (V-I-08) — ignora valores declarados pelo LLM.
    Usa math.isclose para comparações de timestamps (V-I-09).
    """
    errors: list[str] = []
    warnings: list[str] = []

    if "captions" not in data:
        errors.append("schema.missing_captions")
        return errors, warnings
    if "cta" not in data:
        errors.append("schema.missing_cta")
        return errors, warnings

    captions = data["captions"]
    if not isinstance(captions, list) or len(captions) < 3:
        errors.append(f"captions.count={len(captions) if isinstance(captions, list) else 'NOT_LIST'}<3")

    for i, c in enumerate(captions):
        line_1 = (c.get("text_line_1") or "")
        line_2 = (c.get("text_line_2") or "")

        # V-I-08: recomputa chars do TEXTO REAL
        actual_l1 = len(line_1)
        actual_l2 = len(line_2)

        if actual_l1 > MAX_LINE_CHARS:
            errors.append(f"caption[{i}].text_line_1={actual_l1}c>{MAX_LINE_CHARS}")
        if actual_l2 > MAX_LINE_CHARS:
            errors.append(f"caption[{i}].text_line_2={actual_l2}c>{MAX_LINE_CHARS}")
        if actual_l1 + actual_l2 > MAX_TOTAL_CHARS:
            errors.append(f"caption[{i}].total={actual_l1 + actual_l2}c>{MAX_TOTAL_CHARS}")
        if not line_1 or not line_2:
            errors.append(f"caption[{i}].2_linhas_obrigatorias")

        # Duração da caption
        try:
            start = float(c["start_seconds"])
            end = float(c["end_seconds"])
            dur = end - start
        except (KeyError, TypeError, ValueError):
            errors.append(f"caption[{i}].timestamps_invalidos")
            continue

        if dur < NARRATIVE_DUR_MIN - FLOAT_TOL or dur > NARRATIVE_DUR_MAX + FLOAT_TOL:
            errors.append(f"caption[{i}].duration={dur:.3f}∉[{NARRATIVE_DUR_MIN},{NARRATIVE_DUR_MAX}]")

        # Sem travessão no texto
        texto_full = f"{line_1}\n{line_2}"
        if "—" in texto_full or "–" in texto_full:
            errors.append(f"caption[{i}].contains_dash")

    # V-I-09: gap zero entre captions consecutivas com tolerância float
    for i in range(len(captions) - 1):
        try:
            end_i = float(captions[i]["end_seconds"])
            start_next = float(captions[i + 1]["start_seconds"])
        except (KeyError, TypeError, ValueError):
            continue
        if not math.isclose(start_next, end_i, abs_tol=FLOAT_TOL):
            errors.append(f"gap.between_{i}_and_{i+1}: {end_i} vs {start_next}")

    # Primeira caption deve começar em 0.0 ± tol
    if captions:
        try:
            first_start = float(captions[0].get("start_seconds", -1))
            if not math.isclose(first_start, 0.0, abs_tol=FLOAT_TOL):
                errors.append(f"first_caption_start={first_start}≠0.0")
        except (TypeError, ValueError):
            errors.append("first_caption.start_seconds_invalido")

    # CTA
    cta = data["cta"]
    try:
        cta_start = float(cta["start_seconds"])
        cta_end = float(cta["end_seconds"])
    except (KeyError, TypeError, ValueError):
        errors.append("cta.timestamps_invalidos")
        return errors, warnings

    # CTA encadeado com última caption (gap zero)
    if captions:
        try:
            last_end = float(captions[-1]["end_seconds"])
            if not math.isclose(cta_start, last_end, abs_tol=FLOAT_TOL):
                errors.append(f"cta.start={cta_start}≠last_narrative.end={last_end}")
        except (KeyError, TypeError, ValueError):
            pass

    cta_dur = cta_end - cta_start
    if cta_dur < CTA_DUR_MIN - FLOAT_TOL:
        errors.append(f"cta.duration={cta_dur:.3f}<{CTA_DUR_MIN}")
    # V-I-06: warning não-bloqueante se CTA > 15s
    if cta_dur > CTA_DUR_WARNING_MAX + FLOAT_TOL:
        warnings.append(f"cta.duration={cta_dur:.1f}s>{CTA_DUR_WARNING_MAX}s_recomendado")

    # V-I-14: CTA texto byte-a-byte igual ao canônico PT
    cta_l1_expected, cta_l2_expected = get_cta_overlay("pt")
    if cta.get("text_line_1") != cta_l1_expected or cta.get("text_line_2") != cta_l2_expected:
        errors.append("cta.text_not_matching_canonical_pt")

    return errors, warnings


def _call_anthropic_overlay(prompt: str, client) -> dict:
    _assert_test_mock_configured(client)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise OverlaySchemaError("anthropic.no_text_block_in_response")

    text = text_blocks[-1].text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise OverlaySchemaError(f"json.decode_error: {exc}")


def run_bo_overlay(project_id: int, db_session=None) -> dict:
    """Gera overlay BO V2 para um projeto.

    Pré-validação (antes de qualquer chamada LLM):
    - V-I-07: video_duration_seconds is None → ValueError
    - V-C-02: video_duration_seconds < 28.0 → ValueError

    Persiste em project.overlay_json.
    """
    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")

        # V-I-07
        if project.video_duration_seconds is None:
            raise ValueError(
                f"video_duration_seconds ausente no projeto {project_id} — "
                "backend deve popular antes de gerar overlay"
            )

        # V-C-02
        if project.video_duration_seconds < MIN_VIDEO_DURATION:
            raise ValueError(
                f"vídeo {project.video_duration_seconds:.1f}s < {MIN_VIDEO_DURATION}s "
                f"(MIN_VIDEO_DURATION); rejeitado antes do LLM"
            )

        if not project.research_data:
            raise ValueError(f"projeto {project_id} sem research_data")
        if not project.hook_escolhido_json:
            raise ValueError(f"projeto {project_id} sem hook_escolhido_json")

        antipadroes_pt = format_banned_terms_for_prompt("pt")
        base_prompt = build_bo_overlay_prompt(
            research_data=project.research_data,
            hook_escolhido=project.hook_escolhido_json,
            video_duration_seconds=float(project.video_duration_seconds),
            antipadroes_pt=antipadroes_pt,
            cut_start=project.cut_start or "",
            cut_end=project.cut_end or "",
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

            data = _call_anthropic_overlay(current_prompt, client)
            errors, warnings = validate_overlay_schema(data)

            if not errors:
                project.overlay_json = data
                db.commit()
                logger.info(
                    "bo_overlay: projeto %d sucesso na tentativa %d (warnings=%d)",
                    project_id, attempt + 1, len(warnings),
                )
                for w in warnings:
                    logger.warning("bo_overlay.warning: %s", w)
                return data

            last_errors = errors
            logger.warning(
                "bo_overlay: tentativa %d falhou — %d erros: %s",
                attempt + 1, len(errors), errors[:3],
            )

        raise OverlaySchemaError(
            f"esgotou {MAX_VALIDATION_RETRIES + 1} tentativas. Erros: {last_errors[:5]}"
        )
    finally:
        if own_session:
            db.close()
