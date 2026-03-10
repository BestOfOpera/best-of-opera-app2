import os, re, asyncio, shutil
from datetime import datetime
from pathlib import Path

import database as db
from config import PROJECTS_DIR
from shared.storage_service import storage, check_conflict, save_youtube_marker

# ─── DOWNLOAD WORKER (ERR-055) ───
class TaskManager:
    def __init__(self):
        self.tasks = {}  # video_id -> status dict
        self.queue = asyncio.Queue()
        self.current_task = None
        self.lock = asyncio.Lock()

    def set_task(self, video_id, data):
        self.tasks[video_id] = {**data, "updated_at": datetime.now().isoformat()}

    def get_task(self, video_id):
        return self.tasks.get(video_id)

    def get_all_tasks(self):
        return self.tasks


manager = TaskManager()
download_semaphore = asyncio.Semaphore(2)


def sanitize_filename(s: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = s.strip('. ')
    return s[:200] if s else 'video'


async def download_worker():
    """Worker loop following app-editor pattern (asyncio.Queue)"""
    print("🚀 Download worker started")
    while True:
        try:
            video_id, artist, song, callback = await manager.queue.get()
            manager.current_task = video_id
            print(f"📥 Worker processing: {video_id} ({artist} - {song})")

            try:
                manager.set_task(video_id, {"status": "processing", "progress": 0, "message": "Iniciando download..."})
                await callback(video_id, artist, song)
                manager.set_task(video_id, {"status": "completed", "progress": 100, "message": "Concluído!"})
                print(f"✅ Worker completed: {video_id}")
            except Exception as e:
                print(f"❌ Worker error for {video_id}: {e}")
                manager.set_task(video_id, {"status": "error", "message": str(e)})
            finally:
                manager.current_task = None
                manager.queue.task_done()
        except Exception as e:
            print(f"⚠️ Worker loop error: {e}")
            await asyncio.sleep(1)


def _get_ydl_opts(dl_path: str):
    """Generate yt-dlp options with cookie support and robustness flags (ERR-055)"""
    import yt_dlp
    opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best',
        'merge_output_format': 'mp4',
        'outtmpl': dl_path,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'match_filter': yt_dlp.utils.match_filter_func('duration < 900'),
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 5,
        'extractor_retries': 3,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        },
    }

    # Cookies support via YOUTUBE_COOKIES env var (ERR-055)
    cookies_content = os.getenv("YOUTUBE_COOKIES")
    if cookies_content:
        cookies_path = "/tmp/yt_cookies.txt"
        try:
            with open(cookies_path, "w") as f:
                f.write(cookies_content)
            opts['cookiefile'] = cookies_path
            print(f"🍪 Using YOUTUBE_COOKIES (saved to {cookies_path})")
        except Exception as e:
            print(f"⚠️ Error saving YOUTUBE_COOKIES: {e}")
    else:
        # Fallback to legacy path
        legacy_cookies = os.getenv("YT_COOKIES_FILE", "/app/cookies.txt")
        if os.path.exists(legacy_cookies):
            opts['cookiefile'] = legacy_cookies
            print(f"🍪 Using legacy cookies from {legacy_cookies}")

    return opts


async def _prepare_video_logic(video_id: str, artist: str, song: str):
    safe_artist = sanitize_filename(artist)
    safe_song = sanitize_filename(song)
    project_name = f"{safe_artist} - {safe_song}"
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    project_dir = PROJECTS_DIR / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "video").mkdir(exist_ok=True)
    dl_path = str(project_dir / "video" / f"{project_name}.mp4")

    manager.set_task(video_id, {"status": "processing", "progress": 30, "message": "Fazendo download..."})

    try:
        import yt_dlp
        ydl_opts = _get_ydl_opts(dl_path)

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])

        await asyncio.to_thread(_download)

        if not os.path.exists(dl_path):
            import glob as _glob
            files = _glob.glob(str(project_dir / "video" / '*'))
            dl_path_actual = files[0] if files else None
            if not dl_path_actual:
                raise Exception("Download falhou: arquivo não encontrado")
        else:
            dl_path_actual = dl_path

        manager.set_task(video_id, {"status": "processing", "progress": 70, "message": "Enviando para o R2..."})

        try:
            db.save_download(video_id, f"{project_name}.mp4", artist, song, youtube_url)
        except Exception:
            pass

        r2_base = check_conflict(artist, song, video_id)
        r2_key = f"{r2_base}/video/original.mp4"
        storage.upload_file(dl_path_actual, r2_key)
        save_youtube_marker(r2_base, video_id)

        shutil.rmtree(str(project_dir), ignore_errors=True)
        manager.set_task(video_id, {"status": "completed", "progress": 100, "message": "Concluído!"})

    except Exception as e:
        if project_dir.exists():
            shutil.rmtree(str(project_dir), ignore_errors=True)
        raise e


async def _wrapped_prepare_video(video_id, artist, song):
    """Internal helper for the worker to call prepare_video logic"""
    manager.set_task(video_id, {"status": "processing", "progress": 10, "message": "Baixando do YouTube..."})
    await _prepare_video_logic(video_id, artist, song)
