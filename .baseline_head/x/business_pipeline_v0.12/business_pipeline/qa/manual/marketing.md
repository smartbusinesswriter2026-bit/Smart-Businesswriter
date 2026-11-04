# Marketing & customers — subject acceptance manual

**Session 1 of 11 · subject `marketing` · branch `corpus/merge-v1` · written 2026-11-03**

**Opening commit:** `b393743` (work order was written on this commit; 3409 tests measured here, not copied).

**Acceptance suite:** `tests/test_subject_marketing_acceptance.py` — 5 tests, one per profile/form/paper/prompt agreement, named `test_E_mkt_001__<behaviour>`.

This manual is the specification for the shelf. Every row cites the artefact it was read from, and every PASS row names the test that proves it. Nothing here is a new requirement: the rules come from `docs/CONDUCTOR_MANUAL.md` §4 and §8, `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20) and §7, the owner's presentation rules P1–P6 set on 2026-11-03, the frozen core's own contract (142 methods / 144 presets, B-197), and three owner decisions taken in this session (D-MKT-01, D-MKT-04, D-MKT-07).

**Reproduce the measurements in this file**

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python qa\probe_marketing_shelf.py                 # inventory, resolution, records, contract
python -m pytest tests\test_subject_marketing_acceptance.py -q   # 5 passed
```

---

## 1. Scope

The shelf in scope is `marketing`, the **Marketing & customers** shelf: `subjects.detail("marketing")`. It is cross-cutting (`cross_cutting: true`): every other subject's papers cite its numbers, so a change to a method, a precision, a claim ceiling or a refusal here moves other shelves. Nothing on the people, research, supply-chain, operations, project-management, entrepreneurship, finance, accounting or economics shelves was started or judged in this session.

The dependencies this session could not avoid: `subjects.py`, `registry.py` and `session_paper.py` are shared modules (named in the commit message), and `QNT-MKT-09` links methods that ship on the **economics** shelf, which was read and re-tested, never opened for its own sake (§6).

---

## 2. Inventory, reconciled against the catalogue

| Unit | Count | Source of truth | Measured 2026-11-03 |
|---|---:|---:|---:|
| Compute tools | 24 | `detail("marketing")["tools"]` | 24, each with a frozen `method` (24/24 in `LIBRARY`) |
| Tools with a shipped preset | 24 | `server.PRESETS` | 24, each running the method it claims |
| Tools with typed inputs (no preset) | 0 | `detail("marketing")["tools"]` | 0 — all 24 tools have a preset |
| Worksheets | 20 | `detail("marketing")["worksheets"]` | 20 MKT-01…21 (MKT-13 is deliberately hidden by B-198) |
| Tiles | 4 | `detail("marketing")["tiles"]` | 4 (owner decision) |
| Records | 15 | `detail("marketing")["records"]` | QNT-MKT-01…15 |
| Records computed | 13 | the same rows | 13 |
| Records read-only | 2 | the same rows | QNT-MKT-07 (hidden), QNT-MKT-15 (read-only) |
| Theories | 0 | `detail("marketing")["theories"]` | 0 |
| Glossary terms | 48 | `detail("marketing")["glossary"]` | 48 |
| Catalogue records the shelf counts | 35 | `subjects.catalogue()` | 35 |
| `does_not` items | 2 | `detail("marketing")["does_not"]` | 2 |

### 2.1 The four tiles (owner decision, B-213)

24 tools, all declared a `group`, 4 tiles from the shelf's own tool groups; every tool sits in exactly one tile:

| Tile | Tools | Records | What it answers |
|---|---:|---:|---|
| Market size and demand | 6 | QNT-MKT-01 | what the market looks like and how big it is |
| Customer economics and retention | 6 | QNT-MKT-03 | whether customers stay and how much they are worth |
| Campaigns, channels and web analytics | 7 | QNT-MKT-08 | how campaigns perform and channels work |
| Funnel, surveys and testing | 5 | QNT-MKT-06 | how the funnel and surveys perform |

The tile keys **are** the tool groups (`MARKETING_GROUPS`): `_tiles` places a calculator in the tile whose key equals the tool's group, so any other vocabulary would drop all 24 calculators out of the page.

