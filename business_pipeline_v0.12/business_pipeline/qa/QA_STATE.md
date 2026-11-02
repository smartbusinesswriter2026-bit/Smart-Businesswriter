# QA state

## Session 6 — `entrepreneurship` (2026-11-03, owner work order)

**Parameter.** `SUBJECT = entrepreneurship`, shelf 6 of 11. Opening commit `b2987fc`, build 1.68.
Closed at build 1.69.

**Inventory, confirmed against the live catalogue** (`GET /api/cases/subjects/entrepreneurship`
on 8001, then `subjects.detail`): **46 tools, 6 worksheets, 6 records, 0 theories** — as expected, so
no inventory defect. `docs/CURRICULUM_MAP.md` disagreed (it said 5 worksheets) — D-ENT-11.

**Opening state, measured.** `python -m unittest discover -s tests`: **2932 tests, 66 failures, 13
errors, 650 s** (`qa/baseline/ent_suite_out.txt` / `ent_suite_err.txt`, names in
`ent_baseline_failures.txt`). That is exactly the documented baseline; **none of the 79 named
failures belongs to entrepreneurship** — they are worksheet/framework-completion and one network
test, and they carry forward to their own shelves' sessions.

**Delivered.**

| Artefact | Content |
|---|---|
| `qa/manual/entrepreneurship.md` | eleven sections, 46 per-tool contract rows, **106 E-rows**, a traceability matrix, six declared gaps |
| `tests/test_subject_entrepreneurship_acceptance.py` | **106 tests**, one per E-row, offline, retrieval mocked, 12 hand recomputations |
| `qa/probe_ent_shelf.py` | every tool through its own preset: delivery, checks, determinism, units |
| `qa/probe_ent_plan.py` | the witness plan (with a marking guide) and the computation deliverable, judged against V-01…V-20 |
| `qa/probe_ent_mapping.py` | a plan block's columns through the core mapper, before and after D-ENT-02 |
| `qa/evidence/entrepreneurship/` | `business-plan.docx`, `business-plan-no-rubric.docx`, `computation-submission.docx`, `computation-workpapers.xlsx`, `validation.md` |

**Defects fixed, each with a trap test** (`qa/QA_DEFECTS.md` D-ENT-01…05, D-ENT-11):

- **D-ENT-04 — BLOCKER.** Eight presets that declare no period delivered *nothing*:
  `reference failure: RefMismatch('token wants n/None, artifact is n/None')`, and `pearson` crashed.
  Three of the eight are this shelf's (Trend forecast, Descriptive statistics, Chi-square). Fixed in
  the artifact layer and at the template call. **46 of 46 tools deliver now** (43 before).
- **D-ENT-01 — MAJOR.** A marking guide could not reach the business plan at all (`chat.start` had no
  `rubric`); the plan is a second engine and the guide had been wired into the worksheet path only.
- **D-ENT-02 — MAJOR.** A plan block's list columns were refused by the core mapper for the shape the
  plan itself asks for.
- **D-ENT-03 — MAJOR.** A word-budget line in a list rubric became a weighted criterion, and
  "Referencing" never matched "References" — both block a finished paper for ever.
- **D-ENT-05 — MINOR.** The engine that read a scanned brief reached the record but not the caller or
  the page.

