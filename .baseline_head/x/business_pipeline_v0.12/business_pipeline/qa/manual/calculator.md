# Business Calculator — surface acceptance manual

**Session: calculator · subject `calculator` (rail panel `#panel-calculator`) · branch `corpus/merge-v1` · written 2026-11-03**
**Opening commit:** `05efb8f` (marketing's B-211 and research's B-213/B-214 had landed after the work
order was written; the tree was re-measured, never copied — the work order's *33 shared keys* is the
one number that does not reproduce, and it is now **disproved** across all 36 revisions of
`subjects.py` (§5.1), not merely marked unresolved.)
**Acceptance suite:** `tests/test_calculator_acceptance.py` — 25 tests, one per PASS row, named
`test_E_calc_nnn__<behaviour>`.
**Probe:** `qa/probe_calculator.py` — read-only; writes papers to `qa/evidence/calculator/`.

This manual is the specification for the calculator surface. Every row cites the artefact it was read
from, and every PASS row names the test that proves it. Nothing here is a new requirement: the rules
come from `docs/CONDUCTOR_MANUAL.md` §4 and §8, `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20) and §7,
the owner's presentation rules P1–P6, the frozen core's contract (142 methods / 144 presets, B-197),
and the twelve wiring invariants W-01…W-12 set in this session's work order.

## Reproduce the measurements in this file

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python qa\probe_calculator.py                  # inventory + resolution (key vs method): 8 / 206 / 148
python qa\probe_calculator.py --tools          # 148 papers written to qa\evidence\calculator\, gates read
python qa\probe_calculator.py --determinism    # 148/148 identical bytes
python qa\probe_calculator.py --shared         # the 31 multi-group keys agree from every group
python qa\probe_calculator.py --units          # unit/precision sweep: 0 disagreements
python qa\probe_calculator.py --subject operations --prove   # the harness on a shelf we trust: 14/14
python qa\probe_calculator.py --subject research --prove     # the harness on a shelf we trust: 21/21
python -m unittest tests.test_calculator_acceptance          # 25 tests
```

---

## 1. Scope

The surface in scope is the **Business Calculator**: the rail panel `#panel-calculator`, its route
`GET /api/cases/calculator` and `POST /api/cases/calculator/plan`, its guard
(`tests/test_product_subjects.py::CalculatorGuardTest`), and the **148 launchable tools** it offers.

It is not a subject and it owns no worksheets, records, theories or glossary. It is a *view* over the
union of every subject's compute tools, plus a presentation taxonomy of 8 business-function groups.
That is why it had no acceptance manual: each shelf was validated, and the union of them was only
ever *counted*.

**What this session re-measured rather than trusted:** the work order states the calculator is
"complete but unproved — nothing runs the tools, only counts them". That is exactly right, and it is
what changed. Before this session no test launched a calculator tool and read the paper it produces.

**Boundary honestly stated.** No shelf's own papers were opened for their own sake. `operations` and
`research` were re-run *as harness controls* (§4, E-calc-023), because a harness is a suspect until it
has been pointed at a shelf whose own suite is already green. Their suites were green before and are
green after.

## 2. Inventory, reconciled

| Unit | Count | Source of truth | Measured 2026-11-03 |
|---|---:|---|---|
| Compute tools (`compute_tools()`) | 148 | `bp.product.subjects` | **148** |
| Calculator groups | 8 | `CALCULATOR_GROUPS` | **8**, in business-function order |
| Group entries (with repeats) | 206 | `CALCULATOR_GROUPS` | **206** |
| Distinct keys in groups | 148 | the same list | **148** — union == `compute_tools()` |
| Keys listed in more than one group | **33** (order) / **31** (measured) | `group_count()` | **31** — the order's 33 is disproved, §5.1 |
| Tools missing from the calculator | 0 | set difference | **0** |
| Calculator keys not on a subject page | 0 | set difference | **0** |
| Tools with a shipped preset | 144 | `server.PRESETS` | **144**, each running the method it claims |
| Tools with typed inputs (no preset) | 4 | `compute_tools()` | `kruskal_wallis`, `mann_whitney`, `ols_robust`, `spearman` |
| Keys that are **not** `LIBRARY` ids | 131 | `tool["key"] not in LIBRARY` | **131** of 148 — trap 1 |
| Methods resolvable in `LIBRARY` | 147 | `tool["method"] in LIBRARY` | **147** |
| Documented composite exemption | 1 | `case_decision` | **1** |
| Preset/method mismatches | 0 | `PRESETS[p]["method"] == tool["method"]` | **0** |
| Methods in `LIBRARY` | 142 | `bp.methods.LIBRARY` | **142** |
| Presets in `server.PRESETS` | 144 | `bp.server.PRESETS` | **144** |
| Frozen fixture pins | 142 / 144 | `tests/fixtures/frozen_contract.json` | **142 / 144 — in sync** |

