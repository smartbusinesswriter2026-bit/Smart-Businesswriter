# People & organisation — acceptance manual (session 10)

**Subject:** `people` · **branch:** `corpus/merge-v1` · **opening commit:** `b393743`
**Suite at baseline:** 3409 tests, 1 failure, 0 errors (1139 s) — measured here, not copied.
**Acceptance suite:** `tests/test_subject_people_acceptance.py` — **84 tests, 84 passed**, 84 of 84
definitions collected (the defined-vs-collected id audit is in §11).
**Evidence:** `qa/evidence/people/` — the produced `.docx`, its stripped text, the unit audit of
all ten calculators, the parity transcript.

This is the last shelf without a manual and without an acceptance suite, and it is the only shelf
carrying people-specific arithmetic. Three of its ten calculators are **presets of core methods**
rather than re-exports:

| tool | preset key | method | also served by |
|---|---|---|---|
| `trainingroi` | `roi` | `return_on_investment` | Entrepreneurship |
| `labourtightness` | `labour` | `labour_market` | nothing else |
| `programmecost` | `cea` | `cost_effectiveness` | Entrepreneurship, Economics |

That sharing is the point: the arithmetic is the core's, the **placement** is this shelf's, and
the defects below are defects of that placement and of the core contract it relies on.

---

## 1. Baseline, measured before any change

| Measure | Documented in the work order | Measured here | Verdict |
|---|---:|---:|---|
| Tests | 3409 | **3409** | the documented count was right |
| Failures | — | **1** | network-dependent, named in `docs/OPEN_ISSUES.md` |
| Errors | — | **0** | — |
| Wall time | — | 1139 s | — |
| `scripts/econ_shelf.py --check` | in sync | **frozen fixture: in sync** | — |
| `qa/check_page_syntax.py` | OK | **page syntax: OK** | — |
| `test_docs_sync._suite_count()` | — | **3409** | now 3493 with this session's 84 tests |

Raw output: `qa/baseline/ppl-before-suite-err.txt`.

### 1.1 Every failure classified

| # | Test | Class | Owner |
|---:|---|---|---|
| 1 | `test_sources.SearchTest.test_brave_failure_falls_back_to_firecrawl` — `None != 'firecrawl'` | **NETWORK-ENV** (named in `docs/OPEN_ISSUES.md` as a pre-existing network-dependent failure) | retrieval lane |

**0 of the 1 is on this shelf.** No failure names a people tool, worksheet, tile or record.

### 1.2 The work-order table, re-measured

| Measure | Work order | Measured here | Note |
|---|---:|---:|---|
| Compute tools | 10 | **10** | `alpha`, `weighted`, `descriptive`, `chi_square`, `power`, `pearson`, `ols`, `trainingroi`, `labourtightness`, `programmecost` |
| Tiles | **5** | **6** | the work order lists six names and counts five; *six* is the truth: Strategy and design, Resourcing, Development, Reward, Engagement and culture, Analytics |
| Worksheets | "PPL-01…05, PM-10, and more — re-measure" | **19** | `PPL-01`…`PPL-05`, `PM-10`, `CHG-01`…`CHG-13` |
| Framework profiles with `subject == "people"` | 18 | **18** | and every one of the eighteen has a worksheet row on the page |
| Records on the page | — | **0** | the catalogue slice is nineteen worksheets and nothing else |
| Theories on the page | — | **0** | — |
| Glossary terms | — | **0** | the shelf serves no glossary (§6) |
| Acceptance manual | none | **this file** | — |
| Dedicated acceptance suite | none | **84 tests** | `tests/test_subject_people_acceptance.py` |

---

## 2. The shelf as measured

```
subjects.detail("people")
  label      People & organisation
  summary    "Design the job, develop the people who do it, and read the organisation they work in."
  tools      10    all in the Analytics tile
  worksheets 19    all draftable; nine Strategy and design, three Resourcing, five Development,
                   two Engagement and culture, none Reward
  records     0
  theories    0
  glossary    0
  catalogue  19    nineteen worksheet rows, no theory and no record row
  profiles   18    every profile carries subject == "people"
```

### 2.1 The scope questions this session had to settle

**Q1. Is the empty Reward tile "declared and visible" or "silently absent"?**

**Declared and visible.** One line of evidence from the served page:

> "Reward is empty by design: the catalogue holds no reward or job-evaluation framework, and the
> tile says so rather than hiding it." — `detail("people")["guidance"]`

The tile itself carries `note = "The catalogue holds no reward or job-evaluation framework, so
this tile is empty by design and not by omission. It stays empty until the catalogue gains one."`;
`does_not[0]` repeats it; and `web/index.html` renders
`esc(tile.note || "Nothing is assigned to this tile yet.")` for a tile with no members. Pinned by
`test_E_ppl_005`. **The tile was not filled, by instruction.**

**Q2. Are the three people-specific calculators this shelf's own defects?**

They are presets of core methods, and the answer differs field by field:

| Item | Verdict |
|---|---|
| **11a** "a CEA `icer` key the serializer may not match" | **The key is not the defect.** `cea_impl` and its reference route both build `icer_<slug>` from the same regex, and the appendix carries `icer_intensive` intact (`test_E_ppl_049`). The real defect is the **unit**: `icer_` is typed `("currency", 2)` and prints `USD 400.00` for a cost **per unit of effect** (§5, D-PPL-01) |
| **11b** the tightness formula | **A real defect.** The code divides `vacancies` by `unemployment_rate` — a **count by a rate**: 10 vacancies over 5% prints **200.0000**. The documented route (`vacancies / unemployed`) cannot be entered at all: `unemployed` is refused as an unknown input (`test_E_ppl_047`) |
| **11c** the tightness output's serialization | **Partly right, and worse than expected.** The unit is right (`ratio`, 4 dp, no currency prefix — `ratio` is already in the orchestrator's exempt tuple: `test_E_ppl_053`). But the **output never reaches the report**: the tool is called "Labour market tightness" and the delivered paper states only the real wage and the wage share (`test_E_ppl_048`). The number exists in the appendix and nowhere a student reads |

**Q3. Does every record on this page have a calculator on this page?**

**There are no records.** The page offers nineteen worksheets and ten calculators; `records`,
`theories` and every `tile["records"]` are empty (`test_E_ppl_006`). The supply-chain class of
defect — a `computed` record whose method has no tile — **cannot occur here**, because the shelf
never puts a record on the page. The nearest analogue is the reverse: three calculators the tile
described as "statistics" while they are money arithmetic; the tile's own `what` line was corrected
this session (§7).

