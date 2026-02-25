"""Tradução via Google Cloud Translation API v2 (Basic).

Substitui o Gemini para a etapa de tradução de letras,
mantendo a mesma assinatura e estrutura de retorno que
_traducao_task espera.
"""
from __future__ import annotations

import html
import logging

import httpx

from app.config import GOOGLE_TRANSLATE_API_KEY

logger = logging.getLogger(__name__)

TRANSLATE_URL = "https://translation.googleapis.com/language/translate/v2"
# Limite seguro da API v2 Basic: 128 textos por request
_BATCH_SIZE = 128


async def _translate_batch(texts: list[str], target_lang: str) -> list[str]:
    """Traduz uma lista de textos num único request à Cloud Translation API.

    Preserva a ordem e retorna strings vazias para entradas vazias.
    """
    results: list[str] = [""] * len(texts)

    # Índices dos textos não-vazios que precisam de tradução
    non_empty = [(i, t) for i, t in enumerate(texts) if t and t.strip()]
    if not non_empty:
        return results

    # Processa em lotes para respeitar o limite da API
    for chunk_start in range(0, len(non_empty), _BATCH_SIZE):
        chunk = non_empty[chunk_start : chunk_start + _BATCH_SIZE]
        idxs = [item[0] for item in chunk]
        txts = [item[1] for item in chunk]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                TRANSLATE_URL,
                params={"key": GOOGLE_TRANSLATE_API_KEY},
                json={"q": txts, "target": target_lang, "format": "text"},
            )
            resp.raise_for_status()

        translations = resp.json()["data"]["translations"]
        for arr_idx, orig_idx in enumerate(idxs):
            results[orig_idx] = html.unescape(translations[arr_idx]["translatedText"])

    return results


async def traduzir_letra_cloud(
    segmentos_alinhados: list,
    idioma_origem: str,
    idioma_alvo: str,
    metadados: dict,
) -> list:
    """Traduz os segmentos do alinhamento via Google Cloud Translation API.

    Mantém a mesma assinatura e estrutura de retorno que traduzir_letra do Gemini:
      [{"index": 1, "original": "...", "traducao": "..."}, ...]

    Se idioma_origem == idioma_alvo, copia os textos sem chamar a API.
    """
    textos = [
        s.get("texto_final", s.get("text", ""))
        for s in segmentos_alinhados
    ]

    if idioma_origem == idioma_alvo:
        logger.debug(f"[translate] origem == alvo ({idioma_alvo}), copiando sem traduzir")
        traducoes = textos[:]
    else:
        logger.debug(
            f"[translate] Traduzindo {len(textos)} segmentos "
            f"{idioma_origem} -> {idioma_alvo} via Cloud Translation API"
        )
        traducoes = await _translate_batch(textos, idioma_alvo)

    return [
        {
            "index": s.get("index", i + 1),
            "original": textos[i],
            "traducao": traducoes[i],
        }
        for i, s in enumerate(segmentos_alinhados)
    ]