### 2.1 The eight groups, in order

| # | Group id | Label | Entries | Tier mix |
|---:|---|---|---:|---|
| 1 | `finance` | Finance | 31 | T1 25, T2 5, T4 1 (`case_decision`) |
| 2 | `accounting` | Accounting | 12 | T1 10, T2 2 |
| 3 | `statistics` | Statistics | 21 | T1 21 |
| 4 | `economics` | Economics | 59 | T1 55, T2 4 |
| 5 | `entrepreneurship` | Entrepreneurship | 26 | T1 22, T2 3, T4 1 (`case_decision`) |
| 6 | `operations` | Operations | 25 | T1 25 |
| 7 | `marketing` | Marketing | 22 | T1 22 |
| 8 | `people` | People | 10 | T1 9, T2 1 |
| | **total** | | **206** | |

### 2.2 The 31 keys listed in more than one group (W-03)

`forecast` 6 · `multibreakeven` 6 · `chi_square` 5 · `power` 5 · `breakeven` 5 · `unitecon` 5 ·
`descriptive` 4 · `alpha` 3 · `npv` 3 · `ols` 3 · `pearson` 3 · `demandcurve` 3 · and 19 more at 2
(`anova`, `case_decision`, `cba`, `cohort`, `currency`, `dcf`, `dpayback`, `funnel`, `irr`, `loan`,
`missing`, `pricing`, `purchaseintent`, `ratios`, `sroi`, `trendanalysis`, `weighted`, `welch`,
`workingcapital`). Measured by `group_count()`; proved by E-calc-006.

### 2.3 The four typed tools (W-06, trap 2)

| Tool | Method | Preset | Why typed |
|---|---|---|---|
| `spearman` | `spearman` | **none** | the student supplies two ranked lists |
| `ols_robust` | `ols_robust` | **none** | outcome plus named predictors |
| `mann_whitney` | `mann_whitney` | **none** | two named groups of observations |
| `kruskal_wallis` | `kruskal_wallis` | **none** | three or more named groups |

A probe that indexes `PRESETS[tool["preset"]]` crashes on all four. The panel sends `inputs: {}` for
them, so this suite proves both directions: with typed figures they deliver (E-calc-010), and with
`{}` they **block naming the missing input** rather than crashing or delivering an empty success
(E-calc-011).

### 2.4 The one composite (W-04)

`case_decision` is the single tool whose `method` is not a `LIBRARY` id. It is a template delivered
through the core, documented in `tests/test_catalogue_truth.py::SubjectToolsResolve`. This suite
asserts it is the **only** exemption (E-calc-007) and never asserts it against `LIBRARY`.

### 2.5 Key vs method — the 131 trap, made explicit

`welch`→`welch_t`, `descriptive`→`descriptive_stats`, `alpha`→`reliability_alpha`,
`forecast`→`trend_forecast`, `roi` and `trainingroi`→`return_on_investment`. A probe that resolves
`tool["key"]` against `LIBRARY` reports **131 false defects**. This probe resolves both, prints both
numbers (17 / 147), and reports **0** resolution problems.


## 3. UI surfaces

