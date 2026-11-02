# Acceptance manual — `entrepreneurship` shelf

**Session 6 of 11.** Branch `corpus/merge-v1`, opening commit `b2987fc`. Build 1.68.
Every row below cites a source of truth; nothing here is opinion. The measured evidence this
manual is built from is in `qa/baseline/` and `qa/evidence/entrepreneurship/`, produced by the
probes named in the table.

| Evidence file | What it measures |
|---|---|
| `qa/baseline/ent_catalogue.json` | `subjects.detail("entrepreneurship")` verbatim (46 tools, 5 worksheets, 6 records) |
| `qa/baseline/ent_shelf.txt` / `.json` | `python qa/probe_ent_shelf.py` — every tool through its own preset: delivery, checks, determinism, units |
| `qa/baseline/ent_mapping.txt` | `python qa/probe_ent_mapping.py` — a plan block's columns through `bp.ingest.to_method_inputs` |
| `qa/baseline/ent_plan.txt` | `python qa/probe_ent_plan.py` — the plan and the deliverable, with the V-01…V-20 verdicts |
| `qa/evidence/entrepreneurship/business-plan.docx` | the paper, produced through `chat` (with a rubric attached) |
| `qa/evidence/entrepreneurship/business-plan-no-rubric.docx` | the same plan with no marking guide, for the "unchanged" comparison |
| `qa/evidence/entrepreneurship/computation-submission.docx` / `computation-workpapers.xlsx` | the computation deliverable, through `deliverables.check_pair`/`write_export` |
| `qa/evidence/entrepreneurship/validation.md` | each V-rule, judged, with the evidence beside it |
| `qa/baseline/ent_suite_err.txt` | the Phase 0 suite run: **2932 tests, 66 failures, 13 errors** — the documented opening state |

Source ranks used in this manual (work order §1–§3):

1. `bp.methods.LIBRARY[id]` + `bp.server.PRESETS` + `tests/fixtures/frozen_contract.json` — exact contract.
2. `docs/sources/Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md` — what a method is for (read only).
3. `docs/CONDUCTOR_MANUAL.md` §4/§7/§8 + `docs/VALIDATION_HARNESS.md` §5 (V-01…V-20) — paper and export rules.
4. `bp.product.chat` — the plan profile, its blocks, its gate (`PLAN_*`, `COMPUTATION_BLOCKS`).
5. `subjects.SUBJECT_DEFS` / `detail()` — the student-facing promise.
6. `docs/ENTREPRENEURSHIP_STUDENT_GUIDE.md`, `docs/CURRICULUM_MAP.md`, `docs/KNOWN_LIMITATIONS.md` — teaching intent and declared limits.
7. existing tests — executable intent.

---

## 1. Who it serves

Source: `docs/CURRICULUM_MAP.md` row *Entrepreneurship* (rank 6),
`docs/ENTREPRENEURSHIP_STUDENT_GUIDE.md` (rank 6), `subjects.detail("entrepreneurship")` (rank 5).

| Course | Level | What the shelf must survive |
|---|---|---|
| Entrepreneurship | SHS (ABM) | a feasibility argument: market size, price, break-even, cash, capital |
| New Venture Creation | UG1–2 | the same plus a business plan with projected statements, funding and a return |

The shelf declares two disciplines (`detail["disciplines"]`): *strategy* and *marketing and
customers*. The student-facing promise (`summary`) is: *"Test a venture idea: market size, price,
break-even, cash and the capital it needs."* The guidance line says the shelf **follows the
sections of a business plan** and that each tile opens one frozen method, nothing calculated
until the student supplies and confirms their own figures.

## 2. Scope and non-goals — promises to test, not bugs

Source: `subjects.detail("entrepreneurship")["does_not"]` (rank 5), `CURRICULUM_MAP` *Named gaps*
(rank 6), `KNOWN_LIMITATIONS.md` §"Added with the entrepreneurship shelf" and §"Business-plan
profile" (rank 6), `PRODUCT_GAP_MAP.md` §C (rank 6).

`does_not` — three declared non-goals, each an E-row (§8):

1. *"It does not invent a market size, price, cost or growth rate."*
2. *"It does not raise the capital, validate the idea or guarantee a return."*
3. *"It does not replace a customer interview or a real market test."*

`CURRICULUM_MAP` named gaps for this shelf: *term sheets, liquidation preference, anti-dilution,
multi-round cap tables, conjoint, survival models, Monte Carlo.* These are GAP rows (G-ent-01…),
never expectations.

Out of scope by the work order: the parked queue (`docs/PARKED_QUEUE.md`), the REW stages, a
jurisdiction tax engine, and anything the owner has not ratified.

---

## 3. Compute tools — one row per tool

