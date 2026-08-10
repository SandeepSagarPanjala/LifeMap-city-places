/**
 * Generate the lean city-entry catalog for the app (Option B).
 *
 * Reads data/city-places/index.json complete rows (name + bbox) and writes:
 *   assets/city-places/city-entry-catalog.json
 *
 * Does NOT ship pending cities or babysit fields. Also builds a coarse grid
 * `cells` map for O(1)-ish candidate lookup (cellDeg = 0.5°).
 *
 * Usage:
 *   node scripts/generate-city-entry-catalog.mjs
 *   pnpm city-places:catalog
 */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const INDEX_PATH = path.join(ROOT, 'data/city-places/index.json');
const OUT_PATH = path.join(ROOT, 'assets/city-places/city-entry-catalog.json');

/** ~55 km cells — matches city-places plan. */
const CELL_DEG = 0.5;

/**
 * @param {unknown} bbox
 * @returns {bbox is { minLat: number, minLng: number, maxLat: number, maxLng: number }}
 */
function isValidBbox(bbox) {
  if (bbox == null || typeof bbox !== 'object') {
    return false;
  }
  const b = /** @type {Record<string, unknown>} */ (bbox);
  for (const key of ['minLat', 'minLng', 'maxLat', 'maxLng']) {
    if (typeof b[key] !== 'number' || Number.isNaN(b[key])) {
      return false;
    }
  }
  return b.minLat <= b.maxLat && b.minLng <= b.maxLng;
}

/**
 * @param {{ minLat: number, minLng: number, maxLat: number, maxLng: number }} bbox
 * @returns {string[]}
 */
function cellKeysForBbox(bbox) {
  const minI = Math.floor(bbox.minLat / CELL_DEG);
  const maxI = Math.floor(bbox.maxLat / CELL_DEG);
  const minJ = Math.floor(bbox.minLng / CELL_DEG);
  const maxJ = Math.floor(bbox.maxLng / CELL_DEG);
  /** @type {string[]} */
  const keys = [];
  for (let i = minI; i <= maxI; i++) {
    for (let j = minJ; j <= maxJ; j++) {
      keys.push(`${i},${j}`);
    }
  }
  return keys;
}

function main() {
  if (!fs.existsSync(INDEX_PATH)) {
    console.error(`Missing index: ${INDEX_PATH}`);
    process.exit(1);
  }

  const index = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8'));
  /** @type {Record<string, { name: string, bbox: { minLat: number, minLng: number, maxLat: number, maxLng: number } }>} */
  const cities = {};
  /** @type {string[]} */
  const errors = [];

  for (const country of index.countries ?? []) {
    const countryId = country.id;
    for (const state of country.states ?? []) {
      const stateId = state.id;
      for (const city of state.cities ?? []) {
        if (city.status !== 'complete') {
          continue;
        }
        const id = `${countryId}/${stateId}/${city.id}`;
        if (!city.name || typeof city.name !== 'string') {
          errors.push(`${id}: complete row missing name`);
          continue;
        }
        if (!isValidBbox(city.bbox)) {
          errors.push(`${id}: complete row missing or invalid bbox`);
          continue;
        }
        cities[id] = {
          name: city.name,
          bbox: {
            minLat: city.bbox.minLat,
            minLng: city.bbox.minLng,
            maxLat: city.bbox.maxLat,
            maxLng: city.bbox.maxLng,
          },
        };
      }
    }
  }

  if (errors.length > 0) {
    console.error('city-entry-catalog: refused to write — fix index first:');
    for (const err of errors) {
      console.error(`  - ${err}`);
    }
    process.exit(1);
  }

  /** @type {Record<string, string[]>} */
  const cells = {};
  for (const [id, entry] of Object.entries(cities)) {
    for (const key of cellKeysForBbox(entry.bbox)) {
      if (!cells[key]) {
        cells[key] = [];
      }
      if (!cells[key].includes(id)) {
        cells[key].push(id);
      }
    }
  }
  for (const key of Object.keys(cells)) {
    cells[key].sort();
  }

  const sortedCityIds = Object.keys(cities).sort();
  /** @type {Record<string, { name: string, bbox: object }>} */
  const sortedCities = {};
  for (const id of sortedCityIds) {
    sortedCities[id] = cities[id];
  }

  const catalog = {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    cellDeg: CELL_DEG,
    cityCount: sortedCityIds.length,
    cities: sortedCities,
    cells,
  };

  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  fs.writeFileSync(OUT_PATH, `${JSON.stringify(catalog, null, 2)}\n`);
  console.log(
    `Wrote ${sortedCityIds.length} cities → ${path.relative(ROOT, OUT_PATH)}`,
  );
}

main();
