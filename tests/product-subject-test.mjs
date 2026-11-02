/**
 * Product subject test.
 *
 * Validates that the worksheet system integrates with a product subject model:
 *  - Worksheets are registerable product artifacts
 *  - Before briefings are attachable product documentation
 *  - CATALOGUE slice is a valid product registry artifact
 *
 * Usage: node tests/product-subject-test.mjs
 */

import { readFileSync, existsSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = dirname(__dirname);
const SLICE_PATH = join(ROOT, 'catalogue', 'slice.json');

let pass = 0;
let fail = 0;

function assert(condition, message) {
  if (condition) {
    console.log(`  PASS: ${message}`);
    pass++;
  } else {
    console.log(`  FAIL: ${message}`);
    fail++;
  }
}

async function main() {
  console.log('=== Product Subject Test ===\n');

  // ── 1. CATALOGUE slice is a valid product registry artifact ──
  console.log('1. CATALOGUE slice as product artifact');
  let slice;
  try {
    const raw = readFileSync(SLICE_PATH, 'utf8');
    slice = JSON.parse(raw);
    assert(true, 'slice.json parses as valid JSON (product artifact)');
  } catch (e) {
    assert(false, `slice.json valid JSON: ${e.message}`);
    console.log(`\nResults: ${pass} pass, ${fail} fail`);
    process.exit(1);
    return;
  }

  // Version field present (product artifact convention)
  assert(typeof slice.slice.version === 'string' && slice.slice.version.length > 0, 'slice has version field');
  assert(typeof slice.slice.generated === 'string', 'slice has generated timestamp');

  // ── 2. Worksheets are registerable product artifacts ──
  console.log('\n2. Worksheets as registerable product artifacts');
  const worksheets = slice.slice.worksheets;
  for (const ws of worksheets) {
    assert(typeof ws.id === 'string' && ws.id.length > 0, `${ws.id}: has product ID`);
    assert(typeof ws.theorist === 'string' && ws.theorist.length > 0, `${ws.id}: has theorist name`);
    assert(typeof ws.framework === 'string' && ws.framework.length > 0, `${ws.id}: has framework description`);
    assert(typeof ws.path === 'string' && ws.path.length > 0, `${ws.id}: has file path`);
    assert(typeof ws.beforeBriefing === 'string' && ws.beforeBriefing.length > 0, `${ws.id}: has before-briefing path`);
    assert(Array.isArray(ws.chgRefs) && ws.chgRefs.length > 0, `${ws.id}: has CHG references`);
    assert(typeof ws.status === 'string', `${ws.id}: has status field`);
  }

  // ── 3. Files on disk match product registry ──
  console.log('\n3. Product artifact files on disk');
  for (const ws of worksheets) {
    const wsPath = join(ROOT, ws.path);
    const bbPath = join(ROOT, ws.beforeBriefing);
    assert(existsSync(wsPath), `Product artifact on disk: ${ws.path}`);
    assert(existsSync(bbPath), `Product artifact on disk: ${ws.beforeBriefing}`);
  }

  // ── 4. Registration module is importable ──
  console.log('\n4. Registration module importable (product integration)');
  try {
    await import('../catalogue/register.mjs');
    assert(true, 'catalogue/register.mjs imports without error');
  } catch (e) {
    assert(false, `catalogue/register.mjs imports: ${e.message}`);
  }

  // ── 5. Wiring probe exists (CHG-15 product wiring) ──
  console.log('\n5. CHG-15 wiring probe (product wiring artifact)');
  const probePath = join(ROOT, 'wiring', 'chg-15-probe.mjs');
  assert(existsSync(probePath), 'CHG-15 wiring probe exists');

  // ── Summary ──
  console.log(`\n=== Product Subject Test Results ===`);
  console.log(`Pass: ${pass}`);
  console.log(`Fail: ${fail}`);
  console.log(`Product subject integration: ${fail === 0 ? 'VALID' : 'INVALID'}`);

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error('Product subject test crashed:', e);
  process.exit(2);
});