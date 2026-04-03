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
from backend.routers import projects, generation, approval, translation, export, health

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


_run_migrations()

app = FastAPI(title="Best of Opera — APP2")

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
