# Living Manual — Financial Statement Computation Engine (Sections A–K)

> **Purpose.** This is the living manual for the financial-statement computation lane. It records what is built, what
> is wired into the tile, what remains to be built, and how to verify everything. It sits beside the existing manuals —
> it does not replace them.
>
> **Existing manuals (read these first):**
> - `docs/TIPS_FINANCIAL_STATEMENTS.md` — the owner's four tips + Tips 5–7, the problem-solving framework, the 22 guards (G1–G22), the state machine.
> - `docs/STATEMENTS_TILE_PLAN.md` — the approved build instruction for the statements tile.
> - `docs/HANDOFF_STATEMENTS_TILE.md` — the design-lane handoff for the UI/UX side (MiniMax).
> - `docs/HANDOFF.md` — commands, non-negotiables, B-decisions, definition of done.
> - `docs/CONDUCTOR_MANUAL.md` — §4, §7, §7.6 non-negotiables; `docs/CONTRIBUTORS.md` §1A/§1B lane split.
>
> **This manual was rewritten on 2026-11-04.** The previous version made four claims that measurement did not support.
> Each correction is named where it appears, so a later reader can see what used to be claimed and why it changed.

---

## 1. What a model is needed for — measured, not assumed

**The tile reads a trial balance with no model at all.** Deterministic parsing, zero dependencies.

**A transaction narrative is now read deterministically too.** The detector/runtime layer (`src/bp/statement_detect.py`,
wired at build 1.98) turns the text into journal entries, and the plan layer compiles them. Measured on 2026-11-04,
with **no model configured**:

| input | before this increment | now |
|---|---|---|
| a five-clause transactions narrative | crashed (`decimal.InvalidOperation`) | **201 solved**, 11/11 checks, period taken from the text's own dates |
| an exam question with a preamble before the figures | 422 "does not balance" | **201 solved**; the preamble is named as a line it could not place |
| an adjustments narrative (depreciation + accrual) | 400 "two figures on one line" | 400 **"no model is configured"** — an honest gate, not a misleading refusal |
| a trial balance + "Also compute the liquidity ratios." | the balance-sheet-analysis route: total assets **86,900**, the income statement hidden | **201 solved** — the trial-balance route: the three statements and **13 ratios** |
| a ratio question, one account per line | 400 "an account has no code" | **201 solved** (`balance_sheet_analysis`) |
| a ratio question written as a prose list | 400 "an account has no code" | 400 **"no model is configured"** — the tile reads one account per line |
| a cash-flow narrative | 16.9 s, then 400 "the chart needs exactly one retained-earnings account" | 400 **"closing with abnormal balances needs a human decision: 1500 (Property, plant and equipment)"**, in 0.0 s |
| a trial balance in EUR | 400 "this product answers in USD only" | unchanged — a deliberate rule |

**What still needs a model.** The *adjustments* (depreciation convention, prepaid amortisation, tax) are derived by
the plan layer's model step (`_statement_extract` in `bp/server.py`), and a narrative whose transactions the detector
layer does not recognise still needs the model reader. Without a key the tile says plainly:

> no model is configured, so only a trial balance can be read. Set DEEPSEEK_API_KEY (or BP_LLM_PROVIDER + BP_LLM_MODEL).

To configure:
```powershell
$env:DEEPSEEK_API_KEY="your-key"
# or
$env:BP_LLM_PROVIDER="openai"
$env:BP_LLM_MODEL="gpt-4"
```

**A key opens the door; it does not repair the reader.** Before this increment the answer to a transactions narrative
came from the model. It now comes from the deterministic layer, and the model's remaining job is the adjustments.

---

## 2. Current state at a glance

| Item | State | Where |
|------|-------|-------|
| Trial balance → IS/RE/BS | built & tested | `src/bp/product/statements.py` (deterministic parser) |
| Given account balances → IS / BS analysis | built & tested | `src/bp/product/income_statement.py`, `_solve_given_balances` |
| EPS (basic + diluted) | built & tested | `src/bp/product/statements.py` (`_solve_eps`) |
| Reader seams (period model, distinct expense lines, account-name extraction, partition grounding, one chart) | **closed** — 7 of 7 measured | `src/bp/statement_period.py`, `src/bp/statement_chart.py`, `src/bp/statement_extract.py`, `src/bp/product/statements.py` |
| Deterministic transaction narratives | built & tested | `src/bp/statement_detect.py` |
| **Comprehensive computation engine (Sections A–K)** | **built, wired, tested — with a thin vocabulary in front of it (§3)** | **`src/bp/product/financial_computations.py`** |
| **Reconstruction engine (Tip 5 Type 2)** | **built, wired, tested** | **`src/bp/product/reconstruction.py`** |
| **Error correction engine (Tip 5 Type 4)** | **built, wired, tested** | **`src/bp/product/error_correction.py`** |
| **Integrated case solver (Tip 5 Type 7 / Tip 6)** | **built, wired, tested — nine-stage state machine** | **`src/bp/case_solver.py`** |
| **Guards G1–G22 (Tip 7)** | **built, wired into every record** | **`src/bp/guards.py`** |