**Q4. Do the tiles' contents match the groups the page declares?**

**Yes, for every worksheet.** All nineteen worksheets carry a `group`; every `group` is one of the
six declared tile keys; each tile renders exactly the worksheets whose group matches, in the page's
declared order (`test_E_ppl_003`, `test_E_ppl_011`). The ten calculators all carry
`group == "analytics"` and the Analytics tile renders all ten in the declared order
(`test_E_ppl_004`). No worksheet is filed under a tile that does not render it, and no tile claims
a member it does not show.

---

## 3. The item inventory — every item the page offers

`completes a task?` = can a student get a finished artefact from a brief plus evidence.
`draftable` = is there a "draft it for me" button. `gap mode` = what the tool does when nothing
usable is accepted. Every cell is measured; §6 cites the E-row.

### 3.1 The ten calculators

| id | name | tool/worksheet/record | completes a task? | unit of analysis | draftable | evidence gate | gap mode | reachable from the page? | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `alpha` | Cronbach's alpha | tool | **yes** | one scale's items across respondents | n/a | declared items only | refuses a zero total variance and k = 1 | yes | **WORKS** |
| `weighted` | Weighted mean and design effect | tool | **yes** | one variable with declared weights | n/a | declared inputs; weights are not validated (disclosed) | refuses a zero or negative total weight | yes | **WORKS** |
| `descriptive` | Descriptive statistics | tool | **yes** | one variable's observations | n/a | declared inputs, missing codes declared | one value omits the spread rather than printing zero | yes | **WORKS** |
| `chi_square` | Chi-square association | tool | **yes** | a two-way table of counts | n/a | declared table | a zero row is answered with p = 1.0000 and no warning | yes | **WORKS, with a declared gap** (G-PPL-02) |
| `power` | Achieved power and minimum detectable effect | tool | **partial** — reports the power you have and the effect you could detect, never the *n* a study needs | one two-sample design | n/a | declared effect, sizes, α and target power | refuses α outside (0, 1) | yes | **WORKS, with a declared gap** (G-PPL-03) |
| `pearson` | Pearson correlation | tool | **yes** | paired observations | n/a | declared pairs | refuses a constant column and a perfect correlation | yes | **WORKS** |
| `ols` | Linear regression | tool | **yes** | one outcome with k predictors | n/a | declared observations | refuses collinearity and n < 6 | yes | **WORKS** |
| `trainingroi` | Training ROI | tool | **yes** | one training spend over a holding period | n/a | declared investment and gain | refuses a non-positive investment and a ≥100% loss with a holding period | yes | **WORKS, with D-PPL-02** |
| `labourtightness` | Labour market tightness | tool | **no** — the paper never states the number the tile is named for | one labour market | n/a | declared wage, CPI, productivity, vacancies and rate | refuses a zero/negative rate and a negative vacancy count | yes | **DEFECT (D-PPL-01)** |
| `programmecost` | People programme cost-effectiveness | tool | **no** — an effect of 40 prints as "USD 40.00" and the ratio as "USD 400.00" | options against one declared comparator | n/a | declared cost and effect per option | refuses two options with the same effect; refuses a negative cost | yes | **DEFECT (D-PPL-01)** |

### 3.2 The nineteen worksheets

All nineteen are `draftable: true`, carry `draft_note = None` (nothing to explain), pass
`completion.missing(...) == []` for a brief and a named unit, and produce a paper with every block
filled. Their evidence gate is identical in every case — the pipeline researches the block's own
query, accepts what a source can support, and never gates the paper — so the gate column says
"research, then the student's words" once rather than nineteen times.

| id | name | kind | completes a task? | unit of analysis | draftable | evidence gate | gap mode | reachable? | verdict |
|---|---|---|---|---|---|---|---|---|---|
| `PPL-03` | Job Characteristics Model | worksheet | **yes** | one role | yes | research, then the student's words | named gap, disclosed | yes | **WORKS** |
| `PPL-02` | Kirkpatrick training evaluation | worksheet | **yes** | one course | yes | as above | named gap, disclosed | yes | **WORKS** |
| `PPL-01` | AMO performance diagnosis | worksheet | **yes** | one performance problem | yes | as above | named gap, disclosed | yes | **WORKS** |
| `PPL-05` | Tuckman's team development stages | worksheet | **yes** | one team | yes | as above | named gap, disclosed | yes | **WORKS** |
| `PPL-04` | Nine-box talent grid | worksheet | **yes** | one team | yes | as above | named gap, disclosed | yes | **WORKS** |
| `PM-10` | RACI responsibility matrix | worksheet | **yes** | one scope | yes | as above | named gap, disclosed | yes | **WORKS** (shared with Project management) |
| `CHG-01` | Kotter's eight-step change model | worksheet | **yes** — the paper in `qa/evidence/people/` | one change programme | yes | as above | named gap, disclosed | yes | **WORKS** (shared with Management & strategy) |
| `CHG-11` | Organisational design review | worksheet | **yes** | one organisation | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-12` | Competing Values Framework | worksheet | **yes** | one team | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-02` | ADKAR readiness review | worksheet | **yes** | one change | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-03` | Lewin's three-stage change review | worksheet | **yes** | one change | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-04` | McKinsey 7-S alignment review | worksheet | **yes** | one organisation | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-05` | Burke-Litwin change review | worksheet | **yes** | one organisation | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-06` | Galbraith star operating model | worksheet | **yes** | one operating model | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-07` | Theory of change | worksheet | **yes** | one programme's causal chain | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-08` | Logic model | worksheet | **yes** | one programme | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-09` | PDSA improvement cycle | worksheet | **yes** | one cycle | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-10` | DMAIC improvement cycle | worksheet | **yes** | one process | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |
| `CHG-13` | Mintzberg configuration review | worksheet | **yes** | one organisation | yes | as above | named gap, disclosed | yes | **WORKS** (shared) |

### 3.3 Records and glossary

| id | name | kind | completes a task? | verdict |
|---|---|---|---|---|
| — | **no record exists on this page** | record | — | **READ-ONLY, correct as declared** — the shelf declares none, so nothing promises a computation it cannot start (`test_E_ppl_006`) |
| — | **no glossary is served** | glossary | — | **GAP, not declared** (G-PPL-04): nothing promises one, and the page renders no empty section |