| Surface | What it shows | Source of truth | Measured |
|---|---|---|---|
| Group chips (`#calcgroups`) | one chip per business function, 8 in order | `calculator_groups()["groups"]` | 8 chips, 8/8 non-empty |
| Tool list (`#calcout`) | label, `what`, and `Method: <method>, preset <preset>` or `, typed inputs` | `_tool()` | 148 rows, 144 with a preset, 4 typed |
| Search (`#calcq`) | a **global** filter over `label + method + what`; a search does not respect the chip | `renderCalculator()` in `web/index.html` | every tool matches its own label (E-calc-016) |
| Ask (`#calcask`) | a sentence becomes a plan (`/api/cases/calculator/plan`); nothing is computed | `calc_router.plan` | `run` / `need_inputs` / `choose` / `unsupported` / `out_of_scope` |
| Panel note (`#calcnote`) | "computes nothing", "Typed free-form arithmetic is not supported" | `calculator_groups()["note"]` | verbatim, and in the markup (E-calc-020) |
| Workbench cards | `#chartbtn`, `#expbtn`, `#expzip` exist, are wired, and are **not** in the calculator panel | `web/index.html` | present + wired + absent from the panel (E-calc-022) |
| Downloads | the paper (docx) and the workbook (xlsx); never Markdown, never a spec hash | `session_paper` | E-calc-021 |

## 4. Acceptance rows — E-calc-001 … E-calc-025

Every PASS row names the test that proves it. Every test names a row.

| Id | Behaviour | Source | Test | Status |
|---|---|---|---|---|
| E-calc-001 | Every tool on every subject page appears in at least one calculator group (W-01) | work order W-01 | `test_E_calc_001…` | PASS |
| E-calc-002 | Every calculator entry names a real `TOOL_INFO` key; the distinct set equals `compute_tools()` (W-02) | work order W-02 | `test_E_calc_002…` | PASS |
| E-calc-003 | No group is empty and every group has a label (W-02) | work order W-02 | `test_E_calc_003…` | PASS |
| E-calc-004 | The 8 groups are in business-function order | `CALCULATOR_GROUPS` | `test_E_calc_004…` | PASS |
| E-calc-005 | The inventory is 8 groups / 206 entries / 148 distinct | this manual §2 | `test_E_calc_005…` | PASS |
| E-calc-006 | A key listed in several groups behaves identically from each (W-03); 31 today, `chi_square` 5, `forecast` 6 | work order W-03 | `test_E_calc_006…` | PASS |
| E-calc-007 | Every tool resolves to a `LIBRARY` method or the one documented composite (W-04); 131 keys are not method ids | work order W-04 | `test_E_calc_007…` | PASS |
| E-calc-008 | Every preset named by a tool exists and its `method` equals the tool's (W-05) | work order W-05 | `test_E_calc_008…` | PASS |
| E-calc-009 | Every one of the 148 tools delivers a paper through the shipped path (P6) | `VALIDATION_HARNESS.md` §5 | `test_E_calc_009…` | PASS |
| E-calc-010 | The four typed tools run end to end with no preset and no empty success (W-06) | work order W-06 | `test_E_calc_010…` | PASS |
| E-calc-011 | A typed tool sent `inputs: {}` blocks naming the missing input, and writes no result (W-06, W-09) | work order W-06 | `test_E_calc_011…` | PASS |
| E-calc-012 | Every delivered tool prints all its declared checks, none skipped, renamed or duplicated (W-07) | work order W-07 | `test_E_calc_012…` | PASS |
| E-calc-013 | Every figure prints at its declared precision, and none at 6+ decimals (W-08) | W-08, P4, B-214 | `test_E_calc_013…` | PASS |
| E-calc-014 | No paper prints a Python repr or scientific notation (W-08) | W-08, P4, B-197 | `test_E_calc_014…` | PASS |
| E-calc-015 | A refusal names its reason and a blocked run never renders as delivered (W-09) | work order W-09 | `test_E_calc_015…` | PASS |
| E-calc-016 | The search reaches every tool by its own name from every group it is filed under (W-10) | work order W-10 | `test_E_calc_016…` | PASS |
| E-calc-017 | The ask surface routes a named calculation to a real tool and runs nothing yet (W-10) | `calc_router.plan` | `test_E_calc_017…` | PASS |
| E-calc-018 | An unknown sentence never invents a tool; it returns no tool and a reason (W-10) | work order W-10 | `test_E_calc_018…` | PASS |
| E-calc-019 | An unknown calculator route is 404 naming the route (W-10) | work order W-10, D-CALC-03 | `test_E_calc_019…` | PASS |
| E-calc-020 | The panel note stays true: "computes nothing", "free-form arithmetic is not supported" (W-11) | work order W-11 | `test_E_calc_020…` | PASS |
| E-calc-021 | A downloaded paper carries no Markdown, no spec hash, no "Diagram to draw" (W-12) | P1–P6, work order W-12 | `test_E_calc_021…` | PASS |
| E-calc-022 | `#chartbtn`/`#expbtn`/`#expzip` stay wired and stay out of the calculator panel (W-12) | work order W-12 | `test_E_calc_022…` | PASS |
| E-calc-023 | The harness reports nothing on `operations` (14/14) and `research` (21/21) | work order §3 | `test_E_calc_023…` | PASS |
| E-calc-024 | The gates have teeth: a 30-digit Decimal and a missing check are both caught | this manual §4 | `test_E_calc_024…` | PASS |
| E-calc-025 | `LIBRARY` 142 / `PRESETS` 144 / fixture 142–144, and every method is pinned | `BACKEND_CONTRACT.md` §2 | `test_E_calc_025…` | PASS |


