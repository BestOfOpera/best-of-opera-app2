"""Rotas de importação do Redator (APP2) para o Editor (APP3)."""
import logging
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import REDATOR_API_URL
from app.database import get_db
from app.models import Edicao, Overlay, Post, Seo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/editor", tags=["importar"])

TIMEOUT = 30.0


def _extract_video_id(url: str) -> str:
    """Extrai o ID do vídeo de uma URL do YouTube."""
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url or "")
    return match.group(1) if match else ""


def _detect_music_lang(proj: dict) -> str:
    """Detecta o idioma da MÚSICA (não do conteúdo editorial).

    Prioridade:
    1. Campo explícito do Redator: "language", "music_language" ou "original_language"
    2. Inferência: idioma que NÃO aparece nas traduções (excluindo PT editorial)
    3. Se a inferência for ambígua (0 ou 2+ faltando), retorna None — forçando
       o operador a informar o idioma manualmente.

    O fallback "it" foi removido para evitar mascarar erros como o de músicas
    em inglês (onde EN aparece nas traduções do Redator, zerando o conjunto).
    """
    # 1. Campo explícito tem prioridade absoluta
    for field in ("language", "music_language", "original_language"):
        val = proj.get(field)
        if val and isinstance(val, str) and len(val) <= 10:
            return val.lower()

    # 2. Inferência por exclusão
    all_target = {"en", "pt", "es", "de", "fr", "it", "pl"}
    translation_langs = {t["language"] for t in proj.get("translations", [])}
    # O idioma original da música não é traduzido para si mesmo;
    # PT é o idioma editorial, não conta.
    missing = all_target - translation_langs - {"pt"}
    if len(missing) == 1:
        return missing.pop()

    # 3. Ambíguo — retorna None para forçar preenchimento manual
    return None


@router.get("/redator/projetos")
async def listar_projetos_redator(db: Session = Depends(get_db)):
    """Lista projetos do Redator (APP2) com status no Editor."""
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{REDATOR_API_URL}/api/projects")
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro ao conectar com o Redator: {e}")

    projects = resp.json()

    # Cruzar com edições já importadas
    edicoes_importadas = db.query(
        Edicao.redator_project_id, Edicao.id, Edicao.status
    ).filter(Edicao.redator_project_id.isnot(None)).all()
    mapa_edicoes = {e.redator_project_id: (e.id, e.status) for e in edicoes_importadas}

    result = []
    for p in projects:
        item = {
            "id": p["id"],
            "artist": p.get("artist", ""),
            "work": p.get("work", ""),
            "composer": p.get("composer", ""),
            "category": p.get("category", ""),
            "album_opera": p.get("album_opera", ""),
            "youtube_url": p.get("youtube_url", ""),
            "status": p.get("status", ""),
            "translations_count": len(p.get("translations", [])),
            "editor_status": None,
            "editor_edicao_id": None,
        }
        if p["id"] in mapa_edicoes:
            edicao_id, edicao_status = mapa_edicoes[p["id"]]
            item["editor_edicao_id"] = edicao_id
            item["editor_status"] = "concluido" if edicao_status == "concluido" else "em_andamento"
        result.append(item)

    return result


@router.post("/redator/importar/{project_id}")
async def importar_do_redator(
    project_id: int,
    idioma: str = None,
    eh_instrumental: bool = False,
    db: Session = Depends(get_db),
):
    """Importa um projeto do Redator e cria uma edição no Editor.

    ?idioma=XX — sobrescreve a detecção automática do idioma da música.
    Necessário quando o Redator tem tradução para o idioma original da música
    (ex: música em inglês → passar ?idioma=en).
    """
    # Verificar se o projeto já foi importado (anti-duplicata)
    existente = db.query(Edicao).filter(
        Edicao.redator_project_id == project_id
    ).first()
    if existente:
        raise HTTPException(409, detail={
            "duplicata": True,
            "edicao_existente_id": existente.id,
            "status": existente.status,
            "mensagem": f"Projeto já importado como edição #{existente.id} (status: {existente.status})"
        })

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

    music_lang = idioma or _detect_music_lang(proj)
    if music_lang is None:
        raise HTTPException(
            422,
            detail={
                "idioma_necessario": True,
                "mensagem": "Não foi possível detectar o idioma. Selecione manualmente.",
            },
        )

    # O conteúdo original do Redator (overlay, post, seo) é editorial em PT
    editorial_lang = "pt"

    # Montar overlays: {idioma: segmentos}
    overlays = {}
    if proj.get("overlay_json"):
        overlays[editorial_lang] = proj["overlay_json"]
    for t in proj.get("translations", []):
        if t.get("overlay_json"):
            overlays[t["language"]] = t["overlay_json"]

    # Montar posts: {idioma: texto}
    posts = {}
    if proj.get("post_text"):
        posts[editorial_lang] = proj["post_text"]
    for t in proj.get("translations", []):
        if t.get("post_text"):
            posts[t["language"]] = t["post_text"]

    # Montar SEO: {idioma: {titulo, tags}}
    seo = {}
    if proj.get("youtube_title") or proj.get("youtube_tags"):
        seo[editorial_lang] = {
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
        artista=proj.get("artista", "") or proj.get("artist", ""),
        musica=proj.get("musica", "") or proj.get("work", ""),
        compositor=proj.get("compositor", "") or proj.get("composer", ""),
        opera=proj.get("album_opera", ""),
        categoria=proj.get("category", ""),
        idioma=music_lang,
        eh_instrumental=eh_instrumental,
        sem_lyrics=eh_instrumental,
        corte_original_inicio=proj.get("cut_start"),
        corte_original_fim=proj.get("cut_end"),
        redator_project_id=project_id,
    )
    db.add(edicao)
    db.flush()

    # Salvar overlays (congelados — texto imutável a partir daqui)
    for idioma, segmentos in overlays.items():
        textos = [s.get("text", "") for s in segmentos if s.get("text")]
        logger.info(
            f"[importar] edicao={edicao.id} idioma={idioma} "
            f"overlay CONGELADO: {len(segmentos)} segs, textos={textos}"
        )
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
