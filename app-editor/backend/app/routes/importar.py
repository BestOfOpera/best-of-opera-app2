"""Rotas de importação do Redator (APP2) para o Editor (APP3)."""
import logging
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import REDATOR_API_URL
from app.database import get_db
from app.models import Edicao, Overlay, Post, Seo
from app.models.perfil import Perfil

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/editor", tags=["importar"])

TIMEOUT = 30.0


def _extract_video_id(url: str) -> str:
    """Extrai o ID do vídeo de uma URL do YouTube."""
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url or "")
    return match.group(1) if match else ""


def _detect_music_lang(proj: dict, idiomas_alvo: set = None) -> str:
    """Detecta o idioma da MÚSICA (não do conteúdo editorial).

    Prioridade:
    1. Campo explícito do Redator: "language", "music_language" ou "original_language"
    2. Inferência: idioma que NÃO aparece nas traduções (excluindo PT editorial)
    3. Se a inferência for ambígua (0 ou 2+ faltando), retorna None — forçando
       o operador a informar o idioma manualmente.

    idiomas_alvo: set de idiomas do perfil (fallback: {"en","pt","es","de","fr","it","pl"})
    """
    # 1. Campo explícito tem prioridade absoluta
    for field in ("language", "music_language", "original_language"):
        val = proj.get(field)
        if val and isinstance(val, str) and len(val) <= 10:
            return val.lower()

    # 2. Inferência por exclusão
    all_target = idiomas_alvo or {"en", "pt", "es", "de", "fr", "it", "pl"}
    translation_langs = {t["language"] for t in proj.get("translations", [])}
    # O idioma original da música não é traduzido para si mesmo;
    # PT é o idioma editorial, não conta.
    missing = all_target - translation_langs - {"pt"}
    if len(missing) == 1:
        return missing.pop()

    # 3. Ambíguo — retorna None para forçar preenchimento manual
    return None