Source: `bp.methods.LIBRARY[tool.method]` and `bp.server.PRESETS[tool.preset]` (rank 1), the
catalogue row each tool cites (rank 2), `subjects.detail` (rank 5). Tier, headline metric, unit
and claim ceiling are read from the method contract, never restated from memory.
`python qa/probe_ent_shelf.py` measured every row: **46 of 46 deliver through their own preset,
every one of the method's own checks passes, and two runs of the same request are identical.**
(The same probe measured 43 of 46 before this session — D-ENT-04.)

| # | Tool | Method | Tier | Headline metric / unit | Claim ceiling | Required inputs | Preset |
|---|---|---|---|---|---|---|---|
| E-ent-011 | `marketsize` | `market_sizing` | T1 | serviceable_obtainable_market / currency | descriptive | `target_population`, `annual_spend_per_customer`, `serviceable_share`, `obtainable_share` | `marketsize` |
| E-ent-012 | `forecast` | `trend_forecast` | T1 | forecast_1 / @unit | predictive | `values` | `forecast` |
| E-ent-013 | `demandcurve` | `demand_curve` | T1 | slope / ratio | associational | `prices`, `quantities` | `demandcurve` |
| E-ent-014 | `purchaseintent` | `purchase_intent` | T1 | intent_rate / rate | descriptive | `definitely`, `probably`, `maybe`, `never` | `purchaseintent` |
| E-ent-015 | `funnel` | `sales_funnel` | T1 | overall_conversion / rate | descriptive | `stages` | `funnel` |
| E-ent-016 | `cohort` | `cohort_retention` | T1 | average_retention / rate | descriptive | `cohort_sizes`, `retained` | `cohort` |
| E-ent-017 | `concentration` | `market_concentration` | T1 | hhi / ratio | descriptive | `firm_revenues` | `concentration` |
| E-ent-018 | `elasticity` | `elasticity` | T1 | price_elasticity / ratio | descriptive | `quantity_1`, `price_1`, `quantity_2`, `price_2` | `elasticity` |
| E-ent-019 | `descriptive` | `descriptive_stats` | T1 | mean / from_request | descriptive | `values` | `descriptive` |
| E-ent-020 | `chi_square` | `chi_square` | T1 | cramers_v / ratio | associational | `table` | `chi_square` |
| E-ent-021 | `power` | `power_analysis` | T1 | power / probability | descriptive | `design`, `effect`, `n1`, `sd1` | `power` |
| E-ent-022 | `pricing` | `pricing_decision` | T1 | cost_plus_price / currency | descriptive | `unit_cost`, `expected_units`, `markup_rate` | `pricing` |
| E-ent-023 | `breakeven` | `breakeven` | T1 | breakeven_units / units | descriptive | `fixed`, `price`, `variable` | `breakeven` |
| E-ent-024 | `multibreakeven` | `multi_product_breakeven` | T1 | breakeven_total_units / units | descriptive | `fixed_costs`, `products` | `multibreakeven` |
| E-ent-025 | `unitecon` | `unit_economics` | T1 | unit_margin / currency | descriptive | `price`, `variable_cost`, `acquisition_cost` | `unitecon` |
| E-ent-026 | `costcurves` | `cost_curves` | T1 | average_cost / currency | descriptive | `fixed_cost`, `linear_cost`, `quadratic_cost`, `quantity` | `costcurves` |
| E-ent-027 | `marketpower` | `market_power` | T1 | lerner_index / ratio | descriptive | `price`, `marginal_cost` | `marketpower` |
| E-ent-028 | `capacity` | `capacity_analysis` | T1 | max_output / units | descriptive | `resources` | `capacity` |
| E-ent-029 | `inventory` | `inventory_policy` | T1 | economic_order_quantity / units | descriptive | `annual_demand`, `order_cost`, `holding_cost_per_unit`, `lead_time_days` | `inventory` |
| E-ent-030 | `frommarket` | `sales_from_market` | T1 | target_revenue / currency | descriptive | `market_size`, `target_share`, `price` | `frommarket` |
| E-ent-031 | `proforma` | `proforma_statements` | T1 | total_net_income / currency | descriptive | `revenue`, `gross_margin_rate`, `operating_costs`, `depreciation` | `proforma` |
| E-ent-032 | `sensitivity` | `sensitivity_table` | T1 | base_profit / currency | descriptive | `base_price`, `base_units`, `base_variable_cost`, `base_fixed_cost`, `price_changes`, `volume_changes` | `sensitivity` |
| E-ent-033 | `ratios` | `ratio_analysis` | T1 | n_computed / count | descriptive | *(none required)* | `ratios` |
| E-ent-034 | `depreciation` | `depreciation_schedule` | T1 | total_depreciation / currency | descriptive | `cost`, `life` | `depreciation` |
| E-ent-035 | `salesprojection` | `sales_projection` | T1 | total_profit / currency | descriptive | `start_units`, `price`, `unit_variable_cost`, `fixed_cost_per_period` | `salesprojection` |
| E-ent-036 | `startupcapital` | `startup_capital` | T1 | amount_to_raise / currency | descriptive | `start_up_costs`, `working_capital` | `startupcapital` |
| E-ent-037 | `cashrunway` | `cash_runway` | T1 | runway_months / units | descriptive | `opening_cash`, `monthly_net_cash_flow` | `cashrunway` |
| E-ent-038 | `roi` | `return_on_investment` | T1 | roi / rate | descriptive | `total_investment`, `net_gain` | `roi` |
| E-ent-039 | `tax` | `tax_declared` | T1 | total_tax_charge / currency | descriptive | `taxable_income`, `income_tax_rate` | `tax` |
| E-ent-040 | `npv` | `npv` | T1 | npv / from_request | descriptive | `rate`, `cashflows` | `npv` |
| E-ent-041 | `irr` | `irr` | T1 | irr / rate | descriptive | `cashflows` | `irr` |
| E-ent-042 | `dpayback` | `discounted_payback` | T1 | discounted_payback / periods | descriptive | `cashflows` | `dpayback` |
| E-ent-043 | `projectmetrics` | `project_metrics` | T1 | npv / currency | descriptive | `cashflows`, `rate` | `projectmetrics` |
| E-ent-044 | `scenario` | `scenario_analysis` | T1 | npv_base / currency | descriptive | `cashflows`, `discount_rate`, `rate_low`, `rate_high` | `scenario` |
| E-ent-045 | `trendanalysis` | `trend_analysis` | T1 | revenue_cagr / rate | descriptive | `years`, `revenue`, `cost_of_sales`, `operating_expenses`, `net_income` | `trendanalysis` |
| E-ent-046 | `workingcapital` | `working_capital` | T1 | cash_conversion_cycle / days | descriptive | `revenue`, `cost_of_sales`, `inventory`, `receivables`, `payables`, `annual_demand`, `order_cost`, `holding_cost_per_unit`, `discount_percent`, `credit_terms_days`, `discount_days` | `workingcapital` |
| E-ent-047 | `captable` | `cap_table_round` | T1 | investor_pct / rate | descriptive | `pre_money_valuation`, `investment`, `founders_shares` | `captable` |
| E-ent-048 | `loan` | `loan_amortization` | T1 | payment / currency | descriptive | `principal`, `annual_rate`, `years` | `loan` |
| E-ent-049 | `dcf` | `dcf_valuation` | T2 | enterprise_value / currency | descriptive | `cashflows`, `discount_rate` | `dcf` |
| E-ent-050 | `multiples` | `multiples_valuation` | T2 | implied_equity_value / currency | descriptive | `metric`, `subject_value` | `multiples` |
| E-ent-051 | `equitybridge` | `equity_bridge` | T2 | equity_value / currency | descriptive | `enterprise_value` | `equitybridge` |
| E-ent-052 | `currency` | `currency_convert` | T1 | amount / currency | descriptive | `amount`, `from_currency`, `to_currency`, `rate` | `currency` |
| E-ent-053 | `sroi` | `sroi` | T2 | sroi_ratio / ratio | descriptive | `investment`, `benefits` | `sroi` |
| E-ent-054 | `cba` | `cost_benefit` | T2 | net_present_value / currency | descriptive | `costs`, `benefits` | `cba` |
| E-ent-055 | `costeffectiveness` | `cost_effectiveness` | T2 | n_options / count | descriptive | `options` | `cea` |
| E-ent-056 | `case_decision` | `case_decision` (template) | T2 | n/a (per alternative) | descriptive | declared in the template | `case_decision` |

