# CONTEXTO-PROJETO — Best of Opera App2
> Gerado em 2026-02-25. Referência rápida para Claude Code.

---

## 1. Tree do Monorepo (2 níveis)

```
best-of-opera-app2/
├── .claude/
│   └── settings.local.json
├── CLAUDE.md
├── HANDOFF.md
├── PLANO-IMPLEMENTACAO-WORKER.md
├── README.md
├── .dockerignore
├── .env / .env.example / .gitignore
├── app-curadoria/
│   └── backend/
├── app-editor/
│   ├── BRIEFING-CLAUDE-CODE-APP-EDITOR.md
│   ├── CLAUDE.md
│   ├── DECISIONS.md
│   ├── PROGRESS.md
│   ├── railway.json
│   ├── backend/
│   │   ├── Dockerfile
│   │   ├── railway.json
│   │   ├── requirements.txt
│   │   └── app/
│   │       ├── main.py
│   │       ├── worker.py
│   │       ├── config.py
│   │       ├── database.py
│   │       ├── schemas.py
│   │       ├── models/
│   │       ├── routes/
│   │       └── services/
│   └── frontend/
│       ├── package.json
│       └── src/
├── app-portal/
│   ├── Dockerfile
│   ├── railway.json
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── app/
│   ├── components/
│   │   └── editor/
│   └── lib/
│       └── api/
├── app-redator/
│   ├── Dockerfile
│   ├── Procfile
│   ├── railway.json
│   ├── requirements.txt
│   ├── backend/
│   └── frontend/
├── scripts/
│   └── configure-railway-r2.sh
└── shared/
    ├── __init__.py
    └── storage_service.py
```

---

## 2. Backend — Arquivos Completos

### app/worker.py

```python
"""Worker sequencial com asyncio.Queue para tasks longas.

Substitui BackgroundTasks do FastAPI. Roda uma task por vez no mesmo container.
"""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

# Fila global — itens: (async_callable, edicao_id)
task_queue: asyncio.Queue = asyncio.Queue()

_STALE_THRESHOLD = timedelta(minutes=5)


async def worker_loop():
    """Consome tasks da fila uma por vez. Roda como asyncio.Task no lifespan."""
    logger.info("[worker] Worker sequencial iniciado")
    while True:
        try:
            task_func, edicao_id = await task_queue.get()
            logger.info(f"[worker] Iniciando task edicao_id={edicao_id}")
            try:
                await task_func(edicao_id)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error(
                    f"[worker] Task edicao_id={edicao_id} falhou com exceção não tratada: {e}",
                    exc_info=True,
                )
                try:
                    from app.database import SessionLocal
                    from app.models import Edicao
                    with SessionLocal() as db:
                        edicao = db.get(Edicao, edicao_id)
                        if edicao and edicao.status not in ("erro", "concluido", "preview_pronto"):
                            edicao.status = "erro"
                            edicao.erro_msg = f"Falha no worker: {str(e)[:500]}"
                            db.commit()
                except Exception:
                    logger.error(f"[worker] Não conseguiu salvar status 'erro' para edicao_id={edicao_id}")
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            logger.info("[worker] CancelledError — encerrando cleanly")
            raise
        except Exception as e:
            logger.error(f"[worker] Erro inesperado no loop principal: {e}", exc_info=True)


def _make_preview_wrapper(eid: int, idioma: str):
    """Cria wrapper para _render_task com is_preview=True e idioma fixo."""
    async def _preview_task(_ignored_id: int):
        from app.routes.pipeline import _render_task
        await _render_task(eid, idiomas_renderizar=[idioma], is_preview=True)
    return _preview_task


def requeue_stale_tasks():
    """Recoloca na fila TODAS as edições em status de processamento no startup."""
    from app.database import SessionLocal
    from app.models import Edicao
    from app.routes.pipeline import _traducao_task, _render_task

    with SessionLocal() as db:
        candidatos = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).all()

        requeued = 0
        for edicao in candidatos:
            eid, status = edicao.id, edicao.status

            if status == "traducao":
                task_queue.put_nowait((_traducao_task, eid))
            elif status == "renderizando":
                task_queue.put_nowait((_render_task, eid))
            elif status == "preview":
                idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
                task_queue.put_nowait((_make_preview_wrapper(eid, idioma_preview), eid))

            requeued += 1
            logger.info(f"[worker] requeue: edicao_id={eid} status={status} reagendada")

    logger.info(f"[worker] requeue_stale_tasks: {requeued} task(s) reagendada(s)")


def is_worker_busy() -> dict:
    """Verifica se há edição sendo processada ativamente."""
    from app.database import SessionLocal
    from app.models import Edicao

    with SessionLocal() as db:
        em_proc = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).first()

        if em_proc:
            resultado = {
                "ocupado": True,
                "edicao_id": em_proc.id,
                "etapa": em_proc.status,
                "progresso": em_proc.progresso_detalhe or {},
            }
        else:
            resultado = {"ocupado": False}

    return resultado
```

---

### app/main.py

```python
"""APP Editor — Best of Opera. Ponto de entrada FastAPI."""
import asyncio
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import STORAGE_PATH
from app.database import engine, Base
from app.routes import edicoes, letras, pipeline, health, importar

import logging
logger = logging.getLogger(__name__)


def _run_migrations():
    """Adiciona colunas novas que create_all não cria em tabelas existentes."""
    from sqlalchemy import text, inspect
    insp = inspect(engine)
    if "editor_edicoes" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("editor_edicoes")]
    with engine.begin() as conn:
        for col_name, col_type in [
            ("corte_original_inicio", "VARCHAR(20)"),
            ("corte_original_fim", "VARCHAR(20)"),
            ("notas_revisao", "TEXT"),
            ("r2_base", "VARCHAR(500)"),
            ("redator_project_id", "INTEGER"),
            ("task_heartbeat", "TIMESTAMP"),
            ("progresso_detalhe", "JSON"),
        ]:
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE editor_edicoes ADD COLUMN {col_name} {col_type}"))
                logger.info(f"Migration: added column {col_name}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    from app.worker import worker_loop, requeue_stale_tasks
    worker_task = asyncio.create_task(worker_loop())
    requeue_stale_tasks()
    yield
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="Best of Opera — Editor",
    description="APP3: Download, corte, lyrics, renderização em 7 idiomas",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(edicoes.router)
app.include_router(letras.router)
app.include_router(pipeline.router)
app.include_router(importar.router)
```

---

### app/models/edicao.py

```python
"""Modelo principal: editor_edicoes."""
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, func
from sqlalchemy import JSON

from app.database import Base


class Edicao(Base):
    __tablename__ = "editor_edicoes"

    id = Column(Integer, primary_key=True, index=True)
    curadoria_video_id = Column(Integer, nullable=True)
    youtube_url = Column(String(500), nullable=False)
    youtube_video_id = Column(String(20), nullable=False)

    artista = Column(String(300), nullable=False)
    musica = Column(String(300), nullable=False)
    compositor = Column(String(300))
    opera = Column(String(300))
    categoria = Column(String(50))
    idioma = Column(String(10), nullable=False)
    eh_instrumental = Column(Boolean, default=False)
    duracao_total_sec = Column(Float)

    status = Column(String(30), default="aguardando")
    passo_atual = Column(Integer, default=1)
    erro_msg = Column(Text)

    janela_inicio_sec = Column(Float)
    janela_fim_sec = Column(Float)
    duracao_corte_sec = Column(Float)

    corte_original_inicio = Column(String(20))
    corte_original_fim = Column(String(20))

    arquivo_video_completo = Column(String(500))
    arquivo_video_cortado = Column(String(500))
    arquivo_audio_completo = Column(String(500))
    arquivo_video_cru = Column(String(500))

    rota_alinhamento = Column(String(5))
    confianca_alinhamento = Column(Float)

    r2_base = Column(String(500), nullable=True)  # ex: "Pavarotti - Nessun Dorma"
    redator_project_id = Column(Integer, nullable=True)
    notas_revisao = Column(Text, nullable=True)

    editado_por = Column(String(100))
    tempo_edicao_seg = Column(Integer)

    task_heartbeat = Column(DateTime, nullable=True)
    progresso_detalhe = Column(JSON, default=dict)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

---

### app/schemas.py

```python
"""Pydantic schemas para a API."""
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime


