"""APP Editor — Best of Opera. Ponto de entrada FastAPI."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import STORAGE_PATH, SENTRY_DSN

logger = logging.getLogger(__name__)

# Sentry — inicializar antes do lifespan para capturar erros de startup
if SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=0.1,
        environment="production",
    )
    logger.info("[sentry] Sentry inicializado")

from app.database import engine, Base
from app.routes import edicoes, letras, pipeline, health, importar, dashboard, reports


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
            ("tentativas_requeue", "INTEGER DEFAULT 0"),
            ("sem_lyrics", "BOOLEAN DEFAULT FALSE"),
        ]:
            if col_name not in cols:
                conn.execute(text(f"ALTER TABLE editor_edicoes ADD COLUMN {col_name} {col_type}"))
                logger.info(f"Migration: added column {col_name}")

        # Migration: UNIQUE index em traducao_letra (edicao_id, idioma)
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_traducao_edicao_idioma "
                "ON editor_traducoes_letras (edicao_id, idioma)"
            ))
            logger.info("Migration: created unique index uq_traducao_edicao_idioma")
        except Exception as e:
            logger.warning(f"Migration uq_traducao_edicao_idioma: {e}")

        # Migration: UNIQUE index em render (edicao_id, idioma)
        try:
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_render_edicao_idioma "
                "ON editor_renders (edicao_id, idioma)"
            ))
            logger.info("Migration: created unique index uq_render_edicao_idioma")
        except Exception as e:
            logger.warning(f"Migration uq_render_edicao_idioma: {e}")

        # Migration: UNIQUE index em redator_project_id (anti-duplicata)
        try:
            dups = conn.execute(text(
                "SELECT redator_project_id, COUNT(*) as qtd "
                "FROM editor_edicoes "
                "WHERE redator_project_id IS NOT NULL "
                "GROUP BY redator_project_id "
                "HAVING COUNT(*) > 1"
            )).fetchall()
            if dups:
                logger.warning(
                    f"Migration: {len(dups)} redator_project_id duplicados encontrados. "
                    "UNIQUE index NÃO criado. Limpeza manual necessária."
                )
            else:
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uix_redator_project_id "
                    "ON editor_edicoes (redator_project_id) "
                    "WHERE redator_project_id IS NOT NULL"
                ))
                logger.info("Migration: created unique index uix_redator_project_id")
        except Exception as e:
            logger.warning(f"Migration uix_redator_project_id: {e}")

    # Migration: tabela editor_reports (criada pelo create_all, mas garantir colunas)
    if "editor_reports" in insp.get_table_names():
        report_cols = [c["name"] for c in insp.get_columns("editor_reports")]
        with engine.begin() as conn:
            for col_name, col_type in [
                ("prioridade", "VARCHAR(20) DEFAULT 'media'"),
                ("resolvido_em", "TIMESTAMP"),
                ("updated_at", "TIMESTAMP"),
            ]:
                if col_name not in report_cols:
                    try:
                        conn.execute(text(f"ALTER TABLE editor_reports ADD COLUMN {col_name} {col_type}"))
                        logger.info(f"Migration editor_reports: added column {col_name}")
                    except Exception as e:
                        logger.warning(f"Migration editor_reports/{col_name}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Criar tabelas no startup
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    # Criar diretório de storage
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    # Iniciar worker sequencial e reagendar tasks travadas
    from app.worker import worker_loop, requeue_stale_tasks
    worker_task = asyncio.create_task(worker_loop())
    requeue_stale_tasks()
    yield
    # Shutdown: cancelar worker limpo
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

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health.router)
app.include_router(edicoes.router)
app.include_router(letras.router)
app.include_router(pipeline.router)
app.include_router(importar.router)
app.include_router(dashboard.router)
app.include_router(reports.router)