### 3.1 Refusals and unit rules the shelf promises

Source: `bp.methods.LIBRARY` self-tests and `profile()` (rank 1), measured by
`qa/probe_ent_shelf.py` and the acceptance suite's `test_ent_009`, `test_ent_068`.

- An **unknown input name** is refused with the allowed list, as a `blocked` delivery, never
  dropped silently (`validate_inputs`).
- **Every method runs its own declared checks** on its preset's figures, and a failed check
  blocks the delivery. 46 of 46 pass (measured).
- `market_sizing` refuses a share outside 0–1 and a population of zero; `cash_runway` refuses a
  flow that never burns cash instead of reporting an infinite runway; `pricing_decision` shows the
  markup-on-cost and margin-on-price conventions side by side because they give different prices;
  `cap_table_round` grosses the option pool up so the declared share is the share actually held.
- `@unit` is a per-unit amount in the request's own currency; the orchestrator resolves it, so it
  is not a mislabelling (retired as a false alarm by `qa/QA_STATE.md` session 2).

## 4. The business plan — a second engine

Source: `bp.product.chat` (`PLAN_*`, `COMPUTATION_BLOCKS`, `_start_plan`, `_plan_profile`,
`_draft_plan`, `_plan_missing`) (rank 4), `docs/CONDUCTOR_MANUAL.md` §13 (rank 3),
`docs/KNOWN_LIMITATIONS.md` §"Business-plan profile (B-148)" (rank 6), `tests/test_business_plan_profile.py`
(rank 7).

