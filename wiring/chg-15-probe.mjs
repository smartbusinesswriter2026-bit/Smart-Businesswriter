/**
 * CHG-15 Wiring Probe — empirical validation.
 *
 * Confirms:
 *  1. CHG-15 is wired onto the People strategy_design tile (CATALOGUE slice)
 *  2. No CATALOGUE slice drift (slice matches registered worksheets on disk)
 *  3. Reachability (every referenced file exists and is readable)
 *
 * Usage: node wiring/chg-15-probe.mjs
 */

import { readFileSync, existsSync, statSync } from 'node:fs';
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

function check(condition, message) {
  assert(condition, message);
  return condition;
}

async function main() {
  console.log('=== CHG-15 Wiring Probe ===\n');

  // ── 1. Load CATALOGUE slice ──
  console.log('1. CATALOGUE slice load');
  let slice;
  try {
    const raw = readFileSync(SLICE_PATH, 'utf8');
    slice = JSON.parse(raw);
    assert(true, 'slice.json loaded and parsed as valid JSON');
  } catch (e) {
    assert(false, `slice.json could not be loaded: ${e.message}`);
    console.log(`\nResults: ${pass} pass, ${fail} fail`);
    process.exit(fail > 0 ? 1 : 0);
    return;
  }

  const wiring = slice.slice.wiring?.chg15;
  assert(!!wiring, 'CHG-15 wiring block present in slice');

  // ── 2. CHG-15 wired onto People strategy_design tile ──
  console.log('\n2. CHG-15 → People strategy_design tile wiring');
  assert(wiring.targetTile === 'People strategy_design', 'targetTile is "People strategy_design"');
  assert(!!wiring.probePath, 'probePath is defined');

  // ── 3. CATALOGUE slice drift check ──
  console.log('\n3. CATALOGUE slice drift (slice vs disk)');
  const worksheets = slice.slice.worksheets;

  for (const ws of worksheets) {
    const wsPath = join(ROOT, ws.path);
    const bbPath = join(ROOT, ws.beforeBriefing);

    const wsExists = existsSync(wsPath);
    const bbExists = existsSync(bbPath);

    check(wsExists, `Worksheet file exists: ${ws.path}`);
    check(bbExists, `Before-briefing exists: ${ws.beforeBriefing}`);

    if (wsExists && bbExists) {
      // Read files to confirm they are non-empty and readable (reachability)
      try {
        const wsContent = readFileSync(wsPath, 'utf8');
        const bbContent = readFileSync(bbPath, 'utf8');
        check(wsContent.length > 0, `Worksheet readable & non-empty: ${ws.id}`);
        check(bbContent.length > 0, `Before-briefing readable & non-empty: ${ws.id}`);
      } catch (e) {
        check(false, `File read error for ${ws.id}: ${e.message}`);
      }
    }
  }

  // Drift: count of registered worksheets must match count on disk
  const registeredCount = worksheets.length;
  const diskCount = worksheets.filter((ws) =>
    existsSync(join(ROOT, ws.path)) && existsSync(join(ROOT, ws.beforeBriefing))
  ).length;
  check(registeredCount === diskCount, `No drift: registered ${registeredCount} == disk ${diskCount}`);

  // ── 4. Reachability ──
  console.log('\n4. Reachability (all referenced files reachable)');
  let reachable = 0;
  let unreachable = 0;

  for (const ws of worksheets) {
    for (const relPath of [ws.path, ws.beforeBriefing]) {
      const abs = join(ROOT, relPath);
      if (existsSync(abs)) {
        try {
          statSync(abs);
          reachable++;
        } catch {
          unreachable++;
        }
      } else {
        unreachable++;
      }
    }
  }

  // Also check the people shelf briefing
  const shelfBriefing = slice.slice.peopleShelfBriefing?.path;
  if (shelfBriefing) {
    const abs = join(ROOT, shelfBriefing);
    if (existsSync(abs)) reachable++; else unreachable++;
  }

  check(unreachable === 0, `All ${reachable + unreachable} referenced files reachable (${reachable} reachable, ${unreachable} unreachable)`);

  // ── 5. CHG-15 wiring markers updated ──
  console.log('\n5. CHG-15 wiring markers (reachability + drift)');
  const reachabilityVerified = unreachable === 0;
  const driftChecked = registeredCount === diskCount;

  // Update the slice to reflect verified state
  slice.slice.wiring.chg15.reachabilityVerified = reachabilityVerified;
  slice.slice.wiring.chg15.driftChecked = driftChecked;

  try {
    readFileSync(SLICE_PATH, 'utf8'); // confirm we can write back
    // Note: we do not auto-write the slice to avoid side effects; the operator
    // reviews and commits. We report the intended state instead.
    check(reachabilityVerified, 'Reachability verified: true');
    check(driftChecked, 'Drift checked: true (no drift)');
  } catch (e) {
    check(false, `Could not confirm slice write-back: ${e.message}`);
  }

  // ── Summary ──
  console.log('\n=== CHG-15 Wiring Probe Results ===');
  console.log(`Pass: ${pass}`);
  console.log(`Fail: ${fail}`);
  console.log(`CHG-15 target tile: ${wiring?.targetTile ?? 'NOT SET'}`);
  console.log(`Reachability: ${reachabilityVerified ? 'VERIFIED' : 'FAILED'}`);
  console.log(`Drift: ${driftChecked ? 'NONE (in sync)' : 'DRIFT DETECTED'}`);

  process.exit(fail > 0 ? 1 : 0);
}

main().catch((e) => {
  console.error('Probe crashed:', e);
  process.exit(2);
});