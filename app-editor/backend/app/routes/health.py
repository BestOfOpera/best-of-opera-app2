"""Health check e diagnóstico."""
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["health"])

FONTS_CUSTOM_DIR = Path("/usr/local/share/fonts/custom")


@router.get("/health")
def health_check():
    return {"status": "ok", "app": "Best of Opera — Editor", "version": "1.0.0"}


@router.get("/debug/fonts")
def debug_fonts(auth: str = ""):
    """Diagnóstico de fontes disponíveis no container. Requer ?auth=<DEBUG_AUTH>."""
    import os
    expected = os.environ.get("DEBUG_AUTH", "")
    if not expected or auth != expected:
        raise HTTPException(403, "Não autorizado. Defina DEBUG_AUTH e passe ?auth=<valor>.")
    # 1. Arquivos no diretório de fontes custom
    custom_files = []
    if FONTS_CUSTOM_DIR.exists():
        custom_files = sorted(f.name for f in FONTS_CUSTOM_DIR.iterdir())

    # 2. fc-list filtrando Playfair
    fc_list_playfair = ""
    try:
        result = subprocess.run(
            ["fc-list", ":family=Playfair Display"],
            capture_output=True, text=True, timeout=10,
        )
        fc_list_playfair = result.stdout.strip() or "(nenhuma)"
    except Exception as e:
        fc_list_playfair = f"erro: {e}"

    # 3. fc-list completo (todas as fontes do sistema)
    fc_list_all = ""
    try:
        result = subprocess.run(
            ["fc-list", "--format=%{family}\n"],
            capture_output=True, text=True, timeout=10,
        )
        families = sorted(set(result.stdout.strip().split("\n")))
        fc_list_all = families
    except Exception as e:
        fc_list_all = f"erro: {e}"

    # 4. Versão do FFmpeg
    ffmpeg_version = ""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True, timeout=10,
        )
        ffmpeg_version = result.stdout.split("\n")[0]
    except Exception as e:
        ffmpeg_version = f"erro: {e}"

    return {
        "fontsdir": str(FONTS_CUSTOM_DIR),
        "custom_files": custom_files,
        "fc_list_playfair": fc_list_playfair,
        "fc_list_all_families": fc_list_all,
        "ffmpeg_version": ffmpeg_version,
    }
