# Health Program Spec — Smart BusinessWriter Pipeline

**Status:** Step 2 locked (spec). Step 3 task breakdown below. Step 4 build not started.
**Owner (decision):** Beam drafted; implementation split per ownership rules (see §6).
**Last updated:** 2026-11-10
**Companion docs (read first):** `business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md`,
`CONDUCTOR_MANUAL.md`, `docs/CAUSE_LOOP.md`, `plans/eval-spec.md`.

---

## 1. Purpose

Build a health check that **tells the owner accurately what is wrong** with the
pipeline, names the failure, logs it once, and never acts on its own. A pipeline
can be perfectly up while its corpus is down, its cases are failing, and its
repair loop is idle — the existing `/api/health` reports the server, not the
pipeline. This program closes that gap.

The eval program measures *whether the pipeline is correct*. This program
measures *whether the pipeline is alive and honest*: are its stores readable, are
its cases green, is its corpus reachable, is its repair loop actually repairing,
is its retrieval running, and is its own test suite green.

## 2. Non-negotiables (inherited)

- No invented evidence, sources, numbers or citations.
- A missing signal is a **named gap**, never a green. A check that cannot be
  run reports `degraded` with a reason, not `ok`.
- Stdlib only at runtime (`sqlite3`, `urllib`, `json`, `os`).
- No weakening of any existing check to get green.
- The health check **never starts anything**. It reports; the switches on the
  Loops tab decide what runs. A panel that starts a loop is a loop with a UI,
  which is the opposite of the "off by default" rule.
- The health check **never acts**. It never repairs, never applies a gap, never
  writes outside its own store.

## 3. Scope — one computation, one surface

### In scope (computation lane)
- A `health()` function that returns a list of named checks, each with its own
  verdict, plus one overall bit.
- Each check carries its own `checked_at` timestamp; the panel shows the age.
- A failure is logged once, into the existing ops log, under a new lane
  `pipeline-health`. A check that fails twice in a row is one issue, not two.
- A `health()` that a test can call without a server, a model, or a network
  beyond the corpus probe.

### Out of scope (design lane)
- The panel that renders it, the route that serves it, and any button it
  carries.
- Any automatic remediation.

### Not in scope at all
- A numeric health score. A percentage of checks that pass is a metric that
  invites turning off the checks you cannot pass.
- A new data store. Every signal already exists; the health check only reads.
- Continuous monitoring on every request. The check runs on demand; a scheduled
  background sweep is opt-in via a switch.

## 4. The checks

Each check returns `{name, ok, severity, reason, checked_at, ...}`. The
overall bit is `ok` only when **every check that matters is ok**.

| # | Check | Source | Ok when |
|---|---|---|---|
| H1 | server up | the process is answering | always (the check itself ran) |
| H2 | case store readable | `ops.state_dir()` / `case_store.summary()` | the store returns a count, not `null` |
| H3 | case pass rate | the latest case-run manifest (or a fresh replay of one case per subject) | open tile-case errors are within the budget (≤2 pipeline failures; invalid fixtures reported separately, never against the budget) |
| H4 | no regressions | `eval_runner.regressions(run_id)` | empty |
| H5 | corpus reachable | `eval_runner.corpus_available()` | the index answers `/health` |
| H6 | repair loop honest | `autoresearch.status()` + `cause_ledger.summary()` | if open pipeline causes exist, the loop is running *or* a switch is explicitly off; an idle loop with an open queue is not ok |
| H7 | causes | `cause_ledger.summary()` | no cause is `recurring` |
| H8 | eval baseline fresh | the latest Direction 1 manifest | within the budget and no regressions, and newer than the last commit |
| H9 | test suite | the last stored result in `state/test_results/` | 100% pass |
| H10 | RRA | `relevance.status()` / latest run | the last run's controls held (or no run has been attempted yet, which is `ok` with a note) |
| H11 | model assistance | `/api/health` → `model_assistance` | reported (on or off), never a failure either way |
| H12 | self-heal switches | `ops_switches` | reported; an off switch is a reason, not a failure |