A plan is a **paper profile**, not a framework. `chat.start(..., profile="business_plan")` composes
student input, retrieved evidence, plan-level computation and integration prose. Its sections are
fixed by the profile; its computations are the frozen methods called through `chat.compute`.

| Level | Blocks (in order) | Extra sections |
|---|---|---|
| `shs` | `frommarket`, `breakeven`, `depreciation`, `proforma`, `sensitivity` | — |
| `college` | the same, then `tax`, `captable`, `impact` | `funding`, `impact` |

- The plan is **composed from declared drivers, not forecast**: no demand model, seasonality,
  ramp, mix, new borrowing beyond the opening loan, dividend or disposal.
- **The opening balance sheet must balance.** An unbalanced opening is refused with the equity
  that would balance it; the product never plugs a difference (`test_ent_073`).
- Annual periods, one currency.
- Export is blocked while a required field or a required block is missing, and the refusal names
  each one (`test_ent_072`).
- The plan downloads as a real `.docx` through `POST /api/cases/chat/{id}/export`; with a recorded
  computation it ships in one ZIP with its explainer (`test_ent_074`, `test_ent_099`).
- **A marking guide the student attached travels with the plan** (B-193): the paper carries a
  `Rubric coverage` table immediately before the references, the coverage is measured on the paper
  before that table exists, and a weighted criterion the plan does not address blocks the download
  and is named there. The student may accept the gap; the decision is recorded and the table keeps
  naming it (`test_ent_075`…`test_ent_078`).

## 5. Worksheets

Source: `subjects.detail("entrepreneurship")["worksheets"]` (rank 5), `bp.templates` (rank 1),
`docs/CONDUCTOR_MANUAL.md` §6 (rank 3).

| Id | Worksheet | Template | Draftable | Shared with |
|---|---|---|---|---|
| STR-15 | Business Model Canvas | `template_business_model_canvas` | yes | management |
| STR-16 | Lean Canvas | `template_lean_canvas` | yes | management |
| STR-17 | Value Proposition Canvas | `template_value_proposition_canvas` | yes | management |
| STR-18 | SWOT evidence-to-action review | `template_swot` | yes | management |
| STR-13 | Blue Ocean four actions (ERRC) | `template_blue_ocean_errc` | **no** | management |

All five are **T4**: they place and audit the student's own evidence, reproduce it verbatim, name
every empty block and produce **no score, ranking or recommendation**. STR-13 is offered but has no
draft button, by design (the grid is audited, not written). All five are shared with the management
shelf and fixed once, filed under both (`VALIDATION_HARNESS.md` §7.1).

**The marketing plan (`MKT-02`) is not on this shelf.** It carries STP and the marketing mix, which
belongs to the marketing shelf, where it is offered and draftable; the owner assigned it there alone
(B-196). The shelf's own worksheets are the venture canvases, and the marketing mix is reached from
the Marketing shelf rather than duplicated here.

## 6. Records, theories and the glossary

Source: `subjects.CATALOGUE` as served by `detail("entrepreneurship")` (rank 5), `bp.methods.LIBRARY`
(rank 1).

Six catalogue records, all `form: computed`, and **no theory row** (a reading lens is reached by
naming it in the brief, not by clicking a tile):

| Id | Record | States what is implemented | States what is not |
|---|---|---|---|
| QNT-MKT-01 | Market sizing (TAM/SAM/SOM) with source-backed inputs and labelled assumptions | top-down TAM, SAM, SOM from a declared population, spend and two shares | bottom-up segmentation, retrieved market data, a demand estimate |
| QNT-MKT-02 | Market share, growth, penetration, conversion and funnel leakage | growth rates, market share with penetration and relative share, stage conversion | market-data retrieval, an estimated competitor, cross-channel leakage |
| QNT-MKT-03 | Cohort retention, churn, repeat purchase and lifetime | pooled cohort retention, churn, average lifetime, a single-rate LTV, a discounted LTV over a declared horizon | fitted survival curves, segment-level retention, expansion revenue |
| QNT-FIN-06 | Unit economics | contribution margin, acquisition payback, LTV/CAC | retention curves, cohort economics |
| QNT-FIN-07 | Pricing and demand | cost-plus, target-margin, break-even and target-return prices, arc elasticity between two observations | estimating a demand curve or willingness to pay |
| QNT-DEC-02 | Sensitivity, scenario, break-even thresholds and decision flip | decision-flip on the NPV discount rate and a declared low/high rate scenario | multi-input scenario analysis, Monte Carlo, expected-value decision trees |

