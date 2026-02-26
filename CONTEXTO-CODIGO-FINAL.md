# CONTEXTO DE CÓDIGO — Best of Opera App Editor

> Gerado em 2026-02-25. Knowledge file para projeto Claude.ai.
> Complementa o MEMORIAL-REVISAO-EDITOR.md (decisões, bugs, histórico).

---

## 1. Estrutura do Monorepo

```
best-of-opera-app2/
├── CLAUDE.md                          # Instruções globais
├── PLANO-IMPLEMENTACAO-WORKER.md      # Plano de refatoração (6 blocos)
├── MEMORIAL-REVISAO-EDITOR.md         # Histórico de decisões e bugs
├── app-curadoria/                     # APP1 — curadoria de vídeos
│   └── backend/
├── app-editor/                        # APP3 — edição de vídeo (FOCO)
│   ├── CLAUDE.md
│   ├── BRIEFING-CLAUDE-CODE-APP-EDITOR.md
│   ├── DECISIONS.md
│   ├── PROGRESS.md
│   ├── railway.json
│   └── backend/
│       ├── Dockerfile
│       ├── railway.json
│       ├── requirements.txt
│       └── app/
│           ├── main.py                # Lifespan, worker, migrations
│           ├── worker.py              # Queue, worker_loop, requeue
│           ├── config.py
│           ├── database.py
│           ├── schemas.py             # EdicaoOut, LetraOut, etc.
│           ├── models/                # Edicao, TraducaoLetra, Render, etc.
│           ├── routes/                # pipeline.py, importar.py, edicoes.py
│           └── services/              # legendas.py, translate_service.py, regua.py
├── app-portal/                        # Frontend Next.js compartilhado
│   ├── Dockerfile / railway.json
│   ├── components/editor/             # conclusion.tsx, etc.
│   └── lib/
│       ├── api/editor.ts              # API client + tipos
│       └── hooks/use-polling.ts       # useAdaptivePolling
├── app-redator/                       # APP2 — conteúdo editorial
├── scripts/
└── shared/
    └── storage_service.py             # Abstração R2/local
```

---

## 2. Deploy e Infraestrutura

- **Railway** com containers efêmeros (sem disco persistente)
- **numReplicas: 1**, restartPolicyType: ON_FAILURE
- **Dockerfile:** python:3.11-slim + ffmpeg + yt-dlp
- **Storage:** Cloudflare R2 para vídeos e assets persistentes
- **Banco:** PostgreSQL (Railway managed)
- **Frontend:** Next.js standalone no app-portal

### Dockerfile (app-editor/backend/)

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

---

## 3. Status Flow

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

---

## 4. Backend — Código Completo

### app/main.py

```python
"""APP Editor — Best of Opera. Ponto de entrada FastAPI."""
import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(title="Best of Opera — Editor", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(health.router)
app.include_router(edicoes.router)
app.include_router(letras.router)
app.include_router(pipeline.router)
app.include_router(importar.router)
```

### app/worker.py

```python
"""Worker sequencial com asyncio.Queue para tasks longas."""
import asyncio
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)
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
                logger.error(f"[worker] Task edicao_id={edicao_id} falhou: {e}", exc_info=True)
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
                    logger.error(f"[worker] Não conseguiu salvar erro para edicao_id={edicao_id}")
            finally:
                task_queue.task_done()
        except asyncio.CancelledError:
            logger.info("[worker] CancelledError — encerrando cleanly")
            raise
        except Exception as e:
            logger.error(f"[worker] Erro inesperado no loop principal: {e}", exc_info=True)

def _make_preview_wrapper(eid: int, idioma: str):
    async def _preview_task(_ignored_id: int):
        from app.routes.pipeline import _render_task
        await _render_task(eid, idiomas_renderizar=[idioma], is_preview=True)
    return _preview_task

def requeue_stale_tasks():
    """Recoloca TODAS as edições em status ativo no startup (sem checar heartbeat)."""
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
    from app.database import SessionLocal
    from app.models import Edicao
    with SessionLocal() as db:
        em_proc = db.query(Edicao).filter(
            Edicao.status.in_(["traducao", "renderizando", "preview"])
        ).first()
        if em_proc:
            return {"ocupado": True, "edicao_id": em_proc.id, "etapa": em_proc.status,
                    "progresso": em_proc.progresso_detalhe or {}}
        return {"ocupado": False}
```

### app/models/edicao.py

```python
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, func, JSON
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
    r2_base = Column(String(500), nullable=True)
    redator_project_id = Column(Integer, nullable=True)
    notas_revisao = Column(Text, nullable=True)
    editado_por = Column(String(100))
    tempo_edicao_seg = Column(Integer)
    task_heartbeat = Column(DateTime, nullable=True)
    progresso_detalhe = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### app/schemas.py

```python
from pydantic import BaseModel
from typing import Any, Optional
from datetime import datetime

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

