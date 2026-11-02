/**
 * People subject test.
 *
 * Validates People & Organization subject integrity:
 *  - Subject name is correct
 *  - Shelf structure exists
 *  - Worksheets cover the Lewin → Mintzberg range
 *  - Each worksheet has the required sections
 *
 * Usage: node tests/people-test.mjs
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
  console.log('=== People Subject Test ===\n');

  let slice;
  try {
    const raw = readFileSync(SLICE_PATH, 'utf8');
    slice = JSON.parse(raw);
  } catch (e) {
    console.log(`  FAIL: Could not load CATALOGUE slice: ${e.message}`);
    process.exit(1);
    return;
  }

  // ── Subject name ──
  console.log('1. Subject identity');
  assert(slice.slice.subject === 'People and Organization', 'subject = "People and Organization"');
  assert(slice.slice.shelf === 'Strategy and Design', 'shelf = "Strategy and Design"');

  // ── Worksheet count ──
  console.log('\n2. Worksheet coverage (Lewin → Mintzberg range)');
  const worksheets = slice.slice.worksheets;
  assert(worksheets.length >= 3, `At least 3 worksheets (found ${worksheets.length})`);

  const theorists = worksheets.map((w) => w.theorist);
  assert(theorists.includes('Kurt Lewin'), 'Kurt Lewin worksheet present');
  assert(theorists.includes('Jay Galbraith'), 'Jay Galbraith worksheet present');
  assert(theorists.includes('Henry Mintzberg'), 'Henry Mintzberg worksheet present');

  // ── Lewin → Mintzberg ordering ──
  console.log('\n3. Lewin → Mintzberg chain ordering');
  const lewin = worksheets.find((w) => w.theorist === 'Kurt Lewin');
  const mintzberg = worksheets.find((w) => w.theorist === 'Henry Mintzberg');
  assert(lewin.chainPosition < mintzberg.chainPosition, 'Lewin precedes Mintzberg in chain');

  // ── Worksheet content sections ──
  console.log('\n4. Worksheet content sections');
  const requiredSections = [
    '# Worksheet:',
    '## 1. Overview',
    '## 2. Learning Objectives',
    '## 7. Self-Assessment',
    '## 8. References',
  ];

  for (const ws of worksheets) {
    const wsPath = join(ROOT, ws.path);
    if (existsSync(wsPath)) {
      const content = readFileSync(wsPath, 'utf8');
      for (const section of requiredSections) {
        assert(content.includes(section), `${ws.id}: contains "${section}"`);
      }
    } else {
      assert(false, `${ws.id}: worksheet file exists (missing file cannot have sections)`);
    }
  }

  // ── CHG chain coverage ──
  console.log('\n5. CHG strategy_design chain coverage (CHG-03 through CHG-08, CHG-13)');
  const strategyChainRefs = worksheets.flatMap((w) => w.chgRefs);
  const expectedChain = ['CHG-03', 'CHG-04', 'CHG-05', 'CHG-06', 'CHG-07', 'CHG-08', 'CHG-13'];
  for (const ref of expectedChain) {
    assert(strategyChainRefs.includes(ref), `CHG chain: ${ref} covered`);
  }

  // ── People shelf consistency CHGs ──
  console.log('\n6. People shelf consistency CHGs (CHG-02, CHG-09, CHG-10)');
  const shelfRefs = slice.slice.peopleShelfBriefing?.chgRefs ?? [];
  for (const ref of ['CHG-02', 'CHG-09', 'CHG-10']) {
    assert(shelfRefs.includes(ref), `People shelf consistency: ${ref} covered`);
  }

  // ── Summary ──
  console.log(`\n=== People Subject Test Results ===`);
  console.log(`Pass: ${pass}`);
  console.log(`Fail: ${fail}`);
  console.log(`People subject integrity: ${fail === 0 ? 'VALID' : 'INVALID'}`);

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error('People test crashed:', e);
  process.exit(2);
});