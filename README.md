# LifeMap city places

**Public** catalog of curated city packs (landmarks + badge PNGs) for the [LifeMap](https://github.com/SandeepSagarPanjala/LifeMap) app.

LifeMap itself is private. Packs must live here so the app can fetch them over CDN (jsDelivr) without exposing app source.

## CDN

- Packs: `https://cdn.jsdelivr.net/gh/SandeepSagarPanjala/LifeMap-city-places@main/data/city-places/`
- Entry catalog: `https://cdn.jsdelivr.net/gh/SandeepSagarPanjala/LifeMap-city-places@main/assets/city-places/city-entry-catalog.json`

## Babysit / `go` work

Open this repo in Cursor and follow **[docs/city-places/README.md](./docs/city-places/README.md)**. Say `go`.

After completing cities: regenerate the catalog (`pnpm city-places:catalog`), commit, and **push to `main` on this repo** — not the private LifeMap app repo.