**Build:** 1.121 (see `docs/CHANGELOG.md`) · **Branch:** `corpus/merge-v1`
**Repo:** `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline`

### What the engine can actually do — measured

The engine carries **128 computation specs across 11 sections (A–K)**. Its *formulas* are complete; its *vocabulary* is
not. Of the 218 distinct input names the specs declare:

| an input can be supplied by | how many |
|---|---|
| a pattern in the text (`COMMON_PATTERNS`) | **44** |
| another spec's output (so it is reachable once the sections share a pool) | **50** |
| **nothing at all** | **131** |

So of the 128 specs, **56 have every input reachable**, 29 have some, and **43 have no reachable input at all**. The
engine is a catalogue of formulas with a thin vocabulary in front of it. It computes what it can and **names the rest
as gaps** — it never fills one. Closing the vocabulary is the next increment's bill (§5.3), not a claim this manual
makes.

### What was wrong with the engine, and what it cost

The engine was built in one pass and had **no test module at all**, so every claim about it was a claim about the
source rather than about its behaviour. Four defects, none of them visible from reading the code, all four now fixed
and now covered by `tests/test_financial_computations.py`:

1. **One spec was labelled "Peso/Dollar Change."** A home-currency name in a product that must stay global (B-177).
   It is now `e_horizontal_change` / "Horizontal Change (absolute)".
2. **Eight input patterns captured a word instead of the number** — `gain on (disposal|sale)` captured `disposal`, so
   the figure was silently dropped. All eight now capture the number.
3. **The topological sort resolved nothing.** It looked dependencies up by spec **id** while `depends_on` names
   **output names**, so the order was left as the registration order — and four specs whose producer is registered
   after its consumer recorded a gap for a value the engine had already computed.
4. **Values did not travel between sections.** Seventy-two specs depend on a value another section produces, and
   every one of them recorded a gap for something already known. The sections are now computed in dependency order
   over one shared pool.

A fifth defect was found while re-measuring the tile, and it was in the tile rather than the engine: **the engine
answered with a sheet of gaps.** `_solve_financial_computations` returned a record even when it had computed nothing,
so it hijacked the route in front of the model reader. **A route that computes nothing does not answer the question**;
it now hands the instruction back.

And a sixth, in the router: **a trial balance that also asked for ratios did not keep its route.** The
balance-sheet-analysis engine reads the same figures as *balances*, so it ignored the contra accounts — total assets
**86,900** where the trial-balance route prints **77,900** — and it hid the income statement. A trial balance is a
trial balance even when the student also asks for ratios; the more specific reading wins.

---

## 3. What the computation engine covers

The engine in `src/bp/product/financial_computations.py` implements **128 computation specs across 11 sections (A–K)**
from `Financial_Statement_Computations.docx` (the file on `C:\Users\Roderick\Desktop`). Every spec carries: id, section,
label, formula, input variables, output name, compute function, description, and dependency list.

