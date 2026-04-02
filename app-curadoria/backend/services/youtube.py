import re
import logging
import httpx
import database as db

logger = logging.getLogger(__name__)


def parse_iso_dur(iso: str) -> int:
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    h, mn, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mn * 60 + s


def extract_artist_song(title: str) -> tuple:
    clean = re.sub(
        r"\s*[\(\[](?:Official|Live|HD|4K|Lyrics|Audio|Video|Concert|Performance|Full).*?[\)\]]",
        "", title, flags=re.I
    ).strip()
    # Each entry: (regex, group_order)
    #   "artist_song" → group(1)=artist, group(2)=song
    #   "song_artist" → group(1)=song, group(2)=artist
    #   "3part"       → group(3)=artist, group(1)-group(2)=song
    patterns = [
        (r"^(.+?)\s*[-\u2013\u2014]\s*(.+?)\s*[-\u2013\u2014]\s*([^-\u2013\u2014]+)$", "3part"),
        (r"^(.+?)\s*[-\u2013\u2014]\s*[\"'](.+?)[\"']", "artist_song"),
        (r"^(.+?)\s*[-\u2013\u2014]\s*(.+?)$", "artist_song"),
        (r"^(.+?)\s*[:|]\s*(.+?)$", "artist_song"),
        (r'^[\"\'"]?(.+?)[\"\'"]?\s+by\s+(.+?)$', "song_artist"),
        (r"^(.+?)\s*\(([^)]+)\)\s*$", "song_artist"),
        (r"^(.+?)\s+(?:sings?|performs?)\s+(.+?)$", "artist_song"),
    ]
    for p, order in patterns:
        m = re.match(p, clean, re.I)
        if m:
            groups = m.groups()
            if order == "3part":
                return groups[2].strip(), f"{groups[0].strip()} - {groups[1].strip()}"
            if order == "song_artist":
                return groups[1].strip(), groups[0].strip()
            return groups[0].strip(), groups[1].strip()
    return clean, ""


def classify_category(title: str, description: str = "") -> str:
    """Classifica categoria musical a partir do título e descrição.
    Heurístico editável, sem LLM. Retorna categoria ou 'Vocal' como fallback.
    ORDEM IMPORTA: categorias mais específicas primeiro (Música Sacra antes de Coro,
    porque obras sacras frequentemente envolvem coro)."""
    text = f"{title} {description}".lower()
    # Música Sacra ANTES de Coro (obras sacras frequentemente têm "choir" no título)
    if any(w in text for w in [
        "requiem", "mass", "missa", "sacred", "psalm", "hymn",
        "ave maria", "stabat mater", "magnificat", "te deum",
        "sanctus", "agnus dei", "gloria", "kyrie", "credo",
        "salve regina", "panis angelicus",
    ]):
        return "Música Sacra"
    if any(w in text for w in ["duet", "dueto", "duetto"]):
        return "Dueto"
    if any(w in text for w in ["choir", "chorus", "coro", "choral"]):
        return "Coro"
    if any(w in text for w in ["ensemble", "trio", "quartet", "quintet", "quarteto", "quinteto"]):
        return "Ensemble"
    if any(w in text for w in ["lied", "lieder", "mélodie", "melodie", "art song", "chanson"]):
        return "Lied/Canção"
    if any(w in text for w in ["aria", "ária", "cavatina", "romanza", "cabaletta"]):
        return "Ária"
    if any(w in text for w in ["opera", "ópera", "opéra"]):
        return "Ária"
    if any(w in text for w in ["crossover", "musical", "broadway", "west end"]):
        return "Crossover"
    return "Vocal"


