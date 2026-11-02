# QA state

**Session:** 1 of 11 · **Subject:** `accounting` · **Branch:** `corpus/merge-v1`
**Opening commit:** `97544f7` (build 1.56 per `docs/CHANGELOG.md`'s newest numbered entry)
**Written:** 2026-11-02 (this session)

## 1. Baseline (Phase 0) — red, and expected to be red

| Measure | Documented baseline | Measured this session (opening) | Measured this session (closing) |
|---|---|---|---|
| Tests executed | ~2553 | **2548** | **2627** |
| Failures | ~84 | **86** | **68** on the closing full run, **66** on `scripts/ci.py` after the docs repair (the authoritative latest number) |
| Errors | ~12 | **13** | **13** |
| Framework-completion failures | ~55–62 | 61 of the 99 (see list) | 61 |

Raw logs: `qa/baseline/2026-11-02-97544f7-suite.txt` (opening, verbatim),
`qa/baseline/_after_err.txt` (closing), `qa/baseline/failure_list.txt` (opening names),
`qa/baseline/failure_list_after.txt` (closing names).

Count reconciliation (measured, not assumed): `unittest` discovery counts **2577** test cases
without this session's file and **2627** with it (+50). The opening run executed 2548 — 29 fewer
than its own loader count — so the honest comparison is on the failure **set**:

- **19 distinct tests repaired** (root causes D-ACC-01…05 and the docs drift),
- **1 newly red:** `test_sources.SearchTest.test_brave_failure_falls_back_to_firecrawl` —
  the network-dependent Brave→Firecrawl test named in `docs/OPEN_ISSUES.md`. It is
  intermittent; `python -m pytest tests/test_sources.py -q` → **28 passed** in isolation.
  Classified NETWORK/ENV; not deleted, not "fixed" by weakening.

Failure-set diff: `qa/baseline/failure_list.txt` vs `qa/baseline/failure_list_after.txt`.

**Variance between the three measurements, and why.** The opening run and the closing run agree on
the failure *set*; the raw counts differ for two reasons only:

- The closing full run (`qa/baseline/_after_err.txt`) started at 18:44, **before** the `HOME.md` /
  `DECISIONS.md` drift was repaired (18:50), so it still contains the two `test_docs_sync` failures.
  Its 68 = those 2 + the 66 below.
- `scripts/ci.py` ran at 18:59, after the repair: **66 failures** — the same set minus the two
  `test_docs_sync` tests, which pass (`pytest tests/test_docs_sync.py -q` → 7 passed,
  `qa/baseline/docs_sync_now.txt`). It still contains the intermittent Brave→Firecrawl test, which
  passed in isolation (`28 passed`).

`qa/baseline/ci_failure_list.txt` contains **zero** failure names that are not already in the
opening list.

## 2. Gates (Phase 0 and Phase 4)

| Gate | Result | Evidence |
|---|---|---|
| `python -m unittest discover -s tests` | **2627 tests, 68 failures, 13 errors** | `qa/baseline/_after_err.txt` |
| `python -m pytest tests/test_subject_accounting_acceptance.py -q` | **50 passed, 119 subtests** | `qa/baseline/acceptance.txt` |
| `python -m pytest tests/test_docs_sync.py -q` | **7 passed** | `qa/baseline/docs_sync.txt` |
| `python scripts/econ_shelf.py --check` | **frozen fixture: in sync** | `qa/baseline/econ_shelf_after.txt` |
| `python scripts/ui_smoke.py --url http://127.0.0.1:8001` | **0 failure(s)** | `qa/baseline/ui_smoke_after.txt` |
| Live click-through, 12 accounting tiles on 8001 | **0 failure(s)**, `accounts` through its two checkpoints | `qa/evidence/accounting/clickthrough.md` / `.json` |
| `python scripts/ci.py` | **2 of 3 steps passed**: `unit tests` FAIL (2627 tests, 66 failures, 13 errors — the 66 are the carried-forward historical set, listed in `qa/baseline/ci_failure_list.txt` with **zero** new names), `shelf audit and frozen contract` PASS, `page syntax` (node `--check`) PASS | `qa/baseline/ci_out.txt`, `qa/baseline/ci_err.txt` |

## 3. Subject passed so far

| # | Subject | Status |
|---|---|---|
| 1 | accounting | **PASS** — manual + suite + fixes + ledger as below |
| 2–11 | finance … research | not started (the order is fixed: finance next) |

## 4. Deliverables of this session

- **Manual:** `qa/manual/accounting.md` — 51 expectation rows (`E-acc-001…051`), every row
  traced to a source of truth; §9 is the traceability matrix (50 PASS, 1 BLOCKED); §10 lists
  the nine declared gaps.
- **Suite:** `tests/test_subject_accounting_acceptance.py` — **53 tests / 136 subtests** (one test
  per E-row, including the three added under B-179…B-181); `qa/probe_traceability.py` reconciles
  the manual and the suite 1:1 (53 rows ↔ 53 tests).
- **Defect ledger:** `qa/QA_DEFECTS.md` — **8 fixed** (D-ACC-01…05 in the first increment,
  D-ACC-06/-07/-09 under the owner-approved B-179…B-181), 0 blocked, 2 gaps (D-ACC-08, -10).
- **Probes** (read-only, kept so the next session can re-measure): `qa/probe_subject.py`,
  `qa/summarise_subject.py`, `qa/probe_methods.py`, `qa/probe_schema.py`, `qa/probe_related.py`,
  `qa/probe_duplicates.py`, `qa/probe_shadowing.py`, `qa/probe_accounting_papers.py`,
  `qa/probe_accounting_cases.py`, `qa/probe_refusal_path.py`, `qa/probe_guide_miniature.py`,
  `qa/probe_traceability.py`, `qa/clickthrough_accounting.py`.

**Path note.** The work order says to create `qa/` at the repo root. It lives at the **app**
root (`business_pipeline_v0.12/business_pipeline/qa/`) because every probe, gate and test in it
runs from the app folder and the manual's cross-references are app-relative; `qa/` is still
outside `docs/`, so `test_docs_sync.py`'s documentation-spine contract is unaffected (verified:
7 passed).

