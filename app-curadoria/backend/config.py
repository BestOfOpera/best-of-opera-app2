import os, json, shutil
from pathlib import Path

# ─── ENV VARS ───
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
DATASET_PATH = Path(os.getenv("DATASET_PATH", "./dataset_v3_categorizado.csv"))
STATIC_PATH = Path(os.getenv("STATIC_PATH", "./static"))
PLAYLIST_ID = "PLGjiuPqoIDSnphyXIetV6iwm4-3K-fvKk"
APP_PASSWORD = os.getenv("APP_PASSWORD", "opera2026")
PROJECT_ID = os.getenv("PROJECT_ID", "best-of-opera")

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

print(f"🎬 FFmpeg: {FFMPEG_BIN}")
print(f"🎬 FFprobe: {FFPROBE_BIN}")

# ─── ANTI-SPAM ───
ANTI_SPAM = "-karaoke -piano -tutorial -lesson -reaction -review -lyrics -chords"


def load_brand_config(project_id: str = None) -> dict:
    """Carrega config da marca do JSON. Fase 2: ler do banco por perfil_id."""
    pid = project_id or PROJECT_ID
    data_dir = Path(__file__).parent / "data"
    config_path = data_dir / f"{pid}.json"
    if not config_path.exists():
        config_path = data_dir / "best-of-opera.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


# Carregado no startup — Fase 2: receber por perfil_id da request
BRAND_CONFIG = load_brand_config()
