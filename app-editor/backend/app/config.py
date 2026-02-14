"""Configuração do APP Editor."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/railway")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
STORAGE_PATH = os.getenv("STORAGE_PATH", "/tmp/editor_storage")
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["http://localhost:5174","http://localhost:3000"]')
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
IDIOMAS_ALVO = ["en", "pt", "es", "de", "fr", "it", "pl"]
REDATOR_API_URL = os.getenv("REDATOR_API_URL", "https://app-production-870c.up.railway.app")
EXPORT_PATH = os.getenv("EXPORT_PATH", "")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN", "")