@router.get("/redator/projetos")
async def listar_projetos_redator(perfil_id: int = None, db: Session = Depends(get_db)):
    """Lista projetos do Redator (APP2) com status no Editor.

    ?perfil_id=X — filtra por marca: passa brand_slug ao Redator e cruza só edições da marca.
    """
    brand_slug = None
    if perfil_id:
        perfil_obj = db.get(Perfil, perfil_id)
        if perfil_obj:
            brand_slug = perfil_obj.slug

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            url = f"{REDATOR_API_URL}/api/projects"
            if brand_slug:
                url += f"?brand_slug={brand_slug}"
            resp = await client.get(url)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro ao conectar com o Redator: {e}")

    data = resp.json()
    projects = data.get("projects", data) if isinstance(data, dict) else data

    # Cruzar com edições já importadas — filtrar por marca se perfil_id fornecido
    query = db.query(Edicao.redator_project_id, Edicao.id, Edicao.status).filter(
        Edicao.redator_project_id.isnot(None)
    )
    if perfil_id:
        query = query.filter(Edicao.perfil_id == perfil_id)
    edicoes_importadas = query.all()
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
    perfil_id: int = None,
    force: bool = False,
    db: Session = Depends(get_db),
):
    """Importa um projeto do Redator e cria uma edição no Editor.

    ?idioma=XX — sobrescreve a detecção automática do idioma da música.
    ?perfil_id=X — associa a edição a uma marca específica (padrão: Best of Opera).
    ?force=true — substitui edição existente (deleta a anterior e re-importa).
    """
    # Verificar se o projeto já foi importado (anti-duplicata)
    existente = db.query(Edicao).filter(
        Edicao.redator_project_id == project_id
    ).first()
    if existente:
        if not force:
            raise HTTPException(409, detail={
                "duplicata": True,
                "edicao_existente_id": existente.id,
                "status": existente.status,
                "mensagem": f"Projeto já importado como edição #{existente.id} (status: {existente.status}). "
                            f"Use ?force=true para substituir."
            })
        import logging
        _log = logging.getLogger(__name__)
        _log.info(
            f"[IMPORT] Force re-import: deletando edição {existente.id} "
            f"para projeto {project_id}"
        )
        db.delete(existente)
        db.commit()

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

    # Carregar perfil: obrigatório (SPEC-009 — sem fallback BO)
    if not perfil_id:
        raise HTTPException(400, "perfil_id é obrigatório para importação")
    perfil = db.get(Perfil, perfil_id)
    if not perfil:
        raise HTTPException(404, f"Perfil #{perfil_id} não encontrado")

    # Idiomas do perfil para detecção
    _idiomas_set = set(perfil.idiomas_alvo) if perfil and perfil.idiomas_alvo else None

    music_lang = idioma or _detect_music_lang(proj, _idiomas_set)
    if music_lang is None:
        if eh_instrumental:
            music_lang = proj.get("language") or "und"
        else:
            raise HTTPException(
                422,
                detail={
                    "idioma_necessario": True,
                    "mensagem": "Não foi possível detectar o idioma. Selecione manualmente.",
                },
            )

    # Idioma editorial: usa perfil.editorial_lang ou fallback "pt"
    editorial_lang = (perfil.editorial_lang if perfil and perfil.editorial_lang else "pt")

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

    # Marca instrumental por padrão (sem_lyrics_default) — override por projeto via eh_instrumental
    eh_instrumental_final = eh_instrumental or (perfil is not None and perfil.sem_lyrics_default)

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
        eh_instrumental=eh_instrumental_final,
        sem_lyrics=eh_instrumental_final,
        corte_original_inicio=proj.get("cut_start"),
        corte_original_fim=proj.get("cut_end"),
        redator_project_id=project_id,
        perfil_id=perfil.id if perfil else None,
    )
    db.add(edicao)
    db.flush()

    # Salvar overlays (congelados — texto imutável a partir daqui)
    for idioma, segmentos in overlays.items():
        # Validação: pular overlays vazios ou sem segmentos com texto
        if not segmentos:
            logger.warning(f"[importar] Overlay vazio para idioma={idioma}, edicao={edicao.id} — pulando")
            continue
        segmentos_validos = [
            s for s in segmentos
            if s.get("text", "").strip() or s.get("_is_cta")
        ]
        if not segmentos_validos:
            logger.warning(f"[importar] Todos segmentos sem texto para idioma={idioma}, edicao={edicao.id} — pulando")
            continue
        textos = [s.get("text", "") for s in segmentos_validos if s.get("text")]
        logger.info(
            f"[importar] edicao={edicao.id} idioma={idioma} "
            f"overlay CONGELADO: {len(segmentos_validos)} segs, textos={textos}"
        )
        db.add(Overlay(edicao_id=edicao.id, idioma=idioma, segmentos_original=segmentos_validos))
        # Diagnóstico: RC overlays devem ter \n para quebras de linha
        if perfil.slug == "reels-classics":
            for idx_s, s in enumerate(segmentos):
                txt = s.get("text", "")
                if len(txt) > 35 and "\n" not in txt and not s.get("_is_cta"):
                    logger.warning(
                        f"[importar] RC overlay sem \\n: "
                        f"edicao={edicao.id} seg={idx_s} text='{txt[:50]}...'"
                    )

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

    # Auto-download: se corte_original preenchido (importação RC via redator),
    # iniciar download automaticamente para encadear com auto-corte.
    auto_download = False
    if edicao.corte_original_inicio and edicao.corte_original_fim:
        from sqlalchemy import update as _sa_update
        from app.worker import task_queue
        from app.routes.pipeline import _download_task

        _res = db.execute(
            _sa_update(Edicao)
            .where(Edicao.id == edicao.id, Edicao.status == "aguardando")
            .values(status="baixando", passo_atual=1, erro_msg=None)
        )
        db.commit()
        if _res.rowcount:
            task_queue.put_nowait((_download_task, edicao.id))
            auto_download = True
            logger.info(f"[importar] Auto-download enfileirado edicao_id={edicao.id}")

    return {
        "id": edicao.id,
        "artista": edicao.artista,
        "musica": edicao.musica,
        "status": edicao.status,
        "overlays_count": len(overlays),
        "posts_count": len(posts),
        "seo_count": len(seo),
        "auto_download": auto_download,
    }