### Section A — Statement of Comprehensive Income (18 specs)
| Spec id | Label | Formula | Depends on |
|---------|-------|---------|------------|
| `a_net_sales` | Net Sales | Gross Sales − Returns − Discounts − Allowances | — |
| `a_net_purchases` | Net Purchases | Purchases + Freight-In − Returns − Discounts | — |
| `a_goods_available` | Goods Available for Sale | Beg. Inventory + Net Purchases | net_purchases |
| `a_cogs_merch` | COGS (Merchandising) | Beg. Inv. + Net Purchases − End. Inv. | net_purchases |
| `a_cogs_manufactured` | COGM | DM Used + DL + FOH + Beg. WIP − End. WIP | direct_materials_used |
| `a_cogs_manuf` | COGS (Manufacturing) | Beg. FG + COGM − End. FG | cogs_manufactured |
| `a_direct_materials_used` | Direct Materials Used | Beg. Mat. + Purchases + F-In − End. Mat. | — |
| `a_gross_profit` | Gross Profit | Net Sales − COGS | net_sales, cogs_merch |
| `a_total_opex` | Total Operating Expenses | Selling + G&A | — |
| `a_operating_income` | Operating Income (EBIT) | Gross Profit − Total OpEx | gross_profit, total_opex |
| `a_income_before_tax` | Income Before Tax | Op. Income + Other Inc − Other Exp − Interest | operating_income |
| `a_current_tax` | Current Income Tax Expense | Taxable Income × Tax Rate | — |
| `a_total_tax` | Total Income Tax Expense | Current + Deferred | current_tax |
| `a_income_continuing` | Income from Continuing Operations | Pre-tax − Total Tax | income_before_tax, total_tax |
| `a_net_income` | Net Income | Continuing ± Discontinued | income_continuing |
| `a_basic_eps` | Basic EPS | (NI − Pref. Div.) ÷ Weighted Avg Shares | net_income |
| `a_diluted_eps` | Diluted EPS | (NI − Pref. Div. + After-Tax Conv. Interest) ÷ (Shares + Potential) | net_income, basic_eps |
| `a_ebitda` | EBITDA | NI + Interest + Taxes + D+A | net_income, total_tax |

### Section B — Statement of Changes in Equity (16 specs)
Ending RE, Corrected Beginning RE, Cash Dividends Declared, Preferred Dividends (Cumulative), Stock Dividend, Share Capital Issued, Additional Paid-in Capital, Treasury Shares at Cost, Gain/Loss on Treasury Reissue, Stock Split Effect, Appropriated RE, Share-Based Compensation, Accumulated OCI, NCI in Equity, Total Equity, Partner's Capital Balance.

### Section C — Statement of Financial Position / Balance Sheet (28 specs)
Accounting equation check, Cash & equivalents, Adjusted bank/book balances, Net AR, Allowance (aging), Notes receivable maturity, Inventory (FIFO / WAC / Retail / Gross Profit), Lower of Cost & NRV, Prepaid expenses, PPE cost, Accumulated depreciation, Carrying value, Revaluation surplus, Intangibles net, Goodwill, Investment (equity method), Right-of-use asset, Total current assets, Total assets, Accrued liabilities, Unearned revenue, Accounts payable, Total liabilities, Working capital, Net assets, Book value per share.

### Section D — Statement of Cash Flows (13 specs)
Operating CF (indirect), Change in AR/Inventory/AP, Net cash from operating, Capex, Proceeds from sale of assets, Net cash from investing, Dividends paid, Net cash from financing, Net increase/decrease in cash, Ending cash balance, Free cash flow.

### Section E — Horizontal, Vertical & Trend Analysis (6 specs)
Horizontal change (absolute), Percentage change, Trend percentage (index), Common-size IS, Common-size BS, CAGR.

> The first of these was labelled "Peso/Dollar Change" until 2026-11-04. The product is global: USD only (B-177, B-197).

### Section F — Liquidity Ratios (5 specs)
Current ratio, Quick ratio, Cash ratio, Operating cash flow ratio, Defensive interval.

### Section G — Activity / Efficiency Ratios (10 specs)
Receivables turnover, Avg collection period, Inventory turnover, Days sales in inventory, Payables turnover, DPO, Operating cycle, Cash conversion cycle, Working capital turnover, Total asset turnover.

### Section H — Solvency / Leverage Ratios (7 specs)
Debt ratio, Equity ratio, Debt-to-equity, Equity multiplier, Times interest earned, Debt service coverage, Cash flow to debt.

### Section I — Profitability Ratios (9 specs)
Gross margin, Operating margin, EBITDA margin, Net margin, ROA, ROE, Return on common equity, DuPont 3-step, Operating expense ratio.

### Section J — Market & Investor Ratios (10 specs)
P/E, Earnings yield, Dividend yield, Dividend payout, Retention ratio, Sustainable growth rate, P/B, Market cap, Enterprise value, EV/EBITDA.

### Section K — Cash Flow Analysis & Quality of Earnings (6 specs)
Cash flow margin, Cash flow to net income, Capex ratio, Cash return on assets, Accrual ratio, Altman Z-Score.

---

## 4. Architecture

```
ComputationSpec (id, section, label, formula, inputs, output_name, compute_fn, description, depends_on)
    │
    └─► ComputationRegistry (registers all specs, indexed by section)
            │
            └─► compute_all_sections()
                    ├─ _section_order()  — the sections in dependency order
                    ├─ one shared pool of computed values
                    └─► compute_section(section, raw_inputs, registry, pool)
                            ├─ topological sort (by output name, then spec id)
                            ├─ gather inputs from raw_inputs ∪ the shared pool
                            ├─ compute or record a gap (missing input named, never filled)
                            └─ return ComputationPack (results + gaps + formula_map)
```

