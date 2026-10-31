# Pipeline continuation (CONTINUATION NOTE — NOT IMPLEMENTED)
# Consideration for future discussion; read ONLY when instructed.
# Do not treat as implemented framework substitution or filled gap.

Status: consideration / deferred. No framework substituted into pipeline.
Binding constraints preserved (no silent changes):
- corpus-db/CORPUS_DB.md: D-17 (sha256+DOI dedup), D-18 (student-upload private / owner-mediated enrichment), Q-19 (open: non-model-answer upload qualification + copyright check), schema (`source_kind`, `added_by`, `licence`, `licence_verified`).
- business_assignment_taxonomy.md (.md + .docx) and -edited.docx remain EXTERNAL reference only (C:\Users\Roderick\Downloads\BUSINESS ACTIVITY COVERAGE/).
- Pipeline design: SQLite/Meilisearch (layer 1) + OA APIs (layer 2) + curated web (layer 3); CRAAP scoring; no evidence invented.

---

## ADDENDUM 2026-10-31 — taxonomy coverage evaluation (DONE; read before option A/B/C)

Requested: "which taxonomy items can the pipeline do well now, which need enhancement, which are out of scope."
Answer delivered in full at `docs/TAXONOMY_COVERAGE_EVALUATION.md` (per-item mapping, all 19 sections).
Measured against the running code, not the docs. **No framework was added, substituted or removed.**

### The manual
`business_assignment_taxonomy.md` = source of record. The `-edited.docx` differs from the `.docx` only in
Word metadata — paragraph-for-paragraph identical (285 paras each, zero unique lines). Manual's own
exclusions (country-specific formats, qualifications/platform work, industry verticals, academic-skills
services) are excluded from the evaluation.

### Measured capability surface
| Layer | Count | Source |
|---|---|---|
| Frozen computation core | **142 methods**, all `implemented_tested`, 133 T1 + 9 T2 | `bp/methods.py` → `LIBRARY` |
| Framework completion profiles | **68** (`PROFILES`) — but only **37 reachable** | `bp/product/framework_profiles.py` |
| Conductor plan frameworks | **9** + 1 profile (`business_plan`) | `bp/product/chat.py` → `FRAMEWORKS` |
| Capability catalogue | **126** (`capabilities.ENTRIES`) | `bp/product/capabilities.py` |
| Subject shelves | 11 subjects, 158 catalogue entries, 45 worksheets (33 draftable) | `bp/product/subjects.py` |
| Deliverables | `submission`(docx+html), `workpapers`(xlsx+csv), `worksheet`(docx+html), **`presentation` declared but NO renderer** | `bp/product/deliverables.py` |

**Two framework systems, not one.** Worksheet reach (68 profiles) ≈ 7× paper reach (9 frameworks).
A student can complete a DMAIC worksheet with retrieved evidence and cannot get a DMAIC *paper*.

### Four findings that change the coverage answer

1. **The `not_supported` refusal path no longer exists.** Referenced by `web/index.html:2052`,
   `scripts/build_conductor_samples.py:142`, `scripts/build_home_sample.py:113` and 9 tests — but
   `chat.py`/`capabilities.py` contain **zero** occurrences of the string. `guard.subject_fit()` now
   `return True, None` unconditionally. **This breaks "no silent framework substitution."**

2. **Unmatched briefs silently become PESTEL.** `chat._infer_framework()` falls through to
   `return "pestel"`. Measured on 28 briefs: **27/28 mis-routed** (journal entries, Tableau dashboard,
   MBA essay, Python script, literature review, business model canvas → all PESTEL). Only briefs naming
   a framework literally route correctly. The `council` module (`bp/product/council.py`) is the designed
   remedy but is **opt-in (`BP_PLAN_COUNCIL=1`) and off by default**; the deterministic resolver is both
   default and fallback. **Highest-priority fix — every coverage number is contingent on it.**

3. **The catalogue's `status_short` understates coverage.** **21 of 24** "Method not built" entries
   already have working core methods (`cost_benefit`, `cost_effectiveness`, `sroi`, `decision_tree`,
   `expected_utility`, `multi_criteria`, `monte_carlo`, `scenario_analysis`, `sensitivity_table`,
   `risk_metrics`, `power_analysis`, `reliability_alpha`, `multiple_comparison`,
   `missing_data_bounds`, `trend_forecast`, `difference_in_differences`, `instrumental_variables`,
   `regression_discontinuity`, `process_control`, `dcf_valuation`, `multiples_valuation`).
   **Genuinely unbuilt:** FMEA prioritization, LP/integer optimisation, transportation/assignment,
   Markov chains, clustering/classification/segmentation, SEM/PLS-SEM, mediation/moderation, conjoint,
   DEA, event studies, LBO, lease-vs-buy, dividend discount model.
   **Do not trust this column — assess against `LIBRARY` and `PROFILES` directly.**