**The corpus is a hard gate.** A down corpus degrades overall health even when
everything else is green, because RAG is `not_measured` when the index is down
(the eval program's rule, carried over).

## 5. Success criteria

- **Accuracy.** Every check's verdict is derived from a real signal, never
  from a constant. A check that cannot run returns `degraded` with a reason,
  not `ok`.
- **No false green.** The overall bit is `ok` only when every check that
  matters is `ok`. A missing corpus, a regression, or a recurring cause
  each degrades it on its own.
- **No false alarm.** An `invalid` fixture, an off switch, or an unrun RRA
  is reported and explained, not treated as a failure.
- **Logged once.** A check that fails twice in a row is one issue in the ops
  log, not two.
- **On demand.** The check runs when asked; nothing starts by itself.
- **No action.** The health check never starts a loop, never repairs, never
  applies a gap.
- **Provable.** A trap test per check, a browser check of the panel, and a
  security scan of the output.

## 6. Ownership

- **Computation lane (DeepSeek)** owns: `src/bp/product/health.py` (new),
  the `pipeline-health` lane in `ops_log`, the freshness rules, and the tests.
- **Design lane (MiniMax)** owns: the panel, the route `/api/ops/health`,
  the rendering of the age of each signal, and any button the panel carries.

Cross-domain features split into a computation commit then a design commit,
each with tests + CHANGELOG + WORKLOG.

## 7. Stack

- Runtime: Python 3.14, stdlib only. No new dependency.
- Reuse: `ops` (health, state_dir), `case_store`, `case_runner`,
  `eval_runner` (corpus_available, runs, regressions, summarise),
  `cause_ledger`, `autoresearch`, `relevance`, `ops_switches`, `ops_log`,
  `test_runner` (stored results), `build` (version).
- Storage: `state/health/` for the health record (a JSONL of `checked_at`
  + the check list), so a run can be compared with the previous one without
  re-running everything.
- Report: none of its own. The panel reads the record.

## 8. Open questions (locked from the interview)

| # | Question | Locked answer |
|---|---|---|
| Q1 | Shape of the report | A list of named checks with per-check verdicts, plus one overall bit. No percentage, no score. |
| Q2 | Cadence | On demand only. Nothing starts by itself. |
| Q3 | Logging | Yes, into `ops_log` under the lane `pipeline-health`. A check failing twice is one issue. |
| Q4 | Remediation | Never automatic. The panel reports; the owner acts via the switches. |
| Q5 | Freshness | Each signal carries its own `checked_at`; the panel shows the age. No single global window. |
| Q6 | Corpus gate | Yes. A down corpus degrades overall health. |
| Q7 | Ownership | Computation lane owns the checks and the verdict; design lane owns the panel and the route. |
| Q8 | New capability over the old panel | Read the eval manifest, the cause ledger, the RRA and the test suite - not just the case store. |
| Q9 | Proof | A trap test per check, a browser check of the panel, and a security scan. |

## 9. What this program does not do

- It does not repair anything. It names the issue and waits.
- It does not start a loop. The switches decide.
- It does not invent a number. Every verdict comes from a signal that already exists.
- It does not replace the eval program. The eval measures correctness; this
  measures liveness and honesty. The eval's baseline is one of this program's
  checks.

---

## Step 3 — Task breakdown

Each task: acceptance criteria + allowed file list. Skeleton:

- **H1 (computation):** `src/bp/product/health.py` (new) — the checks H1–H12,
  `health()` returning `{overall, checked_at, checks: [...]}`, and `health_record()`
  writing to `state/health/health.jsonl`. Allowed: `health.py`, tests.
  Traps: a check that cannot run returns `degraded` with a reason; the overall
  bit is `ok` only when every required check is `ok`; the corpus check is a
  hard gate; a signal with no data is `degraded`, not `ok`.
- **H2 (computation):** the `pipeline-health` lane in `ops_log`. A check that
  fails twice in a row is one issue. Allowed: `ops_log.py`, `health.py`, tests.
  Traps: the same failure is not logged twice; a check that recovers is logged
  as resolved (a new record, not a deletion).
- **H3 (computation):** the freshness rules. Each signal carries `checked_at`;
  the eval baseline is stale when it is older than the last commit; the test
  suite is stale when it is older than the last run. Allowed: `health.py`,
  tests. Traps: a missing signal is `degraded` with "never checked", never `ok`.
- **H4 (computation):** `health()` is callable without a server, a model, or
  any network beyond the corpus probe. Allowed: `health.py`, tests.
  Traps: calling it in a bare process returns a verdict, not an exception.
- **H5 (design):** the panel and the route `/api/ops/health`, reading the
  record and rendering the age of each signal. Allowed: `web/admin-sbw.html`,
  `src/bp/server.py` (additive).
- **H6 (design):** an explicit "start the repair loop" button that calls the
  existing switch — never an automatic start. Allowed: `web/admin-sbw.html`.
- **H7 (design):** browser check, security scan, simplify.

## Step 4 — Build (test-first)

Red → green, slice by slice: H1 → H2 → H3 → H4. Each slice: trap test red
first, then green. H5 and H6 land in the design commit that follows.

## Step 5 — Verify

- `python -m unittest discover -s tests` green, read the `OK` line.
- `scripts/econ_shelf.py --check` if core touched (it should not be).
- Agent opens the admin in a browser, checks security, simplifies the code.
- Trap test for every bug fixed; no edited expected values.
