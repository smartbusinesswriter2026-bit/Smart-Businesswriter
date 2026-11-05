/**
 * Guard test: every People worksheet carries a `before` briefing.
 *
 * Invariant: For every worksheet registered in the CATALOGUE slice under the
 * People and Organization → Strategy and Design shelf, a paired
 * before-briefing.md must exist in the same directory and be non-empty.
 *
 * Usage: node tests/guard-test.mjs
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
  console.log('=== Guard Test: Every People worksheet carries a before briefing ===\n');

  // Load slice
  let slice;
  try {
    const raw = readFileSync(SLICE_PATH, 'utf8');
    slice = JSON.parse(raw);
  } catch (e) {
    console.log(`  FAIL: Could not load CATALOGUE slice: ${e.message}`);
    console.log(`\nResults: ${pass} pass, ${fail} fail`);
    process.exit(1);
    return;
  }

  const worksheets = slice.slice.worksheets;
  console.log(`Found ${worksheets.length} worksheet(s) in CATALOGUE slice\n`);

  for (const ws of worksheets) {
    const wsPath = join(ROOT, ws.path);
    const bbPath = join(ROOT, ws.beforeBriefing);

    // Worksheet file must exist
    assert(existsSync(wsPath), `${ws.id}: worksheet file exists (${ws.path})`);

    // Before briefing must exist
    const bbExists = existsSync(bbPath);
    assert(bbExists, `${ws.id}: before-briefing exists (${ws.beforeBriefing})`);

    if (bbExists) {
      // Before briefing must be non-empty
      try {
        const bbContent = readFileSync(bbPath, 'utf8');
        assert(bbContent.trim().length > 0, `${ws.id}: before-briefing is non-empty`);
      } catch (e) {
        assert(false, `${ws.id}: before-briefing readable (${e.message})`);
      }
    }

    // Before briefing must reference CHG items (People shelf consistency)
    if (bbExists) {
      try {
        const bbContent = readFileSync(bbPath, 'utf8');
        const hasChgRef = /CHG-\d+/g.test(bbContent);
        assert(hasChgRef, `${ws.id}: before-briefing references CHG item(s)`);
      } catch {
        assert(false, `${ws.id}: before-briefing contains CHG reference`);
      }
    }
  }

  // People shelf briefing must exist
  const shelfBriefing = slice.slice.peopleShelfBriefing?.path;
  if (shelfBriefing) {
    const shelfPath = join(ROOT, shelfBriefing);
    assert(existsSync(shelfPath), 'People shelf before-briefing exists (CHG-02/09/10)');
    if (existsSync(shelfPath)) {
      const content = readFileSync(shelfPath, 'utf8');
      assert(content.trim().length > 0, 'People shelf before-briefing is non-empty');
    }
  } else {
    assert(false, 'People shelf before-briefing path defined in slice');
  }

  // Summary
  console.log(`\n=== Guard Test Results ===`);
  console.log(`Pass: ${pass}`);
  console.log(`Fail: ${fail}`);
  console.log(`Invariant "every People worksheet carries a before briefing": ${fail === 0 ? 'HELD' : 'VIOLATED'}`);

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error('Guard test crashed:', e);
  process.exit(2);
});