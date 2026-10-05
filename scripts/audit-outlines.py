#!/usr/bin/env python3
"""Check every stored outline against its hand-picked point.

A geocoder will happily return a same-named place on another continent, so a
written outline is not evidence of a correct one. Each place already has a
curated lat/lng; the shape has to sit on it. Run this after a fill run and
before pushing packs.

    python3 scripts/audit-outlines.py
    python3 scripts/audit-outlines.py --strip-bad   # drop the wrong ones
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import importlib.util

ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "data" / "city-places"

_spec = importlib.util.spec_from_file_location(
    "fill_place_outlines", Path(__file__).resolve().parent / "fill-place-outlines.py"
)
_fill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fill)


def distance_to_outline(place: dict, rings: list) -> tuple[bool, float]:
    point = (place["lat"], place["lng"])
    if any(_fill.point_in_ring(point, ring) for ring in rings):
        return True, 0.0
    nearest = min(
        _fill.dist_to_segment([point[0], point[1]], ring[i], ring[i + 1], point[0])
        for ring in rings
        for i in range(len(ring) - 1)
    )
    return False, nearest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strip-bad", action="store_true")
    args = parser.parse_args()

    total = inside = near = 0
    bad: list[tuple[float, str, str]] = []

    for path in sorted(PACKS.glob("*/*/*/city.json")):
        pack = json.loads(path.read_text())
        pack_id = str(path.relative_to(PACKS).parent)
        changed = False
        for place in pack.get("places") or []:
            outline = place.get("outline")
            if not outline:
                continue
            total += 1
            rings = outline.get("rings") or []
            radius = place.get("radiusM") or 150
            contains, away = distance_to_outline(place, rings)
            if contains:
                inside += 1
            elif away <= max(250, radius * 2):
                near += 1
            else:
                bad.append((away, f"{pack_id}/{place['id']}", place["name"]))
                if args.strip_bad:
                    place.pop("outline")
                    changed = True
        if changed:
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(pack, indent=2) + "\n")
            tmp.replace(path)

    print(f"outlines: {total}")
    print(f"  contains the point : {inside}")
    print(f"  close to it        : {near}")
    print(f"  wrong place        : {len(bad)}")
    if bad:
        bad.sort(reverse=True)
        print("\nfarthest:")
        for away, key, name in bad[:20]:
            print(f"  {int(away):>9} m  {name[:36]:<36} {key}")
        if args.strip_bad:
            print(f"\nremoved {len(bad)} outlines. Re-run the fill to retry them.")


if __name__ == "__main__":
    main()
