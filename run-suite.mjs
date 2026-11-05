/**
 * Full test suite runner for People & Organization → Strategy and Design worksheets.
 *
 * Runs in order:
 *  1. tests/guard-test.mjs          — every People worksheet carries a before briefing
 *  2. tests/registration-test.mjs   — worksheet registration integrity
 *  3. tests/people-test.mjs         — People subject tests
 *  4. tests/product-subject-test.mjs — product subject tests
 *  5. wiring/chg-15-probe.mjs       — CHG-15 wiring path (drift + reachability)
 *
 * Usage: node run-suite.mjs
 */

import { execFileSync } from 'node:child_process';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = __dirname;

const TESTS = [
  { name: 'Guard test', file: join(ROOT, 'tests', 'guard-test.mjs') },
  { name: 'Registration test', file: join(ROOT, 'tests', 'registration-test.mjs') },
  { name: 'People subject test', file: join(ROOT, 'tests', 'people-test.mjs') },
  { name: 'Product subject test', file: join(ROOT, 'tests', 'product-subject-test.mjs') },
  { name: 'CHG-15 wiring probe', file: join(ROOT, 'wiring', 'chg-15-probe.mjs') },
];

let totalPass = 0;
let totalFail = 0;
let allPassed = true;

for (const t of TESTS) {
  console.log(`\n${'='.repeat(60)}`);
  console.log(`RUNNING: ${t.name}`);
  console.log(`${'='.repeat(60)}`);

  try {
    const result = execFileSync('node', [t.file], {
      encoding: 'utf8',
      cwd: ROOT,
      maxBuffer: 10 * 1024 * 1024,
    });
    console.log(result);

    // Parse pass/fail from output
    const passMatch = result.match(/Pass:\s*(\d+)/);
    const failMatch = result.match(/Fail:\s*(\d+)/);
    if (passMatch) totalPass += parseInt(passMatch[1], 10);
    if (failMatch) {
      const f = parseInt(failMatch[1], 10);
      totalFail += f;
      if (f > 0) allPassed = false;
    }
  } catch (e) {
    console.log(`TEST RUNNER ERROR: ${t.name} failed to execute`);
    console.log(e.stdout ? e.stdout.toString() : '');
    console.log(e.stderr ? e.stderr.toString() : '');
    allPassed = false;
    totalFail++;
  }
}

console.log(`\n${'='.repeat(60)}`);
console.log(`FULL SUITE RESULTS`);
console.log(`${'='.repeat(60)}`);
console.log(`Total pass: ${totalPass}`);
console.log(`Total fail: ${totalFail}`);
console.log(`Overall: ${allPassed ? 'ALL TESTS PASSED' : 'SOME TESTS FAILED'}`);

process.exit(allPassed ? 0 : 1);