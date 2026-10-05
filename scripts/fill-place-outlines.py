#!/usr/bin/env python3
"""Fill city-pack place outlines from OpenStreetMap.

Every place already has a hand-picked lat/lng, a radius, and often the local
name in `address`. That is enough to ask Overpass for named areas around the
point and pick the one that is really the place, without trusting a geocoder
to parse "name, city, state" — that query shape returns nothing whenever the
object sits in a neighbouring commune or OSM knows it by its local name.

Two Overpass calls per place: tags near the point, then geometry for the one
element we picked. Resumable, Ctrl-C safe, one run at a time (lock file).

Object plots (fountain, artwork, statue, water tower) get a 30 m pad because
their outline is the object, not the ground people stand on. Parks, museums,
stadiums, and zoos already cover walkable ground and get no pad.

`--local-name` retries places the English name missed, using the local name
stored in `address`. The saved point has to sit inside that plot.
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import subprocess
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "data" / "city-places"
PROGRESS_PATH = Path(__file__).resolve().parent / ".outline-run-progress.json"
LOCK_PATH = Path(__file__).resolve().parent / ".outline-run.lock"

USER_AGENT = "LifeMap-city-places-outline/2.0 (local pack authoring)"
# Shared public endpoint. It is the two servers gall and lambert.
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# After a successful query the slot stays busy for about as long as the
# query ran. Floor of 5s, not 1.2s: the shorter gap is what drew the 429s.
MIN_QUERY_PAUSE_SEC = 5.0
COOLDOWN_FACTOR = 1.0
# The number in [timeout:] is a reservation, not a wish. The server answers
# 504 without running the query when it cannot set that much time aside.
# These are small around-searches: 25s was still being refused, 10s is
# accepted and finishes in a couple of seconds.
QUERY_TIMEOUT_SEC = 10
# Usage policy: after HTTP 429 or 406, wait at least 30s, or longer when
# the response carries Retry-After. Then try once more. Further retries are
# what gets the IP banned.
ERROR_PAUSE_SEC = 30.0
MAX_POINTS = 80
OBJECT_PAD_M = 30

# Query strategy version. Progress rows older than this are retried, so a
# fixed matcher re-tries everything it previously gave up on.
QUERY_VERSION = 2

# Tags whose outline is the object itself — people stand around it, not in it.
OBJECT_TAGS = {
    ("amenity", "fountain"),
    ("tourism", "artwork"),
    ("man_made", "water_tower"),
    ("man_made", "obelisk"),
    ("historic", "memorial"),
    ("historic", "monument"),
    ("historic", "statue"),
}

# A place badge is somewhere you go. Roads, walls, and admin lines are not.
REJECT_KEYS = {"highway", "barrier", "boundary", "railway", "power", "waterway"}
REJECT_PAIRS = {("natural", "coastline")}

# Tag keys that mark a feature as a destination worth a badge.
DESTINATION_KEYS = (
    "tourism",
    "historic",
    "leisure",
    "amenity",
    "building",
    "man_made",
    "natural",
    "place",
    "landuse",
    "shop",
    "aeroway",
)

# Generic words carry no identity — "Mirabell" does, "Palace" does not.
GENERIC_WORDS = {
    "the", "of", "de", "del", "la", "le", "les", "el", "al", "du", "des", "di",
    "da", "das", "dos", "von", "van", "der", "den", "och", "and", "et", "y",
    "palace", "palacio", "palais", "palazzo", "schloss", "paleis",
    "castle", "castillo", "chateau", "burg", "fort", "fortress", "citadel",
    "cathedral", "catedral", "cathedrale", "dom", "duomo", "minster", "munster",
    "basilica", "church", "iglesia", "eglise", "kirche", "chiesa", "kerk",
    "temple", "templo", "tempio", "mosque", "mezquita", "masjid", "jami",
    "shrine", "monastery", "abbey", "convent", "chapel", "capilla",
    "museum", "museo", "musee", "muzeum", "gallery", "galeria", "galerie",
    "park", "parque", "parc", "garden", "gardens", "jardin", "jardim", "giardino",
    "square", "plaza", "place", "piazza", "platz", "plein",
    "tower", "torre", "turm", "tour", "bridge", "puente", "pont", "brucke",
    "beach", "playa", "plage", "lake", "lago", "lac", "see", "river", "rio",
    "mount", "mountain", "monte", "mont", "hill", "falls", "waterfall",
    "national", "state", "city", "old", "new", "great", "grand", "royal",
    "memorial", "monument", "statue", "fountain", "fuente", "fontana",
    "house", "casa", "haus", "maison", "hall", "centre", "center", "centro",
    "town", "rathaus", "ayuntamiento",
    "market", "mercado", "bazaar", "souk", "street", "avenue", "road",
    "sant", "san", "santa", "santo", "saint", "st", "notre", "dame",
    "art", "arts", "history", "natural", "science", "sciences",
    "view", "viewpoint", "overlook", "lookout", "point", "shore", "area",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


# ---------------------------------------------------------------- name match


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    stripped = stripped.replace("ß", "ss").replace("ø", "o").replace("đ", "d")
    cleaned = "".join(c if c.isalnum() else " " for c in stripped.lower())
    return " ".join(cleaned.split())


def tokens(text: str) -> list[str]:
    return [w for w in normalize(text).split() if len(w) > 2]


def distinctive(text: str, stop: set[str] = frozenset()) -> list[str]:
    return [w for w in tokens(text) if w not in GENERIC_WORDS and w not in stop]


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def name_score(ours: str, theirs: list[str], stop: set[str]) -> float:
    """0..1 similarity between our place name and an OSM feature's names.

    Whole-string similarity breaks across languages (Basel Minster vs Basler
    Münster scores 0.81, but Salta Cathedral vs Catedral Basílica de Salta
    only 0.24). A shared identifying word is the reliable signal, so score
    that first and fall back to whole-string. `stop` holds the city and state
    words, which identify nothing inside their own city — without it "317 W
    Mulberry St, Denton, TX" matches "City of Denton Development Services".

    The English `name` is scored here. A separate pass may also try `address`
    when it is a local name ("Kalaja" for Berat Castle). That pass only keeps
    a polygon the saved point sits inside, so a nearby town or square is not
    adopted just because the words matched.
    """
    mine_norm = normalize(ours)
    if not mine_norm:
        return 0.0
    mine_keys = distinctive(ours, stop)
    best = 0.0
    for other in theirs:
        other_norm = normalize(other)
        if not other_norm:
            continue
        whole = ratio(mine_norm, other_norm)
        # Two unrelated names in the same city can look alike ("Salta
        # Cathedral" vs "Salta Cable" scores 0.69). Only near-identical
        # spelling stands on its own; anything less needs a shared word.
        best = max(best, whole if whole >= 0.8 else whole * 0.7)
        for key in mine_keys:
            for word in distinctive(other, stop):
                if key == word or ratio(key, word) >= 0.86:
                    best = max(best, 0.9)
    return best


def feature_names(tags: dict) -> list[str]:
    names = []
    for key, value in tags.items():
        if not isinstance(value, str):
            continue
        if key == "name" or key.startswith("name:") or key in (
            "alt_name", "int_name", "official_name", "old_name",
            "loc_name", "short_name", "nat_name",
        ):
            names.append(value)
    return names


# ------------------------------------------------------------------ geometry


def to_xy(lat: float, lng: float, lat0: float) -> tuple[float, float]:
    return lng * math.cos(math.radians(lat0)) * 111_320, lat * 111_320


def meters_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    ax, ay = to_xy(a[0], a[1], a[0])
    bx, by = to_xy(b[0], b[1], a[0])
    return math.hypot(ax - bx, ay - by)


def span_m(ring: list[list[float]]) -> float:
    lats = [p[0] for p in ring]
    lngs = [p[1] for p in ring]
    lat0 = sum(lats) / len(lats)
    return max(
        (max(lats) - min(lats)) * 111_320,
        (max(lngs) - min(lngs)) * math.cos(math.radians(lat0)) * 111_320,
    )


def point_in_ring(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y = point[1], point[0]
    inside = False
    for i in range(len(ring) - 1):
        y1, x1 = ring[i]
        y2, x2 = ring[i + 1]
        if (y1 > y) != (y2 > y):
            crossing = x1 + (y - y1) / (y2 - y1) * (x2 - x1)
            if x < crossing:
                inside = not inside
    return inside


def dist_to_segment(
    point: list[float], start: list[float], end: list[float], lat0: float
) -> float:
    px, py = to_xy(point[0], point[1], lat0)
    ax, ay = to_xy(start[0], start[1], lat0)
    bx, by = to_xy(end[0], end[1], lat0)
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def rdp(points: list[list[float]], epsilon: float) -> list[list[float]]:
    if len(points) < 3:
        return points
    lat0 = points[0][0]
    start, end = points[0], points[-1]
    index, dmax = 0, 0.0
    for i in range(1, len(points) - 1):
        d = dist_to_segment(points[i], start, end, lat0)
        if d > dmax:
            index, dmax = i, d
    if dmax > epsilon:
        return rdp(points[: index + 1], epsilon)[:-1] + rdp(points[index:], epsilon)
    return [start, end]


def close_ring(points: list[list[float]]) -> list[list[float]]:
    if points and points[0] != points[-1]:
        return points + [points[0]]
    return points


def simplify_ring(ring: list[list[float]]) -> list[list[float]] | None:
    opened = ring[:-1] if ring and ring[0] == ring[-1] else ring[:]
    if len(opened) < 3:
        return None
    # Scale detail to the object. A flat 8 m turned a castle into a rectangle.
    epsilon = min(8.0, max(1.5, span_m(ring) / 40))
    simplified = opened
    for _ in range(12):
        simplified = rdp(opened, epsilon)
        if len(simplified) <= MAX_POINTS:
            break
        epsilon *= 1.4
    rounded = [[round(lat, 5), round(lng, 5)] for lat, lng in simplified]
    cleaned = [rounded[0]]
    for point in rounded[1:]:
        if point != cleaned[-1]:
            cleaned.append(point)
    cleaned = close_ring(cleaned)
    return cleaned if len(cleaned) >= 5 else None


def stitch_rings(segments: list[list[list[float]]]) -> list[list[list[float]]]:
    """Join relation member ways into closed rings by shared endpoints."""
    pending = [seg[:] for seg in segments if len(seg) >= 2]
    rings: list[list[list[float]]] = []
    while pending:
        current = pending.pop(0)
        changed = True
        while changed and current[0] != current[-1]:
            changed = False
            for i, seg in enumerate(pending):
                if seg[0] == current[-1]:
                    current += seg[1:]
                elif seg[-1] == current[-1]:
                    current += list(reversed(seg))[1:]
                elif seg[-1] == current[0]:
                    current = seg[:-1] + current
                elif seg[0] == current[0]:
                    current = list(reversed(seg))[:-1] + current
                else:
                    continue
                pending.pop(i)
                changed = True
                break
        if current[0] == current[-1] and len(current) >= 4:
            rings.append(current)
    return rings


def keep_rings(rings: list[list[list[float]]]) -> list[list[list[float]]]:
    if not rings:
        return []
    spans = [span_m(ring) for ring in rings]
    largest = max(spans)
    chosen = [r for r, s in zip(rings, spans) if s == largest or s >= 70]
    out = []
    for ring in chosen:
        simple = simplify_ring(ring)
        if simple is not None:
            out.append(simple)
    return out


# ------------------------------------------------------------------ overpass


class OverpassUnavailable(RuntimeError):
    """Rate limit. Stop; do not keep calling or this IP gets banned."""


class OverpassBusy(RuntimeError):
    """This query was refused because the server had no free slot. Skip the
    city and keep going; the places stay unmarked so a later pass retries."""


def run_curl(args: list[str]) -> tuple[str, str, str]:
    """Return body, HTTP status, and the Retry-After header (may be empty)."""
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        return "", proc.stderr.strip() or f"curl {proc.returncode}", ""
    head, _, retry_after = proc.stdout.rpartition("\n")
    body, _, code = head.rpartition("\n")
    return body, code.strip(), retry_after.strip()


def refusal_pause(retry_after: str) -> float:
    """At least 30s, or the server's Retry-After when that is longer."""
    wait = ERROR_PAUSE_SEC
    text = (retry_after or "").strip()
    if text:
        try:
            wait = max(wait, float(text))
        except ValueError:
            pass
    return wait