4. **32 built profiles are orphaned** (no catalogue entry, no worksheet): ADKAR, AIDA, attribution, BCG,
   brand equity, Burke-Litwin, change org, CRO, digital mix, DMAIC, email/CRM, funnel, Galbraith Star,
   GE/McKinsey, generic strategies, Lewin, logic model, marketing automation, McKinsey 7S, Mintzberg,
   PDSA, Porter's Diamond, RFM, SEO, social media, STP, STP-evidence, strategic positioning, Strategy 4,
   TAM, theory of change, UTAUT. **8 draftable worksheets point at templates with NO profile:**
   BMC, Lean Canvas, VPC, project charter, WBS, risk register, stakeholder plan, lessons learned.
   Both are **registration gaps, not build gaps** — cheapest wins available.

### Test state (must be green before next build)
`53 failed, 2412 passed, 102 subtests passed in 103.57s`. The failures split three ways:
- **39 stale tests** — assert the pre-feature state (e.g. `template_customer_journey` "has no profile";
  it now does). The feature shipped; the test lags.
- **14 REAL defects** — `test_value_chain_completion`, `test_operations_frameworks`:
  `test_nine_activities_each_carry_a_sourced_item_or_a_named_gap`,
  `test_no_evidence_is_written_from_general_background`,
  `test_an_empty_block_is_named_and_never_filled`. These hit the completion engine's evidence handling
  — the area the taxonomy leans on hardest.
- **2 routing** — `test_open_pure_accounting_refused` expects `not_supported`, code returns `clarify`.
`OPEN_ISSUES.md` says 58 failures; 53 observed — count has drifted.

### Bucket verdict (full detail in the evaluation doc)
- **A now** — strategy framework papers (PESTEL/SWOT/Five Forces/Value Chain/Ansoff/VRIO + 2 combos);
  worksheet completion across 37 frameworks; the `business_plan` profile (12 sections, 2 levels,
  2 modes); quantitative problem-solving; marketing/customer analytics; consulting recommendations;
  evidence discipline (full-text gate, no-general-background rule, overclaim scanner, recompute guard);
  portfolio lab / mock fund.
- **B with enhancement** — §1, §2, §3, §5, §7, §10, §11, §12, §14, §16, §17, §19. Cheapest wins:
  register the 32 orphan profiles; build the 8 missing worksheet profiles; add a **problem-set paper
  profile** (multi-part worked questions, each bound to a frozen method with stated inputs — reuses all
  142); add a **short-form document profile family** (memos, letters, abstracts, reflections — unlocks
  §12 and §16); extend the plan profile (country analysis + entry mode for global plans).
- **C out of scope** — §8 (bookkeeping: it can *analyze* statements, not *prepare* them), §9 (all
  simulations — the pipeline never observes or plays), §13 (presentations — no renderer),
  §15 (code/spreadsheet/dashboard deliverables), §18 (law, governance, sustainability reporting),
  systematic reviews/meta-analysis, IRB/grant proposals, thesis orchestration, e-portfolios.
  §18 partial: `sroi`, `cost_benefit`, `cost_effectiveness` exist in the core, but no
  sustainability-report or governance/law profile exists.

### Recovery item — CORPUS_DB.md is truncated in the working tree
`corpus-db/CORPUS_DB.md` is **730 bytes** (its final 10 lines only) and `corpus-db/` is **untracked at
HEAD**. The design record referenced by this note (D-17, D-18, Q-19, the schema) is therefore not
readable as it stands. **It is recoverable — do not rewrite it:**
- full 69,327-byte version = git blob `a97402ee84e870896ca71a63242651989d05c232` (commits `df5cdcc` /
  `d78e1b4`, "untracked files on cline checkpoint")
- earlier 58,191-byte version = blob `a168c4381bfaa78a3f279618c23d08eb66d2c35a` (commit `d25d622`)
- restore: `git cat-file blob a97402ee > corpus-db/CORPUS_DB.md`
The corpus layer itself is still unimplemented (§9 of CONDUCTOR_MANUAL: "not yet wired").