Every worksheet record reads `worksheet available: structure and evidence audit only; the evidence
is yours`. The **34-term glossary** carries TAM, SAM, SOM, break-even point, margin of safety, CAC,
LTV, runway, ROI, cap table, dilution, funnel, cohort, purchase intent and positioning among others.

## 7. Student guidance

Source: `docs/ENTREPRENEURSHIP_STUDENT_GUIDE.md` (rank 6), `detail["start_steps"]` and
`detail["guidance"]` (rank 5).

The guide is a teaching layer, not a calculator: it names which tool answers which question, the
period convention of each (break-even and unit economics are per period; the runway is monthly;
market size is top-down and annual), and a worked example per method. The page opens with four
start steps in plan order: size and price the market, plan the cash and capital, appraise the
return, then test the venture model with unit economics and the canvases.

Measured copy ceilings (the rule pins the current terse style rather than imposing a new voice):
guidance 58 words, a tool's `what` ≤ 26, a step ≤ 20, a common mistake ≤ 23, a start step ≤ 12,
a does-not line ≤ 14 (`test_ent_010`).

## 8. Surface routing

Source: `bp.product.api` routes (rank 1), `bp.server` (rank 1), `web/index.html` (rank 5),
`bp.product.calc_router` (rank 5).

| Surface | Route / entry point | What it must do |
|---|---|---|
| Shelf page | `GET /api/cases/subjects/entrepreneurship` | 46 tools, 5 worksheets, 6 records, 0 theories, 34 glossary terms, the guidance and the three does-not lines |
| Shelf index | `GET /api/cases/subjects` | `entrepreneurship` appears with the label `Entrepreneurship` |
| Tool form | the page's schema-driven form | built from `LIBRARY[method].input_schema`; list fields as comma lists, `enum` fields as choices |
| Plan composer | `POST /api/cases/chat {profile: "business_plan"}` | proposes the plan; no source is retrieved and no figure is computed until the student confirms |
| Plan brief | `POST /api/cases/brief` | reads a pasted brief, `.txt`, `.docx`, a PDF text layer, or an image through the OCR chain; the response names the file **and the engine** and the text stays unverified |
| Marking guide | `POST /api/intake/{id}/rubric` then the plan's `rubric` field | the parsed guide travels with the run; the paper carries a coverage table |
| Plan download | `POST /api/cases/chat/{id}/export` | bytes, a `.docx`, or a ZIP with the explainer; 409 with `missing` while incomplete |
| Accept a rubric gap | `POST /api/cases/chat/{id}/rubric-gate {enabled: false}` | the student's own decision, recorded; the gaps stay in the table |
| Dataset into a tool | `POST /api/intake/{id}/map` | proposes values from a stored table through `bp.ingest.to_method_inputs`; executes nothing |
| Deliverables | `POST /api/cases/{id}/export {deliverable, kind, download}` | `submission`→`docx`/`html`, `workpapers`→`xlsx`/`spreadsheetml`/`csv`, `worksheet`→`docx`/`html`; an impossible pair is refused by name |
| Calculator router | `calc_router.plan(text)` | "what is my break-even point" reaches `breakeven`, the same method the tile launches |

The shelf carries no tiles (`tiles: []`) and no reviewer surface; the pricing dialog and the wallet
are shared page furniture, not entrepreneurship features.

## 9. Expected-behaviour table `E-ent-nnn`

Atomic, testable, one line each. Every row is enforced by the test of the same number in
`tests/test_subject_entrepreneurship_acceptance.py` (`test_e_ent_<nnn>__<behaviour>`), offline, with
retrieval mocked where a paper needs evidence. `PASS`/`FAIL`/`GAP` is decided in §10 from the run.

### 9.1 Inventory and contract

| Id | Behaviour | Source |
|---|---|---|
| E-ent-001 | `detail("entrepreneurship")` returns exactly 46 tools, **5** worksheets, 6 records, 0 theories and 34 glossary terms; the worksheet ids are STR-15, STR-16, STR-17, STR-18 and STR-13, and MKT-02 is deliberately absent (B-196) | rank 5 (measured `ent_catalogue.json`) |
| E-ent-002 | Every tool's `method` is a frozen `LIBRARY` method or a registered `templates.TEMPLATES` entry; `case_decision` is the only template | rank 1 |
| E-ent-003 | Every tool carries a `label`, `what`, `formula`, `period`, a `level` in {intro, intermediate, advanced}, ≥3 steps and ≥2 common mistakes | rank 5 |
| E-ent-004 | Every `related` id resolves to a declared tool id | rank 5 `TOOL_INFO` |
| E-ent-005 | Every tool has a preset, and that preset launches the tool's own method | rank 1 `server.PRESETS` |
| E-ent-006 | Every preset's default inputs pass `validate_inputs` **and** the method's `profile()` with no issue | rank 1 |
| E-ent-007 | Every preset **delivers** through `Pipeline().run`, its own checks all pass, no `{{ref:` token survives (D-ENT-04) | rank 1 + `qa/probe_ent_shelf.py` |
| E-ent-008 | No entrepreneurship method claims a `prescriptive` ceiling | rank 1 `claim_ceiling` |
| E-ent-009 | An unknown input name is refused with the allowed list, as a `blocked` delivery | rank 1 `validate_inputs` |
| E-ent-010 | The shelf copy stays inside its measured ceilings: guidance 60 words, `what` 26, step 20, mistake 23, start step 12, does-not line 14 | rank 5 copy, measured |

