/**
 * Worksheet registration module for the People & Organization → Strategy and Design slice.
 *
 * Registers every worksheet in the CATALOGUE slice, validates that each
 * worksheet has a paired before-briefing, and exposes reachability/drift
 * metadata for CHG-15 wiring validation.
 *
 * Usage:
 *   node catalogue/register.mjs        -- validate + print registry
 *   import { register } from './catalogue/register.mjs'
 */

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(__dirname);
const SLICE_PATH = join(ROOT, 'catalogue', 'slice.json');

/** Load the CATALOGUE slice. */
export function loadSlice() {
  const raw = readFileSync(SLICE_PATH, 'utf8');
  return JSON.parse(raw);
}

/** Check that a file exists at the given path (relative to ROOT). */
export function fileExists(relPath) {
  return existsSync(join(ROOT, relPath));
}

/** Register all worksheets: validate presence of worksheet + before-briefing. */
export function register() {
  const slice = loadSlice();
  const worksheets = slice.slice.worksheets;
  const results = [];

  for (const ws of worksheets) {
    const wsExists = fileExists(ws.path);
    const bbExists = fileExists(ws.beforeBriefing);
    results.push({
      id: ws.id,
      theorist: ws.theorist,
      worksheetExists: wsExists,
      beforeBriefingExists: bbExists,
      registered: wsExists && bbExists,
      chgRefs: ws.chgRefs,
      chainPosition: ws.chainPosition,
      chainLabel: ws.chainLabel,
    });
  }

  return { slice, results };
}

/** Print the registry to stdout. */
export function printRegistry() {
  const { results } = register();
  console.log('=== People & Organization → Strategy and Design Worksheet Registry ===\n');
  for (const r of results) {
    const status = r.registered ? 'REGISTERED' : 'MISSING FILES';
    console.log(`${r.id} — ${r.theorist}`);
    console.log(`  Chain: ${r.chainLabel} position ${r.chainPosition}`);
    console.log(`  CHG refs: ${r.chgRefs.join(', ')}`);
    console.log(`  Worksheet: ${r.worksheetExists ? 'present' : 'MISSING'}`);
    console.log(`  Before briefing: ${r.beforeBriefingExists ? 'present' : 'MISSING'}`);
    console.log(`  Status: ${status}\n`);
  }
  const allRegistered = results.every((r) => r.registered);
  console.log(`Total: ${results.length} worksheets, ${results.filter((r) => r.registered).length} registered`);
  console.log(`All registered: ${allRegistered}`);
  process.exit(allRegistered ? 0 : 1);
}

/** Get CHG-15 wiring metadata from the slice. */
export function getChg15Metadata() {
  const slice = loadSlice();
  return slice.slice.wiring.chg15;
}

/** Run when invoked directly. */
if (process.argv[1] && process.argv[1].endsWith('register.mjs')) {
  printRegistry();
}