def pause_for_slot(elapsed: float) -> None:
    """Cooldown after a query that was accepted."""
    time.sleep(max(MIN_QUERY_PAUSE_SEC, elapsed * COOLDOWN_FACTOR))


def fetch_overpass(query: str) -> tuple[str, str, str]:
    """POST one query to the public Overpass endpoint."""
    return run_curl([
        "curl", "-sS", "-A", USER_AGENT,
        "--connect-timeout", "10", "--max-time", "20",
        "-w", "\n%{http_code}\n%header{retry-after}",
        "--data-urlencode", f"data={query}",
        OVERPASS_URL,
    ])


def overpass(query: str) -> dict:
    """One query. A 429 waits the required 30s and retries once, then stops
    the run so this IP is not banned.

    A 504 means the server would not reserve a slot. Retry once after a
    short pause, then skip this city. Waiting minutes and then quitting
    is what left the run on the same country for hours.
    """
    refusals = 0
    server_errors = 0
    connect_errors = 0
    last_wait = ERROR_PAUSE_SEC
    while True:
        started = time.monotonic()
        body, code, retry_after = fetch_overpass(query)
        elapsed = time.monotonic() - started

        if code == "200":
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                server_errors += 1
                if server_errors > 1:
                    raise OverpassUnavailable(
                        "overpass returned a body that is not JSON; stopping"
                    )
                print(f"  overpass bad json, waiting {ERROR_PAUSE_SEC:.0f}s")
                time.sleep(ERROR_PAUSE_SEC)
                continue
            pause_for_slot(elapsed)
            return data

        if code in ("429", "406"):
            if refusals >= 1:
                raise OverpassUnavailable(
                    f"http {code} again after a {last_wait:.0f}s pause; "
                    "stopping so this IP is not banned"
                )
            refusals += 1
            last_wait = refusal_pause(retry_after)
            print(f"  overpass {code}, waiting {last_wait:.0f}s")
            time.sleep(last_wait)
            continue

        if code in ("504", "503", "502", "500"):
            if server_errors >= 1:
                raise OverpassBusy(f"http {code} after one retry")
            server_errors += 1
            print(f"  overpass {code}, waiting 5s")
            time.sleep(5)
            continue

        if not code.isdigit():
            if connect_errors >= 1:
                raise OverpassBusy(
                    "overpass unreachable after one retry. " + (code or "no response")[:160]
                )
            connect_errors += 1
            print("  overpass unreachable, waiting 5s")
            time.sleep(5)
            continue

        raise RuntimeError(f"http {code}: {body[:160]}")