### 9.2 One row per tool — delivery through the tool's own preset

| Id | Tool | Behaviour | Source |
|---|---|---|---|
| E-ent-011 | `marketsize` | the preset delivers, every check passes, two runs agree, no token survives | rank 1 |
| E-ent-012 | `forecast` | same (was **blocked** by D-ENT-04) | rank 1 |
| E-ent-013 | `demandcurve` | same | rank 1 |
| E-ent-014 | `purchaseintent` | same | rank 1 |
| E-ent-015 | `funnel` | same | rank 1 |
| E-ent-016 | `cohort` | same | rank 1 |
| E-ent-017 | `concentration` | same | rank 1 |
| E-ent-018 | `elasticity` | same | rank 1 |
| E-ent-019 | `descriptive` | same (was **blocked** by D-ENT-04) | rank 1 |
| E-ent-020 | `chi_square` | same (was **blocked** by D-ENT-04) | rank 1 |
| E-ent-021 | `power` | same | rank 1 |
| E-ent-022 | `pricing` | same | rank 1 |
| E-ent-023 | `breakeven` | same | rank 1 |
| E-ent-024 | `multibreakeven` | same | rank 1 |
| E-ent-025 | `unitecon` | same | rank 1 |
| E-ent-026 | `costcurves` | same | rank 1 |
| E-ent-027 | `marketpower` | same | rank 1 |
| E-ent-028 | `capacity` | same | rank 1 |
| E-ent-029 | `inventory` | same | rank 1 |
| E-ent-030 | `frommarket` | same | rank 1 |
| E-ent-031 | `proforma` | same | rank 1 |
| E-ent-032 | `sensitivity` | same | rank 1 |
| E-ent-033 | `ratios` | same | rank 1 |
| E-ent-034 | `depreciation` | same | rank 1 |
| E-ent-035 | `salesprojection` | same | rank 1 |
| E-ent-036 | `startupcapital` | same | rank 1 |
| E-ent-037 | `cashrunway` | same | rank 1 |
| E-ent-038 | `roi` | same | rank 1 |
| E-ent-039 | `tax` | same | rank 1 |
| E-ent-040 | `npv` | same | rank 1 |
| E-ent-041 | `irr` | same | rank 1 |
| E-ent-042 | `dpayback` | same | rank 1 |
| E-ent-043 | `projectmetrics` | same | rank 1 |
| E-ent-044 | `scenario` | same | rank 1 |
| E-ent-045 | `trendanalysis` | same | rank 1 |
| E-ent-046 | `workingcapital` | same | rank 1 |
| E-ent-047 | `captable` | same | rank 1 |
| E-ent-048 | `loan` | same | rank 1 |
| E-ent-049 | `dcf` | same | rank 1 |
| E-ent-050 | `multiples` | same | rank 1 |
| E-ent-051 | `equitybridge` | same | rank 1 |
| E-ent-052 | `currency` | same | rank 1 |
| E-ent-053 | `sroi` | same | rank 1 |
| E-ent-054 | `cba` | same | rank 1 |
| E-ent-055 | `costeffectiveness` | same | rank 1 |
| E-ent-056 | `case_decision` | same, through the composite template preset | rank 1 `templates` |

### 9.3 Independent recomputation — the venture arithmetic

