"""Serviço de busca de letras via Genius API + extração de página."""

from __future__ import annotations

import asyncio
import html as html_mod
import json
import logging
import re

import httpx

from app.config import GENIUS_API_TOKEN

_logger = logging.getLogger(__name__)

GENIUS_API_BASE = "https://api.genius.com"
GENIUS_TIMEOUT = 15

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _disponivel() -> bool:
    return bool(GENIUS_API_TOKEN)


async def buscar_letra(metadados: dict) -> str | None:
    """Busca letra no Genius: API search → extrai da página.

    Retorna a letra como string ou None se não encontrar.
    """
    if not _disponivel():
        _logger.info("Genius: token não configurado, pulando")
        return None

    artista = metadados.get("artista", "")
    musica = metadados.get("musica", "")

    if not artista or not musica:
        _logger.info("Genius: artista ou música vazio, pulando busca")
        return None

    _logger.info(f"Genius: buscando '{musica}' por '{artista}'")

    try:
        url = await _buscar_url_letra(artista, musica)
        if not url:
            return None
        letra = await _extrair_letra(url)
        if letra:
            _logger.info(f"Genius: letra encontrada ({len(letra)} chars)")
        return letra
    except asyncio.TimeoutError:
        _logger.warning(f"Genius: timeout buscando '{musica}' por '{artista}'")
        return None
    except Exception as e:
        _logger.warning(f"Genius: erro buscando letra — {e}")
        return None


async def _buscar_url_letra(artista: str, musica: str) -> str | None:
    """Busca na API do Genius e retorna a URL da página de letra."""
    async with httpx.AsyncClient(timeout=GENIUS_TIMEOUT) as client:
        resp = await client.get(
            f"{GENIUS_API_BASE}/search",
            params={"q": f"{musica} {artista}"},
            headers={"Authorization": f"Bearer {GENIUS_API_TOKEN}"},
        )
        resp.raise_for_status()

    data = resp.json()
    hits = data.get("response", {}).get("hits", [])

    if not hits:
        _logger.info(f"Genius: sem resultados para '{musica}' por '{artista}'")
        return None

    for hit in hits:
        if hit.get("type") == "song":
            result = hit["result"]
            url = result.get("url")
            title = result.get("full_title", "")
            _logger.info(f"Genius: encontrado '{title}' → {url}")
            return url

    url = hits[0].get("result", {}).get("url")
    return url


async def _extrair_letra(url: str) -> str | None:
    """Baixa a página do Genius e extrai a letra.

    Estratégia dupla:
    1. JSON embutido (__PRELOADED_STATE__) — mais confiável
    2. Scraping de containers HTML — fallback
    """
    async with httpx.AsyncClient(
        timeout=GENIUS_TIMEOUT,
        headers=_BROWSER_HEADERS,
        follow_redirects=True,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

    page_html = resp.text

    # Estratégia 1: JSON preloaded (funciona mesmo sem JS)
    letra = _extrair_de_json(page_html)
    if letra:
        return letra

    # Estratégia 2: scraping de containers HTML
    letra = _extrair_de_containers(page_html)
    if letra:
        return letra

    _logger.info(f"Genius: nenhuma letra extraída de {url}")
    return None


def _extrair_de_json(page_html: str) -> str | None:
    """Extrai letra do __PRELOADED_STATE__ JSON embutido na página."""
    match = re.search(
        r"__PRELOADED_STATE__\s*=\s*JSON\.parse\('(.*?)'\);",
        page_html,
        re.DOTALL,
    )
    if not match:
        return None

    try:
        raw_json = match.group(1)
        # Genius escapa aspas simples e barras
        raw_json = raw_json.replace("\\'", "'")
        # Remover escapes inválidos antes de decodificar unicode
        # (ex: \/ é inválido em Python mas válido em JS)
        raw_json = raw_json.replace("\\/", "/")
        # Decodificar unicode escapes (\u00e8 → è)
        raw_json = raw_json.encode("utf-8").decode("unicode_escape").encode("latin-1").decode("utf-8")
        data = json.loads(raw_json)
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as e:
        _logger.debug(f"Genius: JSON preloaded não parseável — {e}")
        return None

    body_html = (
        data.get("songPage", {})
        .get("lyricsData", {})
        .get("body", {})
        .get("html", "")
    )

    if not body_html:
        return None

    letra = _html_para_texto(body_html)
    letra = _limpar_letra(letra)
    return letra if letra else None


def _extrair_de_containers(page_html: str) -> str | None:
    """Fallback: extrai letra dos containers HTML com data-lyrics-container."""
    containers = re.findall(
        r'data-lyrics-container="true"[^>]*>(.*?)(?=</div>\s*<div|</div>\s*</section)',
        page_html,
        re.DOTALL,
    )

    lyrics_parts = [c for c in containers if "<br" in c]

    if not lyrics_parts:
        return None

    raw = "\n".join(lyrics_parts)
    letra = _html_para_texto(raw)
    letra = _limpar_letra(letra)
    return letra if letra else None


def _html_para_texto(raw_html: str) -> str:
    """Converte HTML de letras do Genius em texto limpo."""
    text = raw_html
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html_mod.unescape(text)
    return text


def _limpar_letra(raw: str) -> str:
    """Remove lixo típico do Genius (headers, rodapé, marcadores)."""
    lines = raw.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Pular section headers tipo [Verse 1], [Chorus], [Strofa 1], etc.
        if re.match(r"^\[.*\]$", stripped):
            continue
        # Pular linha de contribuidores do Genius
        if re.search(r"\d+\s*Contributor", stripped):
            continue
        if stripped.endswith("Lyrics") and len(stripped) > 20:
            continue
        # Pular embed do Genius no final
        if "Embed" in stripped and stripped and stripped[-1].isdigit():
            continue
        if stripped.startswith("You might also like"):
            continue
        cleaned.append(stripped)

    result = "\n".join(cleaned).strip()
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")
    # Genius retorna "Instrumental" para peças sem letra
    if result.lower().strip() in ("instrumental", ""):
        return ""
    return result
