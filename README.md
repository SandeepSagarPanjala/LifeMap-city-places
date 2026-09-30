# LifeMap city places

**Public** catalog of curated city packs (landmarks + badge PNGs) for the [LifeMap](https://github.com/SandeepSagarPanjala/LifeMap) app.

LifeMap itself is private. Packs must live here so the app can fetch them over CDN (jsDelivr) without exposing app source.

## CDN

- Packs: `https://cdn.jsdelivr.net/gh/SandeepSagarPanjala/LifeMap-city-places@main/data/city-places/`
- Entry catalog (all continents, kept for reference): `https://cdn.jsdelivr.net/gh/SandeepSagarPanjala/LifeMap-city-places@main/assets/city-places/city-entry-catalog.json`
- Continent catalogs the app downloads: `https://cdn.jsdelivr.net/gh/SandeepSagarPanjala/LifeMap-city-places@main/assets/city-places/continents/{af,as,eu,na,oc,sa}.json`
- Explore tree (country / state / city names only): `https://cdn.jsdelivr.net/gh/SandeepSagarPanjala/LifeMap-city-places@main/assets/city-places/geography.json`

## Babysit / `go` work

Open this repo in Cursor and follow **[docs/city-places/README.md](./docs/city-places/README.md)**. Say `go`.

After completing cities: regenerate the catalog (`pnpm city-places:catalog`), commit, and **push to `main` on this repo** — not the private LifeMap app repo.