### Key invariants (non-negotiable)
- **No invented numbers.** If an input is missing, it is recorded as a gap; the computation is not performed.
- **No guessed figures.** Every output traces to declared inputs or previously computed outputs.
- **Dependency-ordered, in a section and across sections.** A dependency may name an output name or a spec id; both are
  resolved, and a value produced in one section reaches the next.
- **A route that computes nothing does not answer.** The engine hands the instruction back rather than returning a
  sheet of gaps.
- **Stdlib only.** `re`, `dataclasses`, `decimal`, `typing` — nothing else at runtime.

---

## 5. What remains to be built

These items are named in `TIPS_FINANCIAL_STATEMENTS.md` §Tip 5 (§Tip 5 problem types), §Tip 6 (state machine), §Tip 7
(22 guards), and in `STATEMENTS_TILE_PLAN.md` §15 (out of scope):

### 5.1 Error correction engine (Tip 5 Type 4) — **BUILT** (build 1.119)

`src/bp/product/error_correction.py`. Six registered patterns (equipment expensed, unearned revenue,
depreciation omitted, ending inventory overstated, accrued expense omitted, capex charged to repairs)
each declare the correcting debit/credit and the signed effect on net income, assets, liabilities and
equity; `correct_stated(original, correct)` handles a stated original-vs-correct pair. A missing amount
is a named gap. The tile route is `_solve_error_correction`. What remains: more patterns — the set is
the six an examiner is most likely to write, not every error.

### 5.2 Integrated case solver (Tip 5 Type 7 / Tip 6 state machine) — **BUILT** (build 1.119)

`src/bp/case_solver.py`. The nine-stage machine INGEST → PARSE → DETECT → RESOLVE → JOURNALIZE → POST →
ADJUST → PROJECT → VALIDATE, with every stage recorded and the first refusal naming what it expected.
The deterministic template layer supplies the journal; `statement_plan.build` supplies the projection and
the articulation gate. The tile route is `_solve_case`; the record carries `stage_trace`.

The six reader seams the previous version of this manual named are closed (measured by
`qa/manual/reader-seams-probe.py`), and two detector gaps were closed while proving the engine:
`sold goods for X cash` was matched as an asset disposal (crediting PPE) and is now `goods_sale_cash`;
a bare `started the business with X cash` had no detector and is now `capital_contribution`.

What is still open on Type 7: the **policy layer** (a `balances` key in the extract contract, and the
timing rules in `src/bp/timing.py` that the model currently guesses at), and the **coverage-based
classifier** — see the discussion notebook's Increment 2 and Increment 3.

### 5.3 The engine's vocabulary — **CLOSED** (build 1.120)