# --- Edição ---
class EdicaoCreate(BaseModel):
    youtube_url: str
    youtube_video_id: str
    artista: str
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    categoria: Optional[str] = None
    idioma: str
    eh_instrumental: bool = False
    overlays: Optional[dict] = None
    posts: Optional[dict] = None
    seo: Optional[dict] = None


class EdicaoUpdate(BaseModel):
    artista: Optional[str] = None
    musica: Optional[str] = None
    compositor: Optional[str] = None
    opera: Optional[str] = None
    categoria: Optional[str] = None
    idioma: Optional[str] = None
    eh_instrumental: Optional[bool] = None
    status: Optional[str] = None
    passo_atual: Optional[int] = None
    erro_msg: Optional[str] = None


class EdicaoOut(BaseModel):
    id: int
    youtube_url: str
    youtube_video_id: str
    artista: str
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    categoria: Optional[str] = None
    idioma: str
    eh_instrumental: bool
    duracao_total_sec: Optional[float] = None
    status: str
    passo_atual: int
    erro_msg: Optional[str] = None
    janela_inicio_sec: Optional[float] = None
    janela_fim_sec: Optional[float] = None
    duracao_corte_sec: Optional[float] = None
    corte_original_inicio: Optional[str] = None
    corte_original_fim: Optional[str] = None
    arquivo_audio_completo: Optional[str] = None
    arquivo_video_completo: Optional[str] = None
    rota_alinhamento: Optional[str] = None
    confianca_alinhamento: Optional[float] = None
    notas_revisao: Optional[str] = None
    task_heartbeat: Optional[datetime] = None
    progresso_detalhe: Optional[Any] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Letra ---
class LetraCreate(BaseModel):
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    idioma: str
    letra: str
    fonte: Optional[str] = "manual"


class LetraUpdate(BaseModel):
    letra: Optional[str] = None
    fonte: Optional[str] = None
    validado_por: Optional[str] = None


class LetraOut(BaseModel):
    id: int
    musica: str
    compositor: Optional[str] = None
    opera: Optional[str] = None
    idioma: str
    letra: str
    fonte: Optional[str] = None
    vezes_utilizada: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Alinhamento ---
class AlinhamentoOut(BaseModel):
    id: int
    edicao_id: int
    segmentos_completo: list
    segmentos_cortado: Optional[list] = None
    confianca_media: Optional[float] = None
    rota: Optional[str] = None
    validado: bool

    class Config:
        from_attributes = True


class AlinhamentoValidar(BaseModel):
    segmentos: list
    validado_por: Optional[str] = "operador"


class LetraAprovar(BaseModel):
    letra: str
    fonte: Optional[str] = "manual"
    validado_por: Optional[str] = "operador"
```

---

### app/routes/importar.py

```python
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
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url or "")
    return match.group(1) if match else ""


def _detect_music_lang(proj: dict) -> str:
    """Detecta o idioma da MÚSICA (não do conteúdo editorial).

    Prioridade:
    1. Campo explícito: "language", "music_language" ou "original_language"
    2. Inferência: idioma que NÃO aparece nas traduções (excluindo PT editorial)
    3. Ambíguo → retorna None (força preenchimento manual)
    """
    for field in ("language", "music_language", "original_language"):
        val = proj.get(field)
        if val and isinstance(val, str) and len(val) <= 10:
            return val.lower()

    all_target = {"en", "pt", "es", "de", "fr", "it", "pl"}
    translation_langs = {t["language"] for t in proj.get("translations", [])}
    missing = all_target - translation_langs - {"pt"}
    if len(missing) == 1:
        return missing.pop()

    return None


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
async def importar_do_redator(
    project_id: int,
    idioma: str = None,
    db: Session = Depends(get_db),
):
    """Importa um projeto do Redator e cria uma edição no Editor.

    ?idioma=XX — sobrescreve a detecção automática do idioma da música.
    """
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{REDATOR_API_URL}/api/projects/{project_id}")
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro ao buscar projeto do Redator: {e}")

    proj = resp.json()

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

    editorial_lang = "pt"

    overlays = {}
    if proj.get("overlay_json"):
        overlays[editorial_lang] = proj["overlay_json"]
    for t in proj.get("translations", []):
        if t.get("overlay_json"):
            overlays[t["language"]] = t["overlay_json"]

    posts = {}
    if proj.get("post_text"):
        posts[editorial_lang] = proj["post_text"]
    for t in proj.get("translations", []):
        if t.get("post_text"):
            posts[t["language"]] = t["post_text"]

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

    edicao = Edicao(
        youtube_url=youtube_url,
        youtube_video_id=video_id,
        artista=proj.get("artist", ""),
        musica=proj.get("work", ""),
        compositor=proj.get("composer", ""),
        opera=proj.get("album_opera", ""),
        categoria=proj.get("category", ""),
        idioma=music_lang,
        corte_original_inicio=proj.get("cut_start"),
        corte_original_fim=proj.get("cut_end"),
    )
    db.add(edicao)
    db.flush()

    for idioma, segmentos in overlays.items():
        db.add(Overlay(edicao_id=edicao.id, idioma=idioma, segmentos_original=segmentos))

    for idioma, texto in posts.items():
        db.add(Post(edicao_id=edicao.id, idioma=idioma, texto=texto))

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
```

---

### app/services/legendas.py

```python
"""Serviço de geração de arquivos ASS com 3 tracks de legenda."""
from typing import Optional
import pysubs2
from app.services.regua import timestamp_to_seconds, seconds_to_timestamp

# Layout para vídeo 16:9 dentro de frame 9:16 (1080x1920)
# Vídeo 640x360 → escala para 1080x608, centralizado verticalmente
# Barras pretas: 656px em cima, vídeo 608px, 656px embaixo
ESTILOS_PADRAO = {
    "overlay": {
        "fontname": "Georgia",
        "fontsize": 47,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 3,
        "shadow": 1,
        "alignment": 8,   # topo
        "marginv": 490,
        "bold": True,
        "italic": True,
    },
    "lyrics": {
        "fontname": "Georgia",
        "fontsize": 35,
        "primarycolor": "#FFFF64",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,   # base
        "marginv": 580,
        "bold": True,
        "italic": True,
    },
    "traducao": {
        "fontname": "Georgia",
        "fontsize": 35,
        "primarycolor": "#FFFFFF",
        "outlinecolor": "#000000",
        "outline": 2,
        "shadow": 0,
        "alignment": 2,   # base, abaixo dos lyrics
        "marginv": 520,
        "bold": True,
        "italic": True,
    },
}

OVERLAY_MAX_CHARS = 35


def hex_to_ssa_color(hex_color: str) -> pysubs2.Color:
    hex_color = hex_color.lstrip("#")
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return pysubs2.Color(r, g, b, 0)


def seg_to_ms(value) -> int:
    if isinstance(value, (int, float)):
        return int(value * 1000)
    if isinstance(value, str):
        return int(timestamp_to_seconds(value) * 1000)
    return 0


def quebrar_texto_overlay(texto: str, max_chars: int = OVERLAY_MAX_CHARS) -> str:
    """Quebra texto em 2 linhas equilibradas se exceder max_chars."""
    if len(texto) <= max_chars:
        return texto
    palavras = texto.split()
    if len(palavras) <= 1:
        return texto
    meio = len(texto) / 2
    melhor_quebra = 0
    melhor_diff = len(texto)
    pos = 0
    for i, palavra in enumerate(palavras[:-1]):
        pos += len(palavra) + (1 if i > 0 else 0)
        diff = abs(pos - meio)
        if diff < melhor_diff:
            melhor_diff = diff
            melhor_quebra = i + 1
    linha1 = " ".join(palavras[:melhor_quebra])
    linha2 = " ".join(palavras[melhor_quebra:])
    return linha1 + "\\N" + linha2


