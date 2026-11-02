# QA state

**Session:** 2 of 11 · **Subject:** `finance` · **Branch:** `corpus/merge-v1`
**Opening commit:** `ab0be0d` (build 1.58 per `docs/HOME.md` and the newest numbered `docs/CHANGELOG.md` entry)
**Written:** 2026-11-02 (this session)

Session 1 (`accounting`, opening `97544f7`) is closed. Its record is kept verbatim at
`qa/baseline/QA_STATE_session1.md`, its manual is `qa/manual/accounting.md`, and its ledger rows are
`D-ACC-*` in `qa/QA_DEFECTS.md`.

## 1. Baseline (Phase 0) — red, and expected to be red

| Measure | Documented baseline | Session 1 closing | Measured this session |
|---|---|---|---|
| Tests executed (`unittest discover -s tests`) | ~2553 | 2627 | **2630** |
| Failures | ~84 | 66 (on `scripts/ci.py`) / 68 (raw run) | **66** |
| Errors | ~12 | 13 | **13** |
| Wall time | — | — | 626 s |

Raw log: `qa/baseline/s2-suite-out.txt` / `s2-suite-err.txt`; summary `qa/baseline/s2-summary.txt`;
failure names `qa/baseline/s2-failures.txt`.

**Failure-set diff against session 1's closing set (`qa/baseline/ci_failure_list.txt`):** 79 distinct
names at the opening, 77 at the close — **0 new names, 2 repaired**.

- **GONE:** `test_pipeline.T.test_no_method_is_framework_only` — repaired when the core pass landed
  **B-181** ("an unknown method name fails closed") in `4e842f0` and replaced that test with it.
- **GONE:** `test_finance_additions.StudentFacingContract.test_the_finance_page_groups_tools_and_carries_study_notes`
  — repaired by this session (D-FIN-06).

The identical-name diff is `qa/baseline/s2-failures.txt` versus `qa/baseline/fin_ci_failures.txt`.


**The tree was dirty when this session opened, and it changed underneath it.** At the opening `git status`
held the B-179/B-180/B-181 implementation (`src/bp/methods.py` typing hooks, `orchestrator.py`,
`product/guard.py`, three lines of `product/chat.py`) plus the accounting leftovers. `docs/DECISIONS.md`
records B-179/B-180/B-181 as **PROVISIONAL (owner instruction, 2026-11-02 — unfreeze approved)** and the
CHANGELOG's top entry is the same work, so that was an owner-approved change that was half-landed. The
core pass committed it at 19:53 (`4e842f0`) and its closing measurement at 19:54 (`3988bb0`) while this
session was running. Nothing was reverted, and this session's commits stage only its own paths.

**A second session was working on the `economics` shelf in this same worktree throughout.**
`qa/manual/economics.md`, `tests/test_subject_economics_acceptance.py`, `qa/probe_econ_*.py` and the
`D-ECO-*` ledger rows are that session's, not this one's. Consequently `qa/QA_DEFECTS.md` temporarily
carries **two sections numbered "Session 2"**; this session's is `Session 2 — finance` and the other is
`Session 2 — economics`, and the collision is recorded here rather than silently renumbered. It also
means `scripts/ci.py` ran while that shelf's tests were in flux — see §2.1.

## 2. Gates

| Gate | Result | Evidence |
|---|---|---|
| `python -m unittest discover -s tests` (opening) | 2630 tests, 66 failures, 13 errors | `qa/baseline/s2-suite-err.txt` |
| `python -m pytest tests/test_subject_finance_acceptance.py -q` | **50 passed** | `qa/baseline/fin_acceptance.txt` |
| Finance slice of the existing suite (9 files) | **147 passed** | `qa/baseline/fin_slice1.txt` |
| Guard set (method contracts, product subjects, catalogue truth, honesty, session API, web inline script, cache headers, product boundary, sample papers, docs sync, frozen contract, drafting) | **129 passed, 1 failed** — only the documented-count test, repaired in this session; `test_docs_sync.py -q` → **7 passed** | `qa/baseline/fin_guards.txt`, `fin_docsync.txt` |
| `python scripts/econ_shelf.py --check` | **frozen fixture: in sync** (142 methods, 144 presets) | `qa/baseline/fin_econ_shelf.txt` |
| `python scripts/ui_smoke.py --url http://127.0.0.1:8001` | **0 failure(s)** | `qa/baseline/fin_ui_smoke.txt` |
| Live click-through, 35 finance tiles on 8001 | **0 failure(s)**: 33 delivered, 1 known-blocked (`dcfmid`, D-FIN-01), 1 no-preset (`ols_robust`, G-fin-05) | `qa/evidence/finance/clickthrough.json` / `.md` |
| `python scripts/ci.py` | **2 of 3 steps passed**: `unit tests` FAIL — 2761 tests, 64 failures, 13 errors, but **0 new failure names** against the opening set; `shelf audit and frozen contract` PASS; `page syntax` (node `--check`) PASS | `qa/baseline/fin_ci_out.txt`, `fin_ci_err.txt`, `fin_ci_failures.txt` |