def search_radius_for(place: dict) -> int:
    radius = place.get("radiusM") or 150
    return int(min(1500, max(400, radius * 3)))


def city_candidates(places: list[dict]) -> list[dict]:
    """One call for every place in the city.

    Highways are excluded — they can never be a badge and would otherwise
    crowd out real candidates.
    """
    parts = []
    for place in places:
        radius = search_radius_for(place)
        lat, lng = place["lat"], place["lng"]
        parts.append(f'way(around:{radius},{lat},{lng})["name"][!"highway"];')
        parts.append(
            f'rel(around:{radius},{lat},{lng})["name"]["type"="multipolygon"];'
        )
    query = (
        f"[out:json][timeout:{QUERY_TIMEOUT_SEC}];"
        f"({''.join(parts)});out tags center 800;"
    )
    data = overpass(query)
    return data.get("elements") or []


def rings_of_element(element: dict) -> list[list[list[float]]]:
    if element.get("type") == "way":
        ring = [[p["lat"], p["lon"]] for p in element.get("geometry") or []]
        return [close_ring(ring)] if len(ring) >= 4 else []
    segments = []
    for member in element.get("members") or []:
        if member.get("role") not in ("outer", ""):
            continue
        geom = member.get("geometry") or []
        if len(geom) >= 2:
            segments.append([[p["lat"], p["lon"]] for p in geom])
    return stitch_rings(segments)


