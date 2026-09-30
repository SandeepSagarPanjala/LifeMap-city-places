/**
 * Generate the lean city-entry catalog for the app (Option B).
 *
 * Reads data/city-places/index.json complete rows (name + bbox) and writes:
 *   assets/city-places/city-entry-catalog.json
 *   assets/city-places/continents/{af,as,eu,na,oc,sa}.json
 *
 * Does NOT ship pending cities or babysit fields. Also builds a coarse grid
 * `cells` map for O(1)-ish candidate lookup (cellDeg = 0.5°).
 * Continent files are the same shape, one continent each. The app downloads
 * all six and keeps only the continent the user is standing in for GPS.
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
const CONTINENTS_DIR = path.join(ROOT, 'assets/city-places/continents');

/** ~55 km cells — matches city-places plan. */
const CELL_DEG = 0.5;

/** Country id (first segment of a city id) → continent file. */
const COUNTRY_CONTINENT = {
  us: 'na', ca: 'na', mx: 'na', gt: 'na', bz: 'na', sv: 'na', hn: 'na',
  ni: 'na', cr: 'na', pa: 'na', cu: 'na', do: 'na', ht: 'na', jm: 'na',
  bs: 'na', bb: 'na', tt: 'na',
  br: 'sa', ar: 'sa', cl: 'sa', co: 'sa', pe: 'sa', ve: 'sa', ec: 'sa',
  bo: 'sa', py: 'sa', uy: 'sa', gy: 'sa', sr: 'sa',
  gb: 'eu', ie: 'eu', fr: 'eu', de: 'eu', es: 'eu', it: 'eu', pt: 'eu',
  nl: 'eu', be: 'eu', lu: 'eu', ch: 'eu', at: 'eu', dk: 'eu', se: 'eu',
  no: 'eu', fi: 'eu', is: 'eu', pl: 'eu', cz: 'eu', sk: 'eu', hu: 'eu',
  ro: 'eu', bg: 'eu', gr: 'eu', hr: 'eu', si: 'eu', rs: 'eu', ba: 'eu',
  me: 'eu', mk: 'eu', al: 'eu', xk: 'eu', ee: 'eu', lv: 'eu', lt: 'eu',
  ua: 'eu', by: 'eu', md: 'eu', mt: 'eu', cy: 'eu', ad: 'eu', mc: 'eu',
  li: 'eu', sm: 'eu', va: 'eu', ru: 'eu',
  in: 'as', cn: 'as', jp: 'as', kr: 'as', kp: 'as', tw: 'as', hk: 'as',
  mo: 'as', mn: 'as', th: 'as', vn: 'as', kh: 'as', la: 'as', mm: 'as',
  my: 'as', sg: 'as', id: 'as', ph: 'as', bn: 'as', tl: 'as', pk: 'as',
  bd: 'as', lk: 'as', np: 'as', bt: 'as', mv: 'as', af: 'as', kz: 'as',
  uz: 'as', tm: 'as', kg: 'as', tj: 'as', az: 'as', am: 'as', ge: 'as',
  tr: 'as', iq: 'as', ir: 'as', sy: 'as', lb: 'as', jo: 'as', il: 'as',
  ps: 'as', sa: 'as', ae: 'as', qa: 'as', kw: 'as', bh: 'as', om: 'as',
  ye: 'as',
  eg: 'af', ly: 'af', tn: 'af', dz: 'af', ma: 'af', sd: 'af', ss: 'af',
  et: 'af', er: 'af', dj: 'af', so: 'af', ke: 'af', ug: 'af', tz: 'af',
  rw: 'af', bi: 'af', cd: 'af', cg: 'af', cm: 'af', cf: 'af', td: 'af',
  ne: 'af', ng: 'af', bj: 'af', tg: 'af', gh: 'af', ci: 'af', bf: 'af',
  ml: 'af', sn: 'af', gm: 'af', gw: 'af', gn: 'af', sl: 'af', lr: 'af',
  mr: 'af', za: 'af', na: 'af', bw: 'af', zw: 'af', zm: 'af', mw: 'af',
  mz: 'af', ao: 'af', ga: 'af', gq: 'af', st: 'af', cv: 'af', mu: 'af',
  sc: 'af', km: 'af', mg: 'af', ls: 'af', sz: 'af',
  au: 'oc', nz: 'oc', pg: 'oc', fj: 'oc', sb: 'oc', vu: 'oc', ws: 'oc',
  to: 'oc', ck: 'oc', pf: 'oc', nc: 'oc',
};

const CONTINENT_IDS = ['af', 'as', 'eu', 'na', 'oc', 'sa'];

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
        if (COUNTRY_CONTINENT[countryId] == null) {
          errors.push(`${id}: country "${countryId}" has no continent`);
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

  /** @type {Record<string, Record<string, { name: string, bbox: object }>>} */
  const byContinent = {};
  for (const id of CONTINENT_IDS) {
    byContinent[id] = {};
  }
  for (const id of sortedCityIds) {
    const continent = COUNTRY_CONTINENT[id.split('/')[0]];
    byContinent[continent][id] = sortedCities[id];
  }

  fs.mkdirSync(CONTINENTS_DIR, { recursive: true });
  /** @type {Record<string, string>} */
  const cellOwner = {};
  /** @type {string[]} */
  const overlaps = [];
  for (const continent of CONTINENT_IDS) {
    const continentCities = byContinent[continent];
    /** @type {Record<string, string[]>} */
    const continentCells = {};
    for (const [id, entry] of Object.entries(continentCities)) {
      for (const key of cellKeysForBbox(entry.bbox)) {
        if (!continentCells[key]) {
          continentCells[key] = [];
        }
        continentCells[key].push(id);
        const owner = cellOwner[key];
        if (owner != null && owner !== continent) {
          overlaps.push(`${key}: ${owner} and ${continent}`);
        } else {
          cellOwner[key] = continent;
        }
      }
    }
    for (const key of Object.keys(continentCells)) {
      continentCells[key].sort();
    }
    const continentCatalog = {
      schemaVersion: 1,
      continent,
      generatedAt: catalog.generatedAt,
      cellDeg: CELL_DEG,
      cityCount: Object.keys(continentCities).length,
      cities: continentCities,
      cells: continentCells,
    };
    const out = path.join(CONTINENTS_DIR, `${continent}.json`);
    fs.writeFileSync(out, `${JSON.stringify(continentCatalog, null, 2)}\n`);
    console.log(
      `Wrote ${continentCatalog.cityCount} cities → ${path.relative(ROOT, out)}`,
    );
  }
  if (overlaps.length > 0) {
    console.warn(
      `Shared squares across continents (${overlaps.length}). GPS uses the first continent for that square:`,
    );
    for (const line of overlaps) {
      console.warn(`  - ${line}`);
    }
  }
}

main();
