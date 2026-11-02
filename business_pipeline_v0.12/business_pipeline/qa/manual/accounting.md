# Acceptance manual — Accounting shelf

**Subject:** `accounting`  **Session:** QA session 1 of 11  **Baseline commit:** `97544f7`
**Build:** 1.56 (`docs/CHANGELOG.md`)  **Written:** 2026-11-02
**Enforced by:** `tests/test_subject_accounting_acceptance.py` (this session's suite)
**Status vocabulary:** PASS / FAIL / BLOCKED / GAP / DISPUTED (see §9).

This is the manual the repo did not have. Every row cites a source of truth. Nothing here
is an opinion: where a row rests on the code, the code path is named; where it rests on a
document, the document and section are named. Where the code and a document disagree the
row is marked **DISPUTED** and both readings are recorded.

Sources, in descending authority (per the session work order §5):

| Rank | Source | Used for |
|---|---|---|
| 1 | `src/bp/methods.py` `LIBRARY[id]` contract + `bp.methods.validate_inputs` | inputs, units, tolerances, claim ceiling, checks |
| 2 | `docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md` (records `QNT-FIN-02/03/05`) | what each method is supposed to do |
| 3 | `docs/CONDUCTOR_MANUAL.md` §4/§8, `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20) | paper and export rules |
| 4 | `bp.product.framework_profiles.PROFILES` | not applicable: the shelf declares no worksheets |
| 5 | `bp.product.subjects.SUBJECT_DEFS`/`detail()` (tools, notes, records, glossary, guidance) | the student-facing promise |
| 6 | `docs/ACCOUNTING_STUDENT_GUIDE.md` | teaching intent and worked examples |
| 7 | the existing accounting tests (see §9 traceability) | executable intent already in the tree |

**Live-catalogue baseline for this shelf** (`GET /api/cases/subjects/accounting`, captured
in `qa/baseline/accounting_catalogue.json`):

| Unit | Count | Source |
|---|---:|---|
| Compute tools | 12 | `subjects.detail("accounting")["tools"]` |
| Worksheets | 0 (declared empty) | `SUBJECT_DEFS[0]["worksheets"] == []` |
| Catalogue records | 3 | `catalogue_ids` = `QNT-FIN-02`, `QNT-FIN-03`, `QNT-FIN-05` |
| Theories | 0 | `detail()["theories"]` |
| Glossary terms | 19 | `detail()["glossary"]` |
| Tiles | 0 — the page groups the tools instead | `detail()["tiles"] == []`; `ACCOUNTING_GROUPS` |
| Starting steps | 4 | `start_steps` |
| "Does not" statements | 3 | `does_not` |

The workload table in the session work order says 12 tools / 0 worksheets / 3 records / 0
theories. **The live catalogue matches exactly**; there is no count defect.

---

## 1. Who it serves

`docs/ACCOUNTING_STUDENT_GUIDE.md` (opening paragraph) and `docs/CURRICULUM_MAP.md`:

- **Senior high school ABM** students, and **first- and second-year undergraduate** accounting
  students.
- Assignments it must survive: record transactions and prepare the statements; check a trial
  balance against a journal; compute liquidity/profitability/solvency/efficiency ratios;
  explain material, labour and overhead variances; cost a product by activity; explain a
  revenue movement by price, mix and yield; compute a declared-rate tax charge; break even on
  one product or a mix; measure the cash conversion cycle and order quantity; amortise a loan;
  read several years of figures as common-size and trend.
- Currency convention: figures are the student's; the presets are declared in PHP or USD and
  the method never converts (`currency` is carried, never inferred).

The assignment → tool mapping is stated in the guide and is tested by E-acc-005/E-acc-011.

## 2. Scope and non-goals

These are promises to test, not bugs. Sources: `SUBJECT_DEFS["accounting"]["does_not"]`,
`docs/ACCOUNTING_STUDENT_GUIDE.md` §"What is not built", `docs/KNOWN_LIMITATIONS.md`,
`docs/PRODUCT_GAP_MAP.md`, and each method's `unsupported_use`.

| # | The shelf declares it does **not** do | Source |
|---|---|---|
| N-1 | File a tax return or apply a jurisdiction's tax law; tax is a declared-rate calculation | `does_not[0]`; `LIBRARY["tax_declared"].unsupported_use`; guide §6 |
| N-2 | Choose the accounting policy, audit the figures or certify the statements | `does_not[1]`; `LIBRARY["management_accounts"].unsupported_use` |
| N-3 | Invent a missing balance or plug an unbalanced trial balance | `does_not[2]`; `LIBRARY["trial_balance_check"].unsupported_use` |
| N-4 | Produce GAAP/IFRS statements, assurance, filings, multi-currency consolidation | `LIBRARY["management_accounts"].unsupported_use` |
| N-5 | Benchmark a ratio against an industry | `LIBRARY["ratio_analysis"].unsupported_use`; guide §3 |
| N-6 | Set standards, or judge whether a standard is attainable | `LIBRARY["standard_cost_variances"].limitations`; guide §2 |
| N-7 | Audit sampling/opinion, group consolidation, target or life-cycle costing, budget/planning/idle-capacity variances | guide §"What is not built"; `QNT-FIN-02/05` `implementation_status` |
| N-8 | Read a PDF, a scan or an image; only CSV/TSV/XLSX is ingested | guide §"What is not built" |
| N-9 | Fit a statement to the student's own chart of accounts: the chart is the student's mapping | `LIBRARY["management_accounts"].assumptions` |

The shelf carries **no worksheet** (`worksheets: []`). That is a declared shape, not a missing
build: `docs/CURRICULUM_MAP.md` lists accounting as compute-only, and `subjects.detail()`
returns `worksheets: []` and `tiles: []` with every tool grouped instead (`ACCOUNTING_GROUPS`).
Row E-acc-012 tests it.

---

## 3. Compute tools

Twelve tools, each a launcher for one frozen method. The launcher is `subjects.TOOL_INFO[key]`;
the preset is `bp.server.PRESETS[preset]`; the arithmetic is `bp.methods.LIBRARY[method]`.
The product formats the core's numbers and never recomputes them.

| # | Tool key | Preset | Method id | Tier | Metric | Unit | Ceiling | Group | Period | Level |
|---|---|---|---|---|---|---:|---|---|---|---|
| 1 | `accounts` | `accounts` | `management_accounts` | T2 | `net_income` | currency | descriptive | Bookkeeping and statements | annual | intermediate |
| 2 | `tbcheck` | `tbcheck` | `trial_balance_check` | T2 | `n_differing` | count | descriptive | Bookkeeping and statements | annual | intro |
| 3 | `ratios` | `ratios` | `ratio_analysis` | T1 | `n_computed` | count | descriptive | Bookkeeping and statements | annual | intro |
| 4 | `scv` | `scv` | `standard_cost_variances` | T1 | `total_variance` | currency | descriptive | Cost and variance analysis | annual | intermediate |
| 5 | `abc` | `abc` | `abc_costing` | T1 | `total_allocated` | currency | descriptive | Cost and variance analysis | annual | intermediate |
| 6 | `salesvar` | `salesvar` | `sales_variances` | T1 | `total_sales_variance` | currency | descriptive | Cost and variance analysis | annual | intermediate |
| 7 | `breakeven` | `breakeven` | `breakeven` | T1 | `breakeven_units` | units | descriptive | Cost and variance analysis | per period | intro |
| 8 | `multibreakeven` | `multibreakeven` | `multi_product_breakeven` | T1 | `breakeven_total_units` | units | descriptive | Cost and variance analysis | per period | intro |
| 9 | `workingcapital` | `workingcapital` | `working_capital` | T1 | `cash_conversion_cycle` | days | descriptive | Working capital and financing | annual | intro |
| 10 | `loan` | `loan` | `loan_amortization` | T1 | `payment` | currency | descriptive | Working capital and financing | annual | intro |
| 11 | `trendanalysis` | `trendanalysis` | `trend_analysis` | T1 | `revenue_cagr` | rate | descriptive | Working capital and financing | annual | intro |
| 12 | `tax` | `tax` | `tax_declared` | T1 | `total_tax_charge` | currency | descriptive | Tax and reporting | annual | intro |

All twelve are **descriptive**: no accounting tool claims association, prediction or causation.
That ceiling is asserted by E-acc-003 and E-acc-010.

### 3.1 Inputs, outputs and refusals, one tool at a time

Legend: **R** = required, **O** = optional. Every numeric input is a **string decimal**
(`methods._num` refuses a binary float outright); a **rate** is a decimal (`0.25`), which the
product states as a percentage.

#### 3.1.1 `accounts` → `management_accounts` (T2)

- **Claims** (`intended_use`): run a declarative engagement (chart, opening balances, entries,
  schedules) through the ledger kernel — statements, trial balance, two-route cash flow, closing,
  retained-earnings rollforward — with every invariant checked.
- **Inputs**: `spec` (R, `engagement_spec`): `period{start,end}`, `currency`, `framework`,
  `places`, `chart[]`, `prior_closing{}`, `opening[]`, `entries[]`, `schedules[]`,
  `policy_changes[]`.
- **Outputs**: `net_income`, and the appendix: `statements`, `trial_balance`, `cash_flow` (two
  routes), `closing`, `retained_earnings`, `changes_in_equity`, `checks`.
- **Checks** (11 frozen `test_names`): `trial_balance_debits_equal_credits`,
  `assets_equal_liabilities_plus_equity`, `net_income_agrees_across_routes`,
  `opening_balances_equal_prior_closing`, `statement_lines_foot_to_totals`,
  `journal_hash_chain_intact`, `cash_flow_agrees_across_routes`, `retained_earnings_rollforward`,
  `income_expense_and_dividends_zero_after_closing`, `statement_internally_consistent`,
  `opening_balances_agree`.
- **Refusals**: an unbalanced entry, an out-of-period date, an unknown account, a wrong currency
  place, an opening balance that disagrees with `prior_closing` (the `accounts` kernel;
  `tests/test_accounting_pipeline_integration.py`).
- **Assumptions**: every entry balanced and inside the period; the chart is the owner's mapping;
  amounts respect the declared currency places.

#### 3.1.2 `tbcheck` → `trial_balance_check` (T2)

- **Claims**: compare the student's trial balance with the one their own journal rebuilds —
  every line matched, differing or missing, with candidate causes labelled as heuristics.
- **Inputs**: `journal` (O, engagement shape), `trial_balance` (O, `rows`, ≥1 row of code/name +
  debit/credit), `places` (O, default 2).
- **Outputs**: `counts` (`n_matched`, `n_differing`, `n_missing_submitted`,
  `n_missing_rebuilt`), `amounts.total_absolute_difference`, `rows[]` with `status` (`matched` /
  `amount-differs` / `only-in-journal` / `only-in-trial-balance` / `unchecked`), `findings[]`,
  `verdict`.
- **Refusals**: neither input supplied; the same account listed twice; a negative figure; more
  decimal places than `places`; a row with neither code nor name (`bp.check.CheckError`).
- **Never claims**: which of the two figures is right. An exact agreement is still reported with
  "does not prove your entries are right" (`tests/test_trial_balance_check.py`).

#### 3.1.3 `ratios` → `ratio_analysis` (T1)

- **Claims**: 15 declared liquidity, profitability, solvency and efficiency ratios from the
  supplied statement figures; a ratio whose inputs are missing or whose denominator is zero is
  **not computed** and the reason is given.
- **Inputs** (all optional decimals): `current_assets`, `current_liabilities`, `cash`,
  `inventory`, `receivables`, `payables`, `total_assets`, `total_liabilities`, `equity`,
  `revenue`, `cost_of_sales`, `operating_profit`, `net_income`, `interest_expense`.
- **Outputs**: the ratio values, `n_computed`, and an appendix (`ratios[]` with definition, unit,
  status, `negative_base`; `not_computed[]` with reason; `figures_supplied`).
- **Refusals / limits**: nothing computable at all (the profile blocks); a zero denominator
  removes the ratio with a reason; a negative base is computed and flagged, never dropped.
- **Never claims**: a benchmark or an industry comparison (`unsupported_use`).

#### 3.1.4 `scv` → `standard_cost_variances` (T1)

- **Claims**: material price and usage, labour rate and efficiency variances for the output
  achieved, plus (when declared) variable- and fixed-overhead variances; positive =
  **unfavourable**.
- **Inputs**: R `actual_units`, `standard_material_per_unit`, `standard_material_price`,
  `actual_material_quantity`, `actual_material_price`, `standard_hours_per_unit`,
  `standard_labour_rate`, `actual_hours`, `actual_labour_rate`; O
  `standard_variable_overhead_rate` + `actual_variable_overhead` (a pair),
  `budgeted_fixed_overhead` + `actual_fixed_overhead` + `denominator_hours` (a triple).
- **Outputs**: `material_price_variance`, `material_usage_variance`, `labour_rate_variance`,
  `labour_efficiency_variance`, `material_variance`, `labour_variance`,
  `variable_overhead_spending_variance`, `variable_overhead_efficiency_variance`,
  `fixed_overhead_spending_variance`, `fixed_overhead_volume_variance`,
  `standard_fixed_overhead_rate`, `total_variance`.
- **Refusals**: `actual_units <= 0`; any negative input; a variable-overhead rate without the
  actual overhead; fixed overhead without `denominator_hours > 0`.
- **Never claims**: mix, yield, sales or planning variances; whether a standard is attainable.

#### 3.1.5 `abc` → `abc_costing` (T1)

- **Claims**: an activity rate per pool, each product's allocation from the drivers it consumes,
  and its unit cost.
- **Inputs**: R `activities` (records: name + pool cost), R `products` (records: name + units),
  R `allocations` (records: activity, product, `driver_quantity`).
- **Outputs**: `total_allocated` (equal to the sum of the pools), per-activity rate, per-product
  allocation and unit cost, `n_activities`, `n_products`.
- **Refusals**: an activity whose driver total is zero; a driver quantity for an unknown activity
  or product; a pool with a cost and no driver (the guide's "common mistake"); negative costs or
  quantities.

#### 3.1.6 `salesvar` → `sales_variances` (T1)

- **Claims**: reconcile the revenue movement into price, mix and yield, per product and in total.
- **Inputs**: R `products` (`records`, ≥2): `name`, `budget_units`, `budget_price`,
  `actual_units`, `actual_price`.
- **Outputs**: per-product `price_variance`, `mix_variance`, `yield_variance`, `total_variance`,
  plus `budget_revenue`, `actual_revenue` and the totals.
- **Invariant**: price + mix + yield = the total revenue variance, exactly.
- **Refusals**: fewer than two products; a missing field; negative units or prices.

#### 3.1.7 `breakeven` → `breakeven` (T1)

- **Claims**: break-even quantity from fixed cost, price and variable cost; break-even revenue;
  the margin of safety at a declared expected volume; the volume for a declared target profit.
- **Inputs**: R `fixed`, `price`, `variable`; O `expected_units`, `target_profit`.
- **Outputs**: `breakeven_units`, `contribution_margin`, `contribution_margin_ratio`,
  `breakeven_revenue`, and when declared `expected_units`, `expected_revenue`,
  `margin_of_safety_units`, `margin_of_safety_ratio`, `target_profit`, `target_profit_units`.
- **Refusals**: `price <= variable` ("no break-even quantity exists"); negative fixed cost;
  negative expected units.
- **Never claims**: a demand forecast; tax is not modelled.

#### 3.1.8 `multibreakeven` → `multi_product_breakeven` (T1)

- **Claims**: the weighted contribution of a declared mix, the break-even total units and the
  units of each product.
- **Inputs**: R `fixed_costs`; R `products` (`records`, ≥2): `name`, `price`, `variable`,
  `mix_units`.
- **Outputs**: `weighted_contribution`, `breakeven_total_units`, `breakeven_revenue`,
  `units_<product>` per product, `total_mix_units`.
- **Refusals**: fewer than two products; a mix summing to zero; a product with price ≤ variable.

#### 3.1.9 `workingcapital` → `working_capital` (T1)

- **Claims**: DSO, DIO, DPO, the cash conversion cycle, net working capital, EOQ, reorder point,
  orders per year and the annual cost of forgoing a discount.
- **Inputs**: R `revenue`, `cost_of_sales`, `inventory`, `receivables`, `payables`,
  `annual_demand`, `order_cost`, `holding_cost_per_unit`, `discount_percent`,
  `credit_terms_days`, `discount_days`; O `daily_demand`, `lead_time_days`, `safety_stock`,
  `days` (default 365).
- **Outputs**: `dso`, `dio`, `dpo`, `cash_conversion_cycle`, `net_working_capital`, `eoq`,
  `reorder_point`, `n_orders_per_year`, `cost_of_trade_credit`, `daily_demand`.
- **Invariant**: `cash_conversion_cycle = dso + dio - dpo`.
- **Refusals**: `holding_cost_per_unit <= 0` (no EOQ); a negative balance; `days <= 0`.

#### 3.1.10 `loan` → `loan_amortization` (T1)

- **Claims**: the level payment, total paid, total interest and the first payment's split on a
  fixed-rate loan.
- **Inputs**: R `principal`, `annual_rate` (decimal), `years`; O `payments_per_year` (default 12).
- **Outputs**: `payment`, `total_paid`, `total_interest`, `periodic_rate`,
  `effective_annual_rate`, `n_payments`, `first_interest`, `first_principal`.
- **Invariant**: `payment = P·r / (1 − (1+r)^−n)` at the method's tolerance.
- **Refusals**: `principal <= 0`; `years <= 0`; `payments_per_year <= 0`; a negative rate.
- **Never claims**: fees, a rate change, an early repayment, or a tax effect.

#### 3.1.11 `trendanalysis` → `trend_analysis` (T1)

- **Claims**: common-size percentages, an index, compound growth and margin movement across the
  declared periods.
- **Inputs**: R `years` (value_list ≥2, increasing), `revenue`, `cost_of_sales`,
  `operating_expenses`, `net_income` (value_lists ≥2, same order); O `total_assets`, `equity`
  (lists ≥2, supplied together for the equity-to-assets and asset-growth rows).
- **Outputs**: `n_periods`, `revenue_cagr`, `revenue_growth_latest`, `net_income_cagr`,
  `revenue_index_latest`, `net_income_index_latest`, `gross_margin_latest`,
  `operating_margin_latest`, `net_margin_latest`, `gross_margin_change`, `net_margin_change`,
  `common_size_cost_of_sales`, `common_size_operating_expenses`, `equity_to_assets_latest`,
  `asset_growth_latest`.
- **Refusals**: fewer than two periods; lists of different lengths; a period label out of order;
  a non-positive revenue (a growth rate off a zero or negative base is refused, not printed).
- **Never claims**: a next-period forecast — that is `trend_forecast`, a different method.

#### 3.1.12 `tax` → `tax_declared` (T1)

- **Claims**: income tax on the declared taxable income at the declared rate, after-tax income,
  VAT payable from declared output and input tax, deferred tax from a declared temporary
  difference and rate, and the total charge.
- **Inputs**: R `taxable_income` (a loss may be negative), `income_tax_rate` (0…1); O
  `vat_output_tax` + `vat_input_tax` (a pair), `temporary_difference` + `deferred_tax_rate`
  (a pair).
- **Outputs**: `taxable_income`, `income_tax_rate`, `income_tax`, `net_income_after_tax`, and
  when declared `vat_output_tax`, `vat_input_tax`, `vat_payable`, `temporary_difference`,
  `deferred_tax_rate`, `deferred_tax`; always `total_tax_charge`.
- **Refusals**: a rate outside 0…1; one half of a pair; a negative VAT figure.
- **Never claims**: any jurisdiction's law, credits, exemptions, thresholds, NOLCO, withholding,
  filing, penalties or refunds (`unsupported_use`).

## 4. Worksheets and framework profiles

**None.** `SUBJECT_DEFS[0]["worksheets"] == []`, and `subjects.detail("accounting")` returns
`worksheets: []`, `tiles: []`, `theories: []`. `docs/CURRICULUM_MAP.md` lists the accounting
shelf as compute-only, so there is no framework profile, no evidence gate, no unit of analysis
and no draft/full behaviour to test for this shelf. This is a **declared shape**, tested by
E-acc-012 and recorded as GAP G-acc-02 — never as a defect.

The cross-shelf worksheets that touch accounting figures (break-even attached to a framework,
working-capital sections inside a finance paper) belong to *their* shelf and are tested there;
this session tests the computation and its capability paper (E-acc-040…E-acc-045).

## 5. Records, theories, glossary

| Record | Name | Form | Linked methods (all in `LIBRARY`) | Status claim |
|---|---|---|---|---|
| `QNT-FIN-02` | Cost and profitability | computed | `breakeven`, `multi_product_breakeven`, `abc_costing`, `sales_variances` | partial: operating-leverage, relevant-cost and make-or-buy are **not** implemented |
| `QNT-FIN-03` | Financial performance | computed | `ratio_analysis`, `dupont_analysis`, `working_capital` | partial: industry benchmarks and restatements are **not** implemented |
| `QNT-FIN-05` | Management accounting | computed | `management_accounts`, `standard_cost_variances`, `abc_costing` | partial: target, life-cycle and budget-variance topics are **not** implemented |

- **No theories** on this shelf (`detail()["theories"] == []`).
- **No read-only record** claims "not implemented" while linking a built method: all three rows
  are `form: computed`, and every id in `linked_methods` resolves in `bp.methods.LIBRARY`
  (measured by `qa/probe_related.py`; asserted by E-acc-015).
- The three rows' `implementation_status` is the authoritative narrow claim: the `partial:`
  prefix names what is missing, and the student guide's "What is not built" says the same.

**Glossary** (19 terms, `GLOSSARIES["accounting"]`): debit/credit, journal, ledger, trial
balance, accrual, prepayment, depreciation, accumulated depreciation, closing entries, retained
earnings, gross profit, working capital, current ratio, variance, favourable/unfavourable,
standard cost, taxable income, VAT, deferred tax. Every entry is a definition only — no number
and no formula output. Row E-acc-016 tests presence and non-emptiness.

## 6. Student guidance

Source: `bp.product.subjects.SUBJECT_DEFS` (the `accounting` entry) and `STUDENT_NOTES[key]`.

| Promise | Value on this shelf | Tested by |
|---|---|---|
| `summary` | "Ledger, statements, ratios and the cost-volume-profit questions built on them." | E-acc-017 |
| `guidance` | present, and orders the work check-first (trial balance → management accounts → ratios/trend → cost tools) | E-acc-017 |
| `start_steps` | 4 steps (≥3 required), each naming a tool or a question | E-acc-017 |
| `does_not` | 3 statements (≥2 required) | E-acc-017 |
| per-tool `level` | present on all 12 | E-acc-011 |
| per-tool `formula` | present on all 12, and it matches the method's own arithmetic | E-acc-011 |
| per-tool `steps` | 4 per tool (≥1 required) | E-acc-011 |
| per-tool `common_mistakes` | 3–4 per tool (≥1 required) | E-acc-011 |
| per-tool `related` | 2–3 ids each; every id resolves to a real calculator tool | E-acc-011 |
| per-tool `need` | **absent**: `TOOL_NEEDS` has no accounting key, so the card omits "You will need" and the figures panel falls back to its generic sentence | E-acc-018 (GAP G-acc-01) |
| `period` badge | every tool carries one (`annual` or `per period`) | E-acc-011 |
| `group` | every tool belongs to exactly one of the four groups | E-acc-012 |

## 7. Surface routing

| Surface | What opens | Route / code | Tested by |
|---|---|---|---|
| Rail tile "Accounting" | the subject page (`detail("accounting")`) | `GET /api/cases/subjects/accounting` (`api.handle`), rendered by the inline script in `web/index.html` | E-acc-014 |
| Tool card → use | the calculator with the tool's preset loaded | `activate("new")` + `PRESETS[tool.preset]` | E-acc-013, E-acc-019 |
| Calculator rail group "accounting" | the same 12 tools | `GET /api/cases/calculator` → `subjects.calculator_groups()` | E-acc-013 |
| Create a run | a plan only; nothing computed | `POST /api/sessions` | E-acc-007 |
| Confirm | the frozen core runs and the report is delivered | `POST /api/sessions/{id}/confirm` | E-acc-007 |
| Confirm the account mapping (management accounts only) | the second mandatory checkpoint before anything is posted | same `confirm` route; the page shows "Confirm the account mapping and post" | E-acc-007, `test_accounts.py` |
| Reject | blocked; the rest `not_run` | `POST /api/sessions/{id}/confirm` with `approved: false` | E-acc-008 |
| Deliverable | `.docx`/`.html` (submission, worksheet) or `.xlsx`/`.csv` (workpapers) | `deliverables.write_export()` | E-acc-045 |
| Records table | the three `QNT-*` rows, read-only | `detail()["records"]` / `["catalogue"]` | E-acc-015 |
| Glossary | 19 terms | `detail()["glossary"]` | E-acc-016 |

**No PDF, no Markdown and no ZIP attachment is offered for a computation deliverable.** The
available pairs are `docx`/`html` (submission, worksheet) and `xlsx`/`spreadsheetml`/`csv`
(workpapers); `presentation` is declared with **no renderer** and is refused with a reason
(`bp.product.deliverables.PROFILES`). That is a declared limit — GAP G-acc-07 — not a defect.

## 8. Expected behaviour — `E-acc-nnn`

Every row is atomic and testable. "Source" is the authority the expectation rests on.

### 8.1 Shelf shape and catalogue

| ID | Expectation | Source |
|---|---|---|
| E-acc-001 | The shelf declares exactly 12 compute tools, whose keys are `accounts, tbcheck, ratios, scv, abc, salesvar, breakeven, multibreakeven, workingcapital, loan, trendanalysis, tax`. | `SUBJECT_DEFS[0]["tools"]`; work-order §9 |
| E-acc-002 | The shelf declares **no** worksheet, theory or tile; the page groups its tools into four groups instead, and every tool carries one group. | `SUBJECT_DEFS[0]`; `ACCOUNTING_GROUPS` |
| E-acc-003 | Every accounting method declares a complete contract: non-empty `intended_use`, `unsupported_use`, `assumptions`, `limitations`, unique `test_names`, a `metric`, a `unit`, a valid tier (T1–T4), a valid `claim_ceiling`, and an `input_schema` whose every field has a `type` and a `desc`. | `LIBRARY[id]` (rank 1) |
| E-acc-004 | Every accounting tool's preset names the method the tool claims, and the preset's default inputs pass `validate_inputs` unchanged. | `server.PRESETS` + `methods.validate_inputs` |
| E-acc-005 | Every assignment in the student guide's requirement table maps to a tool on this shelf (12 rows → 12 tools). | guide §"Your assignment requirement" |
| E-acc-011 | Every tool carries student notes — `level`, `formula`, `steps`, `common_mistakes`, `related` — and every `related` id resolves to a real calculator tool. | `STUDENT_NOTES`; `compute_tools()` |
| E-acc-012 | Every tool carries a period badge and belongs to exactly one declared group; no tool is ungrouped. | `ACCOUNTING_PERIODS`/`ACCOUNTING_GROUPS` |
| E-acc-013 | The calculator's `accounting` group reaches the same 12 methods, and the calculator's union is exactly the subjects' compute tools. | `calculator_groups()`; `test_product_subjects.py` |
| E-acc-014 | `GET /api/cases/subjects/accounting` serves the page — 12 tools, 0 worksheets, 3 records, 19 glossary terms — and computes nothing. | `bp.product.api`; `test_product_subjects.py` |
| E-acc-015 | Every record on the shelf is `form: computed`, and every id in its `linked_methods` resolves in `LIBRARY`; no record denies a method that is built, and each `partial:` clause names an unbuilt topic. | `CATALOGUE` rows; `test_catalogue_truth.py` |
| E-acc-016 | The glossary carries its 19 declared terms, each with a non-empty definition and no number. | `GLOSSARIES["accounting"]` |
| E-acc-017 | `summary`, `guidance`, ≥3 `start_steps` and ≥2 `does_not` statements are present and non-empty. | `SUBJECT_DEFS[0]`; work-order §5 item 6 |
| E-acc-018 | A tool with no `need` text renders the generic "gather the figures" sentence rather than "null"/"undefined"; the absence is a named gap, not a blank cell. | `web/index.html` fallback; GAP G-acc-01 |
| E-acc-019 | Opening a tool from the shelf loads that tool's preset, and the preset's method is the tool's method (no dead tile, no wrong method). | `PRESETS`; `SUBJECT_GROUPS` |

### 8.2 The run path (every accounting tool)

| ID | Expectation | Source |
|---|---|---|
| E-acc-006 | Two runs of the same declared inputs produce byte-identical reports and the same spec hash: no clock, locale or dict-order dependence. | `spec.py` hashing; `test_session_api.py` |
| E-acc-007 | `POST /api/sessions` returns `awaiting_confirmation` with nothing computed and the method's `test_names` in the work plan; `confirm` returns `delivered`; the state is fully JSON-serialisable. `management_accounts` stops at its **second mandatory checkpoint** (`awaiting_mapping_confirmation`) and delivers only after the mapping is confirmed — the page's "Confirm the account mapping and post". | `session.py`; `test_session_api.py`; live click-through `qa/evidence/accounting/` |
| E-acc-008 | Rejecting the plan blocks it and marks the remaining stages `not_run`; a blocked run cannot later be confirmed. | `session.py`; `test_session_api.py` |
| E-acc-009 | An unknown input name, a wrong type or a binary float is refused at intake with an actionable message — never a 500, never a silent coercion. | `methods.validate_inputs`; orchestrator intake |
| E-acc-051 | An **unknown method name** is refused with a reason, not silently converted into a framework-only (T4) delivery; the declared `framework_only` sentinel still delivers a structure-only paper. | `HANDOFF.md` non-negotiable 4 ("unknown method → block"); `orchestrator.start` intake; B-181 |
| E-acc-052 | Every accounting method — and the accounting-adjacent methods `tax_incidence`, `risk_metrics`, `social_welfare` — owns its own `typing` hook: no two methods share a hook name or function object, and each answers with its own units. | `LIBRARY[id].typing`; B-179 |
| E-acc-053 | A brief that belongs to another shelf is refused by the shelf vocabulary, naming the shelf ("does not look like a management or strategy instruction"); one recognised word is enough, and an explicitly named framework is never refused. | `guard.subject_fit`; `CONDUCTOR_MANUAL.md` §4; B-180 |
| E-acc-010 | A delivered accounting computation carries its honesty block, passes every declared check, keeps its claim ceiling (`descriptive`) and contains no unresolved `{{ref:` token. | orchestrator/`claims`; `test_honesty.py` |
| E-acc-045 | A delivered computation exports to `.docx` (submission) and `.xlsx` (workpapers) with the computed numbers unchanged and no template text; `presentation` is refused with a reason. | `deliverables.py`; `CONDUCTOR_MANUAL.md` §8 |

### 8.3 Tool behaviour, refusals and independent recomputation

| ID | Expectation | Source |
|---|---|---|
| E-acc-020 | A trial balance that does not balance is reported **first**, with the difference, and the tool never plugs it. | `bp.check`; `test_trial_balance_check.py` |
| E-acc-021 | A balanced-but-wrong trial balance is compared line by line: the differing lines carry a finding and the verdict says it cannot tell which figure is right. | `LIBRARY["trial_balance_check"].unsupported_use` |
| E-acc-022 | An account listed twice, a negative figure, or a figure with more decimals than declared is refused with a specific reason. | `bp.check.CheckError` |
| E-acc-023 | A management-accounts engagement with an unbalanced entry is refused or fails a named check; nothing is posted. | `accounts` kernel; guide §1 |
| E-acc-024 | The management accounts satisfy `assets = liabilities + equity`, both cash-flow routes agree, and the retained-earnings rollforward closes — on the preset and on a multi-feature engagement. | `test_accounting_pipeline_integration.py` |
| E-acc-025 | An opening balance that disagrees with `prior_closing` fails the opening-balances check. | `LIBRARY["management_accounts"].defaults` |
| E-acc-026 | `net_margin` from `ratio_analysis` equals an independent `net_income / revenue` recomputation at 1e-9. | guide §3; `ratio_golden.json` |
| E-acc-027 | A ratio with a zero denominator is **not computed** and the reason names the denominator; a ratio is never printed as infinity or NaN. | `test_ratio.py` |
| E-acc-028 | Ratio output contains no benchmark, no industry comparison and no verdict — only arithmetic and the stated limitation. | `LIBRARY["ratio_analysis"].unsupported_use` |
| E-acc-029 | The four core standard-cost variances plus the total equal the student guide's worked example (`4,900 U`, `3,000 U`, `7,300 U`, `4,000 U`, total `46,200 U`), and a positive variance is unfavourable. | guide §2 |
| E-acc-030 | Overhead variances appear only when the overhead inputs are declared, and `total_variance` equals the sum of the variances actually reported. | `LIBRARY["standard_cost_variances"]` checks |
| E-acc-031 | Activity-based costing allocates exactly the pool total (`total_allocated` = sum of pools), and per-unit costs equal allocation ÷ units. | guide §4 |
| E-acc-032 | An activity with a cost and no driver quantity is refused rather than silently unallocated. | guide §4 "Common mistake" |
| E-acc-033 | Sales price + mix + yield equals the total revenue variance exactly, and the guide's example reconciles (`-40 + -200 + 0 = -240`). | guide §5 |
| E-acc-034 | A break-even with `price <= variable` is refused with an actionable reason — never a division by zero, never `Infinity`. | `methods.breakeven` |
| E-acc-035 | Break-even units equal `fixed / (price - variable)` at 1e-9, and the margin of safety is measured against the declared expected volume only. | `LIBRARY["breakeven"]` checks |
| E-acc-036 | The multi-product break-even's per-product units sum to the break-even total, and the weighted contribution is the mix-weighted unit contribution. | `LIBRARY["multi_product_breakeven"]` |
| E-acc-037 | `cash_conversion_cycle = dso + dio - dpo`, and `eoq` equals `sqrt(2·D·S/H)` independently recomputed from the declared demand, order cost and holding cost. | guide §"Answer key" 2 |
| E-acc-038 | The loan payment equals `P·r/(1-(1+r)^-n)` independently recomputed, and a zero-rate loan pays exactly `principal / n` per payment. | `LIBRARY["loan_amortization"]` |
| E-acc-039 | `revenue_cagr` equals `(end/start)^(1/periods) - 1` independently recomputed, and a negative net-income base omits the income CAGR rather than printing an imaginary root. | `LIBRARY["trend_analysis"]`; guide §"Common mistake" |
| E-acc-040 | `tax_declared` applies the student's declared rate and never a jurisdiction's law: income tax = positive income × rate, a loss carries no positive tax, and the report states the limitation. | `LIBRARY["tax_declared"].unsupported_use`; guide §6 |
| E-acc-041 | `vat_payable = output - input` and `total_tax_charge = income_tax + deferred_tax`, and a half-declared VAT or deferred pair is refused. | `tax_declared_tests` |
| E-acc-042 | The student guide's worked examples reproduce through the tools: trial balance 85,000 / assets 76,000; current ratio 2.50 and quick ratio 1.50; ABC 40,000 + 40,000 = 80,000; tax 250,000 / 60,000 / 25,000 / 275,000; EOQ 447.21. | guide §"Worked examples" and "Answer key" |

### 8.4 The paper the student receives

| ID | Expectation | Source |
|---|---|---|
| E-acc-043 | A recorded accounting computation appears in the paper as prose built from the recorded result — never a raw `key: value` dump, never a 50-digit Decimal, never the internal `_appendix` dict. | `CONDUCTOR_MANUAL.md` §8; `VALIDATION_HARNESS.md` V-06/V-07 |
| E-acc-044 | Each capability is formatted by its **own** formatter: `trend_analysis` reports the common-size/trend figures and `trend_forecast` reports the forecast, each under its own section heading. | `chat.CAPABILITY_LINES`; V-05 |
| E-acc-046 | A chained input states the result it came from ("from the … result"), so a derived figure is never presented as one the student typed. | `chat._declared_inputs_line`; V-13 |
| E-acc-047 | A computation section opens with its declared inputs, and a computation that was refused or not run says so and reports no figure. | V-12; `test_plan_verifier.py` |
| E-acc-048 | The paper's accounting prose contains no recommendation, no forecast claim and no invented number: the figures in it are the recorded ones at the declared precision. | `verify.overclaims`; `CONDUCTOR_MANUAL.md` §4 |

### 8.5 Routing and documentation coherence

| ID | Expectation | Source |
|---|---|---|
| E-acc-049 | A brief that is a pure accounting computation ("prepare the journal entries and the trial balance") typed into the framework chat is **refused** (`stage: not_supported`) and names the Accounting shelf, instead of being wrapped in a PESTEL paper. | `guard.computation_boundary`; `CONDUCTOR_MANUAL.md` §4 (no silent framework substitution) |
| E-acc-050 | The student guide's "What is not built" list, the catalogue's `partial:` clauses and `KNOWN_LIMITATIONS.md`/`PRODUCT_GAP_MAP.md` agree: no document claims a built feature that is absent, and no built feature is described as absent. | §2 table; `test_docs_sync.py` |

## 9. Traceability matrix

Every E-row maps to the test that enforces it. `PASS` = the test exists and is green in this
session; `GAP` = a declared gap (ledger id given); `BLOCKED` = waiting on an owner decision.

| E-row | Enforced by | Status |
|---|---|---|
| E-acc-001 | `test_E_acc_001__shelf_declares_twelve_tools` | PASS |
| E-acc-002 | `test_E_acc_002__no_worksheets_theories_or_tiles` | PASS |
| E-acc-003 | `test_E_acc_003__every_method_declares_its_full_contract` | PASS |
| E-acc-004 | `test_E_acc_004__preset_launches_the_claimed_method_with_valid_inputs` | PASS |
| E-acc-005 | `test_E_acc_005__every_guide_assignment_maps_to_a_tool` | PASS |
| E-acc-006 | `test_E_acc_006__same_inputs_same_report_and_hash` | PASS |
| E-acc-007 | `test_E_acc_007__session_plans_then_delivers_and_serialises` | PASS |
| E-acc-008 | `test_E_acc_008__rejecting_the_plan_blocks_and_marks_the_rest_not_run` | PASS |
| E-acc-009 | `test_E_acc_009__bad_input_is_refused_never_coerced` | PASS |
| E-acc-010 | `test_E_acc_010__delivered_report_is_honest_and_licensed` | PASS |
| E-acc-011 | `test_E_acc_011__tool_notes_and_related_ids_resolve` | PASS |
| E-acc-012 | `test_E_acc_012__every_tool_has_one_group_and_one_period` | PASS |
| E-acc-013 | `test_E_acc_013__calculator_reaches_the_same_twelve_methods` | PASS |
| E-acc-014 | `test_E_acc_014__subject_route_serves_the_shelf_and_computes_nothing` | PASS |
| E-acc-015 | `test_E_acc_015__records_claim_only_what_is_built` | PASS |
| E-acc-016 | `test_E_acc_016__glossary_is_complete_and_definition_only` | PASS |
| E-acc-017 | `test_E_acc_017__guidance_start_steps_and_does_not_are_present` | PASS |
| E-acc-018 | `test_E_acc_018__missing_need_text_falls_back_and_is_ledgered` | PASS (GAP G-acc-01) |
| E-acc-019 | `test_E_acc_019__opening_a_tool_loads_its_own_preset` | PASS |
| E-acc-020 | `test_E_acc_020__unbalanced_trial_balance_reports_the_difference_never_plugs` | PASS |
| E-acc-021 | `test_E_acc_021__balanced_but_wrong_trial_balance_is_located` | PASS |
| E-acc-022 | `test_E_acc_022__trial_balance_refuses_duplicates_negatives_and_precision` | PASS |
| E-acc-023 | `test_E_acc_023__unbalanced_entry_is_refused` | PASS |
| E-acc-024 | `test_E_acc_024__statements_balance_and_both_cash_routes_agree` | PASS |
| E-acc-025 | `test_E_acc_025__opening_balance_must_equal_prior_closing` | PASS |
| E-acc-026 | `test_E_acc_026__net_margin_matches_an_independent_recomputation` | PASS |
| E-acc-027 | `test_E_acc_027__zero_denominator_is_removed_with_a_reason` | PASS |
| E-acc-028 | `test_E_acc_028__ratios_make_no_benchmark_claim` | PASS |
| E-acc-029 | `test_E_acc_029__variances_match_the_guide_example` | PASS |
| E-acc-030 | `test_E_acc_030__overhead_variances_only_when_declared_and_total_foots` | PASS |
| E-acc-031 | `test_E_acc_031__abc_allocates_exactly_the_pools` | PASS |
| E-acc-032 | `test_E_acc_032__abc_refuses_a_pool_with_no_driver` | PASS |
| E-acc-033 | `test_E_acc_033__price_mix_yield_reconcile_to_the_total` | PASS |
| E-acc-034 | `test_E_acc_034__breakeven_refuses_price_at_or_below_variable_cost` | PASS |
| E-acc-035 | `test_E_acc_035__breakeven_units_and_margin_of_safety` | PASS |
| E-acc-036 | `test_E_acc_036__multi_product_units_sum_to_the_total` | PASS |
| E-acc-037 | `test_E_acc_037__ccc_and_eoq_match_an_independent_recomputation` | PASS |
| E-acc-038 | `test_E_acc_038__loan_payment_matches_the_closed_form` | PASS |
| E-acc-039 | `test_E_acc_039__cagr_matches_an_independent_recomputation` | PASS |
| E-acc-040 | `test_E_acc_040__tax_uses_the_declared_rate_and_no_jurisdiction` | PASS |
| E-acc-041 | `test_E_acc_041__vat_and_deferred_tax_foot_and_pairs_are_enforced` | PASS |
| E-acc-042 | `test_E_acc_042__guide_worked_examples_reproduce` | PASS |
| E-acc-043 | `test_E_acc_043__papers_read_as_prose_not_raw_decimals` | PASS |
| E-acc-044 | `test_E_acc_044__each_capability_uses_its_own_formatter` | PASS |
| E-acc-045 | `test_E_acc_045__deliverables_carry_the_numbers_and_refuse_presentation` | PASS |
| E-acc-046 | `test_E_acc_046__a_chained_input_names_its_source` | PASS |
| E-acc-047 | `test_E_acc_047__a_section_opens_with_its_declared_inputs` | PASS |
| E-acc-048 | `test_E_acc_048__paper_prose_carries_no_recommendation_or_forecast` | PASS |
| E-acc-049 | `test_E_acc_049__a_pure_accounting_brief_is_refused_and_named` | PASS |
| E-acc-050 | `test_E_acc_050__guide_catalogue_and_limitations_agree` | PASS |
| E-acc-051 | `test_E_acc_051__an_unknown_method_is_refused` | PASS (was BLOCKED; fixed under B-181) |
| E-acc-052 | `test_E_acc_052__each_method_owns_its_typing_hook` | PASS (was BLOCKED; fixed under B-179) |
| E-acc-053 | `test_E_acc_053__a_brief_for_another_shelf_is_refused_by_vocabulary` | PASS (was BLOCKED; fixed under B-180) |

Rows E-acc-043, E-acc-044, E-acc-046, E-acc-049 were **FAIL** when this session opened (they are
baseline failures `test_a_bespoke_formatter_reports_the_core_numbers_as_money`,
`test_a_finance_paper_reports_the_cash_conversion_cycle`, `test_plan_dependencies…`,
`test_plan_verifier…` and `test_open_pure_accounting_refused`). Their fixes are this session's
first increment; see `qa/QA_DEFECTS.md` D-ACC-01…D-ACC-05.

Rows E-acc-051, E-acc-052 and E-acc-053 were **BLOCKED** at the same point — each needed an owner
decision. The owner approved all three in the session that followed, so they are now **PASS**,
each with its own trap test and its own decision: **B-179** (one `typing` hook per method),
**B-180** (the shelf vocabulary enforces again, with a named-framework carve-out) and **B-181**
(an unknown method name fails closed).

## 10. Known gaps (declared, not fixed)

| ID | Gap | Declared by | Why it stays open |
|---|---|---|---|
| G-acc-01 | No `TOOL_NEEDS` text for the 12 accounting tools; the card omits "You will need" and the figures panel uses its generic sentence. | this manual, E-acc-018 | Presentation copy, not a capability: no number is affected. Ledgered for the design lane. |
| G-acc-02 | No worksheet or framework profile on this shelf. | `SUBJECT_DEFS[0]["worksheets"] == []`; `CURRICULUM_MAP.md` | Declared shelf shape. |
| G-acc-03 | No jurisdiction tax law, credits, thresholds, NOLCO or filing; no audit sampling or opinion; no group consolidation; no target or life-cycle costing; no budget, planning or idle-capacity variances. | guide §"What is not built"; `LIBRARY` limitations; `QNT-FIN-02/05` | Owner-gated (tax is B-052; standards retrieval is HANDOFF §4G). |
| G-acc-04 | No PDF, scan or image ingestion. | guide §"What is not built" | Parked ingestion work (HANDOFF §4). |
| G-acc-05 | `_tax_typing` is defined twice in `src/bp/methods.py` (lines 5164 and 13953); `tax_incidence` captures the second, so its unit/precision hook answers for `tax_declared`. `_risk_typing` and `_social_typing` are duplicated the same way. | `qa/probe_duplicates.py`, `qa/probe_shadowing.py` | **RESOLVED — B-179 (owner unfreeze, 2026-11-02).** All six hooks renamed to one per method (`_tax_incidence_typing`, `_tax_declared_typing`, `_risk_metrics_typing`, `_schedule_risk_typing`, `_social_welfare_typing`, `_social_engagement_typing`) and re-pointed; `methods.py` now has **zero** duplicate definitions. Test: E-acc-052. |
| G-acc-06 | `guard.subject_fit()` returned `(True, None)` unconditionally, so a marketing brief typed on the management shelf was refused by `_fit`'s external-evidence rule rather than by the subject vocabulary. | `docs/CONTINUATION_NOTE.md`; `tests/test_product_home_routing.py::test_shelf_mode_control` | **RESOLVED — B-180 (owner decision, 2026-11-02).** The vocabulary enforces again (`SUBJECT_HINTS`, one recognised word is enough) with a named-framework carve-out and the computation boundary checked first; the refusal names the shelf. Test: E-acc-053. |
| G-acc-07 | No PDF, Markdown or ZIP deliverable for a computation; `presentation` has no renderer. | `deliverables.PROFILES` | Declared limit: a format is offered only where a renderer exists. |
| G-acc-08 | The student guide's practice-set questions 3 and 4 are queueing and line-balancing exercises — operations tools, not accounting ones. | guide §"Practice set"; `OPERATIONS_GROUPS` | Documentation drift. Ledgered D-ACC-08 (MINOR, DOC-DRIFT): the questions are answerable on the Operations shelf. |
| G-acc-09 | An unknown `method` name was delivered as a framework-only (T4) response instead of being refused. | `orchestrator.start`; `HANDOFF.md` non-negotiable 4 | **RESOLVED — B-181 (owner unfreeze, 2026-11-02).** The intake refuses a name that is neither a frozen method nor a template, with the reason and the pointer to `/api/methods`; the declared `framework_only` sentinel still produces a structure-only paper. Test: E-acc-051. |