### CORRECTION (same day) — the accounting ledger kernel was missed; §8 is NOT out of scope
The first evaluation pass rated taxonomy **§8 Financial Statement Preparation & Bookkeeping as "C —
out of scope"**. **That was wrong.** It was caused by reading only the product layer
(`src/bp/product/*`) and missing the ledger kernel in **`src/bp/`** (sibling of `bp/product/`, not
under it). A product-layer-only sweep of this codebase will miss it again.

**What actually exists** — `src/bp/ledger.py` (32 KB), `accounts.py` (22 KB), `schedules.py` (33 KB),
`reconcile.py`, `report.py` — wired in as the **`management_accounts`** method (T2), covered by five
test modules (`test_accounts.py`, `test_accounting_operations.py`,
`test_accounting_pipeline_integration.py`, `test_accounting_sandbox_parity.py`,
`test_t_account_ledger.py`) and by `docs/ACCOUNTING_STUDENT_GUIDE.md`.

**Verified by execution:** one engagement (29-account chart, 6 entries, a reversal, a dividend,
7 schedules: prepayment, deferred income, depreciation, two bad-debt events, disposal, revaluation)
produced **11/11 frozen checks passing** and a `.xlsx` with sheets
**Case · Statements · Trial balance · Journal · Checks · Recorded values · Report**, where `Statements`
carries trial balance, income statement, balance sheet, cash flow statement, reconciliation and notes.
(Cases with CPM artifacts also get a `Schedule` sheet with a coloured bar strip.)
The kernel derives: journal → trial balance → income statement → balance sheet → two-route cash flow →
statement of changes in equity → comprehensive income with a separate OCI reserve → T-accounts with a
running balance → bank reconciliation → retained-earnings rollforward → closing balances → next-period
opening lines → human-review flags. **Eight schedule kinds**: depreciation, amortization, accrual,
bad debt, disposal, prepayment, deferred income, revaluation. Declared policy changes (useful-life /
residual-value revision) apply prospectively from their date. Reversals post a visible mirror entry, not
a silent balance tweak.

**So the spreadsheet gap is a LINKAGE gap, not a FORMAT gap.** The `.xlsx` exists and is real. But:
- **Every cell is an inline string (`t="inlineStr"`), never a formula.** Nothing recalculates when the
  student changes an assumption. This is the actual gap behind §3 "Excel financial modeling" and §15
  "Excel projects".
- **No pivot tables, no charts, no conditional formatting, no named ranges, no Solver.** §3's "ratio
  analysis … often accompanied by charts", §15's "pivot tables and Solver models" and §2's "Linear
  programming and Solver models" have no spreadsheet-side home.
- **The xlsx omits the T-accounts, the statement of changes in equity, the closing balances, the
  next-period opening lines and the human-review flags.** `spreadsheets._accounting_rows()` reads only
  `statements_export` (trial_balance, income_statement, balance_sheet, cash_flow, reconciliation,
  notes), `trial_balance`, `journal` and `checks`. The rest of the appendix (`t_accounts_export`,
  `equity_statement_export`, `ledgers`, `closing_balances`, `flags`, `export`, `opening_lines_next`)
  reaches the student **only through the .docx explainer** (`product/explain.py` builds the accounting
  cycle from `journal_export`, `t_accounts_export` and `statements_export`). So the artefact an
  examiner "audits cell by cell" is missing the ledger walk-through the explainer has.
- **The schedule workings are not broken out as schedules** — no structured `schedules` key in the
  appendix; depreciation appears as a journal posting and an income-statement line, not as a
  cost/life/residual/annual-charge schedule.

**Still genuinely out of scope in accounting:** audit opinions and audit sampling; consolidation
(goodwill, NCI); IFRS-vs-GAAP comparison; FX translation; lease accounting; deferred-tax rollforward;
jurisdiction tax rules (credits, exemptions, thresholds, NOLCO, withholding, filing); not-for-profit
and government accounting; ERP/AIS practice sets; target costing, life-cycle costing, budget/planning
variances and idle-capacity variances; standards setting; **scanned-ledger ingestion** (CSV/TSV/XLSX
read fine, a PDF scan or image of a ledger cannot).

**Also still out of scope elsewhere in the spreadsheet space:** §17 ER/UML/DFD/BPMN diagrams, §15
code and dashboard deliverables, §7 portfolio construction with real holdings, §16 marketing
dashboards.

