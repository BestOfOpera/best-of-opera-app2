import re, csv, unicodedata
from pathlib import Path
from config import DATASET_PATH

# ─── POSTED REGISTRY ───
posted_registry = set()


def normalize_str(s: str) -> str:
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9\s]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def is_posted(artist: str, song: str) -> bool:
    na, ns = normalize_str(artist), normalize_str(song)
    if not na and not ns:
        return False
    stop = {"", "the", "and", "de", "di", "la", "le", "el", "a", "o", "in", "of"}
    for ra, rs in posted_registry:
        if ra == na and rs == ns:
            return True
        aw = set(na.split()) - stop
        rw = set(ra.split()) - stop
        am = (len(aw & rw) >= min(2, len(aw)) or ra in na or na in ra) if aw and rw else False
        sw = set(ns.split()) - stop
        rsw = set(rs.split()) - stop
        sm = (len(sw & rsw) >= min(2, len(sw)) or rs in ns or ns in rs) if sw and rsw else False
        if am and sm:
            return True
    return False


def load_posted():
    global posted_registry
    posted_registry = set()
    if DATASET_PATH.exists():
        with open(DATASET_PATH, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                a = row.get("Nome do Cantor", "").strip()
                s = row.get("Nome da Musica", "").strip()
                if a:
                    posted_registry.add((normalize_str(a), normalize_str(s)))
        print(f"✅ Posted registry: {len(posted_registry)} entries")


# ─── SCORING V7 ───
def calc_score_v7(v: dict, category: str = None, config: dict = None) -> dict:
    """Calcula score V7 para um vídeo. config: perfil da marca (lê do JSON).
    Fase 2: config virá do banco por perfil_id.
    """
    elite_hits = config["elite_hits"] if config else []
    power_names = config["power_names"] if config else []
    voice_keywords = config["voice_keywords"] if config else []
    institutional_channels = config["institutional_channels"] if config else []
    category_specialty = config["category_specialty"] if config else {}
    weights = config.get("scoring_weights", {}) if config else {}

    w_elite = weights.get("elite_hit", 15)
    w_power = weights.get("power_name", 15)
    w_specialty = weights.get("specialty", 25)
    w_voice = weights.get("voice", 15)
    w_institutional = weights.get("institutional", 10)
    w_quality = weights.get("quality", 10)
    w_views = weights.get("views", 10)
    views_threshold = weights.get("views_threshold", 100000)
    max_total = weights.get("max_total", 100)

    reasons = []
    total = 0
    title_low = (v.get("title") or "").lower()
    artist_low = (v.get("artist") or "").lower()
    song_low = (v.get("song") or "").lower()
    channel_low = (v.get("channel") or "").lower()

    # 1. elite_hits
    hit_match = None
    for hit in elite_hits:
        hl = hit.lower()
        if hl in song_low or hl in title_low:
            hit_match = hit
            break
    if hit_match:
        total += w_elite
        reasons.append({"tag": "elite_hit", "label": hit_match, "points": w_elite})

    # 2. power_names
    name_match = None
    for name in power_names:
        nl = name.lower()
        if nl in artist_low or nl in channel_low or nl in title_low:
            name_match = name
            break
    if name_match:
        total += w_power
        reasons.append({"tag": "power_name", "label": name_match, "points": w_power})

    # 3. specialty (dual match OR deep category keywords)
    specialty_match = None
    if hit_match and name_match:
        specialty_match = f"{name_match} + {hit_match}"
    elif category and category in category_specialty:
        for kw in category_specialty[category]:
            if kw in title_low or kw in channel_low:
                specialty_match = kw
                break
    if specialty_match:
        total += w_specialty
        reasons.append({"tag": "specialty", "label": specialty_match, "points": w_specialty})

    # 4. voice
    voice_match = None
    for kw in voice_keywords:
        if kw in title_low:
            voice_match = kw
            break
    if voice_match:
        total += w_voice
        reasons.append({"tag": "voice", "label": voice_match, "points": w_voice})

    # 5. institutional
    inst_match = None
    for ch in institutional_channels:
        if ch in channel_low:
            inst_match = v.get("channel", "")
            break
    if inst_match:
        total += w_institutional
        reasons.append({"tag": "institutional", "label": inst_match, "points": w_institutional})

    # 6. quality (HD)
    if v.get("hd"):
        total += w_quality
        reasons.append({"tag": "quality", "label": "HD", "points": w_quality})

    # 7. views
    views = v.get("views", 0)
    if views > views_threshold:
        total += w_views
        reasons.append({"tag": "views", "label": f"{views:,}", "points": w_views})

    total = min(total, max_total)

    return {
        "total": total,
        "reasons": reasons,
        # Compat fields for DB storage
        "fixed": 0,
        "guia": 0.0,
        "artist_match": name_match,
        "song_match": hit_match,
    }


def _process_v7(videos, query, hide_posted, category=None, config=None):
    scored = []
    for v in videos:
        if category:
            v["category"] = category
        sc = calc_score_v7(v, category, config)
        p = is_posted(v.get("artist", ""), v.get("song", ""))
        scored.append({**v, "score": sc, "posted": p})
    scored.sort(key=lambda x: x["score"]["total"], reverse=True)
    pc = sum(1 for v in scored if v["posted"])
    vis = [v for v in scored if not v["posted"]] if hide_posted else scored
    return {
        "query": query,
        "category": category,
        "total_found": len(scored),
        "posted_hidden": pc if hide_posted else 0,
        "videos": vis,
    }


def _rescore_cached(videos, category=None, config=None):
    """Recompute V7 scores for cached videos (adds reasons)"""
    for v in videos:
        v["score"] = calc_score_v7(v, category, config)
    videos.sort(key=lambda x: x["score"]["total"], reverse=True)
    return videos
