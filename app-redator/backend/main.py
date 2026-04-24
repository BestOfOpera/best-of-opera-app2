import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.database import engine, Base

_SENTRY_DSN = os.getenv("SENTRY_DSN")
if _SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        traces_sample_rate=0.1,
        environment="production",
        attach_stacktrace=True,
        server_name="redator-backend",
    )
from backend.routers import projects, generation, approval, translation, export, health, calendar

Base.metadata.create_all(bind=engine)


def _run_migrations():
    from sqlalchemy import text, inspect as sa_inspect
    insp = sa_inspect(engine)
    if "projects" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("projects")]
    with engine.begin() as conn:
        if "hook_category" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN hook_category VARCHAR(50) DEFAULT ''"))
        if "perfil_id" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN perfil_id INTEGER"))
        if "brand_slug" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN brand_slug VARCHAR(50) DEFAULT 'best-of-opera'"))
        # SPEC-009: remover default BO — novos projetos devem sempre ter slug explícito
        conn.execute(text("ALTER TABLE projects ALTER COLUMN brand_slug DROP DEFAULT"))
        # v13 — RC foundation fields
        if "research_data" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN research_data JSON"))
        if "hooks_json" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN hooks_json JSON"))
        if "selected_hook" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN selected_hook TEXT"))
        if "automation_json" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN automation_json JSON"))
        if "automation_approved" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN automation_approved BOOLEAN DEFAULT FALSE"))
        # v14 — RC metadata fields
        if "instrument_formation" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN instrument_formation VARCHAR(255)"))
        if "orchestra" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN orchestra VARCHAR(255)"))
        if "conductor" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN conductor VARCHAR(255)"))
        # v15 — Calendar: scheduled_date
        if "scheduled_date" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN scheduled_date DATE"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_scheduled_date ON projects (scheduled_date)"))
        # v16 — R2 folder reference
        if "r2_folder" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN r2_folder VARCHAR(500)"))
        # v17 — RC overlay audit metadata (refactor overlay-sentinel-restructure)
        if "overlay_audit" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN overlay_audit JSON"))
        # v18 — BO Pipeline V2 columns (feature flag + Gate 0 classification + timestamps de aprovação)
        if "pipeline_version" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN pipeline_version VARCHAR(10) NOT NULL DEFAULT 'v1'"))
            conn.execute(text("UPDATE projects SET pipeline_version = 'v1' WHERE pipeline_version IS NULL"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_pipeline_version ON projects (pipeline_version)"))
        if "hook_escolhido_json" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN hook_escolhido_json JSON"))
        if "dim_1_detectada" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN dim_1_detectada VARCHAR(50)"))
        if "dim_2_detectada" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN dim_2_detectada VARCHAR(50)"))
        if "dim_2_subtipo_detectada" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN dim_2_subtipo_detectada VARCHAR(50)"))
        if "dim_3_pai_detectada" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN dim_3_pai_detectada VARCHAR(50)"))
        if "dim_3_sub_detectada" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN dim_3_sub_detectada VARCHAR(50)"))
        if "video_duration_seconds" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN video_duration_seconds REAL"))
        if "operator_notes" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN operator_notes TEXT"))
        if "research_approved_at" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN research_approved_at TIMESTAMP"))
        if "overlay_approved_at" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN overlay_approved_at TIMESTAMP"))
        if "post_approved_at" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN post_approved_at TIMESTAMP"))
        if "youtube_tags_list" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN youtube_tags_list JSON"))
        if "youtube_approved_at" not in cols:
            conn.execute(text("ALTER TABLE projects ADD COLUMN youtube_approved_at TIMESTAMP"))

        # v18 (cont.) — translations: verificacoes + detecção de stale após edição em PT
        if "translations" in insp.get_table_names():
            trans_cols = [c["name"] for c in insp.get_columns("translations")]
            if "verificacoes_json" not in trans_cols:
                conn.execute(text("ALTER TABLE translations ADD COLUMN verificacoes_json JSON"))
            if "is_stale" not in trans_cols:
                conn.execute(text("ALTER TABLE translations ADD COLUMN is_stale BOOLEAN DEFAULT FALSE NOT NULL"))
            if "stale_reason" not in trans_cols:
                conn.execute(text("ALTER TABLE translations ADD COLUMN stale_reason VARCHAR(200)"))
            # Índice parcial em Postgres; fallback para índice full em SQLite (não suporta WHERE em CREATE INDEX)
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_translations_stale ON translations(is_stale) WHERE is_stale = TRUE"))
            except Exception:
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_translations_stale ON translations(is_stale)"))


_run_migrations()


def _recover_stuck_projects():
    """Marca projetos em status transitório como awaiting_approval no startup."""
    from backend.database import SessionLocal
    from backend.models import Project

    db = SessionLocal()
    try:
        stuck_statuses = ["translating", "generating"]
        stuck = db.query(Project).filter(
            Project.status.in_(stuck_statuses)
        ).all()

        if stuck:
            for p in stuck:
                old_status = p.status
                p.status = "awaiting_approval"
                print(
                    f"[RECOVERY] Projeto {p.id} ({p.artist} - {p.work}): "
                    f"{old_status} → awaiting_approval",
                    flush=True,
                )
            db.commit()
            print(f"[RECOVERY] {len(stuck)} projetos recuperados no startup", flush=True)
    except Exception as e:
        print(f"[RECOVERY] Erro na recuperação: {e}", flush=True)
        db.rollback()
    finally:
        db.close()


_recover_stuck_projects()

_raw_origins = os.environ.get("ALLOWED_ORIGINS", "")
if _raw_origins:
    _cors_origins = [o.strip() for o in _raw_origins.split(",")]
else:
    _cors_origins = ["*"]

app = FastAPI(title="Best of Opera — APP2")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(calendar.router)     # /api/calendar — prefix próprio, sem conflito
app.include_router(export.router)       # ANTES de projects — rotas literais (/export-config) primeiro
app.include_router(projects.router)     # catch-all /{project_id} depois
app.include_router(generation.router)
app.include_router(approval.router)
app.include_router(translation.router)
app.include_router(health.router)

# Serve frontend in production
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = FRONTEND_DIST / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST / "index.html")