### ROOT CAUSE FOUND — the 27/28 → PESTEL routing is an UNCOMMITTED LOCAL REGRESSION, not a design change
This is the single most important item in this addendum. **The refusal path was never removed by
design. It was deleted in the working tree by an uncommitted local edit, in TWO files.**

`git diff` against HEAD (`d3df5c3`) shows the damage. HEAD is correct and contains the refusal code.

**File 1 — `src/bp/product/guard.py`** — `subject_fit()` was gutted:
```diff
 def subject_fit(text, subject="management"):
-    """Return (ok, message).  The message names the subject the brief belongs to."""
-    ok, message = computation_boundary(text, subject)
-    if not ok: return ok, message
-    ... (full SUBJECT_HINTS matching, "This does not look like a management or strategy instruction",
-         "This instruction looks like <other>, not <subject>", "This does not name a <subject> question") ...
-    return False, (...)
+    """Return (ok, message).  Home is the macro conductor: it accepts any subject
+    and any combination of framework + computation; the subject field is advisory."""
+    return True, None
```

**File 2 — `src/bp/product/chat.py`** — three deletions:
```diff
 # in _fit():
-    if any(hint in text for hint in COMPUTATION_HINTS) and not any(hint in text for hint in EXTERNAL_HINTS):
-        return False, ("This looks like an accounting or finance computation, not a strategic analysis. "
-                       "Use the Accounting or Finance shelf instead.")

 # in start():
-    if selection.get("question") and fits:
+    if selection.get("question"):
         questions.insert(0, dict(selection["question"]))

 # in start(), immediately before `return state`:
-    if not fits:
-        state.update({"stage": "not_supported", "message": message, "questions": [], "question_index": 0})
     return state
```

