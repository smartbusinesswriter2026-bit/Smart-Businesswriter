# Research & statistics — subject acceptance manual

**Session 11 of 11 · subject `research` · branch `corpus/merge-v1` · written 2026-11-03**
**Opening commit:** `6c7073c` (marketing's B-211 had landed after the work order was written; the
tree was re-measured, not copied — the work order's `b393743` and its 3409 tests were stale).
**Acceptance suite:** `tests/test_subject_research_acceptance.py` — 53 tests, one per PASS row,
named `test_E_res_nnn__<behaviour>`.

This manual is the specification for the shelf. Every row cites the artefact it was read from, and
every PASS row names the test that proves it. Nothing here is a new requirement: the rules come from
`docs/CONDUCTOR_MANUAL.md` §4 and §8, `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20) and §7, the owner's
presentation rules P1–P6 set on 2026-11-03, the frozen core's own contract (142 methods / 144 presets,
B-197), and one owner decision taken in this session (D3, B-212).

**Reproduce the measurements in this file**

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python qa\probe_research_shelf.py                 # inventory, resolution (key vs method), records, contract
python qa\probe_research_shelf.py --tools         # 21 papers written to qa/evidence/research/ and read back
python qa\probe_research_shelf.py --figures       # every tool's figures, at their declared precision
python qa\probe_research_shelf.py --verify        # 61 figures re-derived independently: 0 disagreements
python qa\probe_research_shelf.py --subject operations --prove   # the harness, on a shelf we trust
python -m pytest tests\test_subject_research_acceptance.py -q
```

---

## 1. Scope

The shelf in scope is `research`, the **Research & statistics** shelf: `subjects.detail("research")`.
It is cross-cutting (`cross_cutting: true`): every other subject's papers cite its numbers, so a
change to a method, a precision, a claim ceiling or a refusal here moves nine other shelves. Nothing
on the people, marketing, supply-chain, operations, project-management, entrepreneurship, finance,
accounting or economics shelves was started or judged in this session.

The dependencies this session could not avoid: `subjects.py`, `registry.py` and `session_paper.py` are
shared modules (named in the commit message), and `QNT-STA-09` links methods that ship on the
**economics** shelf, which was read and re-tested, never opened for its own sake (§6).

## 2. Inventory, reconciled against the catalogue

| Unit | Count | Source of truth | Measured 2026-11-03 |
|---|---:|---|---|
| Compute tools | 21 | `detail("research")["tools"]` | 21, each with a frozen `method` (21/21 in `LIBRARY`) |
| Tools with a shipped preset | 17 | `server.PRESETS` | 17, each running the method it claims |
| Tools with typed inputs (no preset) | 4 | `detail("research")["tools"]` | `spearman`, `ols_robust`, `mann_whitney`, `kruskal_wallis` |
| Worksheets | 0 | `detail("research")["worksheets"]` | 0 — this shelf is calculators and records only |
| Tiles | 4 | `detail("research")["tiles"]` | **4** (was 0 before this session, D-RES-06) |
| Records | 10 | `detail("research")["records"]` | QNT-STA-01…10 |
| Records computed | 8 | the same rows | 8 (was 3 before this session, D-RES-01) |
| Records read-only | 2 | the same rows | QNT-STA-08, QNT-STA-10 — both genuinely unbuilt |
| Theories | 0 | `detail("research")["theories"]` | 0 |
| Glossary terms | 0 | `detail("research")["glossary"]` | 0 |
| Catalogue records the shelf counts | 10 | `subjects.catalogue()` | 10 = 8 computed + 2 read-only, reconciled |
| `does_not` items | 3 | `detail("research")["does_not"]` | 3, one of them the causal promise |
| `start_steps` | 4 | `detail("research")["start_steps"]` | 4 — and they are the four tile names |
| Methods in `LIBRARY` | 142 | `bp.methods.LIBRARY` | 142 |
| Presets in `server.PRESETS` | 144 | `bp.server.PRESETS` | 144 |
| Frozen fixture pins | 142 / 144 | `tests/fixtures/frozen_contract.json` | 142 / 144 — in sync |

### 2.1 The four tiles (owner decision, B-213)

21 tools, 0 declared a `group`, 0 tiles, and 9 of 21 declared no `level`, so `web/index.html` fell
back to a flat list. The owner chose the shelf's **own four `start_steps`** as the tiles, verbatim, so
no taxonomy was invented for a cross-cutting shelf:

| Tile | Tools | Records | What it answers |
|---|---:|---|---|
| Describe the data | 2 | QNT-STA-01 | what one variable looks like before anything is tested |
| Compare groups | 9 | QNT-STA-03 | whether two or more groups differ |
| Relate variables | 6 | QNT-STA-04, -07, -08, -10 | whether variables move together, and the trend that follows |
| Check the design | 4 | QNT-STA-02, -05, -06, -09 | whether the study could have found what it looked for |

The tile keys **are** the tool groups (`RESEARCH_GROUPS`): `_tiles` places a calculator in the tile
whose key equals the tool's group, so any other vocabulary would drop all 21 calculators out of the
page. The nine null `level`s were left null on purpose: with every tool grouped the page groups by
tile, and inventing levels to feed a fallback the page no longer needs would have been a taxonomy the
owner did not ask for (E-res-010).

### 2.2 Records, one row each (10)

Read from `subjects.detail("research")["records"]`, the committed slice in `src/bp/product/subjects.py`,
cross-checked against `registry.load()["records"]`. **Eight are `computed` after this session; before
it, three were** — the other five said "Method not built" while the page offered a calculator for the
area (D-RES-01, §4).

| Id | Form | Status | Method(s) the record claims | What ships / what does not |
|---|---|---|---|---|
| QNT-STA-01 | computed | Computed | `descriptive_stats` | descriptive statistics for one variable; no cross-tabulation, no visualisation |
| QNT-STA-02 | **computed** (was read_only) | Computed | `power_analysis` | power, sample size, MDE for one- and two-sample means; no sampling design, no CI planning |
| QNT-STA-03 | computed | Computed | `welch_t`, `mann_whitney`, `chi_square`, `anova`, `kruskal_wallis`, `two_way_anova`, `posthoc_pairwise`, `paired_t`, `one_sample_t` | as listed; ANCOVA not implemented |
| QNT-STA-04 | computed | Computed | `pearson`, `spearman`, `ols`, `ols_robust`, `logistic_regression` | as listed; categorical predictors, interactions, non-linear terms not implemented |
| QNT-STA-05 | **computed** (was read_only) | Computed | `reliability_alpha` | Cronbach's alpha; factor analysis and test-retest not implemented |
| QNT-STA-06 | **computed** (was read_only) | Computed | `multiple_comparison`, `missing_data_bounds` | Holm and Bonferroni; worst-case missing-data bounds; no imputation, no sensitivity analysis |
| QNT-STA-07 | **computed** (was read_only) | Computed | `trend_forecast` | linear trend with an out-of-sample backtest, interval and drift; no seasonal/ARIMA, no break tests |
| QNT-STA-08 | read_only | Method not built | — | clustering/classification is **genuinely unbuilt** (parked by B-075) |
| QNT-STA-09 | **computed** (was read_only) | Computed | `difference_in_differences`, `regression_discontinuity`, `instrumental_variables`, `panel_regression` | the four designs ship on the **Economics** shelf, with their identification assumptions; RCTs, matching and weighting not implemented |
| QNT-STA-10 | read_only | Method not built | — | mediation/moderation/SEM is **genuinely unbuilt** |

The record's own shelf note is appended by `_record_shelf_note` where the calculator lives on another
page: QNT-STA-09 now reads "…are not implemented. The method is computed, but its calculator is on the
Economics shelf, not on this page; open it there and the same frozen method runs." (E-res-015).

### 2.3 UI surfaces

| Surface | What it shows | Source of truth | Measured |
|---|---|---|---|
| `#subjectpage` tool tiles | 4 tiles, each with its calculators, records and a "what this needs" line | `detail("research")["tiles"]` | 4 tiles, 21/21 tools placed, 10/10 records placed |
| Tool card | label, method, preset (or "typed inputs"), difficulty word where declared | `_tool()` | 12 of 21 carry a level; 9 carry none by design |
| Records table | id, name, form, status, note, linked methods | `_catalogue_row()` | 10 rows, 8 computed, 2 read-only |
| Workbench cards | `#chartbtn`, `#expbtn`, `#expzip` exist and the chart/export cards stay hidden | `web/index.html` | ids present (E-res-026); P2 |
| Downloads | docx (the paper), xlsx, spreadsheetml, csv — never Markdown, never a hash | `session_paper`, `spreadsheets` | E-res-022/023/024 |

### 2.4 Compute tools, one row each (21)

Tier and ceiling are read from `bp.methods.LIBRARY[method]`. "Declared precision" is what
`method.typing(key)` returns and is checked on the paper by E-res-019.

| Tool | Method | Preset | Group | Level | Tier | Ceiling |
|---|---|---|---|---|---|---|
| `descriptive` | `descriptive_stats` | `descriptive` | Describe the data | intro | T1 | descriptive |
| `pearson` | `pearson` | `pearson` | Relate variables | intermediate | T1 | associational |
| `spearman` | `spearman` | (typed) | Relate variables | — | T1 | associational |
| `ols` | `ols` | `ols` | Relate variables | advanced | T1 | associational |
| `ols_robust` | `ols_robust` | (typed) | Relate variables | advanced | T1 | associational |
| `welch` | `welch_t` | `welch` | Compare groups | advanced | T1 | associational |
| `mann_whitney` | `mann_whitney` | (typed) | Compare groups | — | T1 | associational |
| `anova` | `anova` | `anova` | Compare groups | advanced | T1 | associational |
| `kruskal_wallis` | `kruskal_wallis` | (typed) | Compare groups | — | T1 | associational |
| `chi_square` | `chi_square` | `chi_square` | Compare groups | advanced | T1 | associational |
| `factorial` | `two_way_anova` | `factorial` | Compare groups | — | T1 | associational |
| `posthoc` | `posthoc_pairwise` | `posthoc` | Compare groups | — | T1 | associational |
| `multicomp` | `multiple_comparison` | `multicomp` | Check the design | — | T1 | descriptive |
| `power` | `power_analysis` | `power` | Check the design | advanced | T1 | descriptive |
| `missing` | `missing_data_bounds` | `missing` | Check the design | intermediate | T1 | descriptive |
| `paired` | `paired_t` | `paired` | Compare groups | — | T1 | associational |
| `onesample` | `one_sample_t` | `onesample` | Compare groups | — | T1 | associational |
| `logit` | `logistic_regression` | `logit` | Relate variables | — | T1 | associational |
| `alpha` | `reliability_alpha` | `alpha` | Check the design | intro | T1 | descriptive |
| `weighted` | `weighted_summary` | `weighted` | Describe the data | intro | T1 | descriptive |
| `forecast` | `trend_forecast` | `forecast` | Relate variables | intro | T1 | predictive |

**The two vocabularies (D-RES-02).** A tool carries a `key` (the page's own name) and a `method` (a
frozen `LIBRARY` id). **Only 8 of the 21 keys are library ids**; 13 are not (`welch`→`welch_t`,
`descriptive`→`descriptive_stats`, `alpha`→`reliability_alpha`, `forecast`→`trend_forecast`, …). A
probe that resolves `tool["key"]` against `LIBRARY` reports 13 false defects; this shelf's probe
resolves both and prints the difference, and E-res-009 pins the counts.

**The four typed tools.** `spearman`, `ols_robust`, `mann_whitney` and `kruskal_wallis` ship with
`preset: null`, which the page renders as "typed inputs": the student enters the figures and the same
frozen method runs. This is the same declared mode finance's `ols_robust` uses (G-fin-05), not a
broken button — the page's launch path reads `inputs: {}` and the schema drives the form. Every one of
the four is still proved on a hand case (E-res-029, 030, 032, 035).

---

## 3. Expected behaviour — E-res-001 … E-res-053

Every row is PASS, GAP or BLOCKED. A GAP names its ledger id and the manual says what a student sees
instead; a BLOCKED row would say what is missing and why it cannot be tested. There are no BLOCKED
rows.

### 3.1 The shelf against the catalogue (E-res-001 … 010)

| Row | Behaviour | Source of truth | Test | Status |
|---|---|---|---|---|
| E-res-001 | The shelf declares 21 tools with distinct keys, each with a label and a "what it does" | `detail("research")["tools"]` | `test_E_res_001…` | PASS |
| E-res-002 | Every tool resolves to a frozen method; every preset exists and runs the method it claims; the four typed tools declare no preset | `LIBRARY`, `server.PRESETS` | `test_E_res_002…` | PASS |
| E-res-003 | The shelf has no worksheets, no theories and no glossary | `detail("research")` | `test_E_res_003…` | PASS |
| E-res-004 | Ten records, in catalogue order, 8 computed and 2 read-only | `detail("research")["records"]` | `test_E_res_004…` | PASS |
| E-res-005 | The shelf is cross-cutting, carries four start steps, and its `does_not` includes "It does not prove causality from observational data" | `detail("research")` | `test_E_res_005…` | PASS |
| E-res-006 | Four tiles whose keys are exactly the tool groups; every tool sits in exactly one tile | `detail("research")["tiles"]` | `test_E_res_006…` | PASS |
| E-res-007 | Every record sits in exactly one tile; every tile has calculators, a description and a "what this needs" | the same | `test_E_res_007…` | PASS |
| E-res-008 | The catalogue row agrees with the detail page (21/0/10/0/10, cross-cutting) | `subjects.catalogue()` | `test_E_res_008…` | PASS |
| E-res-009 | 8 of 21 tool keys are library ids and 21 of 21 methods are (D-RES-02) | `LIBRARY` | `test_E_res_009…` | PASS |
| E-res-010 | The page groups by tile; the nine null levels stay null (owner decision B-213) | `detail("research")["tools"]` | `test_E_res_010…` | PASS |

### 3.2 The records: honesty (E-res-011 … 015)

| Row | Behaviour | Source of truth | Test | Status |
|---|---|---|---|---|
| E-res-011 | No record says "not implemented" while it links a method; only QNT-STA-08 and -10 read "Method not built" | `detail("research")["records"]` | `test_E_res_011…` | PASS |
| E-res-012 | The five repaired records are `computed`, start "partial:", and link exactly the methods they claim | `subjects.py`, `registry.py` | `test_E_res_012…` | PASS |
| E-res-013 | QNT-STA-08 and -10 stay read-only, link nothing, and the gap is real (no cluster/SEM method exists) | `LIBRARY` | `test_E_res_013…` | PASS |
| E-res-014 | The committed slice and the registry agree on every record's `implementation_status` | `registry.load()` | `test_E_res_014…` | PASS |
| E-res-015 | QNT-STA-09 names the Economics shelf and keeps saying what it cannot do | `_record_shelf_note` | `test_E_res_015…` | PASS |

### 3.3 The papers, read on the artefact (E-res-016 … 026)

| Row | Behaviour | Source of truth | Test | Status |
|---|---|---|---|---|
| E-res-016 | Every tool delivers, sections print in reading order, and every paper prints the honesty heading | `session_paper.HEADINGS` | `test_E_res_016…` | PASS (21/21; **D-RES-04 closed by B-215**) |
| E-res-017 | Every declared check is run and printed; none is skipped or renamed | `method.test_names` | `test_E_res_017…` | PASS |
| E-res-018 | Every paper prints the method's assumptions and limitations | `method.assumptions/limitations` | `test_E_res_018…` | PASS |
| E-res-019 | Every computed figure prints at the method's declared precision | `method.typing` | `test_E_res_019…` | PASS |
| E-res-020 | No paper prints a Python repr | the paper text | `test_E_res_020…` | PASS (D-RES-03 fixed) |
| E-res-021 | Two identical runs produce identical bytes | `session_paper.docx_bytes` | `test_E_res_021…` | PASS |
| E-res-022 | No download carries a specification footer or a hash (docx, csv, spreadsheetml) | `session_paper`, `spreadsheets` | `test_E_res_022…` | PASS |
| E-res-023 | The hash stays in the record | `appendix["spec_hash"]` | `test_E_res_023…` | PASS |
| E-res-024 | There is no Markdown download anywhere | `web/index.html`, `server.py`, `api.py` | `test_E_res_024…` | PASS |
| E-res-025 | No paper or page promises a diagram | sources, page, papers | `test_E_res_025…` | PASS |
| E-res-026 | `#chartbtn`, `#expbtn` and `#expzip` still exist for the unguarded inline script | `web/index.html` | `test_E_res_026…` | PASS |

### 3.4 The figures, proved by hand on the paper (E-res-027 … 046)

Each row gives the case, the arithmetic done on paper (or the published value), and the test that
pins the printed figure. `qa/probe_research_shelf.py --verify` repeats every one of these against an
independent implementation (`betai`, `erfc`, the normal CDF, ranks, sums of squares) and reports
**61 figures compared, 0 disagreements**.

| Row | Case | Hand arithmetic / published value | Test |
|---|---|---|---|
| E-res-027 | descriptive, `2,4,4,4,5,5,7,9` | n 8; mean 40/8 = 5; median (4+5)/2 = 4.5; variance 32/7 = 4.5714; sd 2.1381 | `test_E_res_027…` |
| E-res-028 | pearson, x 1…5, y 2,3,5,4,6 | r = 9/√(10·10) = 0.9; t = 0.9·√3/√0.19 = 3.5762; df 3 → p 0.0374 | `test_E_res_028…` |
| E-res-029 | spearman, 6 pairs, Σd² = 6 | ρ = 1 − 6·6/(6·35) = 0.828571 | `test_E_res_029…` |
| E-res-030 | welch, a 1-4, b 5-7 | diff 2.5 − 6 = −3.5; se √(1.6667/4 + 1/3) = 0.8660; t −4.041; **df = 0.75²/((0.4167²/3)+(0.3333²/2)) = 4.9591, not n₁+n₂−2 = 5**; p 0.0101 | `test_E_res_030…` |
| E-res-031 | anova, 1-3 / 4-6 / 7-9 | SSB 54, df 2; SSW 6, df 6; F = 27; η² = 54/60 = 0.9 | `test_E_res_031…` |
| E-res-032 | kruskal, same three groups | H = 12/(9·10)·279 − 3·10 = 7.2, df 2 | `test_E_res_032…` |
| E-res-033 | chi-square 2×2 `[[20,30],[30,20]]` | expected 25 each; χ² = 4·25/25 = 4.0; p = erfc(√2) = 0.0455; V = √(4/100) = 0.2 | `test_E_res_033…` |
| E-res-034 | ols, y 2,4,5,4,5,7,8,9 on x 1…8 | slope 38/42 = 0.9048; intercept 5.5 − slope·4.5 = 1.4286; R² 38/42; F = (0.9048/0.0952)·6 = 57; residual se √(3.619/6) = 0.777 | `test_E_res_034…` |
| E-res-035 | ols_robust, same data | coefficients identical; HC3 se 0.103 ≠ classical 0.120 | `test_E_res_035…` |
| E-res-036 | one-sample t, 1…11, μ₀ = 4 | mean 6, sd √11, se 1, t = 2.0, df 10; **published P(\|T\|>2.0) = 0.0734** | `test_E_res_036…` |
| E-res-037 | paired, before/after | diffs 2,1,1,1,1: mean 1.2, sd 0.4472, se 0.2, t 6.0, df 4 → p 0.0039 | `test_E_res_037…` |
| E-res-038 | reliability, 4 items × 8 respondents | α = k/(k−1)·(1 − Σs²ᵢ/s²_total); kit recomputes it: 0.8874 | `test_E_res_038…` |
| E-res-039 | weighted, 1,2,3,4 with 1,1,1,3 | (1+2+3+12)/6 = 3.00; Σw = 6 | `test_E_res_039…` |
| E-res-040 | multicomp, p 0.01/0.04/0.03, Holm | sorted 0.01,0.03,0.04 ×3,×2,×1 → 0.03,0.06,0.04 → monotone 0.03,0.06,0.06; one rejection | `test_E_res_040…` |
| E-res-041 | missing, 10,12,·,14,99(code),16 | 4 valid, mean 13; fill both missings at min 10 → 12.00, at max 16 → 14.00 | `test_E_res_041…` |
| E-res-042 | power, effect 5, sd 10/12, n 30/40 | se √(100/30+144/40) = 2.6325; ncp 1.899; power = Φ(ncp−1.96)+Φ(−ncp−1.96) = 0.4757 | `test_E_res_042…` |
| E-res-043 | posthoc, three groups | three pairs = C(3,2); every adjusted p ≥ its raw p | `test_E_res_043…` |
| E-res-044 | two-way ANOVA | SS_A + SS_B + SS_AB + SS_E = SS_Total; MS_E = SS_E/4 | `test_E_res_044…` |
| E-res-045 | logit | odds ratio = exp(coefficient) for every predictor | `test_E_res_045…` |
| E-res-046 | forecast, 1,2,2,4,4,5,7 | slope 26/28 = 0.9286; intercept 3.5714 − 0.9286·4 = −0.1429 | `test_E_res_046…` |

### 3.5 Refusals and the claim ceiling (E-res-047 … 050)

| Row | Behaviour | Measured reason | Test | Status |
|---|---|---|---|---|
| E-res-047 | A perfect fit is refused, not reported with an undefined interval | "data problem: perfect fit: inference is undefined; check for a duplicated or derived predictor" | `test_E_res_047…` | PASS |
| E-res-048 | A binary float is refused, not silently coerced | "pass numbers as strings, integers or exact decimals, not binary floats" (B-190 typing rule) | `test_E_res_048…` | PASS |
| E-res-049 | A group below the schema's minimum is refused with a reason | the schema's `min_items` refusal | `test_E_res_049…` | PASS |
| E-res-050 | No paper asserts causation from an observational design | every causal verb is either absent or denied in the same sentence; "effect of" is allowed only in ANOVA's technical sense | `test_E_res_050…` | PASS |

### 3.6 Shelf-wide traps (E-res-051 … 053)

| Row | Trap | Why it exists | Test | Status |
|---|---|---|---|---|
| E-res-051 | Every method in `LIBRARY` declares a `typing` hook | a figure with no declared precision can print as a raw Decimal on any shelf (P4) | `test_E_res_051…` | PASS |
| E-res-052 | The probe re-derives ≥ 55 figures with 0 disagreements, **and** reports no problem when pointed at `operations` | warning 2: never trust a harness you have not pointed at a shelf you trust | `test_E_res_052…` | PASS |
| E-res-053 | `LIBRARY` 142 / `PRESETS` 144 and the frozen fixture pins the same | D4(b): the document drifted, the fixture did not | `test_E_res_053…` | PASS |

---

## 4. DISPUTED rows

Six rows were judgement calls. Each says what was decided, what the alternative was, and who owns the
other answer. None is silently resolved.

| Dispute | What was decided | The alternative, and who owns it |
|---|---|---|
| **D-RES-01 — five records said "Method not built"** | All five are now `computed` and start "partial:", naming the part that ships and the part that does not. `implementation_status` is byte-identical in `subjects.py` and in `registry.py`'s link rules, so the page and the framework API cannot disagree. | Leave them read-only and only soften `status_note`. Rejected: `_record_form` derives `computed` from `linked_methods`, so a read-only record linking a method contradicts the code's own rule and the catalogue-truth test. |
| **QNT-STA-09 links four methods that live on economics** | The record is `computed`, links `difference_in_differences`, `regression_discontinuity`, `instrumental_variables`, `panel_regression`, and says in its own note that the calculator is on the Economics shelf. | Say nothing on this shelf. Rejected: it denies four shipped methods, which is the exact class the catalogue-truth test exists for. The economics shelf was read and re-tested (§6). |
| **D-RES-04 — `power` and `missing` printed no honesty heading** | **CLOSED (B-215, owner unfreeze).** Re-measured first: both methods already declared `caveats` and those sentences already printed, in the Result — what was absent was the *heading*, because `orchestrator._honesty` fills a fixed four-field structure and fills it only for inferential methods. On the owner's instruction the block gains a fifth field, `this_method`, carrying the method's own caveats, and it is added **only when all four standard fields are empty**, so no paper discloses the same thing twice. The paper now reads "Honesty: what was not done / this method: Power is a planning property of the design, not evidence about the result…". | Do nothing (the caveats were already on the page). Rejected once the owner chose the unfreeze: a paper whose only disclosure sits in the middle of the Result reads as though nothing was withheld, under a heading that does not exist. |
| **D-RES-05 — `logistic_regression` declared 6 decimal places** | **FIXED (B-214).** The declaration is now 4 dp for coefficients, standard errors and both log-likelihoods, so the paper reads `-22.8067` instead of `-22.806666`. Nothing else moves: the fixture pins `tier/metric/unit/ceiling/test_names/inputs` and **not** precision, `test_honesty`/`test_missing`/`test_frozen_contract` are green, and no other shelf ships logistic regression. | Leave it at 6 and state P4 as "declared precision" only. Rejected because the two promises then stay in conflict on every paper that method writes. |
| **D3 — the nine null levels** | **Measured harmless.** Level is rendered only inside the study-notes block (`index.html:4932`), and only for tools that have `formula` (i.e., study notes). All 12 study-note tools carry a level; the 9 nulls carry neither. The `hasLevels` guard (`index.html:4823`) groups by level only if *every* tool has one, and the tile branch (`index.html:4824-4825`) returns before the level fallback is ever reached on a tiled shelf. The nine null levels are therefore invisible by construction, and B-213 stands without change. | Fill `intro/intermediate/advanced` for all 21. The owner chose tiles only, so inventing levels would have been a second taxonomy. |
| **The four typed tools have no preset** | Accepted as a declared mode ("typed inputs"), the same as finance's `ols_robust` (G-fin-05); each is proved on a hand case instead. | Add four presets. That is a new preset, which §8 reserves to the owner. |

## 5. Traceability matrix

The manual and the suite reconcile **1:1**: 53 E-rows, 53 tests, no test without a row and no row
without a test. Tests are named `test_E_res_nnn__<behaviour>`, so the mapping is mechanical:

| Suite class | Rows | Tests | What it proves |
|---|---:|---:|---|
| `InventoryTest` | E-res-001 … 010 | 10 | the shelf against the catalogue, the tiles, the two vocabularies |
| `RecordHonestyTest` | E-res-011 … 015 | 5 | no record denies a method that ships; slice and registry agree |
| `PaperTest` | E-res-016 … 026 | 11 | the paper on the artefact: sections, checks, precision, repr, determinism, downloads, ids |
| `FigureTest` | E-res-027 … 046 | 20 | every figure, by hand, on the printed paper |
| `RefusalTest` | E-res-047 … 050 | 4 | refusals with reasons; the claim ceiling |
| `TrapTest` | E-res-051 … 053 | 3 | the shelf-wide traps that keep the rest honest |

```powershell
python -m pytest tests\test_subject_research_acceptance.py -q      # 53 passed
```

## 6. What this session changed, and what it re-tested

### 6.1 The changes, and the layer each was made in

| Change | Layer | Why not the frozen core |
|---|---|---|
| Five records repaired (`QNT-STA-02`, -05, -06, -07, -09): form, status and linked methods | product slice `src/bp/product/subjects.py` | the record text is the product's claim about the engine, not the engine |
| Five link rules added to `METHOD_LINK_RULES` with the same sentences | `src/bp/registry.py` | the registry derives `implementation_status`; the slice must mirror it, and `test_catalogue_truth` compares the two |
| Four tile keys and the group map for the 21 tools | `src/bp/product/subjects.py` (`RESEARCH_GROUPS`, `RESEARCH_TILES`, `RESEARCH_RECORD_GROUPS`) | the page's taxonomy is product presentation, not a method |
| A dict input renders as words, not a Python repr | `src/bp/product/session_paper.py` (`_render`) | D-RES-03 is a paper-rendering defect; the core returned the right figure and the paper printed it wrong |
| `BACKEND_CONTRACT.md` §2: 140/142 → 142/144 in four places | docs | D4(b) is doc drift; the fixture was right and was not touched |
| `logistic_regression` declares **4 dp** instead of 6 for coefficients, standard errors and both log-likelihoods (D-RES-05, **B-214**) | core `src/bp/methods.py` (`_logit_typing`) | this is the one core edit of the session, made only on the owner's instruction: a declared precision that prints `-22.806666` in a student's paper is a wrong number, not a design choice. It touches no route, preset or input schema; the fixture pins `tier/metric/unit/ceiling/test_names/inputs` and **not** precision; and `logistic_regression` is offered by this shelf alone |
| A fifth honesty field, `this_method`, carries a descriptive method's own caveats (**D-RES-04, B-215**, owner unfreeze) | core `src/bp/orchestrator.py` (after `_honesty`) | the alternative was to leave two papers with no honesty heading while their caveats sat mid-Result. The field is added **only when all four standard fields are empty**, so no paper gains a duplicate, and `tests/test_honesty.py` was rewritten to assert the stronger rule rather than a fixed key set |

Nothing else in `bp/methods.py` was edited: no method, no preset, no input schema, no claim ceiling and
no test name. The four *other* kinds of core change each move nine other shelves' papers (D6) and stay
with the owner.

**D-RES-04 was re-measured, and the first report was wrong.** It said the two methods "declare an
empty `honesty` map therefore no caveats exist". They do exist — `_power_caveats` and `_md_caveats` —
and they printed, in the Result prose. What was absent was the *heading*, because `_honesty` fills a
fixed four-field structure and fills it only for inferential methods. `tests/test_honesty.py` pinned
that key set, so the "one-line caveats" fix proposed in the first report was not available. On the
owner's unfreeze (**B-215**) the structure gained a fifth field rather than a fifth sentence: the paper
now prints the heading and the caveats beneath it, and the pin was replaced by a stronger rule.

### 6.2 The full suite, before and after

| Run | Result |
|---|---|
| Baseline at `6c7073c`, before any edit | `unittest.TestLoader().discover("tests")` → **3418** cases; the documented count in `HANDOFF`/`CONTRIBUTORS` said 3478 (stale, and the work order's 3409 was staler still) |
| After this session's 53-test acceptance file | **3478** measured immediately after the file landed. A live lane's two `test_product_bundle` tests were in the working tree but not committed while this was written, so a scan of the dirty tree reads 3480; the loader, not a document, is the source of truth |
| A full run on the closing tree | reached **2974 of 3478** with **1 failure** (`test_sources.SearchTest.test_brave_failure_falls_back_to_firecrawl` — a network-environment test that is not this shelf's) and **0 errors**, then spent more than ten minutes in `test_subject_management_acceptance`, which takes **235 s on its own**; the batch was stopped rather than left to run. Every suite was then run separately: the eight other shelves **493 passed / 136 subtests**, management **50 passed**, this shelf's suite + the core gates **157 passed** |

### 6.3 Blast radius, and what was re-tested

The shelf is cross-cutting, so the changes above were re-tested against the shelves that consume them:

| Re-tested | Why | Result |
|---|---|---|
| `tests/test_catalogue_truth.py` (6 tests) | the record repair is exactly its subject | green |
| `tests/test_product_subjects.py` (57 tests) | the slice must match the registry | green |
| **All nine other shelf acceptance suites** | the honesty block changed shape for every descriptive method on every shelf (94 of 142), and `session_paper._render` changed for every paper | **543 passed**: accounting, economics, entrepreneurship, finance, marketing, operations, project-management and supply-chain **493 passed / 136 subtests**, management **50 passed** |
| `qa/probe_research_shelf.py --subject operations --prove` | the harness itself, on a shelf whose 46-test suite is green | 0 problems reported |
| `scripts/econ_shelf.py --check` | the frozen fixture must stay in sync | `methods: 142`, `presets: 144`, `frozen fixture: in sync` |

## 7. Defects found, and where they are recorded

Severity follows the ledger's convention: **BLOCKER** = wrong number, invented evidence, gate bypass,
crash or silent success.

| Id | Severity | Defect | Status | Evidence | Trap test |
|---|---|---|---|---|---|
| D-RES-01 | MAJOR | Five records said "Method not built" while the page offered a calculator for the area; QNT-STA-09 also denied four methods that ship on economics | **FIXED** | `detail("research")["records"]`; §2.2 | `test_E_res_011`, `012`, `015` |
| D-RES-02 | TRAP | 13 of 21 `tool["key"]` values are not `LIBRARY` ids, so a probe comparing keys reports 13 false defects | DOCUMENTED, PINNED | `probe_research_shelf.resolution()` | `test_E_res_009` |
| D-RES-03 | MAJOR | Every paper whose method takes a `column_map` input printed the student's own figures as a Python repr — a P4 breach on the artefact | **FIXED** | `qa/evidence/research/research-welch.txt` (before/after) | `test_E_res_020` |
| D-RES-04 | MINOR (HONESTY) | `power` and `missing` printed no "Honesty: what was not done" heading. **Re-measured on the owner's instruction, and the first diagnosis was wrong:** both methods *do* declare `caveats` (`_power_caveats`, `_md_caveats`) and those sentences *do* print — in the Result prose. What was missing was the *section*, because the honesty block was a fixed four-field structure filled only for inferential methods | **FIXED (B-215, owner unfreeze)**: a fifth field `this_method` carries a method's own caveats, added only when all four standard fields are empty so nothing is disclosed twice. `tests/test_honesty.py` was strengthened, not loosened: the four standard fields must always be present, the fifth may appear only alone and non-empty, and `ratio_analysis` still carries no inferential notice | `qa/evidence/research/research-power.txt` and `research-missing.txt`: the heading now prints | `test_E_res_016` (every one of the 21 papers prints the heading and discloses something) | FIXED (B-215) |
| D-RES-05 | MINOR (ROUNDING) | `logistic_regression` declared 6 decimal places, so its paper printed `-22.806666` while the house rule other shelves test for is "no six-decimal figure" | **FIXED (B-214)**: the declaration is 4 dp for coefficients, standard errors and both log-likelihoods; the paper now reads `-22.8067`, and `test_honesty`/`test_missing`/`test_frozen_contract` are unaffected because the fixture pins `tier/metric/unit/ceiling/test_names/inputs`, not precision | `qa/evidence/research/research-logit.txt` (before/after) | `test_E_res_019` now also fails on any `\d\.\d{6,}` |
| D-RES-06 | MAJOR (page) | 0 groups, 0 tiles and 9 null levels: the page could group by neither topic nor level and fell back to a flat list | **FIXED** (owner decision B-213) | `detail("research")["tiles"]` | `test_E_res_006`, `007`, `010` |
| D-RES-07 | DOC-DRIFT | `docs/BACKEND_CONTRACT.md` §2 said "140 methods" and "142 presets" in four places; measured 142/144 and the fixture pins 142/144 | **FIXED** (the document, never the fixture) | `scripts/econ_shelf.py --check` | `test_E_res_053` |

## 8. Evidence

| Artefact | Path |
|---|---|
| Probe (inventory, resolution, records, contract, papers, figures, verify) | `qa/probe_research_shelf.py` |
| The 21 papers, docx and text, as produced | `qa/evidence/research/research-<tool>.docx` / `.txt` |
| Independent re-derivation | `python qa/probe_research_shelf.py --verify` → 61 figures, 0 disagreements |
| Harness proof on a trusted shelf | `python qa/probe_research_shelf.py --subject operations --prove` → 0 problems |
| Acceptance suite | `tests/test_subject_research_acceptance.py` → 53 passed |
| Blast radius | `tests/test_subject_economics_acceptance.py` + `test_subject_operations_acceptance.py` → 129 passed |
| Run logs | `qa/baseline/` (`probe-*.txt`, `suite-*.txt`, `pytest-*.txt`) |

## 9. Declared gaps

These are gaps, not defects: nothing here is claimed to work.

| Id | Gap | Why it is not built |
|---|---|---|
| G-res-01 | Clustering, classification and segmentation (QNT-STA-08) | parked by B-075 for the frontier lane; the owner has not granted it |
| G-res-02 | Factor analysis, exploratory or confirmatory (part of QNT-STA-05) | same parking rule; α ships, factor analysis does not |
| G-res-03 | Mediation, moderation and SEM (QNT-STA-10) | not built; the record says so and links nothing |
| G-res-04 | ANCOVA (part of QNT-STA-03) | not built; two-way ANOVA ships, covariate adjustment does not |
| G-res-05 | Seasonal and ARIMA forecasting, structural-break tests (part of QNT-STA-07) | parked by B-075; the linear trend with an out-of-sample check ships |
| G-res-06 | Randomised experiments, matching and weighting (part of QNT-STA-09) | not built; DiD/RDD/IV/panel ship on economics |
| G-res-07 | Multiple imputation and sensitivity analysis across missing-data assumptions (part of QNT-STA-06) | not built; worst-case bounds ship |
| G-res-08 | No glossary and no worksheets on this shelf | by design: it is a calculator shelf; the terms live on the subject shelves that use them |
| G-res-09 | Nine tools declare no difficulty level | owner decision B-213: the page groups by tile; a second taxonomy was not requested |
| G-res-10 | Four tools ship with no worked example (`preset: null`) | typed-input mode; adding presets is an owner decision (§8) |
| G-res-11 | ~~D-RES-04 above~~ | **CLOSED**: D-RES-04 is fixed by B-215 (the fifth honesty field) and D-RES-05 by B-214 (4 dp). No gap remains under this id |

## 10. Residual risk

1. **A declared precision can still print a number nobody wants.** D-RES-05 was one instance, fixed
   under B-214; nothing yet checks a declaration against the "no six-decimal figure" house rule
   automatically, so the class recurs every time a method's typing is written. The shelf's own
   `test_E_res_019` now catches it for the 21 methods here, and no other shelf has that assertion.
2. **The honesty block now has a shape that must be kept.** The fifth field is added by one condition in
   `Pipeline.run` (all four standard fields empty and the method declares caveats). A future method that
   declares caveats *and* an inferential notice will get only the notice — correct, but easy to
   mis-remember; `test_honesty` asserts the rule rather than a fixed key set, so it will catch a drift.
3. **`QNT-STA-09` depends on another shelf staying honest.** If the economics lane ever drops
   `instrumental_variables`, `regression_discontinuity`, `difference_in_differences` or
   `panel_regression`, this record silently becomes a false claim. E-res-012 fails on the day.
4. **The probe is now the only independent check of the figures.** It is 61 comparisons deep and agrees
   with the engine, but it is one implementation of the textbook: a shared misreading would agree with
   itself. The published-reference rows (E-res-036's t-table value, E-res-033's `erfc` value) are the
   anchor against that.







