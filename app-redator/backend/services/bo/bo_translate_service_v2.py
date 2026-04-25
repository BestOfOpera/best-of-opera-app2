"""
BO Translate Service v2 — Tradução paralela 6 idiomas (Tarefa 1.7 da Fase 1)
=============================================================================

🔑 DECISÃO ARQUITETURAL (sync-first):
TODAS as funções deste módulo são sync (`def`, NÃO `async def`).

Razões:
1. translate_project_parallel (RC v1) é sync — paridade arquitetural
2. Paralelismo dos 6 idiomas via ThreadPoolExecutor(max_workers=6),
   NÃO via asyncio.gather — IO-bound (Anthropic API) é eficaz com threads
3. Endpoint Fase 2 vai rodar em rota sync FastAPI — sync casa direto
4. Onde plano mestre dizia `async def`, ADAPTO para sync. Dispatcher
   espelha sync sem `await`. Mistura sync→sync no callgraph é segura;
   o oposto (sync com `return coroutine_unawaited`) seria silently broken.

Achados V-* cobertos:
- V-I-05: tags_list é única fonte; tags_csv derivado em runtime
- V-I-08: validador RECOMPUTA chars do texto traduzido (l1/l2 ≤ 38)
- V-I-15: retry NÃO-acumulativo
- V-I-16: MAX_VALIDATION_RETRIES=1 (documentado vs overlay 2)
- V-I-18: @retry tenacity backoff exponencial 2s→60s p/ APIStatusError
- V-I-19: timestamps PRESERVADOS — math.isclose para floats, == para int (index)
- V-I-34: mark_translations_stale para invalidação por endpoints da Fase 2
"""
from __future__ import annotations

import json
import logging
import math
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import anthropic
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.config import ANTHROPIC_API_KEY
from backend.services.bo.antipadroes_loader import format_banned_terms_for_prompt
from backend.services.bo.bo_ctas import get_cta_overlay
from backend.services.bo.prompts.bo_translation_prompt_v1 import build_bo_translation_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
TEMPERATURE = 0.5  # tradução pede precisão > criatividade

# V-I-16: 1 retry para falhas de validação. Documentado: 6 idiomas paralelos
# × 2 retries = custo 12x. Trade-off: validador robusto (recomputação) reduz
# falhas reais; 1 retry é suficiente para correção pontual.
MAX_VALIDATION_RETRIES = 1

FLOAT_TOL = 0.001
MAX_LINE_CHARS = 38
MAX_TITLE_CHARS = 100
MAX_TAGS_CSV_CHARS = 450
MIN_TAGS = 8
MAX_TAGS = 15
MAX_POST_CHARS = 1900

TARGET_LANGUAGES = ["en", "es", "de", "fr", "it", "pl"]


class TranslationSchemaError(RuntimeError):
    """Schema da tradução retornado pelo LLM está inválido após todas as tentativas."""


def _assert_test_mock_configured(client) -> None:
    if os.environ.get("TESTING_MODE") == "1":
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado FakeAnthropicClient)."
            )


