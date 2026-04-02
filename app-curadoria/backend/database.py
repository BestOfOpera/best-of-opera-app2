# ══════════════════════════════════════════════════════════════
# DATABASE MODULE V7 — PostgreSQL Cache, Seeds & Quota
# Uses psycopg 3 (modern driver) with connection pooling
# ══════════════════════════════════════════════════════════════

import os, io, csv, logging
from datetime import datetime, date
from typing import List, Dict, Optional

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "")
if not DATABASE_URL:
    DATABASE_URL = "postgresql://postgres:PWlhCmhfTQOFywLdRKexzGfKKxEfXGgs@postgres.railway.internal:5432/railway"
    logger.warning("DATABASE_URL env var not found — using Railway internal fallback")
else:
    logger.info("DATABASE_URL loaded from env var")

_pool: Optional[ConnectionPool] = None


def init_pool(min_size: int = 2, max_size: int = 10) -> None:
    global _pool
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL not set — add PostgreSQL on Railway")
    _pool = ConnectionPool(DATABASE_URL, min_size=min_size, max_size=max_size, open=True)
    logger.info(f"Database connection pool initialized (min={min_size}, max={max_size})")


def close_pool() -> None:
    global _pool
    if _pool:
        _pool.close()
        logger.info("Database connection pool closed")


def _get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Pool not initialized — call init_pool() first")
    return _pool