def geometry_batch(wanted: list[tuple[str, int]]) -> dict[tuple[str, int], dict]:
    if not wanted:
        return {}
    way_ids = sorted({i for kind, i in wanted if kind == "way"})
    rel_ids = sorted({i for kind, i in wanted if kind == "relation"})
    parts = []
    if way_ids:
        parts.append(f"way(id:{','.join(str(i) for i in way_ids)});")
    if rel_ids:
        parts.append(f"rel(id:{','.join(str(i) for i in rel_ids)});")
    query = (
        f"[out:json][timeout:{QUERY_TIMEOUT_SEC}];"
        f"({''.join(parts)});out geom;"
    )
    data = overpass(query)
    return {
        (element.get("type"), element.get("id")): element
        for element in data.get("elements") or []
    }


# -------------------------------------------------------------------- picker


def is_rejected(tags: dict) -> bool:
    if any(key in tags for key in REJECT_KEYS):
        return True
    return any(tags.get(k) == v for k, v in REJECT_PAIRS)


def has_destination_tag(tags: dict) -> bool:
    return any(key in tags for key in DESTINATION_KEYS)


# A translated name often shares no word with the local one ("Basel Town Hall"
# vs "Rathaus Basel"). Accept a weak match only when the shape actually
# contains the hand-picked point; require only nearness when the name is sure.
STRONG_NAME = 0.85
CLEAR_NAME = 0.62
WEAK_NAME = 0.45
# Address matches are less trusted than the English name. This score sits
# under CLEAR_NAME so the point must fall inside the ring, and outline_from
# also rejects a ring big enough to be the surrounding town.
LOCAL_NAME = 0.5
OBJECT_NAME_WORDS = {"statue", "fountain", "artwork", "obelisk"}