def validate_translation_schema(
    parsed: dict, target_lang: str, overlay_pt: dict,
) -> tuple[list[str], list[str]]:
    """Valida tradução. Retorna (errors, warnings).

    V-I-19: timestamps PRESERVADOS exatamente vs PT.
    - start_seconds, end_seconds (float): math.isclose(abs_tol=0.001)
    - index (int): comparação direta `==` (NÃO math.isclose)

    V-I-08: recomputa chars do texto traduzido (não confia em LLM).
    """
    errors: list[str] = []
    warnings: list[str] = []

    overlay_tr = parsed.get("overlay", {})
    captions_tr = overlay_tr.get("captions", []) if isinstance(overlay_tr, dict) else []
    captions_pt = overlay_pt.get("captions", [])

    if len(captions_tr) != len(captions_pt):
        errors.append(
            f"captions.count_mismatch: tr={len(captions_tr)} vs pt={len(captions_pt)}"
        )

    for i, (c_pt, c_tr) in enumerate(zip(captions_pt, captions_tr)):
        # V-I-08: recomputa chars do texto REAL traduzido
        l1_tr = (c_tr.get("text_line_1") or "")
        l2_tr = (c_tr.get("text_line_2") or "")
        if len(l1_tr) > MAX_LINE_CHARS:
            errors.append(f"captions[{i}].text_line_1({target_lang})={len(l1_tr)}c>{MAX_LINE_CHARS}")
        if len(l2_tr) > MAX_LINE_CHARS:
            errors.append(f"captions[{i}].text_line_2({target_lang})={len(l2_tr)}c>{MAX_LINE_CHARS}")
        if not l1_tr or not l2_tr:
            errors.append(f"captions[{i}].2_linhas_obrigatorias({target_lang})")

        # V-I-19: timestamps preservados — diferenciado por tipo
        # start_seconds, end_seconds: float, math.isclose
        for ts_field in ("start_seconds", "end_seconds"):
            v_pt = c_pt.get(ts_field)
            v_tr = c_tr.get(ts_field)
            if isinstance(v_pt, (int, float)) and isinstance(v_tr, (int, float)):
                if not math.isclose(float(v_pt), float(v_tr), abs_tol=FLOAT_TOL):
                    errors.append(
                        f"captions[{i}].{ts_field}_altered: pt={v_pt} vs tr={v_tr}"
                    )
            elif v_pt != v_tr:
                errors.append(
                    f"captions[{i}].{ts_field}_altered: pt={v_pt} vs tr={v_tr}"
                )

        # index: int, comparação direta (== é correto, math.isclose seria errado)
        idx_pt = c_pt.get("index")
        idx_tr = c_tr.get("index")
        if idx_pt is not None or idx_tr is not None:
            if idx_pt != idx_tr:
                errors.append(
                    f"captions[{i}].index_altered: pt={idx_pt} vs tr={idx_tr}"
                )

    # Post text
    post_tr = parsed.get("post_text", "") or ""
    if len(post_tr) > MAX_POST_CHARS:
        errors.append(f"post_text({target_lang}).len={len(post_tr)}>{MAX_POST_CHARS}")

    # YouTube
    yt_tr = parsed.get("youtube", {})
    if isinstance(yt_tr, dict):
        title_tr = yt_tr.get("title", "") or ""
        if len(title_tr) > MAX_TITLE_CHARS:
            errors.append(
                f"youtube.title({target_lang}).chars={len(title_tr)}>{MAX_TITLE_CHARS}"
            )
        tags_list_tr = yt_tr.get("tags_list", [])
        if not (MIN_TAGS <= len(tags_list_tr) <= MAX_TAGS):
            errors.append(
                f"youtube.tags_count({target_lang})={len(tags_list_tr)}∉[{MIN_TAGS},{MAX_TAGS}]"
            )
        tags_csv_chars = len(", ".join(tags_list_tr)) if tags_list_tr else 0
        if tags_csv_chars > MAX_TAGS_CSV_CHARS:
            errors.append(
                f"youtube.tags_csv({target_lang})={tags_csv_chars}c>{MAX_TAGS_CSV_CHARS}"
            )

    return errors, warnings


def _substitute_cta_post_llm(parsed: dict, target_lang: str) -> dict:
    """Substitui CTA do LLM por get_cta_overlay(target_lang) byte-a-byte.

    Regra v2: NÃO confiar no LLM para CTA — sempre substituir pós-LLM com
    valores canônicos de bo_ctas.py.
    """
    if "overlay" not in parsed or not isinstance(parsed["overlay"], dict):
        return parsed
    if "cta" not in parsed["overlay"] or not isinstance(parsed["overlay"]["cta"], dict):
        return parsed

    cta_l1, cta_l2 = get_cta_overlay(target_lang)
    parsed["overlay"]["cta"]["text_line_1"] = cta_l1
    parsed["overlay"]["cta"]["text_line_2"] = cta_l2
    return parsed


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type(anthropic.APIStatusError),
    reraise=True,
)
def _call_anthropic_translation(prompt: str, client) -> dict:
    """Chama Anthropic com tenacity backoff exponencial 2s→60s para 429/503 (V-I-18)."""
    _assert_test_mock_configured(client)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise TranslationSchemaError("anthropic.no_text_block_in_response")
    text = text_blocks[-1].text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise TranslationSchemaError(f"json.decode_error: {exc}")


