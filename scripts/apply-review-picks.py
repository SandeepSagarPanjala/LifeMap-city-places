#!/usr/bin/env python3
"""Write outlines for places whose OpenStreetMap feature was picked by review.

The saved point must sit inside the polygon. A small object whose point is
just outside the footprint is kept and given the 30 m pad.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "data" / "city-places"
PICKS = Path(__file__).resolve().parent / ".review-picks.json"

_path = Path(__file__).resolve().parent / "fill-place-outlines.py"
_spec = importlib.util.spec_from_file_location("fill_place_outlines", _path)
fill = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(fill)


def nearest_m(point, rings) -> float:
    return min(
        fill.dist_to_segment([point[0], point[1]], ring[i], ring[i + 1], point[0])
        for ring in rings
        for i in range(len(ring) - 1)
    )


def main() -> None:
    picks = json.loads(PICKS.read_text())
    places = {}
    packs = {}
    for path in PACKS.glob("*/*/*/city.json"):
        pack_id = str(path.relative_to(PACKS).parent)
        if not any(key.startswith(pack_id + "/") for key in picks):
            continue
        pack = json.loads(path.read_text())
        packs[pack_id] = (path, pack)
        for place in pack.get("places") or []:
            places[f"{pack_id}/{place['id']}"] = place

    wanted = [(row["type"], row["id"]) for row in picks.values()]
    geometry = fill.geometry_batch(wanted)
    progress = fill.load_progress()
    written = 0
    for key, row in picks.items():
        place = places.get(key)
        element = geometry.get((row["type"], row["id"]))
        if place is None or element is None:
            print(f"  miss {key} — no geometry")
            continue
        outline = fill.outline_from(element, place, fill.STRONG_NAME)
        if outline is None:
            print(f"  miss {place['name']} — shape unusable")
            continue
        rings = outline["rings"]
        point = (place["lat"], place["lng"])
        inside = any(fill.point_in_ring(point, ring) for ring in rings)
        span = max(fill.span_m(ring) for ring in rings)
        if not inside:
            gap = nearest_m(point, rings)
            if span > 80 or gap > 80:
                print(f"  miss {place['name']} — point {int(gap)}m outside a {int(span)}m shape")
                continue
            outline["padM"] = fill.OBJECT_PAD_M
        name = (element.get("tags") or {}).get("name", "?")
        pack_id = key.rsplit("/", 1)[0]
        path, pack = packs[pack_id]
        place["outline"] = outline
        progress[key] = {
            "status": "ok",
            "at": fill.now_iso(),
            "qv": fill.QUERY_VERSION,
            "points": sum(max(0, len(r) - 1) for r in rings),
            "padM": outline.get("padM", 0),
            "source": f"{row['type']} {row['id']} — {name} — review",
        }
        pack["updatedAt"] = fill.now_iso()
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(pack, indent=2) + "\n")
        tmp.replace(path)
        written += 1
        print(f"  ok {place['name']} — {name}")
    fill.save_progress(progress)
    print(f"done. written {written}.")


if __name__ == "__main__":
    main()