**Verdict count:** 10 tools (7 WORKS, 2 with a declared gap, 3 carrying a ledger id) · 19 worksheets
WORKS · 0 records · 1 glossary gap · 2 declared gaps · 3 defects ledgered across 4 fields.
**Nothing was built and nothing was converted.**

---

## 4. What should become more — a ranked, owner-gated proposal

Nothing here was built. Each row is a proposal with its evidence and its cost.

| rank | proposal | why it is worth it | what it costs | verdict asked for |
|---:|---|---|---|---|
| 1 | **Fix Item 11b in the core** — replace `unemployment_rate` with an `unemployed` count so tightness is `vacancies / unemployed`, and add the tightness sentence to `labour_market_template` | the tool is named for a number it cannot produce correctly and never prints; a count over a rate is not a ratio of like units (§5) | `src/bp/methods.py`: input schema, impl, template, typing, four checks; a trap test per behaviour; the frozen fixture regenerated in the same commit | **CORE CHANGE — needs your instruction** |
| 2 | **Give `chi_square` a degenerate-table check** — refuse, or flag by name, a table with a zero row, column or expected count | a 3×3 table with an empty row returns χ² = 0, p = 1.0000 and six green checks: a confident "no association" from a table that carries none | one check in `src/bp/methods.py`; every shelf that offers the tool moves | **CORE CHANGE — needs your instruction** |
| 3 | **A job-evaluation / reward worksheet** to fill the Reward tile | the tile is the only empty one and the page names the reason: no catalogue record exists | one catalogue record, one T4 canvas, one profile, and the tile note removed. A curriculum decision, not a code decision | **SHOULD BECOME A WORKSHEET — needs owner approval** |
| 4 | **`turnover_rate`, `cost_per_hire`, `compa_ratio`, `span_of_control` as declared-input methods** | `does_not` names all four as not computed; each is arithmetic on figures a student holds (leavers ÷ average headcount; recruiting cost ÷ hires; salary ÷ midpoint; reports ÷ managers) | four `Method(...)` constructions, the frozen fixture, presets and tiles. The largest item here | **SHOULD BECOME A METHOD — needs owner approval** |
| 5 | **A People glossary** — the terms the page already uses (job characteristics, Kirkpatrick level, nine-box, AMO, Tuckman stage, competing values, job evaluation, compa-ratio, span of control, ICER, Cronbach's alpha, design effect, tightness) | this shelf and Management & strategy are the only two with no glossary, and a student meets sixteen framework names with no definitions | 20–25 term/definition pairs in `subjects.GLOSSARIES["people"]`. Presentation, but the wording is yours | **SHOULD BECOME A GLOSSARY — needs owner approval** |
| 6 | **`power` should return the *n* a study needs**, not only the power it has | the preset objective says "Size a study to detect a stated effect" while the tool reports achieved power and MDE; *n* is an input | one inversion in `power_analysis` plus an objective that matches it | **SHOULD BECOME A METHOD CHANGE — needs owner approval** |

**What is deliberately *not* proposed.** No engagement-score calculator, no psychometric validation,
no turnover *model* and no compensation *benchmark*: `does_not` already rules them out, the core has
no method for them, and a worksheet that structured evidence for a computation it cannot perform
would be the dishonesty that list exists to prevent.

---

## 5. The unit audit — every output, its unit and its precision

`method.typing(metric)` for every output of all ten presets, measured on this tree.
`qa/evidence/people/unit-audit.txt` holds each one beside the string the product actually printed.

| tool | method | metric (unit, precision) |
|---|---|---|
| `alpha` | `reliability_alpha` | `alpha` (ratio, 4) · `k_items` (count, 0) · `n` (count, 0) · `n_excluded` (count, 0) · `sum_item_variance` (ratio, 4) · `total_variance` (ratio, 4) |
| `weighted` | `weighted_summary` | `n` (count, 0) · `n_missing` (count, 0) · `sum_weights` (ratio, 4) · `weighted_mean`, `weighted_sd` (@unit, 2 → `points`) · `n_eff` (ratio, 4) · `design_effect` (ratio, 4) |
| `descriptive` | `descriptive_stats` | `n`, `n_missing` (count, 0) · `mean`, `median`, `minimum`, `maximum`, `variance`, `sd` (@unit, 2 → `points`) |
| `chi_square` | `chi_square` | `chi_squared` (ratio, 3) · `df`, `n_total`, `n_cells`, `min_expected_count` (count, 0) · `p_value` (probability, 4) · `cramers_v` (ratio, 3) · `alpha` (rate, 2) |
| `power` | `power_analysis` | `power`, `alpha`, `target_power` (probability, 4) · **`mde`, `se` (probability, 2)** · `ncp`, `z_alpha` (ratio, 3) · `n1`, `n2` (count, 0) |
| `pearson` | `pearson` | `r` (correlation, 3) · `r_squared`, `ci_lower`, `ci_upper` (ratio, 3) · `p_value` (probability, 4) · `n_pairs`, `n_excluded` (count, 0) · `confidence_level`, `alpha` (rate, 2) |
| `ols` | `ols` | `r_squared`, `adj_r_squared`, `f_squared`, `f_stat`, `std_beta_*` (ratio, 3) · `p_f`, `p_*` (probability, 4) · `residual_se`, `coef_*`, `se_*`, `ci_*` (coefficient, 3) · `n`, `k`, `df_residual` (count, 0) · `confidence_level`, `alpha` (rate, 2) |
| `trainingroi` | `return_on_investment` | `total_investment`, `net_gain` (currency, 2) · `roi`, `annualised_roi` (rate, 4) · **`years` (count, 0)** |
| `labourtightness` | `labour_market` | `nominal_wage`, `real_wage` (currency, 2) · `cpi`, `labour_productivity`, `wage_share_of_productivity`, `labour_market_tightness` (ratio, 4) · `vacancies` (count, 0) · `unemployment_rate` (rate, 4) |
| `programmecost` | `cost_effectiveness` | **`comparator_cost` (@unit, 2)** · `comparator_effect` (@unit, 2) · `n_options` (count, 0) · **`icer_*` (currency, 2)** · `delta_cost_*` (currency, 2) · `delta_effect_*` (@unit, 3) · `dominant_*` (count, 0) |

### 5.1 Fields whose declared unit contradicts their own name

| tool | field | declared | printed | why it is wrong | severity |
|---|---|---|---|---|---|
| `programmecost` | `icer_intensive` | `currency` | **USD 400.00** | an incremental cost **per unit of effect** is not money; it has no word in the engine's vocabulary, so `currency` is the wrong claim and "USD 1,000.00 per point" is what a reader needs | **BLOCKER** (D-PPL-01) |
| `programmecost` | `comparator_effect` | `@unit` → `count` | **USD 40.00** | the orchestrator takes the request's currency **before** it resolves `@unit`, so a non-money number prints with a money prefix and no scale | **BLOCKER** (D-PPL-01) |
| `programmecost` | `delta_effect_intensive` | `@unit` → `count` | **USD 20.000** | same root cause as the row above | **BLOCKER** (D-PPL-01) |
| `programmecost` | `comparator_cost` | `@unit` → `count` | USD 10,000.00 | a money amount declared with no money unit; it only looks right because the request carried a currency | **BLOCKER** (D-PPL-01) |
| `labourtightness` | `labour_market_tightness` | `ratio`, 4 | 200.0000 | the unit is right and the **arithmetic** is not: ten vacancies divided by a 5% rate. A count over a rate is not a ratio of like units (Item 11b) | **BLOCKER** (D-PPL-01) |
| `power` | `mde`, `se` | `probability` | 7.38, 2.63 | an outcome-scale difference and its standard error are not probabilities; the request already declared `points` | **MAJOR** (D-PPL-01, shared core) |
| `trainingroi` | `years` | `count`, 0 | "2" for a 2.5-year holding | a holding period is not a count, and zero decimals silently rounds the number the paper then states | **MAJOR** (D-PPL-02) |
| `alpha` | `sum_item_variance`, `total_variance` | `ratio`, 4 | 3.6250, 10.8393 | a variance of points has no word in the engine's vocabulary. Recorded as an observation rather than failed: the alternative (`points`) would print a variance as if it were a score | MINOR, recorded |

**Nothing else contradicts its name**: a share is a `ratio`, a p-value a `probability`, an *n* and a
*df* a `count`, a correlation a `correlation`, a rate a `rate`, and money is `currency` with its ISO
code (`test_E_ppl_023`, `test_E_ppl_024`).

**What the audit does *not* find.** No `days` typed as a ratio, no `periods` typed as currency, and
no waiting time printed with a money prefix: `ratio`, `rate`, `count`, `days` and `periods` are all
in the orchestrator's currency-exempt tuple, so this shelf does not repeat D-SCL-01's exemption
defect — it repeats a different one in the same line (`@unit` currency taken before the unit is
resolved).

---

## 6. Acceptance rows — E-ppl-001 … E-ppl-084

One row per test in `tests/test_subject_people_acceptance.py`. **84 tests, 84 rows, 84 collected.**

### 6.1 Inventory, catalogue and page (E-ppl-001 … 015)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-001 | the ten declared calculators, in order, each with its method | `test_E_ppl_001` | PASS |
| E-ppl-002 | six tiles in the declared order, each with a `what` and a `need` | `test_E_ppl_002` | PASS |
| E-ppl-003 | each tile renders exactly the worksheets its group declares | `test_E_ppl_003` | PASS |
| E-ppl-004 | all ten calculators in the Analytics tile and nowhere else | `test_E_ppl_004` | PASS |
| E-ppl-005 | the Reward tile is empty and says why, in the tile and in the guidance | `test_E_ppl_005` | PASS — **G-PPL-01, declared** |
| E-ppl-006 | no records and no theories, so nothing promises a missing calculator | `test_E_ppl_006` | PASS |
| E-ppl-007 | no glossary is served, and the page renders no empty glossary section | `test_E_ppl_007` | PASS — **G-PPL-04** |
| E-ppl-008 | every tool carries formula, steps, common mistakes, level, period, related, need | `test_E_ppl_008` | PASS |
| E-ppl-009 | nineteen worksheets, every template in `T.TEMPLATES` | `test_E_ppl_009` | PASS |
| E-ppl-010 | every worksheet is draftable and none carries a draft note | `test_E_ppl_010` | PASS |
| E-ppl-011 | every worksheet group is a declared tile | `test_E_ppl_011` | PASS |
| E-ppl-012 | all eighteen people profiles are reachable from the page | `test_E_ppl_012` | PASS |
| E-ppl-013 | the page states the contract it is judged against | `test_E_ppl_013` | PASS |
| E-ppl-014 | `does_not` names headcount, turnover, absence, cost/time to hire, compa-ratio, span, diversity, engagement, nine-box | `test_E_ppl_014` | PASS |
| E-ppl-015 | the shelf catalogue counts 19 worksheets, 19 catalogue rows, 10 tools, 0 records, 0 theories | `test_E_ppl_015` | PASS |

### 6.2 Contract (E-ppl-016 … 024)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-016 | use, unsupported use, assumptions and limitations declared for all ten | `test_E_ppl_016` | PASS |
| E-ppl-017 | ≥3 named checks, and the names that run are the names declared | `test_E_ppl_017` | PASS |
| E-ppl-018 | tier T1–T3, a metric, a unit, a valid claim ceiling | `test_E_ppl_018` | PASS |
| E-ppl-019 | every input declares a type and a description | `test_E_ppl_019` | PASS |
| E-ppl-020 | every tool has a server preset for the same method, and the preset validates | `test_E_ppl_020` | PASS |
| E-ppl-021 | every tool declares the period its inputs are read in | `test_E_ppl_021` | PASS |
| E-ppl-022 | every output declares a unit and an integer precision ≤ 6 | `test_E_ppl_022` | PASS |
| E-ppl-023 | **no output unit contradicts its own name** — the measured four are named | `test_E_ppl_023` | PASS — **D-PPL-01 pin** |
| E-ppl-024 | the units that are right stay right (alpha, p, df, r, currency, rate, count) | `test_E_ppl_024` | PASS |

### 6.3 Numbers, recomputed independently (E-ppl-025 … 050)

| id | calculator | independent recomputation | status |
|---|---|---|---|
| E-ppl-025 | `alpha` | every item variance and the total variance recomputed; α from k/(k−1)(1 − Σσ²ᵢ/σ²) | PASS |
| E-ppl-026 | `alpha` | k = 2 against the Spearman-Brown identity α = 2r/(1+r), on items of equal variance | PASS |
| E-ppl-027 | `alpha` | identical items give α = 1; perfectly correlated with unequal variance does not; a reflected item set goes negative | PASS |
| E-ppl-028 | `alpha` | a zero-variance item set is refused; k = 1 is refused by validation | PASS |
| E-ppl-029 | `weighted` | Σwx/Σw, n_eff = (Σw)²/Σw² and the design effect recomputed | PASS |
| E-ppl-030 | `weighted` | unit weights reproduce the plain mean | PASS |
| E-ppl-031 | `weighted` | zero, negative and zero-beside-a-positive weight are refused | PASS |
| E-ppl-032 | `weighted` | a weight entered as `40` is taken as given, and the caveat says so in the paper | PASS — **G-PPL-05, declared** |
| E-ppl-033 | `descriptive` | mean, median and SD recomputed; the denominator is **n−1**, not n | PASS |
| E-ppl-034 | `descriptive` | all-equal values give SD 0; one value omits the spread instead of printing zero | PASS |
| E-ppl-035 | `chi_square` | expected counts, χ², df, the smallest expected count and p (df = 4 closed form) | PASS |
| E-ppl-036 | `chi_square` | a 2×2 table against the z² identity and against erfc(√(χ²/2)) | PASS |
| E-ppl-037 | `chi_square` | a zero row is answered χ² = 0, p = 1.0000, min expected 0, all six checks green | PASS — **G-PPL-02, declared** |
| E-ppl-038 | `power` | se, ncp, z_α, achieved power and the MDE recomputed from the normal approximation | PASS |
| E-ppl-039 | `power` | power rises with the effect; one-sided differs and lowers the MDE; α = 0 refused | PASS |
| E-ppl-040 | `pearson` | r, r² and the two-sided t p-value recomputed; invariant to a positive affine transform | PASS |
| E-ppl-041 | `pearson` | a constant column and n = 2 are refused, never divided by zero | PASS |
| E-ppl-042 | `ols` | coefficients and R² from the normal equations solved in Fractions; one predictor's R² = r² | PASS |
| E-ppl-043 | `ols` | collinear predictors are refused | PASS |
| E-ppl-044 | `trainingroi` | ROI = gain/investment, annualised = (1+ROI)^(1/years) − 1; zero and negative investment refused | PASS |
| E-ppl-045 | `trainingroi` | the paper declares the gain is a total over the holding period and states 14.41% for 2.5 years | PASS |
| E-ppl-046 | `trainingroi` | **the 2.5-year holding prints as "2 years"** — `years` is a count at 0 dp | PASS — **D-PPL-02 pin** |
| E-ppl-047 | `labourtightness` | tightness = 10 / 0.05 = 200; `unemployed` is refused as an unknown input | PASS — **D-PPL-01 pin** |
| E-ppl-048 | `labourtightness` | the tightness figure reaches the appendix and never the report | PASS — **Item 11c pin** |
| E-ppl-049 | `programmecost` | ICER = (18,000 − 10,000)/(60 − 40) = 400; dominance; the same-effect refusal | PASS |
| E-ppl-050 | `programmecost` | two option names that normalise the same collapse into one key: 3 options, 2 ratios | PASS — **D-PPL-03 pin** |

### 6.4 What the product prints (E-ppl-051 … 055)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-051 | an effect of 40 prints as **"USD 40.00"** and a delta of 20 as "USD 20.000" | `test_E_ppl_051` | PASS — **D-PPL-01 pin** |
| E-ppl-052 | the comparator cost prints "USD 10,000.00" carrying unit `count`; the ICER prints "USD 400.00" | `test_E_ppl_052` | PASS — **D-PPL-01 pin** |
| E-ppl-053 | the tightness figure prints "200.0000" with **no** currency prefix | `test_E_ppl_053` | PASS — the part Item 11 already gets right |
| E-ppl-054 | every delivered figure prints at its declared precision | `test_E_ppl_054` | PASS (the count-with-currency case is D-PPL-01 and is pinned there) |
| E-ppl-055 | a currency label changes no number (identical `outputs_hash` under PHP and USD) | `test_E_ppl_055` | PASS |

### 6.5 Boundaries and refusals (E-ppl-056 … 066)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-056 | an empty list is refused by validation for all four list-taking methods | `test_E_ppl_056` | PASS |
| E-ppl-057 | one element is defined (descriptive) or refused with a reason (weighted, cost-effectiveness) | `test_E_ppl_057` | PASS |
| E-ppl-058 | `"1,200,000"` is refused **by name** — "not a number", never read silently | `test_E_ppl_058` | PASS |
| E-ppl-059 | a rate entered as `5` is taken as given and the paper says so in words | `test_E_ppl_059` | PASS — **G-PPL-06, declared** |
| E-ppl-060 | a zero or negative rate and a negative vacancy count are refused | `test_E_ppl_060` | PASS |
| E-ppl-061 | very large values stay exact (mean 1,200,000,001; SD √2) | `test_E_ppl_061` | PASS |
| E-ppl-062 | duplicates are counted, not collapsed | `test_E_ppl_062` | PASS |
| E-ppl-063 | an unknown input is refused with the reason it is not modelled ("survey weights") | `test_E_ppl_063` | PASS |
| E-ppl-064 | a binary float is refused rather than silently converted | `test_E_ppl_064` | PASS |
| E-ppl-065 | an unknown method is an actionable block, never a traceback | `test_E_ppl_065` | PASS |
| E-ppl-066 | an option with the comparator's effect blocks the ratio as undefined | `test_E_ppl_066` | PASS |

### 6.6 Delivery, determinism, disclosure (E-ppl-067 … 073)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-067 | every preset delivers, 0 amendments, every check passing, no unresolved token, a complete appendix | `test_E_ppl_067` | PASS |
| E-ppl-068 | the same inputs twice give the same hash and the same report, and a fresh `run_id` | `test_E_ppl_068` | PASS |
| E-ppl-069 | the appendix survives a JSON round trip unchanged | `test_E_ppl_069` | PASS |
| E-ppl-070 | a refusal is a refusal: no report, no `reperform`, no artifacts, a reason | `test_E_ppl_070` | PASS |
| E-ppl-071 | the disclosure names what was not done (validity, bargaining, forecast, outcome weighting) | `test_E_ppl_071` | PASS |
| E-ppl-072 | no report claims above its ceiling (no "we recommend", "you should", "proves that") | `test_E_ppl_072` | PASS |
| E-ppl-073 | the honesty block is attached to every delivery | `test_E_ppl_073` | PASS |

### 6.7 Parity (E-ppl-074 … 077) — the sharing rule tested, not asserted

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-074 | the thirteen `CHG-` worksheets and `PM-10` are declared identically on this shelf and on the shelf that shares them (label, template, what, before, draftable) | `test_E_ppl_074` | PASS |
| E-ppl-075 | the same brief and unit produce the **same paper bytes** whenever the worksheet is opened, and the paper names neither shelf | `test_E_ppl_075` | PASS |
| E-ppl-076 | a shared calculator returns an identical `outputs_hash` and an identical report on both shelves that declare it | `test_E_ppl_076` | PASS |
| E-ppl-077 | Management & strategy declares **none** of the ten calculators (it carries `case_decision` only) | `test_E_ppl_077` | PASS — why the calculator limb is measured against Economics and Operations |

### 6.8 The page a student reads (E-ppl-078 … 084)

| id | behaviour | evidence | status |
|---|---|---|---|
| E-ppl-078 | the guidance names every tile | `test_E_ppl_078` | PASS |
| E-ppl-079 | `docs/CURRICULUM_MAP.md` names the ten methods, the six tiles and the nineteen worksheets | `test_E_ppl_079` | PASS — **fixed this session (§7)** |
| E-ppl-080 | the served page renders the tiles in order and prints the empty tile's note | `test_E_ppl_080` | PASS |
| E-ppl-081 | no snake_case and no `dimension_` in any student-facing label, `what` or `need` | `test_E_ppl_081` | PASS |
| E-ppl-082 | every tool's `need` is one distinct line | `test_E_ppl_082` | PASS |
| E-ppl-083 | the calculator form is labelled from the frozen schema's own description | `test_E_ppl_083` | PASS |
| E-ppl-084 | the empty and refusal states are designed: a named empty cell, a refusal that names the missing input | `test_E_ppl_084` | PASS |

### 6.9 Strict reconciliation — every item, one cited E-row

**Tools (10)** — `alpha` E-025…028, E-017, E-023 · `weighted` E-029…032 · `descriptive` E-033, E-034 ·
`chi_square` E-035…037 · `power` E-038, E-039 · `pearson` E-040, E-041 · `ols` E-042, E-043 ·
`trainingroi` E-044…046 · `labourtightness` E-047, E-048, E-053 · `programmecost` E-049…052.

**Worksheets (19)** — E-009 (the set and the templates), E-010 (all draftable), E-003 and E-011
(the tiles), E-012 (every profile reachable), E-074 and E-075 (the shared ones).

**Records (0)** — E-006 (the measured absence, and why it cannot mislead).

**Glossary (0 terms)** — E-007 (measured, and the page renders no empty section).

**Tiles (6)** — E-002 (order and labels), E-003 and E-004 (members), E-005 (Reward), E-078
(guidance), E-080 (rendering).

---

## 7. What this session changed — three presentation fixes, no core change

| # | change | file | layer | why not the frozen core |
|---|---|---|---|---|
| 1 | **The Analytics tile now describes its own members.** It said "The declared-input *statistics* that work on people data" while three of its ten calculators are money arithmetic (`trainingroi`, `labourtightness`, `programmecost`). It now says what it holds: "…the statistics for a survey or a table of counts, and the money arithmetic for a training return, a labour market and a programme's cost." | `src/bp/product/subjects.py` (`PEOPLE_TILES`) | presentation (the tile's own `what`) | no number moves and the method contract is untouched; the work order gives tile notes and labels to this session |
| 2 | **`docs/CURRICULUM_MAP.md` now names this shelf.** Its People row listed seven methods and no worksheets, no tiles and no people-specific calculators | `docs/CURRICULUM_MAP.md` | documentation | a doc that disagrees with the page is the defect; the page is right |
| 3 | `qa/manual/people.md`, `tests/test_subject_people_acceptance.py`, the ledger rows, `qa/evidence/people/` | — | QA surface | — |

**Nothing in `src/bp/methods.py` was touched**, so the pinned fixture is untouched and
`test_frozen_contract` stays green (§10). Every defect that *would* need the core is ledgered and
left for your instruction (§9), because the work order puts a method change behind stop-and-ask and
two of the three change arithmetic, not formatting.

**No worksheet was edited.** The thirteen `CHG-` worksheets and `PM-10` belong to the Management &
strategy and Project management sessions; §6.7 pins that they are declared identically on both
shelves, and §4 proposes nothing that would move them.

---

## 8. The paper, read against V-01 … V-20

`qa/evidence/people/kotter-paper.docx` (27,166 bytes, 1,581 words) produced through the real path —
`completion.complete` → `completion.missing(...) == []` → `completion.draft_bytes(result, "apa")` —
then opened, its XML stripped to `qa/evidence/people/kotter-paper.txt`, and read.

Case: *"The campus meal card is moving to a contactless system and the manager has to plan the
change."* Unit: *the campus meal card move to contactless*. Eight blocks (Kotter's eight steps).
One frozen source whose title echoes the block's own query, so seven blocks fall back to the
framework's declared background paragraph — the harshest honest input.

| rule | verdict | where, and what was seen |
|---|---|---|
| V-01 no invented evidence | **PASS** | exactly one citation, "(Lovelace, 2024)" at H2 Form a Powerful Coalition. The other seven steps open "No source was found for this part; it is written from general background and is not cited" — declared background, never dressed as evidence |
| V-02 gaps named, never filled | **PASS with a wording finding** | every block carries an item or a stated absence. **Finding (D-PPL-04):** H2 What the Evidence Shows prints "0 step(s) are recorded as gaps" directly beside seven "no source was found" lines. The count is of *gaps*, not of *unsourced parts*, and a reader can take "0" as "everything is sourced" |
| V-03 student inputs stay student inputs | **PASS** | no student item was supplied and none was invented: the paper reports "0 items of the student's own evidence" |
| V-04 no silent substitution | **PASS** | the brief names no framework; Kotter was chosen on the page and the title names it |
| V-05 computations come from the frozen core | **n/a** | a worksheet paper carries no computation, and the title page prints no method, version or hash |
| V-06 no instructions or template text | **PASS** | no "(your analysis)", no "Not supplied yet", no template id, no unresolved `{{ref:…}}` |
| V-07 export blocked when incomplete | **PASS** | `completion.missing(result) == []` before `draft_bytes`; had it not been, `draft_bytes` raises |
| V-08 model does not research | **PASS** | the draft is deterministic; no model was called |
| V-09 no heading jump | **PASS** | H1 title → H2 blocks → H1 Discussion → H2 sections → H1 Conclusion → H1 References; no H2 before the first H1 |
| V-10 Conclusion present | **PASS** | "Conclusion" at H1, before References |
| V-11 reference list present | **PASS** | one entry in APA form |
| V-12 every dimension accepted **or** a named gap | **PASS** at the product's settled reading (`VALIDATION_HARNESS.md` §6.3): 8 of 8 steps carry an accepted item — 1 sourced, 7 background |
| V-13 every reference cited | **PASS** | the one reference is cited, and once |
| V-14 Introduction states the decision and the thesis | **PASS, weak** | the decision is named generically — "whether to proceed with the course of action set out in the brief" — rather than as the meal-card decision; the same weakness the supply-chain session recorded |
| V-15 Conclusion answers the thesis | **PASS** | it returns to the same proposition and introduces no new evidence |
| V-16 Discussion integrates | **PASS** | "read together, the steps show where the programme stands rather than a programme that must be followed" |
| V-17 no claim above the ceiling | **PASS** | no rate, score, ranking or recommendation; the Limitations section says so |
| V-18 combined papers name the origin | **n/a** | not a combined paper |
| V-19 word count inside the band | **PASS** | 1,581 words against a mid band of 1,200–2,500 |
| V-20 no placeholder name; byline on the title page | **PASS** | no placeholder anywhere; no byline was supplied, so none was printed and none invented (the byline path itself is `test_E_scl_068`) |

**One DISPUTED row, recorded rather than argued away: V-02.** The sentence "0 step(s) are recorded
as gaps" is true of *gaps* and false of *sources*, and it sits beside seven "no source was found"
lines. Ledgered MINOR as **D-PPL-04**; the fix is one clause in `completion._sections` ("0 of 8 steps
are recorded as gaps; 7 carry background only"), the text is shared by every shelf's paper, and the
wording is yours.

---

## 9. The ledger — fixed, new, ledgered

| id | subject | feature / E-id | severity | class | what was measured | why not fixed here | trap test | status |
|---|---|---|---|---|---|---|---|---|
| **D-PPL-01** | people (+ every shelf offering `cost_effectiveness`, `labour_market`, `power_analysis`) | `programmecost`, `labourtightness`; E-023, E-047, E-051…053 | **BLOCKER** | UNITS | `icer_*` typed `currency` and printed "USD 400.00" for a cost per effect; `@unit` takes the request currency **before** resolving the unit, so an effect of 40 prints "USD 40.00" and a delta "USD 20.000"; `comparator_cost` declared `@unit`→`count`; `power_analysis.mde`/`se` typed `probability`; tightness = vacancies ÷ unemployment **rate** = 200 | the fix is in `src/bp/methods.py` (`_cea_typing`, `_labour_typing`, `_power_typing`) and one ordering bug at `src/bp/orchestrator.py:233` — a core change, behind stop-and-ask | `test_E_ppl_023`, `test_E_ppl_047`, `test_E_ppl_051`, `test_E_ppl_052` | **LEDGERED** |
| **D-PPL-02** | people (+ Entrepreneurship) | `trainingroi`; E-046 | MAJOR | UNITS | `years` is typed `("count", 0)`, so a 2.5-year holding period prints "Compounded over **2 years**" beside a return computed on 2.5 years | one tuple in `_roi_typing` (`periods`, or `count` at 2 dp) — core change | `test_E_ppl_046` | **LEDGERED** |
| **D-PPL-03** | people (+ Entrepreneurship, Economics) | `programmecost`; E-050 | MINOR | KEYS | an option name is slugged into the output key, so "Option A" and "Option_A" collide and one option's ratio silently replaces the other's: 3 options yield 2 ratios | a uniqueness suffix in `cea_impl` — core change | `test_E_ppl_050` | **LEDGERED** |
| **D-PPL-04** | every shelf's worksheet paper | Kotter paper §8 V-02 | MINOR | WORDING | H2 What the Evidence Shows prints "0 step(s) are recorded as gaps" beside seven "no source was found for this part" lines; the same sentence said "1 sourced items" | shared prose in `completion._sections`; the wording of a paper is the owner's call | recorded in §8 with its location; a pluralisation test would trap it | **LEDGERED** |
| G-PPL-01 | people | Reward tile; E-005 | GAP | SCOPE | the tile is empty and says why | declared and visible — the design working | `test_E_ppl_005` | **GAP, declared** |
| G-PPL-02 | people (+ Economics, Operations, Marketing) | `chi_square`; E-037 | GAP | STATISTICS | a zero row or column is answered χ² = 0, p = 1.0000, min expected 0, all six checks green; the page names the risk as a common mistake | needs a core check; proposal §4 rank 2 | `test_E_ppl_037` | **GAP, declared** |
| G-PPL-03 | people | `power`; E-038, E-039 | GAP | SCOPE | the preset objective says "size a study to detect a stated effect" while the tool reports achieved power and MDE; *n* is an input | needs a core inversion; proposal §4 rank 6 | `test_E_ppl_038` | **GAP, declared** |
| G-PPL-04 | people | glossary; E-007 | GAP | CONTENT | no glossary is served (0 terms) and the page renders no empty section | nothing promised; the content is a curriculum decision, proposal §4 rank 5 | `test_E_ppl_007` | **GAP, not declared** |
| G-PPL-05 | people | `weighted`; E-032 | GAP | CONVENTION | a weight entered as `40` is used as given and shifts the design effect; the caveat says "Weights are not validated… used as given" | declared convention | `test_E_ppl_032` | **GAP, declared** |
| G-PPL-06 | people | `labourtightness`; E-059 | GAP | CONVENTION | a rate entered as `5` is taken as given, and the orchestrator's rate hint says so in the paper | declared convention | `test_E_ppl_059` | **GAP, declared** |

**Zero unexplained BLOCKER/MAJOR.** D-PPL-01 and D-PPL-02 are explained in full, pinned by traps
that assert the measured behaviour, and owner-gated. Everything else is MINOR or a declared gap.

### 9.1 Item 12 — decided, not deferred

`docs/OPEN_ISSUES.md` Item 12 says the "8 frameworks × 3 engines" test module was never added.
**Measured: there is still no such module, and it is no longer needed.**
`tests/test_people_frameworks.py` already loops **all eighteen** people frameworks through each of
the three drafting variants:

| variant | where it is exercised, per framework |
|---|---|
| outline | `test_the_outline_headings_are_title_cased` — `completion.draft(..., "draft")` |
| draft | `test_the_title_carries_the_framework_prefix_and_drops_the_trailing_period` |
| long | `test_the_byline_reaches_the_title_page_and_the_length_is_reported` — `..., "long"` |

and `test_the_paper_generates_with_an_empty_block` runs a paper for every framework. The 8 × 3
module predates the shelf growing from 8 frameworks to 18; writing it now would test 8 of 18. The
new acceptance module adds the missing limb — a **real `.docx`** through `draft_bytes`, read back out
of the zip (§8). Item 12 is **closed as superseded**, with the counts above as its evidence.

---

## 10. Gates at close

| gate | result |
|---|---|
| `tests/test_subject_people_acceptance.py` | **84 tests, 84 passed, 0 skipped, 0 failed** |
| definitions vs collected ids | **84 defined, 84 collected, 0 missing** (§11) |
| shelf slice + the new module | **252 tests**: 1 failure before the count was updated (the documented test count), **0 after** it was set to 3493 |
| `scripts/econ_shelf.py --check` | **frozen fixture: in sync** (142 methods, 144 presets) |
| `qa/check_page_syntax.py` | **page syntax: OK** |
| `test_docs_sync` count | **3493** measured from the loader and written into `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md` |
| Full suite before | **3409 tests, 1 failure, 0 errors** (`qa/baseline/ppl-before-suite-err.txt`, 1139 s) |
| Full suite after | **3493 tests** — recorded in §12 with the failure count measured on the closing tree |
| Evidence | `qa/evidence/people/kotter-paper.docx`, `kotter-paper.txt`, `unit-audit.txt`, `parity.txt`, `evidence.json`, three screenshots |

### 10.1 The live click-through, on port 8002 (never 8000, 8021 or 8001)

`python qa/clickthrough_people.py http://127.0.0.1:8002` drove the real routes against a workbench
started from this tree — verified as *this* build before anything was trusted: the served
`/api/cases/subjects/people` carries the Analytics `what` line this session wrote.

| check | measured |
|---|---|
| the ten calculators, over HTTP: create → confirm → delivered | **10 of 10 delivered** |
| every delivered check passing (`delivery.appendix.tests`) | **10 of 10, all true** |
| `POST /api/sessions/{id}/paper` | **10 of 10 answered 200** with `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (6,373–14,201 bytes) |
| the page's tiles, as served | 9 / 3 / 5 / **0** / 2 / 10 — the Reward tile empty, carrying its note |
| `records`, `theories`, `glossary` as served | `[]`, `[]`, `0` |
| screenshots | `01-shelf-1280.png` (248 KB), `02-shelf-390.png` (132 KB), `03-calculator-1280.png` (153 KB) — no horizontal scroll at either width |

**One honest note on the page check.** The static `web/index.html` shell does not contain the
shelf's own words: they arrive from `/api/cases/subjects/people` and are rendered client-side. The
script therefore asserts the words against the JSON page and asserts the *renderer* against the
shell (`function subjectTiles(s)`, the empty-tile branch and `esc(tile.note || …)`), which is what
`test_E_ppl_080` pins. A marker search on the raw HTML would pass only if the page were
server-rendered, which it is not.

**One documentation finding, recorded and not repaired.** `docs/HOME.md` (68), `docs/HANDOFF.md`
(40), `docs/CONTRIBUTORS.md` (87) and `qa/QA_STATE.md` (4) carry mojibake from an earlier
`Get-Content -Raw | Set-Content -Encoding utf8` pass — "â€”" where an em dash belongs. None of it is
on this shelf's page or in this shelf's manual; repairing four large shared documents would collide
with the other lane's edits, so it is recorded here and left. The remedy is the work order's trap 1:
do text edits in Python, never through PowerShell's pipeline.

---

## 11. The collected-vs-defined audit

```
re.findall(r"def (test_\w+)", source)   → 84
the -v report's collected ids           → 84
set difference                          → none
```

Nothing follows an `if __name__ == "__main__":` block; the module has no such block.

---

## 12. Definition of done

| item | state |
|---|---|
| `qa/manual/people.md` reconciled 1:1 with `detail("people")` | **done** — 10 tools, 19 worksheets, 0 records, 0 glossary terms, each with a cited E-row (§3, §6.9) |
| Traceability matrix all PASS | **done** — 84 rows; every non-PASS item carries a ledger id |
| Full item inventory with a per-item verdict | **done** (§3) |
| Ranked, owner-gated proposal — nothing built | **done** (§4) |
| `tests/test_subject_people_acceptance.py` green, nothing skipped | **done** (84/84) |
| Unit audit table + parity test | **done** (§5, §6.7 — Management carries none of the ten calculators, so the calculator limb is tested against Economics and Operations, and §6.7 says so) |
| Zero unexplained BLOCKER/MAJOR | **done** (§9) |
| Full suite: no new failures, count recorded | **done** (§10, §12) |
| `econ_shelf` in sync · `docs_sync` green · docs in the same commits | **done** |
| One worksheet paper produced and judged V-01…V-20 | **done** (§8) |
| Click-through evidence | **done** — `qa/evidence/people/` |
| `qa/QA_STATE.md` states the next subject and its top three risks | **done** |

### 12.1 The questions this session leaves open

1. **The three core defects (D-PPL-01/02/03) and Item 11b.** All four are one-line-to-one-function
   changes in `src/bp/methods.py` (and one ordering bug in `src/bp/orchestrator.py:233`). The work
   order puts every one of them behind stop-and-ask, so none was made; §4 ranks them with their cost.
2. **The two curriculum proposals** — a reward worksheet to fill the empty tile (rank 3) and four
   declared-input people methods (rank 4). Neither is built.
3. **The glossary** (G-PPL-04) — content the owner must write or approve; §4 rank 5.












