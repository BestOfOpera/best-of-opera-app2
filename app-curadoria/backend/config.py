import os, json, shutil, time, logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ─── ENV VARS ───
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
DATASET_PATH = Path(os.getenv("DATASET_PATH", "./dataset_v3_categorizado.csv"))
STATIC_PATH = Path(os.getenv("STATIC_PATH", "./static"))
PLAYLIST_ID = "PLGjiuPqoIDSnphyXIetV6iwm4-3K-fvKk"
APP_PASSWORD = os.getenv("APP_PASSWORD", "opera2026")
PROJECT_ID = os.getenv("PROJECT_ID", "best-of-opera")
def _resolve_editor_url() -> str:
    """Resolve EDITOR_API_URL: env var > Railway auto-detect > localhost."""
    url = os.getenv("EDITOR_API_URL")
    if url:
        return url.rstrip("/")
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return "https://editor-backend-production.up.railway.app"
    return "http://localhost:8000"


EDITOR_API_URL = _resolve_editor_url()
BRAND_SLUG = os.getenv("BRAND_SLUG", "best-of-opera")
COBALT_API_URL = os.getenv("COBALT_API_URL", "https://api.cobalt.tools")

# ─── SHARED DIR ───
PROJECTS_DIR = Path("/tmp/best-of-opera-projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# ─── FFMPEG ───
try:
    import imageio_ffmpeg
    FFMPEG_BIN = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_BIN = shutil.which("ffmpeg") or "ffmpeg"

_ffmpeg_dir = os.path.dirname(FFMPEG_BIN)
_ffprobe_candidate = os.path.join(_ffmpeg_dir, "ffprobe")
FFPROBE_BIN = _ffprobe_candidate if os.path.isfile(_ffprobe_candidate) else (shutil.which("ffprobe") or "ffprobe")

logger.info(f"FFmpeg: {FFMPEG_BIN}")
logger.info(f"FFprobe: {FFPROBE_BIN}")

# ─── ANTI-SPAM ───
ANTI_SPAM = "-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords"


# ─── CACHE de config (TTL 5min) ───
_brand_config_cache: dict = {}   # slug -> {"data": {...}, "ts": float}
_CACHE_TTL = 300  # segundos


def _load_from_json(slug: str) -> dict:
    """Carrega config do JSON local como fallback."""
    data_dir = Path(__file__).parent / "data"
    config_path = data_dir / f"{slug}.json"
    if not config_path.exists():
        config_path = data_dir / "best-of-opera.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def load_brand_config(slug: str = None) -> dict:
    """Carrega config da marca.

    1. Tenta GET {EDITOR_API_URL}/api/internal/perfil/{slug}/curadoria-config
    2. Se falhar (editor offline / erro de rede), usa JSON local como fallback.

    Resultado cacheado por _CACHE_TTL segundos para evitar I/O excessivo.
    """
    target_slug = slug or BRAND_SLUG
    now = time.monotonic()

    cached = _brand_config_cache.get(target_slug)
    if cached and (now - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    # Tentar buscar do editor
    try:
        import urllib.request
        url = f"{EDITOR_API_URL}/api/internal/perfil/{target_slug}/curadoria-config"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
        _brand_config_cache[target_slug] = {"data": data, "ts": now}
        return data
    except Exception as exc:
        logger.warning(f"load_brand_config: editor offline ({exc}), usando JSON local")

    # Fallback JSON local
    data = _load_from_json(target_slug)
    _brand_config_cache[target_slug] = {"data": data, "ts": now}
    return data


# Carregado no startup como default global (compatibilidade com código existente)
BRAND_CONFIG = load_brand_config()