class LetraAprovar(BaseModel):
    letra: str
    fonte: Optional[str] = "manual"
    validado_por: Optional[str] = "operador"

class AlinhamentoValidar(BaseModel):
    segmentos: list
    validado_por: Optional[str] = "operador"
```

### app/routes/importar.py

```python
"""Importação do Redator (APP2) para o Editor (APP3)."""
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
    """Detecta idioma da música. Retorna None se ambíguo (força manual)."""
    for field in ("language", "music_language", "original_language"):
        val = proj.get(field)
        if val and isinstance(val, str) and len(val) <= 10:
            return val.lower()
    all_target = {"en", "pt", "es", "de", "fr", "it", "pl"}
    translation_langs = {t["language"] for t in proj.get("translations", [])}
    missing = all_target - translation_langs - {"pt"}
    if len(missing) == 1:
        return missing.pop()
    return None  # força preenchimento manual via frontend

@router.get("/redator/projetos")
async def listar_projetos_redator():
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            resp = await client.get(f"{REDATOR_API_URL}/api/projects")
            resp.raise_for_status()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Erro ao conectar com o Redator: {e}")
    projects = resp.json()
    return [
        {"id": p["id"], "artist": p.get("artist", ""), "work": p.get("work", ""),
         "composer": p.get("composer", ""), "category": p.get("category", ""),
         "album_opera": p.get("album_opera", ""), "youtube_url": p.get("youtube_url", ""),
         "status": p.get("status", ""), "translations_count": len(p.get("translations", []))}
        for p in projects
    ]

@router.post("/redator/importar/{project_id}")
async def importar_do_redator(project_id: int, idioma: str = None, db: Session = Depends(get_db)):
    """?idioma=XX sobrescreve detecção automática."""
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
        raise HTTPException(400, "Projeto sem URL do YouTube válida")
    music_lang = idioma or _detect_music_lang(proj)
    if music_lang is None:
        raise HTTPException(422, detail={
            "idioma_necessario": True,
            "mensagem": "Não foi possível detectar o idioma. Selecione manualmente.",
        })
    # ... cria Edicao + Overlay + Post + Seo (ver código completo no repo)
```

### app/services/legendas.py

```python
"""Geração de arquivos ASS com 3 tracks de legenda para FFmpeg."""
import pysubs2
from typing import Optional
from app.services.regua import timestamp_to_seconds, seconds_to_timestamp

# Layout: vídeo 16:9 dentro de frame 9:16 (1080x1920)
# Vídeo centralizado com barras pretas em cima e embaixo
ESTILOS_PADRAO = {
    "overlay": {  # Topo — texto editorial
        "fontname": "Georgia", "fontsize": 47,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 3, "shadow": 1,
        "alignment": 8, "marginv": 490,  # topo
        "bold": True, "italic": True,
    },
    "lyrics": {  # Base — transcrição original
        "fontname": "Georgia", "fontsize": 35,
        "primarycolor": "#FFFF64", "outlinecolor": "#000000",
        "outline": 2, "shadow": 0,
        "alignment": 2, "marginv": 580,  # base (bottom-center)
        "bold": True, "italic": True,
    },
    "traducao": {  # Abaixo dos lyrics — tradução
        "fontname": "Georgia", "fontsize": 35,
        "primarycolor": "#FFFFFF", "outlinecolor": "#000000",
        "outline": 2, "shadow": 0,
        "alignment": 2, "marginv": 520,  # acima do lyrics
        "bold": True, "italic": True,
    },
}

OVERLAY_MAX_CHARS = 35

def seg_to_ms(value) -> int:
    if isinstance(value, (int, float)):
        return int(value * 1000)
    if isinstance(value, str):
        return int(timestamp_to_seconds(value) * 1000)
    return 0

def gerar_ass(overlay, lyrics, traducao, idioma_versao, idioma_musica, estilos=None):
    """Gera ASS com até 3 tracks. Lógica chave:
    precisa_traducao = idioma_versao != idioma_musica and traducao
    Preview em "pt" faz precisa_traducao=True para músicas não-PT.
    """
    estilos = estilos or ESTILOS_PADRAO
    subs = pysubs2.SSAFile()
    subs.info["PlayResX"] = "1080"
    subs.info["PlayResY"] = "1920"
    # ... cria estilos, track overlay, track lyrics, track traducao
    # Ver código completo no repo — legendas.py
    return subs
