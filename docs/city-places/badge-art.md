# City place badge art

Place badges use the **same visual pipeline** as LifeMap achievement badges. Do not invent a second frame style.

Frame script (in this repo): `scripts/apply-achievement-badge-frame.mjs`

This matches LifeMap achievement badge framing (same gold bezel). The private LifeMap app repo is not needed for babysit work.

---

## Output

| Rule | Value |
| --- | --- |
| Size | **512 × 512** px |
| Format | PNG |
| Path | `data/city-places/{country}/{state}/{city}/badges/{placeId}.png` |
| Frame | Identical gold bezel via the shared frame script — never drawn by the image model |

Working (unframed) scenes may live at:

`data/city-places/{country}/{state}/{city}/scenes/{placeId}.png`

---

## Two-step pipeline (mandatory)

1. Generate a **scene only** (full-bleed, square, no frame) for the place.
2. Run the frame script so every badge gets the **same** gold bezel.

Example (adjust paths for the city you are packing):

```bash
# Frame scenes for one city into its badges folder
node scripts/apply-achievement-badge-frame.mjs \
  --in data/city-places/us/california/san-francisco/scenes \
  --out data/city-places/us/california/san-francisco/badges
```

Never ship a model image that already includes a gold frame. Never skip the frame script.

City place badges are **not** wired into `src/lib/achievements/images.ts` (those are bundled achievements only). Packs are downloaded later by the app.

---

## Scene prompt template

Copy and fill `{PLACE_NAME}` / `{CITY}` / `{SUBJECT_DETAIL}` / `{MOOD}`. Keep the STRICT block unchanged.

```text
LifeMap city-place achievement SCENE only (frame will be added in post).

STRICT (must obey):
- EXACTLY square 1:1 composition (not landscape / widescreen)
- Subject fills the ENTIRE canvas edge-to-edge
- FULL BLEED photograph / soft painterly realism
- NO frame, NO border, NO gold trim, NO mat, NO rounded badge shape
- NO letterboxing, NO pillarboxing, NO black or white bars on any side
- NO text, NO logo, NO watermark, NO UI chrome
- Readable and clear when scaled down to ~72pt

Place: {PLACE_NAME} in {CITY}
Subject: {SUBJECT_DETAIL}
Mood: {MOOD}
Color harmony: warm cream, soft teal accents, natural light preferred
```

**Subject tip:** the badge **is** the place. Golden Gate → the bridge; a museum → that museum building; a beach → that beach. Not a map pin, trophy, or generic skyline (unless the place *is* that viewpoint). See [place-selection.md](./place-selection.md) § Badge subject.

---

## Checklist per place

- [ ] `placeId` slug matches JSON `id` and filename
- [ ] Scene generated with STRICT prompt (no frame in the image)
- [ ] Frame script applied → `badges/{placeId}.png` is 512×512 with gold bezel
- [ ] Visual QA: same gold on all four sides; no second frame; no text/logos