Every **raw input** the 128 specs declare (168 distinct names that are never another spec's
output) now has a parse pattern in `COMMON_PATTERNS`.  The extended vocabulary is in
`_EXTRA_PATTERNS` with a `_p()` helper that builds a word-bounded `label [of|is|was|:] amount`
pattern.  A rich sample ("beginning inventory 10,000 … depreciation expense 3,000 … dividends
declared 5,000 … number of years 5") parses all of them.  Two false-positive traps were found
and fixed while proving it: `depreciation_expense` no longer reads "accumulated depreciation",
and `payments` no longer reads "repayments".  The 42 inputs that are *outputs* of another spec
(capex, gross profit, ebitda) are computed, not parsed — that is correct, not a gap.

### 5.4 Reconstruction engine (Tip 5 Type 2) — **BUILT** (build 1.119)

`src/bp/product/reconstruction.py`. Linear identities solve for any variable; ratio identities solve for the
ratio, the numerator or the denominator; `solve_all` chains solved values across relations. It covers
COGS, net sales, net purchases, gross profit, net income, A = L + E (capital as the balancing figure),
ending RE rollforward, working capital, CFO and the common ratios (current, quick, cash, debt, equity,
gross/net margin, ROA, ROE, ROCE, inventory/asset turnover, times interest, book value). `cross_check`
looks for a second relation that agrees. The tile route is `_solve_reconstruction`. What remains: more
relations — the set is the identities Tip 5 and the computation document name, not every identity.

### 5.5 Request detection / problem-type classification — **BUILT** (build 1.120)

`src/bp/product/problem_type.py` classifies a problem into one of Tip 5's seven types and the
record carries the verdict as `tip5_type`. The order is specific-to-general: correcting an error
(4), an explicit missing raw figure (2), ratio analysis (3), any other reconstruction (2), trial
balance (6), cash-flow statement (5), integrated case (7, three or more transaction cues),
preparing from transactions (1). A text no cue matches is `type=None`, never a guess.

### 5.6 Guards G1–G22 (Tip 7) — **BUILT** (build 1.119)

`src/bp/guards.py`. One runner over all 22 guards, reporting pass/fail/not-applicable for each. The
correctness guards (G1–G9, G13, G18, G21) block the record; the trust and extraction guards are recorded
for the audit trail. Injected from `bp.server` so the product package imports no core module. Every record
carries `record["guards"]`.

### 5.7 What is genuinely still open

- **The policy layer** (§5.2): a `balances` key was added to the extract contract and converted to
  an opening entry (`to_opening`), so a problem that states opening balances separately is read. The
  timing rules the model guesses at (a `provenance` tag per policy) are the remaining piece.
- **A live model key:** the reader needs OpenCode Go credentials. `bp.server` now loads them from
  `Backend/.env` (`OPENCODE_API_KEY` → `BP_OPENGO_API_KEY`, `LLM_PROVIDER` → `BP_LLM_PROVIDER`,
  `PROSE_MODEL` → `BP_LLM_MODEL`) when the `BP_*` names are unset, so live mode works without a
  manual export. Proved with a live extraction: a grant-and-van narrative returned 50,000 other
  income, assets 50,000, 11/11 checks.

---

## 6. Commands

### Run the statements tests
```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python -m unittest tests.test_product_statements tests.test_product_statements_api tests.test_product_statements_tile tests.test_product_statements_council tests.test_product_boundary -v
```

### Run the reader, plan and engine tests
```powershell
python -m unittest tests.test_statement_plan tests.test_statement_detect tests.test_statement_detect_contract tests.test_statement_reader_seams tests.test_financial_computations -v
```

### Run the full suite
```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests
# Expect "OK" line. pwsh may print [exit code: 1] from ResourceWarnings — read the OK line, not the exit code.
# PYTHONPATH matters. Without it the first test module imported fails with "ModuleNotFoundError: No module named
# 'bp'", its 8 tests never run, and the suite reports "Ran 3821 tests" instead of "Ran 3828 tests".
```

### Compare a working tree against HEAD (the step-7 measurement)
```powershell
# 1. build the two baseline trees, snapshot the working tree, run the suite in all three
powershell -File qa/manual/suite_measure.ps1 -Pre d938095 -Head f1bb0c5
# 2. prove each copy is byte-exact to its commit: its git tree hash against the commit's own tree hash
python qa/manual/suite_treehash.py D:\SMART BUSINESSWRITER D:\SMART BUSINESSWRITER\.baseline_pre\x d938095
python qa/manual/suite_treehash.py D:\SMART BUSINESSWRITER D:\SMART BUSINESSWRITER\.baseline_head2\x f1bb0c5
# 3. separate the pre-existing failures from the new ones
python qa/manual/suite_compare.py qa/baseline/seam-suite-comparison.txt
```
```

### Start the workbench
```powershell
python -m bp.server 8000
# Workbench at http://127.0.0.1:8000
```

### Measure the reader's seams
```powershell
python qa/manual/reader-seams-probe.py
```

### Re-measure the owner's case
```powershell
python qa/manual/ashgrove-remeasure.py
```

### Quick EPS smoke test
```powershell
python -c "
from bp import methods
import bp.product.statements as ps
ps.attach_core(
    solve=lambda spec: methods.LIBRARY['management_accounts'].impl({'spec': spec}),
    diagnose=lambda rows, places: methods.LIBRARY['trial_balance_check'].impl({'journal': None, 'trial_balance': rows, 'places': places}),
    reader=None, extract=None,
    build=lambda plan: methods.LIBRARY['management_accounts'].impl({'spec': plan}),
)
text = '''Rowan plc reports profit from continuing operations 1,000 and loss from discontinued operations 200. It has: ordinary shares opening 1,000; bonus issue 1-for-5 during the year; preference dividends 50; share options 100 with exercise price 5 and average market price 10; convertible bonds 500 at 6%, convertible into 100 ordinary shares; tax rate 25%.'''
r = ps.solve(text)
print(r['statements']['income_statement'])
print('basic_eps:', r['core']['scalars']['basic_eps'])
print('diluted_eps:', r['core']['scalars']['diluted_eps'])
"
```

### Quick financial-computations smoke test
```powershell
python -c "
from decimal import Decimal
from bp.product.financial_computations import compute_section, REGISTRY
pack = compute_section('F', {'current_assets': Decimal('50000'), 'current_liabilities': Decimal('20000')})
print('current_ratio:', pack.results['current_ratio'].value)
print('gaps:', pack.gaps)
"
```

---

## 7. Test contract

| Module | What it verifies |
|--------|-----------------|
| `tests/test_financial_computations.py` | The engine: 128 specs in 11 sections, the ordering, the shared pool, the gap that is named rather than filled, the global-product rule |
| `tests/test_statement_reader_seams.py` | The seven reader seams, end to end: period, comparative, distinct expense lines, account-name extraction, partition grounding, the one chart |
| `tests/test_product_statements.py` | Request contract: compute scope vs output scope, `requested`/`computed`/`hidden`, `verify_output()`, one-statement export |
| `tests/test_product_statements_api.py` | POST/GET/export routes, boundary (no `bp.*` imports in product package) |
| `tests/test_product_statements_council.py` | Council: advocate → verifier → examiner, grounding, same-model disclosure |
| `tests/test_product_statements_tile.py` | Tile UI affordances (design lane) |
| `tests/test_product_boundary.py` | Product package imports no core module |
| `tests/test_statement_plan.py` | Plan layer: chart, policy, adjustment DAG, articulation gate, golden engagement |
| `tests/test_statement_detect.py` | The detector layer: the wordings it reads, and the named failure when a detection carries no amount |
| `tests/test_statement_detect_contract.py` | The detector layer's contract with the plan layer |
| `tests/test_statements_render_contract.py` | Render contract: workbook from frozen record, no invented figures |
| `tests/xlsx_read.py` | Read-back harness for workbook cells |

### The baseline, measured (2026-11-05)

**The full suite, run three ways on pinned trees.** A copy of a commit is byte-exact when its git tree hash equals that
commit's own tree hash; `qa/manual/suite_treehash.py` makes that check, and `qa/manual/suite_measure.ps1` builds each
copy and runs the suite in it.

| tree | what it is | result |
|---|---|---|
| the pre-increment baseline | a byte-exact copy of `d938095` ("build 1.98: detector/runtime layer wired") | **3784 tests, 25 failures, 40 errors** |
| the current HEAD | a byte-exact copy of `f1bb0c5` | **3828 tests, 27 failures, 38 errors** |
| the working tree | a snapshot of it, measured in the snapshot so a second session cannot move the numbers | **3828 tests, 27 failures, 38 errors** |

The earlier version of this manual claimed "3784 tests, 2 pre-existing failures only". That was wrong: the suite was
measured on a tree that was not HEAD, and 59 problems went uncounted. The pre-existing problems fall into these groups:

| group | count | note |
|---|---|---|
| the plan layer's golden engagements (bad debt, OCI, revaluation, disposal, deferrals, depreciation methods) | 40 errors | all with one root cause: `EngagementError: chart[11]: duplicate account code 1100`. The helpers build an engagement from the `accounts` preset and **append** `1100 Trade receivables` to its chart; the preset's chart now carries that account already, so the append duplicates it. A stale test helper, not a product defect — and older than this increment: `src/bp/server.py` and `src/bp/accounts.py` are unchanged by it |
| the product-boundary and committed-slice tests | 5 failures | another lane's `subjects.py` edit |
| `test_the_served_build_is_the_newest_changelog_build` | 1 failure | `bp/build.py` said 1.97 while the changelog's newest was 1.98 |
| the calculator, forecast and product-package tests | 4 failures | another lane, and one network test |

The two failures this manual used to name are real — `test_ratios_are_computed_only_when_the_instruction_asks` and
`test_the_statements_modules_import_no_frozen_core_module` — but they are two of sixty-three, not two of two.

**Against the pre-increment baseline: of the 63 tests that fail in the working tree, 58 are pre-existing, 5 are fixed
by this increment, and 5 are new.** The five fixed are the detector's `decimal.InvalidOperation` crash (two tests), the
runtime's ok-path, the detector contract, and the served build number. **This increment adds 44 tests and five new
failures**, and the five are named in `docs/OPEN_ISSUES.md` (Item 18):

| new failure | why | what would close it |
|---|---|---|
| `test_product_boundary.ProductBoundaryTest.test_the_product_package_imports_only_the_standard_library`, `...never_imports_the_frozen_core`, `test_product_statements_api.RouteTest.test_the_statements_modules_import_no_frozen_core_module` | `src/bp/product/statements.py:1084` imports `bp.product.income_statement` absolutely, and the boundary rule reads any `bp.`-prefixed import as the product reaching into the frozen core | one line: `from .income_statement import parse_problem as _isp_parse` — the rule ignores relative imports, and that module already uses them at its lines 31-32 |
| `test_product_subjects.ServedUiContractTest.test_the_keypad_is_off_for_list_and_worksheet_tools` | `e4184a8` changed the calculator's fit rule so `management_accounts` is no longer forced to the no-keypad path; the committed test still asserts the old line | restore the special case, or update the committed test — the second is editing the verifier to get green, so it is the owner's call |
| `tests.test_statement_reader_seams.RouteTest.test_a_route_that_computed_nothing_does_not_answer` | this increment's own new test: it passes alone and fails in the suite, because `bp.server` wires the product module and a wired module answers that instruction instead of refusing | decide what the route does in the shipped configuration, and assert that |

**Against the current HEAD the working tree changes nothing: 0 new, 0 fixed.** The full separation is in
`qa/baseline/seam-suite-comparison.txt`.

---

## 8. Non-negotiables (from CONDUCTOR_MANUAL.md + DATABASE.md + CONTRIBUTORS.md)

1. **No invented evidence, sources, numbers or citations.** Gaps are named, never guesses.
2. **No model-authored figures.** A model may propose; code computes every number.
3. **Stdlib only at runtime** (`sqlite3`, `urllib`). Build tools may use `pypdf`.
4. **Product layer may not import `bp.*` core modules** — `test_product_boundary` enforces.
5. **Global product: USD only.** No PHP/PSE/PSEi/Philippine references (B-177, B-197). The engine's labels are covered
   by a test, so this cannot drift back in.
6. **Every figure traceable to source text.** Detectors/templates carry quotes; no hallucination (G20).
7. **Every gate fails loudly with root-cause diagnostics; no auto-correction** (G9, G11).
8. **One document per work — never ingest the same document twice.**
9. **Corpus R2 bucket stays private — no `r2.dev` subdomain.**

---

## 8A. The four engines built in this increment

These four capabilities close the "handle any financial-statement problem" gap without a model for the
cases that a relation or a declared error can answer. Every one is deterministic, uses `Decimal`, and
names a gap rather than inventing a figure.

### 8A.1 Reconstruction engine (Tip 5 Type 2) — `src/bp/product/reconstruction.py`

Solves a missing figure from a stated relation. Two relation shapes:

- **linear** (`a = b + c − d`), solved for any variable by moving terms;
- **ratio** (`ratio = numerator / denominator`), solved for the ratio, the numerator or the denominator.

`solve_for(target, knowns)` returns the first relation that reaches the target, with the formula and the
knowns it used. `solve_all(knowns)` chains solved values across relations, so `cogs` feeds `gross_profit`
feeds `gross_margin` in one pass. `cross_check(target, knowns)` looks for a second relation that agrees.

The tile route is `_solve_reconstruction` in `statements.py`; detection is
`reconstruction.detect_reconstruction_problem` (a "find/compute/determine/what is" cue plus a named
variable). A target no relation can reach is a gap, never a guess.

### 8A.2 Error correction engine (Tip 5 Type 4) — `src/bp/product/error_correction.py`

Detects a wrong entry and builds the correcting entry plus its effect on the statements. Two modes:

- **pattern**: the text says "X was expensed instead of capitalised" and a registered `ErrorPattern`
  supplies the declared correcting treatment (debit/credit accounts and the signed effect on net income,
  assets, liabilities, equity). Six patterns: equipment expensed, unearned revenue, depreciation omitted,
  ending inventory overstated, accrued expense omitted, capital expenditure charged to repairs.
- **stated**: the problem gives the original and correct entries; `correct_stated` computes
  `correct − original`.

The amount is parsed from the text; a missing amount is a named gap. The tile route is
`_solve_error_correction`; detection is `error_correction.detect_error_problem` (a correction cue plus a
matching pattern).

### 8A.3 Integrated case solver (Tip 5 Type 7 / Tip 6) — `src/bp/case_solver.py`

Runs one case problem through the explicit nine-stage state machine:

```
INGEST -> PARSE -> DETECT -> RESOLVE -> JOURNALIZE -> POST -> ADJUST -> PROJECT -> VALIDATE
```

Each stage records its outcome; the first stage that refuses returns a `CaseResult` with `status="review"`
and names what it expected. The deterministic template layer (`statement_detect`) supplies the journal;
`statement_plan.build` supplies the projection, the adjustment DAG and the articulation gate. The tile
route is `_solve_case`; the record carries a `stage_trace` array so the reader can see every stage.

Two detector gaps were found and closed while proving it: `sold goods for X cash` was matched as an
**asset disposal** (it credited PPE); it is now a `goods_sale_cash` detector. A bare
`started the business with X cash` had no detector at all; it is now `capital_contribution`. `paid rent
of X` now matches `rent_payment2`.

### 8A.4 Guards G1–G22 (Tip 7) — `src/bp/guards.py`

One runner over the frozen record. Every guard has a stable id and reports `ok`, `applicable` and a
`detail`. A guard that cannot run is `applicable=False`, never a silent pass; a guard that raises is
`ok=False`. The runner is injected from `bp.server` as `_core("guards")`, so the product package never
imports the core.

The **blocking** guards are the correctness and cross-reconciliation ones (G1–G9, G13, G18, G21): a
failure there refuses the record. The trust and extraction guards (G10–G12, G14–G17, G19–G20, G22) are
recorded for the reader and the audit trail but do not block. The full verdicts travel with every record
under `record["guards"]`.

The guards are pinned in `tests/test_financial_engines.py`, together with the reconstruction, error
correction and case-solver contracts (27 tests).

---

## 9. Pick-up order (if this session is cut off)

1. Read `docs/TIPS_FINANCIAL_STATEMENTS.md` §Tip 5 (§problem types), §Tip 6 (state machine), §Tip 7 (guards).
2. Read `docs/STATEMENTS_TILE_PLAN.md` §1 (deliverable is type-dependent), §15 (out of scope), §16 (traps).
3. Re-read this manual §5 (what remains) and pick one item.
4. Build one increment: tests + `CHANGELOG.md` + `WORKLOG.md` entry + `DECISIONS.md` B-number if a convention is chosen.
5. Run the full suite **on HEAD and on the working tree**, and report the true count and the separation.
6. Commit with a message stating what changed, what verifies it, and the test count.

---

## 10. Cross-references

- **Source computation document:** `C:\Users\Roderick\Desktop\Financial_Statement_Computations.docx` (198 computations, sections A–K)
- **Engine module:** `src/bp/product/financial_computations.py`
- **Problem-type classifier:** `src/bp/product/problem_type.py` (Tip 5 Types 1–7)
- **Reconstruction engine:** `src/bp/product/reconstruction.py` (Tip 5 Type 2)
- **Error-correction engine:** `src/bp/product/error_correction.py` (Tip 5 Type 4)
- **Integrated case solver:** `src/bp/case_solver.py` (Tip 5 Type 7 / Tip 6 state machine)
- **Guards runner:** `src/bp/guards.py` (Tip 7, G1–G22)
- **Live credentials loader:** `src/bp/server.py` (`_load_opencode_env`, maps `Backend/.env` names to `BP_*`)
- **Reader layer:** `src/bp/statement_period.py` (one period model), `src/bp/statement_chart.py` (one chart), `src/bp/statement_detect.py` (deterministic transactions), `src/bp/statement_extract.py` (the model boundary and the grounding rule), `src/bp/statement_plan.py` (the plan layer)
- **Tile wiring:** `src/bp/product/statements.py` (`_solve_financial_computations`, `_solve_eps`, `_solve_income_statement`, `_solve_balance_sheet_analysis`, `_solve_given_balances`)
- **Measurements:** `qa/manual/reader-seams-probe.py`, `qa/manual/ashgrove-remeasure.py`, `qa/manual/statements-case-study.md`
- **TIPS manual:** `docs/TIPS_FINANCIAL_STATEMENTS.md`
- **Tile plan:** `docs/STATEMENTS_TILE_PLAN.md`
- **UI handoff:** `docs/HANDOFF_STATEMENTS_TILE.md`
- **General handoff:** `docs/HANDOFF.md`
- **Conductor manual:** `docs/CONDUCTOR_MANUAL.md`
- **Contributors (lane split):** `docs/CONTRIBUTORS.md` §1A/§1B
- **Backend contract:** `docs/BACKEND_CONTRACT.md` §3 (unfreeze policy, frozen core)
- **Known limitations:** `docs/KNOWN_LIMITATIONS.md`
- **Product gap map:** `docs/PRODUCT_GAP_MAP.md`
- **Discussion notebook:** `docs/DISCUSSION_NOTEBOOK.md` (the plan this manual's §5 follows)
- **Work log:** `docs/WORKLOG.md`
- **Changelog:** `docs/CHANGELOG.md`

---

*End of manual. Update §1–§5 on every increment; keep it current with the code.*
