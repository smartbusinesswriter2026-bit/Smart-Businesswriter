# QA state

## Session 11 — `calculator` (2026-11-03) · branch `corpus/merge-v1`, opening commit `05efb8f`

**Surface chosen by the work order** — not a shelf: the rail panel `#panel-calculator`, its route, its
guard, and the **148 launchable tools** it offers. Manual: `qa/manual/calculator.md` (10 sections,
25 E-rows). Suite: `tests/test_calculator_acceptance.py` (**25 tests, 25 passed**). Probe:
`qa/probe_calculator.py`. Evidence: `qa/evidence/calculator/` (148 delivered papers).

**This surface had no manual and no suite of its own.** Four modules asserted *membership* — the union
of the groups (`CalculatorGuardTest`), the preset↔method pairs, the method resolution
(`SubjectToolsResolve`) — and **nothing launched a tool the way the panel launches it**. Coverage was
complete but unproved.

### Baseline (measured here, not assumed)

| Measure | Documented | Measured |
|---|---:|---:|
| Tests | 3564 | **3564** at the opening tree; **3589** after this session's 25 |
| Failures | — | **3** — all `test_product_intake` PDF cases, `NETWORK-ENV` (optional `pypdf` not installed); 0 on this surface |
| Errors | — | **1** — the same PDF text-layer case |
| Wall time | — | 50 s |

**0 of the 4 is on this surface.** Two were the documented env gap (optional `pypdf`), one was
`test_docs_sync`'s count, which this session moved to 3589 and is now green.

**Inventory, re-measured:** `compute_tools()` **148** · `CALCULATOR_GROUPS` **8 groups / 206 entries /
148 distinct** · 0 missing from the calculator · 0 keys off a page · 144 presets each running the method
it claims · **4** typed tools · **131 of 148** keys are not `LIBRARY` ids · 1 composite
(`case_decision`) · `LIBRARY` 142 / `PRESETS` 144 / fixture in sync. **The work order's "33 shared
keys" does not reproduce: the tree measures 31** (DISPUTED in the manual, pinned at 31 in the suite).

### Delivered

- **All 148 tools launched and read on the artefact** — `--tools`: 148/148 pass every gate; two runs
  byte-identical 148/148; the 31 shared keys agree from every group (0 disagreements); unit sweep 0.
- **The harness was proved before it judged**: `operations` 14/14, `research` 21/21, zero problems —
  after it had reported three problems of its own (D-CALC-04).
- **D-CALC-01 / D-CALC-02 fixed (B-217)**: `currency_convert.rate` and `real_option`'s four ratios
  declared 6 dp and printed `0.920000` / `0.617058`; now 4 dp, `Rate: 0.9200` / `Delta: 0.6171`.
- **D-CALC-03 fixed**: an unknown calculator route answered `422 case id must be 12 lowercase hex
  characters`; now `404 unknown route …`.
- **Twelve wiring invariants W-01…W-12 as 25 tests**, with a negative control (`test_E_calc_024`).

### Next subject and its top three risks

**Next: `marketing`** (the shelf whose B-211 landed while this session's work order was being written;
it has a manual section in `QA_DEFECTS.md` but **no full E-row table and no acceptance suite yet** —
the same "complete but unproved" shape this session closed for the calculator).

1. **The six-decimal class is not extinct.** D-RES-05 (B-214) fixed `logistic_regression`; this session
   found two more under B-217. Any of the 148 tools can declare `("ratio", 6)` again, and only
   `test_E_calc_013` now catches it *for the calculator surface*. **Risk: a new method ships at 6 dp
   and no shelf suite reads it.**
2. **Marketing's 22 calculator entries are 16 distinct tools, most of them shared.** `chi_square`,
   `alpha`, `forecast`, `power` and `unitecon` are filed on several shelves, so a defect in one of them
   moves four shelves' papers at once — and marketing's own suite does not exist to notice.
3. **The ask router's vocabulary is hand-maintained.** `CLUES` / `INPUT_WORDS` in `calc_router.py` are
   literals; a new tool that nobody adds a clue for is reachable only by exact label, and the failure
   mode is a silent `unsupported` rather than an error.



## Session 10 — `people` (2026-11-03) · branch `corpus/merge-v1`, opening commit `b393743`

**Subject chosen by the work order.** Manual: `qa/manual/people.md` (12 sections, 84 E-rows).
Suite: `tests/test_subject_people_acceptance.py` (**84 tests, 84 passed, 0 skipped**; 84 defined,
84 collected). Evidence: `qa/evidence/people/` (the produced `.docx`, its stripped text, the unit
audit of all ten calculators, the parity transcript).

**This was the last shelf with no manual and no acceptance suite**, and the only shelf carrying
people-specific arithmetic: `trainingroi`, `labourtightness` and `programmecost` are presets of
`return_on_investment`, `labour_market` and `cost_effectiveness`, so their defects are the core's.

### Baseline (measured here, not assumed)

| Measure | Documented | Measured |
|---|---:|---:|
| Tests | 3409 | **3409** |
| Failures | — | **1** (`test_sources…test_brave_failure_falls_back_to_firecrawl`, NETWORK-ENV) |
| Errors | — | **0** |
| Wall time | — | 1139 s |

Raw output: `qa/baseline/ppl-before-suite-err.txt`. **0 of the 1 is on this shelf.**

**Inventory, re-measured:** 10 tools · 19 worksheets (all draftable) · **6 tiles** (the work order
said 5 and then listed six — six is the truth) · 0 records · 0 theories · 0 glossary terms ·
18 profiles with `subject == "people"`, every one reachable.

### The four scope questions, answered

1. **The Reward tile is declared and visible** — the tile's own `note`, the page's `guidance` and
   `does_not[0]` all say why it is empty. It was not filled.
2. **Item 11 is settled and three of its findings are real.** 11a's key is correct (the unit is
   not); 11b divides a count by a rate (10 / 0.05 = **200**); 11c's serialization is right but the
   number **never reaches the paper**. Ledgered D-PPL-01, D-PPL-02, D-PPL-03.
3. **No record promises a calculator it cannot start** — the shelf puts no record on the page.
4. **Every worksheet's group is a declared tile**, and every tile renders exactly its group.

### Delivered

| Artefact | Content |
|---|---|
| `qa/manual/people.md` | The **30-item inventory** with a per-item verdict, a **ranked owner-gated proposal** (6 items, nothing built), 84 E-rows reconciled 1:1, the **unit audit** of all 96 outputs, the parity section, the V-01…V-20 reading of one paper, the ledger, the gate table |
| `tests/test_subject_people_acceptance.py` | 84 tests — independent recomputation for all ten calculators, the unit audit, the boundary and refusal sweep, the parity tests, the page tests |
| `qa/evidence/people/` | `kotter-paper.docx` (27,166 bytes), `kotter-paper.txt` (1,581 words), `unit-audit.txt`, `parity.txt`, `evidence.json` |
| `qa/baseline/ppl-before-suite-err.txt`, `ppl-after-suite-err.txt` | Baseline and closing measurements |

### Fixed — one core change (B-216, the owner's option A) and two presentation fixes