def init_db():
    try:
        with _get_pool().connection() as conn:
            c = conn.cursor()

            # Table: cached_videos
            c.execute("""
                CREATE TABLE IF NOT EXISTS cached_videos (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    url TEXT,
                    title TEXT,
                    artist TEXT,
                    song TEXT,
                    channel TEXT,
                    year INTEGER,
                    published TEXT,
                    duration INTEGER,
                    views INTEGER,
                    hd BOOLEAN,
                    thumbnail TEXT,
                    category TEXT,
                    score_total INTEGER,
                    score_fixed INTEGER,
                    score_guia REAL,
                    artist_match TEXT,
                    song_match TEXT,
                    posted BOOLEAN,
                    brand_slug TEXT NOT NULL DEFAULT 'best-of-opera',
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(video_id, category, brand_slug)
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_category ON cached_videos(category)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_score ON cached_videos(score_total DESC)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_video_id ON cached_videos(video_id)")

            # Migration: add brand_slug to existing cached_videos
            try:
                c.execute("ALTER TABLE cached_videos ADD COLUMN IF NOT EXISTS brand_slug TEXT NOT NULL DEFAULT 'best-of-opera'")
            except Exception:
                pass  # Column already exists

            # Migration: update unique constraint to include brand_slug
            try:
                c.execute("ALTER TABLE cached_videos DROP CONSTRAINT IF EXISTS cached_videos_video_id_category_key")
                c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cached_video_category_brand ON cached_videos(video_id, category, brand_slug)")
            except Exception:
                pass  # Already migrated
            c.execute("CREATE INDEX IF NOT EXISTS idx_cached_brand ON cached_videos(brand_slug)")

            # Table: playlist_videos
            c.execute("""
                CREATE TABLE IF NOT EXISTS playlist_videos (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    url TEXT,
                    title TEXT,
                    artist TEXT,
                    song TEXT,
                    channel TEXT,
                    year INTEGER,
                    published TEXT,
                    duration INTEGER,
                    views INTEGER,
                    hd BOOLEAN,
                    thumbnail TEXT,
                    score_total INTEGER,
                    score_fixed INTEGER,
                    score_guia REAL,
                    artist_match TEXT,
                    song_match TEXT,
                    posted BOOLEAN,
                    position INTEGER,
                    brand_slug TEXT NOT NULL DEFAULT 'best-of-opera',
                    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_playlist_score ON playlist_videos(score_total DESC)")

            # Migration: add brand_slug to existing playlist_videos
            try:
                c.execute("ALTER TABLE playlist_videos ADD COLUMN IF NOT EXISTS brand_slug TEXT NOT NULL DEFAULT 'best-of-opera'")
            except Exception:
                pass  # Column already exists

            # Migration: update unique constraint to include brand_slug
            try:
                c.execute("ALTER TABLE playlist_videos DROP CONSTRAINT IF EXISTS playlist_videos_video_id_key")
                c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_playlist_video_brand ON playlist_videos(video_id, brand_slug)")
            except Exception:
                pass  # Already migrated
            c.execute("CREATE INDEX IF NOT EXISTS idx_playlist_brand ON playlist_videos(brand_slug)")

            # Table: system_config
            c.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table: downloads
            c.execute("""
                CREATE TABLE IF NOT EXISTS downloads (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT NOT NULL,
                    filename TEXT,
                    artist TEXT,
                    song TEXT,
                    youtube_url TEXT,
                    brand_slug TEXT DEFAULT NULL,
                    downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Migration: adicionar brand_slug se tabela já existia
            c.execute("ALTER TABLE downloads ADD COLUMN IF NOT EXISTS brand_slug TEXT DEFAULT NULL")

            # Table: category_seeds (V7 seed rotation)
            c.execute("""
                CREATE TABLE IF NOT EXISTS category_seeds (
                    category_id TEXT PRIMARY KEY,
                    last_seed INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Table: quota_usage (V7 daily quota tracking)
            c.execute("""
                CREATE TABLE IF NOT EXISTS quota_usage (
                    usage_date DATE PRIMARY KEY,
                    search_calls INTEGER DEFAULT 0,
                    detail_calls INTEGER DEFAULT 0,
                    total_points INTEGER DEFAULT 0
                )
            """)

            conn.commit()
    except Exception as e:
        logger.error(f"PostgreSQL connection failed: {e}")
        raise
    logger.info("Database initialized (PostgreSQL V7)")


# ─── CACHED VIDEOS ───

def save_cached_videos(videos: List[Dict], category: str, brand_slug: str = "best-of-opera"):
    if not videos:
        logger.warning(f"Skipping cache save for {category}: no videos")
        return
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM cached_videos WHERE category = %s AND brand_slug = %s", (category, brand_slug))
        for v in videos:
            score = v.get("score", {})
            c.execute("""
                INSERT INTO cached_videos
                (video_id, url, title, artist, song, channel, year, published, duration,
                 views, hd, thumbnail, category, score_total, score_fixed, score_guia,
                 artist_match, song_match, posted, brand_slug)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (video_id, category, brand_slug) DO UPDATE SET
                    url=EXCLUDED.url, title=EXCLUDED.title, artist=EXCLUDED.artist,
                    song=EXCLUDED.song, channel=EXCLUDED.channel, year=EXCLUDED.year,
                    published=EXCLUDED.published, duration=EXCLUDED.duration, views=EXCLUDED.views,
                    hd=EXCLUDED.hd, thumbnail=EXCLUDED.thumbnail, score_total=EXCLUDED.score_total,
                    score_fixed=EXCLUDED.score_fixed, score_guia=EXCLUDED.score_guia,
                    artist_match=EXCLUDED.artist_match, song_match=EXCLUDED.song_match,
                    posted=EXCLUDED.posted, fetched_at=CURRENT_TIMESTAMP
            """, (
                v["video_id"], v["url"], v["title"], v["artist"], v["song"],
                v["channel"], v["year"], v["published"], v["duration"],
                v["views"], v["hd"], v["thumbnail"], category,
                score.get("total", 0), score.get("fixed", 0), score.get("guia", 0.0),
                score.get("artist_match"), score.get("song_match"), v.get("posted", False),
                brand_slug
            ))
        conn.commit()
    logger.info(f"Cached {len(videos)} videos for: {category} [{brand_slug}]")


def get_cached_videos(category: str, hide_posted: bool = True, brand_slug: str = "best-of-opera") -> List[Dict]:
    with _get_pool().connection() as conn:
        c = conn.cursor(row_factory=dict_row)
        query = "SELECT * FROM cached_videos WHERE category = %s AND brand_slug = %s"
        params: list = [category, brand_slug]
        if hide_posted:
            query += " AND posted = FALSE"
        query += " ORDER BY score_total DESC"
        c.execute(query, params)
        rows = c.fetchall()
    return [
        {
            "video_id": r["video_id"], "url": r["url"], "title": r["title"],
            "artist": r["artist"], "song": r["song"], "channel": r["channel"],
            "year": r["year"], "published": r["published"], "duration": r["duration"],
            "views": r["views"], "hd": bool(r["hd"]), "thumbnail": r["thumbnail"],
            "category": r["category"],
            "score": {
                "total": r["score_total"], "fixed": r.get("score_fixed", 0),
                "guia": r.get("score_guia", 0),
                "artist_match": r["artist_match"], "song_match": r["song_match"]
            },
            "posted": bool(r["posted"])
        }
        for r in rows
    ]


def get_cached_video_category(video_id: str) -> Optional[str]:
    """Retorna a category de um vídeo em cached_videos, ou None."""
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("SELECT category FROM cached_videos WHERE video_id = %s LIMIT 1", (video_id,))
        row = c.fetchone()
        return row[0] if row else None


# ─── PLAYLIST ───

def save_playlist_videos(videos: List[Dict], brand_slug: str = "best-of-opera"):
    if not videos:
        logger.warning("Skipping playlist save: no videos")
        return
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM playlist_videos WHERE brand_slug = %s", (brand_slug,))
        for idx, v in enumerate(videos):
            score = v.get("score", {})
            c.execute("""
                INSERT INTO playlist_videos
                (video_id, url, title, artist, song, channel, year, published, duration,
                 views, hd, thumbnail, score_total, score_fixed, score_guia,
                 artist_match, song_match, posted, position, brand_slug)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (video_id, brand_slug) DO UPDATE SET
                    url=EXCLUDED.url, title=EXCLUDED.title, artist=EXCLUDED.artist,
                    song=EXCLUDED.song, channel=EXCLUDED.channel, year=EXCLUDED.year,
                    published=EXCLUDED.published, duration=EXCLUDED.duration, views=EXCLUDED.views,
                    hd=EXCLUDED.hd, thumbnail=EXCLUDED.thumbnail, score_total=EXCLUDED.score_total,
                    score_fixed=EXCLUDED.score_fixed, score_guia=EXCLUDED.score_guia,
                    artist_match=EXCLUDED.artist_match, song_match=EXCLUDED.song_match,
                    posted=EXCLUDED.posted, position=EXCLUDED.position, fetched_at=CURRENT_TIMESTAMP
            """, (
                v["video_id"], v["url"], v["title"], v["artist"], v["song"],
                v["channel"], v["year"], v["published"], v["duration"],
                v["views"], v["hd"], v["thumbnail"],
                score.get("total", 0), score.get("fixed", 0), score.get("guia", 0.0),
                score.get("artist_match"), score.get("song_match"), v.get("posted", False), idx,
                brand_slug,
            ))
        conn.commit()
    logger.info(f"Cached {len(videos)} playlist videos for {brand_slug}")


def get_playlist_videos(hide_posted: bool = True, brand_slug: str = "best-of-opera") -> List[Dict]:
    with _get_pool().connection() as conn:
        c = conn.cursor(row_factory=dict_row)
        query = "SELECT * FROM playlist_videos WHERE brand_slug = %s"
        params: list = [brand_slug]
        if hide_posted:
            query += " AND posted = FALSE"
        query += " ORDER BY score_total DESC"
        c.execute(query, params)
        rows = c.fetchall()
    return [
        {
            "video_id": r["video_id"], "url": r["url"], "title": r["title"],
            "artist": r["artist"], "song": r["song"], "channel": r["channel"],
            "year": r["year"], "published": r["published"], "duration": r["duration"],
            "views": r["views"], "hd": bool(r["hd"]), "thumbnail": r["thumbnail"],
            "score": {
                "total": r["score_total"], "fixed": r.get("score_fixed", 0),
                "guia": r.get("score_guia", 0),
                "artist_match": r["artist_match"], "song_match": r["song_match"]
            },
            "posted": bool(r["posted"]), "position": r["position"]
        }
        for r in rows
    ]


# ─── CONFIG ───

def set_config(key: str, value: str):
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO system_config (key, value, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
        """, (key, value))
        conn.commit()


def get_config(key: str) -> Optional[str]:
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("SELECT value FROM system_config WHERE key = %s", (key,))
        row = c.fetchone()
    return row[0] if row else None


# ─── CACHE STATUS ───

def get_cache_status() -> Dict:
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("""
            SELECT category, COUNT(*) as count, MAX(fetched_at) as last_update
            FROM cached_videos GROUP BY category
        """)
        categories = {}
        for row in c.fetchall():
            categories[row[0]] = {"count": row[1], "last_update": row[2].isoformat() if row[2] else None}
        c.execute("SELECT COUNT(*) FROM playlist_videos")
        playlist_count = c.fetchone()[0]
        c.execute("SELECT MAX(fetched_at) FROM playlist_videos")
        prow = c.fetchone()
        playlist_update = prow[0].isoformat() if prow and prow[0] else None
    # pool connection returned before calling get_config (avoids nested borrow)
    return {
        "categories": categories,
        "playlist": {"count": playlist_count, "last_update": playlist_update},
        "last_category_refresh": get_config("last_category_refresh"),
        "last_playlist_refresh": get_config("last_playlist_refresh"),
        "cache_initialized": len(categories) > 0 or playlist_count > 0
    }


def is_cache_empty() -> bool:
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM cached_videos")
        count = c.fetchone()[0]
    return count == 0


# ─── DOWNLOADS ───

def save_download(video_id: str, filename: str, artist: str, song: str, youtube_url: str, brand_slug: str = None):
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("INSERT INTO downloads (video_id, filename, artist, song, youtube_url, brand_slug) VALUES (%s,%s,%s,%s,%s,%s)",
                  (video_id, filename, artist, song, youtube_url, brand_slug))
        conn.commit()


def get_downloads(brand_slug: str = None) -> List[Dict]:
    with _get_pool().connection() as conn:
        c = conn.cursor(row_factory=dict_row)
        if brand_slug:
            c.execute("SELECT * FROM downloads WHERE brand_slug = %s ORDER BY downloaded_at DESC", (brand_slug,))
        else:
            c.execute("SELECT * FROM downloads ORDER BY downloaded_at DESC")
        rows = c.fetchall()
    return [
        {"id": r["id"], "video_id": r["video_id"], "filename": r["filename"],
         "artist": r["artist"], "song": r["song"], "youtube_url": r["youtube_url"],
         "brand_slug": r.get("brand_slug"),
         "downloaded_at": r["downloaded_at"].isoformat() if r["downloaded_at"] else None}
        for r in rows
    ]


def get_download_brands() -> List[str]:
    """Retorna lista de brand_slugs distintos que têm downloads."""
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("SELECT DISTINCT brand_slug FROM downloads WHERE brand_slug IS NOT NULL ORDER BY brand_slug")
        return [row[0] for row in c.fetchall()]


def export_downloads_csv() -> str:
    downloads = get_downloads()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "video_id", "filename", "artist", "song", "youtube_url", "downloaded_at"])
    for d in downloads:
        writer.writerow([d["id"], d["video_id"], d["filename"], d["artist"], d["song"], d["youtube_url"], d["downloaded_at"]])
    return output.getvalue()


# ─── V7: SEED ROTATION ───

def get_last_seed(category_id: str) -> int:
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("SELECT last_seed FROM category_seeds WHERE category_id = %s", (category_id,))
        row = c.fetchone()
    return row[0] if row else 0


def save_last_seed(category_id: str, seed_index: int):
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO category_seeds (category_id, last_seed, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (category_id) DO UPDATE SET
                last_seed = EXCLUDED.last_seed, updated_at = CURRENT_TIMESTAMP
        """, (category_id, seed_index))
        conn.commit()


# ─── V7: QUOTA TRACKING ───

def register_quota_usage(search_calls: int = 0, detail_calls: int = 0):
    today = date.today()
    points = search_calls * 100 + detail_calls * 1
    with _get_pool().connection() as conn:
        c = conn.cursor()
        c.execute("""
            INSERT INTO quota_usage (usage_date, search_calls, detail_calls, total_points)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (usage_date) DO UPDATE SET
                search_calls = quota_usage.search_calls + EXCLUDED.search_calls,
                detail_calls = quota_usage.detail_calls + EXCLUDED.detail_calls,
                total_points = quota_usage.total_points + EXCLUDED.total_points
        """, (today, search_calls, detail_calls, points))
        conn.commit()


def get_quota_status() -> Dict:
    today = date.today()
    with _get_pool().connection() as conn:
        c = conn.cursor(row_factory=dict_row)
        c.execute("SELECT * FROM quota_usage WHERE usage_date = %s", (today,))
        row = c.fetchone()
    if row:
        return {
            "date": str(row["usage_date"]),
            "search_calls": row["search_calls"],
            "detail_calls": row["detail_calls"],
            "total_points": row["total_points"],
            "limit": 10000,
            "remaining": max(0, 10000 - row["total_points"]),
        }
    return {
        "date": str(today),
        "search_calls": 0, "detail_calls": 0, "total_points": 0,
        "limit": 10000, "remaining": 10000,
    }