### 2.1 Note on the CI run

`scripts/ci.py` was started after the core pass committed B-179…181 and while the `economics` session was
still editing its own tests, so its "2761 tests" includes this session's +50 and that shelf's additions.
The number that matters for the definition of done is the **failure-name set**, not the count: 77 names
at the close against 79 at the opening, with nothing added (the diff is in §1). The failing names are the
historical carried-forward set — worksheet/profile/prompt failures on other shelves — listed in
`qa/baseline/fin_ci_failures.txt`. None is on the finance shelf.


## 3. Subject inventory (measured, not assumed)

| Measure | Work order (2026-11-02) | Measured this session | Match |
|---|---|---|---|
| Tools | 35 | **35** | yes |
| Worksheets | 0 | **0** | yes |
| Records | 23 | **23** (8 `computed`, 15 `read_only`) | yes |
| Theories | 0 | **0** | yes |
| Glossary | (not stated) | **22** | recorded |
| Tiles (`detail["tiles"]`) | (not stated) | **0** by design: `subjects.SUBJECT_TILES` names only people/economics/management | recorded |
| Tools with a preset | (not stated) | **34** (33 frozen-method tools + the `case_decision` template); `ols_robust` has none (G-fin-05) | recorded |
| Tools without `need` text | (not stated) | **25** (G-fin-07) | recorded |

`GET /api/cases/subjects/finance` serves the same 35 tools and 23 records (click-through evidence).

## 4. Traceability scoreboard (this session's result)

`qa/manual/finance.md` §8 defines 50 `E-fin-nnn` rows; each is enforced by the test of the same number.

| Rows | Result |
|---|---|
| E-fin-001…004 | PASS |
| E-fin-005 | **GAP** G-fin-05 (`ols_robust` has no preset; frozen `PRESETS`) |
| E-fin-006 | PASS |
| E-fin-007 | PASS — D-FIN-01 fixed by **B-183** (the mid-year tile delivers) |
| E-fin-008…025 | PASS |
| E-fin-026…036 | PASS |
| E-fin-037 | **GAP** G-fin-07 (25 tools have no `need` text) |
| E-fin-038…050 | PASS |
| **Total** | **48 PASS, 0 BLOCKED, 2 GAP — 0 unexplained** |

## 5. Open decisions for the owner (do not invent a default)

| # | Decision needed | Evidence | Ledger |
|---|---|---|---|
| 1 | ~~Unfreeze `src/bp/methods.py::_dcf_tests`~~ — **CLOSED**: the owner approved the unfreeze ("okay go. unfreeze and finish it") and **B-183** landed the one-line fix; the `dcfmid` tile now delivers | `qa/probe_dcf_midyear.py`: six checks pass on both conventions; `econ_shelf.py --check` still "in sync" | D-FIN-01 (FIXED) |
| 2 | ~~Land the in-flight B-179/B-180/B-181 implementation and align `test_pipeline`~~ — **closed by the core pass**: `4e842f0` landed the unfreezes and replaced `test_no_method_is_framework_only`; the failure is gone from the closing set (D-FIN-13) | `docs/DECISIONS.md` B-179…181; `git log 4e842f0` | D-FIN-13 (CLOSED) |
| 3 | Should `ols_robust` get a preset? `server.PRESETS` is part of the frozen 144, so it needs an unfreeze | `tool("ols_robust")["preset"] is None` | D-FIN-08 / G-fin-05 |
| 4 | Should the calculator router's match threshold be lowered so "price this bond" reaches `bond_analysis`? The threshold is shared by all 11 shelves | `qa/baseline/fin_router2.txt` | D-FIN-12 |