## 5. Open decisions for the owner — all three resolved on 2026-11-02 (see §8)

| Outcome | Decision | Ledger |
|---|---|---|
| APPROVED ("to unfreeze, yes unfreeze it") | **B-179**, fixed | D-ACC-06 |
| "implement your reco" | **B-180**, fixed | D-ACC-07 |
| APPROVED ("yes unfreeze") | **B-181**, fixed | D-ACC-09 |

### 5.1 The questions as they stood

| # | Decision needed | Evidence | Ledger |
|---|---|---|---|
| 1 | Unfreeze `src/bp/methods.py` to rename the duplicated `_tax_typing` (and `_risk_typing`, `_social_typing`) so `tax_incidence` keeps its own unit hook | `qa\probe_shadowing.py`: `tax_incidence.typing("producer_share")` → `("currency", 2)` | D-ACC-06 |
| 2 | Should `guard.subject_fit()` enforce the subject vocabulary again (the design note) or stay advisory (its docstring)? | `docs/CONTINUATION_NOTE.md` vs `guard.subject_fit` docstring; `test_shelf_mode_control` | D-ACC-07 |
| 3 | Unfreeze the stage contract so an **unknown method name** is refused instead of being delivered as a framework-only (T4) paper | `Pipeline().run({"method": "no_such_method", "inputs": {}}, …)` → `delivered` | D-ACC-09 / E-acc-051 |

## 6. Commit status — read this before committing anything

**A second writer was active in this worktree during the session.** At the opening
`git status --porcelain` the tree held only `M SERVING.md` and `M _baseline_wt`; by the closing
it also carried a Portfolio-Lab / market-data / UI change set (staged `docs/CHANGELOG.md`,
`docs/WORKLOG.md`, `web/DESIGN_NOTES.md`, `web/index.html`; unstaged `src/bp/product/subjects.py`,
`src/bp/server.py`, `src/bp/templates.py`, `src/bp/product/marketdata.py`,
`scripts/ui_smoke.py`, several tests and docs). **None of that is mine and none of it was
reverted.**