# Some names are only the city plus a category — "Salta Cathedral" has no
# identifying word left once "Salta" and "cathedral" are set aside. For those,
# the category itself is the signal: take the nearest feature tagged that way.
CATEGORY_TAGS: dict[str, list[tuple[str, str]]] = {}


def _register(words: str, pairs: list[tuple[str, str]]) -> None:
    for word in words.split():
        CATEGORY_TAGS[word] = pairs


_register(
    "cathedral catedral cathedrale duomo dom minster munster basilica",
    [("building", "cathedral"), ("amenity", "place_of_worship")],
)
_register(
    "church iglesia eglise kirche chiesa kerk chapel capilla",
    [("amenity", "place_of_worship")],
)
_register(
    "mosque mezquita masjid jami temple templo tempio shrine",
    [("amenity", "place_of_worship")],
)
_register(
    "monastery abbey convent",
    [("amenity", "monastery"), ("historic", "monastery")],
)
_register("museum museo musee muzeum", [("tourism", "museum")])
_register("gallery galeria galerie", [("tourism", "gallery")])
_register("park parque parc", [("leisure", "park")])
_register("garden gardens jardin jardim giardino", [("leisure", "garden"), ("leisure", "park")])
_register("zoo", [("tourism", "zoo")])
_register("stadium", [("leisure", "stadium")])
_register(
    "castle castillo chateau schloss burg fort fortress citadel",
    [("historic", "castle"), ("historic", "fort"), ("historic", "citadel")],
)
_register("palace palacio palais palazzo", [("historic", "castle"), ("building", "palace")])
_register("square plaza piazza platz plein", [("place", "square")])
_register("bridge puente pont brucke", [("man_made", "bridge")])
_register("tower torre turm", [("man_made", "tower")])
_register("market mercado bazaar souk", [("amenity", "marketplace")])
_register("library", [("amenity", "library")])
_register("rathaus ayuntamiento", [("amenity", "townhall")])

# Categories that only read as one across two words.
PHRASE_TAGS: list[tuple[str, list[tuple[str, str]]]] = [
    ("town hall", [("amenity", "townhall")]),
    ("city hall", [("amenity", "townhall")]),
    ("hotel de ville", [("amenity", "townhall")]),
    ("opera house", [("amenity", "theatre")]),
    ("botanical garden", [("leisure", "garden")]),
]
_register("university", [("amenity", "university")])
_register("beach playa plage", [("natural", "beach")])
_register("fountain fuente fontana", [("amenity", "fountain")])
_register("memorial monument statue", [("historic", "memorial"), ("historic", "monument")])


def rank_candidates(
    elements: list[dict], place: dict, pack: dict
) -> list[tuple[float, dict]]:
    stop = set(tokens(pack.get("cityName", ""))) | set(tokens(pack.get("stateName", "")))
    point = (place["lat"], place["lng"])
    radius = place.get("radiusM") or 150

    ranked: list[tuple[float, dict]] = []
    for element in elements:
        tags = element.get("tags") or {}
        if is_rejected(tags) or not has_destination_tag(tags):
            continue
        score = name_score(place["name"], feature_names(tags), stop)
        if score < WEAK_NAME:
            continue
        center = element.get("center") or {}
        try:
            away = meters_between(point, (center["lat"], center["lon"]))
        except KeyError:
            away = radius
        # Near the curated point beats a better-spelled match further off.
        ranked.append((score - min(away, 2000) / 6000, score, element))
    ranked.sort(key=lambda item: item[0], reverse=True)
    shortlist = [(score, element) for _, score, element in ranked]
    if not any(score >= CLEAR_NAME for score, _ in shortlist):
        shortlist += category_candidates(elements, place, stop)
    # Only when the English name and the category both missed. Address is a
    # local name often, and also often a neighbouring landmark.
    if not shortlist:
        shortlist += address_candidates(elements, place, pack, stop)
    return shortlist