def corrigir_timestamps_sobrepostos(segmentos: list) -> list:
    """Garante que nenhum segmento sobrepõe o próximo."""
    if not segmentos:
        return segmentos
    result = [dict(s) for s in segmentos]
    for i in range(len(result) - 1):
        end_sec = timestamp_to_seconds(result[i].get("end", "0"))
        next_start_sec = timestamp_to_seconds(result[i + 1].get("start", "0"))
        if end_sec > next_start_sec:
            result[i]["end"] = seconds_to_timestamp(max(0, next_start_sec - 0.1))
    last = result[-1]
    start_sec = timestamp_to_seconds(last.get("start", "0"))
    end_sec = timestamp_to_seconds(last.get("end", "0"))
    if end_sec - start_sec < 2.0:
        last["end"] = seconds_to_timestamp(start_sec + 2.0)
    return result


def gerar_ass(
    overlay: list,
    lyrics: list,
    traducao: Optional[list],
    idioma_versao: str,
    idioma_musica: str,
    estilos: dict = None,
) -> pysubs2.SSAFile:
    """Gera arquivo ASS com até 3 tracks."""
    estilos = estilos or ESTILOS_PADRAO
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = "1080"
    subs.info["PlayResY"] = "1920"

    for nome, config in estilos.items():
        style = pysubs2.SSAStyle()
        style.fontname = config["fontname"]
        style.fontsize = config["fontsize"]
        style.primarycolor = hex_to_ssa_color(config["primarycolor"])
        style.outlinecolor = hex_to_ssa_color(config["outlinecolor"])
        style.outline = config.get("outline", 2)
        style.shadow = config.get("shadow", 0)
        style.alignment = config["alignment"]
        style.marginv = config["marginv"]
        style.bold = config.get("bold", False)
        style.italic = config.get("italic", False)
        subs.styles[nome.capitalize()] = style

    lyrics = corrigir_timestamps_sobrepostos(lyrics)

    duracao_total_ms = 0
    for seg in lyrics:
        end_ms = seg_to_ms(seg.get("end", 0))
        if end_ms > duracao_total_ms:
            duracao_total_ms = end_ms

    # Track 1: Overlay
    overlay_filtrado = [seg for seg in overlay if seg.get("text")]

    def _get_start_ms(s):
        k = "start" if "start" in s else "timestamp"
        return seg_to_ms(s.get(k, 0))

    overlay_starts = [_get_start_ms(s) for s in overlay_filtrado]
    todos_iguais = len(overlay_filtrado) > 1 and len(set(overlay_starts)) <= 1

    for i, seg in enumerate(overlay_filtrado):
        event = pysubs2.SSAEvent()

        if todos_iguais and duracao_total_ms > 0:
            n = len(overlay_filtrado)
            interval = duracao_total_ms // n
            event.start = i * interval
            event.end = (i + 1) * interval
        else:
            start_key = "start" if "start" in seg else "timestamp"
            event.start = seg_to_ms(seg.get(start_key, 0))
            if i + 1 < len(overlay_filtrado):
                next_seg = overlay_filtrado[i + 1]
                next_start_key = "start" if "start" in next_seg else "timestamp"
                next_start_ms = seg_to_ms(next_seg.get(next_start_key, 0))
                event.end = max(event.start + 1, next_start_ms - 1000)
            else:
                event.end = duracao_total_ms if duracao_total_ms > 0 else event.start + 10000

        if event.end - event.start < 2000:
            event.end = event.start + 2000
        event.text = quebrar_texto_overlay(seg["text"])
        event.style = "Overlay"
        subs.events.append(event)

    # Tracks 2 e 3: Lyrics + Tradução
    precisa_traducao = idioma_versao != idioma_musica and traducao
    traducao_por_index = {}
    if precisa_traducao:
        for seg in traducao:
            idx = seg.get("index")
            if idx is not None and seg.get("traducao"):
                traducao_por_index[idx] = seg

    for seg in lyrics:
        text = seg.get("texto_final", seg.get("text", ""))
        if not text:
            continue

        idx = seg.get("index")

        if precisa_traducao and idx not in traducao_por_index:
            continue

        event = pysubs2.SSAEvent()
        event.start = seg_to_ms(seg.get("start", 0))
        event.end = seg_to_ms(seg.get("end", 0))
        event.text = text
        event.style = "Lyrics"
        subs.events.append(event)

        if precisa_traducao and idx in traducao_por_index:
            trad_seg = traducao_por_index[idx]
            event_trad = pysubs2.SSAEvent()
            event_trad.start = event.start
            event_trad.end = event.end
            event_trad.text = trad_seg["traducao"]
            event_trad.style = "Traducao"
            subs.events.append(event_trad)

    return subs
```

---

## 3. pipeline.py — Tasks e Endpoints

### Endpoints (resumo de rotas)

```
POST /api/v1/editor/edicoes/{id}/garantir-video
POST /api/v1/editor/edicoes/{id}/upload-video
POST /api/v1/editor/edicoes/{id}/letra
PUT  /api/v1/editor/edicoes/{id}/letra
POST /api/v1/editor/edicoes/{id}/transcricao
GET  /api/v1/editor/edicoes/{id}/alinhamento
PUT  /api/v1/editor/edicoes/{id}/alinhamento
POST /api/v1/editor/edicoes/{id}/aplicar-corte
POST /api/v1/editor/edicoes/{id}/traducao-lyrics
GET  /api/v1/editor/edicoes/{id}/traducao-lyrics
POST /api/v1/editor/edicoes/{id}/limpar-traducoes
POST /api/v1/editor/edicoes/{id}/reset-traducao
POST /api/v1/editor/edicoes/{id}/renderizar
POST /api/v1/editor/edicoes/{id}/renderizar-preview
POST /api/v1/editor/edicoes/{id}/aprovar-preview
POST /api/v1/editor/edicoes/{id}/exportar
POST /api/v1/editor/edicoes/{id}/pacote
GET  /api/v1/editor/edicoes/{id}/renders
GET  /api/v1/editor/edicoes/{id}/renders/{render_id}/download
GET  /api/v1/editor/edicoes/{id}/audio
GET  /api/v1/editor/edicoes/{id}/video/status
GET  /api/v1/editor/edicoes/{id}/corte
GET  /api/v1/editor/fila/status
POST /api/v1/editor/edicoes/{id}/desbloquear
```

### Função `_traducao_task`

```python
async def _traducao_task(edicao_id: int):
    try:
        from app.database import SessionLocal
        from app.services.translate_service import traduzir_letra_cloud as traduzir_letra

        # PASSO A — Ler estado e inicializar (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                logger.error(f"[{edicao_id}] Edição não encontrada, abortando task")
                return

            alinhamento = db.query(Alinhamento).filter(
                Alinhamento.edicao_id == edicao_id
            ).order_by(Alinhamento.id.desc()).first()

            if not alinhamento or not alinhamento.segmentos_cortado:
                edicao.status = "erro"
                edicao.erro_msg = "Alinhamento cortado não encontrado"
                db.commit()
                return

            # Idempotência: calcular idiomas faltantes
            ja_traduzidos = {
                t.idioma for t in db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == edicao_id
                ).all()
            }
            idioma_origem = edicao.idioma
            faltantes = [
                idioma for idioma in IDIOMAS_ALVO
                if idioma != idioma_origem and idioma not in ja_traduzidos
            ]
            total = len([i for i in IDIOMAS_ALVO if i != idioma_origem])
            concluidos = total - len(faltantes)

            segmentos_cortado = alinhamento.segmentos_cortado
            metadados = {"musica": edicao.musica, "compositor": edicao.compositor}

            edicao.status = "traducao"
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "etapa": "traducao",
                "total": total,
                "concluidos": concluidos,
                "atual": None,
                "erros": [],
            }
            db.commit()

        # PASSO B — Loop de tradução (banco FECHADO durante I/O externo)
        falhas = []
        for idioma in faltantes:
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "traducao",
                        "total": total,
                        "concluidos": concluidos,
                        "atual": idioma,
                        "erros": falhas,
                    }
                    db.commit()

            try:
                logger.info(f"[{edicao_id}] Traduzindo para {idioma}...")
                resultado = await asyncio.wait_for(
                    traduzir_letra(segmentos_cortado, idioma_origem, idioma, metadados),
                    timeout=180,
                )

                with SessionLocal() as db:
                    trad = TraducaoLetra(
                        edicao_id=edicao_id,
                        idioma=idioma,
                        segmentos=resultado,
                    )
                    db.add(trad)
                    db.commit()

                concluidos += 1
                logger.info(f"[{edicao_id}] Tradução {idioma} OK ({concluidos}/{total})")

            except asyncio.TimeoutError:
                falhas.append(f"{idioma}: timeout (180s)")
            except Exception as e:
                falhas.append(f"{idioma}: {e}")

        # PASSO C — Finalização (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.passo_atual = 7
                edicao.status = "montagem"
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "etapa": "traducao",
                    "total": total,
                    "concluidos": concluidos,
                    "atual": None,
                    "erros": falhas,
                }
                if falhas:
                    edicao.erro_msg = f"Traduções com falha ({len(falhas)}): {'; '.join(falhas)}"
                else:
                    edicao.erro_msg = None
                db.commit()

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        else:
            erro_msg = f"Erro inesperado: {str(e)[:500]}"
        logger.error(f"[{edicao_id}] _traducao_task erro inesperado: {e}", exc_info=True)
        try:
            from app.database import SessionLocal
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = erro_msg
                    db.commit()
        except Exception:
            pass
        if isinstance(e, asyncio.CancelledError):
            raise
