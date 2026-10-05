# Fill place outlines

One script. All packs. Resumable.

Chicago already has outlines and is skipped. Everyone else gets the same rules: an OpenStreetMap plot when one exists, simplified to about 80 points. A fountain, sculpture, statue, monument, or water tower also gets a **30 m pad**, because their outline is the object, not the ground people stand on. A park, museum, stadium, or zoo does not. No plot in OpenStreetMap means the place stays one point and a radius, and that is a normal outcome, not a failure.

Do this in the **LifeMap-city-places** repo, not the private app repo. Do not push until a sample looks right in the places explorer.

## How a place is matched

Every place already has a hand-picked lat/lng and a radius, so the script never asks a geocoder to parse `"name, city, state"`. That query shape returns nothing whenever the object sits in a neighbouring commune (Château de Chillon is in Veytaux, not Montreux) or OSM knows it by its local name (Schloss Mirabell, not Mirabell Palace Gardens).

Instead it asks Overpass for named areas around the curated point, then picks one by name:

- A shared identifying word wins, across languages: Basel Minster matches Basler Münster, Mozart's Birthplace matches Mozarts Geburtshaus.
- City and state words are ignored when matching, or every place in Denton matches every other thing named Denton.
- Near-identical spelling also wins. Anything less needs a shared word, so "Salta Cathedral" does not grab "Salta Cable".
- When the name is only a city plus a category ("Basel Town Hall"), the category is the signal and the nearest feature tagged that way is used.
- The pack's `address` is deliberately not used. It holds a nearby landmark — "Place du Marché" for the Freddie Mercury statue — so matching it returns the wrong building.

A match is only kept if the shape sits on the curated point: it contains the point, or it is close enough given how sure the name is.

## Run

From the repo root:

```bash
python3 scripts/fill-place-outlines.py
```

Ctrl-C is safe. Run the same command again and it continues. Progress is `scripts/.outline-run-progress.json`, and a lock file stops two runs at once — two runs get the IP rate-limited and both crawl.

Useful while checking:

```bash
python3 scripts/fill-place-outlines.py --city us/texas/denton --dry-run --redo
python3 scripts/fill-place-outlines.py --country us --limit 200
```

`--dry-run` writes nothing, not even progress. `--redo` re-looks-up places that already have an outline.

Expect **10 hours or so** for all ~4,100 places, so run it overnight. It is two Overpass calls per city, not per place, but the public Overpass endpoint refuses roughly 40% of calls under load and each one is retried.

## Then check it

```bash
python3 scripts/audit-outlines.py
```

This compares every stored outline to its hand-picked point. It is the check that caught an earlier run writing shapes up to 16,000 km from the place, because the geocoder had found a same-named place on another continent. `--strip-bad` removes the wrong ones so the next fill run retries them.

Then open the places explorer, pick a few cities, and click one place at a time. The solid shape is the plot. A dashed line inside it is the object before the 30 m pad.

The phone app does not read these outlines yet.