def category_candidates(
    elements: list[dict], place: dict, stop: set[str]
) -> list[tuple[float, dict]]:
    """Nearest feature tagged as the category our name describes."""
    if distinctive(place["name"], stop):
        return []
    wanted: list[tuple[str, str]] = []
    for word in tokens(place["name"]):
        wanted += CATEGORY_TAGS.get(word, [])
    normalized = normalize(place["name"])
    for phrase, pairs in PHRASE_TAGS:
        if phrase in normalized:
            wanted += pairs
    if not wanted:
        return []
    point = (place["lat"], place["lng"])
    hits = []
    for element in elements:
        tags = element.get("tags") or {}
        if is_rejected(tags) or not any(tags.get(k) == v for k, v in wanted):
            continue
        center = element.get("center") or {}
        try:
            away = meters_between(point, (center["lat"], center["lon"]))
        except KeyError:
            continue
        hits.append((away, element))
    hits.sort(key=lambda item: item[0])
    # The nearest one may sit just off the curated point; anything behind it
    # has to contain the point outright.
    return [
        (CLEAR_NAME if index == 0 else WEAK_NAME, element)
        for index, (_, element) in enumerate(hits[:2])
    ]


def local_address(place: dict, pack: dict) -> str | None:
    """Local name stored in `address`, or None when it is not safe to search.

    Street numbers are a postal address. The city or state name matches every
    civic building. A statue's address is the square it stands on, and the
    English name was already tried when the two strings are the same.
    """
    address = (place.get("address") or "").strip()
    if not address or any(ch.isdigit() for ch in address):
        return None
    name = (place.get("name") or "").strip()
    if normalize(address) == normalize(name):
        return None
    if set(tokens(name)) & OBJECT_NAME_WORDS:
        return None
    stop = set(tokens(pack.get("cityName", ""))) | set(tokens(pack.get("stateName", "")))
    if not distinctive(address, stop):
        return None
    return address


def phrase_match(address: str, osm_names: list[str]) -> bool:
    """True when one name is the other, or one begins with the other.

    "Kalaja" matches "Kalaja e Beratit". "Corcovado" does not match
    "Capela do Corcovado", and "The Olgas" does not match "Olga Gorge".
    A shared word in the middle of a different name is a different place.
    """
    address_words = normalize(address).split()
    if not address_words:
        return False
    for other in osm_names:
        other_words = normalize(other).split()
        if not other_words:
            continue
        short, long = (
            (address_words, other_words)
            if len(address_words) <= len(other_words)
            else (other_words, address_words)
        )
        if long[: len(short)] == short:
            return True
    return False


def address_candidates(
    elements: list[dict], place: dict, pack: dict, stop: set[str]
) -> list[tuple[float, dict]]:
    """Features whose OSM name is the local address, nearest first."""
    address = local_address(place, pack)
    if not address:
        return []
    point = (place["lat"], place["lng"])
    hits = []
    for element in elements:
        tags = element.get("tags") or {}
        if is_rejected(tags) or not has_destination_tag(tags):
            continue
        if not phrase_match(address, feature_names(tags)):
            continue
        center = element.get("center") or {}
        try:
            away = meters_between(point, (center["lat"], center["lon"]))
        except KeyError:
            away = 0
        hits.append((away, element))
    hits.sort(key=lambda item: item[0])
    return [(LOCAL_NAME, element) for _, element in hits[:3]]


def outline_from(element: dict, place: dict, score: float) -> dict | None:
    rings = keep_rings(rings_of_element(element))
    if not rings:
        return None
    point = (place["lat"], place["lng"])
    radius = place.get("radiusM") or 150
    biggest = max(span_m(ring) for ring in rings)
    if biggest > max(4000, radius * 25):
        return None
    inside = any(point_in_ring(point, ring) for ring in rings)
    if score == LOCAL_NAME:
        # The local name matched. Keep it only when the visitor's point is
        # inside a plot about the size of the place, not the town around it.
        if biggest > min(2500, max(1000, radius * 8)) or not inside:
            return None
    elif not inside:
        if score < CLEAR_NAME:
            return None
        nearest = min(
            dist_to_segment([point[0], point[1]], ring[i], ring[i + 1], point[0])
            for ring in rings
            for i in range(len(ring) - 1)
        )
        # Curated points sometimes sit on the square outside the building.
        allowed = (
            max(600, radius * 4) if score >= STRONG_NAME else max(250, radius * 2)
        )
        if nearest > allowed:
            return None
    outline: dict = {"type": "polygon", "rings": rings}
    tags = element.get("tags") or {}
    if any(tags.get(k) == v for k, v in OBJECT_TAGS):
        outline["padM"] = OBJECT_PAD_M
    return outline


