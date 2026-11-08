# Case-authoring brief — Accounting shelf

**Give this whole file to the authoring model.** It is self-contained: the contract,
the rules, the tile list, the ten-case design and the acceptance check.

---

## 1. What you are producing

Real, solvable problems for the **Accounting** subject of Smart Business Writer, ten per
tile, written as files the product can replay:

| Group | Tiles | Deliverable |
|---|---|---|
| Financial statements | the statements service | ten `problem_NNN.txt` + one `problems.json` |
| Management accounts | `accounts` | ten `case_001.json` … `case_010.json` |
| Check a trial balance | `tbcheck` | ten `case_001.json` … `case_010.json` |
| Statement analysis | `ratios`, `dupont`, `trendanalysis` | ten cases each |
| Adjustments and depreciation | `depreciation` | ten cases |
| Cost and variance analysis | `scv`, `abc`, `salesvar`, `breakeven`, `multibreakeven` | ten cases each |
| Working capital and financing | `workingcapital`, `loan` | ten cases each |
| Planning and projection | `proforma`, `sensitivity`, `frommarket`, `salesprojection` | ten cases each |
| Tax and reporting | `tax` | ten cases |

A "case" is not an essay. It is the instruction the student sees, the figures the method
takes, and **the result the frozen core actually returns for those figures**. The product
replays it and fails if any number differs.

---

## 2. Ground truth and non-negotiables

1. **Every expected number comes from the frozen core.** You never hand-compute, never
   estimate, never round a result. Run the method, copy its output dict exactly (§5).
2. **No invented evidence, source, figure or citation.** If a figure is not in the
   problem, it does not exist. A missing figure is a named gap, not a guess.
3. **Student inputs stay student inputs.** The case's `inputs` are exactly what the
   instruction states — nothing added to make the arithmetic tidy.
4. **Global product.** USD only. Neutral place names ("a mid-sized city", "Northport",
   "Riverside Supplies"). **Never** PSE, PHP, Philippine, Manila, or a home-country
   exchange. No real company, brand or person.
5. **No silent substitution.** The case names the method it is for; it must not be a
   different tile's problem wearing that label.
6. **A refusal is a valid case.** Some of the ten must be inputs the engine must refuse
   (missing required figure, impossible value). Those carry `expected.status: "blocked"`.
7. **Do not modify the product.** Add files under `qa/cases/accounting/` only. Never edit
   `src/`, `web/`, `tests/` or an existing case.

---

## 3. Repository facts

Project root: `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline`

Run every Python command with the source on the path:

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
```

Cases live at `qa/cases/<subject>/<tile>/case_<NNN>.json`; the id inside is
`<subject>/<tile>/<NNN>` (three digits, matching the file name).

---

## 4. The case file contract

```json
{
 "format": "bp-tile-case/1",
 "id": "accounting/depreciation/002",
 "subject": "accounting",
 "subject_label": "Accounting",
 "tile": "depreciation",
 "tile_label": "Depreciation schedule",
 "group": "Adjustments and depreciation",
 "method": "depreciation_schedule",
 "objective": "Depreciation schedule at a declared rate",
 "instruction": "A delivery van costs USD 24,000 with an estimated residual value of USD 4,000 and a five-year life. Required: prepare the straight-line depreciation schedule for the five years.",
 "inputs": {"cost": "24000", "salvage": "4000", "life": "5", "method": "straight_line"},
 "expected": {
  "status": "ok",
  "result": { "...": "every key the core returned, exactly as returned" },
  "contains": ["Depreciation schedule", "Declared inputs", "References"],
  "xlsx_sheets": ["Summary", "Inputs", "Results", "Record"]
 },
 "created_at": "2026-11-08T00:00:00+00:00",
 "origin": "authored"
}
```

Rules for the fields:

* `tile` is the **tool key** from the table in §7; `tile_label` is that tool's label;
  `group` is the shelf tile it belongs to (the table's left column).
* `method` is the frozen method id from the table. It must be the tile's own method.
* `instruction` is a readable problem, not a dump of the JSON. It states the figures in
  prose and ends with what is required. Any figure in `inputs` must appear in the
  instruction.
* `inputs` values are **strings**, as the method's schema requires. Lists and tables keep
  the schema's shape (`decimal_list`, `rows`, `engagement_spec`, …).
* `expected.status` is `"ok"` or `"error"`.
* `expected.result` must contain **every** key the core returned and **no key it did not**
  — the runner fails on both a missing key and an extra one.
* A **refusal case** is `{"status": "error"}` and nothing else: no `result`, no
  `contains`, no `xlsx_sheets`. The engine's own message is what proves the refusal.
* `expected.contains` are phrases the Word paper must print. Use the tile's own paper
  title (as it appears in the paper), then `"Declared inputs"`, then `"References"`.
* `expected.xlsx_sheets` is `["Summary", "Inputs", "Results", "Record"]` for every tile
  case.
* `origin` is `"authored"`.

---

## 5. How to produce `expected` — the only acceptable way

Never type a result by hand. For each case:

```python
import json
from bp import methods

