import os, subprocess
from fastapi import APIRouter

import database as db
from config import YOUTUBE_API_KEY, FFMPEG_BIN, FFPROBE_BIN
from services.scoring import posted_registry

router = APIRouter()


@router.get("/api/health")
async def health():
    quota = db.get_quota_status()
    return {
        "status": "ok", "version": "V7",
        "youtube_api": bool(YOUTUBE_API_KEY),
        "posted_count": len(posted_registry),
        "quota_remaining": quota["remaining"],
    }


@router.get("/api/debug/ffmpeg")
async def debug_ffmpeg():
    import glob as _glob
    info = {
        "FFMPEG_BIN": FFMPEG_BIN,
        "FFPROBE_BIN": FFPROBE_BIN,
        "PATH": os.environ.get("PATH", ""),
    }
    try:
        r = subprocess.run([FFMPEG_BIN, "-version"], capture_output=True, text=True, timeout=5)
        info["ffmpeg_version"] = r.stdout.split("\n")[0] if r.returncode == 0 else f"ERROR: {r.stderr[:200]}"
    except Exception as e:
        info["ffmpeg_error"] = str(e)
    info["nix_ffmpeg"] = _glob.glob("/nix/store/*/bin/ffmpeg")[:5]
    info["usr_ffmpeg"] = _glob.glob("/usr/bin/ffmpeg") + _glob.glob("/usr/local/bin/ffmpeg")
    try:
        r2 = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True, timeout=5)
        info["which_ffmpeg"] = r2.stdout.strip()
    except Exception:
        info["which_ffmpeg"] = "not found"
    return info


@router.get("/api/debug/bgutil")
async def debug_bgutil():
    r = subprocess.run(
        ["python3", "test_bgutil.py"],
        capture_output=True, text=True, timeout=90,
        cwd="/app",
    )
    return {"stdout": r.stdout, "stderr": r.stderr, "rc": r.returncode}