```

### Função `_render_task`

```python
async def _render_task(edicao_id: int, idiomas_renderizar: list = None, is_preview: bool = False):
    try:
        from app.database import SessionLocal
        from app.services.legendas import gerar_ass
        from pathlib import Path as _Path

        # PASSO A — Ler estado (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if not edicao:
                return

            if not edicao.arquivo_video_cortado:
                edicao.status = "erro"
                edicao.erro_msg = "Vídeo cortado não disponível"
                db.commit()
                return

            idiomas = idiomas_renderizar if idiomas_renderizar else IDIOMAS_ALVO

            # Idempotência: calcular idiomas faltantes
            ja_concluidos = {
                r.idioma for r in db.query(Render).filter(
                    Render.edicao_id == edicao_id,
                    Render.status == "concluido",
                ).all()
            }
            faltantes = [i for i in idiomas if i not in ja_concluidos]
            total = len(idiomas)
            concluidos = total - len(faltantes)

            arquivo_video = edicao.arquivo_video_cortado
            idioma_musica = edicao.idioma
            r2_base_val = _get_r2_base(edicao)

            alinhamento = db.query(Alinhamento).filter(
                Alinhamento.edicao_id == edicao_id
            ).order_by(Alinhamento.id.desc()).first()
            lyrics_segs = alinhamento.segmentos_cortado if alinhamento else []

            dados_idiomas = {}
            for idioma in faltantes:
                overlay = db.query(Overlay).filter(
                    Overlay.edicao_id == edicao_id, Overlay.idioma == idioma
                ).first()
                traducao = db.query(TraducaoLetra).filter(
                    TraducaoLetra.edicao_id == edicao_id,
                    TraducaoLetra.idioma == idioma,
                ).first()
                dados_idiomas[idioma] = {
                    "overlay_segs": overlay.segmentos_reindexado if overlay else [],
                    "traducao_segs": traducao.segmentos if traducao else None,
                }

            status_inicial = "preview" if is_preview else "renderizando"
            edicao.status = status_inicial
            edicao.task_heartbeat = datetime.now(timezone.utc)
            edicao.progresso_detalhe = {
                "etapa": "render",
                "total": total,
                "concluidos": concluidos,
                "atual": None,
                "erros": [],
            }
            db.commit()

        # PASSO B — Loop de render (banco FECHADO durante FFmpeg)
        renders_ok = 0
        falhas = []

        local_video = storage.ensure_local(arquivo_video)

        for idioma in faltantes:
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.task_heartbeat = datetime.now(timezone.utc)
                    edicao.progresso_detalhe = {
                        "etapa": "render",
                        "total": total,
                        "concluidos": concluidos,
                        "atual": idioma,
                        "erros": falhas,
                    }
                    db.commit()

            try:
                d = dados_idiomas[idioma]

                ass_obj = gerar_ass(
                    overlay=d["overlay_segs"] or [],
                    lyrics=lyrics_segs or [],
                    traducao=d["traducao_segs"],
                    idioma_versao=idioma,
                    idioma_musica=idioma_musica,
                )

                output_dir = _Path(STORAGE_PATH) / str(edicao_id) / "renders" / idioma
                output_dir.mkdir(parents=True, exist_ok=True)
                ass_path = str(output_dir / f"legendas_{idioma}.ass")
                ass_obj.save(ass_path)

                output_video = str(output_dir / f"video_{idioma}.mp4")

                ass_escaped = ass_path.replace("\\", "/").replace(":", "\\:")
                cmd = (
                    f'ffmpeg -y -i "{local_video}" '
                    f'-vf "scale=1080:1920:force_original_aspect_ratio=decrease,'
                    f'pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black,'
                    f"ass='{ass_escaped}'\" "
                    f'-c:v libx264 -preset medium -crf 23 '
                    f'-c:a aac -b:a 128k "{output_video}"'
                )
                processo = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                try:
                    _, stderr_out = await asyncio.wait_for(processo.communicate(), timeout=600)
                except asyncio.TimeoutError:
                    processo.kill()
                    await processo.wait()
                    raise

                if processo.returncode != 0:
                    raise Exception(f"FFmpeg falhou: {stderr_out.decode()[-1000:]}")

                tamanho = _Path(output_video).stat().st_size

                # Upload render para R2 e limpar arquivo local
                arquivo_render = output_video
                if r2_base_val:
                    r2_key = f"{r2_base_val}/{idioma}/video_{idioma}.mp4"
                    try:
                        storage.upload_file(output_video, r2_key)
                        arquivo_render = r2_key
                        _Path(output_video).unlink(missing_ok=True)
                    except Exception as upload_err:
                        logger.warning(f"[{edicao_id}] Upload R2 render {idioma} falhou: {upload_err}")

                with SessionLocal() as db:
                    db.add(Render(
                        edicao_id=edicao_id,
                        idioma=idioma,
                        tipo="9:16",
                        arquivo=arquivo_render,
                        tamanho_bytes=tamanho,
                        status="concluido",
                    ))
                    db.commit()

                renders_ok += 1
                concluidos += 1
                _Path(ass_path).unlink(missing_ok=True)

            except asyncio.TimeoutError:
                falhas.append(f"{idioma}: timeout (600s)")
                with SessionLocal() as db:
                    db.add(Render(edicao_id=edicao_id, idioma=idioma, tipo="9:16",
                                  status="erro", erro_msg="timeout (600s)"))
                    db.commit()
            except Exception as e:
                falhas.append(f"{idioma}: {str(e)[:200]}")
                with SessionLocal() as db:
                    db.add(Render(edicao_id=edicao_id, idioma=idioma, tipo="9:16",
                                  status="erro", erro_msg=str(e)[:500]))
                    db.commit()

        # PASSO C — Finalização (sessão curta)
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            if edicao:
                edicao.task_heartbeat = datetime.now(timezone.utc)
                edicao.progresso_detalhe = {
                    "etapa": "render",
                    "total": total,
                    "concluidos": concluidos,
                    "atual": None,
                    "erros": falhas,
                }
                if renders_ok > 0:
                    if is_preview:
                        edicao.status = "preview_pronto"
                        edicao.passo_atual = 8
                    else:
                        edicao.status = "concluido"
                        edicao.passo_atual = 9
                    edicao.erro_msg = (
                        f"Renders com falha ({len(falhas)}): {'; '.join(falhas)}"
                        if falhas else None
                    )
                else:
                    edicao.status = "erro"
                    edicao.erro_msg = f"Nenhum render concluído. Falhas: {'; '.join(falhas)}"
                db.commit()

                if not is_preview and renders_ok > 0:
                    _exportar_renders(edicao, db)

    except BaseException as e:
        if isinstance(e, asyncio.CancelledError):
            erro_msg = "Interrompido por reinício do servidor"
        else:
            erro_msg = f"Erro inesperado: {str(e)[:500]}"
        logger.error(f"[{edicao_id}] _render_task erro inesperado: {e}", exc_info=True)
        try:
            from app.database import SessionLocal
            with SessionLocal() as db:
                edicao = db.get(Edicao, edicao_id)
                if edicao:
                    edicao.status = "erro"
                    edicao.erro_msg = erro_msg
                    db.commit()
        except Exception:
            pass
        if isinstance(e, asyncio.CancelledError):
            raise
