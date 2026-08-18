# City places catalog — babysit runbook

> **Home repo:** [LifeMap-city-places](https://github.com/SandeepSagarPanjala/LifeMap-city-places) (public).  
> Do **not** add packs, badges, or catalog files to the private LifeMap app repo.  
> After each `go`: `pnpm city-places:catalog`, commit, and **push to `main` here** so jsDelivr updates.

Single source of truth for cataloging **popular places per city** worldwide.

Goal: build downloadable **city packs** (JSON + badge PNGs). The LifeMap app will later fetch a pack when the user enters that city and unlock places by lat/lng. **Do not** bake the world into the app binary.

---

## Human — how to run (minimal)

You should **not** need a long prompt.

1. Open this **LifeMap-city-places** repo in Cursor (not the private LifeMap app).
2. Open a **new** Cursor Agent chat (keep it only for city-places).
3. Attach / mention this file: `@docs/city-places/README.md`
4. Send only: `go`

That is enough. The agent must follow **START HERE** below. Optional: use Cursor Automations / a daily loop that opens this doc and sends `go`.

**Batching:** each `go` **starts and finishes one country** (bootstrap geography if needed, then every curated city in that country through Phase C). Do not stop after a state slice or a city count cap. Long runs are expected and OK.

**Always run / chain countries:** When a country is fully complete (catalog + commit + push `main`), **immediately** start the next country in the queue — do **not** ask the human which country, whether to continue, or for another `go`. Keep working until the session is interrupted or the queue is empty. Do not wait for “ok start” between countries.

Do **not** paste research instructions, schemas, or checklists — they live in this doc and its links.

---

## START HERE (Cursor agent)

If you are an agent and the user pointed you at this file (or said `go` / `continue` / `next city` / `start` / granted ongoing run permission), **execute immediately**. Do not wait for a longer prompt. Do not ask “what should I do?”, “which country next?”, or “should I continue?”.

### Mandatory reads (do these first)

1. This file (all sections).
2. [place-selection.md](./place-selection.md) — what to include/exclude; badge subject = that place.
3. [badge-art.md](./badge-art.md) — scene → gold frame pipeline.
4. Framing details live in [badge-art.md](./badge-art.md) (shared gold-frame script in this repo).

### Country queue (auto-advance)

Skip countries already `complete` in `index.json`. Take the first incomplete entry:

1. `us` — United States (**complete**)
2. `in` — India (**complete**)
3. `jp` — Japan (**complete**)
4. `gb` — United Kingdom (**complete**)
5. `fr` — France (**complete**)
6. `it` — Italy (**complete**)
7. `es` — Spain (**complete**)
8. `de` — Germany (**complete**)
9. `au` — Australia (**complete**)
10. `ca` — Canada (**complete**)
11. `th` — Thailand (**complete**)
12. `kr` — South Korea (**complete**)
13. `nl` — Netherlands (**complete**)
14. `pt` — Portugal (**complete**)
15. `ch` — Switzerland (**complete**)
16. `nz` — New Zealand (**complete**)
17. `sg` — Singapore (**complete**)
18. `ae` — United Arab Emirates (**complete**)
19. `br` — Brazil (**complete**)
20. `mx` — Mexico (**complete**)
21. `id` — Indonesia (**complete**)
22. `tr` — Turkey (**complete**)
23. `gr` — Greece (**complete**)
24. `eg` — Egypt (**complete**)
25. `ma` — Morocco (**complete**)
26. `vn` — Vietnam (**complete**)
27. `ph` — Philippines (**complete**)
28. `my` — Malaysia (**complete**)
29. `za` — South Africa (**complete**)
30. `ar` — Argentina (**complete**)
31. `pe` — Peru (**complete**)
32. `co` — Colombia (**complete**)
33. `cl` — Chile (**complete**)
34. `ie` — Ireland (**complete**)
35. `cz` — Czech Republic (**complete**)
36. `at` — Austria (**complete**)
37. `no` — Norway (**complete**)
38. `hr` — Croatia (**complete**)
39. `hu` — Hungary (**complete**)
40. `pl` — Poland (**complete**)
41. `is` — Iceland (**complete**)
42. `se` — Sweden (**complete**)
43. `dk` — Denmark (**complete**)
44. `fi` — Finland (**complete**)
45. `be` — Belgium (**complete**)
46. `tw` — Taiwan (**complete**)
47. `hk` — Hong Kong (**complete**)
48. `jo` — Jordan (**complete**)
49. `il` — Israel (**complete**)
50. `kh` — Cambodia (**complete**)
51. `lk` — Sri Lanka (**complete**)
52. `np` — Nepal (**complete**)
53. `ke` — Kenya (**complete**)
54. `cr` — Costa Rica (**complete**)
55. `do` — Dominican Republic (**complete**)
56. `ro` — Romania (**complete**)
57. `tn` — Tunisia (**complete**)
58. `pa` — Panama (**complete**)
59. `ec` — Ecuador (**complete**)
60. `uy` — Uruguay (**complete**)
61. `gt` — Guatemala

When the listed queue is exhausted, extend it again with the next high-tourism country (do not stall asking the human). Update `index.json` notes to the country currently in progress.

### Then do work (loop)

1. Ensure `data/city-places/` exists. Curated popular cities only — do not add every municipality.
2. Open `data/city-places/index.json`.
3. Decide work from the index:
   - Incomplete cities under a country → finish that country (Phase C for every pending city).
   - `cursor` is `null` / no incomplete country → take the **next queue country**, bootstrap Phase A+B, then Phase C for **all** curated cities.
4. Follow [place-selection.md](./place-selection.md). If its status is TBD → **stop** and tell the human; do not invent places.
5. For Phase C: research (web), write `city.json` + badge PNGs, mark each city `complete` **including copying `bbox` onto the index row**, run `pnpm city-places:catalog`, advance `cursor`.
6. When the country’s last pending city is complete: update notes, catalog, commit, **push `main`**, summarize briefly, then **immediately start the next queue country** in the same session (do not wait for another human message).
7. Keep looping until interrupted or no more countries remain to pack.

### Country batch rule (important)

| Situation | What to do |
| --- | --- |
| New / incomplete country under focus | Finish **the entire country** (A+B if needed + all curated cities) |
| Country just finished + pushed | **Immediately** start the next queue country — no ask |
| Do **not** | Cap at 10 states / 50 cities, leave a country half-done, or pause for “which country?” |

Long sessions and many badge generations are expected. Prefer finishing and chaining over stopping early.

### Hard stops

- Never leave the focused country with pending curated cities when ending a successful country (unless the human explicitly interrupts the session).
- Never edit another `in_progress` city.
- Never rename completed slugs.
- Never open or modify the private LifeMap app repo for pack work unless a human explicitly asks for app/runtime changes.
- Never ask the human for permission to continue to the next country.

Related docs:

| Doc | Role |
| --- | --- |
| [badge-art.md](./badge-art.md) | Place badge images (same gold-frame pipeline as achievements) |
| [place-selection.md](./place-selection.md) | What counts as a popular place |
Data lives under `data/city-places/` in **this** repository (see layout below).

---

## Non‑negotiable rules

1. **0–20 places per city** (cap, not a target). Empty cities are valid: `status: complete` with `places: []`.
2. **Never invent place-selection criteria.** Follow [place-selection.md](./place-selection.md). If that doc still says TBD, **stop and ask a human** before listing places.
3. **Finish country, then chain:** complete the focused country (all curated cities), push `main`, then immediately start the next queue country. Do not touch another city’s pack while it is `in_progress`. Do not ask the human between countries.
4. **Stable slugs forever.** Never rename a completed `country` / `state` / `city` / `place` id. Fix typos only via a new place id + deprecate note (do not silently rewrite history).
5. **Ids are lowercase ASCII:** `[a-z0-9-]+` only. Example city id: `us/california/san-francisco`. Example place id: `golden-gate-bridge`.
6. **Badge art matches achievements.** Scene → shared gold frame script → 512×512 PNG. See [badge-art.md](./badge-art.md).
7. **Coordinates required** for every place (`lat`, `lng`). Address is optional but preferred when reliable.
8. Mark progress in `data/city-places/index.json` every time you finish a city.

---

## Phases

Work in order. Do not jump to place badges before the geography under the cursor exists.

### Phase A — Countries and states

Populate `data/city-places/index.json` with countries and first-level subdivisions.

**Current focus:** follow the **Country queue** above. Complete countries: US, India, Japan. Next: United Kingdom (`gb`), then continue the queue without asking.

### Phase B — Popular cities only (not every city)

For each state, add only **destination / popular cities** (see [place-selection.md](./place-selection.md) § Which cities). Typical: ~2–8 per state. Status starts as `pending` (or `complete` if a pack already exists).

Do **not** dump every census place. Still no place badges in this phase — geography list only.

### Phase C — Places + badges (daily babysit)

For each **pending** city in the curated list, research and write the pack (0–20 places + badges), then mark `complete`. Finish **every** pending city in the focused country (no city-count cap), then chain to the next country.

---

## Repo layout

```text
data/city-places/
  index.json                          # master progress + cursor
  schema/
    city-pack.schema.json             # optional JSON Schema
  {country}/{state}/{city}/
    city.json                         # pack
    badges/{placeId}.png              # framed 512×512
    scenes/{placeId}.png              # optional unframed scene (working files)
```

Docs:

```text
docs/city-places/
  README.md                 # this file
  badge-art.md
  place-selection.md
```

---

## Slug and path rules

| Piece | Rule | Example |
| --- | --- | --- |
| country | ISO-ish lowercase slug | `us`, `in`, `jp` |
| state | lowercase hyphenated | `california`, `karnataka` |
| city | lowercase hyphenated | `san-francisco`, `bengaluru` |
| place | lowercase hyphenated, unique within city | `golden-gate-bridge` |
| city pack id | `{country}/{state}/{city}` | `us/california/san-francisco` |
| badge file | `badges/{placeId}.png` | `badges/golden-gate-bridge.png` |

Folder path must equal pack `id`.

---

## Progress index (`data/city-places/index.json`)

Minimal shape:

```json
{
  "schemaVersion": 1,
  "cursor": "us/california/san-francisco",
  "updatedAt": "2026-08-09T00:00:00.000Z",
  "countries": [
    {
      "id": "us",
      "countryCode": "US",
      "name": "United States",
      "states": [
        {
          "id": "california",
          "stateCode": "CA",
          "name": "California",
          "cities": [
            {
              "id": "san-francisco",
              "name": "San Francisco",
              "status": "pending",
              "packPath": "us/california/san-francisco/city.json",
              "placeCount": null,
              "completedAt": null,
              "bbox": null
            }
          ]
        }
      ]
    }
  ]
}
```

### City row fields

| Field | When | Notes |
| --- | --- | --- |
| `name` | always | Display name (“Welcome to {name}”) |
| `status` | always | See table below |
| `packPath` | always | Relative path to `city.json` |
| `placeCount` / `completedAt` | `complete` | Set when pack is finished |
| `bbox` | **required when `status: complete`** | Copy from that city’s `city.json` `bbox`. `null` / omit while `pending` / `in_progress` |

**Repo vs app (important):**

| Artifact | Role | What it contains |
| --- | --- | --- |
| `data/city-places/index.json` | Babysit / progress in the **repo** | All curated cities (pending + complete), statuses, packPath, placeCount, and `bbox` on complete rows |
| App city-entry catalog (generated) | What the **app** ships or downloads for welcome | **Only complete** cities, lean shape: `id → { name, bbox }` — no pending cities, no babysit fields |

Do **not** embed the full `index.json` in the app. It is large and full of progress-only fields the client does not need before Track.

**Generate lean catalog (Option B shape) from complete index rows:**

```bash
pnpm city-places:catalog
# → assets/city-places/city-entry-catalog.json
```

Output shape (app-facing; not the full index):

```json
{
  "schemaVersion": 1,
  "cellDeg": 0.5,
  "cityCount": 2,
  "cities": {
    "us/alabama/birmingham": {
      "name": "Birmingham",
      "bbox": {
        "minLat": 33.45,
        "minLng": -86.9,
        "maxLat": 33.56,
        "maxLng": -86.74
      }
    }
  },
  "cells": {
    "66,-174": ["us/alabama/birmingham"]
  }
}
```

Re-run after every city marked `complete` (babysit definition of done). The script **fails** if a complete row is missing `name` or `bbox`. App code reads only this file for “Welcome to {name}” / point-in-bbox — never embed full `index.json`.

Babysit agents still write `bbox` onto the index when completing a city (so the generator always has a source).

### App lookup — not O(n) over all cities

Do **not** loop `Object.values(cities)` on every GPS point. The catalog includes a precomputed `cells` map:

1. Most points: if `cellKey === lastCellKey` → return (almost free).
2. `cellKey = floor(lat/cellDeg) + "," + floor(lng/cellDeg)` → **O(1)** hash lookup in `cells`.
3. That returns 0–few candidate city ids (usually 0 or 1).
4. Point-in-bbox only on those candidates — then sticky / already-welcomed checks.

So cost stays ~O(1) per cell change, not O(number of cities). A naive scan of all cities would be O(n); that is why `cells` exists.

### City `status`

| Status | Meaning |
| --- | --- |
| `pending` | Not started |
| `in_progress` | This run owns the city — do not steal |
| `complete` | Pack written; 0–20 places finalized; **`bbox` set** |
| `skipped` | Intentionally not cataloged (rare; note why in a comment field if added later) |

### Cursor rules

- `cursor` is the next city pack id to work (`country/state/city`).
- After completing a city, set that city to `complete`, copy `bbox` from `city.json`, set `cursor` to the next `pending` city in deterministic order: country order → state order → city order (as listed in the index).
- If no pending cities remain in the current state, Phase B that state (or move to the next state / country).

---

## City pack (`city.json`)

```json
{
  "schemaVersion": 1,
  "id": "us/california/san-francisco",
  "countryCode": "US",
  "countryName": "United States",
  "stateCode": "CA",
  "stateName": "California",
  "cityName": "San Francisco",
  "bbox": {
    "minLat": 37.7,
    "minLng": -122.55,
    "maxLat": 37.84,
    "maxLng": -122.35
  },
  "updatedAt": "2026-08-09T00:00:00.000Z",
  "status": "complete",
  "places": [
    {
      "id": "golden-gate-bridge",
      "name": "Golden Gate Bridge",
      "lat": 37.8199,
      "lng": -122.4783,
      "radiusM": 150,
      "address": "Golden Gate Bridge, San Francisco, CA",
      "howTo": "Visit the Golden Gate Bridge.",
      "badge": "badges/golden-gate-bridge.png"
    }
  ]
}
```

### Place fields

| Field | Required | Notes |
| --- | --- | --- |
| `id` | yes | Slug; matches badge filename |
| `name` | yes | Human display name |
| `lat` / `lng` | yes | WGS84 decimal degrees; verify from a reliable source |
| `radiusM` | yes | Unlock radius in meters; default **150** unless the site clearly needs more (large parks) |
| `address` | no | Prefer a short real-world address or well-known location string |
| `howTo` | yes | Plain language (“Visit …”). No app jargon |
| `badge` | yes | Relative path `badges/{id}.png` |

### Pack rules

- `places.length` must be **0–20**.
- Every place with a `badge` path must have a matching framed PNG on disk.
- `bbox` should roughly cover the city (used later for “user entered this city”).
- `status` on the pack should be `complete` when written.

---

## Babysit session loop (Phase C)

Agents: run this checklist without the human re-pasting it (see **START HERE**).

1. **Read** this README + [place-selection.md](./place-selection.md) + [badge-art.md](./badge-art.md).
2. **Open** `data/city-places/index.json`. Identify the focused country (incomplete cities, or next queue country). Scope = **that whole country**.
3. If [place-selection.md](./place-selection.md) is still TBD → **stop** and ask a human.
4. If the country is missing from the index → Phase A+B (subdivisions + curated cities) first, then Phase C in the same session.
5. For each pending city in that country (cursor / pending order):
   1. Set city to `in_progress`. Update `updatedAt`.
   2. **Research** popular places (web search). Apply place-selection rules. Cap at 20; 0 is OK; do not pad.
   3. Record each place: `id`, `name`, `lat`, `lng`, `radiusM`, optional `address`, `howTo`.
   4. **Create badges** per [badge-art.md](./badge-art.md) (scene → frame → `badges/{id}.png`).
   5. Write `data/city-places/{country}/{state}/{city}/city.json`.
   6. Set city `status: complete`, `placeCount`, `completedAt`, copy `bbox` from `city.json` onto the index row, run `pnpm city-places:catalog`, advance `cursor`.
6. When the country has no pending curated cities left: update notes, catalog, commit, push `main`, brief summary.
7. **Immediately** take the next country from the queue and repeat from step 2 — do not ask the human.

### Conflict / safety

- Do not edit a city already `in_progress` by another session.
- Do not change lat/lng or ids of a `complete` pack without an explicit human amend request.
- Do not add places over 20; if more candidates exist, pick the best 20 per place-selection.md and leave the rest out.
- Do not commit secrets. Packs are intended to be public.

---

## App behavior (implemented)

When a user visits a curated city (complete pack in lean catalog):

1. GPS persist (cell-gated) resolves city from `assets/city-places/city-entry-catalog.json` (`cells` + `bbox`).
2. Map shows non-dismissable **Welcome to {name}** (`Close` = decline, `Track achievements` = download).
3. Cold start refreshes remote catalog at most every 24h (configurable); never on GPS.
4. Track downloads `city.json` + `badges/` from jsDelivr (`data/city-places/...`) into Documents + SQLite.
5. Achievements shows tracked city sections (locked grayscale / unlocked color).
6. When a stay **seals** (today’s sealable prefix on refresh, or yesterday finalize), centroids within `radiusM` unlock that city’s places and Map can celebrate the same day — not “tomorrow only”.

Babysit agents only produce packs + progress. They do not change app unlock code unless explicitly asked.

---

## Definition of done for one city

- [ ] City folder exists: `data/city-places/{country}/{state}/{city}/`
- [ ] `city.json` valid (0–20 places, required fields present)
- [ ] Each place has framed `badges/{id}.png` (512×512, gold frame)
- [ ] Index city row: `status: complete`, `placeCount` set, `completedAt` set, **`bbox` copied from `city.json`**
- [ ] `pnpm city-places:catalog` regenerated (`assets/city-places/city-entry-catalog.json` includes the city)
- [ ] Changes committed and **pushed to `main` on LifeMap-city-places** (not LifeMap)
- [ ] `cursor` advanced
- [ ] Place selection followed; no invented criteria


---

## Publishing (CDN)

This repository is public so the LifeMap app can download packs via jsDelivr.

1. Finish Phase C for the **country** (packs + index + `pnpm city-places:catalog`).
2. Commit on `main` (or merge a PR into `main`).
3. **Push to GitHub** `SandeepSagarPanjala/LifeMap-city-places`.
4. Wait a minute for jsDelivr to pick up `@main` (purge CDN cache only if a stale file is stuck).

Do **not** commit city packs into the private LifeMap app repository.
