/**
 * Worksheet registration test.
 *
 * Validates:
 *  - Every worksheet ID follows PPL-STR-XXX-### pattern
 *  - Every worksheet has a unique ID
 *  - Every worksheet chainPosition is sequential (1, 2, 3...)
 *  - CHG references are present and well-formed
 *  - chainLabel is "strategy_design" for all strategy chain worksheets
 *
 * Usage: node tests/registration-test.mjs
 */

import { readFileSync } from 'node:fs';
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
  console.log('=== Worksheet Registration Test ===\n');

  let slice;
  try {
    const raw = readFileSync(SLICE_PATH, 'utf8');
    slice = JSON.parse(raw);
  } catch (e) {
    console.log(`  FAIL: Could not load CATALOGUE slice: ${e.message}`);
    process.exit(1);
    return;
  }

  const worksheets = slice.slice.worksheets;
  const ids = new Set();
  const idPattern = /^PPL-STR-[A-Z]+-\d{3}$/;

  // ── ID format & uniqueness ──
  console.log('1. Worksheet ID format & uniqueness');
  for (const ws of worksheets) {
    assert(idPattern.test(ws.id), `${ws.id}: matches PPL-STR-XXX-### pattern`);
    if (ids.has(ws.id)) {
      assert(false, `${ws.id}: unique ID (DUPLICATE FOUND)`);
    } else {
      ids.add(ws.id);
      assert(true, `${ws.id}: unique ID`);
    }
  }

  // ── Chain position sequential ──
  console.log('\n2. Chain position sequence');
  const positions = worksheets.map((w) => w.chainPosition).sort((a, b) => a - b);
  for (let i = 0; i < positions.length; i++) {
    assert(positions[i] === i + 1, `Chain position ${i + 1} present`);
  }

  // ── chainLabel ──
  console.log('\n3. chainLabel = strategy_design');
  for (const ws of worksheets) {
    assert(ws.chainLabel === 'strategy_design', `${ws.id}: chainLabel is "strategy_design"`);
  }

  // ── CHG references ──
  console.log('\n4. CHG references present & well-formed');
  const chgPattern = /^CHG-\d+$/;
  for (const ws of worksheets) {
    assert(Array.isArray(ws.chgRefs) && ws.chgRefs.length > 0, `${ws.id}: has CHG references`);
    for (const ref of ws.chgRefs) {
      assert(chgPattern.test(ref), `${ws.id}: CHG ref "${ref}" well-formed`);
    }
  }

  // ── subject/shelf ──
  console.log('\n5. Subject & shelf');
  assert(slice.slice.subject === 'People and Organization', 'subject is "People and Organization"');
  assert(slice.slice.shelf === 'Strategy and Design', 'shelf is "Strategy and Design"');

  // ── People shelf briefing ──
  console.log('\n6. People shelf briefing');
  const psb = slice.slice.peopleShelfBriefing;
  assert(!!psb, 'peopleShelfBriefing defined');
  assert(Array.isArray(psb.chgRefs) && psb.chgRefs.length > 0, 'peopleShelfBriefing has CHG refs');

  // ── Summary ──
  console.log(`\n=== Registration Test Results ===`);
  console.log(`Pass: ${pass}`);
  console.log(`Fail: ${fail}`);
  console.log(`Registration integrity: ${fail === 0 ? 'VALID' : 'INVALID'}`);

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error('Registration test crashed:', e);
  process.exit(2);
});