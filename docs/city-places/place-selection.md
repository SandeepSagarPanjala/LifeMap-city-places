# Place selection criteria

**Status: active** — babysit agents must follow these rules when filling a city pack.

Related: [README.md](./README.md) · [badge-art.md](./badge-art.md)

---

## Goal

Encourage people to go see the places that **make that city famous** — landmarks and destinations worth a deliberate visit. Each city pack lists **min 0, max 20** places. **20 is a cap, not a goal** — only add a place if it truly belongs; never pad to hit 20. Most cities will land well under the cap; mega destinations (NYC, LA, etc.) may use more of the range.

---

## Which cities go in the index (critical)

**Do not catalog every municipality.** The USA alone has tens of thousands of cities; packing all of them is impossible.

Only add **popular / destination cities** to `index.json`:

- Major metros and state capitals people travel to
- Famous tourist towns (e.g. Sedona, Savannah, Bar Harbor, Moab)
- Skip ordinary suburbs, tiny towns, and places with no clear visitor draw

Rough scale: **a few cities per state** (often ~2–8), not hundreds. Worldwide: expand **country by country**; start with **United States**.

Cities not in the index simply have no city-places pack. Category achievements still work everywhere.

---

## Include (places inside a packed city)

Prefer places a visitor would go see **on purpose**:

- Famous landmarks, monuments, bridges, towers, viewpoints
- Major parks, beaches, lakes, waterfronts people travel for
- Iconic cultural / historic sites (temples, plazas, old towns, city-defining museums)
- Stadiums / arenas only if they are a real destination for that city
- **Paid attractions are OK when they are city-famous** (e.g. Louvre, Empire State Building). Prefer free/public when equally iconic; do not exclude a must-see just because it charges admission.

Rule of thumb: if a traveler would name it when asked “what should I see in {city}?”, it qualifies.

---

## Exclude

Do **not** fill slots with:

- Generic chains (Starbucks, McDonald’s, gas stations, pharmacies)
- **Hotels, resorts, motels, B&Bs, and restaurants / cafés / bars / shops as places to stay or eat** — even famous or luxury ones. City packs are not a lodging or dining guide.
- Airports, hospitals, offices, strip malls (unless a true tourist icon — almost never)
- Residential neighborhoods or random streets
- Temporary events, pop-ups, seasonal markets (unless permanently iconic)
- Duplicate viewpoints of the same landmark (one place id per landmark)

**Narrow exception:** a building that *happens* to be (or once was) a hotel, motel, or restaurant may qualify **only** if visitors go there as a **historic / cultural landmark**, not for a room or a meal — e.g. A.G. Gaston Motel as part of Birmingham’s Civil Rights National Monument. If the pitch is “great hotel” or “must-eat restaurant,” **skip it**.

---

## Ranking when there are more than 20

1. Most recognizable / most “must visit for this city”
2. Prefer geographic spread across the city over clustering every slot in one district
3. Prefer outdoors / public-access when two options are tied
4. Prefer free when two options are equally iconic; otherwise keep the famous paid one
5. Drop the rest — do not exceed 20

---

## Cities with nothing notable

If research finds no place that clearly qualifies, write `places: []` and mark the city `complete`. Zero is valid.

---

## Coordinates and unlock radius

| Field | Rule |
| --- | --- |
| `lat` / `lng` | Main public access point or the recognizable center of the landmark (verify from a reliable map/source) |
| `radiusM` | Default **150**. Use **300–500** only for large parks, beaches, or sprawling sites where 150 m would miss a normal visit |
| `address` | Optional; short real-world or well-known location string when reliable |
| `howTo` | Plain language: “Visit the Golden Gate Bridge.” No app jargon |

---

## Badge subject (what the image shows)

The badge must show **that place** — what we are telling the user to go see.

| Place type | Badge shows |
| --- | --- |
| Landmark (bridge, tower, monument) | That landmark, recognizable |
| Museum / famous building | That building’s exterior (or iconic hall only if the exterior is not distinctive) |
| Park / beach / viewpoint | That park/beach/view, not a generic “nature” stock scene |
| Temple / plaza / historic site | That specific site |

**Do not** use:

- A generic city skyline unless the place *is* that viewpoint
- Unrelated symbols, maps pins, trophies, or abstract icons
- Text or logos on the scene
- A different famous place from another city

Full art pipeline: [badge-art.md](./badge-art.md).

---

## Research expectations

- Cross-check that the place is in **this** city (not a suburb listed under the wrong pack unless the pack is for that suburb).
- Prefer well-established destinations over fleeting “viral” spots.
- If unsure whether something is city-famous enough, **skip it** rather than pad the list.
