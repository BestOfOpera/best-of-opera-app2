import os, asyncio, shutil, logging
from datetime import datetime
from pathlib import Path
from urllib.parse import quote
import unicodedata as _ud

import httpx
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response

import database as db
from config import (
    YOUTUBE_API_KEY, APP_PASSWORD, PLAYLIST_ID, BRAND_SLUG,
    ANTI_SPAM, PROJECTS_DIR, load_brand_config,
)
from services.youtube import yt_search, yt_playlist, extract_artist_song, parse_iso_dur, classify_category
from services.scoring import calc_score_v7, _process_v7, _rescore_cached, is_posted
from services.download import (
    manager, download_semaphore, sanitize_filename,
    _get_ydl_opts, _prepare_video_logic, _wrapped_prepare_video,
    _download_via_cobalt,
)
from shared.storage_service import storage, check_conflict, save_youtube_marker
from worker import task_queue

router = APIRouter()
logger = logging.getLogger(__name__)


# ─── BACKGROUND TASKS ───

async def populate_initial_cache(brand_slug: str | None = None):
    """Background: populate cache using seed 0 for each V7 category"""
    logger.info("Starting V7 initial cache population...")
    config = load_brand_config(brand_slug)
    categories = config["categories"]
    for cat_key, cat_data in categories.items():
        try:
            seed_query = cat_data["seeds"][0]
            anti_spam = config.get("anti_spam") or ANTI_SPAM
            full_query = f"{seed_query} {anti_spam}"
            raw = await yt_search(full_query, 25, YOUTUBE_API_KEY)
            result = _process_v7(raw, seed_query, False, cat_key, config)
            db.save_cached_videos(result["videos"], cat_key, brand_slug=brand_slug or BRAND_SLUG)
            db.save_last_seed(cat_key, 0)
            logger.info(f"Cached {len(result['videos'])} videos for {cat_key}")
        except Exception as e:
            logger.error(f"Error caching {cat_key}: {e}")
    db.set_config("last_category_refresh", datetime.now().isoformat())
    logger.info("V7 cache population complete!")


def _extract_playlist_id(raw: str) -> str:
    """Extrai playlist ID de URL completa ou retorna raw se já for ID."""
    if not raw:
        return PLAYLIST_ID  # fallback global
    if "list=" in raw:
        from urllib.parse import urlparse, parse_qs
        parsed = parse_qs(urlparse(raw).query)
        return parsed.get("list", [raw])[0]
    return raw


async def refresh_playlist(brand_slug: str | None = None):
    slug = brand_slug or BRAND_SLUG
    config = load_brand_config(brand_slug)
    pl_id = _extract_playlist_id(config.get("playlist_id", ""))
    logger.info(f"Refreshing playlist for {slug} (playlist_id={pl_id})...")
    raw = await yt_playlist(pl_id, api_key=YOUTUBE_API_KEY)
    processed = _process_v7(raw, "Playlist", False, "Playlist", config)
    db.save_playlist_videos(processed["videos"], brand_slug=slug)
    db.set_config(f"last_playlist_refresh:{slug}", datetime.now().isoformat())
    logger.info(f"Playlist refreshed for {slug}: {len(processed['videos'])} videos")


# ─── AUTH ───

@router.post("/api/auth")
async def auth(password: str = Query(...)):
    if password == APP_PASSWORD:
        return {"ok": True}
    raise HTTPException(401, "Senha incorreta")


# ─── SEARCH & CATEGORIES ───

