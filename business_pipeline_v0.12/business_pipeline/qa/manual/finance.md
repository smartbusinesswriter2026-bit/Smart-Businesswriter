# Acceptance manual — `finance` shelf

**Session 2 of 11.** Branch `corpus/merge-v1`, opening commit `ab0be0d`.
Every row below cites a source of truth; nothing here is opinion. The measured
evidence this manual is built from is in `qa/baseline/` (produced by the probes in
`qa/probe_finance_*.py`, `qa/probe_dcf_midyear.py` and `qa/audit_finance.py`).

| Evidence file | What it measures |
|---|---|
| `qa/baseline/finance_catalogue.json` | `subjects.detail("finance")` verbatim |
| `qa/baseline/finance_surface.json` | definition block: guidance, start steps, does-not list, tiles, glossary |
| `qa/baseline/finance_contracts.json` | `bp.methods.LIBRARY[m]` contract for all 35 tools + preset wiring + self-tests |
| `qa/baseline/finance_contracts_rows.txt` | the same, human-readable |
| `qa/baseline/finance_anomalies.txt` | `qa/audit_finance.py` — every contract rule the shelf breaks |
| `qa/baseline/finance_pipeline.json` | every tool driven through `Pipeline().run(...)` |
| `qa/baseline/fin_papers.txt` | every finance capability through the paper formatter |
| `qa/baseline/fin_dcf_midyear.txt` | the independent recomputation for D-FIN-01 |
| `qa/baseline/s2-*.txt` | the Phase 0 baseline suite, its failure set and the gate results |

Source ranks used in this manual (from the work order §5):