def _translate_one_language(
    target_lang: str,
    overlay_pt: dict,
    post_pt: str,
    youtube_pt: dict,
    client,
) -> dict:
    """Traduz para 1 idioma. Sync, rodado dentro do ThreadPoolExecutor."""
    antipadroes = format_banned_terms_for_prompt(target_lang)
    base_prompt = build_bo_translation_prompt(
        target_language=target_lang,
        overlay_pt=overlay_pt,
        post_pt=post_pt,
        youtube_pt=youtube_pt,
        antipadroes_idioma_alvo_formatado=antipadroes,
    )

    last_errors: list[str] = []

    # V-I-16: 1 retry para falhas de validação (não-acumulativo, V-I-15)
    for attempt in range(MAX_VALIDATION_RETRIES + 1):
        current_prompt = base_prompt
        if last_errors:
            current_prompt = (
                base_prompt
                + "\n\nERROS DA TENTATIVA ANTERIOR:\n"
                + "\n".join(f"- {e}" for e in last_errors)
            )

        parsed = _call_anthropic_translation(current_prompt, client)
        # CTA substituído pós-LLM byte-a-byte
        parsed = _substitute_cta_post_llm(parsed, target_lang)

        errors, warnings = validate_translation_schema(parsed, target_lang, overlay_pt)

        if not errors:
            for w in warnings:
                logger.warning("bo_translate[%s].warning: %s", target_lang, w)
            return parsed

        last_errors = errors
        logger.warning(
            "bo_translate[%s]: tentativa %d falhou — %d erros: %s",
            target_lang, attempt + 1, len(errors), errors[:3],
        )

    raise TranslationSchemaError(
        f"[{target_lang}] esgotou {MAX_VALIDATION_RETRIES + 1} tentativas. Erros: {last_errors[:5]}"
    )


def translate_project_bo_v2(project_id: int, db_session=None) -> None:
    """Orquestra tradução BO V2 paralela em 6 idiomas via ThreadPoolExecutor.

    - PT é cópia byte-a-byte (NÃO passa pelo LLM)
    - Cada idioma → uma chamada Anthropic + validate_translation_schema
    - Persiste em Translation (verificacoes_json/is_stale/stale_reason já existem)
    """
    from backend.database import SessionLocal
    from backend.models import Project, Translation

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")
        if not project.overlay_json or not project.post_text or not project.youtube_title:
            raise ValueError(
                f"projeto {project_id} sem prerequisitos aprovados (overlay/post/youtube)"
            )

        overlay_pt = project.overlay_json
        post_pt = project.post_text
        youtube_pt = {
            "title": project.youtube_title,
            "tags_list": project.youtube_tags_list or [],
        }

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=180.0)

        # PT é cópia byte-a-byte
        pt_translation = Translation(
            project_id=project_id,
            language="pt",
            overlay_json=overlay_pt,
            post_text=post_pt,
            youtube_title=youtube_pt["title"],
            youtube_tags=", ".join(youtube_pt["tags_list"]) if youtube_pt["tags_list"] else None,
        )
        db.merge(pt_translation)

        # 6 idiomas paralelos via ThreadPoolExecutor
        results: dict[str, dict] = {}
        errors_by_lang: dict[str, str] = {}

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = {
                executor.submit(
                    _translate_one_language, lang, overlay_pt, post_pt, youtube_pt, client
                ): lang
                for lang in TARGET_LANGUAGES
            }
            for future in as_completed(futures):
                lang = futures[future]
                try:
                    results[lang] = future.result()
                except Exception as exc:
                    errors_by_lang[lang] = str(exc)
                    logger.error("bo_translate: %s falhou: %s", lang, exc)

        if errors_by_lang:
            raise TranslationSchemaError(
                f"falhas nas traduções: {errors_by_lang}"
            )

        # Persiste cada idioma
        for lang, parsed in results.items():
            yt_tr = parsed.get("youtube", {})
            tr = Translation(
                project_id=project_id,
                language=lang,
                overlay_json=parsed.get("overlay", {}),
                post_text=parsed.get("post_text", ""),
                youtube_title=yt_tr.get("title", ""),
                youtube_tags=", ".join(yt_tr.get("tags_list", [])),
                verificacoes_json=parsed.get("verificacoes"),
                is_stale=False,
            )
            db.merge(tr)

        db.commit()
        logger.info("bo_translate: projeto %d — 7 idiomas (pt + 6) persistidos", project_id)
    finally:
        if own_session:
            db.close()


def mark_translations_stale(project_id: int, reason: str = "pt_modified", db_session=None) -> None:
    """Marca todas as traduções (exceto PT) como stale por modificação no PT.

    Chamado pelos endpoints da Fase 2 quando overlay/post/youtube em PT é
    modificado pós-aprovação. Stale_translations devem ser regeneradas pelo
    operador antes do export.

    V-I-34.
    """
    from sqlalchemy import text

    from backend.database import SessionLocal

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        db.execute(
            text(
                "UPDATE translations SET is_stale = :stale, stale_reason = :reason "
                "WHERE project_id = :pid AND language != 'pt'"
            ),
            {"pid": project_id, "stale": True, "reason": reason},
        )
        db.commit()
        logger.info("bo_translate: projeto %d translations marcadas stale (%s)", project_id, reason)
    finally:
        if own_session:
            db.close()
