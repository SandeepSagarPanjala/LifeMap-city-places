#!/usr/bin/env python3
"""Save nearby OpenStreetMap names for US and India places the name match missed.

One Overpass call per city. Resumable. Does not write outlines.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

_path = Path(__file__).resolve().parent / "fill-place-outlines.py"
_spec = importlib.util.spec_from_file_location("fill_place_outlines", _path)
fill = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fill)

OUT = Path(__file__).resolve().parent / ".review-candidates.json"
COUNTRIES = ("us", "in")
KEEP = 15
TAG_KEYS = (
    "tourism", "historic", "leisure", "amenity", "building", "man_made",
    "natural", "place", "landuse", "shop", "aeroway", "boundary",
)


def load_out() -> dict:
    if not OUT.exists():
        return {}
    return json.loads(OUT.read_text())


def save_out(data: dict) -> None:
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(OUT)


def brief_tags(tags: dict) -> dict:
    kept = {}
    for key in TAG_KEYS:
        if key in tags:
            kept[key] = tags[key]
    return kept


def candidates_for(place: dict, elements: list[dict]) -> list[dict]:
    point = (place["lat"], place["lng"])
    rows = []
    for element in elements:
        if not fill.near_enough(element, place):
            continue
        tags = element.get("tags") or {}
        if fill.is_rejected(tags):
            continue
        names = fill.feature_names(tags)
        if not names:
            continue
        center = element.get("center") or {}
        try:
            away = int(fill.meters_between(point, (center["lat"], center["lon"])))
        except KeyError:
            away = 0
        rows.append((away, {
            "type": element.get("type"),
            "id": element.get("id"),
            "name": tags.get("name") or names[0],
            "names": names[:6],
            "tags": brief_tags(tags),
            "awayM": away,
        }))
    rows.sort(key=lambda item: item[0])
    return [row for _, row in rows[:KEEP]]


def main() -> None:
    fill.acquire_lock()
    saved = load_out()
    progress = fill.load_progress()
    print(f"overpass: {fill.OVERPASS_URL.split('/')[2]}")
    looked = 0
    try:
        for pack_id, path in fill.iter_packs(None):
            if not pack_id.startswith(COUNTRIES):
                continue
            pack = json.loads(path.read_text())
            todo = []
            for place in pack.get("places") or []:
                key = f"{pack_id}/{place['id']}"
                if key in saved:
                    continue
                row = progress.get(key) or {}
                why = row.get("why") or ""
                if place.get("outline"):
                    continue
                if row.get("status") != "miss" or not why.startswith("no name match"):
                    continue
                todo.append(place)
            if not todo:
                continue
            print(f"{pack_id} — {len(todo)} places")
            try:
                elements = fill.city_candidates(todo)
            except fill.OverpassBusy as error:
                print(f"  skipped for now: {error}")
                continue
            except fill.OverpassUnavailable as error:
                print(f"  stopped: {error}")
                save_out(saved)
                return
            for place in todo:
                key = f"{pack_id}/{place['id']}"
                rows = candidates_for(place, elements)
                saved[key] = {
                    "name": place.get("name"),
                    "address": place.get("address") or "",
                    "city": pack.get("cityName"),
                    "state": pack.get("stateName"),
                    "lat": place.get("lat"),
                    "lng": place.get("lng"),
                    "radiusM": place.get("radiusM"),
                    "nearby": len(elements),
                    "candidates": rows,
                }
                looked += 1
                print(f"  {place['name']} — {len(rows)} names")
            save_out(saved)
        save_out(saved)
        print(f"done. collected {looked}. saved {len(saved)}.")
    finally:
        fill.release_lock()


if __name__ == "__main__":
    main()