**Why this produces 27/28 → PESTEL:** with `subject_fit()` always returning `(True, None)`, the
subject guard never refuses. With the `_fit()` computation-hint refusal gone, a computation brief is
never refused either. With the `if not fits:` return gone, even when `fits` **is** set to `False`
(HEAD's `open_mode` branch does exactly that for a pure computation brief) the state is still
returned with `stage: "clarify"`. And `_infer_framework()` still falls through to `return "pestel"`.
The result: every unmatched brief becomes a PESTEL paper.

**The FIX is two file restores, not a redesign:**
```powershell
git -C 'D:\SMART BUSINESSWRITER' checkout -- business_pipeline_v0.12/business_pipeline/src/bp/product/chat.py business_pipeline_v0.12/business_pipeline/src/bp/product/guard.py
```
(Or re-apply the three hunks above by hand if other local edits to those two files must be kept —
check `git diff` first; for `chat.py` the ONLY local change is these three hunks, so a checkout
loses nothing.)

**VERIFIED in an isolated copy** (whole working tree copied to a temp dir, only `chat.py` +
`guard.py` restored from HEAD, the real tree never touched). Full suite, same machine, same run:
- **BASELINE (live tree): 54 failed, 2411 passed** → **FIXED: 52 failed, 2413 passed.**
- **3 tests flip fail → pass, and nothing regresses:**
  `test_chat.py::test_a_computation_brief_is_refused_instead_of_forced_into_pestel`,
  `test_product_home_routing.py::test_open_pure_accounting_refused`,
  `test_product_home_routing.py::test_shelf_mode_control`.
  (One further "new" failure, `test_product_cases.py::..._uses_the_repo_cases_folder`, is an artifact
  of the temp copy's folder name — it asserts the parent directory is literally named
  `business_pipeline`. Not a regression. Note the baseline failure count drifts 52–54 across runs
  because of the known network-dependent tests; compare the *set*, not the count.)
- `tests/test_product_home_routing.py` + `tests/test_chat.py` → **40 passed** (was 2 failing).
- The 28-brief probe → **23 × `not_supported` with a specific message, 6 × `clarify`**
  (was 27 × `clarify` with a silent PESTEL framework).
  Now correctly refused: journal entries, NPV, literature review, reflection paper, MBA essay,
  Tableau dashboard, Python script, peer evaluation, IRAC brief, ESG report, risk register, etc.
  Still accepted (correctly): business plan, Five Forces, market sizing, press release,
  business model canvas, break-even.
- `not_supported` is the stage the UI already renders: `web/index.html:2052` shows
  "This analysis is not the right tool here" plus a button that opens the detected subject's shelf
  (`c.subject_detected.label` / `.id`). `scripts/build_conductor_samples.py:142` and
  `scripts/build_home_sample.py:113` already raise on it. **No UI work is needed — the front end
  was built for this contract and was left waiting for the backend.**

**KNOWN OVER-REFUSAL to check after the restore (do not "fix" it by widening the guard blindly):**
with the restore, `"SWOT analysis of our coffee shop in Davao City"` is refused with "This does not
look like a management or strategy instruction" **even though the framework was correctly detected as
`swot`**. The management-subject hint list does not contain "shop"/"coffee"/"Davao". The fix is to
let an **explicitly named framework** bypass the subject guard (the same carve-out HEAD already makes
for `breakeven`/`vrio` in `start()`), not to widen the hint list. `tests/test_conductor_frameworks.py`
asserts `assertNotEqual(state["stage"], "not_supported")` for framework briefs — run it and confirm.

**Also check after the restore:** `docs/OPEN_ISSUES.md` still lists the routing failure as open, and
`docs/HANDOFF.md` / `HOME.md` / `CONTRIBUTORS.md` carry test counts that will shift.

### Work orders — pick-up-ready
Each item below is independent. Do them in order; do not batch them.

**WO-1 — restore the refusal path (P0, correctness).**
Files: `src/bp/product/chat.py`, `src/bp/product/guard.py`.
Action: `git checkout --` both files (see the root-cause section), or re-apply the three hunks.
Verify: `pytest tests/test_product_home_routing.py tests/test_chat.py tests/test_conductor_frameworks.py -q`
→ all pass; re-run the 28-brief probe and confirm 0 briefs silently become PESTEL.
Then close the over-refusal gap for explicit frameworks (see the note above) and add a test.

**WO-2 — register the 32 orphan profiles (P1, cheapest coverage win).**
File: `src/bp/product/subjects.py` → `CATALOGUE` (158 entries) and `WORKSHEETS` (45).
The profiles exist and are tested in `framework_profiles.PROFILES`; they have no catalogue entry and
no worksheet, so the UI never shows them. Add the catalogue record (copy the shape of an existing
`F` entry: `id, name, type, form, disciplines, summary, evidence_needs, template, status_note,
status_short, linked_methods`) and the `WORKSHEETS` entry with `draftable: True`.
Orphans: `template_adkar, aida, attribution, bcg, brand_equity, burke_litwin, change_organization,
cro, digital_mix, dmaic, email_crm, funnel, galbraith_star, ge_mckinsey, generic_strategies, lewin,
logic_model, marketing_automation, mckinsey_7s, mintzberg, pdsa, porters_diamond, rfm, seo_content,
social_media, stp, stp_evidence, strategic_positioning, strategy_4, tam, theory_of_change, utaut`.
Do NOT edit `completion.py`, `api.py` or `web/index.html` to make a profile appear (AGENTS.md).
Verify: the new catalogue ids appear in `GET /api/cases/subjects/<subject>` and each worksheet's
`template` resolves in `framework_profiles.PROFILES`.

**WO-3 — build the 8 missing worksheet profiles (P1).**
Eight `WORKSHEETS` entries are `draftable: True` but point at templates with **no** profile:
`STR-15` business_model_canvas, `STR-16` lean_canvas, `STR-17` value_proposition_canvas,
`PM-05` project_charter, `PM-09` wbs, `PM-06` risk_register, `PM-15` stakeholder_plan,
`PM-16` lessons_learned. Add one `PROFILES` entry per template following §6.3 of
`CONDUCTOR_MANUAL.md` and the checklist in `docs/HANDOFF_NEXT_CHAT.md` §3 (unit, gap mode, blocks
must match `templates.CANVAS_BLOCKS`, notes with `analysis`/`qualify`/`short`).
Verify: `completion.complete()` returns blocks or named gaps for each; copy
`tests/test_pestel_completion.py` per framework.

**WO-4 — fix the 14 real completion defects (P1).**
`tests/test_value_chain_completion.py` and `tests/test_operations_frameworks.py` fail on substance:
`test_nine_activities_each_carry_a_sourced_item_or_a_named_gap`,
`test_no_evidence_is_written_from_general_background`,
`test_an_empty_block_is_named_and_never_filled`,
`test_no_score_ranking_or_verdict_is_derived`. Also `test_email_crm/funnel/kano/marketing_plan/
measurement_plan/rfm/servqual/social_media/stp/tam` (`..._each_carry_a_sourced_item_or_a_named_gap`,
`..._outline_headings_are_present_and_title_cased`).
These are the areas the taxonomy leans on hardest. Work one framework at a time, live-verified.

**WO-5 — update the 39 stale profile tests (P1).**
They assert the pre-feature state (e.g. `test_a_framework_without_a_profile_has_no_extension` asserts
`template_customer_journey` has no profile; it does now). Change the assertion to the current
truth — a profile exists, so the test should assert that a *genuinely* profileless template is
refused with the real options named. Do not weaken the intent.

**WO-6 — spreadsheet linkage (P2).**
`src/bp/product/spreadsheets.py` → `_accounting_rows()` reads only `statements_export`
(trial_balance, income_statement, balance_sheet, cash_flow, reconciliation, notes), `trial_balance`,
`journal`, `checks`. Add sheets for `t_accounts_export`, `equity_statement_export`, `closing_balances`,
`flags` and `opening_lines_next` (all are already in the appendix). Emit a structured `schedules`
block from `src/bp/accounts.py` so the depreciation/accrual/prepayment/deferred-income workings are
broken out, not just posted. Then decide the formula-cell question (cells are currently inline
strings, so nothing recalculates).

**WO-7 — doc hygiene (P2).** `docs/OPEN_ISSUES.md` (failure count 58 vs 53 observed),
`docs/HANDOFF_NEXT_CHAT.md` §1 (claims `PROFILES` has two entries; it has 68),
`docs/CONDUCTOR_MANUAL.md` §13 ("Only break-even is registered"; `capabilities.ENTRIES` has 126;
"auto-completion runs for Five Forces and PESTEL"; 68 profiles now),
`docs/HANDOFF.md` / `HOME.md` / `CONTRIBUTORS.md` test counts.

### Doc drift also noted (do not trust these files)
- `docs/HANDOFF_NEXT_CHAT.md` §1 claims `PROFILES` has **two** entries (five_forces, pestel). It has **68**.
- `CONDUCTOR_MANUAL.md` §13 says "Only break-even is registered today" for computations. `capabilities.ENTRIES`
  has **126**. The manual is behind the code here.
- `CONDUCTOR_MANUAL.md` §13 says "Framework auto-completion runs for Porter's Five Forces and PESTEL on
  one engine." Completion profiles now number 68.

### Recommended sequence (for the next discussion)
1. **WO-1** — restore the refusal path. Two file restores, not a redesign (see ROOT CAUSE above).
   **Correctness issue, not coverage** — while briefs are silently answered with PESTEL, the product
   overstates its own coverage and the student receives a confident, on-topic, wrong-genre paper.
   Afterwards, close the one over-refusal (an explicitly named framework must bypass the subject
   guard) and consider making the council the default.
2. **WO-2 + WO-3** — reconcile the catalogue with reality: register the 32 orphan profiles, build the
   8 missing worksheet profiles, regenerate `status_short` from `LIBRARY`. Low effort, large honest gain.
3. **WO-4 + WO-5** — fix the 14 real completion defects and update the 39 stale profile tests. Suite
   must be green before the next build.
4. **WO-6** — spreadsheet linkage (T-accounts, equity statement, flags, schedules into the `.xlsx`;
   then the formula-cell decision).
5. **WO-7** — doc hygiene, then the larger architectural additions (problem-set profile, short-form
   document family, artefact binding), and settle option A/B/C against the corrected coverage numbers.
---


To discuss / redesign only when explicitly instructed (do NOT check automatically):
- Read: corpus-db/CORPUS_DB.md (policy) + business_pipeline_v0.12/business_pipeline/docs/CONDUCTOR_MANUAL.md + HANDOFF.md (current build).
- Then read external taxonomy: C:\Users\Roderick\Downloads\BUSINESS ACTIVITY COVERAGE/business_assignment_taxonomy.md (primary); .docx mirrors.
- Then consider the three options already discussed (A = corpus scope expansion for written-analysis §1/§4/§5/§6-written/§7-reports; B = separate computation-verification layer for §2/§3-model/§6-quant; C = both with named exclusions; exclusions: country-specific, qualification/platform/industry-vertical).
- Before any redesign action: resolve Q-19 (enrichment qualification + copyright check for cross-student reuse, `licence` NULL / `licence_verified=0` default, G-07 protects R2 bucket); confirm target (HANDOFF.md vs CORPUS_DB.md); confirm option (A/B/C). No silent substitution.

This file is the durable pointer for any follow-up model / chat. Do not activate content above without explicit instruction.