## 5. DISPUTED

| # | Dispute | Evidence | Ruling |
|---|---|---|---|
| 1 | The work order states **33** keys are listed in more than one group. | **Disproved, not just unmatched** — see §5.1: `group_count()` returns **31**, 33 appears in **none** of the 36 historical revisions of `subjects.py`, and no alternative reading of "shared" produces 33 either. | **RESOLVED: the order's 33 is a miscount; the tree is right.** Nothing to change in the product. 31 is pinned exactly, together with the **full sharing distribution** — 117 keys in 1 group, 19 in 2, 5 in 3, 1 in 4, 4 in 5, 2 in 6 — so a taxonomy edit that moved a key from 2 groups to 3 could not hide behind an unchanged total (E-calc-006). |
| 2 | W-10 says an unknown term returns **404 naming the unknown term**. | `POST /api/cases/calculator/plan` answers **200** with `outcome: "unsupported"`, `tool: null`, `reason: "no_method: no frozen method matches this sentence"`. An unknown *route* answered `422 case id must be 12 lowercase hex characters` (D-CALC-03). | **Split ruling.** The route case was a real defect and is fixed (404 naming the route, E-calc-019). The *plan* case is not a lookup — it is a plan, and a plan that says "no frozen method matches, here are the nearest three, nothing was guessed" is the honest answer; forcing 404 would lose the alternatives. The prompt's own §9 makes "what the calculator says when a tool cannot run" an **owner decision**, so the plan surface was left alone. |
| 3 | W-08 says "figures at `method.typing(key)` precision" **and** "no `\d\.\d{6,}`". For a method that declares 6 dp these conflict. | `currency_convert.rate` and `real_option.delta` returned `("ratio", 6)`, so the paper obediently printed `0.920000` and `0.617058`. | **`DECISIONS.md` B-214 already settled it**: the *declaration* is the defect, not the renderer ("Six decimals read as an unrounded `Decimal`, which is what P4 exists to prevent"). Both declarations were lowered to 4 dp under B-217 (D-CALC-01/02). |
| 4 | Two "problems" the probe reported on its first run were the probe's own. | `descriptive` flagged for `1e-9` inside the declared **limitation** "Float reference comparison tolerance is 1e-9 relative"; `currency`/`realoption` flagged for figures at their own declared precision. | **Both were false positives** and the probe was corrected, not the product: the shape gates now read the report and the figure lines, not the declared assumption/limitation/check prose (E-calc-023, E-calc-024). |

### 5.1 The "33 shared keys" number, disproved

The work order states 33 keys are listed in more than one group, and correctly instanced
`chi_square` in 5 and `forecast` in 6 — *those two are right*. The total is not. Three independent
tests were run rather than one.

**(a) Every historical revision of `CALCULATOR_GROUPS`.** All 36 revisions of
`src/bp/product/subjects.py` in the repository were parsed and the sharing count computed for each:

| count | revisions | when |
|---:|---:|---|
| 13 | 1 | earliest |
| 17 | 3 | |
| 20 | 2 | |
| 24 | 1 | |
| 27 | 13 | up to 2026-11-02 |
| 30 | 1 | `d120ed3` |
| **31** | **15** | `c220576` (2026-11-02) → `dda7d22` (2026-11-03) |
| 33 | **0** | — |