async def yt_search(query: str, max_results: int = 25, api_key: str = "") -> list:
    if not api_key:
        return []
    async with httpx.AsyncClient(timeout=15) as client:
        r1 = await client.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet", "q": query, "type": "video",
                "maxResults": min(max_results, 50),
                "key": api_key, "videoCategoryId": "10", "order": "relevance",
            },
        )
        if r1.status_code != 200:
            logger.warning(f"YT search error {r1.status_code}: {r1.text[:200]}")
            return []
        items = r1.json().get("items", [])
        if not items:
            return []

        vids = [it["id"]["videoId"] for it in items if "videoId" in it.get("id", {})]
        if not vids:
            return []

        r2 = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "contentDetails,statistics", "id": ",".join(vids), "key": api_key},
        )
        dm = {}
        if r2.status_code == 200:
            for v in r2.json().get("items", []):
                dm[v["id"]] = v

        # Register quota usage
        try:
            db.register_quota_usage(search_calls=1, detail_calls=1)
        except Exception as e:
            logger.warning(f"Quota tracking error: {e}")

        results = []
        for it in items:
            vid = it["id"].get("videoId", "")
            if not vid:
                continue
            sn = it.get("snippet", {})
            title = sn.get("title", "")
            pub = sn.get("publishedAt", "")[:10]
            yr = int(pub[:4]) if pub else 0
            thumb = sn.get("thumbnails", {}).get("high", {}).get("url", "")
            det = dm.get(vid, {})
            dur = parse_iso_dur(det.get("contentDetails", {}).get("duration", ""))
            defn = det.get("contentDetails", {}).get("definition", "sd")
            views = int(det.get("statistics", {}).get("viewCount", 0))
            artist, song = extract_artist_song(title)
            results.append({
                "video_id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": title, "artist": artist, "song": song or title,
                "channel": sn.get("channelTitle", ""), "year": yr, "published": pub,
                "duration": dur, "views": views, "hd": defn in ("hd", "4k"),
                "thumbnail": thumb, "category": "",
            })
        return results


async def yt_playlist(playlist_id: str, max_results: int = 50, api_key: str = "") -> list:
    if not api_key:
        return []

    all_items = []
    next_page_token = None

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            params = {
                "part": "snippet",
                "playlistId": playlist_id,
                "maxResults": 50,
                "key": api_key,
            }
            if next_page_token:
                params["pageToken"] = next_page_token

            r1 = await client.get(
                "https://www.googleapis.com/youtube/v3/playlistItems", params=params
            )
            if r1.status_code != 200:
                logger.warning(f"YT playlist error {r1.status_code}: {r1.text[:200]}")
                break

            data = r1.json()
            items = data.get("items", [])
            all_items.extend(items)

            try:
                db.register_quota_usage(search_calls=0, detail_calls=1)
            except Exception:
                pass

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        if not all_items:
            return []

        # Get details for all videos in batches of 50
        vids = [it["snippet"]["resourceId"]["videoId"] for it in all_items]
        dm = {}

        for i in range(0, len(vids), 50):
            batch = vids[i:i + 50]
            r2 = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "contentDetails,statistics", "id": ",".join(batch), "key": api_key},
            )
            if r2.status_code == 200:
                for v in r2.json().get("items", []):
                    dm[v["id"]] = v
            try:
                db.register_quota_usage(search_calls=0, detail_calls=1)
            except Exception:
                pass

        results = []
        for it in all_items:
            vid = it["snippet"]["resourceId"]["videoId"]
            sn = it.get("snippet", {})
            title = sn.get("title", "")
            pub = sn.get("publishedAt", "")[:10]
            yr = int(pub[:4]) if pub else 0
            thumb = sn.get("thumbnails", {}).get("high", {}).get("url", "")
            det = dm.get(vid, {})
            dur = parse_iso_dur(det.get("contentDetails", {}).get("duration", ""))
            defn = det.get("contentDetails", {}).get("definition", "sd")
            views = int(det.get("statistics", {}).get("viewCount", 0))
            artist, song = extract_artist_song(title)
            results.append({
                "video_id": vid,
                "url": f"https://www.youtube.com/watch?v={vid}",
                "title": title, "artist": artist, "song": song or title,
                "channel": sn.get("channelTitle", ""), "year": yr, "published": pub,
                "duration": dur, "views": views, "hd": defn in ("hd", "4k"),
                "thumbnail": thumb, "category": "Playlist",
            })
        return results