case = json.load(open("qa/cases/accounting/depreciation/case_002.json", encoding="utf-8"))
method = methods.LIBRARY[case["method"]]

errors = methods.validate_inputs(method, case["inputs"])
assert not errors, errors          # fix the inputs, never the method

result = method.impl(case["inputs"])
print(json.dumps({k: str(v) for k, v in result.items() if not str(k).startswith("_")}, indent=1))
```

Paste that printed dict into `expected.result` unchanged. If the method refuses
(validation error), the case is either an input mistake to fix, or a **blocked** case:
then set `expected` to `{"status": "blocked"}` and keep no result.

A case is replayed from **its own** `inputs`, so a tile with no published preset — every
accounting tile — still replays. The preset is only the fallback for a preview with no
inputs, never a requirement for a case.

To discover a method's inputs:

```python
from bp import methods
import json
print(json.dumps(methods.describe("<method_id>")["input_schema"], indent=1))
```

---

## 6. The ten-case design (same skeleton for every tile)

Write ten cases that between them prove the tile handles a real spread. Each row is one
case; adapt the wording to the tile, keep the role.

| # | Role | What it proves |
|---|---|---|
| 1 | Clean baseline | whole figures, a tidy answer, the ordinary case |
| 2 | Realistic exam | a paragraph of prose, figures embedded, commas in the numbers |
| 3 | Boundary | zero, or the exact break-even/maturity/limit point |
| 4 | Large values | millions, thousands separators, six-figure results |
| 5 | Loss or adverse | negative result, decline, unfavourable variance |
| 6 | Rate or percentage | a rate given in prose ("12% a year"), rounded answer |
| 7 | Two-period / comparison | the method's prior-period or comparison inputs, if it has them |
| 8 | Mixed or repeated structure | several products/activities/years in one problem |
| 9 | Refusal | a required figure missing or an impossible value; `expected: {"status": "error"}` |
| 10 | Free choice | the hardest realistic problem the tile can actually solve |

For `accounts` (management accounts), the ten roles map onto engagements: a service
business, a retail business with inventory, a business with a loss, one with a loan and
interest, one with depreciation, one with prepaid and accrued adjustments, one with a
contra-revenue return, one with a full year and twelve monthly entries, one the engine
must refuse (an unbalanced opening or an empty chart — `status: "error"`), and one whose
accounts the mapping cannot place, which the product reports rather than posts.

For `tbcheck`, the ten roles are: perfect match; a transposition; one account missing from
the submitted TB; an extra account; a wrong side; an obvious typo; a large difference; a
compensating pair; an unreadable line (blocked); a TB that balances but disagrees with the
journal line by line.

---

## 7. Tiles, methods and inputs

| Group | `tile` key | `tile_label` | `method` | Input names |
|---|---|---|---|---|
| Bookkeeping | `accounts` | Management accounts | `management_accounts` | `spec` |
| Bookkeeping | `tbcheck` | Check a trial balance | `trial_balance_check` | `journal, trial_balance, places` |
| Statement analysis | `ratios` | Financial statement ratios | `ratio_analysis` | `current_assets, current_liabilities, cash, inventory, receivables, payables, total_assets, total_liabilities, equity, revenue, cost_of_sales, operating_profit, net_income, interest_expense, operating_cash_flow, capital_expenditure, working_capital, retained_earnings, ebit, sales, market_value_equity, share_price, shares_outstanding, dividends_declared` |
| Statement analysis | `dupont` | DuPont analysis | `dupont_analysis` | `revenue, net_income, total_assets, equity, cost_of_sales, ebit, pretax_income, tax_expense, prior_revenue, prior_net_income, prior_total_assets, prior_equity` |
| Statement analysis | `trendanalysis` | Common-size and trend | `trend_analysis` | `years, revenue, cost_of_sales, operating_expenses, net_income, total_assets, equity` |
| Adjustments and depreciation | `depreciation` | Depreciation schedule | `depreciation_schedule` | `cost, salvage, life, method, declining_rate` |
| Cost and variance | `scv` | Standard-cost variances | `standard_cost_variances` | `actual_units, standard_material_per_unit, standard_material_price, actual_material_quantity, actual_material_price, standard_hours_per_unit, standard_labour_rate, actual_hours, actual_labour_rate, standard_variable_overhead_rate, actual_variable_overhead, budgeted_fixed_overhead, actual_fixed_overhead, denominator_hours` |
| Cost and variance | `abc` | Activity-based costing | `abc_costing` | `activities, products, allocations` |
| Cost and variance | `salesvar` | Sales price, mix and yield | `sales_variances` | `products` |
| Cost and variance | `breakeven` | Break-even point | `breakeven` | `fixed, price, variable, expected_units, target_profit` |
| Cost and variance | `multibreakeven` | Multi-product break-even | `multi_product_breakeven` | `fixed_costs, products` |
| Working capital | `workingcapital` | Working capital and EOQ | `working_capital` | `revenue, cost_of_sales, inventory, receivables, payables, annual_demand, order_cost, holding_cost_per_unit, discount_percent, credit_terms_days, discount_days, days, daily_demand, lead_time_days, safety_stock` |
| Working capital | `loan` | Loan amortization | `loan_amortization` | `principal, annual_rate, years, payments_per_year` |
| Planning and projection | `proforma` | Projected statements | `proforma_statements` | `revenue, gross_margin_rate, operating_costs, depreciation, interest, principal_repayment, loan_principal, loan_annual_rate, loan_years, capex, tax_rate, receivable_days, inventory_days, payable_days, opening_cash, opening_fixed_assets, opening_receivables, opening_inventory, opening_payables, opening_loan, opening_equity` |
| Planning and projection | `sensitivity` | Price and volume sensitivity | `sensitivity_table` | `base_price, base_units, base_variable_cost, base_fixed_cost, price_changes, volume_changes` |
| Planning and projection | `frommarket` | Sales from market share | `sales_from_market` | `market_size, target_share, price` |
| Planning and projection | `salesprojection` | Sales and profit projection | `sales_projection` | `start_units, price, unit_variable_cost, fixed_cost_per_period, growth_rate, periods` |
| Tax and reporting | `tax` | Tax on declared rates | `tax_declared` | `taxable_income, income_tax_rate, vat_output_tax, vat_input_tax, temporary_difference, deferred_tax_rate` |

The `spec` input of management accounts is a JSON engagement:

```json
{"period": {"start": "2026-01-01", "end": "2026-03-31"},
 "currency": "USD", "framework": "local", "places": 2,
 "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"}],
 "prior_closing": {"1000": "5000"},
 "opening": [{"lines": [{"account": "1000", "debit": "5000"}, {"account": "3000", "credit": "5000"}]}],
 "entries": [{"date": "2026-01-15", "description": "sale",
              "lines": [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}]}],
 "schedules": []}