1. `bp.methods.LIBRARY[id]` + `tests/fixtures/*_golden.json` — exact contract.
2. `docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md` — what the method is for.
3. `docs/CONDUCTOR_MANUAL.md` §4/§8 + `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20) — paper/export rules.
4. `framework_profiles.PROFILES[...]` — not used: the finance shelf has no worksheet profile.
5. `subjects.SUBJECT_DEFS` / `detail()` — the student-facing promise.
6. `docs/FINANCE_STUDENT_GUIDE.md`, `docs/CURRICULUM_MAP.md` — teaching intent.
7. existing tests — executable intent.

---

## 1. Who it serves

Source: `docs/CURRICULUM_MAP.md` row *Finance* (rank 6), `docs/FINANCE_STUDENT_GUIDE.md` (rank 6),
`subjects.detail("finance")["disciplines"]` (rank 5).

| Course | Level | What the shelf must survive |
|---|---|---|
| Business Finance | SHS (ABM) | time value, a loan, break-even, one investment appraisal |
| Financial Management | UG1–2 | WACC, DCF, the equity bridge, ratios, working capital |
| Investments | UG3+ | CAPM, portfolio return and risk, bonds, options, VaR |

The shelf declares two disciplines (`detail["disciplines"]`):
*f"finance, accounting and managerial economics"* and *"decision analysis and risk quantification"*.
The student-facing promise (`summary`) is: *"Corporate finance, valuation and the
investments, debt, risk and international tools a finance student needs."*

## 2. Scope and non-goals — promises to test, not bugs

Source: `subjects.detail("finance")["does_not"]` (rank 5), `docs/CURRICULUM_MAP.md` *Named gaps*
(rank 6), `docs/KNOWN_LIMITATIONS.md` (rank 6), `docs/PRODUCT_GAP_MAP.md` (rank 6).

`does_not` — three declared non-goals, each an E-row (§8):

1. *"It does not retrieve market prices, yields, exchange rates or peer multiples; you declare them."*
2. *"It does not choose the discount rate, the peer set or the risk appetite for you."*
3. *"It does not model tax, American exercise, liquidity risk or a full portfolio optimisation."*

`CURRICULUM_MAP` named gaps for this shelf: *market data retrieval in the core, credit/liquidity risk,
multi-asset optimisation, real options.* These are GAP rows (G-fin-01…04), never expectations.

Out of scope by the work order: the parked queue (`docs/PARKED_QUEUE.md`), the REW stages, tax
jurisdiction rules, breadth templates, and any change to the frozen core contract
(`tests/test_frozen_contract.py`, decision B-079).

**The shelf has no worksheets.** `detail("finance")["worksheets"] == []` and
`definition["worksheets"] == []` (measured: `finance_surface.json`). The 23 catalogue records on the
shelf are *computed* or *read-only* records, never worksheet launchers. This is a design fact to
test (§4), not a missing feature to build: `docs/CURRICULUM_MAP.md` names no worksheet for Finance,
and the strategy/operations/marketing worksheets live on their own shelves.


## 3. Compute tools — one row per tool

Source of truth for every cell: `bp.methods.LIBRARY[id]` (`input_schema` name/type/required, `tier`,
`metric`, `unit`, `claim_ceiling`, `intended_use`, `unsupported_use`, `assumptions`, `limitations`,
`test_names`) — rank 1 — and `subjects.detail("finance")["tools"]` for `label`, `what`, `need`,
`formula`, `level`, `steps`, `common_mistakes`, `related`, `diagram`, `preset`, `group` — rank 5.
Measured in `qa/baseline/finance_contracts.json`.

All 35 tools are **T1** except six: `dcf`, `dcfmid`, `equitybridge`, `multiples` and `options` (T2
templates of the frozen core's own kind) and `case_decision` (a T2 template registered in
`bp.case_decision.TEMPLATES`). `case_decision` is the only tool whose id is not a frozen `LIBRARY`
method: it carries its own `validate`/`build`/`render`/`tests` (rank 1). Every other tool resolves to a
frozen method.

### 3.1 The tool contract table

| Tool | Method | Tier | Metric / unit | Claim ceiling | Required inputs | Preset |
|---|---|---|---|---|---|---|
| `tvm` | `time_value` | T1 | future_value / currency | descriptive | `present_value`, `rate`, `periods` | `tvm` |
| `loan` | `loan_amortization` | T1 | payment / currency | descriptive | `principal`, `annual_rate`, `years` | `loan` |
| `dupont` | `dupont_analysis` | T1 | return_on_equity / ratio | descriptive | `revenue`, `net_income`, `total_assets`, `equity` | `dupont` |
| `trendanalysis` | `trend_analysis` | T1 | revenue_cagr / rate | descriptive | `years`, `revenue`, `cost_of_sales`, `operating_expenses`, `net_income` | `trendanalysis` |
| `workingcapital` | `working_capital` | T1 | cash_conversion_cycle / days | descriptive | `revenue`, `cost_of_sales`, `inventory`, `receivables`, `payables`, `annual_demand`, `order_cost`, `holding_cost_per_unit`, `discount_percent`, `credit_terms_days`, `discount_days` | `workingcapital` |
| `ratios` | `ratio_analysis` | T1 | n_computed / count | descriptive | *(none: every field is optional)* | `ratios` |
| `breakeven` | `breakeven` | T1 | breakeven_units / units | descriptive | `fixed`, `price`, `variable` | `breakeven` |
| `multibreakeven` | `multi_product_breakeven` | T1 | breakeven_total_units / units | descriptive | `fixed_costs`, `products` | `multibreakeven` |
| `unitecon` | `unit_economics` | T1 | unit_margin / currency | descriptive | `price`, `variable_cost`, `acquisition_cost` | `unitecon` |
| `forecast` | `trend_forecast` | T1 | forecast_1 / from_request | predictive | `values` | `forecast` |
| `descriptive` | `descriptive_stats` | T1 | mean / from_request | descriptive | `values` | `descriptive` |
| `npv` | `npv` | T1 | npv / currency | descriptive | `rate`, `cashflows` | `npv` |
| `irr` | `irr` | T1 | irr / rate | descriptive | `cashflows` | `irr` |
| `dpayback` | `discounted_payback` | T1 | discounted_payback / periods | descriptive | `cashflows` | `dpayback` |
| `projectmetrics` | `project_metrics` | T1 | npv / currency | descriptive | `cashflows`, `rate` | `projectmetrics` |
| `wacc` | `wacc` | T1 | wacc / rate | descriptive | `equity_value`, `debt_value`, `cost_of_equity`, `cost_of_debt_after_tax` | `wacc` |
| `capm` | `capm` | T1 | cost_of_equity / rate | descriptive | `risk_free_rate`, `market_return` | `capm` |
| `leverage` | `leverage_analysis` | T1 | eps / currency | descriptive | `ebit`, `interest_expense`, `tax_rate`, `debt`, `equity`, `shares_outstanding` | `leverage` |
| `scenario` | `scenario_analysis` | T1 | npv_base / currency | descriptive | `cashflows`, `discount_rate`, `rate_low`, `rate_high` | `scenario` |

The remaining 16 tools (Valuation, Investments, Risk & derivatives, International) continue in §3.2.

### 3.2 The valuation, investment, risk and international tools

| Tool | Method | Tier | Metric / unit | Claim ceiling | Required inputs | Preset |
|---|---|---|---|---|---|---|
| `case_decision` | `case_decision` (template) | T2 | n/a (per-alternative NPV) | descriptive | `facts`, `alternatives`, `rate`, `rate_range` | `case_decision` |
| `dcf` | `dcf_valuation` | T2 | enterprise_value / currency | descriptive | `cashflows`, `discount_rate` | `dcf` |
| `dcfmid` | `dcf_valuation` (timing=mid) | T2 | enterprise_value / currency | descriptive | `cashflows`, `discount_rate` | `dcfmid` |
| `equitybridge` | `equity_bridge` | T2 | equity_value / currency | descriptive | `enterprise_value` | `equitybridge` |
| `multiples` | `multiples_valuation` | T2 | implied_equity_value / currency | descriptive | `metric`, `subject_value` | `multiples` |
| `portfolioval` | `portfolio_valuation` | T1 | nav / currency | descriptive | `holdings` | `portfolioval` |
| `portfolioperf` | `portfolio_performance` | T1 | twr / ratio | descriptive | `periods` | `portfolioperf` |
| `bond` | `bond_analysis` | T1 | price / currency | descriptive | `face_value`, `coupon_rate`, `years_to_maturity` | `bond` |
| `portfolio` | `portfolio_analysis` | T1 | portfolio_return / rate | descriptive | `returns_a`, `returns_b`, `weight_a`, `risk_free_rate`, `returns_market` | `portfolio` |
| `pearson` | `pearson` | T1 | r / correlation | associational | `x`, `y` | `pearson` |
| `ols` | `ols` | T1 | r_squared / ratio | associational | `y`, `predictors` | `ols` |
| `ols_robust` | `ols_robust` | T1 | r_squared / ratio | associational | `y`, `predictors` | *(none — G-fin-05)* |
| `risk` | `risk_metrics` | T1 | historical_var / rate | descriptive | `returns` | `risk` |
| `options` | `option_pricing` | T2 | option_price / currency | descriptive | `option_type`, `spot_price`, `strike_price`, `volatility`, `risk_free_rate`, `time_to_maturity` | `options` |
| `fx` | `fx_parity` | T1 | ppp_expected_spot / value | descriptive | `spot_rate`, `domestic_rate`, `foreign_rate`, `domestic_inflation`, `foreign_inflation`, `time_to_maturity` | `fx` |
| `currency` | `currency_convert` | T1 | amount / currency | descriptive | `amount`, `from_currency`, `to_currency`, `rate` | `currency` |

### 3.3 Refusals and unit rules the shelf promises

Each line is an E-row (§8) and is enforced by a test in
`tests/test_subject_finance_acceptance.py`. Sources: `LIBRARY[id].unsupported_use` and the method's
`profile()`/`impl()` refusals (rank 1) — all quoted from
`qa/baseline/finance_contracts_rows.txt`.

| Rule | Tool(s) | Source |
|---|---|---|
| An unknown input name is refused with the allowed list; `weights`, `weight`, `strata`, `cluster`, `clusters`, `repeated`, `id`, `time`, `pair`, `pairs` are refused by name as unsupported survey structure | every frozen method | `methods._UNSUPPORTED_CONCEPTS` + `validate_inputs` |
| A rate entered as `6` for 6% is explained ("6% is 0.06"), never quietly read as 600% | `tvm`, and every rate input | `tests/test_finance_additions.py::test_a_percent_typed_as_a_whole_number_is_flagged` |
| An IRR with no sign change (or more than one) is refused with an actionable reason, never `NaN` | `irr` | `LIBRARY["irr"].unsupported_use`, self-test `unconventional_or_signless_cash_flows_are_refused` |
| Discounted payback of an outlay the flows never recover is refused | `dpayback` | self-test `unrecovered_outlays_are_refused` |
| Break-even with a contribution margin ≤ 0 is refused | `breakeven` | `breakeven_tests` |
| Terminal growth ≥ discount rate is refused | `dcf`, `dcfmid` | `dcf_impl` `DataError` |
| A terminal value is only reported when `terminal_growth` is declared | `dcf` | self-test `without_terminal_growth_there_is_no_terminal_value` |
| `timing` accepts only `end` or `mid`; anything else is refused | `dcf`, `dcfmid` | `_dcf_timing` `DataError` |
| Option inputs must satisfy Black-Scholes' domain (positive spot/strike/volatility, `T > 0`); put-call parity is reported, not assumed | `options` | `option_pricing` self-tests |
| The currency rate is the student's declared figure; provenance is recorded and no rate is retrieved | `currency`, `fx` | `does_not` #1, `_convert_lines` |
| A break-even, NPV or IRR is never given a recommendation: the claim ceiling is `descriptive` | all | `LIBRARY[*].claim_ceiling` |

Optional inputs are exactly the schema's non-required entries and are listed in
`qa/baseline/finance_contracts_rows.txt`; a tool with no optional entry is complete as listed.


## 4. Worksheets and framework profiles

**There are none, and the shelf says so.** Measured: `detail("finance")["worksheets"] == []`,
`definition["worksheets"] == []` (`qa/baseline/finance_surface.json`). `framework_profiles.PROFILES`
carries 75 profiles, none of them on this shelf, and `subjects.SUBJECT_WORKSHEET_GROUPS` has no
`finance` key.

Consequences the suite must prove (E-fin-030…032):

- no finance tool is a worksheet launcher (`tool["kind"]` is never `"worksheet"`);
- no finance catalogue record declares a `template` or a `worksheet` id;
- `detail("finance")["tiles"] == []` — the tile surface exists only for the shelves named in
  `subjects.SUBJECT_TILES` (`people`, `economics`, `management`). This is a recorded design fact
  (`_tiles()` returns `[]` when a shelf declares no tiles), not a defect: the finance page renders
  its 35 tools grouped by `tool["group"]` instead. E-fin-032 pins it so a future tile change is
  noticed.

## 5. Records, theories and glossary

Source: `subjects.detail("finance")["records"]` / `["theories"]` / `["glossary"]` (rank 5), reconciled
against `subjects.WORKSHEETS` and `methods.LIBRARY` (rank 1) and `tests/test_catalogue_truth.py`
(rank 7).

`detail("finance")["theories"] == []` — the shelf declares no reading lenses (measured).

### 5.1 The 23 catalogue records

| Id | Name | Form | Declared status (verbatim, abridged) |
|---|---|---|---|
| QNT-FIN-01 | Capital budgeting | computed | partial: NPV, IRR, discounted payback, PI, MIRR, simple payback, EAA implemented; unequal-life ranking and real options not |
| QNT-FIN-02 | Cost and profitability | computed | partial: single/multi break-even, ABC, sales variances; operating leverage, relevant cost, make-or-buy not |
| QNT-FIN-03 | Financial performance | computed | partial: 15 ratios, DuPont (3- and 5-step), common-size, growth, multi-year trend, CCC; benchmarks and restatements not |
| QNT-FIN-04 | Valuation and financing | computed | partial: WACC, CAPM, DCF, equity bridge, multiples, bond price/duration; debt capacity and real options not |
| QNT-FIN-05 | Management accounting | computed | partial: double-entry engagement, standard-cost variances, ABC; target/life-cycle/budget-variance not |
| QNT-FIN-06 | Unit economics | computed | partial: contribution margin, acquisition payback, LTV/CAC; retention curves and cohort economics not |
| QNT-FIN-07 | Pricing and demand | computed | partial: cost-plus, target-margin, break-even, target-return prices, arc elasticity; demand curve and willingness-to-pay not |
| QNT-DEC-01 | Decision trees, expected value and utility | read_only | not implemented |
| QNT-DEC-02 | Sensitivity, scenario, break-even thresholds, decision flip | computed | partial: decision-flip on the NPV rate and a declared low/high rate scenario; multi-input scenarios, Monte Carlo, decision trees not |
| QNT-DEC-03 | Multi-criteria decision analysis (weighted sum, AHP, TOPSIS) | read_only | not implemented |
| QNT-DEC-04 | Monte Carlo simulation | read_only | not implemented |
| QNT-DEC-05 | Expected loss, risk exposure, stress testing | read_only | not implemented |
| QNT-DEC-06 | Fault-tree probability | read_only | not implemented |
| QNT-DEC-07 | FMEA prioritization scores | read_only | not implemented |
| RSK-01 | ISO 31000 Risk Management Process | read_only | read-only record: no worksheet yet |
| RSK-02 | COSO Enterprise Risk Management | read_only | read-only record: no worksheet yet |
| RSK-03 | Bow-Tie Analysis | read_only | read-only record: no worksheet yet |
| RSK-04 | Fault Tree Analysis | read_only | not implemented |
| RSK-05 | Stakeholder Analysis / Power–Interest Matrix | read_only | read-only record: no worksheet yet |
| RSK-06 | Materiality Assessment | read_only | read-only record: no worksheet yet |
| RSK-07 | Red-Team / Premortem Review | read_only | read-only record: no worksheet yet |
| RSK-08 | Dialectical Inquiry / Devil's Advocate | read_only | read-only record: no worksheet yet |
| RSK-09 | Multi-Criteria Decision Analysis (MCDA) | read_only | read-only record: no worksheet yet |

Rules the suite enforces (E-fin-026…029): a `computed` record's declared methods exist in
`LIBRARY`; a `read_only` record never declares a linked method or a worksheet; no record declares a
worksheet (there are none on this shelf); `form_short` never contradicts `implementation_status`
(`FORM_SHORT` maps `read_only` → "No worksheet yet", so RSK-04's "not implemented" is shown as
"No worksheet yet" — a wording gap ledgered as G-fin-06).

### 5.2 The 22 glossary terms

`NPV, IRR, WACC, CAPM, Beta, YTM, Duration, Convexity, EOQ, CCC, VaR, CVaR, Delta, Hedge,
Enterprise value, Net debt, EBIT / EBITDA, EPS, ROE, Common-size, CAGR, Altman Z` — each with a
non-empty `definition` (measured). E-fin-033 asserts the set, the count and that every definition is
non-empty and unique.

## 6. Student guidance

Source: `subjects.detail("finance")` `guidance`, `start_steps`, `does_not` (rank 5) and
`docs/FINANCE_STUDENT_GUIDE.md` (rank 6). Measured verbatim in
`qa/baseline/finance_surface.json`.

**Guidance** (one paragraph, shelf-level): *"Start with the question, not the tool. For one cash flow
or one instrument, use time value, a loan or a bond. For a project, use NPV, IRR and discounted
payback, then rank it. For a company, use WACC and DCF, then bridge to equity. For an investment or a
risk question, use CAPM, the portfolio, risk and options tools. For an international question, use the
parity and currency tools. Every rate, price and cash flow is yours to declare."*

**Start steps** (5, all present, each naming real tools):

1. One cash flow or instrument: `tvm`, `loan`, `bond`.
2. A project: `npv`, `irr`, `dpayback`, then `projectmetrics` and `scenario`.
3. A company: `wacc`, `dcf`, `equitybridge`, `multiples`.
4. An investment or risk question: `capm`, `portfolio`, `risk`, `options`.
5. An international question: `fx`, then `currency`.

**Does-not list** (3): market-data retrieval; choosing the discount rate/peer set/risk appetite;
tax, American exercise, liquidity risk, full portfolio optimisation.

**Per-tool teaching notes** — every one of the 35 tools carries `level`, `formula`, ≥3 `steps`, ≥2
`common_mistakes`, and `related` ids (measured: `finance_contracts_rows.txt`; the minimum observed is
3 steps / 3 mistakes). Levels: 17 intro, 12 intermediate, 3 advanced (+ `case_decision`,
`projectmetrics`, `dcf`, `dcfmid`, `equitybridge`, `multiples` at intermediate; `ols`, `ols_robust`,
`options` at advanced). E-fin-003 and E-fin-004 assert these, that every `related` id resolves to a
tool on a declared shelf, and E-fin-037 asserts that `need` is either present or the fallback is the
named gap (§10 G-fin-07).

## 7. Surface routing

Source: `web/index.html` (rank 5, one 752 KB page, one inline script), `bp/server.py` (rank 1
routes), `bp/product/api.py` (rank 1 `/api/cases/*`), `bp/product/subjects.py` (rank 5),
`bp/product/calc_router.py` (rank 5).

| Surface | Route / entry point | What it must do |
|---|---|---|
| Shelf page | `GET /api/cases/subjects/finance` | returns the 35 tools, 23 records, 22 glossary terms, 0 worksheets, 0 tiles, the guidance and the does-not list |
| Shelf index | `GET /api/cases/subjects` | `finance` is one of the 11 shelves with the label `Finance` |
| Tool form | the page's schema-driven form | built from `LIBRARY[method].input_schema`; `enum` fields render as choices (`compounding`, `timing`, `option_type`), list fields as comma lists (`cashflows`, `values`, `returns`) |
| Session | `POST /api/sessions` → `awaiting_confirmation` | nothing is computed before the plan is confirmed |
| Confirm | `POST /api/sessions/{id}/confirm` → `delivered` | the report names the method's `test_names` and carries the honesty block |
| Portfolio lab | `GET /api/portfolios/*` (design lane) | separate surface; not a finance tool route, ledgered as design-lane |
| Downloads | `md`, `xlsx`, `docx`, `pdf` | the computed numbers unchanged, no template text |
| Calculator router | `calc_router` word → method | the same method is reached from the calculator as from the tile |
| Preset launch | `GET /api/presets` | 34 of the 35 finance tools have a preset whose `method` matches |

The finance page carries no worksheet links, no draft buttons and no reviewer surface; the pricing
dialog and wallet are shared page furniture, not finance features (E-fin-038…041).

## 8. Expected-behaviour table `E-fin-nnn`

Atomic, testable, one line each. `PASS`/`FAIL`/`BLOCKED`/`GAP` is decided in §9 from the test run.

### 8.1 Catalogue and contract

| Id | Behaviour | Source |
|---|---|---|
| E-fin-001 | `detail("finance")` returns exactly 35 tools, 0 worksheets, 23 records, 22 glossary terms and 0 theories; a change in any count fails the suite | rank 5 `subjects.detail` (measured `finance_surface.json`) |
| E-fin-002 | Every tool's `method` is a frozen `LIBRARY` method **or** a registered `templates.TEMPLATES` entry; `case_decision` is the only template | rank 1 `LIBRARY` + `TEMPLATES` |
| E-fin-003 | Every tool carries a non-empty `formula`, `label`, `what` and a `level` in {intro, intermediate, advanced}; its method declares a tier in T1–T4, and exactly six tools are T2 (`case_decision`, `dcf`, `dcfmid`, `equitybridge`, `multiples`, `options`) | rank 5 + rank 1 `tier` |
| E-fin-004 | Every tool carries ≥3 `steps`, ≥2 `common_mistakes`, and every `related` id resolves to a declared tool id | rank 5 |
| E-fin-005 | Every tool has a preset whose `method` equals the tool's method — with `ols_robust` the single named exception (G-fin-05) | rank 1 `server.PRESETS` |
| E-fin-006 | Every finance preset's default inputs pass `validate_inputs` **and** the method's `profile()` with no issue | rank 1 |
| E-fin-007 | Every frozen method's declared self-tests pass on its own preset's defaults, including `dcf_valuation` at `timing="mid"` (D-FIN-01, fixed by **B-183**) | rank 1 `Method.tests`; B-183 |
| E-fin-008 | No finance method claims a `prescriptive` ceiling; every ceiling is `descriptive` except `pearson`, `ols`, `ols_robust` (`associational`) | rank 1 `claim_ceiling` |
| E-fin-009 | An unknown input name is refused with the allowed list; the refusal is a `blocked` delivery, never a silent drop | rank 1 `validate_inputs` |
| E-fin-010 | `weights`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)` are refused by name as unsupported survey structure | rank 1 `_UNSUPPORTED_CONCEPTS` |
| E-fin-011 | A rate typed as `6` for 6% is explained ("6% is 0.06") and never read as 600% | rank 7 `test_finance_additions` |
| E-fin-012 | An IRR with no sign change, or more than one, is refused with an actionable reason — never `NaN`, never a delivered figure | rank 1 `unsupported_use` + self-test |
| E-fin-013 | A discounted payback on an outlay the flows never recover is refused | rank 1 self-test |
| E-fin-014 | A break-even whose contribution margin is ≤ 0 is refused | rank 1 `breakeven_tests` |
| E-fin-015 | A DCF with `terminal_growth ≥ discount_rate`, or a `timing` outside {`end`,`mid`}, is refused with the reason named | rank 1 `dcf_impl` |

### 8.2 Independent recomputation

Each row compares the frozen method with a route that is **not** the method: hand arithmetic, a
second formula, or the hash-pinned fixture in `tests/fixtures/`.

| Id | Behaviour | Independent route |
|---|---|---|
| E-fin-016 | `npv` equals a hand-summed `Σ CF_t/(1+r)^t`, to 1e-9 on the preset default | hand sum, `qa/baseline/finance_contracts_rows.txt` |
| E-fin-017 | `dcf_valuation` mid-year EV equals the hand-computed mid-year value (1,836,400.47 on the `dcfmid` preset) and exceeds the end-year value by 1.048808848…, the ratio hand-computed for those flows | hand loop, `qa/probe_dcf_midyear.py` |
| E-fin-018 | `equity_bridge`: equity = EV − net debt − minority − preferred, per share = equity / shares, both hand-computed | hand arithmetic |
| E-fin-019 | `wacc` equals `E/(D+E)·ke + D/(D+E)·kd(1−t)` computed by hand | hand arithmetic |
| E-fin-020 | `capm` cost of equity equals `rf + β(rm − rf)` computed by hand | hand arithmetic |
| E-fin-021 | `breakeven` quantity equals `fixed / (price − variable)` and revenue equals quantity × price | hand arithmetic |
| E-fin-022 | `loan_amortization` payment equals `P·r/(1−(1+r)^−n)` with `r` the annual rate over payments per year | hand arithmetic |
| E-fin-023 | `ratio_analysis` matches `tests/fixtures/ratio_golden.json` | hash-pinned fixture |
| E-fin-024 | `descriptive_stats`, `trend_forecast`, `pearson` and `ols` match their golden fixtures (`descriptive_golden.json`, `forecast_golden.json`, `correlation_golden.json`, `regression_golden.json`) | hash-pinned fixtures |
| E-fin-025 | `bond_analysis` price equals the hand-summed coupon/face discounts and Macaulay duration equals the PV-weighted time, both hand-computed | hand arithmetic |

### 8.3 Records

| Id | Behaviour | Source |
|---|---|---|
| E-fin-026 | Every `computed` record's implemented topics name methods that exist in `LIBRARY`; no computed record names a method the engine lacks | rank 5 + rank 1 + rank 7 `test_catalogue_truth` |
| E-fin-027 | No `read_only` record declares a linked method or a worksheet — a read-only record is something to read and cite | rank 5 `subjects._record_form` |
| E-fin-028 | No finance record declares a `template` or a `worksheet`: the shelf has none, and a record that claimed one would be a dead button | rank 5 |
| E-fin-029 | A record whose status begins "not implemented" is delivered as `read_only`, never as `computed` | rank 5 `_record_form` |

### 8.4 Worksheets, tiles and glossary

| Id | Behaviour | Source |
|---|---|---|
| E-fin-030 | `detail("finance")["worksheets"]` is empty and no tool has `kind == "worksheet"` | rank 5 |
| E-fin-031 | `SUBJECT_WORKSHEET_GROUPS` has no `finance` key and `framework_profiles.PROFILES` carries no finance profile | rank 4/5 |
| E-fin-032 | `detail("finance")["tiles"]` is empty because `subjects.SUBJECT_TILES` names only `people`, `economics`, `management` | rank 5 `_tiles()` |
| E-fin-033 | The 22 glossary terms are exactly the declared set, each with a non-empty, unique definition | rank 5 |

### 8.5 Student guidance

| Id | Behaviour | Source |
|---|---|---|
| E-fin-034 | `start_steps` has ≥3 entries and every tool id it names exists on the shelf | rank 5 |
| E-fin-035 | `does_not` has ≥2 entries and the three declared non-goals are present | rank 5 |
| E-fin-036 | `guidance` is non-empty, names the shelf's tool families, and never promises a market-data retrieval | rank 5 |
| E-fin-037 | Every tool's `need` text is present, or the fallback is the recorded gap G-fin-07 (25 of 35 tools) | rank 5 `TOOL_NEEDS` |

### 8.6 Surface and routing

| Id | Behaviour | Source |
|---|---|---|
| E-fin-038 | The shelf index lists `finance` with label `Finance`, and the detail route returns the same 35 tools as the catalogue | rank 1 routes |
| E-fin-039 | The served page builds the tool form from `input_schema`: `enum` fields get choices, list fields get comma lists | rank 5 `web/index.html` + rank 7 `test_product_subjects` |
| E-fin-040 | The calculator router reaches the same frozen method for the finance vocabulary the shelf declares (e.g. "net present value" → `npv`, "wacc" → `wacc`, "break even" → `breakeven`) | rank 5 `calc_router` |
| E-fin-041 | The finance page carries no worksheet link, no draft button and no reviewer surface | rank 5 page contract |

### 8.7 Product path, honesty and deliverables

| Id | Behaviour | Source |
|---|---|---|
| E-fin-042 | `POST /api/sessions {objective, method, inputs}` answers `awaiting_confirmation` and computes nothing; `POST /api/sessions/{id}/confirm {}` answers `delivered` | rank 3 `CONDUCTOR_MANUAL` §8 |
| E-fin-043 | A delivered finance computation carries its honesty block, and the plan names the method's `test_names` | rank 3 §8 + rank 7 `test_honesty` |
| E-fin-044 | The same inputs twice give a byte-identical result and hash; no clock, locale or dict-order dependence | rank 3 §7.5 |
| E-fin-045 | The in-process result equals the subprocess sandbox result for the same method and inputs | rank 7 `test_accounting_sandbox_parity` pattern |
| E-fin-046 | Every delivered finance result states what was **not** tested; a non-applicable field says so and is never blank | rank 7 `test_honesty` |
| E-fin-047 | No finance capability paper prints a raw core Decimal: money is 2 dp, a ratio 2 dp, a count integral | D-FIN-02 (measured `qa/baseline/fin_papers.txt`) |
| E-fin-048 | Every finance capability has a bespoke formatter, or its fallback is the recorded gap G-fin-08 | rank 5 `chat.CAPABILITY_LINES` |
| E-fin-049 | The markdown, xlsx and docx deliverables carry the computed numbers unchanged, open cleanly and contain no `{{ref:` token | rank 3 §8 |
| E-fin-050 | A refused computation is delivered as a refusal with the core's own reason — never as a zero, a blank or a fabricated figure | rank 3 §8 + `HANDOFF` non-negotiable 4 |

## 9. Traceability matrix

Filled from the executed suite. Each E-id is enforced by the test method of the same number in
`tests/test_subject_finance_acceptance.py` (`test_<nnn>__<behaviour>`), unless another file is named.
The closing status of every row is in `qa/QA_STATE.md` §4; the run that produced it is
`qa/baseline/fin_acceptance.txt`.

| E-ids | Enforcing test family | Status |
|---|---|---|
| E-fin-001…008 | `test_00n__…` — catalogue, contract, preset and self-test rows, one test each | PASS except E-fin-005 (GAP G-fin-05) |
| E-fin-009…015 | `test_00n__…` — refusal rows, one test each, through `Pipeline().start` so the product route is what refuses | PASS |
| E-fin-016…025 | `test_0nn__…` — independent recomputation, hand arithmetic or the hash-pinned fixture | PASS |
| E-fin-026…029 | `test_02n__…` — record truth against `LIBRARY` and `WORKSHEETS` | PASS |
| E-fin-030…033 | `test_03n__…` — worksheets, tiles and glossary | PASS |
| E-fin-034…037 | `test_03n__…` — guidance, start steps, does-not list, `need` fallback | PASS except E-fin-037 (GAP G-fin-07) |
| E-fin-038…041 | `test_04n__…` — routes, form kinds, calculator router, page surface | PASS |
| E-fin-042…046 | `test_04n__…` — session lifecycle, honesty, determinism, sandbox parity | PASS |
| E-fin-047…048 | `test_04n__…` — capability paper formatting | PASS after D-FIN-02 |
| E-fin-049…050 | `test_04n__…` — deliverables and refusal-not-zero | PASS |

## 10. Known gaps

Named, with the document or decision that declares each. None is converted into an expectation, and
none is built by this session.

| Id | Gap | Declared by | Ledger |
|---|---|---|---|
| G-fin-01 | No market-data retrieval: prices, yields, exchange rates and peer multiples are the student's | `does_not` #1; `CURRICULUM_MAP` named gaps | D-FIN-07 |
| G-fin-02 | Credit and liquidity risk are not modelled | `CURRICULUM_MAP` named gaps; `does_not` #3 | D-FIN-07 |
| G-fin-03 | No multi-asset portfolio optimisation | `CURRICULUM_MAP` named gaps; `does_not` #3 | D-FIN-07 |
| G-fin-04 | No real-option valuation (also named on record QNT-FIN-04) | `CURRICULUM_MAP` named gaps | D-FIN-07 |
| G-fin-05 | `ols_robust` has no preset, so it has no one-click worked example; the schema form still runs it | `server.PRESETS` is part of the frozen 144 and none launches `ols_robust` | D-FIN-08 |
| G-fin-06 | RSK-04's "not implemented" is shown as "No worksheet yet", because `FORM_SHORT["read_only"]` is a single label | `subjects.FORM_SHORT` | D-FIN-09 |
| G-fin-07 | 25 of the 35 tools declare no `need` ("what to gather") text; `TOOL_NEEDS` has no finance key | `subjects.TOOL_NEEDS`; same class as accounting's G-acc-01 | D-FIN-10 |
| G-fin-08 | The generic fallback still quotes the core's output verbatim for any capability without a bespoke formatter; the three finance ones were given formatters by D-FIN-02 | `chat._generic_lines` | D-FIN-03 |
| G-fin-09 | `CURRICULUM_MAP` says "33 tools … plus `trend_analysis`"; the shelf has 35 | `docs/CURRICULUM_MAP.md` (stale count) | D-FIN-11 |





