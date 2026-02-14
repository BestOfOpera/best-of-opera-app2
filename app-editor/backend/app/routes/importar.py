"""Rotas de importação do Redator (APP2) para o Editor (APP3)."""
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import REDATOR_API_URL
from app.database import get_db
from app.models import Edicao, Overlay, Post, Seo

router = APIRouter(prefix="/api/v1/editor", tags=["importar"])

TIMEOUT = 30.0


def _extract_video_id(url: str) -> str:
    """Extrai o ID do vídeo de uma URL do YouTube."""
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url or "")
    return match.group(1) if match else ""


def _detect_lang_from_hook(hook: str) -> str:
    """Detecta idioma do hook. Heurística simples baseada em palavras-chave."""
    if not hook:
        return "it"
    hook_lower = hook.lower()
    indicators = {
        "de": ["der", "die", "das", "und", "ich", "ein"],
        "fr": ["le", "la", "les", "une", "des", "que", "est"],
        "en": ["the", "and", "is", "are", "this", "that"],
        "es": ["el", "la", "los", "las", "una", "del"],
        "pt": ["o ", "os ", "as ", "uma", "dos", "das"],
        "ru": ["и", "в", "на", "что", "это"],
        "cs": ["je", "na", "se", "že", "to"],
    }
    for lang, words in indicators.items():
        if any(f" {w} " in f" {hook_lower} " for w in words):
            return lang
    return "it"


@router.get("/redator/projetos")
async def listar_projetos_redator():
    """Lista projetos do Redator (APP2)."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{REDATOR_API_URL}/api/projects")
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro ao conectar com o Redator: {e}")

    projects = resp.json()
    return [
        {
            "id": p["id"],
            "artist": p.get("artist", ""),
            "work": p.get("work", ""),
            "composer": p.get("composer", ""),
            "category": p.get("category", ""),
            "album_opera": p.get("album_opera", ""),
            "youtube_url": p.get("youtube_url", ""),
            "status": p.get("status", ""),
            "translations_count": len(p.get("translations", [])),
        }
        for p in projects
    ]


@router.post("/redator/importar/{project_id}")
async def importar_do_redator(project_id: int, db: Session = Depends(get_db)):
    """Importa um projeto do Redator e cria uma edição no Editor."""
    # Buscar projeto completo do Redator
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{REDATOR_API_URL}/api/projects/{project_id}")
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro ao buscar projeto do Redator: {e}")

    proj = resp.json()

    # Extrair dados básicos
    youtube_url = proj.get("youtube_url", "")
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        raise HTTPException(400, "Projeto do Redator não tem URL do YouTube válida")

    original_lang = _detect_lang_from_hook(proj.get("hook", ""))

    # Montar overlays: {idioma: segmentos}
    overlays = {}
    if proj.get("overlay_json"):
        overlays[original_lang] = proj["overlay_json"]
    for t in proj.get("translations", []):
        if t.get("overlay_json"):
            overlays[t["language"]] = t["overlay_json"]

    # Montar posts: {idioma: texto}
    posts = {}
    if proj.get("post_text"):
        posts[original_lang] = proj["post_text"]
    for t in proj.get("translations", []):
        if t.get("post_text"):
            posts[t["language"]] = t["post_text"]

    # Montar SEO: {idioma: {titulo, tags}}
    seo = {}
    if proj.get("youtube_title") or proj.get("youtube_tags"):
        seo[original_lang] = {
            "titulo": proj.get("youtube_title", ""),
            "tags": proj.get("youtube_tags", ""),
        }
    for t in proj.get("translations", []):
        if t.get("youtube_title") or t.get("youtube_tags"):
            seo[t["language"]] = {
                "titulo": t.get("youtube_title", ""),
                "tags": t.get("youtube_tags", ""),
            }

    # Criar a edição
    edicao = Edicao(
        youtube_url=youtube_url,
        youtube_video_id=video_id,
        artista=proj.get("artist", ""),
        musica=proj.get("work", ""),
        compositor=proj.get("composer", ""),
        opera=proj.get("album_opera", ""),
        categoria=proj.get("category", ""),
        idioma=original_lang,
    )
    db.add(edicao)
    db.flush()

    # Salvar overlays
    for idioma, segmentos in overlays.items():
        db.add(Overlay(edicao_id=edicao.id, idioma=idioma, segmentos_original=segmentos))

    # Salvar posts
    for idioma, texto in posts.items():
        db.add(Post(edicao_id=edicao.id, idioma=idioma, texto=texto))

    # Salvar SEO
    for idioma, seo_data in seo.items():
        db.add(Seo(
            edicao_id=edicao.id,
            idioma=idioma,
            titulo=seo_data.get("titulo"),
            tags=seo_data.get("tags"),
        ))

    db.commit()
    db.refresh(edicao)

    return {
        "id": edicao.id,
        "artista": edicao.artista,
        "musica": edicao.musica,
        "status": edicao.status,
        "overlays_count": len(overlays),
        "posts_count": len(posts),
        "seo_count": len(seo),
    }