```

Roles that must be present in a working chart: `cash`, `capital`, `retained_earnings`.
Every entry must balance to the cent before the case is written.

---

## 8. Financial statements is a service, not a case JSON

The statements tile takes one instruction and builds the journal, trial balance and
statements itself. Do **not** write `case_*.json` for it. Write ten problems:

```
qa/cases/accounting/statements/problem_001.txt … problem_010.txt
qa/cases/accounting/statements/problems.json
```

`problem_NNN.txt` is the raw text a student would paste. `problems.json` records what the
solver must return:

```json
{"format": "bp-statements-problems/1", "problems": [
 {"id": "accounting/statements/001", "type": "trial_balance", "file": "problem_001.txt",
  "expected": {"solved": true, "problem_type": "trial_balance",
               "scalars": {"total_assets": "45900", "net_income": "0",
                           "checks_passed": "9", "checks_total": "11"}}}
]}
```

The ten must cover the seven problem shapes the shelf handles: a trial balance that
balances; a trial balance with adjustments; a transaction narrative; a missing figure to
reconstruct; an error to correct; a ratio question; a cash-flow question. Two extra: an
instruction that names a different shape (must be refused with `solved: false`), and a
full integrated case.

Produce the expected values the same way — never by hand. The statements tile needs the
frozen core attached, so start the workbench and use its own route:

```powershell
python -m bp.server 8000
```

```powershell
$body = @{ instruction = (Get-Content "qa/cases/accounting/statements/problem_001.txt" -Raw) } | ConvertTo-Json
$r = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/cases/statements" -Method Post -ContentType "application/json" -Body $body
$r.solved; $r.problem_type; $r.core.scalars | ConvertTo-Json
```

Copy `solved`, `problem_type` and **every key of `core.scalars`** (`net_income`,
`total_assets`, `total_liabilities`, `total_equity`, `retained_earnings_closing`,
`cash_net`, `checks_passed`, `checks_total`, `checks_na`, `n_entries`, `n_flags`) into
`expected.scalars`. A refused problem is `{"solved": false}` with the refusal text recorded
in a `"why"` field.

---

## 9. Definition of done

For every case you write:

```powershell
$env:PYTHONPATH="src"
python -c "from bp.product import case_runner; import json; print(json.dumps(case_runner.run_case('accounting/depreciation/002'), indent=1))"
```

`"status": "pass"` and an empty `problems` list. For a refusal case the replay must
return `"status": "error"` with the engine's own message — that is the proof the engine
refused rather than answered.

At the end:

```powershell
$env:PYTHONPATH="src"
python -m pytest tests/test_product_case_loop.py -q
python -m pytest tests/test_statements_figures.py tests/test_product_statements_api.py -q
```

All green, and no new `tile-case` error in the error log.

**Hand back:** the files, a table of case id → one-line description, the exact commands
you ran, and any case you could not make pass with the reason. Never delete or edit a
seeded case to make yours pass.