@router.get("/api/search")
async def search(
    q: str = Query(...),
    max_results: int = Query(10, ge=1, le=50),
    hide_posted: bool = Query(True),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Manual search with anti-spam filtering"""
    config = load_brand_config(brand_slug)
    anti_spam = config.get("anti_spam") or ANTI_SPAM
    full_query = f"{q} {anti_spam}"
    raw = await yt_search(full_query, max_results, YOUTUBE_API_KEY)
    return _process_v7(raw, q, hide_posted, config=config)


@router.get("/api/category/{category}")
async def search_category(
    category: str,
    hide_posted: bool = Query(True),
    force_refresh: bool = Query(False),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Category search with V7 seed rotation"""
    config = load_brand_config(brand_slug)
    categories = config["categories"]
    cat_data = categories.get(category)
    if not cat_data:
        raise HTTPException(404, f"Categoria nao encontrada: {category}")

    last_seed = db.get_last_seed(category)
    total_seeds = len(cat_data["seeds"])

    # Serve from cache unless force_refresh
    if not force_refresh:
        cached = db.get_cached_videos(category, hide_posted, brand_slug=brand_slug or BRAND_SLUG)
        if cached:
            cached = _rescore_cached(cached, category, config)
            logger.info(f"Serving {len(cached)} cached videos for {category}")
            return {
                "query": category, "category": category,
                "total_found": len(cached), "posted_hidden": 0,
                "videos": cached, "cached": True,
                "seed_index": last_seed, "total_seeds": total_seeds,
                "seed_query": cat_data["seeds"][last_seed % total_seeds],
            }

    # Rotate to next seed
    next_seed = (last_seed + 1) % total_seeds
    seed_query = cat_data["seeds"][next_seed]
    anti_spam = config.get("anti_spam") or ANTI_SPAM
    full_query = f"{seed_query} {anti_spam}"

    logger.info(f"V7 category '{category}' seed {next_seed}/{total_seeds}: {seed_query[:50]}...")
    raw = await yt_search(full_query, 25, YOUTUBE_API_KEY)
    db.save_last_seed(category, next_seed)

    result = _process_v7(raw, seed_query, hide_posted, category, config)
    db.save_cached_videos(result["videos"], category, brand_slug=brand_slug or BRAND_SLUG)
    result["cached"] = False
    result["seed_index"] = next_seed
    result["total_seeds"] = total_seeds
    result["seed_query"] = seed_query
    return result


@router.get("/api/ranking")
async def ranking(
    hide_posted: bool = Query(True),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Ranking across all V7 categories using first seed each"""
    config = load_brand_config(brand_slug)
    categories = config["categories"]
    all_q = [(key, data["seeds"][0]) for key, data in categories.items()]
    anti_spam = config.get("anti_spam") or ANTI_SPAM
    tasks = [yt_search(f"{q} {anti_spam}", 10, YOUTUBE_API_KEY) for _, q in all_q]
    batches = await asyncio.gather(*tasks, return_exceptions=True)
    seen = set()
    merged = []
    for i, batch in enumerate(batches):
        if isinstance(batch, Exception):
            continue
        cat = all_q[i][0]
        for v in batch:
            if v["video_id"] not in seen:
                seen.add(v["video_id"])
                v["category"] = cat
                merged.append(v)
    return _process_v7(merged, "ranking", hide_posted, config=config)


@router.get("/api/categories")
async def list_categories(
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """List V7 categories with seed info"""
    categories = load_brand_config(brand_slug)["categories"]
    cats = []
    for key, data in categories.items():
        last_seed = db.get_last_seed(key)
        cats.append({
            "key": key, "name": data["name"], "emoji": data["emoji"],
            "desc": data["desc"], "total_seeds": len(data["seeds"]),
            "last_seed": last_seed,
            "seed_query": data["seeds"][last_seed % len(data["seeds"])],
        })
    return {"categories": cats}


# ─── POSTED ───

@router.get("/api/posted")
async def get_posted():
    from services.scoring import posted_registry
    return {"count": len(posted_registry)}


@router.get("/api/posted/check")
async def check_posted(artist: str = "", song: str = ""):
    return {"posted": is_posted(artist, song)}


# ─── MANUAL VIDEO ───

@router.post("/api/manual-video")
async def add_manual_video(
    payload: dict,
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    import re as _re
    youtube_url = payload.get("youtube_url", "")
    if not youtube_url:
        raise HTTPException(400, "URL do YouTube é obrigatória")

    video_id = None
    patterns = [
        r"v=([0-9A-Za-z_-]{11})",
        r"be\/([0-9A-Za-z_-]{11})",
        r"embed\/([0-9A-Za-z_-]{11})",
        r"shorts\/([0-9A-Za-z_-]{11})",
    ]
    for p in patterns:
        m = _re.search(p, youtube_url)
        if m:
            video_id = m.group(1)
            break

    if not video_id:
        raise HTTPException(400, "URL do YouTube inválida")

    if YOUTUBE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "snippet,contentDetails,statistics", "id": video_id, "key": YOUTUBE_API_KEY},
                )
                if r.status_code == 200:
                    items = r.json().get("items", [])
                    if items:
                        v = items[0]
                        sn = v.get("snippet", {})
                        det = v.get("contentDetails", {})
                        stat = v.get("statistics", {})

                        title = sn.get("title", "")
                        artist, song = extract_artist_song(title)
                        pub = sn.get("publishedAt", "")[:10]
                        yr = int(pub[:4]) if pub else 0
                        thumb = sn.get("thumbnails", {}).get("high", {}).get("url", "")
                        dur = parse_iso_dur(det.get("duration", ""))
                        defn = det.get("definition", "sd")
                        views = int(stat.get("viewCount", 0))

                        _cat = classify_category(title)
                        video_data = {
                            "video_id": video_id,
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "title": title, "artist": artist, "song": song or title,
                            "channel": sn.get("channelTitle", ""), "year": yr, "published": pub,
                            "duration": dur, "views": views, "hd": defn in ("hd", "4k"),
                            "thumbnail": thumb, "category": _cat,
                        }

                        try:
                            db.register_quota_usage(search_calls=0, detail_calls=1)
                        except Exception as e:
                            logger.warning(f"Falha ao registrar quota usage: {e}")

                        _cfg = load_brand_config(brand_slug)
                        sc = calc_score_v7(video_data, _cat, _cfg)
                        p = is_posted(video_data.get("artist", ""), video_data.get("song", ""))
                        return {**video_data, "score": sc, "posted": p}
        except Exception as e:
            logger.warning(f"Error fetching from YT API: {e}")

    # Fallback via oEmbed
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://www.youtube.com/oembed",
                params={"url": youtube_url, "format": "json"},
            )
            if r.status_code == 200:
                data = r.json()
                title = data.get("title", "YouTube Video")
                artist, song = extract_artist_song(title)
                _cat = classify_category(title)
                video_data = {
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "title": title, "artist": artist, "song": song or title,
                    "channel": data.get("author_name", "Unknown"), "year": 0, "published": "",
                    "duration": 0, "views": 0, "hd": False,
                    "thumbnail": data.get("thumbnail_url", ""), "category": _cat,
                }
                sc = calc_score_v7(video_data, _cat, load_brand_config(brand_slug))
                p = is_posted(video_data.get("artist", ""), video_data.get("song", ""))
                return {**video_data, "score": sc, "posted": p}
    except Exception as e:
        logger.warning(f"Error fetching from oEmbed: {e}")

    raise HTTPException(404, "Vídeo não encontrado ou URL inválida")


# ─── CACHE ENDPOINTS ───

@router.get("/api/cache/status")
async def cache_status():
    return db.get_cache_status()


@router.post("/api/cache/populate-initial")
async def populate_cache(
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    await task_queue.put(populate_initial_cache(brand_slug))
    return {"status": "started", "message": "V7 cache population started"}


@router.post("/api/cache/refresh-categories")
async def refresh_categories(
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    await task_queue.put(populate_initial_cache(brand_slug))
    return {"status": "started", "message": "V7 category refresh started"}


# ─── PLAYLIST ENDPOINTS ───

@router.get("/api/playlist/videos")
async def get_playlist(
    hide_posted: bool = Query(True),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    slug = brand_slug or BRAND_SLUG
    videos = db.get_playlist_videos(hide_posted, brand_slug=slug)
    if not videos:
        await refresh_playlist(brand_slug)
        videos = db.get_playlist_videos(hide_posted, brand_slug=slug)
    config = load_brand_config(brand_slug)
    pl_id = _extract_playlist_id(config.get("playlist_id", ""))
    return {"total_found": len(videos), "videos": videos, "playlist_id": pl_id, "cached": True}


@router.post("/api/playlist/refresh")
async def refresh_playlist_endpoint(
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    await task_queue.put(refresh_playlist(brand_slug))
    return {"status": "started", "message": "Playlist refresh started"}


@router.post("/api/playlist/download-all")
async def download_all_playlist(
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    slug = brand_slug or BRAND_SLUG
    videos = db.get_playlist_videos(hide_posted=False, brand_slug=slug)
    if not videos:
        return {"status": "error", "message": "Playlist vazia"}

    added = 0
    cfg = load_brand_config(brand_slug)
    for v in videos:
        vid = v["video_id"]
        artist = v["artist"]
        song = v["song"]
        r2_prefix = cfg.get("r2_prefix", "")
        r2_base = check_conflict(artist, song, vid, r2_prefix=r2_prefix)
        full_base = f"{r2_prefix}/{r2_base}" if r2_prefix else r2_base
        r2_key = f"{full_base}/video/original.mp4"

        if storage.exists(r2_key):
            manager.set_task(vid, {"status": "completed", "progress": 100, "message": "Já no R2"})
            continue

        if vid in manager.tasks and manager.tasks[vid]["status"] in ("pending", "processing"):
            continue

        manager.set_task(vid, {"status": "pending", "progress": 0, "message": "Na fila"})
        await manager.queue.put((vid, artist, song, _wrapped_prepare_video))
        added += 1

    return {"status": "started", "added": added, "total": len(videos)}


@router.get("/api/playlist/download-status")
async def get_download_status():
    return manager.get_all_tasks()


# ─── QUOTA ENDPOINTS ───

@router.get("/api/quota/status")
async def quota_status():
    return db.get_quota_status()


@router.post("/api/quota/register")
async def quota_register(search_calls: int = Query(0), detail_calls: int = Query(0)):
    db.register_quota_usage(search_calls, detail_calls)
    return db.get_quota_status()


# ─── DOWNLOAD ENDPOINTS ───

@router.get("/api/download/{video_id}")
async def download_video(
    video_id: str,
    artist: str = Query("Unknown"),
    song: str = Query("Video"),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    safe_artist = sanitize_filename(artist)
    safe_song = sanitize_filename(song)
    project_name = f"{safe_artist} - {safe_song}"
    filename = f"{project_name}.mp4"
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    project_dir = PROJECTS_DIR / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "video").mkdir(exist_ok=True)
    dl_path = str(project_dir / "video" / filename)

    async with download_semaphore:
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
                if files:
                    dl_path_actual = files[0]
                else:
                    raise HTTPException(500, "Download failed: output file not found")
            else:
                dl_path_actual = dl_path

            try:
                db.save_download(video_id, filename, artist, song, youtube_url, brand_slug=brand_slug)
            except Exception as e:
                logger.warning(f"Failed to save download record: {e}")

            r2_ok = False
            r2_key = ""
            r2_base = ""
            try:
                cfg = load_brand_config(brand_slug)
                r2_prefix = cfg.get("r2_prefix", "")
                r2_base = check_conflict(artist, song, video_id, r2_prefix=r2_prefix)
                full_base = f"{r2_prefix}/{r2_base}" if r2_prefix else r2_base
                r2_key = f"{full_base}/video/original.mp4"
                storage.upload_file(dl_path_actual, r2_key)
                save_youtube_marker(r2_base, video_id, r2_prefix=r2_prefix)
                r2_ok = True
                logger.info(f"R2 upload OK: {r2_key}")
            except Exception as e:
                logger.warning(f"R2 upload failed (streaming anyway): {e}")

            cleanup_path = dl_path_actual

            def iter_file():
                try:
                    with open(cleanup_path, 'rb') as f:
                        while chunk := f.read(1024 * 1024):
                            yield chunk
                finally:
                    if r2_ok:
                        try:
                            shutil.rmtree(str(project_dir), ignore_errors=True)
                            logger.info(f"Limpeza local: {project_dir}")
                        except Exception as e:
                            logger.warning(f"Falha ao limpar diretório local {project_dir}: {e}")

            ascii_name = _ud.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
            resp_headers = {
                "Content-Disposition": f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}",
                "X-R2-Upload": "ok" if r2_ok else "failed",
            }
            if r2_ok:
                resp_headers["X-R2-Key"] = r2_key
                resp_headers["X-R2-Base"] = r2_base
            return StreamingResponse(
                iter_file(), media_type="video/mp4",
                headers=resp_headers,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Download error for {video_id}: {e}")
            raise HTTPException(500, f"Erro yt-dlp: {str(e)}")


@router.post("/api/prepare-video/{video_id}")
async def prepare_video(
    video_id: str,
    artist: str = Query("Unknown"),
    song: str = Query("Video"),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Download + upload R2 sem streaming. Retorna JSON com status."""
    safe_artist = sanitize_filename(artist)
    safe_song = sanitize_filename(song)
    project_name = f"{safe_artist} - {safe_song}"
    youtube_url = f"https://www.youtube.com/watch?v={video_id}"

    cfg = load_brand_config(brand_slug)
    r2_prefix = cfg.get("r2_prefix", "")
    r2_base = check_conflict(artist, song, video_id, r2_prefix=r2_prefix)
    full_base = f"{r2_prefix}/{r2_base}" if r2_prefix else r2_base
    r2_key = f"{full_base}/video/original.mp4"
    if storage.exists(r2_key):
        return {
            "status": "ok",
            "r2_key": r2_key,
            "r2_base": r2_base,
            "cached": True,
            "message": "Vídeo já está no R2",
        }

    project_dir = PROJECTS_DIR / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "video").mkdir(exist_ok=True)
    dl_path = str(project_dir / "video" / f"{project_name}.mp4")

    async with download_semaphore:
        dl_path_actual = None
        try:
            # PASSO 1 — yt-dlp (com cookies se configurado)
            try:
                import yt_dlp
                ydl_opts = _get_ydl_opts(dl_path)
                logger.info(f"[prepare-video] ydl_opts format: {ydl_opts.get('format', 'NENHUM')}")

                def _download():
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        n_errors = ydl.download([youtube_url])
                        if n_errors:
                            raise Exception(f"yt-dlp reportou {n_errors} erro(s) sem exceção")

                await asyncio.to_thread(_download)

                if not os.path.exists(dl_path):
                    import glob as _glob
                    files = _glob.glob(str(project_dir / "video" / '*'))
                    dl_path_actual = files[0] if files else None
                else:
                    dl_path_actual = dl_path

                if not dl_path_actual:
                    raise Exception("yt-dlp terminou sem erro mas arquivo não encontrado")
            except Exception as e:
                logger.warning(f"[prepare-video] yt-dlp falhou para {video_id}: {e}")

            # PASSO 2 — cobalt.tools (fallback)
            if not dl_path_actual:
                logger.info(f"[prepare-video] Tentando cobalt.tools para {video_id}...")
                cobalt_ok = await _download_via_cobalt(youtube_url, dl_path)
                if cobalt_ok:
                    dl_path_actual = dl_path

            if not dl_path_actual:
                raise HTTPException(500, "Download falhou: yt-dlp e cobalt.tools falharam. Use upload manual.")

            try:
                db.save_download(video_id, f"{project_name}.mp4", artist, song, youtube_url, brand_slug=brand_slug)
            except Exception as e:
                logger.warning(f"Failed to save download record: {e}")

            storage.upload_file(dl_path_actual, r2_key)
            save_youtube_marker(r2_base, video_id, r2_prefix=r2_prefix)
            file_size = os.path.getsize(dl_path_actual)
            logger.info(f"R2 upload OK: {r2_key} ({file_size / 1024 / 1024:.1f}MB)")

            shutil.rmtree(str(project_dir), ignore_errors=True)
            logger.info(f"Limpeza local: {project_dir}")

            return {
                "status": "ok",
                "r2_key": r2_key,
                "r2_base": r2_base,
                "cached": False,
                "file_size_mb": round(file_size / 1024 / 1024, 1),
                "message": "Vídeo baixado e salvo no R2",
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"prepare-video error for {video_id}: {e}")
            raise HTTPException(500, f"Erro no download (prepare): {str(e)}")


@router.post("/api/upload-video/{video_id}")
async def upload_video_manual(
    video_id: str,
    file: UploadFile = File(...),
    artist: str = Query("Unknown"),
    song: str = Query("Video"),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Upload manual de vídeo para R2."""
    if not file.filename or not file.filename.lower().endswith((".mp4", ".mkv", ".webm", ".mov")):
        raise HTTPException(400, "Formato inválido. Envie MP4, MKV, WEBM ou MOV.")

    cfg = load_brand_config(brand_slug)
    r2_prefix = cfg.get("r2_prefix", "")
    r2_base = check_conflict(artist, song, video_id, r2_prefix=r2_prefix)
    full_base = f"{r2_prefix}/{r2_base}" if r2_prefix else r2_base
    r2_key = f"{full_base}/video/original.mp4"

    tmp_dir = PROJECTS_DIR / sanitize_filename(f"{artist} - {song}") / "video"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = str(tmp_dir / "upload.mp4")

    try:
        with open(tmp_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)

        file_size = os.path.getsize(tmp_path)
        logger.info(f"Upload manual recebido: {file.filename} ({file_size / 1024 / 1024:.1f}MB)")

        storage.upload_file(tmp_path, r2_key)
        save_youtube_marker(r2_base, video_id, r2_prefix=r2_prefix)
        logger.info(f"R2 upload OK (manual): {r2_key}")

        youtube_url = f"https://www.youtube.com/watch?v={video_id}"
        try:
            db.save_download(video_id, f"{artist} - {song}.mp4", artist, song, youtube_url, brand_slug=brand_slug)
        except Exception as e:
            logger.warning(f"Failed to save download record: {e}")

        return {
            "status": "ok",
            "r2_key": r2_key,
            "r2_base": r2_base,
            "file_size_mb": round(file_size / 1024 / 1024, 1),
            "message": "Vídeo enviado e salvo no R2",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload manual error for {video_id}: {e}")
        raise HTTPException(500, f"Falha no upload: {str(e)}")
    finally:
        shutil.rmtree(str(tmp_dir.parent), ignore_errors=True)


# ─── R2 ENDPOINTS ───

@router.get("/api/r2/check")
async def r2_check(
    artist: str = Query(...),
    song: str = Query(...),
    video_id: str = Query(""),
    brand_slug: str | None = Query(None, description="Slug da marca (default: env BRAND_SLUG)"),
):
    """Verifica se o vídeo já está no R2."""
    cfg = load_brand_config(brand_slug)
    r2_prefix = cfg.get("r2_prefix", "")
    r2_base = check_conflict(artist, song, video_id, r2_prefix=r2_prefix)
    full_base = f"{r2_prefix}/{r2_base}" if r2_prefix else r2_base
    r2_key = f"{full_base}/video/original.mp4"
    exists = storage.exists(r2_key)
    return {"exists": exists, "r2_key": r2_key, "r2_base": r2_base}


@router.get("/api/r2/info")
async def r2_info(folder: str = Query(...)):
    """Retorna youtube_url, thumbnail, título e descrição do vídeo para uma pasta R2."""
    marker_key = f"{folder}/video/.youtube_id"
    try:
        video_id = storage.read_text(marker_key).strip()
        if not video_id:
            raise HTTPException(404, "YouTube ID não encontrado")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(404, f"Pasta não encontrada: {e}")

    result = {
        "video_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "thumbnail_url": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        "title": db.get_cached_video_title(video_id) or "",
        "description": "",
        "category": db.get_cached_video_category(video_id) or "",
    }

    if YOUTUBE_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    "https://www.googleapis.com/youtube/v3/videos",
                    params={"part": "snippet", "id": video_id, "key": YOUTUBE_API_KEY},
                )
                data = resp.json()
                items = data.get("items", [])
                if items:
                    snippet = items[0].get("snippet", {})
                    result["title"] = snippet.get("title", "") or result["title"]
                    result["description"] = snippet.get("description", "")
        except Exception as e:
            logger.warning(f"[r2/info] Falha ao enriquecer com YouTube API para {video_id}: {e}")

    return result


# ─── DOWNLOADS ───

@router.get("/api/downloads/brands")
async def list_download_brands():
    """Retorna lista de brand_slugs distintos que têm downloads."""
    return db.get_download_brands()


@router.get("/api/downloads")
async def list_downloads(brand_slug: str = None):
    return {"downloads": db.get_downloads(brand_slug=brand_slug)}


@router.get("/api/downloads/export")
async def export_downloads():
    csv_content = db.export_downloads_csv()
    return Response(
        content=csv_content, media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="downloads.csv"'},
    )
