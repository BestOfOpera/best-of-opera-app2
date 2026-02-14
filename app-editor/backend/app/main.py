"""APP Editor — Best of Opera. Ponto de entrada FastAPI."""
import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import CORS_ORIGINS, STORAGE_PATH
from app.database import engine, Base
from app.routes import edicoes, letras, pipeline, health, importar


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Criar tabelas no startup
    Base.metadata.create_all(bind=engine)
    # Criar diretório de storage
    Path(STORAGE_PATH).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Best of Opera — Editor",
    description="APP3: Download, corte, lyrics, renderização em 7 idiomas",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
origins = json.loads(CORS_ORIGINS) if isinstance(CORS_ORIGINS, str) else CORS_ORIGINS
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(health.router)
app.include_router(edicoes.router)
app.include_router(letras.router)
app.include_router(pipeline.router)
app.include_router(importar.router)
