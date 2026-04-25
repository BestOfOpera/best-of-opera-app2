"""
BO Detect Metadata Service v2 — Gate 0 (Tarefa 1.9 da Fase 1)
=============================================================

Classificação multimodal expandida do projeto BO V2. Recebe screenshot +
título + descrição do YouTube e produz:

- 5 dimensões classificatórias canonizadas (validadas contra enums)
- Metadados estruturados: artist, work, composer

Persistência:
- project.dim_1_detectada (formação)
- project.dim_2_detectada (tipo vocal/instrumento)
- project.dim_2_subtipo_detectada (subtipo da dim 2)
- project.dim_3_pai_detectada (categoria pai — atenção: 'pai', NÃO 'pais')
- project.dim_3_sub_detectada (subcategoria — atenção: 'sub', NÃO 'subcategoria')
- project.artist, project.work, project.composer

Achados V-* cobertos:
- V-I-23: enums canonizados; cada `dimensao_*` deve estar nas listas
  importadas de bo_detect_metadata_prompt_v1

Decisão sync-first.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from backend.config import ANTHROPIC_API_KEY
from backend.services.bo.prompts.bo_detect_metadata_prompt_v1 import (
    DIMENSAO_1_FORMACAO,
    DIMENSAO_2_TIPO_VOCAL,
    DIMENSAO_3_PAIS,
    DIMENSAO_3_SUBCATEGORIAS,
    build_bo_detect_metadata_prompt,
)

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048
TEMPERATURE = 0.3  # precisão > criatividade


class DetectMetadataError(RuntimeError):
    """Erro de classificação ou enum inválido em detect_metadata_bo."""


def _assert_test_mock_configured(client) -> None:
    if os.environ.get("TESTING_MODE") == "1":
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado FakeAnthropicClient)."
            )


def validate_enums(parsed: dict) -> None:
    """Valida que cada `dimensao_*` está na lista canônica.

    V-I-23: enums canonizados. Levanta DetectMetadataError se valor inválido.

    Nota sobre 'nao_aplicavel' para Dimensão 2:
    - DIMENSAO_2_TIPO_VOCAL já INCLUI 'nao_aplicavel' (linha 53 do prompt v1).
    - Portanto a aceitação é automática via lookup direto na lista.
    """
    classificacao = parsed.get("classificacao", {})
    if not isinstance(classificacao, dict):
        raise DetectMetadataError(
            f"classificacao.tipo={type(classificacao).__name__}≠dict"
        )

    # Dimensão 1: formação
    dim_1 = classificacao.get("dimensao_1_formacao")
    if dim_1 and dim_1 not in DIMENSAO_1_FORMACAO:
        raise DetectMetadataError(
            f"dim_1 enum inválido: {dim_1!r}. Válidos: {DIMENSAO_1_FORMACAO}"
        )

    # Dimensão 2: tipo vocal (já inclui 'nao_aplicavel')
    dim_2 = classificacao.get("dimensao_2_tipo_vocal")
    if dim_2 and dim_2 not in DIMENSAO_2_TIPO_VOCAL:
        raise DetectMetadataError(
            f"dim_2 enum inválido: {dim_2!r}. Válidos: {DIMENSAO_2_TIPO_VOCAL}"
        )

    # Dimensão 3: categoria pai
    dim_3_pai = classificacao.get("dimensao_3_pai")
    if dim_3_pai and dim_3_pai not in DIMENSAO_3_PAIS:
        raise DetectMetadataError(
            f"dim_3_pai enum inválido: {dim_3_pai!r}. Válidos: {DIMENSAO_3_PAIS}"
        )

    # Dimensão 3: subcategoria — deve ser consistente com pai
    dim_3_sub = classificacao.get("dimensao_3_sub")
    if dim_3_sub and dim_3_pai:
        valid_subs = DIMENSAO_3_SUBCATEGORIAS.get(dim_3_pai, [])
        if dim_3_sub not in valid_subs:
            raise DetectMetadataError(
                f"dim_3_sub {dim_3_sub!r} inválido para pai={dim_3_pai!r}. "
                f"Válidos: {valid_subs}"
            )


def _call_anthropic_multimodal(prompt: str, screenshot_base64: str | None, client) -> dict:
    """Chama Anthropic com imagem (multimodal) + prompt texto. Sync."""
    _assert_test_mock_configured(client)

    content_blocks: list[dict] = []
    if screenshot_base64:
        content_blocks.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/png",
                "data": screenshot_base64,
            },
        })
    content_blocks.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        messages=[{"role": "user", "content": content_blocks}],
    )

    text_blocks = [b for b in response.content if hasattr(b, "text")]
    if not text_blocks:
        raise DetectMetadataError("anthropic.no_text_block_in_response")

    text = text_blocks[-1].text
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise DetectMetadataError(f"json.decode_error: {exc}")


def detect_metadata_bo(
    project_id: int,
    screenshot_base64: str | None = None,
    youtube_url: str = "",
    video_title: str = "",
    video_description: str = "",
    operator_hints: str = "",
    db_session=None,
) -> dict:
    """Detecta metadata e classifica projeto BO V2 multidimensionalmente.

    Persiste nos 5 nomes EXATOS de models.py:84-88:
    - dim_1_detectada, dim_2_detectada, dim_2_subtipo_detectada,
      dim_3_pai_detectada, dim_3_sub_detectada
    - artist, work, composer
    """
    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")

        prompt = build_bo_detect_metadata_prompt(
            youtube_url=youtube_url or project.youtube_url or "",
            video_title_raw=video_title,
            video_description_raw=video_description,
            operator_hints=operator_hints,
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=60.0)
        parsed = _call_anthropic_multimodal(prompt, screenshot_base64, client)

        # Validação de enums (V-I-23) — levanta DetectMetadataError se inválido
        validate_enums(parsed)

        # Persistência nos 5 nomes EXATOS de models.py:84-88
        classif = parsed.get("classificacao", {})
        project.dim_1_detectada = classif.get("dimensao_1_formacao")
        project.dim_2_detectada = classif.get("dimensao_2_tipo_vocal")
        project.dim_2_subtipo_detectada = classif.get("dimensao_2_subtipo")
        project.dim_3_pai_detectada = classif.get("dimensao_3_pai")
        project.dim_3_sub_detectada = classif.get("dimensao_3_sub")

        # Metadados editorialmente úteis
        meta = parsed.get("metadados", {}) if isinstance(parsed.get("metadados"), dict) else {}
        if meta.get("artist"):
            project.artist = meta["artist"]
        if meta.get("work"):
            project.work = meta["work"]
        if meta.get("composer"):
            project.composer = meta["composer"]

        db.commit()
        logger.info(
            "bo_detect_metadata: projeto %d classificado — dim_1=%s dim_2=%s dim_3=%s/%s",
            project_id,
            project.dim_1_detectada,
            project.dim_2_detectada,
            project.dim_3_pai_detectada,
            project.dim_3_sub_detectada,
        )
        return parsed
    finally:
        if own_session:
            db.close()


# Smoke pós-implementação (sanity check anti-typo) — executa só se chamado direto
def _verify_model_columns_exist() -> None:
    """Verifica que as 5 colunas dim_*_detectada existem no model.

    Útil para detectar typos durante desenvolvimento. Não chamado em runtime.
    """
    from backend.models import Project
    expected = (
        "dim_1_detectada",
        "dim_2_detectada",
        "dim_2_subtipo_detectada",
        "dim_3_pai_detectada",
        "dim_3_sub_detectada",
    )
    for f in expected:
        assert hasattr(Project, f), f"campo {f} ausente do model — typo?"


if __name__ == "__main__":
    _verify_model_columns_exist()
    print("OK -- todas as 5 colunas dim_* presentes no model")