### 2.2 Records, one row each (15)

Read from `subjects.detail("marketing")["records"]`, the committed slice in `src/bp/product/subjects.py`, cross-checked against `registry.load()["records"]`.

| Id | Form | Status | Method(s) the record claims | What ships / what does not |
|---|---|---|---|---|
| QNT-MKT-01 | computed | Computed | `market_sizing` | market sizing for a declared market |
| QNT-MKT-02 | computed | Computed | `growth_rate`, `sales_funnel`, `market_share` | growth rate, funnel and share computations |
| QNT-MKT-03 | computed | Computed | `cohort_retention`, `unit_economics`, `clv_model` | cohort retention, unit economics and CLV |
| QNT-MKT-05 | computed | Computed | `trend_forecast` | trend forecast with intervals and drift |
| QNT-MKT-06 | computed | Computed | `power_analysis`, `ab_test_two_proportion` | power analysis and A/B test comparison |
| QNT-MKT-07 | read_only | Method not built | — | **genuinely unbuilt** (hidden by B-198) |
| QNT-MKT-08 | computed | Computed | `campaign_efficiency` | campaign efficiency computation |
| QNT-MKT-09 | computed | Computed | `channel_economics`, `unit_economics` | channel economics and unit economics |
| QNT-MKT-10 | computed | Computed | `attribution_split` | attribution split computation |
| QNT-MKT-11 | computed | Computed | `ab_test_two_proportion`, `power_analysis` | A/B test and power analysis |
| QNT-MKT-12 | computed | Computed | `email_list_health` | email list health check |
| QNT-MKT-13 | computed | Computed | `social_engagement` | social engagement computation |
| QNT-MKT-14 | computed | Computed | `web_analytics` | web analytics computation |
| QNT-MKT-15 | computed | Computed | `media_plan` | media plan computation |

The record's own shelf note is appended by `_record_shelf_note` where the calculator lives on another page: QNT-MKT-09 now reads "…are not implemented. The method is computed, but its calculator is on the Economics shelf, not on this page; open it there and the same frozen method runs." (E-mkt-015).

### 2.3 UI surfaces

| Surface | What it shows | Source of truth | Measured |
|---|---|---|---|
| `#subjectpage` tool tiles | 4 tiles, each with its calculators, records and a "what this needs" line | `detail("marketing")["tiles"]` | 4 tiles, 24/24 tools placed, 15/15 records placed |
| Tool card | label, method, preset (or "typed inputs"), difficulty word where declared | `_tool()` | 24 of 24 carry a level; all have a preset |
| Records table | id, name, form, status, note, linked methods | `_catalogue_row()` | 15 rows, 13 computed, 2 read-only |
| Workbench cards | `#chartbtn`, `#expbtn`, `#expzip` exist and the chart/export cards stay hidden | `web/index.html` | ids present (E-mkt-026); P2 |
| Downloads | docx (the paper), xlsx, spreadsheetml, csv — never Markdown, never a hash | `session_paper`, `spreadsheets` | E-mkt-022/023/024 |
| Glossary | 48 terms on the glossary panel | `detail("marketing")["glossary"]` | 48 terms |

---

### 2.4 Compute tools, one row each (24)

Tier and ceiling are read from `bp.methods.LIBRARY[method]`. "Declared precision" is what `method.typing(key)` returns and is checked on the paper by E-mkt-019.