## 6. Commit status — read this before committing anything

**Landed:** `d871503` — `fix(finance): the paper prints money, and the shelf finally has a manual and a
suite` (58 files: the manual, the suite, the probes and evidence, `src/bp/product/chat.py`,
`tests/test_finance_additions.py`, the six docs, `qa/QA_STATE.md`, `qa/QA_DEFECTS.md`).
Post-commit verification: `tests/test_subject_finance_acceptance.py tests/test_finance_additions.py
tests/test_docs_sync.py` → **80 passed** (`qa/baseline/fin_post_commit.txt`).

Committed finance only — **explicit paths, never `git add qa`**, because another session's economics
manual/suite/probes live in the same tree:


```
git add business_pipeline_v0.12/business_pipeline/qa/manual/finance.md \
        business_pipeline_v0.12/business_pipeline/qa/QA_STATE.md \
        business_pipeline_v0.12/business_pipeline/qa/QA_DEFECTS.md \
        business_pipeline_v0.12/business_pipeline/qa/evidence/finance \
        business_pipeline_v0.12/business_pipeline/qa/audit_finance.py \
        business_pipeline_v0.12/business_pipeline/qa/clickthrough_finance.py \
        business_pipeline_v0.12/business_pipeline/qa/manual_finance_tables.py \
        business_pipeline_v0.12/business_pipeline/qa/probe_dcf_midyear.py \
        business_pipeline_v0.12/business_pipeline/qa/probe_finance_*.py \
        business_pipeline_v0.12/business_pipeline/qa/probe_fixtures.py \
        business_pipeline_v0.12/business_pipeline/qa/probe_router.py \
        business_pipeline_v0.12/business_pipeline/qa/summarise_finance_*.py \
        business_pipeline_v0.12/business_pipeline/qa/baseline/fin_* \
        business_pipeline_v0.12/business_pipeline/qa/baseline/s2-* \
        business_pipeline_v0.12/business_pipeline/qa/baseline/QA_STATE_session1.md \
        business_pipeline_v0.12/business_pipeline/tests/test_subject_finance_acceptance.py \
        business_pipeline_v0.12/business_pipeline/tests/test_finance_additions.py \
        business_pipeline_v0.12/business_pipeline/src/bp/product/chat.py \
        business_pipeline_v0.12/business_pipeline/docs/{CHANGELOG,WORKLOG,HOME,HANDOFF,CONTRIBUTORS,CURRICULUM_MAP}.md
```

`src/bp/product/chat.py` also carries the three lines of **B-180** wiring that were already in the tree
when this session opened; that is stated in the commit message rather than hidden. Everything else in the
file is this session's D-FIN-02 fix.

**Not committed, deliberately:** the `economics` session's files (`qa/manual/economics.md`,
`tests/test_subject_economics_acceptance.py`, `qa/probe_econ_*.py`, `qa/build_econ_manual.py`, the `D-ECO-*`
ledger rows and its `qa/baseline/*` logs), the accounting leftovers, and the owner's `M SERVING.md` /
`_baseline_wt`.

## 7. Next action

**Session 3 — `economics`.** A concurrent pass has already produced `qa/manual/economics.md`,
`tests/test_subject_economics_acceptance.py` and the `D-ECO-*` ledger rows in this worktree, so session 3
starts from *their* closing state, not from a blank shelf. Top three risks, measured from this session:

1. **Two sessions share one worktree.** Before staging anything, run `git status` and `git log -3` and
   stage explicit paths only — `git add qa` would sweep another shelf's manual, suite and probes into the
   wrong commit. This session hit exactly that trap.
2. **The economics shelf is the largest tool set (59)** and `SUBJECT_TILES["economics"]` makes it one of
   only three tile shelves, so its page surface is richer than finance's: the tile → tool routing needs
   the click-through treatment, and `_tiles()` groups by `tool["group"]`, which is populated for all 59.
3. **Three of the work order's named first defects are economics'** (labour-market tightness denominator,
   tightness serialisation, the `icer_{slug}` key). `D-ECO-01…03` already record two of them as
   MAJOR; verify whether they were fixed or ledgered before re-opening them, and check the frozen core
   before writing any formula fix.

