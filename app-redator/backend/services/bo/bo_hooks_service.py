"""
BO Hooks Service v2 — Geração de 5 hooks ranqueados (Tarefa 1.3 da Fase 1)
=========================================================================

Consome `project.research_data` (preenchido pelo Passo 1.2), gera 5 hooks
ranqueados via `build_bo_hooks_prompt(...)` + Anthropic, valida com chars
recomputados do texto real, e persiste:

- `project.hooks_json` ← array dos 5 hooks gerados (campo legacy RC v1
  reaproveitado por compatibilidade — confirmado em models.py:65)
- `project.hook_escolhido_json` ← dict do hook escolhido pelo operador
  (campo BO V2 dedicado — confirmado em models.py:83)

ATENÇÃO: campo `selected_hook` (Text, RC v1) NÃO é usado em código BO V2.
É só para RC.

Achados V-* cobertos:
- V-I-08: validador RECOMPUTA len(text_line_1)/len(text_line_2) do texto
  real, ignora line_1_chars/line_2_chars declarados pelo LLM.
- V-I-14: comparação por chars conta após json.loads (LF real, não \\n
  escapado).
- V-I-15: retry NÃO-acumulativo.

Decisão sync-first: todas as funções `def` (não async).
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.services.bo.antipadroes_loader import format_banned_terms_for_prompt
from backend.services.bo.prompts.bo_hooks_prompt_v1 import build_bo_hooks_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_VALIDATION_RETRIES = 2
MAX_TOKENS = 4096
TEMPERATURE = 0.8  # criatividade controlada
MAX_LINE_CHARS = 38


class HooksSchemaError(RuntimeError):
    """Schema dos hooks retornados pelo LLM está inválido após todas as tentativas."""


def _assert_test_mock_configured(client) -> None:
    if os.environ.get("TESTING_MODE") == "1":
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado FakeAnthropicClient)."
            )


def validate_hooks(data: dict) -> list[str]:
    """Valida 5 hooks. Retorna lista de erros (vazia se válido).

    V-I-08: recomputa chars do texto real após json.loads.
    Cada hook tem `hook_text` com formato "linha1\\nlinha2" (LF real após
    parsing do JSON).
    """
    errors: list[str] = []
    hooks = data.get("hooks", [])

    if not isinstance(hooks, list):
        errors.append(f"hooks.tipo={type(hooks).__name__}≠list")
        return errors
    if len(hooks) != 5:
        errors.append(f"hooks.count={len(hooks)}≠5")

    for i, h in enumerate(hooks):
        if not isinstance(h, dict):
            errors.append(f"hooks[{i}].tipo={type(h).__name__}≠dict")
            continue

        hook_text = h.get("hook_text", "") or ""
        # V-I-14: comparação após parse — LF real, não \n escapado
        if "\n" in hook_text:
            line_1, line_2 = hook_text.split("\n", 1)
            # Pega só a primeira linha do segundo split (caso tenha mais quebras)
            line_2 = line_2.split("\n", 1)[0]
        else:
            line_1, line_2 = hook_text, ""

        # V-I-08: recomputa do texto real, NÃO confia em campos line_1_chars
        actual_l1 = len(line_1)
        actual_l2 = len(line_2)

        if actual_l1 > MAX_LINE_CHARS:
            errors.append(f"hooks[{i}].text_line_1={actual_l1}c>{MAX_LINE_CHARS}")
        if actual_l2 > MAX_LINE_CHARS:
            errors.append(f"hooks[{i}].text_line_2={actual_l2}c>{MAX_LINE_CHARS}")
        if actual_l1 + actual_l2 > 76:
            errors.append(f"hooks[{i}].total={actual_l1 + actual_l2}c>76")
        if not line_1 or not line_2:
            errors.append(f"hooks[{i}].2_linhas_obrigatorias")

    return errors


def _call_anthropic_hooks(prompt: str, client) -> dict:
    """Chama Anthropic e parse JSON da resposta."""
    _assert_test_mock_configured(client)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise HooksSchemaError("anthropic.no_text_block_in_response")

    text = text_blocks[-1].text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise HooksSchemaError(f"json.decode_error: {exc}")


def run_bo_hooks(project_id: int, db_session=None) -> dict:
    """Gera 5 hooks ranqueados para um projeto.

    Persiste array dos 5 hooks em `project.hooks_json`.
    NÃO persiste hook_escolhido — isso é feito por `choose_hook(...)` separadamente.
    """
    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")
        if not project.research_data:
            raise ValueError(
                f"projeto {project_id} sem research_data — rodar bo_research_service primeiro"
            )

        antipadroes_pt = format_banned_terms_for_prompt("pt")
        base_prompt = build_bo_hooks_prompt(
            research_data=project.research_data,
            work=project.work or "",
            artist=project.artist or "",
            composer=project.composer or "",
            antipadroes_pt=antipadroes_pt,
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=120.0)
        last_errors: list[str] = []

        # Retry NÃO-acumulativo (V-I-15)
        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            current_prompt = base_prompt
            if last_errors:
                current_prompt = (
                    base_prompt
                    + "\n\n"
                    + "ERROS DA TENTATIVA ANTERIOR:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                )

            data = _call_anthropic_hooks(current_prompt, client)
            errors = validate_hooks(data)

            if not errors:
                # Persiste array dos 5 hooks (campo legacy reaproveitado)
                project.hooks_json = data.get("hooks", [])
                db.commit()
                logger.info(
                    "bo_hooks: projeto %d sucesso na tentativa %d",
                    project_id, attempt + 1,
                )
                return data

            last_errors = errors
            logger.warning(
                "bo_hooks: tentativa %d falhou — %d erros: %s",
                attempt + 1, len(errors), errors[:3],
            )

        raise HooksSchemaError(
            f"esgotou {MAX_VALIDATION_RETRIES + 1} tentativas. Erros: {last_errors[:5]}"
        )
    finally:
        if own_session:
            db.close()


def choose_hook(project_id: int, chosen_hook: dict, db_session=None) -> dict:
    """Persiste o dict completo do hook escolhido em `project.hook_escolhido_json`.

    NÃO usar `selected_hook` (RC v1) — esse é um campo Text legacy só para RC.
    BO V2 usa `hook_escolhido_json` (JSON dict, models.py:83).
    """
    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")
        if not isinstance(chosen_hook, dict):
            raise ValueError(
                f"chosen_hook deve ser dict (recebido {type(chosen_hook).__name__})"
            )

        project.hook_escolhido_json = chosen_hook
        db.commit()
        db.refresh(project)
        logger.info("bo_hooks: projeto %d hook_escolhido_json persistido", project_id)
        return chosen_hook
    finally:
        if own_session:
            db.close()