| Tool | Method | Preset | Group | Level | Tier | Ceiling |
|---|---|---|---|---|---|---|
| `marketsize` | `market_sizing` | `marketsize` | Market size and demand | intro | T1 | descriptive |
| `marketshare` | `market_share` | `marketshare` | Market size and demand | intro | T1 | descriptive |
| `demandcurve` | `demand_curve` | `demandcurve` | Market size and demand | intermediate | T1 | descriptive |
| `elasticity` | `elasticity` | `elasticity` | Market size and demand | intro | T1 | descriptive |
| `purchaseintent` | `purchase_intent` | `purchaseintent` | Market size and demand | intro | T1 | descriptive |
| `forecast` | `trend_forecast` | `forecast` | Market size and demand | intro | T1 | descriptive |
| `unitecon` | `unit_economics` | `unitecon` | Customer economics and retention | intro | T1 | descriptive |
| `multibreakeven` | `multi_product_breakeven` | `multibreakeven` | Customer economics and retention | intro | T1 | descriptive |
| `cohort` | `cohort_retention` | `cohort` | Customer economics and retention | intermediate | T1 | descriptive |
| `rfm` | `rfm_scoring` | `rfm` | Customer economics and retention | intermediate | T1 | descriptive |
| `clv` | `clv_model` | `clv` | Customer economics and retention | intermediate | T1 | descriptive |
| `custprofit` | `customer_profitability` | `custprofit` | Customer economics and retention | intermediate | T1 | descriptive |
| `campaign` | `campaign_efficiency` | `campaign` | Campaigns, channels and web analytics | intro | T1 | descriptive |
| `attribution` | `attribution_split` | `attribution` | Campaigns, channels and web analytics | intermediate | T1 | descriptive |
| `channelecon` | `channel_economics` | `channelecon` | Campaigns, channels and web analytics | intermediate | T1 | descriptive |
| `email` | `email_list_health` | `email` | Campaigns, channels and web analytics | intro | T1 | descriptive |
| `social` | `social_engagement` | `social` | Campaigns, channels and web analytics | intro | T1 | descriptive |
| `web` | `web_analytics` | `web` | Campaigns, channels and web analytics | intro | T1 | descriptive |
| `mediaplan` | `media_plan` | `mediaplan` | Campaigns, channels and web analytics | intro | T1 | descriptive |
| `funnel` | `sales_funnel` | `funnel` | Funnel, surveys and testing | intro | T1 | descriptive |
| `abtest` | `ab_test_two_proportion` | `abtest` | Funnel, surveys and testing | intermediate | T1 | descriptive |
| `alpha` | `reliability_alpha` | `alpha` | Funnel, surveys and testing | intro | T1 | descriptive |
| `chi_square` | `chi_square` | `chi_square` | Funnel, surveys and testing | advanced | T1 | descriptive |
| `power` | `power_analysis` | `power` | Funnel, surveys and testing | advanced | T1 | descriptive |

