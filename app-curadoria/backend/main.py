# ══════════════════════════════════════════════════════════════
# BEST OF OPERA — MOTOR V7
# Seed Rotation · V7 Scoring · Anti-Spam · Quota Control
# ══════════════════════════════════════════════════════════════

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

import database as db
from config import YOUTUBE_API_KEY, STATIC_PATH

_SENTRY_DSN = os.getenv("SENTRY_DSN")
if _SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=_SENTRY_DSN,
        traces_sample_rate=0.1,
        environment="production",
        attach_stacktrace=True,
        server_name="curadoria-backend",
    )
from services.scoring import load_posted
from services.download import download_worker
from worker import worker_loop, task_queue
from routes import curadoria, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_pool()
    db.init_db()
    load_posted()
    if YOUTUBE_API_KEY:
        logger.info("YouTube API configured")
    else:
        logger.warning("YouTube API NOT SET")

    asyncio.create_task(download_worker())
    asyncio.create_task(worker_loop())

    if db.is_cache_empty():
        logger.info("Cache empty — auto-populating with V7 seeds...")
        await task_queue.put(curadoria.populate_initial_cache())
    yield
    db.close_pool()


app = FastAPI(title="Best of Opera — Motor V7", version="7.0.0", lifespan=lifespan)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(health.router)
app.include_router(curadoria.router)

# ─── SERVE FRONTEND ───
possible_paths = [STATIC_PATH / "index.html", Path("./index.html"), Path("./static/index.html")]
static_index = next((p for p in possible_paths if p.exists()), None)
if static_index:
    static_dir = static_index.parent

    @app.get("/")
    async def index():
        return FileResponse(static_index)

    app.mount("/", StaticFiles(directory=str(static_dir)), name="static")