Committed in this session (files verified to contain only this session's work):

```
git add business_pipeline_v0.12/business_pipeline/src/bp/product/chat.py \
        business_pipeline_v0.12/business_pipeline/docs/HOME.md \
        business_pipeline_v0.12/business_pipeline/docs/DECISIONS.md \
        business_pipeline_v0.12/business_pipeline/tests/test_subject_accounting_acceptance.py \
        business_pipeline_v0.12/business_pipeline/qa
```

**Correction to the first report.** The two paragraphs that stood here said the session's
`docs/CHANGELOG.md` and `docs/WORKLOG.md` entries were uncommitted. They were not: the other
lane's commit **`2c2a4f3`** swept them in (`git log -S'## Accounting: the paper'` names that
commit). The content is intact and at the top of both files; the attribution is theirs. The
follow-up increment (§8) commits its own CHANGELOG/WORKLOG entries normally, because those two
files were clean by then.

## 8. Follow-up increment — owner-approved unfreezes (B-179…B-181)

The owner replied to §5 of the first report: *"to unfreeze, yes unfreeze it … implement your
reco … yes unfreeze"*, and *"dont do finance yet, its doing some fixing"*. All three BLOCKED
findings are therefore fixed, in the layer the decision names:

| Ledger | Decision | Change | Layer | Trap test |
|---|---|---|---|---|
| D-ACC-06 | **B-179** | six duplicated `typing` hooks renamed one-per-method and re-pointed; `methods.py` has zero duplicate definitions; `risk_metrics`, `tax_incidence`, `social_welfare` get their own units | frozen core (`src/bp/methods.py`), owner-approved unfreeze | `E-acc-052` |
| D-ACC-07 | **B-180** | `guard.subject_fit()` enforces the shelf vocabulary again, with a named-framework carve-out; `chat.start` checks the computation boundary first so the message names the right shelf | product (`guard.py`, `chat.py`) | `E-acc-053` |
| D-ACC-09 | **B-181** | `orchestrator.start` refuses a `method` that is neither a frozen method nor a template; the `framework_only` sentinel still delivers the structure-only paper | frozen stage contract (`orchestrator.py`), owner-approved unfreeze | `E-acc-051` |

One existing test asserted the old fail-open (`tests/test_pipeline.py::test_no_method_is_framework_only`
ran `method: "mystery"` and expected a T4 delivery). Under B-181 that expectation contradicts the
decision of record, so the **test** was the stale side: it is now
`test_a_missing_method_is_framework_only_and_an_unknown_one_is_refused`, which asserts both halves
(a missing method still delivers; an unknown name is blocked with its reason). No assertion was
weakened — the test gained one.

Manual: `E-acc-051…053` added, matrix now **53 rows / 53 tests**, all PASS. Documented count
**2627 → 2630** (`HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`); `test_docs_sync` 7 passed.
`econ_shelf --check`: "frozen fixture: in sync" after the core rename.
`qa/probe_duplicates.py src/bp/methods.py` → **0 duplicate definitions**.

## 9. Closing measurement after the follow-up increment (2026-11-02, 19:52)

| Measure | Value | Note |
|---|---|---|
| Full suite | **2711 tests, 65 failures, 14 errors** | `qa/baseline/_final_err.txt` |
| New failure names vs the previous run | **1** — `test_E_eco_079__hhi_uses_percentage_shares` in `tests/test_subject_economics_acceptance.py`, a file the **other** session added while this run was in flight | not mine; their session owns it |
| Failures that disappeared | 3 — the flaky social-media route ERROR, `test_documented_test_count…` (green at the time) and `test_no_method_is_framework_only` (updated under B-181) | verified |
| `pytest tests/test_subject_accounting_acceptance.py tests/test_pipeline.py tests/test_product_home_routing.py tests/test_frozen_contract.py` | **84 passed, 136 subtests** | `qa/baseline/verify_final.txt` |
| `qa/probe_duplicates.py src/bp/methods.py src/bp/product/chat.py` | **0 duplicate definitions** in both | `qa/baseline/dups_final.txt` |
| `scripts/econ_shelf.py --check` | "frozen fixture: in sync" | `qa/baseline/econ_shelf_after2.txt` |