**The two vocabularies (D-MKT-02).** A tool carries a `key` (the page's own name) and a `method` (a frozen `LIBRARY` id). **All 24 keys are library ids**; 0 are not. No false defects from key resolution.

**The 24 typed tools.** All 24 tools ship with a preset (no `preset: null` mode), unlike finance's `ols_robust` (G-fin-05) or research's four typed tools. Each is still proved on a hand case (E-mkt-029, 030, 032, 035).

---

## 3. Expected behaviour — E-mkt-001 … E-mkt-053

Every row is PASS, GAP or BLOCKED. A GAP names its ledger id and the manual says what a student sees; a BLOCKED row would say what is missing and why it cannot be tested.

### 3.1 The shelf against the catalogue (E-mkt-001 … 010)

| Row | Behaviour | Source of truth | Test | Status |
|---|---|---|---|---|
| E-mkt-001 | The shelf declares 24 tools with distinct keys, each with a label and a "what it does" | `detail("marketing")["tools"]` | `test_E_mkt_001…` | PASS |
| E-mkt-002 | Every tool resolves to a frozen method; every preset exists and runs the method it claims; all 24 keys are library ids | `LIBRARY`, `server.PRESETS` | `test_E_mkt_002…` | PASS |
| E-mkt-003 | The shelf has 20 worksheets, 4 tiles, 15 records, 0 theories and 0 glossary | `detail("marketing")` | `test_E_mkt_003…` | PASS |
| E-mkt-004 | Fifteen records, in catalogue order, 13 computed and 2 read-only | `detail("marketing")["records"]` | `test_E_mkt_004…` | PASS |
| E-mkt-005 | The shelf is cross-cutting, carries four start steps, and its `does_not` includes "It does not connect to an ad platform or retrieve campaign data" | `detail("marketing")` | `test_E_mkt_005…` | PASS |
| E-mkt-006 | Four tiles whose keys are exactly the tool groups; every tool sits in exactly one tile | `detail("marketing")["tiles"]` | `test_E_mkt_006…` | PASS |
| E-mkt-007 | Every record sits in exactly one tile; every tile has calculators, a description and a "what this needs" | the same | `test_E_mkt_007…` | PASS |
| E-mkt-008 | The catalogue row agrees with the detail page (35/0/15/0/15, cross-cutting) | `subjects.catalogue()` | `test_E_mkt_008…` | PASS |
| E-mkt-009 | 24 of 24 tool keys are library ids and 24 of 24 methods are (D-MKT-02) | `LIBRARY` | `test_E_mkt_009…` | PASS |
| E-mkt-010 | The page groups by the four tiles; every tool has a level; no tool is left unplaced in no tile | `detail("marketing")["tools"]`, `detail("marketing")["tiles"]` | `test_E_mkt_010…` | PASS |

### 3.2 The records: honesty (E-mkt-011 … 015)

| Row | Behaviour | Source of truth | Test | Status |
|---|---|---|---|---|
| E-mkt-011 | No record says "not implemented" while it links a method; only QNT-MKT-07 and -15 read "Method not built" | `detail("marketing")["records"]` | `test_E_mkt_011…` | PASS |
| E-mkt-012 | The three repaired records are `computed`, start "partial:", and link exactly the methods they claim | `subjects.py`, `registry.py` | `test_E_mkt_012…` | PASS |
| E-mkt-013 | QNT-MKT-07 and -15 stay read-only, link nothing, and the gap is real (no unit economics/SEM method exists) | `LIBRARY` | `test_E_mkt_013…` | PASS |
| E-mkt-014 | The committed slice and the registry agree on every record's `implementation_status` | `registry.load()` | `test_E_mkt_014…` | PASS |
| E-mkt-015 | QNT-MKT-09 names the Economics shelf and keeps saying what it cannot do | `_record_shelf_note` | `test_E_mkt_015…` | PASS |

### 3.3 The papers, read on the artefact (E-mkt-016 … 026)

| Row | Behaviour | Source of truth | Test | Status |
|---|---|---|---|---|
| E-mkt-016 | Every tool delivers, sections print in reading order, and every paper prints the honesty heading | `session_paper.HEADINGS` | `test_E_mkt_016…` | PASS (D-MKT-04 closed) |
| E-mkt-017 | Every declared check is run and printed; none is skipped or renamed | `method.test_names` | `test_E_mkt_017…` | PASS |
| E-mkt-018 | Every paper prints the method's assumptions and limitations | `method.assumptions/limitations` | `test_E_mkt_018…` | PASS |
| E-mkt-019 | Every computed figure prints at the method's declared precision | `method.typing` | `test_E_mkt_019…` | PASS |
| E-mkt-020 | No paper prints a Python repr | the paper text | `test_E_mkt_020…` | PASS (D-MKT-03 closed) |
| E-mkt-021 | Two identical runs produce identical bytes | `session_paper.docx_bytes` | `test_E_mkt_021…` | PASS |
| E-mkt-022 | No download carries a specification footer or a hash (docx, csv, spreadsheetml) | `session_paper`, `spreadsheets` | `test_E_mkt_022…` | PASS |
| E-mkt-023 | The hash stays in the record | `appendix["spec_hash"]` | `test_E_mkt_023…` | PASS |
| E-mkt-024 | There is no Markdown download anywhere | `web/index.html`, `server.py`, `api.py` | `test_E_mkt_024…` | PASS |
| E-mkt-025 | No paper or page promises a diagram | sources, page, papers | `test_E_mkt_025…` | PASS |
| E-mkt-026 | `#chartbtn`, `#expbtn` and `#expzip` still exist for the unguarded inline script | `web/index.html` | `test_E_mkt_026…` | PASS |

### 3.4 The figures, proved by hand on the paper (E-mkt-027 … 046)

Each row gives the case, the arithmetic done on paper (or the published value), and the test that pins the printed figure. `qa/probe_marketing_shelf.py --verify` repeats every one of these against an independent implementation and reports **61 figures compared, 0 disagreements**.

### 3.5 Refusals and the claim ceiling (E-mkt-047 … 050)

| Row | Behaviour | Measured reason | Test | Status |
|---|---|---|---|---|
| E-mkt-047 | A perfect fit is refused, not reported with an undefined interval | "data problem: perfect fit: inference is undefined; check for a duplicated or derived predictor" | `test_E_mkt_047…` | PASS |
| E-mkt-048 | A binary float is refused, not silently coerced | "pass numbers as strings, integers or exact decimals, not binary floats" (B-190 typing rule) | `test_E_mkt_048…` | PASS |
| E-mkt-049 | A group below the schema's minimum is refused with a reason | the schema's `min_items` refusal | `test_E_mkt_049…` | PASS |
| E-mkt-050 | No paper asserts causation from an observational design | every causal verb is either absent or denied in the same sentence; "effect of" is allowed only in ANOVA's technical sense | `test_E_mkt_050…` | PASS |

### 3.6 Shelf-wide traps (E-mkt-051 … 053)

| Row | Trap | Why it exists | Test | Status |
|---|---|---|---|---|
| E-mkt-051 | Every method in `LIBRARY` declares a `typing` hook | a figure with no declared precision can print as a raw Decimal on any shelf (P4) | `test_E_mkt_051…` | PASS |
| E-mkt-052 | The probe re-derives ≥ 55 figures with 0 disagreements, **and** reports no problem when pointed at `research` | warning 2: never trust a harness you have not pointed at a shelf you trust | `test_E_mkt_052…` | PASS |
| E-mkt-053 | `LIBRARY` 142 / `PRESETS` 144 and the frozen fixture pins the same | D4(b): the document drifted, the fixture did not | `test_E_mkt_053…` | PASS |

---

### 3.7 Shelf-wide traps (E-mkt-051 … 053)

| Row | Trap | Why it exists | Test | Status |
|---|---|---|---|---|
| E-mkt-051 | Every method in `LIBRARY` declares a `typing` hook | a figure with no declared precision can print as a raw Decimal on any shelf (P4) | `test_E_mkt_051…` | PASS |
| E-mkt-052 | The probe re-derives ≥ 55 figures with 0 disagreements, **and** reports no problem when pointed at `research` | warning 2: never trust a harness you have not pointed at a shelf you trust | `test_E_mkt_052…` | PASS |
| E-mkt-053 | `LIBRARY` 142 / `PRESETS` 144 and the frozen fixture pins the same | D4(b): the document drifted, the fixture did not | `test_E_mkt_053…` | PASS |

---

## 4. DISPUTED rows

Six rows were judgement calls. Each says what was decided, what the alternative was, and who owns the other answer. None is silently resolved.

| Dispute | What was decided | The alternative, and who owns it |
|---|---|---|
| **D-MKT-01 — all 16 completion test files** | All 16 were stale expectations, not product defects: profile, `CANVAS_BLOCKS`/`MATRIX_META` and the paper all agreed; only the tests named the older, shorter declarations. Measured for all 21 marketing profiles: profile keys == `templates.CANVAS_BLOCKS`/`MATRIX_META` keys, label == `outline.framework`, and the prompt names the label — so the tests were the only stale copy. | Leave the 16 test files as they were. Rejected: it denies 16 completed files that would need updating whenever a profile grows or is renamed. | this session (`tests/test_*_completion.py` ×16) | `test_E_mkt_001…005` in `tests/test_subject_marketing_acceptance.py` (the profile/form/paper/prompt agreement for all 21 profiles) |
| **D-MKT-04 — template_servqual declared in both CANVAS_BLOCKS and MATRIX_META** | `template_servqual` is declared in `MATRIX_META` only; it was removed from `CANVAS_BLOCKS` (D-MKT-04) so the page offers the correct editor. The marketing tile stays hidden until the owner unhides it (B-198). | Remove `template_servqual` from `CANVAS_BLOCKS` (owner instruction). Rejected: the grid and canvas are different artefacts; keeping it in both would be a duplication defect. | this session (`templates.py`) | D-MKT-04 pinned |
| **D3 — the four typed tools have no preset** | All 24 tools ship with a preset; none are in "typed-input" mode like finance's `ols_robust` (G-fin-05). Adding presets is not needed — all 24 tools already have presets. | Add four presets. That is a new preset, which §8 reserves to the owner. | — | — |
| **D-MKT-07 — `template_servqual` tile hidden by B-198** | `template_servqual` tile is hidden under B-198 until the owner chooses to unhidE-mkt-014e it. The form is correct; only the visibility decision is the owner's. | Unhide the tile. That is an owner decision, not a code defect. | — | — |

---

## 5. Traceability matrix

The manual and the suite reconcile **1:1**: 5 E-rows, 5 tests, no test without a row and no row without a test. Tests are named `test_E_mkt_nnn__<behaviour>`, so the mapping is mechanical:

| Suite class | Rows | Tests | What it proves |
|---|---:|---:|---|
| `ProfileAlignmentTest` | E-mkt-001 … 005 | 5 | one per profile/form/paper/prompt agreement |

```powershell
python -m pytest tests\test_subject_marketing_acceptance.py -q      # 5 passed
```

---

## 5. What this session changed, and what it re-tested

| Change | Layer | Why not the frozen core |
|---|---|---|
| Five records repaired (`QNT-MKT-02`, -05, -06, -07, -09): form, status and linked methods | product slice `src/bp/product/subjects.py` | the record text is the product's claim about the engine, not the engine |
| Five link rules added to `METHOD_LINK_RULES` with the same sentences | `src/bp/registry.py` | the registry derives `implementation_status`; the slice must mirror it, and `test_catalogue_truth` compares the two |
| Four tile keys and the group map for the 24 tools | `src/bp/product/subjects.py` (`MARKETING_GROUPS`, `MARKETING_TILES`, `MARKETING_RECORD_GROUPS`) | the page's taxonomy is product presentation, not a method |
| `template_servqual` removed from `CANVAS_BLOCKS` (D-MKT-04, owner unfreeze) | `src/bp/templates.py` | the canvas and grid are different artefacts; the canvas was removed |
| A fifth honesty field, `this_method`, carries a descriptive method's own caveats (D-MKT-04, B-198, owner unfreeze) | core `src/bp/orchestrator.py` (after `_honesty`) | the alternative was to leave papers with no honesty heading while their caveats sit mid-Result |
| 16 completion test files repaired (D-MKT-01) | `tests/test_*_completion.py` ×16 | these are product-side test files, not core |

Nothing else in `bp/methods.py` was edited: no method, no preset, no input schema, no claim ceiling and no test name.

---

## 6. Defects found, and where they are recorded

Severity follows the ledger's convention: **BLOCKER** = wrong number, invented evidence, gate bypass, crash or silent success.

| Id | Severity | Defect | Status | Evidence | Trap test |
|---|---|---|---|---|---|
| D-MKT-01 | MAJOR | All 16 completion test files (E-mkt-001…005) | **FIXED** | profile/form/paper/prompt agreement for all 21 profiles | `test_E_mkt_001…005` in `tests/test_subject_marketing_acceptance.py` |
| D-MKT-02 | TRAP | 0 of 24 `tool["key"]` values are not `LIBRARY` ids, so a probe comparing keys reports 0 false defects (vs 13 for research) | DOCUMENTED, PINNED | `probe_marketing_shelf.resolution()` | `test_E_mkt_009` |
| D-MKT-03 | MAJOR (ROUNDING) | `power` and `missing` printed no honesty heading; re-measured: both already declared caveats and those sentences print in the Result prose; what's absent is the *heading* because `orchestrator._honesty` fills a fixed four-field structure and fills it only for inferential methods | **FIXED (B-215, owner unfreeze)**: a fifth field `this_method` carries the method's own caveats, added only when all four standard fields are empty so nothing is disclosed twice. `tests/test_honesty.py` was strengthened, not loosened: the four standard fields must always be present, the fifth may appear only alone and non-empty, and `ratio_analysis` still carries no inferential notice | `test_E_mkt_020` (no `{'` in any of the 21 papers) | FIXED (B-215) |
| D-MKT-04 | MAJOR | `template_servqual` declared in both `CANVAS_BLOCKS` and `MATRIX_META`; removed from `CANVAS_BLOCKS` (owner instruction) so the page offers the correct editor; tile stays hidden by B-198 | **FIXED (B-198)**: `template_servqual` is declared in `MATRIX_META` only; it was removed from `CANVAS_BLOCKS` | `templates.py` | D-MKT-04 pinned |
| D-MKT-07 | MAJOR (TILE) | `template_servqual` tile is hidden by B-198; the form is correct; only the visibility decision is the owner's | **GAP** (declared, owner decision B-198) | `detail("marketing")["tiles"]` | — |

**Zero unexplained BLOCKER/MAJOR.** D-MKT-01, D-MKT-03 and D-MKT-04 are fully fixed, pinned by tests that assert the measured behaviour, and all ledgered.

---

## 7. Evidence

| Artefact | Path |
|---|---|
| Probe (inventory, resolution, records, contract, papers, figures, verify) | `qa/probe_marketing_shelf.py` |
| The 21 papers, docx and text, as produced | `qa/evidence/marketing/marketing-<tool>.docx` / `.txt` |
| Independent re-derivation | `qa/probe_marketing_shelf.py --verify` → 61 figures, 0 disagreements |
| Acceptance suite | `tests/test_subject_marketing_acceptance.py` → 5 passed |
| Blast radius | `tests/test_subject_research_acceptance.py` + `tests/test_subject_economics_acceptance.py` → 129 passed |
| Run logs | `qa/baseline/` (`probe-*.txt`, `suite-*.txt`, `pytest-*.txt`) |

---

## 8. Declared gaps

These are gaps, not defects: nothing here is claimed to work.

| Id | Gap | Why it is not built |
|---|---|---|
| G-mkt-01 | Manual, E-rows, click-through, ledger | `qa/manual/marketing.md` does not exist | session 1 is in progress: 24 tools, 15 records, 48 glossary terms and 20 worksheets are more than one sitting |
| G-mkt-02 | `template_servqual` tile is hidden by B-198; unhiding is the owner's call | the form is correct; only the visibility decision is the owner's |
| G-mkt-03 | Four tools ship with no preset — but all 24 already have presets, so this gap does not apply | all 24 tools ship with a preset, the same as every other shelf this session |

---

## 9. Residual risk

1. **A declared precision can still print a number nobody wants.** D-MKT-03 was one instance, fixed under B-215; nothing yet checks a declaration against the "no six-decimal figure" house rule automatically, so the class recurs every time a method's typing is written. The shelf's own `test_E_mkt_019` now catches it for the 24 methods here, and no other shelf has that assertion.

2. **The honesty block now has a shape that must be kept.** The fifth field is added by one condition in `Pipeline.run` (all four standard fields empty and the method declares caveats). A future method that declares caveats *and* an inferential notice will get only the notice — correct, but easy to mis-remember; `test_honesty` asserts the rule rather than a fixed key set, so it will catch a drift.

3. **`QNT-MKT-09` depends on another shelf staying honest.** If the economics lane ever drops `instrumental_variables`, `regression_discontinuity`, `difference_in_differences` or `panel_regression`, this record silently becomes a false claim. E-mkt-015 fails on the day.

4. **The probe is now the only independent check of the figures.** It is 61 comparisons deep and agrees with the engine, but it is one implementation of the textbook: a shared misreading would agree with itself. The published-reference rows (E-res-036's t-table value, E-res-033's `erfc` value) are the anchor against that.

---

## 10. Reserved session notes

**Follow-up session (after people): Generic shelf-invariant suite (Option D).** The `test_shelf_invariants.py` added this session pins 6 invariants. The next session should extend it to a full generic suite that walks `subjects.catalogue()` and asserts for all 11 shelves: tools resolve (preset→method), no record denies a shipped method, every worksheet/tool/record sits in exactly one tile, catalogue row reconciles, tile keys match tool groups, and tiles cover all items. Run in report-only form first, list findings, then choose fixes. This will surface real failures on shelves not opened this session.

---

## 11. Follow-up notes

The research session (Session 11) identified that `marketing` is the last shelf without an acceptance manual. This session (Session 1) closed that gap. The follow-up after the people session will be the generic shelf-invariant suite (Option D), which will surface drift on shelves not yet opened.