**Declared, not built** (G-ent-01…06 / D-ENT-06…10): term sheets, liquidation preference,
anti-dilution, multi-round cap tables, conjoint, survival models, Monte Carlo; 36 tools with no
`need` text; no theory row by design; no dataset picker on the plan form (B-192's open surface);
`case`/`unsupported` presets are fixtures.

**Gates at close.**

| Gate | Result | Evidence |
|---|---|---|
| `python -m pytest tests/test_subject_entrepreneurship_acceptance.py -q` | **106 passed** | `qa/baseline/ent_acceptance.txt` |
| the shelf's own suites (`test_entrepreneurship`, `test_entrepreneurship_planning`, `test_business_plan_core`, `test_business_plan_profile`, `test_plan_verifier`, `test_plan_replay`, `test_export_downloads`) | **164 passed** | this session's runs; `ent_slice.txt` |
| the shared-worksheet slice (`-k "strategic or mkt or worksheet"`) | **119 passed, 2 failed** — both `test_marketing_worksheets` and both in the historical set; not this shelf's. (`test_strategic_positioning_completion` was in the opening set and has since been repaired by the framework-profile lane.) | `ent_worksheets.txt` |
| `python -m unittest discover -s tests` (inside `scripts/ci.py`) | **3038 tests, 40 failures, 6 errors** — **0 names absent from the opening baseline**, **33 gone** (79 → 46). The 33 are another lane's repairs to `framework_profiles.py` and its tests; this session's own fix removed no name from the set because the eight period-less presets were never exercised by a delivery test | `qa/baseline/ent_ci_err.txt`, `ent_baseline_failures.txt` → `ent_final_failures.txt`, `ent_repaired.txt` |
| `python scripts/ci.py` | **2 of 3 steps passed**: unit tests FAIL on the 46 historical problems; `shelf audit and frozen contract` **PASS**; `page syntax` (node `--check`) **PASS** | `qa/baseline/ent_ci_out.txt` |
| `python scripts/econ_shelf.py --check` | **frozen fixture: in sync** | `qa/baseline/ent_econ_shelf.txt` |
| `python qa/_count.py` | **SUITE_COUNT 3038** (2932 + 106) | `qa/baseline/ent_count.txt` |
| `python qa/check_page_syntax.py` | **page syntax: OK** | `qa/baseline/ent_page_syntax.txt` |
| `python qa/probe_duplicates.py` on the ten edited/read modules | **0 duplicate definitions** — the trap that has silently changed `chat.py` twice | `qa/baseline/ent_duplicates.txt` |
| `python scripts/ui_smoke.py --url http://127.0.0.1:8003` | **0 failure(s)**, including "business plan drafts with no missing input" and "business plan exports its submission" | `qa/baseline/ent_ui_smoke.txt` |
| live click-through, 46 tiles + the plan's marking-guide path, on 8003 | **0 failure(s)**: 46 of 46 tools delivered, the coverage table sits before the references, an unaddressed criterion blocks at 409, the gate is accepted, and the paper then downloads | `qa/evidence/entrepreneurship/clickthrough.json` / `.md` |
| `python -m pytest tests/test_docs_sync.py -q` | **7 passed** | `qa/baseline/ent_docsync.txt` |

**Why 8003 and not 8001.** The 8001 process (PID 9512) was started before this session's changes and
belongs to another lane; killing it would have interrupted them. The live gates therefore ran on a
fresh instance of the current code on 8003 (`ent_server_pid.txt`), and the served page on 8001 was
smoked separately. Nothing in `web/index.html` is cached by the server — it is read per request — so
the page coverage applies to both.

**Next subject: `operations` (shelf 7 of 11).** Its top three risks, measured from this session:

1. **Eleven T4 worksheets share the supply-chain shelf** (`OPS-01`…`OPS-08`, `OPS-10`…`OPS-12`); each
   belongs to two shelves and must be fixed once. The marketing worksheet registration failures
   (`test_marketing_worksheets`, in the historical set) are the same class and will be met again.
2. **The no-period defect's blast radius was eight presets**; the operations tools carry more list
   inputs than any other shelf, so run `qa/probe_ent_shelf.py`'s pattern over them first — it found
   D-ENT-04 in one pass after two sessions had missed it.
3. **The plan profile is a second engine** and the lesson generalises: any feature wired into the
   conductor must be proved on the *plan* path too. The four profiles share `chat.draft`, so a rubric
   now reaches all four; nothing else is yet proved there.

## Session R — the rubric lane (2026-11-02, owner instruction)

**Ask.** "a rubric to be uploaded which should be followed in writing the paper".

**Built.** `src/bp/product/rubric.py` (reader + coverage), binding in `completion.complete`/`draft`,
the export gate in `paper.missing`/`check`, the upload path (`intake.ROLES` + `use_as_rubric`,
`POST /api/intake/{id}/rubric`, the **Use as the rubric** button, and `rubric` travelling with
`/api/cases/frameworks/complete` so the report 409s while a weighted criterion is unaddressed),
`qa/manual/rubric.md` (35 E-rows), `tests/test_product_rubric.py` (35 tests), `qa/probe_rubric.py`,
`qa/_count.py`, `qa/check_page_syntax.py`. Decision **B-187** (B-186 was taken concurrently).

**Commits.** `ff3f58d` (reader) · `eb204d1` (coverage, appendix, gate).

**Gates at close.** `tests.test_product_rubric` 29 OK · `tests.test_docs_sync` 7 OK (count 2902 in sync)
· framework-completion slice 61 failed / 521 passed with **0 names absent from the recorded baseline**
(historical, other shelves) · paper/session/export/sample-papers 68 passed · rubric+ansoff+drafting+
honesty+method-contracts 64 passed · `scripts/econ_shelf.py --check` **frozen fixture: in sync**.
No frozen core, method, preset, input, check, number, route family or paper rule changed; no new
dependency; no network or model call.

**Open (declared, not silently dropped).** No upload role/button for a rubric; no section injection
(a rubric heading the profile lacks is a named gap, never an empty section); OCR chain not built;
the engine never writes a recommendation (B-154), so a rubric demanding one gets a gap.

**Found and fixed this lane.** D-RUB-01 (weight regex dropped every `%` weight), D-RUB-02 (lead-in
line read as a criterion), D-RUB-03 (`qa/_count.py` under-reported by 2), D-RUB-04 (unreadable rubric
was validated after the research run), D-RUB-05 (self-inflicted UTF-8 double-decode in five docs,
repaired and verified). Full detail in `qa/manual/rubric.md` §6.

**Coordination hazard, recorded for the next session.** Three lanes write in this worktree at once:
one lane committed some of this lane's in-flight doc text under its own message, and staged a broad
set (`git add`) that included this lane's source files. Every commit here was made with an explicit
pathspec so no other lane's work was bundled; the three count docs were left to the lane holding them
and are in sync again. Never edit docs with `Get-Content -Raw`/`Set-Content` on Windows PowerShell
5.1 — it double-decodes UTF-8.



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


---

# Session 2 — `economics` (2026-11-02/03) · commits `8bd1e9f`, `6e20fc4`

*This section was written once and then lost when another lane rewrote this file; it is re-appended
at the end rather than edited in place.*

**Subject chosen by the owner.** The recorded order said `finance` next; the owner's work order
named `economics` and the owner confirmed it when asked, noting `finance` is being fixed in another
session. `finance` is deliberately skipped and remains not started.

## Baseline (Phase 0) — measured, not assumed

`ab0be0d`: **2627 tests, 66 failures, 13 errors, 634.8 s**
(`qa/baseline/2026-11-02-ab0be0d-suite-err.txt`). **None of the 79 named failures belongs to
economics** — all are worksheet/framework-completion plus one network test, and they carry forward
to their own shelves' sessions.

## Delivered

| Artefact | Content |
|---|---|
| `qa/manual/economics.md` | The shelf's missing acceptance manual: 10 sections, **59 generated per-tool contract rows**, **84 E-rows**, scoreboard, declared gaps |
| `tests/test_subject_economics_acceptance.py` | **83 tests** (59 generated per tool, 24 cross-cutting), incl. 23 worked examples recomputed by hand from the student guide |
| `qa/probe_econ_*.py`, `qa/build_econ_manual.py` | The reproducible evidence behind every claim in the manual |
| `qa/baseline/econ_*` | Raw measurements |

**Result:** all **59 tools** deliver through their own preset, every method's own checks pass, every
computation is deterministic, and every reproduced guide example matches hand arithmetic. The
shelf's arithmetic layer is sound.

## Defects — `qa/QA_DEFECTS.md` D-ECO-01…09

- **FIXED (B-190):** D-ECO-01 `labour` typed a share and a ratio as money; D-ECO-03 the currency
  paper printed its source amount with the target currency. Both with trap tests.
- **FIXED (docs):** D-ECO-08 `CURRICULUM_MAP.md` said 55 tools; the catalogue has 59.
- **BLOCKED:** D-ECO-02 tightness = `vacancies / unemployment_rate` (a count ÷ a rate). Owner rules
  the replacement is a modelling decision and the absent-denominator case must refuse with a named
  gap. E-eco-082.
- **GAP:** G-eco-01…04 (52 tools without `need` text; no worksheets by design; VAR/cointegration
  parked; diagram renderer not built).
- **CLOSED, not reproducible:** D-ECO-09 (session 1's `tax_incidence` units claim) — B-179 fixed the
  duplicated hooks.

**Two false alarms retired rather than written up:** `@unit` and a `None` `typing` hook are handled
by `orchestrator.py` (227, 233-234, 270); all 151 `related` ids resolve (131 local, 20 cross-shelf).

## Gates (closing)

**93 passed** across the economics acceptance suite, `test_docs_sync.py` and
`test_frozen_contract.py` (`qa/baseline/final_gates.txt`). Documented count re-measured to **2910**.
`scripts/econ_shelf.py --check`: **frozen fixture: in sync**.

## Still uncommitted (owner's condition b)

`docs/DECISIONS.md` (the **B-190** row), `docs/CHANGELOG.md`, `docs/WORKLOG.md`, `docs/HOME.md`,
`docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, `qa/QA_STATE.md`, `qa/QA_DEFECTS.md` — written on disk,
held back because another lane has uncommitted edits in them. Follow-up:

```
git commit -m "docs(economics): B-190 decision row, CHANGELOG/WORKLOG entries, count 2910 - session 2 of 11" -- \
  business_pipeline_v0.12/business_pipeline/docs/DECISIONS.md \
  business_pipeline_v0.12/business_pipeline/docs/CHANGELOG.md \
  business_pipeline_v0.12/business_pipeline/docs/WORKLOG.md \
  business_pipeline_v0.12/business_pipeline/docs/HOME.md \
  business_pipeline_v0.12/business_pipeline/docs/HANDOFF.md \
  business_pipeline_v0.12/business_pipeline/docs/CONTRIBUTORS.md \
  business_pipeline_v0.12/business_pipeline/qa/QA_STATE.md \
  business_pipeline_v0.12/business_pipeline/qa/QA_DEFECTS.md
```

## Definition of done — §8

Manual complete ✔ · scoreboard 83 PASS / 1 BLOCKED / 0 DISPUTED ✔ · suite passes with no skipped or
loosened assertion ✔ · no unexplained BLOCKER/MAJOR ✔ · frozen contract unchanged and in sync ✔ ·
gates green ✔ · deliverable produced through the real path ✔ · **click-through on port 8001 NOT run**
(no server started; page coverage is the Python contract tests) ✘ — recorded, not claimed.

## Next action

**Session 3 — `finance`.** Three risks, measured here: (1) the unit audit in
`qa/probe_econ_tools.py` (`suspicious()`) found `labour_market` in one pass — run it first on
finance's 35 tools, which mix ratios and money far more; (2) template wording can contradict correct
arithmetic and no numeric check catches it (`qa/probe_econ_reports.py` is that harness); (3) another
lane is live in this worktree — check `git status` before and after every commit and use path-scoped
commits.

