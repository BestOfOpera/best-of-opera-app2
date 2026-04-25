"""
BO Research Service v2 — Pesquisa profunda do pipeline Best of Opera V2
======================================================================

Primeiro serviço orquestrador do pipeline BO V2 (Tarefa 1.2 da Fase 1).
Consome `bo_research_prompt_v1.build_bo_research_prompt(...)` + tool
Anthropic `web_search_20250305` (max_uses=5) e produz JSON estruturado
persistido em `project.research_data`.

Achados V-* cobertos:
- V-I-15: retry NÃO-acumulativo — cada tentativa usa
  `current_prompt = base_prompt + last_errors_str`, NUNCA prompt += err.
- V-I-17: hard cap de 5 web searches via `max_uses` no tool definition.
- V-I-21: validador exige `len(sources) >= 3` OU algum `tipo == "conhecimento_interno"`.

Decisão sync-first (consistente com Commit 10):
- Função pública `run_bo_research(project_id)` é sync.
- Validador `validate_research_schema(data)` é sync, transformação pura.

Branch B (Google CSE) — stub com NotImplementedError nesta fase.
Plano: implementação futura com GOOGLE_CSE_API_KEY/GOOGLE_CSE_CX.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

from backend.config import ANTHROPIC_API_KEY, USE_ANTHROPIC_WEB_SEARCH
from backend.services.bo.antipadroes_loader import format_banned_terms_for_prompt
from backend.services.bo.prompts.bo_research_prompt_v1 import build_bo_research_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"
MAX_VALIDATION_RETRIES = 2  # 2 tentativas de retry (3 chamadas total)
MAX_TOKENS = 4096
TEMPERATURE = 0.6  # precisão factual > criatividade


class ResearchSchemaError(RuntimeError):
    """Schema do research retornado pelo LLM está inválido após todas as tentativas."""


def _assert_test_mock_configured(client) -> None:
    """Belt-and-suspenders: aborta se TESTING_MODE=1 e client não foi mockado.

    Os fixtures autouse do conftest.py substituem `anthropic.Anthropic` por
    `FakeAnthropicClient`. Se chegou aqui em modo teste com client real,
    o mock falhou — abortar antes de cobrar API.
    """
    if os.environ.get("TESTING_MODE") == "1":
        # Em modo teste, o client deve ser FakeAnthropicClient
        cls_name = type(client).__name__
        if cls_name not in ("FakeAnthropicClient",):
            raise RuntimeError(
                f"TESTING_MODE=1 mas client é {cls_name} (esperado: FakeAnthropicClient). "
                "Mock do conftest.py falhou — chamada à API real foi abortada para "
                "evitar cobrança acidental."
            )


def validate_research_schema(data: dict) -> None:
    """Valida o schema do research JSON. Levanta `ResearchSchemaError` se inválido.

    Regras (achado V-I-21):
    - Chaves obrigatórias presentes
    - 5 ≤ len(fatos_surpreendentes) ≤ 8
    - len(sources) >= 3 OU algum source["tipo"] == "conhecimento_interno"
    - Warning (logger) se > 50% dos fatos não têm fonte_url declarada
    """
    REQUIRED_KEYS = {
        "classificacao_refinada",
        "metadados_obra",
        "metadados_interprete",
        "contexto_dramatico_cena",
        "fatos_surpreendentes",
        "sources",
        "verificacoes",
    }
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ResearchSchemaError(f"chaves_obrigatorias_ausentes: {sorted(missing)}")

    fatos = data.get("fatos_surpreendentes", [])
    if not isinstance(fatos, list):
        raise ResearchSchemaError(f"fatos_surpreendentes.tipo={type(fatos).__name__}≠list")
    if not (5 <= len(fatos) <= 8):
        raise ResearchSchemaError(f"fatos_surpreendentes.count={len(fatos)}∉[5,8]")

    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ResearchSchemaError(f"sources.tipo={type(sources).__name__}≠list")

    has_conhecimento_interno = any(
        isinstance(s, dict) and s.get("tipo") == "conhecimento_interno"
        for s in sources
    )
    if len(sources) < 3 and not has_conhecimento_interno:
        raise ResearchSchemaError(
            f"sources.count={len(sources)}<3 e sem declaração de 'conhecimento_interno'"
        )

    # Warning não-bloqueante: > 50% dos fatos sem fonte_url declarada
    fatos_sem_fonte = sum(
        1 for f in fatos
        if isinstance(f, dict) and not f.get("fonte_url") and not f.get("fonte_id")
    )
    if fatos_sem_fonte > len(fatos) / 2:
        logger.warning(
            "research_schema: %d/%d fatos sem fonte_url/fonte_id declarada (>50%%)",
            fatos_sem_fonte, len(fatos),
        )


def _call_anthropic_with_websearch(prompt: str, client) -> dict:
    """Chama Anthropic com tool web_search_20250305, max_uses=5 (achado V-I-17).

    Retorna o JSON parseado da resposta.
    """
    _assert_test_mock_configured(client)

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        tools=[
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }
        ],
        messages=[{"role": "user", "content": prompt}],
    )

    # Anthropic retorna content como lista de blocks; o último com tipo="text" tem o JSON
    text_blocks = [
        b for b in response.content
        if getattr(b, "type", None) == "text" or hasattr(b, "text")
    ]
    if not text_blocks:
        raise ResearchSchemaError("anthropic.no_text_block_in_response")

    text = text_blocks[-1].text
    # LLM pode envolver o JSON em ```json ... ``` — extrair se for o caso
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        return json.loads(text.strip())
    except json.JSONDecodeError as exc:
        raise ResearchSchemaError(f"json.decode_error: {exc}")


def run_bo_research(project_id: int, db_session=None) -> dict:
    """Executa pesquisa BO V2 para um projeto.

    Args:
        project_id: ID do projeto a pesquisar.
        db_session: sessão SQLAlchemy opcional (se None, abre uma nova).

    Returns:
        dict — research_data persistido em project.research_data.

    Raises:
        ResearchSchemaError: se schema falha em todas as tentativas.
        NotImplementedError: se USE_ANTHROPIC_WEB_SEARCH=false (Branch B stub).
        ValueError: se projeto não encontrado ou faltam campos.
    """
    if not USE_ANTHROPIC_WEB_SEARCH:
        # Branch B (Google CSE) — stub para fase futura
        raise NotImplementedError(
            "Branch B (Google CSE fallback) não habilitado nesta fase. "
            "Set USE_ANTHROPIC_WEB_SEARCH=true ou aguarde fase futura."
        )

    from backend.database import SessionLocal
    from backend.models import Project

    own_session = db_session is None
    db = db_session or SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if project is None:
            raise ValueError(f"projeto {project_id} não encontrado")

        antipadroes_pt = format_banned_terms_for_prompt("pt")
        base_prompt = build_bo_research_prompt(
            artist=project.artist or "",
            work=project.work or "",
            composer=project.composer or "",
            youtube_url=project.youtube_url or "",
            antipadroes_pt=antipadroes_pt,
            cut_start=project.cut_start or "",
            cut_end=project.cut_end or "",
            dimensao_1_detectada=project.dim_1_detectada or "",
            dimensao_2_detectada=project.dim_2_detectada or "",
            dimensao_3_pai_detectada=project.dim_3_pai_detectada or "",
            dimensao_3_sub_detectada=project.dim_3_sub_detectada or "",
        )

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=180.0)
        last_errors: list[str] = []
        last_exc: Exception | None = None

        # Retry NÃO-acumulativo (achado V-I-15)
        for attempt in range(MAX_VALIDATION_RETRIES + 1):
            current_prompt = base_prompt
            if last_errors:
                current_prompt = (
                    base_prompt
                    + "\n\n"
                    + "ERROS DA TENTATIVA ANTERIOR — corrigir e regerar JSON completo:\n"
                    + "\n".join(f"- {e}" for e in last_errors)
                )

            try:
                data = _call_anthropic_with_websearch(current_prompt, client)
                validate_research_schema(data)
                # Sucesso — persiste
                project.research_data = data
                db.commit()
                logger.info(
                    "bo_research: projeto %d sucesso na tentativa %d",
                    project_id, attempt + 1,
                )
                return data
            except ResearchSchemaError as exc:
                last_exc = exc
                last_errors = [str(exc)]
                logger.warning(
                    "bo_research: tentativa %d falhou: %s", attempt + 1, exc,
                )

        # Esgotou retries
        raise ResearchSchemaError(
            f"esgotou {MAX_VALIDATION_RETRIES + 1} tentativas. Último erro: {last_exc}"
        )
    finally:
        if own_session:
            db.close()