def interior_point(rings: list[list[list[float]]]) -> tuple[float, float] | None:
    """A point inside the biggest ring, for re-centring a stale coordinate."""
    ring = max(rings, key=span_m)
    lats = [p[0] for p in ring[:-1]]
    lngs = [p[1] for p in ring[:-1]]
    middle = (sum(lats) / len(lats), sum(lngs) / len(lngs))
    if point_in_ring(middle, ring):
        return middle
    # Concave shape — walk the scanline through the centre instead.
    row = middle[0]
    crossings = []
    for i in range(len(ring) - 1):
        y1, x1 = ring[i]
        y2, x2 = ring[i + 1]
        if (y1 > row) != (y2 > row):
            crossings.append(x1 + (row - y1) / (y2 - y1) * (x2 - x1))
    crossings.sort()
    if len(crossings) >= 2:
        return (row, (crossings[0] + crossings[1]) / 2)
    return None


def near_enough(element: dict, place: dict) -> bool:
    center = element.get("center") or {}
    try:
        away = meters_between((place["lat"], place["lng"]), (center["lat"], center["lon"]))
    except KeyError:
        return True
    return away <= search_radius_for(place) + 400


def resolve_city(pack: dict, places: list[dict]) -> dict[str, tuple[dict | None, str]]:
    """Pick an outline for every place in one city, using two Overpass calls."""
    elements = city_candidates(places)
    if not elements:
        return {p["id"]: (None, "nothing mapped nearby") for p in places}

    shortlist: dict[str, list[tuple[float, dict]]] = {}
    wanted: list[tuple[str, int]] = []
    for place in places:
        nearby = [e for e in elements if near_enough(e, place)]
        top = rank_candidates(nearby, place, pack)[:3]
        shortlist[place["id"]] = top
        for _, element in top:
            if element.get("type") in ("way", "relation") and element.get("id"):
                wanted.append((element["type"], element["id"]))

    geometry = geometry_batch(wanted)

    results: dict[str, tuple[dict | None, str]] = {}
    for place in places:
        top = shortlist[place["id"]]
        if not top:
            results[place["id"]] = (None, f"no name match among {len(elements)} nearby")
            continue
        chosen = None
        for score, element in top:
            full = geometry.get((element.get("type"), element.get("id")))
            if full is None:
                continue
            full = {**full, "tags": element.get("tags") or full.get("tags") or {}}
            outline = outline_from(full, place, score)
            if outline is not None:
                name = (element.get("tags") or {}).get("name", "?")
                via = " — local name" if score == LOCAL_NAME else ""
                chosen = (outline, f"{element['type']} {element['id']} — {name}{via}")
                break
        results[place["id"]] = chosen or (
            None,
            f"{len(top)} name matches, none usable as an area",
        )
    return results


# ------------------------------------------------------------------- driving


def load_progress() -> dict:
    if not PROGRESS_PATH.exists():
        return {}
    return json.loads(PROGRESS_PATH.read_text())


def save_progress(progress: dict) -> None:
    tmp = PROGRESS_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(progress, indent=2) + "\n")
    tmp.replace(PROGRESS_PATH)


def iter_packs(country: str | None):
    for path in sorted(PACKS.glob("*/*/*/city.json")):
        pack_id = str(path.relative_to(PACKS).parent)
        if country and not pack_id.startswith(f"{country}/"):
            continue
        yield pack_id, path


def acquire_lock() -> None:
    if LOCK_PATH.exists():
        pid = LOCK_PATH.read_text().strip()
        alive = pid.isdigit() and Path(f"/proc/{pid}").exists()
        if not alive and pid.isdigit():
            try:
                os.kill(int(pid), 0)
                alive = True
            except (OSError, ValueError):
                alive = False
        if alive:
            raise SystemExit(
                f"another run is active (pid {pid}). Two runs get the IP rate-limited."
            )
    LOCK_PATH.write_text(str(os.getpid()))