| Id | Behaviour | Source |
|---|---|---|
| E-ent-057 | `market_sizing` on the guide's example (20,000 customers × 3,000 spend, 25%, 20%) gives TAM 60,000,000, SAM 15,000,000, SOM 3,000,000 and 1,000 customers | guide §"Market size" (rank 6), recomputed |
| E-ent-058 | `breakeven` on 1,000 fixed / 20 price / 10 variable declares 100 units, 2,000 revenue, a 10 contribution margin, a 150 target volume at +500 profit and a 50-unit margin of safety at 150 expected | guide §"Break-even" (rank 6), recomputed |
| E-ent-059 | `pricing_decision` shows total cost 135,000, cost-plus 24.00, the same 24 at a 37.5% margin, break-even 22.50 and target return 25.8333… side by side | guide §"Pricing" (rank 6), recomputed |
| E-ent-060 | `startup_capital` adds a 47,000 contingency to 470,000 and reports 167,000 still to raise after 150,000 equity and a 200,000 loan | guide §"Start-up capital" (rank 6), recomputed |
| E-ent-061 | `cash_runway` reports 7.5 months on 300,000 cash and a 40,000 monthly burn, a −60,000 balance at month 9 and a 60,000 funding gap | guide §"Cash runway" (rank 6), recomputed |
| E-ent-062 | `return_on_investment` reports 25% and an annualised 7.7217% on 125,000 over 500,000 in 3 years | guide §"Return on investment" (rank 6), recomputed |
| E-ent-063 | `sales_funnel` reports 0.25, 0.20, 0.05 conversion and a 50 acquisition cost on 10,000 → 2,500 → 500 for 25,000 spend | rank 1, recomputed |
| E-ent-064 | `cohort_retention` pools 530 starters and reports 0.7358490… in period 2 with a 2.726415… average lifetime | rank 1, recomputed |
| E-ent-065 | `demand_curve` fits slope −12, intercept 640, R² 1, and a revenue peak at 26.6667 and 8,533.33 | rank 1, recomputed |
| E-ent-066 | `purchase_intent` applies the declared 0.8/0.3/0.1/0 weights: 135 of 400 → 0.3375, 6,750 buyers and 1,687,500 revenue at 250 | rank 1 (`purchase_intent_impl`), recomputed |
| E-ent-067 | `cap_table_round` reports a 5,000,000 post-money, a 4 price, 250,000 new shares, the founders at 72% and the pool at exactly 10% after the gross-up | rank 1, recomputed |
| E-ent-068 | Six venture methods pass **every check they declare** (`checks_pass` compares the names and the results) | rank 1 `Method.tests` |

### 9.4 The business plan and the marking guide

| Id | Behaviour | Source |
|---|---|---|
| E-ent-069 | The SHS plan carries `frommarket`, `breakeven`, `depreciation`, `proforma`, `sensitivity` in that order, all required, and no funding section | rank 4 `PLAN_*` |
| E-ent-070 | The college plan adds `tax`, `captable`, `impact` and the funding and impact sections | rank 4 |
| E-ent-071 | The Financial Plan is one H1 whose H2s are the five computation blocks in plan order | rank 4 `_draft_plan` |
| E-ent-072 | An incomplete plan blocks export and names every missing item ("what the business sells" among them) | rank 3 §8, rank 4 `_plan_missing` |
| E-ent-073 | An opening balance sheet that does not balance is refused with the core's own reason | rank 1 `proforma_statements` |
| E-ent-074 | The plan exports a real `.docx` (a ZIP carrying `word/document.xml`) | rank 3 §8 |
| E-ent-075 | A marking guide adds a `Rubric coverage` table immediately before the references, and a word-limit line is a budget, not a criterion | D-ENT-03 / B-193 |
| E-ent-076 | A weighted criterion the plan does not address blocks the download and is named in `missing` | B-187 at the plan path |
| E-ent-077 | The student may accept the gap: the gate turns off, the download proceeds and the table still names it | B-193 |
| E-ent-078 | A plan with no marking guide carries no `rubric` key and no coverage table — byte for byte what it was | B-193 |
| E-ent-079 | An unreadable marking guide is refused before the plan is built, with the reader's own reason | B-187 |

### 9.5 Worksheets

| Id | Behaviour | Source |
|---|---|---|
| E-ent-080 | The Business Model Canvas is T4, places the items, names the gaps and carries no raw digit | rank 1 `templates` |
| E-ent-081 | The Lean Canvas says in words that it does not score, rank or choose, and no field of its result is a mark or a ranking | rank 1 |
| E-ent-082 | The Value Proposition Canvas reports only the fit the student claims | rank 1 |
| E-ent-083 | The SWOT review turns evidence into declared actions and adds no digit | rank 1 |
| E-ent-084 | STR-13 (Blue Ocean ERRC) is offered as a worksheet but not draftable, and still runs | rank 5 |
| E-ent-085 | The marketing plan (MKT-02) is **not** on this shelf and not among its catalogue rows; the marketing shelf offers it, draftable, and the worksheet still runs | rank 5 + B-196 |

### 9.6 Records

| Id | Behaviour | Source |
|---|---|---|
| E-ent-086 | The shelf lists exactly the six records above and no theory row | rank 5 |
| E-ent-087 | Every computed record's status begins `partial:` | rank 5 |
| E-ent-088 | Every computed record states both what is implemented and what is not, and carries its structure text | rank 5 |
| E-ent-089 | Every worksheet record is on this shelf and reads `worksheet available` | rank 5 |
| E-ent-090 | No computed record appears as a worksheet the shelf does not have | rank 5 |

### 9.7 Surfaces, routes and the page