- **Presentation, this session:** the Analytics tile said "statistics" while three of its ten
  calculators are money arithmetic — its `what` now names both; and `docs/CURRICULUM_MAP.md`'s People
  row now names the ten methods, six tiles and nineteen worksheets it had omitted.
- **Core, on the owner's instruction (option A) — B-216:** the `@unit` currency ordering bug
  (`orchestrator`), one new composite unit `currency_per_effect` (`quantity.display`), the CEA typing
  (ICER → cost-per-effect, effects → `units`), `mde`/`se` → `units`, `years` → `(periods, 2)`, and
  Item 11b — `labour_market` now divides by an `unemployed` **count** (tightness **0.2000**), with a
  sixth declared check and a template sentence that states the figure. The fixture was regenerated by
  `scripts/econ_shelf.py --fixture`. **10 of the 11 trap tests fail on the pre-fix code.**
- **Still ledgered:** **D-PPL-03** (MINOR — two option names that slug the same collapse one ratio),
  **D-PPL-04** (MINOR — "0 step(s) are recorded as gaps" beside seven unsourced parts).
- **Gaps:** G-PPL-01 Reward tile (declared), G-PPL-02 a zero-row chi-square (declared on the page),
  G-PPL-03 `power` promises a sample size it does not compute, G-PPL-04 no glossary,
  G-PPL-05 weights not validated (disclosed). G-PPL-06 is **closed by the fix**: the tool no longer
  takes a rate at all.
- **`docs/OPEN_ISSUES.md` Items 11 and 12 are settled:** Item 11 as three defects (above); Item 12
  **closed as superseded** — `test_people_frameworks` already runs all eighteen frameworks through
  all three drafting variants, and the new module adds the missing real-`.docx` limb.
- **No change in `src/bp/methods.py`**, so the pinned fixture is untouched and `econ_shelf --check`
  still says "frozen fixture: in sync".

### Gates at close