**The documented test count is a moving target while the other session adds tests.** The count
went 2627 → 2630 (this session's three new tests) → 2711 (their finance/economics suites) → 2726
(their next additions, measured at 19:53). `HOME.md` / `HANDOFF.md` / `CONTRIBUTORS.md` currently
carry **2711**, which was correct when that session wrote it; `test_documented_test_count_matches_the_real_suite`
is therefore red until the number is refreshed again. That is the intended pressure of the test,
and it belongs to whichever session is adding tests — not a defect in this increment. My own
three tests are inside the number.

## 10. Next action

**Session 2 — `finance`.** Top three risks, measured from this session's data:

1. **The same shadowing class may hide in `chat.py`'s 50-odd formatters.** Three of this
   session's five defects were duplicate definitions; `qa/probe_duplicates.py` is the gate, and
   it must be run on `src/bp/product/*.py` at the start of every session.
2. **Capability formatters without a bespoke function print raw Decimals.** 17 of the 126
   capability keys have no `CAPABILITY_LINES` entry (measured: `qa/baseline/formatters.txt`), so
   they fall back to `_generic_lines`, which quotes the core's full Decimal when a value carries
   more than two places. Finance's `time_value`, `leverage_analysis`, `equity_bridge`,
   `return_on_investment` and `cap_table_round` are five of the seventeen.
3. **A second mandatory checkpoint exists for `management_accounts` only.** Any future method
   with `mapping` must be driven through both checkpoints by the click-through, or the paper
   silently stays at `awaiting_mapping_confirmation`.

---

# Session 2 — `economics` (2026-11-02)

**Opening commit:** `ab0be0d` · **Branch:** `corpus/merge-v1`

**Subject chosen by the owner in this session.** This file's §8/§9 said `finance` was next; the
owner's work order for this session named `economics`, and the owner confirmed `economics` when
asked directly. `finance` is therefore **deliberately skipped** and remains not started. That is
an owner instruction, not a silent reordering.

## 1. Baseline (Phase 0)

| Measure | Documented | Measured at `ab0be0d` |
|---|---|---|
| Tests executed | ~2553 / 2630 documented | **2627 tests** |
| Failures | ~84 | **66** |
| Errors | ~12 | **13** |
| Duration | 623 s | **634.8 s** |
| Loader count | 2630 documented | **2630** (2711 after this session's 81 tests) |

Raw log: `qa/baseline/2026-11-02-ab0be0d-suite-err.txt`; failure names:
`qa/baseline/failure_list_ab0be0d.txt` (79 FAIL/ERROR lines). **Zero belong to the economics
shelf.** All 79 are worksheet/framework-completion (value chain, STP, TAM, RFM/SERVQUAL,
AIDA/attribution/BCG/brand equity, change organisation, operations examples), the registry import
count, a chat research-hang, a completion template refusal, a templates registry link, and the
network Brave→Firecrawl test. They carry forward to their own shelves' sessions.

## 2. Gates (closing, on the working tree)

| Gate | Result | Evidence |
|---|---|---|
| `pytest tests/test_subject_economics_acceptance.py -q` | **81 passed** | `qa/baseline/econ_acceptance.txt` |
| economics slice (shelf tests + 10 owner-contract files) | **122 passed** | `qa/baseline/econ_slice.txt` |
| acceptance + frozen contract + docs sync together | **91 passed** | `qa/baseline/recheck.txt` |
| `python scripts/econ_shelf.py --check` | **frozen fixture: in sync**; 142 methods, 144 presets, 59 economics tools (23/23/13), glossary 25, "missing student notes: none" | `qa/baseline/econ_shelf_before.txt` |
| `python -m unittest discover` after the change | **2711 tests**, run while another writer was editing the tree — see §5 | `qa/baseline/after_err.txt` |

## 3. What was produced

- `qa/manual/economics.md` — the shelf's acceptance manual: 10 sections, **59 per-tool contract
  rows** generated from `LIBRARY`, records/glossary/tiles, and **84 E-rows**.
- `tests/test_subject_economics_acceptance.py` — **81 tests**, one per PASS E-row.
- `qa/probe_econ_recon.py`, `probe_econ_contracts.py`, `probe_econ_examples.py`,
  `probe_econ_tools.py`, `probe_econ_reports.py`, `probe_econ_related.py`, `probe_econ_facts.py`,
  `build_econ_manual.py` — the reproducible evidence behind every claim.
- `qa/baseline/econ_*.txt|json` — the raw measurements.

**Headline:** all 59 economics tools deliver through their own preset, every method's own checks
pass, every computation is deterministic, and **all 23 reproducible worked examples in
`docs/ECONOMICS_STUDENT_GUIDE.md` match hand arithmetic** (`qa/baseline/econ_examples.txt`).
The shelf's arithmetic layer is sound.

## 4. Defects — see `qa/QA_DEFECTS.md` (D-ECO-01…09)

- **BLOCKED (frozen core):** D-ECO-01 `labour` types a share and a tightness ratio as currency;
  D-ECO-02 tightness divides by the unemployment *rate*, not the unemployed count; D-ECO-03 the
  currency paper labels the source amount with the target currency.
- **FIXED:** D-ECO-08 `CURRICULUM_MAP.md` said 55 tools; the catalogue has 59.
- **GAPs ledgered:** G-eco-01…04 (no per-tool `need` for 52 tools; no worksheets by design; VAR /
  cointegration parked; diagram renderer and catalogue section not built).
- **Closed, not reproducible:** D-ECO-09 (session 1's `tax_incidence` units claim).

## 5. A second writer was active in this worktree — read before committing

At the Phase-0 baseline the tree held `M _baseline_wt`, `M documents/index.json` and deleted
`_qa_*.txt`. By 19:39 it had gained **another lane's uncommitted work**: the owner-approved core
unfreeze **B-179…B-181** in `src/bp/methods.py`, `orchestrator.py`, `chat.py`, `guard.py`, plus
`docs/CHANGELOG.md`, `docs/DECISIONS.md`, `docs/WORKLOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`,
`docs/CONTRIBUTORS.md`, `tests/test_pipeline.py`, `qa/QA_STATE.md`, `qa/QA_DEFECTS.md`,
`qa/manual/accounting.md` and a set of `qa/probe_finance_*` / `qa/audit_finance.py` files.
**None of that is mine and none of it was reverted.**

Two consequences, recorded honestly:

1. **The baseline run and the post-change run straddle a moving tree.** 2627/66/13 is the tree as
   it stood when that run started; the 2711-test re-run is indicative, not a clean before/after.
   The trustworthy numbers are the targeted slices in §2.
2. **`src/bp/methods.py` now has 0 duplicate definitions** (B-179 renamed `_risk_typing`,
   `_tax_typing`, `_social_typing` one per method). That removes session 1's D-ACC-06 root cause
   and is why D-ECO-09 no longer reproduces. D-ECO-01/02/03 **still reproduce**
   (`qa/baseline/dup_now.txt`).

**Nothing was committed this session.** Staging `docs/CHANGELOG.md`, `docs/WORKLOG.md`,
`docs/HOME.md`, `docs/HANDOFF.md` or `docs/CONTRIBUTORS.md` would have committed the other lane's
unfinished prose under this session's message — the exact mistake session 1 avoided. The files are
written on disk; the commit waits for a quiet tree (§6 decision 3).

## 6. Owner decisions needed

| # | Decision | Evidence |
|---|---|---|
| 1 | **Unfreeze `src/bp/methods.py`** (already unfrozen for B-179…B-181) to fix D-ECO-01 — retype `wage_share_of_productivity` and `labour_market_tightness` as ratio, `vacancies` as a count — and D-ECO-03 (`currency_convert`'s template labelling the source currency) | `qa/baseline/econ_labour_typing.txt`, `qa/baseline/econ_reports.txt` |
| 2 | **Tightness denominator (D-ECO-02).** Standard is vacancies per unemployed person. Options: add an optional `unemployed` input and compute `vacancies / unemployed`, refusing when absent; keep the formula but rename the output to say what it is; or drop the output. A convention decision, not a code default | `docs/OPEN_ISSUES.md` 11b/11c |
| 3 | **When to commit session 2**, given the concurrent writer: (a) now, adding only this session's own paths and leaving the five shared docs uncommitted; (b) after the other lane commits; (c) both lanes' work in one commit | `git status --porcelain` at 19:39 |

## 7. Next action

**Session 3 — `finance`** (still not started; the one shelf skipped out of order).
Top three risks measured from this session:

1. **Frozen-core label defects are systemic, not one-off.** `labour_market`'s typing hook falls
   through to `currency` for every key it does not enumerate — the same shape as B-179. Finance
   has 35 tools and far more ratio/money mixing; run the unit audit in `qa/probe_econ_tools.py`
   (`suspicious()`) over the finance shelf first: it found `labour_market` in one pass.
2. **Template wording can contradict the computation.** D-ECO-03 is a correct number with a wrong
   label, and no numeric check catches it. Render every finance preset's report and read the
   sentences — `qa/probe_econ_reports.py` is that harness.
3. **Concurrent writers.** Check `git status` before and after every commit, and commit only your
   own paths while another lane is live in the same worktree.