| Id | Behaviour | Source |
|---|---|---|
| E-ent-091 | `GET /api/cases/subjects/entrepreneurship` serves 46 tools, 5 worksheets, 6 records, three does-not lines and the guidance | rank 1 route |
| E-ent-092 | The shelf index serves `entrepreneurship` with the label `Entrepreneurship` | rank 1 route |
| E-ent-093 | The page groups the tools in plan order, from *Market and customers* to *Impact and options* | rank 5 |
| E-ent-094 | The glossary carries TAM, SAM, SOM, break-even point, margin of safety, CAC, LTV, runway, ROI, cap table, dilution, funnel, cohort, purchase intent and positioning | rank 5 |
| E-ent-095 | The page opens with four ordered start steps and a guidance line that names the business plan | rank 5 |
| E-ent-096 | The calculator router sends "what is my break-even point" to `breakeven`, the method the tile launches | rank 5 `calc_router` |
| E-ent-097 | The brief route reads pasted text and refuses invalid base64 with 422 | rank 1 route |
| E-ent-098 | A scanned brief reaches the vision model when no local Tesseract exists, the response names the **engine** that read it, the file it came from, and the text stays unverified (D-ENT-05) | B-191 + `bp.product.ocr` |
| E-ent-099 | The plan export answers bytes (`filename`, `mime`, `data`) and never a server path | rank 1 route, D-dl |
| E-ent-100 | Every deliverable pair the results panel asks for is a pair the core allows, and an impossible pair is refused | rank 1 `deliverables` |
| E-ent-101 | The page posts the parsed marking guide with the plan, explains it before the run, and offers the accept-the-gap button | B-193, `web/index.html` |

### 9.8 Trap rows — the defects this session fixed

| Id | Behaviour | Defect |
|---|---|---|
| E-ent-102 | A plan block's list columns are **proposed** from a stored table and its drivers are named in `not_mapped`, not refused | D-ENT-02 |
| E-ent-103 | A scalar asked to come from a column is still refused, in the core's own words | D-ENT-02 (unchanged) |
| E-ent-104 | A mapping executes nothing: no report, delivery, session, result or check in the response | B-192 (unchanged) |
| E-ent-105 | A word-budget line in a **list** rubric is the length budget, not a weighted criterion | D-ENT-03 |
| E-ent-106 | A criterion and a heading that share a six-letter stem are the same requirement ("Referencing" / "References"), while near words stay apart ("Content" / "Context") | D-ENT-03 |

## 10. Traceability matrix

Filled from the executed suite. Each E-id is enforced by the test method of the same number in
`tests/test_subject_entrepreneurship_acceptance.py` unless another file is named. The run is
`qa/baseline/ent_acceptance.txt`.

| E-ids | Enforcing test group | Status |
|---|---|---|
| E-ent-001…010 | `InventoryTest` — inventory, contract, presets, refusals, measured copy | PASS |
| E-ent-011…056 | `ToolDeliveryTest` — one generated test per tool, through its own preset | PASS (46/46) |
| E-ent-057…068 | `ArithmeticTest` — hand recomputation from the guide and the contract | PASS |
| E-ent-069…079 | `PlanProfileTest` — plan shape, gate, refusals, rubric coverage, gate switch | PASS |
| E-ent-080…085 | `WorksheetTest` — the five T4 worksheets, the undraftable ERRC grid and the marketing plan's ownership | PASS |
| E-ent-086…090 | `RecordTest` — record truth against the catalogue | PASS |
| E-ent-091…101 | `SurfaceTest` — routes, grouping, glossary, brief, OCR engine, export bytes, pairs, page | PASS |
| E-ent-102…106 | `TrapTest` — the two fixed defects and the two kept refusals | PASS |

## 11. Known gaps

Named, with the document or decision that declares each. None is converted into an expectation,
and none is built by this session.

| Id | Gap | Declared by | Ledger |
|---|---|---|---|
| G-ent-01 | No term sheet, liquidation preference, anti-dilution or multi-round cap table: `cap_table_round` prices one round | `CURRICULUM_MAP` named gaps | D-ENT-06 |
| G-ent-02 | No conjoint, survival model or Monte Carlo; sensitivity is price-and-volume only | `CURRICULUM_MAP`; `KNOWN_LIMITATIONS` | D-ENT-06 |
| G-ent-03 | 36 of the 46 tools declare no `need` ("what to gather") text; `subjects.TOOL_NEEDS` has no entrepreneurship keys | `subjects.TOOL_NEEDS`, measured | D-ENT-07 |
| G-ent-04 | The three canvas catalogue records are correct, but a *theory* row does not exist on the shelf; a reading lens is reached only by naming it in a brief | `detail["theories"] == []` | D-ENT-08 |
| G-ent-05 | The dataset mapper proposes values but no plan form offers a picker yet: the Calculator form is where a mapping is consumed | B-192 ("the surface is still open") | D-ENT-09 |
| G-ent-06 | `case` and `unsupported` are presets with no method key / a deliberately unknown method; they are fixtures, not tools, and the shelf does not offer them | `server.PRESETS` | D-ENT-10 |