| gate | result |
|---|---|
| `tests/test_subject_people_acceptance.py` | **85 tests, 85 passed, 0 skipped** |
| defined vs collected ids | **85 / 85, none missing** |
| the traps, on the pre-fix code | **10 of 11 fail** (five source files stashed, re-run, restored) |
| core change slice | `test_frozen_contract`, `test_method_contracts`, `test_people_frameworks`, economics and entrepreneurship acceptance — **234 tests, all passed** |
| `scripts/econ_shelf.py --check` | **frozen fixture: in sync** |
| `qa/check_page_syntax.py` | **page syntax: OK** |
| documented test count | **3574** (3409 at this session's open; +84 here, +71 from the lanes that landed during it), written into `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md` |
| full suite | before **3409 tests, 1 failure, 0 errors**; after the rebase **3564 tests** measured with `test_docs_sync._suite_count()` |

---

## Next subject: `marketing` — and its top three risks

`marketing` is the last shelf with a page, a catalogue and calculators but **no acceptance manual**:
every other shelf now has one — `research` gained its own in a lane that landed while this session was
in flight, and this shelf's is `qa/manual/people.md`.

1. **Reachability will dominate its inventory.** `docs/OPEN_ISSUES.md` Item 15 measures 16 marketing
   worksheets that are built and offered on no shelf page (they appear as record rows carrying the
   status "Worksheet" that cannot be opened), plus `STR-19` and `CHG-15` on no page at all. That
   session must decide which shelf owns each one — a curriculum decision, not a wiring fix.
2. **Two declared-template defects are already known and unfixed.** `template_servqual` is declared
   in both `CANVAS_BLOCKS` and `MATRIX_META` (the D-MKT-04 family), and `MKT-07` (SERVQUAL) is
   deliberately hidden by B-198 — so the suite's green depends on the hiding, not on the form.
3. **D-PPL-01 will surface there too.** Marketing shares `alpha`, `chi_square`, `power`, `unitecon`,
   `cohort` and `abtest`; every marketing tool that returns a `@unit` output under a currency
   request prints that unit with a money prefix, and the unit audit is the only thing that catches
   it. Run the audit before anything else.

---

## Session 11 — `research` (2026-11-03) · branch `corpus/merge-v1`, opening commit `6c7073c`

**Subject chosen by the work order.** Manual: `qa/manual/research.md` (53 E-rows, 10 sections).
Suite: `tests/test_subject_research_acceptance.py` (**53 tests, 53 passed**). Evidence:
`qa/evidence/research/` (21 papers, `.docx` and stripped `.txt`), probe `qa/probe_research_shelf.py`.

**The work order's snapshot was stale and that is itself the first finding.** It named `b393743` and
"in sync"; the tree was `6c7073c` (marketing's B-211) and **2 ahead of origin**, with a dirty tree from
live lanes. The documented test count (3478) did not match the loader (3418) at the opening.

### Baseline (measured here, not assumed)

| Measure | Work order | Measured at opening | Measured at close |
|---|---:|---:|---:|
| Tests (`TestLoader().discover`) | 3409 | **3418** | **3478** (3480 while a live lane's two uncommitted bundle tests sit in the tree) |
| Failures / errors | 0 / 0 | **1 / 0 in the 2974 tests a batch run reached** — `test_sources…firecrawl_fallback` (NETWORK-ENV, not this shelf). The batch was stopped in `test_subject_management_acceptance` (that suite takes 235 s alone); every suite was then run separately and is green | see `qa/baseline/suite-after-err.txt`, `shelves8.txt`, `mgt2.txt` |
| `LIBRARY` / `PRESETS` / fixture | 142 / 144 / 142–144 | 142 / 144 / 142–144 | unchanged |
| Tools / worksheets / tiles / records | 21 / 0 / 0 / 10 | 21 / 0 / **0** / 10 (3 computed, 7 read-only) | 21 / 0 / **4** / 10 (**8 computed**, 2 read-only) |

**Inventory confirmed exactly as the work order stated**, except the two defects it predicted: the
seven records saying "Method not built" (five of them denied a shipped method) and the page's inability
to group anything.

### Delivered

| Artefact | Content |
|---|---|
| `qa/manual/research.md` | 10 sections: the inventory reconciled against the catalogue, the four tiles, ten record rows, 21 tool rows, 53 E-rows with sources, a DISPUTED table (six judgement calls), the traceability matrix, the defect ledger, declared gaps, residual risk |
| `tests/test_subject_research_acceptance.py` | 53 tests: the shelf against the catalogue, the two vocabularies (8 keys / 21 methods), record honesty against the registry, eleven paper gates read on the artefact, **20 hand-arithmetic figure rows**, refusals with reasons, and the three shelf-wide traps (including "prove the harness on operations") |
| `qa/probe_research_shelf.py` | inventory, double resolution, records, contract, papers, figures, `--verify` (61 figures, 0 disagreements), `--subject operations --prove` |
| `qa/evidence/research/` | the 21 papers as produced |
| `qa/baseline/` | baseline suite, probe transcripts, pytest digests |

### Defects

D-RES-01 (five records denying shipped methods) **FIXED** · D-RES-03 (dict input printed as a Python
repr in every column-map paper) **FIXED** · D-RES-06 (0 tiles / 0 groups, page could not group) **FIXED
by B-213** · D-RES-07 (doc said 140/142; measured 142/144) **FIXED in the doc** · D-RES-02 (13 keys are
not library ids) **PINNED** · D-RES-04 (`power`, `missing` printed no honesty heading — **re-measured:
the caveats existed, the heading did not**) **FIXED by B-215** (a fifth field `this_method`, added only
when the four standard fields are empty) · D-RES-05 (`logistic_regression` declared 6 dp) **FIXED by
B-214 (4 dp; the paper reads `-22.8067`)**.

### Next subject, and its top three risks

**`marketing` is the last shelf without an acceptance manual** (11 shelves, 10 with manuals; the People shelf has `qa/manual/people.md` at 51,696 bytes with 84 acceptance tests, and the Research shelf has `qa/manual/research.md` with 53 E-rows). Its top three risks, from what this session measured on the adjacent shelves:

1. **Reachability will dominate its inventory.** `docs/OPEN_ISSUES.md` Item 15 measures 16 marketing worksheets that are built and offered on no shelf page (they appear as record rows carrying the status "Worksheet" that cannot be opened), plus `STR-19` and `CHG-15` on no page at all. That session must decide which shelf owns each one — a curriculum decision, not a wiring fix.
2. **Two declared-template defects are already known and unfixed.** `template_servqual` is declared in both `CANVAS_BLOCKS` and `MATRIX_META` (the D-MKT-04 family), and `MKT-07` (SERVQUAL) is deliberately hidden by B-198 — so the suite's green depends on the hiding, not on the form.
3. **D-PPL-01 will surface there too.** Marketing shares `alpha`, `chi_square`, `power`, `unitecon`, `cohort` and `abtest`; every marketing tool that returns a `@unit` output under a currency request prints that unit with a money prefix, and the unit audit is the only thing that catches it. Run the audit before anything else.

**Follow-up session (after marketing): Generic shelf-invariant suite (Option D).** The `test_shelf_invariants.py` added this session pins 6 invariants. The next session should extend it to a full generic suite that walks `subjects.catalogue()` and asserts for all 11 shelves: tools resolve (preset→method), no record denies a shipped method, every worksheet/tool/record sits in exactly one tile, catalogue row reconciles, tile keys match tool groups, and tiles cover all items. Run in report-only form first, list findings, then choose fixes. This will surface real failures on shelves not opened this session.

---


## Session 9 — `supply-chain` (2026-11-03) · branch `corpus/merge-v1`, opening commit `f699579`, rebased onto `2cd3347`

**Subject chosen by the work order.** Manual: `qa/manual/supply-chain.md` (62 E-rows, 12 sections).
Suite: `tests/test_subject_supply_chain_acceptance.py` (**68 tests, 68 passed**). Evidence:
`qa/evidence/supply-chain/` (the produced `.docx`, its stripped XML, the unit audit, the parity
transcript, the worksheet-completion transcript).

**A second lane closed two of this session's findings while it was in flight.** The Operations
session (`2cd3347`, "the shelf is verified end to end") repaired `templates.EXAMPLES` (D-SCL-03)
and the duplicated in-text citation in `completion._sections` (D-SCL-04). This session rebased
onto it, re-produced its evidence paper and re-read it, and records both as fixed by that lane
rather than as its own work.

### Baseline (measured here, not assumed)

| Measure | Documented | Measured |
|---|---:|---:|
| Tests | 3184 | **3171** |
| Failures | 1 known | **6** |
| Errors | — | **4** |
| Wall time | — | 946 s |

10 problems, all classified in the manual §1.1: **0 on this shelf**. Four were
`test_operations_frameworks.ExampleTest` errors (`KeyError: 'template_sipoc'` — stale
`templates.EXAMPLES`, D-SCL-03, since repaired by the Operations lane), one was the documented
`test_docs_sync` count drift (fixed here), one is the known rail test, two are foreign-lane
(paper store, balanced scorecard), two are network-dependent. On the final tree the same suite
runs **3314 tests with 4 failures and 0 errors**.

**Inventory confirmed exactly as the work order stated:** 8 tools · 11 worksheets (one not
draftable) · 9 records (two read-only) · 0 theories · 20 glossary terms · 0 profiles with
`subject == "supply-chain"`.

### Delivered

| Artefact | Content |
|---|---|
| `qa/manual/supply-chain.md` | The **28-item inventory** with a per-item verdict, a **ranked owner-gated proposal** (7 frameworks, nothing built), 62 E-rows reconciled 1:1, the **unit audit** of every output, the parity table, the V-01…V-20 reading of one paper, the defect ledger, residual risk |
| `tests/test_subject_supply_chain_acceptance.py` | 68 tests — independent recomputation for all eight methods, the parity test against Operations, the boundary and refusal sweep, the unit audit with four traps |
| `qa/evidence/supply-chain/` | `sipoc-paper.docx` (23,074 bytes), `sipoc-paper.txt`, `unit-audit.txt`, `parity.txt`, `worksheet-completion.txt` |
| `qa/baseline/scl-*` | Baseline and after measurements |

### Fixed (6) and settled (1)

- **D-SCL-01 (BLOCKER, UNITS) — the core fix, on the owner's instruction (option A).**
  `queue_analysis.average_in_queue` / `average_in_system` were typed `ratio`,
  `inventory_policy.days_per_year` was typed `currency`, `unit_economics.payback_periods` was
  typed `ratio`, and `periods` was absent from the currency-exempt list — so the delivered queue
  report read **"a wait of PHP 0.1250 periods"**. Fixed in three `typing` functions in
  `src/bp/methods.py` and one tuple in `src/bp/orchestrator.py`. Four trap tests fail on the
  pre-fix code, proved by stashing the source and re-running.
- **D-SCL-02 (MINOR, declaration).** A worksheet with no drafting button now says why, on the
  card, before the click: `detail()` derives a `draft_note` from the worksheet's own
  `evidence_needs` and `capabilityCard` renders it (`test_E_scl_006`, `test_E_scl_067`).
- **D-SCL-05 (MINOR, presentation).** `completion.complete(..., byline=[...])` now carries the
  student's own title-page lines to the `.docx`; an absent byline still prints no block and
  invents no name (`test_E_scl_068`).
- **D-SCL-06 (MINOR, doc drift).** The handoff's two open commercial questions are logged as
  **B-204** / **B-205** with status `OPEN`; `test_docs_sync` is **7/7 green**.
- **G-scl-01 (GAP, reachability).** A `computed` record whose calculator is on another shelf now
  says so and names that shelf, derived from `SUBJECT_DEFS` (`test_E_scl_066`).
- **Documented test count** and the **`CURRICULUM_MAP.md` supply-chain row** (as before).
- **G-scl-05 (GAP, honesty) — SETTLED.** V-12 now reads "an **accepted** item", recorded in
  `VALIDATION_HARNESS.md` §5 and its §6.3 change log.
- **`docs/CURRICULUM_MAP.md` supply-chain row** said the shelf carried "the SIPOC and value stream
  worksheets" when it carries all eleven, and did not name the unbuilt LP/network method. Both
  corrected; pinned by `test_E_scl_062`.

### Ledgered / declared (5 defects + 5 gaps)

- **D-SCL-01 (BLOCKER class, UNIT) — FIXED on the owner's instruction (option A).** `days_per_year`
  typed currency, the two queue lengths typed ratio, `payback_periods` typed ratio, and `periods`
  absent from the currency-exempt list — the delivered queue report read "a wait of PHP 0.1250
  periods". Three `typing` functions and one tuple; four traps that fail on the old code.
- **D-SCL-02 (MINOR, declaration).** `OPS-03` has no drafting button while its catalogue row still
  reads "worksheet available"; nothing says why. Pinned by `test_E_scl_006`.
- **D-SCL-03 (MINOR, test fixture) — FIXED by the Operations session `2cd3347`.** Four
  `test_operations_frameworks` errors (`KeyError: 'template_sipoc'`) meant the shared worksheet
  test could not run; the other lane added the eleven worked examples.
- **D-SCL-04 (MINOR, presentation) — FIXED by the Operations session `2cd3347`.** A block with one
  sourced item printed its in-text citation twice; the re-produced paper cites once.
- **D-SCL-05 (MINOR, presentation).** No byline block on the title page (V-20 partial).
- **G-scl-01** three `computed` records (`OPS-09`, `QNT-OPS-05`, `QNT-OPS-06`) link methods with
  **no tile on this page**. **G-scl-02** a monthly demand with a daily lead time is taken as given
  and disclosed, not converted. **G-scl-03** a plausible-but-wrong decimal rate is taken as given
  and disclosed. **G-scl-04** all eleven profiles served here declare `subject: "operations"`;
  zero declare `subject: "supply-chain"`. **G-scl-05** V-12's word "sourced" means one thing in
  the rule text and another in `completion.missing()` — **DISPUTED, owner's reading needed**.

### The scope question, settled

1. **Are the gaps stated where the student sees them? Yes.** `QNT-OPS-03` (LP/network
   optimisation) and `QNT-OPS-07` (SPC measurement checks) both **render on this page** as
   read-only records, because this shelf derives its catalogue from the discipline tags while
   Operations lists its ids explicitly and omits both. That is the shelf being deliberately wider
   than Operations, and it is the design working. **No defect.**
2. **Frameworks of its own?** Seven proposed and ranked (safety-stock policy, ABC–XYZ, supplier
   scorecard, bullwhip, network design, reverse logistics, Incoterms). **Nothing built.**
3. **`missing_data_bounds` placement?** Defensible and stays — settled on one line of the method's
   own output ("Under the extreme-case convention the complete-data mean lies between 12.00 and
   14.00"), which is a demand-planning sentence, not a statistics one. No owner decision needed.

### Gates at close

| Gate | Result |
|---|---|
| Shelf acceptance suite | **68 passed, 0 skipped** |
| Live click-through on **8002** (the owner's 8001 left alone) | **8 of 8 calculators delivered over HTTP, every check passed; 8 of 8 papers download as `.docx`; 3 screenshots** — `qa/evidence/supply-chain/clickthrough.json` |
| `test_docs_sync` | **7/7 green** — the count assertion and the decision crosswalk both pass |
| `test_frozen_contract` | **passed** (no core change) |
| Full suite before (opening tree `f699579`) | **3171 tests, 6 failures, 4 errors** |
| Full suite after (pre-rebase tree) | **3227 tests, 4 failures, 4 errors** — 0 new, 2 fewer (the docs-count fix and the flaky Brave→Firecrawl network test) |
| Rebased onto `2cd3347` | **3314 tests** measured (3231 upstream + 68 here); shelf suite green; documents set to 3314 |
| Full suite, measured on `2cd3347` + an earlier version of this commit | **3287 tests, 4 failures, 0 errors** — 0 new, 0 errors. **Disclosed:** that run collected only 56 of this module's tests; six (E-scl-007 … 012) had been appended after the `if __name__` guard and never ran. Found by auditing defined-vs-collected ids, moved into their class, and three traps were added on top. The six are page/record/glossary assertions with no numeric content, so the failure count stands — but the claim was measured with them absent |
| Full suite, final tree (`c910d27`) | **3372 tests, 1 failure, 9 errors** — all ten in the Business Bundle lane's in-flight billing/export tests (`KeyError: 'unlimited'`); zero diff between my commit and its parent on billing/exports/credits. **None on this shelf** |
| `scripts/econ_shelf.py --check` | **frozen fixture: in sync** |
| Live click-through on 8001 | **NOT RUN** — see the manual §10; the session's largest gap |

### Next subject and its top three risks

**Next: `people` (People & organisation).** It is the last shelf that owns its own framework
profiles (18 of them) and has neither an acceptance manual nor an acceptance suite; `operations`
was closed by the other lane in `2cd3347` while this session ran, and `marketing` is still open
from session 6.

1. **D-SCL-01 is still live on every shelf that shows `queue_analysis`.** A paper can contain
   "a wait of PHP 0.1250 periods" today. The fix is core and owner-gated; whoever takes the next
   shelf should ask for it once and let it land for all shelves together.
2. **The `subject` field is empty for most of the product.** 0 profiles declare `supply-chain`;
   the harness still has no canonical crosswalk (§7 of the harness doc), so a subject-by-subject
   report depends on a hand-kept map.
3. **A finding can be fixed underneath you.** Two of this session's five defects were repaired by
   another lane mid-flight. Re-read before you commit, and re-measure before you report.

---

## Session 8 — `operations` (2026-11-03) · branch `corpus/merge-v1`, opening commit `1660f25`

**Subject chosen by the work order.** Manual: `qa/manual/operations.md` (46 E-rows). Suite:
`tests/test_subject_operations_acceptance.py` (**46 tests**). Probes: `qa/probe_ops_shelf.py`
(inventory, forms, records, glossary, block provenance, the auto-fill trap, the eleven papers, the
fourteen tool papers) and `qa/probe_mgt_debug.py` (repaired, then pointed at this shelf).

### Baseline (measured here, not assumed)

| Measure | Documented | Measured |
|---|---:|---:|
| Tests | 3165 | **3184** |
| Failures | 4 | **5** |
| Errors | 4 | **4** |
| Wall time | — | 945 s |

The four errors were **this shelf's** — `test_operations_frameworks.ExampleTest` ×4, `KeyError:
'template_sipoc'` — exactly as the work order predicted. The five failures were classified in
`qa/manual/operations.md` §6.2: three KNOWN-HISTORICAL (chat hung dimension, paper store, web rail),
one NETWORK-ENV (Brave→Firecrawl), and one **NEW-UNEXPLAINED→FOREIGN** —
`template_balanced_scorecard/organisational_capacity` cannot accept evidence for its own query, a
profile the project-management lane added in `f699579` while this session ran.

**The baseline is 3184, not the documented 3165**, and the tree already carried another lane's
in-flight work when the run started; both facts are recorded rather than smoothed. **Inventory
confirmed exactly as the work order stated:** 14 tools · 11 worksheets (OPS-03 not draftable) ·
7 records · 0 theories · 20 glossary terms · 11 profiles · all 11 shared with `supply-chain`.

### Delivered

| Artefact | Content |
|---|---|
| `qa/manual/operations.md` | one row per tool (14), worksheet (11), record (7), glossary term (20) and UI surface, each citing its source of truth; 46 E-rows reconciled 1:1 with the traceability matrix; the V-01…V-20 reading of the eleven papers; the defect ledger; residual risk |
| `tests/test_subject_operations_acceptance.py` | 46 tests, 46 passed |
| `qa/probe_ops_shelf.py` | the reproducible evidence behind every claim, including the auto-fill trap and the eleven + fourteen papers |
| `matrix.LAYOUTS` (eleven layouts) | every worksheet paper now carries its grid: one labelled cell per block, the items already accepted or the gap already named (G-ops-01 closed, B-202) |
| `subjects.OPERATIONS_TILES` (three tiles) + the record map | the page groups the shelf: 11 worksheets, 14 calculators and 7 records, each in exactly one tile, nothing dropped (D-OPS-06 / G-ops-02 closed, B-206) |
| `qa/evidence/operations/` | the eleven worksheet papers and fourteen tool papers (`.docx` + the `.txt` a reader sees) |
| `qa/baseline/ops-*` | baseline and after measurements, probe output, acceptance run, completion slice |

### Fixed (5 ledger rows, 3 found only by reading the produced .docx)

- **D-OPS-01** (MAJOR, wiring): no worksheet had a worked example, so `ExampleTest` errored instead
  of testing. Eleven synthetic examples added, each passing its template's own `validate()` and every
  check. Trap tests `test_E_ops_007`, `test_E_ops_043`.
- **D-OPS-03** (BLOCKER, honesty; B-201): the borrowing rule matched the student's sentence against
  the *retrieval* cue list, so â€œThe manager reviews the change next termâ€ was printed as what PDCA's
  act stage standardised. A block now declares `quote_cues`; 59 blocks declared; the trap brief
  produces **0** quotes. Trap tests `test_E_ops_023`, `test_E_ops_037`, `test_E_ops_038`.
- **D-OPS-02** (MAJOR, honesty): the conclusion named one part both strongest and weakest and ranked
  the parts. Trap tests `test_E_ops_020`, `test_E_ops_040`.
- **D-OPS-04** (MAJOR, honesty): every sourced cell printed its citation twice. Trap tests
  `test_E_ops_016`, `test_E_ops_045`.
- **D-OPS-05** (MINOR, honesty): a `gap` cell dropped the probe its profile declares. Trap tests
  `test_E_ops_013`, `test_E_ops_024`.
- **G-ops-01** (declared → FIXED on the owner's instruction): none of the eleven papers drew a
  figure because `matrix.LAYOUTS` had no operations entry. Eleven layouts added (B-202); trap test
  `test_E_ops_018` now asserts one labelled cell per block, none empty, and the figure in the paper.
- **D-OPS-06 / G-ops-02** (declared → FIXED on the owner's instruction): the eleven worksheets sat in
  one flat list while three other shelves group theirs. Three tiles added (B-206) — keys taken from the
  shelf's own tool groups — plus a record map, so seven computed records are not printed as "read and
  cite" cards. Trap test `test_E_ops_010`.

### Ledgered / declared

D-OPS-06 / G-ops-02 (no worksheet groups: one flat list), D-OPS-07 (a process-unit query repeats the
unit; shared by four shelves), G-ops-01 (**no figure in any of the eleven papers** — `matrix.LAYOUTS`
has no operations entry; a presentation decision), G-ops-03 (one brief sentence can fill two adjacent
SIPOC parts), G-ops-04 (no theories, by design), G-ops-05 (the four shared capabilities).

### Gates at close

| Gate | Result |
|---|---|
| Shelf acceptance suite | **46 passed** (`qa/baseline/ops-acceptance-out.txt`) |
| `test_operations_frameworks` | **50 passed** (was 49 with 4 errors) |
| Framework-completion slice | **584 passed, 0 failed** (`qa/baseline/ops-completion-slice-out.txt`) |
| `qa/probe_mgt_debug.py` on this shelf | **0 problems** (`qa/baseline/ops-probe-after-harness-fix.txt`) |
| `qa/check_page_syntax.py` | **page syntax: OK** |
| `test_docs_sync` | **7 passed** (build 1.74; 3236 tests set from the loader) |
| Full suite | **3409 tests, 0 failures, 0 errors** on the integrated tree |

### Full suite

| | Tests | Failures | Errors | Wall time |
|---|---:|---:|---:|---:|
| Before (`qa/baseline/ops-base-suite-err.txt`) | 3184 | 5 | 4 | 945 s |
| After (`qa/baseline/ops-after-suite-err.txt`) | 3236 | **7** | **0** | 1127 s |
| Final, on the integrated tree (`qa/baseline/ops-final-suite-err.txt`) | **3409** | **0** | **0** | 1093 s |

**The four errors are gone** — that was this shelf's one defect, `ExampleTest` building eleven
worksheets that had no example. **None of the seven failures is on this shelf.** All seven classified
from `qa/baseline/ops-after-failure-names.txt`:

| Failure | Class |
|---|---|
| `test_chat.ResearchTest.test_a_hung_dimension_becomes_a_named_gap_instead_of_blocking` | KNOWN-HISTORICAL (in the baseline) |
| `test_paper_documents.DocumentRouteTest.test_generating_a_paper_saves_it_to_the_store` | KNOWN-HISTORICAL (in the baseline) |
| `test_product_subjects.ServedUiContractTest.test_the_rail_carries_the_portfolio_lab_above_the_calculator` | KNOWN-HISTORICAL (in the baseline) |
| `test_product_profile_cues...test_every_researched_block_accepts_its_own_query` | FOREIGN (project-management's `balanced_scorecard`, added in `f699579`; in the baseline) |
| `test_docs_sync...test_every_doc_file_is_covered_by_the_home_documentation_spine` | FOREIGN — `docs/BUNDLE_PRICING_HANDOFF.md` is another lane's untracked file, absent from HOME's spine |
| `test_docs_sync...test_every_mentioned_decision_id_has_a_row_in_the_decision_register` | FOREIGN — that lane's in-flight `docs/HANDOFF.md` mentions `B-180a`/`B-180b` with no decision row |
| `test_subject_finance_acceptance.test_032__the_shelf_declares_no_tiles…` | FOREIGN — `subjects.SUBJECT_TILES` now has `project-management`, from that lane's uncommitted `subjects.py` |

The one baseline failure that is **no longer failing** is the network-dependent
`test_sources.SearchTest.test_brave_failure_falls_back_to_firecrawl` (NETWORK-ENV): the 503 in the
after-run's log shows the live service answered differently, which is why it is filed as environment,
not product.

**The documented count is 3409**, set from `unittest.TestLoader().discover("tests")` on the integrated
tree, and the final run is **3409 tests, 0 failures, 0 errors**. Re-measure from the loader, never from
the doc: the count moved four times while this session ran.

### Next subject and its top three risks

**Next: `supply-chain`** — the one shelf with no acceptance manual and no acceptance suite, and it
shares **all eleven** of this shelf's worksheets.

1. **It inherits every fix in this commit.** `quote_cues`, the citation rule, the conclusion and the
   `gap` probe all reach its papers. Its brief produces different cells, so re-measure the trap on
   *its* page rather than assuming the operations measurement carries.
2. **The shared page is a real coupling.** `OPS-01…08` and `OPS-10…12` sit on both shelves; a change
   to a shared profile changes a supply-chain paper. `test_E_ops_044` is the pattern for the check.
3. **Inventory arithmetic is the dangerous part.** `inventory_policy` (EOQ, reorder point) mixes
   money, shares and periods; recompute by hand first, then by a second formula — never the method's
   own output against itself. D-OPS-07 (a repeated unit in the query) is still open and will be
   visible there too.


---

## Session 7 — `project-management` (2026-11-03) · branch `corpus/merge-v1`, opening commit `84490ec`

**Subject chosen by the work order.** Manual: `qa/manual/project-management.md` (62 E-rows).
Suite: `tests/test_subject_project_management_acceptance.py` (**62 tests**). Probes:
`qa/probe_pm_shelf.py` (inventory, forms, K1 audit, K5 refusals), `qa/probe_pm_paper.py`
(builds the .docx and reads `word/document.xml`).

### Baseline (measured here, not assumed)

| Measure | Documented | Measured |
|---|---:|---:|
| Tests | 3084 | **3084** |
| Failures | 40 | **40** |
| Errors | 6 | **6** |
| Wall time | — | 705 s |

46 distinct failure names (`qa/baseline/pm-before-failures.txt`): 30 marketing-shelf completion,
9 operations/marketing worksheet + registry import, 2 `customer_journey` profile, 5 other-shelf
(rail, paper store, template refusal, chat), 1 network (Brave→Firecrawl). **0 new, 0 on this shelf.**
Inventory confirmed exactly as the work order stated: 18 tools · 6 worksheets · 10 records ·
0 theories · 23 glossary terms · tiles 0 · 75 profiles.

### Delivered

| Artefact | Content |
|---|---|
| `qa/manual/project-management.md` | The **16-item delivery/governance inventory** with a per-item verdict, a **ranked owner-gated proposal** (nothing built), 62 E-rows reconciled 1:1 with `detail('project-management')`, the V-01…V-20 reading of one paper, the defect ledger, residual risk |
| `tests/test_subject_project_management_acceptance.py` | 62 tests, 62 passed — independent recomputation for all 17 core methods |
| `qa/probe_pm_shelf.py`, `qa/probe_pm_paper.py` | The reproducible evidence behind every claim |
| `qa/baseline/pm-*` | Baseline + after measurements, probe output, shelf-test slice |
| `qa/evidence/project-management/` | The paper, its no-source twin, `paper-read.json` |

### Fixed (3)

- **D-PM-01** (MAJOR, wiring): five worksheets searched with one shared cue (`evidence`) and a raw-key
  query; 32 blocks now carry their own vocabulary. Trap tests `test_E_pm_049`, `test_E_pm_050`.
- **D-PM-02** (MAJOR, declaration): RACI's profile said `subject: 'management'` while its catalogue id
  is `PM-10` and two pages carry it. Trap test `test_E_pm_058`.
- **D-PM-05** (BLOCKER, gate/V-06): the charter, WBS, risk register, stakeholder plan and lessons
  learned shipped `'lead': 'lead'` and the produced paper **printed the literal token `lead`** as its
  framework-overview paragraph. Fixed in **both layers**: the eight leads (those five plus BMC, Lean
  Canvas and VPC) are now **authored** — 56–86 words each, grounded on that profile's own block
  labels, with no case fact, number or source — and `_lead_of()` still fails closed on any future
  stub. Trap test `test_E_pm_063`; before/after in
  `qa/evidence/project-management/lead-before-after.txt`. Blast radius measured: 139 entrepreneurship
  tests, 63 shelf rows and the shared contracts green.

### Ledgered / declared (4 + 4 gaps)

D-PM-03 (marketing's two kinds declared canvas **and** matrix — not this shelf's to fix),
D-PM-04 (`case_decision` is a T2 template, measured and pinned), G-pm-01 (probe-profile background
fill; V-01 fails at all ten blocks of the charter paper, disclosed), G-pm-02 (17 profiles unreachable
from any page), G-pm-03 (risk register has no paper figure), G-pm-04 (a rate entered as `6` is taken
as given and disclosed, not rescaled).

### Gates at close

| Gate | Result |
|---|---|
| Shelf acceptance suite | **62 passed** |
| Shelf acceptance + `test_docs_sync` + `test_frozen_contract` | **72 passed** |
| Shelf + 19 shared contract modules | 234 passed, 3 failed — all three are baseline failures on other shelves (`qa/baseline/pm-shelf-tests.txt`) |
| Full suite before | **3084 tests, 40 failures, 6 errors** (`qa/baseline/pm-before-suite-err.txt`) |
| Full suite after | **3151 tests, 14 failures, 6 errors** (`qa/baseline/pm-after2-suite-err.txt`) — 33 repaired by the marketing lane's `2209822`, **0 from this shelf**, 1 NEW elsewhere (below) |
| `qa/check_page_syntax.py` | **page syntax: OK** (`qa/baseline/pm-page-syntax.txt`) |
| Live click-through on 8001 | **18 of 18 delivered**, 4 markers, **4 screenshots** |

**The one NEW failure in the after-run is not this shelf's.**
`test_product_spreadsheets.SpreadsheetTest.test_spreadsheetml_is_a_three_sheet_workbook_of_strings`
still expects `sha256:spec-abc` in the Case sheet, while the owner's rule removed the
specification hash from every paper and workbook (P3). It is a foreign-lane stale expectation —
the same class the marketing lane repaired 27 of in `2209822` — and it is **not** in this
shelf's tests. Classification: `NEW-UNEXPLAINED→FOREIGN-STALE` (recorded, not fixed here).

### Next subject and its top three risks

**Next: `supply-chain`** — the one shelf with no acceptance manual and no acceptance suite, and it
inherits the whole operations toolset.

1. **Reachability.** It shares worksheets with operations; `test_E_pm_057` measures 17 profiles that no
   subject page reaches. Measure supply chain's own reachability before writing a row.
2. **Inventory arithmetic is the dangerous part.** `inventory_policy` (EOQ, reorder point) mixes money,
   shares and periods; recompute by hand first, then by a second formula — never the method's own
   output against itself.
3. **Another lane is live in this worktree.** HEAD moved mid-session here (`84490ec` → `0970a06`).
   Print `git diff --cached --name-only` before every commit, never `git add -A`, and re-read a file
   that appears to have "vanished".


---

## Session 6 — `marketing` (started 2026-11-03, in progress)

**Owner instruction:** "8. GO." — the next subject, after the management shelf closed and after the
owner made the core unfrozen (B-197).

**Baseline, measured.** `subjects.detail("marketing")`: **24 tools, 6 worksheets, 29 records, 0
theories, 48 glossary terms**; 21 framework profiles carry `subject: "marketing"`. The framework
completion slice's last **27 failures were all on this shelf** (`qa/baseline/mgt-completion-after.txt`).

**Found and fixed (D-MKT-01).** Every one of the 27 was a **stale expectation, not a product defect**:
for all 21 marketing profiles the profile, `templates.CANVAS_BLOCKS`/`MATRIX_META`, the paper and the
prompt agreed with each other, and only the tests named the older, shorter frameworks — the profile
declares 10 blocks for the marketing plan (4 STP + the 7 Ps) against a test that expected 4, "Kano
Model" against "Kano", "Technology Acceptance Model" against "TAM". Sixteen test files were aligned
with the declaration (expected block lists, the framework name, and the prompt's framework name) and
nothing else was touched. `tests/test_subject_marketing_acceptance.py` is the net under it: five tests
that assert the profile/form/paper/prompt agreement for **all 21** profiles, so a profile that grows or
is renamed cannot leave a test behind again.

**Result.** The 16 marketing completion files: **192 passed, 0 failed** (was 27 failed). The new net: 5
passed. Documented test count re-measured and set to **3151** in `docs/HOME.md`, `docs/HANDOFF.md`,
`docs/CONTRIBUTORS.md` (the real suite count, as `test_docs_sync.py` requires); `test_docs_sync.py`
7 passed.

**Not done, and not claimed.** The marketing shelf's acceptance manual (`qa/manual/marketing.md`), its
full E-row table, its click-through and its defect ledger are **session 6's work and are not written
yet**. 29 records and 48 glossary terms make it the largest shelf after economics. The next session
starts from the net and the 21 aligned profiles, not from a blank shelf.


## Session 5 — `management` (2026-11-03) · commit `29d0509`

**Subject chosen by the work order** ("SUBJECT = management, do not start marketing, people, operations
or any other shelf"). Branch `corpus/merge-v1`, opening commit `211b672`.

### Baseline (Phase 0) — measured, not assumed

| Measure | Documented | Measured at `211b672` |
|---|---|---|
| Tests (`python -m unittest discover -s tests`) | 2910 (economics' close) | **2932** |
| Failures | 67 | **66** |
| Errors | 13 | **13** |
| Distinct failure names | — | **79** |
| Wall time | — | 650 s |

Raw: `qa/baseline/mgt-suite-err.txt`. Framework-completion slice: 539 tests, **60 failed**
(`qa/baseline/mgt-completion-slice.txt`). Shelf inventory confirmed exactly as the work order stated:
1 compute tool, 31 worksheets, 0 records, 0 theories, 75 profiles overall, 12 non-draftable profiles.
The one number that did **not** match: **17** profiles are reachable from no subject page, not the 22
recorded in `VALIDATION_HARNESS.md` §7.2 (D-MGT-09 / G-mgt-04).

### Delivered

| Artefact | Content |
|---|---|
| `qa/manual/management.md` | The shelf's acceptance manual: inventory reconciled 1:1 with the catalogue, **46 E-rows** (44 PASS · 2 BLOCKED · 0 DISPUTED), traceability matrix, declared gaps, residual risk |
| `tests/test_subject_management_acceptance.py` | **46 tests, 46 passed** — one per row, named `test_E_mgt_nnn__<behaviour>` |
| `qa/probe_mgt_shelf.py` | Read-only inventory + one mocked run per profile (the evidence behind the manual) |
| `qa/probe_mgt_paper.py` | Builds the papers and reads `word/document.xml` back (P6) |
| `qa/evidence/management/` | Five artefacts + `summary.txt` |

### Fixed (eleven ledger rows, `D-MGT-01…11`)

The two that were not this shelf's tests at all: **D-MGT-01** — `framework_profiles.py` ran
`exec(open("C:/tmp/profiles_out.py"))` at import time, so eight profiles lived outside the repository
and the module could not import on any other machine (BLOCKER); and **D-MGT-11** — `deliverables.py`
still printed the specification footer the owner deleted from the computation paper (P3, BLOCKER).

The shelf's own: the Value Chain declared twice with two vocabularies (D-MGT-05), its nine cells
`fill: "auto"` so the brief's own sentence filled Procurement and eight cells went empty (D-MGT-03),
firm infrastructure unable to accept any real overhead evidence (D-MGT-04), a chain figure with nine
empty boxes (D-MGT-02), Change and Organization refusing every industry brief (D-MGT-06), a prompt that
never named the unit of analysis (D-MGT-07), and â€œa activitieâ€ in every `-ies` paper (D-MGT-10).

### Gates at close

| Gate | Result | Evidence |
|---|---|---|
| Full suite, after | **3084 tests, 40 failures, 6 errors** — **0 new names**, 33 repaired (79 → 46) | `qa/baseline/mgt-after-suite-err.txt`, `mgt-after-failures.txt` |
| Framework-completion slice | **27 failed, 512 passed** (from 60 failed); every remaining failure is on the marketing shelf | `qa/baseline/mgt-completion-after.txt` |
| Shelf acceptance suite | **46 passed** | `python -m pytest tests/test_subject_management_acceptance.py -q` |
| `tests/test_docs_sync.py` + `tests/test_frozen_contract.py` | **10 passed** (documented count 3084 unchanged) | — |
| `python scripts/econ_shelf.py --check` | **frozen fixture: in sync** | after the B-197 unfreeze too |
| Artefact read (P6) | value-chain, change-organization, no-source twins, worksheet export — no footer, no diagram promise, byline on the title page, background disclosed | `qa/evidence/management/summary.txt` |

**Push: BLOCKED by this machine, not by the work.** `git push origin corpus/merge-v1` fails with
`remote: Invalid username or token. Password authentication is not supported for Git operations.` and
`GIT_TERMINAL_PROMPT=0` (as the work order requires) makes it fail rather than prompt. Both commits are
in the local tree (`29d0509`, `0217a42`) and the branch is 6 ahead of `origin/corpus/merge-v1`; a lane
with credentials must push them. Recorded rather than worked around.

### Left open, deliberately

- **D-MGT-08 — CLOSED after the owner's ruling.** The owner answered the one question of this session
  with "UNFREEZE IT", and then made the unfreeze standing (B-197). Four methods now declare their
  precision (`npv`, `pearson`, `spearman`, `descriptive_stats` — 142 of 142), `case_decision`'s derived
  keys are formatted from the precision the core itself records, and no paper prints a raw Decimal or a
  Python repr. E-mgt-039 flipped BLOCKED → PASS. Re-measured after the change: **3084 tests, 40
  failures, 6 errors, 0 new failure names** (`qa/baseline/mgt2-suite-err.txt`,
  `mgt2-failures.txt` — identical to the pre-unfreeze set), `test_frozen_contract.py` green and
  `scripts/econ_shelf.py --check` "frozen fixture: in sync".
- **D-MGT-09 / E-mgt-046 (BLOCKED).** The shelf page counts 28 catalogue records beside 31 worksheets
  (STR-01, STR-07, STR-18 uncounted). The number is on the page, so which side moves is the owner's.
- **G-mgt-02.** Change and Organization has a profile, tests and no worksheet row: no page reaches it.
  Adding one changes the catalogue surface — owner decision.

### Debugging the shelf by driving it (owner: "ensure correctness")

`qa/probe_mgt_debug.py` runs **all 30 shelf templates twice** (with evidence and with none),
strips `word/document.xml`, reads the paper, and checks V-01…V-20, the figure, the citations,
the references and determinism. It found three defects no unit test had asserted, and one where
the harness itself was wrong:

| Id | Found by | What it was |
|---|---|---|
| D-MGT-12 (BLOCKER) | a source whose title echoes the block's own query was still refused | the three canvas profiles declared `cues: ['evidence']` and `queries: ['<key> evidence']` — a list of cues became the token `"['evidence']"`, so **no** evidence could ever be accepted. 24 blocks now carry a real vocabulary and phrase; `retrieval.cue_words_of` reads a list |
| D-MGT-13 (MAJOR) | 5 of 168 researched blocks refused their own query | missing cue words (boundaries, axes, communicate) and two queries searching "intervention", a word the gate blocks on purpose |
| D-MGT-14 (MINOR) | the produced paper read "it is **a element**" | the last hard-coded article; now `_article()` |
| — | my own harness false positive | `"a activitie" in text` also matches "rot**a activitie**s"; the needles are word-bounded now |

**Measured:** `python qa/probe_mgt_debug.py` → **0 problems** over 30 templates × 2 runs.
**Framework-completion slice: 539 passed, 0 failed** (60 failing at session start).
**Full suite: 3165 tests, 4 failures, 4 errors** — from 2932 / 66 / 13 at `211b672`. All eight
remaining are other lanes' and named in the commit: four `test_operations_frameworks` (an example
template was renamed), one chat hung-dimension, one paper store, one web rail, one network-dependent
sources test. **Nothing on this shelf fails.**

Counts re-measured rather than copied: **18** profiles reachable from no page (SERVQUAL's row left
the marketing shelf while that lane repairs it), **11** non-draftable, documented suite count **3165**.

**Session 6 — `marketing`.** It is the only shelf with failures left in the framework-completion slice
(27 of 27: attribution, cro, customer_journey, digital_mix, email_crm, funnel, kano, marketing_plan,
measurement_plan, paid_media_plan, rfm, servqual, social_media, stp, stp_evidence, tam). Top three
risks, measured from this session:

1. **The shared prompt fix already repaired twelve of its tests; the rest are real.** The marketing
   profiles fail on `test_four_cells_each_carry_a_sourced_item_or_a_named_gap` and
   `test_outline_headings_are_present_and_title_cased` — the same two classes this shelf had, so read
   each profile's `fill`, its cue sets and its `outline` before touching a test.
2. **Marketing has the largest profile surface (35 catalogue records, 6 worksheets).** Two of its
   profiles (kano, measurement_plan, paid_media_plan, servqual, customer_journey) are in the
   non-draftable twelve, so a paper must be produced for them through the engine while the button stays
   off — `test_E_mgt_045` is the pattern.
3. **`framework_profiles.py` is now 640 KB of data in one module and three lanes are editing it.**
   Check `git status` before and after every commit, stage explicit paths, and re-read a file before
   editing it: this session had one in-flight `completion.py` edit swept into another lane's commit.
   The module should become a package — that is an owner decision, not a lane's.


Another lane committed three times while this session ran (`839f06e`, `bfd9872`, `d765853`) and
`839f06e` swept an in-flight edit of `completion.py` into its own commit. Nothing was lost; every
commit here used an explicit pathspec and `git diff --cached --name-only` was read before each one.
The documented test count also moved under this session (2910 → 3084) as that lane added 106 tests;
the count is 3084 after this session's 46, so `test_docs_sync` still passes unchanged.


## Session 6 — `entrepreneurship` (2026-11-03, owner work order)

**Parameter.** `SUBJECT = entrepreneurship`, shelf 6 of 11. Opening commit `b2987fc`, build 1.68.
Closed at build 1.69.

**Inventory, confirmed against the live catalogue** (`GET /api/cases/subjects/entrepreneurship`
on 8001, then `subjects.detail`): **46 tools, 6 worksheets, 6 records, 0 theories** at the opening —
as the work order expected, so no inventory defect; `docs/CURRICULUM_MAP.md` disagreed (it said 5
worksheets) — D-ENT-11. **The owner then ruled that the marketing plan (`MKT-02`, STP and the
marketing mix) belongs to the marketing shelf alone (B-196), so the shelf closes with 5 worksheets**;
the inventory rows in the manual, the tests and the docs were corrected rather than left behind.

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
| `python -m unittest discover -s tests` | **3084 tests, 40 failures, 6 errors, 684 s** at close (the same 40/6 as the `ci.py` run at 3038): **0 names absent from the opening baseline**, **33 gone** (79 → 46). The 33 are another lane's repairs to `framework_profiles.py` and its tests; this session's own fix removed no name from the set because the eight period-less presets were never exercised by a delivery test | `qa/baseline/ent_final_err.txt` (close), `ent_ci_err.txt` (CI), `ent_baseline_failures.txt` → `ent_final_failures.txt`, `ent_repaired.txt` |
| `python scripts/ci.py` | **2 of 3 steps passed**: unit tests FAIL on the 46 historical problems; `shelf audit and frozen contract` **PASS**; `page syntax` (node `--check`) **PASS** | `qa/baseline/ent_ci_out.txt` |
| `python scripts/econ_shelf.py --check` | **frozen fixture: in sync** | `qa/baseline/ent_econ_shelf.txt` |
| `python qa/_count.py` | **SUITE_COUNT 3084** at close: 2932 at the opening, +106 from this session's acceptance suite, +46 added moments later by the concurrent framework-profile lane. The three count docs are shared with that lane; they were re-measured and set to 3084, and `test_docs_sync` is green at that number | `qa/baseline/ent_count.txt` |
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

### Owner follow-up, same day — the two marketing worksheets (B-198)

The owner reviewed the failing set and ruled: **fix the Customer journey map, hide the SERVQUAL
grid**. Both were declared as a canvas *and* a grid, so the page gave a grid worksheet a canvas
editor that could never submit.

| | Result |
|---|---|
| **MKT-04 Customer journey** | FIXED — declared only as a grid; `describe()` now publishes the axis labels (`touchpoint × stage`) and the form prints them. The two failing marketing worksheet tests flip **with no test edit**. |
| **MKT-07 SERVQUAL** | **HIDDEN** — the tile is off the marketing page (MKT-02, 04, 06, 15, 18 remain). Its template, registry record, grid declaration and completion profile are untouched, so the framework still completes through the conductor. `D-MKT-07` carries the reason and the reversal. |
| Traps added | a grid may not open a canvas form; a hidden worksheet must stay registered and stay hidden *while the defect exists* (repairing it fails the test until the tile is unhidden). |
| Ledger | `D-MKT-04` FIXED, `D-MKT-07` HIDDEN, `D-MKT-08` half of project-management's `D-PM-03` closed (`E-pm-057` now pins one declaration, not two). |
| Also corrected | `E-mkt-001` (a grid's form is its two axes, not the profile's blocks) and `E-mkt-004` (five worksheets, and MKT-07 named as absent). |

Expected effect on the failure set: 19 → 17. The other 17 were left alone as instructed — the
registry JSON, the rail literal, the operations example packs and the three stale "no profile"
premises are untouched and still failing.

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

