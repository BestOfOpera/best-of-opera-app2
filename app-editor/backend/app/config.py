"""Configuração do APP Editor."""
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    import warnings
    warnings.warn(
        "DATABASE_URL não definido! Usando localhost fallback. "
        "DEFINA DATABASE_URL em produção!",
        RuntimeWarning,
        stacklevel=1,
    )
    DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/railway"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
import logging as _logging
_cfg_logger = _logging.getLogger("app.config")
if not GEMINI_API_KEY:
    _cfg_logger.warning("GEMINI_API_KEY not configured — Gemini calls will fail")
GOOGLE_TRANSLATE_API_KEY = os.getenv("GOOGLE_TRANSLATE_API_KEY", "")
STORAGE_PATH = os.getenv("STORAGE_PATH", "/tmp/editor_storage")
MAX_VIDEO_SIZE_MB = int(os.getenv("MAX_VIDEO_SIZE_MB", "500"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", '["*"]')
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    import warnings
    warnings.warn(
        "SECRET_KEY não definido! Usando fallback INSEGURO. "
        "DEFINA SECRET_KEY em produção!",
        RuntimeWarning,
        stacklevel=1,
    )
    SECRET_KEY = "dev-secret-key-INSECURE-FALLBACK"
IDIOMAS_ALVO = ["en", "pt", "es", "de", "fr", "it", "pl"]
REDATOR_API_URL = os.getenv("REDATOR_API_URL", "https://app-production-870c.up.railway.app")
EXPORT_PATH = os.getenv("EXPORT_PATH", "")
CURADORIA_API_URL = os.getenv("CURADORIA_API_URL", "https://curadoria-backend-production.up.railway.app")
GENIUS_API_TOKEN = os.getenv("GENIUS_API_TOKEN", "")
SENTRY_DSN = os.getenv("SENTRY_DSN", None)
SENTRY_ORG_URL = os.getenv("SENTRY_ORG_URL", "https://sentry.io")
COBALT_API_URL = os.getenv("COBALT_API_URL", "https://api.cobalt.tools")
COBALT_API_KEY = os.getenv("COBALT_API_KEY", "")
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