```

---

## 5. pipeline.py — Tasks e Endpoints

### Mapa completo de endpoints

```
POST /edicoes/{id}/garantir-video        # Passo 1: download yt-dlp
POST /edicoes/{id}/upload-video          # Passo 1: upload manual
POST /edicoes/{id}/letra                 # Passo 2: buscar letra (banco/genius/gemini)
PUT  /edicoes/{id}/letra                 # Passo 2: aprovar letra
POST /edicoes/{id}/transcricao           # Passo 3: transcrição Gemini audio
GET  /edicoes/{id}/alinhamento           # Passo 4: ver alinhamento
PUT  /edicoes/{id}/alinhamento           # Passo 4: validar alinhamento
POST /edicoes/{id}/aplicar-corte         # Passo 5: corte FFmpeg
POST /edicoes/{id}/traducao-lyrics       # Passo 6: tradução → worker queue
GET  /edicoes/{id}/traducao-lyrics       # Passo 6: ver traduções
POST /edicoes/{id}/limpar-traducoes      # Passo 6: limpar e refazer
POST /edicoes/{id}/reset-traducao        # Passo 6: desbloquear status
POST /edicoes/{id}/renderizar-preview    # Passo 7: preview PT → worker
POST /edicoes/{id}/aprovar-preview       # Passo 8: aprovar → render todos
POST /edicoes/{id}/renderizar            # Passo 8: render 7 idiomas → worker
POST /edicoes/{id}/exportar              # Passo 9: export local
POST /edicoes/{id}/pacote                # Passo 9: ZIP completo
GET  /edicoes/{id}/renders               # Listar renders
GET  /edicoes/{id}/renders/{rid}/download # Download render individual
GET  /fila/status                        # Estado do worker
POST /edicoes/{id}/desbloquear           # Recovery manual
POST /admin/reset-total                  # TEMPORÁRIO — zerar dados de teste
```

### _traducao_task (sessões curtas)

```python
async def _traducao_task(edicao_id: int):
    try:
        from app.database import SessionLocal                                    # ← DENTRO do try
        from app.services.translate_service import traduzir_letra_cloud as traduzir_letra  # ← DENTRO do try

        # PASSO A (sessão curta): ler edição + alinhamento, calcular idiomas
        # faltantes (idempotência), setar status="traducao" + heartbeat, commit
        with SessionLocal() as db:
            edicao = db.get(Edicao, edicao_id)
            # ... lê alinhamento.segmentos_cortado
            # ... calcula faltantes = IDIOMAS_ALVO - idioma_origem - ja_traduzidos
            # ... seta progresso_detalhe, commit

        # PASSO B (loop, banco FECHADO durante I/O):
        for idioma in faltantes:
            # sessão curta: heartbeat + progresso_detalhe
            # I/O externo: await asyncio.wait_for(traduzir_letra(...), timeout=180)
            # sessão curta: salvar TraducaoLetra

        # PASSO C (sessão curta): status="montagem", passo_atual=7

    except BaseException as e:
        # CancelledError → status="erro" + raise
        # Exception → status="erro"
```

### _render_task (sessões curtas)

```python
async def _render_task(edicao_id, idiomas_renderizar=None, is_preview=False):
    try:
        from app.database import SessionLocal
        from app.services.legendas import gerar_ass

        # PASSO A: ler estado, calcular faltantes, copiar dados locais
        # PASSO B: para cada idioma:
        #   - heartbeat
        #   - gerar ASS (overlay + lyrics + tradução)
        #   - FFmpeg com timeout=600
        #   - upload R2 + limpar local
        #   - salvar Render no banco
        # PASSO C: renders_ok > 0 → "preview_pronto"/"concluido", senão → "erro"

    except BaseException as e:
        # mesmo tratamento de _traducao_task
```

### Endpoint de tradução (check-and-set atômico)

```python
@router.post("/edicoes/{edicao_id}/traducao-lyrics")
async def traduzir_lyrics(edicao_id: int, db: Session = Depends(get_db)):
    from app.worker import task_queue
    edicao = db.get(Edicao, edicao_id)
    if not edicao:
        raise HTTPException(404)
    result = db.execute(
        update(Edicao)
        .where(Edicao.id == edicao_id, Edicao.status.in_({"traducao", "montagem", "erro"}))
        .values(status="traducao")
    )
    db.commit()
    if result.rowcount == 0:
        raise HTTPException(409, f"Status '{edicao.status}' não permite tradução")
    task_queue.put_nowait((_traducao_task, edicao_id))
    return {"status": "tradução enfileirada"}
```

### Endpoint de preview (idioma PT)

```python
@router.post("/edicoes/{edicao_id}/renderizar-preview")
async def renderizar_preview(edicao_id: int):
    from app.worker import task_queue, _make_preview_wrapper
    with SessionLocal() as db:
        edicao = db.get(Edicao, edicao_id)
        idioma_preview = "pt" if edicao.idioma != "pt" else edicao.idioma
        # check-and-set atômico
        task_queue.put_nowait((_make_preview_wrapper(edicao_id, idioma_preview), edicao_id))