def release_lock() -> None:
    if LOCK_PATH.exists():
        LOCK_PATH.unlink()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--country", help="Only this country id, e.g. us")
    parser.add_argument("--city", help="Only this pack id, e.g. us/texas/denton")
    parser.add_argument("--limit", type=int, default=0, help="Stop after N lookups")
    parser.add_argument(
        "--redo",
        action="store_true",
        help="Re-look-up places that already have an outline",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--local-name",
        action="store_true",
        help="Retry name-match misses using the local name stored in address",
    )
    args = parser.parse_args()

    acquire_lock()
    print(f"overpass: {OVERPASS_URL.split('/')[2]}")
    progress = load_progress()
    looked_up = written = skipped = missed = busy = 0
    busy_in_a_row = 0

    try:
        for pack_id, path in iter_packs(args.country):
            if args.city and pack_id != args.city:
                continue
            pack = json.loads(path.read_text())
            changed = False

            todo = []
            for place in pack.get("places") or []:
                key = f"{pack_id}/{place['id']}"
                row = progress.get(key) or {}
                if args.local_name:
                    why = row.get("why") or ""
                    if (
                        place.get("outline")
                        or row.get("status") != "miss"
                        or not why.startswith("no name match")
                        or row.get("local")
                        or local_address(place, pack) is None
                    ):
                        skipped += 1
                        continue
                    todo.append(place)
                    continue
                if place.get("outline") and not args.redo:
                    progress[key] = {
                        "status": "ok",
                        "at": row.get("at", now_iso()),
                        "qv": max(row.get("qv", 0), QUERY_VERSION),
                    }
                    skipped += 1
                    continue
                if row.get("qv", 0) >= QUERY_VERSION and row.get("status") in (
                    "ok",
                    "miss",
                    "error",
                ):
                    skipped += 1
                    continue
                todo.append(place)

            if not todo:
                continue
            if args.limit and looked_up >= args.limit:
                save_progress(progress)
                print(f"stopped at limit {args.limit}. written {written}.")
                return

            print(f"{pack_id} — {len(todo)} places")
            looked_up += len(todo)
            try:
                resolved = resolve_city(pack, todo)
            except OverpassBusy as error:
                busy += 1
                busy_in_a_row += 1
                print(f"  skipped for now: {error}")
                if busy_in_a_row >= 8:
                    print(
                        "  stopped: eight cities in a row found the server busy. "
                        "Restart later; nothing here was marked done."
                    )
                    if not args.dry_run:
                        save_progress(progress)
                    return
                continue
            except OverpassUnavailable as error:
                print(f"  stopped: {error}")
                if not args.dry_run:
                    save_progress(progress)
                return
            except Exception as error:  # noqa: BLE001 — keep the run moving
                print(f"  error {error}")
                if not args.dry_run:
                    for place in todo:
                        progress[f"{pack_id}/{place['id']}"] = {
                            "status": "error",
                            "at": now_iso(),
                            "qv": QUERY_VERSION,
                            "error": str(error)[:200],
                        }
                    save_progress(progress)
                continue

            busy_in_a_row = 0
            for place in todo:
                key = f"{pack_id}/{place['id']}"
                outline, why = resolved.get(place["id"], (None, "not resolved"))
                if outline is None:
                    missed += 1
                    print(f"  miss {place['name']} — {why}")
                    if not args.dry_run:
                        progress[key] = {
                            "status": "miss",
                            "at": now_iso(),
                            "qv": QUERY_VERSION,
                            "why": why,
                        }
                        if args.local_name:
                            progress[key]["local"] = 1
                    continue
                points = sum(max(0, len(r) - 1) for r in outline["rings"])
                pad = outline.get("padM", 0)
                rings = outline["rings"]

                # An exact name match whose shape sits away from the stored
                # coordinate means the coordinate is stale, not the shape.
                # Leaving them apart would frame the map away from the plot.
                moved = 0.0
                if not any(
                    point_in_ring((place["lat"], place["lng"]), ring) for ring in rings
                ):
                    middle = interior_point(rings)
                    if middle is not None:
                        moved = meters_between((place["lat"], place["lng"]), middle)
                        if not args.dry_run:
                            place["lat"] = round(middle[0], 5)
                            place["lng"] = round(middle[1], 5)

                print(
                    f"  ok {place['name']} — {points} pts"
                    + (f" pad {pad}m" if pad else "")
                    + (f" — point moved {int(moved)}m" if moved >= 25 else "")
                    + f" — {why}"
                )
                if args.dry_run:
                    continue
                progress[key] = {
                    "status": "ok",
                    "at": now_iso(),
                    "qv": QUERY_VERSION,
                    "points": points,
                    "padM": pad,
                    "source": why,
                }
                if args.local_name:
                    progress[key]["local"] = 1
                if moved >= 25:
                    progress[key]["movedM"] = int(moved)
                place["outline"] = outline
                changed = True
                written += 1

            if not args.dry_run:
                save_progress(progress)

            if changed and not args.dry_run:
                pack["updatedAt"] = now_iso()
                tmp = path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(pack, indent=2) + "\n")
                tmp.replace(path)

        save_progress(progress)
        print(
            f"done. lookups {looked_up}. written {written}. "
            f"missed {missed}. skipped {skipped}. busy {busy}."
        )
    finally:
        release_lock()


if __name__ == "__main__":
    main()