```

### Endpoints completos (pipeline.py)

```python
# --- Passo 1: Download ---
@router.post("/edicoes/{edicao_id}/garantir-video")
async def garantir_video(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    if edicao.arquivo_video_completo and storage.exists(edicao.arquivo_video_completo):
        return {"status": "já disponível", "arquivo": edicao.arquivo_video_completo}
    edicao.status = "baixando"
    edicao.passo_atual = 1
    db.commit()
    background_tasks.add_task(_download_video_task, edicao_id, edicao.youtube_url)
    return {"status": "download iniciado"}


@router.post("/edicoes/{edicao_id}/upload-video")
async def upload_video(edicao_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    output_dir = FilePath(STORAGE_PATH) / str(edicao_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    local_path = str(output_dir / "original.mp4")
    with open(local_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
    base = check_conflict(edicao.artista, edicao.musica, edicao.youtube_video_id or "")
    r2_key = f"{base}/video/original.mp4"
    storage.upload_file(local_path, r2_key)
    if edicao.youtube_video_id:
        save_youtube_marker(base, edicao.youtube_video_id)
    edicao.arquivo_video_completo = r2_key
    edicao.r2_base = base
    edicao.status = "letra"
    edicao.passo_atual = 2
    edicao.erro_msg = None
    db.commit()
    return {"status": "ok", "arquivo": r2_key}


# --- Passo 2: Letra ---
@router.post("/edicoes/{edicao_id}/letra")
async def buscar_letra_endpoint(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    if edicao.eh_instrumental:
        edicao.passo_atual = 5
        edicao.status = "corte"
        db.commit()
        return {"status": "instrumental — passo de letra pulado"}
    from app.models import Letra
    letra_existente = db.query(Letra).filter(Letra.musica.ilike(f"%{edicao.musica}%")).first()
    if letra_existente:
        letra_existente.vezes_utilizada += 1
        db.commit()
        return {"fonte": "banco", "letra": letra_existente.letra, "letra_id": letra_existente.id}
    letra_genius = buscar_letra_genius(edicao.musica)
    if letra_genius:
        return {"fonte": "genius", "letra": letra_genius}
    try:
        metadados = {"artista": edicao.artista, "musica": edicao.musica,
                     "opera": edicao.opera, "compositor": edicao.compositor, "idioma": edicao.idioma}
        letra_text = await gemini_buscar_letra(metadados)
        return {"fonte": "gemini", "letra": letra_text}
    except Exception as e:
        return {"fonte": "erro", "erro": str(e), "letra": ""}


@router.put("/edicoes/{edicao_id}/letra")
def aprovar_letra(edicao_id: int, body: LetraAprovar, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    from app.models import Letra
    letra = db.query(Letra).filter(
        Letra.musica == edicao.musica, Letra.idioma == edicao.idioma
    ).first()
    if letra:
        letra.letra = body.letra
        letra.fonte = body.fonte
        letra.validado_por = body.validado_por
    else:
        letra = Letra(musica=edicao.musica, compositor=edicao.compositor,
                      opera=edicao.opera, idioma=edicao.idioma,
                      letra=body.letra, fonte=body.fonte, validado_por=body.validado_por)
        db.add(letra)
    edicao.passo_atual = 3
    edicao.status = "transcricao"
    db.commit()
    db.refresh(letra)
    return {"ok": True, "letra_id": letra.id}


# --- Passo 3: Transcrição ---
@router.post("/edicoes/{edicao_id}/transcricao")
async def iniciar_transcricao(edicao_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    if not edicao.arquivo_video_completo:
        raise HTTPException(409, "Vídeo ainda não foi baixado.")
    if not storage.exists(edicao.arquivo_video_completo):
        if edicao.youtube_url:
            resultado_dl = await download_video(
                edicao.youtube_url, edicao_id, STORAGE_PATH,
                artista=edicao.artista, musica=edicao.musica,
                youtube_video_id=edicao.youtube_video_id or "",
            )
            edicao.arquivo_video_completo = resultado_dl["arquivo_original"]
            edicao.r2_base = resultado_dl.get("r2_base", edicao.r2_base)
            edicao.arquivo_audio_completo = None
            db.commit()
        else:
            raise HTTPException(409, "Vídeo não encontrado e sem URL para re-baixar.")
    if not edicao.arquivo_audio_completo or not storage.exists(edicao.arquivo_audio_completo):
        audio_key = await extrair_audio_completo(
            edicao.arquivo_video_completo, edicao_id, STORAGE_PATH,
            r2_base=_get_r2_base(edicao),
        )
        edicao.arquivo_audio_completo = audio_key
        db.commit()
    edicao.status = "transcricao"
    db.commit()
    background_tasks.add_task(_transcricao_task, edicao_id)
    return {"status": "transcrição iniciada"}


# --- Passo 4: Alinhamento ---
@router.get("/edicoes/{edicao_id}/alinhamento")
def obter_alinhamento(edicao_id: int, db: Session = Depends(get_db)):
    alinhamento = db.query(Alinhamento).filter(
        Alinhamento.edicao_id == edicao_id
    ).order_by(Alinhamento.id.desc()).first()
    if not alinhamento:
        raise HTTPException(404, "Alinhamento não encontrado")
    edicao = db.get(Edicao, edicao_id)
    return {
        "alinhamento": {
            "id": alinhamento.id,
            "segmentos": alinhamento.segmentos_completo,
            "segmentos_cortado": alinhamento.segmentos_cortado,
            "confianca_media": alinhamento.confianca_media,
            "rota": alinhamento.rota,
            "validado": alinhamento.validado,
        },
        "janela": {
            "inicio": edicao.janela_inicio_sec,
            "fim": edicao.janela_fim_sec,
            "duracao": edicao.duracao_corte_sec,
        } if edicao.janela_inicio_sec else None,
    }


@router.put("/edicoes/{edicao_id}/alinhamento")
def validar_alinhamento(edicao_id: int, body: AlinhamentoValidar, db: Session = Depends(get_db)):
    alinhamento = db.query(Alinhamento).filter(
        Alinhamento.edicao_id == edicao_id
    ).order_by(Alinhamento.id.desc()).first()
    if not alinhamento:
        raise HTTPException(404, "Alinhamento não encontrado")
    alinhamento.segmentos_completo = body.segmentos
    alinhamento.validado = True
    alinhamento.validado_por = body.validado_por
    edicao = db.get(Edicao, edicao_id)
    edicao.passo_atual = 5
    edicao.status = "corte"
    db.commit()
    return {"ok": True}


# --- Passo 5: Aplicar corte ---
@router.post("/edicoes/{edicao_id}/aplicar-corte")
async def aplicar_corte(edicao_id: int, body: CorteParams = CorteParams(), db: Session = Depends(get_db)):
    # delega para _aplicar_corte_impl (helper interno)
    ...


# --- Passo 6: Tradução lyrics ---
@router.post("/edicoes/{edicao_id}/traducao-lyrics")
async def traduzir_lyrics(edicao_id: int, db: Session = Depends(get_db)):
    from app.worker import task_queue
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    if edicao.eh_instrumental:
        edicao.passo_atual = 7
        edicao.status = "montagem"
        db.commit()
        return {"status": "instrumental — tradução pulada"}
    result = db.execute(
        update(Edicao)
        .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_TRADUCAO))
        .values(status="traducao")
    )
    db.commit()
    if result.rowcount == 0:
        db.refresh(edicao)
        raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar tradução")
    task_queue.put_nowait((_traducao_task, edicao_id))
    return {"status": "tradução enfileirada"}


@router.get("/edicoes/{edicao_id}/traducao-lyrics")
def obter_traducoes(edicao_id: int, db: Session = Depends(get_db)):
    traducoes = db.query(TraducaoLetra).filter(TraducaoLetra.edicao_id == edicao_id).all()
    return [{"idioma": t.idioma, "segmentos": t.segmentos} for t in traducoes]


@router.post("/edicoes/{edicao_id}/limpar-traducoes")
def limpar_traducoes(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    deletados = db.query(TraducaoLetra).filter(TraducaoLetra.edicao_id == edicao_id).delete()
    edicao.status = "montagem"
    edicao.passo_atual = 7
    edicao.erro_msg = None
    db.commit()
    return {"ok": True, "traducoes_deletadas": deletados, "status": "montagem"}


@router.post("/edicoes/{edicao_id}/reset-traducao")
def reset_traducao(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    if edicao.status not in ("traducao", "erro"):
        raise HTTPException(400, f"Status atual é '{edicao.status}', não precisa de reset")
    traducoes_existentes = db.query(TraducaoLetra).filter(TraducaoLetra.edicao_id == edicao_id).count()
    edicao.status = "montagem"
    edicao.passo_atual = 7
    edicao.erro_msg = None
    db.commit()
    return {"ok": True, "traducoes_existentes": traducoes_existentes,
            "msg": f"Status resetado. {traducoes_existentes} traduções mantidas."}


# --- Passos 7-8: Renderização ---
@router.post("/edicoes/{edicao_id}/renderizar")
async def renderizar(edicao_id: int):
    from app.database import SessionLocal
    from app.worker import task_queue
    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")
        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_RENDER))
            .values(status="renderizando")
        )
        db.commit()
        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite renderizar")
    task_queue.put_nowait((_render_task, edicao_id))
    return {"status": "renderização iniciada"}


@router.post("/edicoes/{edicao_id}/renderizar-preview")
async def renderizar_preview(edicao_id: int):
    from app.database import SessionLocal
    from app.worker import task_queue, _make_preview_wrapper
    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")
        idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
        result = db.execute(
            update(Edicao)
            .where(Edicao.id == edicao_id, Edicao.status.in_(_STATUS_PERMITIDOS_PREVIEW))
            .values(status="preview")
        )
        db.commit()
        if result.rowcount == 0:
            db.refresh(edicao)
            raise HTTPException(409, f"Status atual '{edicao.status}' não permite iniciar preview")
    task_queue.put_nowait((_make_preview_wrapper(edicao_id, idioma_preview), edicao_id))
    return {"status": "preview iniciado", "idioma": idioma_preview}


@router.post("/edicoes/{edicao_id}/aprovar-preview")
async def aprovar_preview(edicao_id: int, body: AprovarPreviewParams):
    from app.database import SessionLocal
    from app.worker import task_queue
    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")
        if body.aprovado:
            result = db.execute(
                update(Edicao)
                .where(Edicao.id == edicao_id, Edicao.status == "preview_pronto")
                .values(status="renderizando", notas_revisao=None)
            )
            db.commit()
            if result.rowcount == 0:
                db.refresh(edicao)
                raise HTTPException(409, f"Status atual '{edicao.status}' não permite aprovar preview")
            task_queue.put_nowait((_render_task, edicao_id))
            return {"status": "renderização dos demais idiomas iniciada"}
        else:
            edicao.status = "revisao"
            edicao.notas_revisao = body.notas_revisao
            db.commit()
            return {"status": "revisão solicitada", "notas": body.notas_revisao}


@router.post("/edicoes/{edicao_id}/exportar")
def exportar_renders(edicao_id: int, db: Session = Depends(get_db)):
    if not EXPORT_PATH:
        raise HTTPException(400, "EXPORT_PATH não configurado.")
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    _exportar_renders(edicao, db)
    pasta = FilePath(EXPORT_PATH) / f"{edicao.artista} - {edicao.musica}"
    arquivos = list(pasta.glob("*.mp4")) if pasta.exists() else []
    return {"pasta": str(pasta), "arquivos_exportados": len(arquivos), "nomes": [f.name for f in arquivos]}


@router.post("/edicoes/{edicao_id}/pacote")
def gerar_pacote(edicao_id: int, body: PacoteParams = PacoteParams(), db: Session = Depends(get_db)):
    """ZIP: renders + textos do Redator (post.txt, subtitles.srt, youtube.txt)."""
    import io, zipfile, tempfile
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    slug = f"{edicao.artista} - {edicao.musica}"
    r2_base = _get_r2_base(edicao)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        renders = db.query(Render).filter(Render.edicao_id == edicao_id, Render.status == "concluido").all()
        for render in renders:
            if render.arquivo:
                local_file = storage.ensure_local(render.arquivo)
                zf.write(local_file, f"{slug}/{render.idioma}/video_{render.idioma}.mp4")
        if r2_base:
            for idioma_dir in IDIOMAS_ALVO:
                prefix = lang_prefix(r2_base, idioma_dir)
                for filename in ["post.txt", "subtitles.srt", "youtube.txt"]:
                    r2_key = f"{prefix}/{filename}"
                    if storage.exists(r2_key):
                        local_file = storage.ensure_local(r2_key)
                        zf.write(local_file, f"{slug}/{idioma_dir}/{filename}")
    zip_bytes = buffer.getvalue()
    r2_key = f"{r2_base}/export/pacote.zip" if r2_base else f"exports/{edicao_id}/pacote.zip"
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp.write(zip_bytes)
        tmp_path = tmp.name
    try:
        storage.upload_file(tmp_path, r2_key)
    finally:
        os.unlink(tmp_path)
    safe_slug = slug.replace('"', "'")
    return Response(content=zip_bytes, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{safe_slug}.zip"'})


@router.get("/edicoes/{edicao_id}/renders")
def listar_renders(edicao_id: int, db: Session = Depends(get_db)):
    renders = db.query(Render).filter(Render.edicao_id == edicao_id).all()
    return [{"id": r.id, "idioma": r.idioma, "tipo": r.tipo, "arquivo": r.arquivo,
             "tamanho_bytes": r.tamanho_bytes, "status": r.status, "erro_msg": r.erro_msg}
            for r in renders]


@router.get("/edicoes/{edicao_id}/renders/{render_id}/download")
def download_render(edicao_id: int, render_id: int, db: Session = Depends(get_db)):
    render = db.query(Render).filter(Render.id == render_id, Render.edicao_id == edicao_id).first()
    if not render:
        raise HTTPException(404, "Render não encontrado")
    if render.status != "concluido" or not render.arquivo:
        raise HTTPException(400, "Render não disponível")
    local_path = storage.ensure_local(render.arquivo)
    edicao = db.get(Edicao, edicao_id)
    filename = f"{edicao.artista} - {edicao.musica} [{render.idioma.upper()}].mp4" if edicao else FilePath(local_path).name
    return FileResponse(path=local_path, media_type="video/mp4", filename=filename)


@router.get("/edicoes/{edicao_id}/audio")
def servir_audio(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao or not edicao.arquivo_audio_completo:
        raise HTTPException(404, "Áudio não disponível")
    local_path = storage.ensure_local(edicao.arquivo_audio_completo)
    return FileResponse(path=local_path, media_type="audio/ogg",
                        filename=f"{edicao.artista} - {edicao.musica}.ogg")


@router.get("/edicoes/{edicao_id}/video/status")
def status_video(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    return {"video_completo": edicao.arquivo_video_completo,
            "video_cortado": edicao.arquivo_video_cortado,
            "audio_completo": edicao.arquivo_audio_completo,
            "duracao_total": edicao.duracao_total_sec,
            "status": edicao.status}


@router.get("/edicoes/{edicao_id}/corte")
def info_corte(edicao_id: int, db: Session = Depends(get_db)):
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404, "Edição não encontrada")
    return {"janela_inicio_sec": edicao.janela_inicio_sec,
            "janela_fim_sec": edicao.janela_fim_sec,
            "duracao_corte_sec": edicao.duracao_corte_sec}


@router.get("/fila/status")
async def fila_status():
    from app.worker import is_worker_busy
    return is_worker_busy()


@router.post("/edicoes/{edicao_id}/desbloquear")
async def desbloquear_edicao(edicao_id: int):
    """Recovery manual: infere status correto e desbloqueia edição travada."""
    from app.database import SessionLocal
    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        if not edicao:
            raise HTTPException(404, "Edição não encontrada")
        is_erro = edicao.status == "erro"
        is_active = edicao.status in _ACTIVE_STATUSES
        hb = edicao.task_heartbeat
        if hb is not None and hb.tzinfo is None:
            hb = hb.replace(tzinfo=timezone.utc)
        is_stale = hb is None or (datetime.now(timezone.utc) - hb) > _STALE_THRESHOLD
        if not is_erro and not (is_active and is_stale):
            raise HTTPException(409, f"Edição não pode ser desbloqueada: status='{edicao.status}'")
        n_traducoes = db.query(TraducaoLetra).filter(TraducaoLetra.edicao_id == edicao_id).count()
        n_renders = db.query(Render).filter(Render.edicao_id == edicao_id, Render.status == "concluido").count()
        novo_status = "preview_pronto" if n_renders > 0 else ("montagem" if n_traducoes > 0 else "alinhamento")
        edicao.status = novo_status
        edicao.erro_msg = None
        edicao.progresso_detalhe = {}
        db.commit()
    return {"novo_status": novo_status, "renders_concluidos": n_renders, "traducoes": n_traducoes}
```

---

## 4. Frontend

### app-portal/lib/api/editor.ts

```typescript
import { request, requestFormData, API_URLS } from "./base"

function BASE() { return API_URLS.editor + "/api/v1/editor" }

export interface Edicao {
  id: number
  youtube_url: string
  youtube_video_id: string
  artista: string
  musica: string
  compositor: string
  opera: string
  idioma: string
  categoria: string
  eh_instrumental: boolean
  status: string
  cut_start: string | null
  cut_end: string | null
  rota_alinhamento: string | null
  confianca_alinhamento: number | null
  duracao_corte_sec: number | null
  janela_inicio_sec: number | null
  janela_fim_sec: number | null
  letra: string | null
  letra_fonte: string | null
  notas_revisao: string | null
  arquivo_video_completo: boolean
  arquivo_audio_completo: boolean
  erro_msg: string | null
  progresso_detalhe: ProgressoDetalhe | null
  overlays_count?: number
  posts_count?: number
  seo_count?: number
  created_at: string
  updated_at: string
}

export interface Segmento {
  start: string
  end: string
  texto_final: string
  texto_gemini?: string
  candidato_letra?: string
  flag: string
  confianca: number
}

export interface Janela {
  inicio: number
  fim: number
  duracao: number
}

export interface AlinhamentoData {
  segmentos: Segmento[]
  rota: string
  confianca_media: number
}

export interface AlinhamentoResponse {
  alinhamento: AlinhamentoData
  janela: Janela
}

export interface Render {
  id: number
  edicao_id: number
  idioma: string
  status: string
  arquivo: string | null
  tamanho_bytes: number | null
  erro_msg: string | null
  created_at: string
}

export interface ProgressoDetalhe {
  etapa: "traducao" | "render"
  total: number
  concluidos: number
  atual: string | null
}

export interface FilaStatus {
  ocupado: boolean
  edicao_id: number | null
  etapa: string | null
  progresso: ProgressoDetalhe | null
}

export interface RedatorProject {
  id: number
  artist: string
  work: string
  composer: string
  album_opera?: string
  category: string
  status: string
  youtube_url: string
  cut_start: string
  cut_end: string
  translations_count: number
}

export const editorApi = {
  listarEdicoes: (params?: Record<string, string>) => {
    const qs = params ? "?" + new URLSearchParams(params).toString() : ""
    return request<Edicao[]>(`${BASE()}/edicoes${qs}`)
  },
  criarEdicao: (data: Partial<Edicao>) =>
    request<Edicao>(`${BASE()}/edicoes`, { method: "POST", body: JSON.stringify(data) }),
  obterEdicao: (id: number) => request<Edicao>(`${BASE()}/edicoes/${id}`),
  atualizarEdicao: (id: number, data: Partial<Edicao>) =>
    request<Edicao>(`${BASE()}/edicoes/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  removerEdicao: (id: number) =>
    request<void>(`${BASE()}/edicoes/${id}`, { method: "DELETE" }),

  garantirVideo: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/garantir-video`, { method: "POST" }),
  uploadVideo: (id: number, file: File) => {
    const form = new FormData()
    form.append("file", file)
    return requestFormData<{ status: string }>(`${BASE()}/edicoes/${id}/upload-video`, form)
  },
  statusVideo: (id: number) =>
    request<{ status: string; progresso?: number }>(`${BASE()}/edicoes/${id}/video/status`),
  buscarLetra: (id: number) =>
    request<{ letra: string; fonte: string }>(`${BASE()}/edicoes/${id}/letra`, { method: "POST" }),
  aprovarLetra: (id: number, data: { letra: string }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/letra`, { method: "PUT", body: JSON.stringify(data) }),
  iniciarTranscricao: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/transcricao`, { method: "POST" }),
  obterAlinhamento: (id: number) =>
    request<AlinhamentoResponse>(`${BASE()}/edicoes/${id}/alinhamento`),
  validarAlinhamento: (id: number, data: { segmentos: Segmento[] }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/alinhamento`, { method: "PUT", body: JSON.stringify(data) }),
  aplicarCorte: (id: number, params?: Record<string, number>) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/aplicar-corte`, { method: "POST", body: JSON.stringify(params || {}) }),
  infoCorte: (id: number) =>
    request<{ cut_start: string; cut_end: string; duracao: number }>(`${BASE()}/edicoes/${id}/corte`),
  traduzirLyrics: (id: number) =>
    request<{ traducoes: Record<string, string> }>(`${BASE()}/edicoes/${id}/traducao-lyrics`, { method: "POST" }),
  obterTraducoes: (id: number) =>
    request<{ traducoes: Record<string, string> }>(`${BASE()}/edicoes/${id}/traducao-lyrics`),
  renderizar: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/renderizar`, { method: "POST" }),
  renderizarPreview: (id: number) =>
    request<{ status: string }>(`${BASE()}/edicoes/${id}/renderizar-preview`, { method: "POST" }),
  aprovarPreview: (id: number, params: { aprovado: boolean; notas_revisao?: string }) =>
    request<Edicao>(`${BASE()}/edicoes/${id}/aprovar-preview`, { method: "POST", body: JSON.stringify(params) }),
  listarRenders: (id: number) =>
    request<Render[]>(`${BASE()}/edicoes/${id}/renders`),
  exportarRenders: (id: number) =>
    request<{ pasta: string; arquivos_exportados: number }>(`${BASE()}/edicoes/${id}/exportar`, { method: "POST" }),

  audioUrl: (id: number) => `${BASE()}/edicoes/${id}/audio`,
  downloadRenderUrl: (edicaoId: number, renderId: number) =>
    `${BASE()}/edicoes/${edicaoId}/renders/${renderId}/download`,
  pacoteUrl: (id: number) => `${BASE()}/edicoes/${id}/pacote`,

  filaStatus: () => request<FilaStatus>(`${BASE()}/fila/status`),

  listarProjetosRedator: () => request<RedatorProject[]>(`${BASE()}/redator/projetos`),
  importarDoRedator: (projectId: number, idioma?: string) =>
    request<Edicao>(`${BASE()}/redator/importar/${projectId}${idioma ? `?idioma=${idioma}` : ""}`, { method: "POST" }),
}
```

---

### app-portal/components/editor/conclusion.tsx

```tsx
"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { editorApi, type Edicao, type Render, type FilaStatus, type ProgressoDetalhe } from "@/lib/api/editor"
import { useAdaptivePolling } from "@/lib/hooks/use-polling"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  ArrowLeft, Download, Play, RefreshCw, CheckCircle, XCircle,
  ExternalLink, Pencil, RotateCcw, Eye, MessageSquare, Package,
} from "lucide-react"

const IDIOMAS = [
  { code: "en", flag: "🇬🇧", label: "Inglês" },
  { code: "pt", flag: "🇧🇷", label: "Português" },
  { code: "es", flag: "🇪🇸", label: "Espanhol" },
  { code: "de", flag: "🇩🇪", label: "Alemão" },
  { code: "fr", flag: "🇫🇷", label: "Francês" },
  { code: "it", flag: "🇮🇹", label: "Italiano" },
  { code: "pl", flag: "🇵🇱", label: "Polonês" },
]

function formatProgresso(p: ProgressoDetalhe | null | undefined): string | null {
  if (!p || typeof p !== "object") return null
  if (!p.etapa || p.total == null || p.concluidos == null) return null
  const label = p.etapa === "traducao" ? "Traduzindo" : "Renderizando"
  const atual = p.atual ? ` (${p.atual})` : ""
  return `${label}: ${p.concluidos}/${p.total} idiomas${atual}`
}

function formatBytes(bytes: number | null | undefined) {
  if (!bytes) return "--"
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatSec(sec: number | null | undefined) {
  if (!sec && sec !== 0) return "--:--"
  const m = Math.floor(sec / 60)
  const s = Math.floor(sec % 60)
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
}

export function EditorConclusion({ edicaoId }: { edicaoId: number }) {
  const router = useRouter()
  const [edicao, setEdicao] = useState<Edicao | null>(null)
  const [renders, setRenders] = useState<Render[]>([])
  const [loading, setLoading] = useState(true)
  const [renderizando, setRenderizando] = useState(false)
  const [traduzindo, setTraduzindo] = useState(false)
  const [baixandoTodos, setBaixandoTodos] = useState(false)
  const [error, setError] = useState("")
  const [editandoCorte, setEditandoCorte] = useState(false)
  const [corteInicio, setCorteInicio] = useState("")
  const [corteFim, setCorteFim] = useState("")
  const [reaplicando, setReaplicando] = useState(false)
  const [notasRevisao, setNotasRevisao] = useState("")
  const [mostrarRevisao, setMostrarRevisao] = useState(false)
  const [aprovando, setAprovando] = useState(false)
  const [filaStatus, setFilaStatus] = useState<FilaStatus | null>(null)

  const load = async () => {
    try {
      const [e, r, fila] = await Promise.all([
        editorApi.obterEdicao(edicaoId),
        editorApi.listarRenders(edicaoId),
        editorApi.filaStatus().catch(() => null),
      ])
      setEdicao(e)
      setRenders(r)
      setFilaStatus(fila)
    } catch (err: unknown) {
      setError("Erro ao carregar dados: " + (err instanceof Error ? err.message : "Erro"))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [edicaoId])

  const isProcessing = !!edicao && ["renderizando", "traducao", "preview"].includes(edicao.status)
  const { isSlowPolling } = useAdaptivePolling(load, isProcessing)

  const handleTraduzir = async () => {
    setTraduzindo(true); setError("")
    try { await editorApi.traduzirLyrics(edicaoId); await load() }
    catch (err: unknown) { setError("Erro na tradução: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setTraduzindo(false) }
  }

  const handleRenderizarPreview = async () => {
    setRenderizando(true); setError("")
    try { await editorApi.renderizarPreview(edicaoId); await load() }
    catch (err: unknown) { setError("Erro na renderização: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setRenderizando(false) }
  }

  const handleAprovarPreview = async () => {
    setAprovando(true); setError("")
    try { await editorApi.aprovarPreview(edicaoId, { aprovado: true }); await load() }
    catch (err: unknown) { setError("Erro ao aprovar: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setAprovando(false) }
  }

  const handleSolicitarRevisao = async () => {
    setAprovando(true); setError("")
    try {
      await editorApi.aprovarPreview(edicaoId, { aprovado: false, notas_revisao: notasRevisao })
      setMostrarRevisao(false); setNotasRevisao(""); await load()
    }
    catch (err: unknown) { setError("Erro ao solicitar revisão: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setAprovando(false) }
  }

  const handleRenderizarTodos = async () => {
    setRenderizando(true); setError("")
    try { await editorApi.renderizar(edicaoId); await load() }
    catch (err: unknown) { setError("Erro na renderização: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setRenderizando(false) }
  }

  const handleBaixarTodos = async () => {
    if (!edicao) return
    setBaixandoTodos(true); setError("")
    try {
      const url = editorApi.pacoteUrl(edicaoId)
      const res = await fetch(url, { method: "POST" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const blob = await res.blob()
      const a = document.createElement("a")
      a.href = URL.createObjectURL(blob)
      a.download = `${edicao.artista} - ${edicao.musica}.zip`
      document.body.appendChild(a); a.click(); document.body.removeChild(a)
      URL.revokeObjectURL(a.href)
    }
    catch (err: unknown) { setError("Erro ao baixar pacote: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setBaixandoTodos(false) }
  }

  const parseMMSS = (val: string) => {
    const parts = val.split(":")
    if (parts.length === 2) return parseFloat(parts[0]) * 60 + parseFloat(parts[1])
    return parseFloat(val) || 0
  }

  const handleReaplicarCorte = async (params?: Record<string, number>) => {
    setReaplicando(true); setError("")
    try { await editorApi.aplicarCorte(edicaoId, params); await load(); setEditandoCorte(false) }
    catch (err: unknown) { setError("Erro ao reaplicar corte: " + (err instanceof Error ? err.message : "Erro")) }
    finally { setReaplicando(false) }
  }

  if (loading || !edicao) return <div className="text-center py-16 text-muted-foreground">Carregando...</div>

  const concluidos = renders.filter(r => r.status === "concluido")
  const erros = renders.filter(r => r.status === "erro")
  const todosOk = concluidos.length === 7 && erros.length === 0
  const isConcluido = edicao.status === "concluido"
  const isPreviewPronto = edicao.status === "preview_pronto"
  const isPreview = edicao.status === "preview"
  const isRevisao = edicao.status === "revisao"
  const sistemaBloqueado = !!(filaStatus?.ocupado && filaStatus.edicao_id !== edicaoId)
  const previewRender = renders.find(r => r.idioma === edicao.idioma && r.status === "concluido")

  return (
    <div className="max-w-4xl mx-auto">
      {/* ... JSX completo — ver arquivo original em
          app-portal/components/editor/conclusion.tsx */}
    </div>
  )
}
```

> JSX completo omitido aqui por brevidade — ver [conclusion.tsx](app-portal/components/editor/conclusion.tsx) para o render completo. A lógica de estado e handlers está acima.

---

## 5. Dockerfile e railway.json

### app-editor/backend/Dockerfile

```dockerfile
FROM python:3.11-slim

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install yt-dlp

WORKDIR /app
COPY app-editor/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app-editor/backend/app/ ./app/
COPY shared/ ./shared/

RUN mkdir -p /storage/videos /storage/renders

EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### app-editor/railway.json (raiz do app-editor)

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### app-editor/backend/railway.json

```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "app-editor/backend/Dockerfile"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

---

## 6. CLAUDE.md

### /CLAUDE.md (raiz do monorepo)

> Conteúdo completo — ver [CLAUDE.md](CLAUDE.md). Pontos-chave:
> - **Autonomia total** — sem confirmações. Deploy obrigatório após cada alteração.
> - **Railway CLI inutilizável** com account tokens UUID — usar sempre GraphQL API.
> - **Next.js Standalone + Rewrites não funciona** — detecção de ambiente via `window.location.hostname` em `base.ts`.
> - **Storage R2** — Railway tem storage efêmero. Vídeos renderizados vão para Cloudflare R2.
> - **Arquitetura multi-projeto** — plataforma reutilizável. Nunca hardcode nome de canal ou prompt.

### /app-editor/CLAUDE.md

```
# APP EDITOR — Best of Opera

## Instruções
Leia o arquivo BRIEFING-CLAUDE-CODE-APP-EDITOR.md nesta pasta.

## Modo de operação
- Autonomia total. NÃO peça confirmação.
- Se encontrar erro, resolva sozinho (até 3 tentativas).
- Documente decisões em DECISIONS.md
- Documente progresso em PROGRESS.md
- Commits frequentes com mensagens em português.

## Stack
- Backend: FastAPI + PostgreSQL + FFmpeg + yt-dlp + Gemini API
- Frontend: React + Vite + Tailwind
- Deploy: Railway (Docker)
- Idioma da interface: Português (PT-BR)
```

---

## Referência Rápida — Status Flow

```
aguardando → baixando → letra → transcricao → alinhamento → corte
→ traducao → montagem → preview → preview_pronto → revisao
→ renderizando → concluido
                  ↑
               (ou "erro" em qualquer etapa)
```

**Status permitidos por operação:**
- `traducao-lyrics`: `traducao | montagem | erro`
- `renderizar`: `montagem | preview_pronto | erro`
- `renderizar-preview`: `montagem | revisao | erro`
- `aprovar-preview`: `preview_pronto`
- `desbloquear`: `erro` OU status ativo com heartbeat stale (>5 min)

**R2 key de render:** `{r2_base}/{idioma}/video_{idioma}.mp4`