The count went **27 → 30 → 31** and has been 31 for the last **15** consecutive revisions. It has
never been 33.

**(b) Alternative readings of "shared".** Each was measured to see whether the order meant something
else:

| Reading | Result |
|---|---:|
| keys listed in more than one **group** | **31** |
| distinct **methods** appearing in more than one group | 31 |
| keys whose **method** is shared (catches `roi`/`trainingroi`, `dcf`/`dcfmid`, …) | 32 |
| keys listed on more than one **subject page** | 45 |
| surplus entries (`entries − distinct` = 206 − 148) | 58 |
| keys duplicated **within** a single group | 0 |

None is 33.

**(c) What is pinned.** E-calc-006 pins the total **and** the distribution
`117 / 19 / 5 / 1 / 4 / 2` (keys in 1 / 2 / 3 / 4 / 5 / 6 groups). A count-only assertion is weaker
than it looks: moving one key from two groups to three keeps the total at 31 and changes only the
distribution. The distribution is what makes the pin resistant, and it is why a future "33" would be
caught instead of argued about.

**Conclusion.** 33 is recorded as a miscount in the work order. The product needed no change, and the
only surviving hypothesis is that the order was measured against an uncommitted local edit; the
committed tree — which the order itself names as the source of truth — says 31 in all 15 recent
revisions.


## 6. Defects

| Id | Severity | What | Repro | Root cause | Fix | Trap test |
|---|---|---|---|---|---|---|
| D-CALC-01 | MAJOR | Every currency-conversion paper printed `Rate: 0.920000` — a ratio at 6 dp, which P4 and the B-214 house rule both call an unrounded `Decimal`. | `python qa/probe_calculator.py --tools` → `currency: 6+ decimal figure: '0.920000'` | `_cc_typing` returned `("ratio", 6)` for `rate`. The declaration was wrong, not the renderer. | `_cc_typing` → `("ratio", 4)`; the paper now reads `Rate: 0.9200`. | E-calc-013 |
| D-CALC-02 | MAJOR | Every real-option paper printed `Delta: 0.617058`; the four ratio outputs (`delta`, `up_factor`, `down_factor`, `risk_neutral_probability`) were all at 6 dp. | same sweep → `realoption: 6+ decimal figure: '0.617058'` | `_real_option_typing` returned `("ratio", 6)` for those four metrics. | → `("ratio", 4)`; the paper reads `Delta: 0.6171`. | E-calc-013 |
| D-CALC-03 | MINOR | `POST /api/cases/calculator/nonsense` answered `422 case id must be 12 lowercase hex characters` — a wrong reason that named neither the route nor the mistake. | `python -c "from bp.product import api; print(api.handle('POST','/api/cases/calculator/nonsense',{}))"` | An unknown calculator sub-route fell through to the case-id parser. | 404 `unknown route /api/cases/calculator/nonsense`. | E-calc-019 |
| D-CALC-04 | PROBE (not product) | The probe's first run flagged `descriptive` (scientific notation) and would have flagged two more — all false positives. | `python qa/probe_calculator.py --tools` on the uncorrected probe | The number-shape gates scanned declared assumption/limitation/honesty prose as if it were a figure. | Gates read the report and the figure lines only; declared prose is excluded by construction. | E-calc-023, E-calc-024 |

**None of the four is a BLOCKER.** No wrong number was delivered, no evidence invented, no gate
bypassed, nothing crashed, and no tool rendered a silent success. D-CALC-01/02 were wrong *presentation
of a right number*; D-CALC-03 was a wrong *error message*; D-CALC-04 was the harness's own error.


## 7. Traceability matrix