```

### Endpoint de desbloquear (recovery manual)

```python
@router.post("/edicoes/{edicao_id}/desbloquear")
async def desbloquear_edicao(edicao_id: int):
    """Infere status correto: renders → preview_pronto, traduções → montagem, senão → alinhamento."""
    # Permite se status=="erro" OU (status ativo + heartbeat stale >5min)
```

---

## 6. Frontend

### lib/api/editor.ts — Tipos principais

```typescript
interface Edicao {
  id: number; status: string; artista: string; musica: string; idioma: string;
  eh_instrumental: boolean; erro_msg: string | null;
  progresso_detalhe: ProgressoDetalhe | null;
  task_heartbeat: string | null;
  // ... demais campos
}

interface ProgressoDetalhe {
  etapa: "traducao" | "render"; total: number; concluidos: number; atual: string | null;
}

interface FilaStatus {
  ocupado: boolean; edicao_id: number | null; etapa: string | null;
  progresso: ProgressoDetalhe | null;
}

interface Render {
  id: number; idioma: string; status: string; arquivo: string | null;
  tamanho_bytes: number | null; erro_msg: string | null;
}
```

### editorApi — Chamadas principais

```typescript
editorApi.traduzirLyrics(id)           // POST traducao-lyrics → worker queue
editorApi.renderizarPreview(id)        // POST renderizar-preview → preview PT
editorApi.aprovarPreview(id, params)   // POST aprovar-preview → render todos
editorApi.renderizar(id)               // POST renderizar → render todos
editorApi.listarRenders(id)            // GET renders
editorApi.downloadRenderUrl(eid, rid)  // GET renders/{rid}/download
editorApi.pacoteUrl(id)                // POST pacote → ZIP
editorApi.filaStatus()                 // GET fila/status
editorApi.importarDoRedator(pid, idioma?) // POST redator/importar/{pid}
```

### components/editor/conclusion.tsx — Lógica

- **useAdaptivePolling**: 3s → 15s após 2min, sem timeout
- **Polling ativo** em status: renderizando, traducao, preview
- **filaStatus**: detecta sistema ocupado por outra edição → banner âmbar
- **formatProgresso**: converte progresso_detalhe em "Traduzindo: 3/7 idiomas (de)"
- **7 idiomas**: en, pt, es, de, fr, it, pl — com bandeiras e status
- **Botões**: Traduzir → Renderizar Preview → Aprovar/Revisar → Renderizar Todos → Baixar

---

## 7. Regras Críticas do Projeto

### Arquitetura
- **Concorrência = 1** — um vídeo por vez, sem Celery/Redis
- **Worker único** — asyncio.Queue + worker_loop no lifespan
- **Sessões curtas** — abrir → ler/escrever → fechar → I/O externo → abrir de novo
- **Imports dentro do try** — imports nas tasks DEVEM estar dentro do try-except
- **BaseException** — tasks capturam BaseException (não só Exception) para CancelledError
- **Heartbeat** — atualizado antes de cada operação pesada
- **Idempotência** — toda task verifica o que já foi feito antes de refazer
- **Check-and-set atômico** — UPDATE WHERE status IN (...) nos endpoints (anti double-click)

### Deploy
- **Railway efêmero** — container pode reiniciar a qualquer momento
- **R2 obrigatório** — tudo persistente vai pro Cloudflare R2
- **Arquivo local deletado** após upload pro R2 (disco limitado)
- **Recovery no startup** — requeue_stale_tasks reenfileira TUDO com status ativo

### CLAUDE.md
- **Autonomia total** — sem confirmações, deploy obrigatório após alteração
- **Railway CLI inutilizável** com account tokens UUID
- **Multi-projeto** — nunca hardcode nome de canal ou prompt
- **Commits** em português, documentar decisões em DECISIONS.md

---

## 8. O que falta implementar (pendências ativas)

1. **Vídeo PT do preview precisa ser salvo no R2** — hoje pode estar só no disco efêmero
2. **Botão "Aprovar e Renderizar Todos"** — ajustar frontend para mostrar progresso por idioma
3. **Download individual por idioma** — botões "Baixar" com link direto pro R2 (não player embarcado)
4. **"Baixar Todos"** — download sequencial ou ZIP quando 7 estiverem prontos
5. **Remover player de vídeo embarcado** — substituir por "Baixar Preview"
6. **Problema 2 (posição das legendas)** — testar se se resolveu com fix do problema 1
7. **Remover endpoint temporário** `/admin/reset-total`