| Requirement | Source | Row | Test | Re-measured |
|---|---|---|---|---|
| W-01 tools reachable from the calculator | work order | E-calc-001 | `…001…` | 0 missing |
| W-02 entries name real tools, union == `compute_tools()` | work order | E-calc-002/003 | `…002…`, `…003…` | 148 == 148 |
| W-03 shared keys behave identically | work order | E-calc-006 | `…006…` | 31 keys, 0 disagreements |
| W-04 method resolution, composite exemption | work order | E-calc-007 | `…007…` | 147 + 1 |
| W-05 preset ↔ method agreement | work order | E-calc-008 | `…008…` | 144/144 |
| W-06 typed tools, empty `inputs` | work order | E-calc-010/011 | `…010…`, `…011…` | 4/4 |
| W-07 every check printed once | work order | E-calc-012 | `…012…` | 148/148 |
| W-08 precision, no repr, no exponent | work order, P4 | E-calc-013/014 | `…013…`, `…014…` | 148/148 |
| W-09 a refusal names its reason | work order | E-calc-011/015 | `…015…` | named in every case |
| W-10 search/ask never invent a tool | work order | E-calc-016…019 | `…016…`–`…019…` | 0 invented |
| W-11 the panel note stays true | work order | E-calc-020 | `…020…` | verbatim |
| W-12 P1–P6 on downloads | work order, P1–P6 | E-calc-021/022 | `…021…`, `…022…` | clean |
| V-05 computations from the frozen core | `VALIDATION_HARNESS.md` §5 | E-calc-009 | `…009…` | 148/148 |
| Determinism / re-performance | `BACKEND_CONTRACT.md` §1 | E-calc-006 + `--determinism` | `…006…` | 148/148 identical bytes |
| Frozen contract unchanged | `BACKEND_CONTRACT.md` §3 | E-calc-025 | `…025…` | 142/144 in sync |

## 8. Evidence

| Artefact | Path | What proves it |
|---|---|---|
| 148 delivered papers | `qa/evidence/calculator/paper_<key>.txt` | written by `python qa/probe_calculator.py --tools`; each read back by the gates. Text, not `.docx`: the paper bytes embed the core's code hash, so a binary would churn on every `src/bp/**` edit without a number changing (the research shelf's `*.txt` precedent) |
| Inventory + resolution | table in §2 | `python qa/probe_calculator.py` |
| Determinism | §4 E-calc-006 | `python qa/probe_calculator.py --determinism` |
| Shared keys | §2.2 | `python qa/probe_calculator.py --shared` |
| Unit sweep | §9 | `python qa/probe_calculator.py --units` |
| Harness controls | §4 E-calc-023 | `--subject operations --prove`, `--subject research --prove` |
| Defect before/after | D-CALC-01/02 | `paper_currency.docx` / `paper_realoption.docx` now read `Rate: 0.9200` / `Delta: 0.6171` |

## 9. Gaps

| Gap | Why it is open | What would close it |
|---|---|---|
| The calculator has no *records*, *worksheets* or *glossary* of its own | it is a view, not a shelf; all of those live on the subject pages | nothing to close — this is the design |
| `--units` compares `typing` against `output_units`/`output_precision`, not against a hand calculation | the unit sweep is a *contract* sweep; the arithmetic is proved by each shelf's own figures suite (`qa/probe_research_shelf.py --verify` does the hand arithmetic for statistics) | a per-tool hand-arithmetic oracle for 148 tools would duplicate eight shelves' suites |
| The ask router's vocabulary is CLUES/INPUT_WORDS-driven, not learned | by design: a fuzzy matcher that returns the nearest tool would violate W-10 | nothing — the current refusal is the requirement |
| No live-server click-through for `#panel-calculator` | this session proves the artefact and the routes, not the browser | a `qa/clickthrough_calculator.py` on the `clickthrough_*` pattern |

## 10. Risk

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| A new shelf tool is added and nobody adds it to `CALCULATOR_GROUPS` | medium — happened on every shelf session | the tool is dark on the calculator | W-01/E-calc-001 fails the moment the union drifts |
| A group list is edited by hand and a key is typo'd | medium | a tool silently disappears | W-02/E-calc-002 |
| A preset is retargeted at another method | low | the wrong method runs under a familiar label | W-05/E-calc-008 |
| A method's declared precision drifts upward | low — D-CALC-01/02 were this | a paper prints an unrounded Decimal | E-calc-013 + the B-214 house rule |
| A check stops being printed | low | a gate bypass presented as a pass | W-07/E-calc-012 |
| The ask router starts guessing | low | invented evidence | W-10/E-calc-018 |

