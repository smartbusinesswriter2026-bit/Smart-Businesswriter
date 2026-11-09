# Product gap map (working backlog)

**Status: PROVISIONAL planning aid, not a decision.** It prioritises candidate work; nothing here is committed to build until the owner picks a direction and it becomes a B-… decision. Read it alongside `docs/DECISIONS.md` and `docs/KNOWN_LIMITATIONS.md`.

## Why this exists

The pipeline grew **method-by-method** (provider → statistics → forecasting → accounting), while the catalogue describes a **whole product** (140 records: 61 frameworks, 22 models, 50 quantitative methods, 7 theory clusters). This map is the difference between the two, ordered by leverage and risk, so gaps are addressed *before* more is built on top.

## What is already covered (baseline)

- **Model assistance** (DeepSeek/OpenAI-compatible boundary; facts/alternatives/critique under code validation), literature DOI verification, held-out evaluation scaffold.
- **Statistics**: descriptive, Pearson/Spearman, OLS + HC3 (diagnostics), Welch t-test + Mann-Whitney, one-way ANOVA + Kruskal-Wallis, chi-square; effect sizes + intervals throughout.
- **Forecasting**: linear trend with prediction intervals and an out-of-sample holdout (linear only).
- **Accounting (Stage 8)**: declarative engagement → ledger kernel → **T-accounts and a journal view** → schedules (straight-line, reducing-balance and units-of-production depreciation; amortization; accruals; **disposal; prepayments; deferred income; bad-debt allowance; revaluation**) → cash flow (two routes) → closing + retained-earnings rollforward → reconciliation → **statement of changes in equity, current/non-current balance sheet, and an other-comprehensive-income route** → statement exports, with the account-mapping checkpoint.
- **Ratio analysis**: `ratio_analysis` (T1, B-056) computes 15 declared liquidity, profitability, solvency and efficiency ratios from supplied statement figures, with a not-computed reason for anything uncomputable and no invented benchmarks.
- **Templates**: SWOT, Five Forces, and `case_decision` (2–5 alternatives compared by NPV).

## The four gaps, with tier/verification notes

Priorities: **P0** = gatekeeper (unblocks other work) · **P1** = high leverage, low risk · **P2** = breadth.

### A. Gatekeepers (P0)

| Gap | Why it matters | Tier / verification note |
|---|---|---|
| **Retrieval + citation layer** — standards, company filings, tax, literature | The manual makes retrieval mandatory before trusting any drifting rule ([manual §15, line 520](sources/business_pipeline_v0_3.md#L520)); it unblocks framework citation, tax (B-052), the research workflow (REW), and valuation multiples | A *boundary*, not a computation: hash-audited, fail-closed, labels of `retrieved + cited` vs `declared by you (not verified)`, never a silent memory citation. **Built:** literature slice with response sha256 + UTC time (B-054), durable retrieval log (B-058), APA/Harvard citation formatting (B-059), Crossref→OpenAlex failover with recorded attempts and a drift sweep (B-064). **Still missing:** standards/filings/tax source families and any additional scholarly APIs. |
| **Ingestion** — PDF/scan/Excel/SPSS → structured, reusing the quote/provenance discipline | Most of the 140 catalogue items are data-hungry; the system today only eats hand-typed JSON. Manual open question ([§16, line 552](sources/business_pipeline_v0_3.md#L552)) | **Built (B-065, B-071, B-076):** CSV/TSV and XLSX → typed table with types, missing counts and a provenance pointer; caps refused, not truncated; named columns map into a method's inputs through the pipeline's own validation (B-071); XLSX sheet selection by exact name or 1-based number, and a declared merged-cell policy — refused by default, `top_left` expansion recorded as a declared convention (B-076). **Still missing:** PDF/scan/OCR and SPSS ingestion (refused explicitly), reading several sheets into one table (needs a declared concatenation rule), and unattended column→method mapping (deliberately not built: which column is `values`/`y`/`predictors` is the user's declaration). Structured files → T1; OCR/PDF → unverified text → T2 + label + human confirm (not implemented) |
| **Decision dependencies** | Reviewer naming is not planned (B-112); nothing is promoted on review grounds. Was: promote T2→T1 (B-005), the ledger-engine choice (B-032), ratification of the research-manual proposals (B-053; R11 done, R1–R10 open) | Owner decisions, not build; they gate promotion and any jurisdiction-dependent work |

### B. Statistics completion (manual 9B.2/9B.3) — P1

The manual's own growth order ([§9B.2, lines 345–359](sources/business_pipeline_v0_3.md#L345)) minus what exists:

| Gap | Tier / verification note |
|---|---|
| Paired and one-sample t-tests | **Built** (B-067): `paired_t` and `one_sample_t`, T1, five frozen checks each, scipy goldens. Remaining: no signed-rank fallback; no one-sided test. |
| Factorial ANOVA, ANCOVA, repeated measures, post-hoc tests | **Partly built** (B-070): `two_way_anova` (balanced two-way, T1) and `posthoc_pairwise` (Welch pairs with declared Holm/Bonferroni, T1). **Still open:** unbalanced designs, ANCOVA, repeated measures, three-way, and Tukey/Dunnett/Games-Howell procedures. |
| Logistic regression | **Built** (B-074): `logistic_regression` T1, Newton-Raphson with convergence/separation blocks, Wald inference, odds ratios, McFadden pseudo R-squared. Remaining: categorical predictors/interactions, regularisation, goodness-of-fit and calibration. |
| Reliability (Cronbach's α) and factor analysis | **alpha built** (B-074): `reliability_alpha` T1. **Still open:** factor analysis (needs declared extraction/rotation defaults, [§9B.4](sources/business_pipeline_v0_3.md#L377)) and standardised alpha/confidence intervals. |
| Clustering (segmentation) | T2 initially — many algorithms, no single "right" answer; needs a labelled evaluation set |
| **Cross-cutting (9B.3)**: multiple-comparison correction, power/precision statements, missing-data mechanisms + imputation, survey weights / clustered-data detection | **Built for what can be declared honestly (B-057, B-060, B-061, B-062, B-063):** disclosure layer in every delivery; **multiple-comparison correction** (`multiple_comparison`); **power and minimum effect** (`power_analysis`); **missing-data bounds with a declared-but-unverified mechanism** (`missing_data_bounds`); **weighted summaries** with declared reliability/frequency weights, effective sample size and design effect (`weighted_summary`). **Still open:** imputation / MAR-MCAR-MNAR models and complex-design inference (stratification, clustering, replicate weights) ([§9B.3, lines 369–375](sources/business_pipeline_v0_3.md#L369)) |
| Time series beyond linear trend (seasonality, backtesting, break detection) | Highest stats risk — sits under the §8 regime-change controls |

### C. Finance & valuation (sits on the finished ledger) — P1

| Gap | Tier / verification note |
|---|---|
| **Financial statement ratio analysis** (liquidity, profitability, solvency, efficiency) computed from the statements | **Built** (B-056, `ratio_analysis`, T1): 15 declared ratios in Decimal, exact-rational second route, not-computed reasons, no benchmarks or verdicts. **Completed** (B-090, B-102) with `dupont_analysis` (T1, three- and five-step ROE, common-size ratios and one-period growth), `trend_analysis` (T1, multi-year common-size, index and compound growth) and the cash conversion cycle inside `working_capital` (T1). Remaining: industry benchmarks, restatements and segment/consolidated analysis, which need retrieved sources or a declared standard (P2). |
| DCF valuation + WACC | **Built** (B-068): `wacc` (T1, declared costs; no tax) and `dcf_valuation` (T2, declared cash flows, rates and Gordon growth; five frozen checks each); **completed** (B-078) with a declared mid-year timing convention (`timing: end|mid`) and the separate `equity_bridge` T2 method (EV → equity value via net debt, minority interest and preferred equity, optional per-share). **Completed** (B-090) with `capm` (T1, declared or OLS-estimated beta plus Hamada relevering), `multiples_valuation` (T2, declared peers to an implied EV/equity/per-share value) and `bond_analysis` (T1, price or solved yield with duration, convexity and DV01). Remaining: scenario/real-option valuation and a spot/forward curve (P2). |
| Capital budgeting: NPV, IRR, discounted payback | **Built** (B-077): `npv` (existing), `irr` (T1; the unique root of the NPV function, several sign changes refused rather than one root chosen) and `discounted_payback` (T1; recovery period with declared within-period interpolation, unrecovered outlays block). **Completed** (B-090) with `project_metrics` (T1: profitability index, MIRR, simple payback and equivalent annual annuity beside NPV/IRR) and `scenario_analysis` (T1: declared low/high discount-rate range and the decision-flip rate). Remaining: mid-year conventions on these measures, a ratified unequal-life ranking rule, and real options. |
| Unit economics (unit margin, LTV/CAC), multi-product break-even | **Built** (B-072): `unit_economics` (T1) and `multi_product_breakeven` (T1), five frozen checks each. **Completed for the venture shelf** (B-104): `breakeven` now also reports the break-even revenue, contribution margin, margin of safety and target-profit volume when those inputs are declared. Remaining: discounted LTV, retention curves, segment-level CAC, changing mix and step costs. |
| Market sizing, pricing and the venture funding need (entrepreneurship) | **Built** (B-104): `market_sizing` (T1, top-down TAM/SAM/SOM from a declared population, spend and two shares), `pricing_decision` (T1, cost-plus, target-margin, break-even and target-return prices), `startup_capital` (T1, set-up costs plus working capital plus contingency, less declared sources), `cash_runway` (T1, months to zero cash, lowest balance and funding gap) and `return_on_investment` (T1, ROI and annualised ROI), five checks each. **Extended** (B-109) with `sales_projection` (T1, period revenue/cost/profit), `cap_table_round` (T1, one priced round and dilution), `sales_funnel` (T1, stage conversion and CAC), `cohort_retention` (T1, pooled retention and lifetime), `demand_curve` (T1, declared-data line fit and revenue-max price) and `purchase_intent` (T1, weighted intent and projected buyers); the Business Model Canvas, Lean Canvas, Value Proposition Canvas and a marketing plan are now T4 worksheets (B-106). Remaining: term sheets and negotiated clauses, multi-round cap tables, conjoint analysis, survival models, multi-input scenarios and Monte Carlo, and market-data retrieval. |
| A complete business plan: brief in, projected statements, Word out | **Built** (B-148): the `business_plan` paper profile composes student input, market evidence, plan-level computation and integration sections; the Financial Plan is one H1 with its blocks as H2s. New T1 methods `sales_from_market`, `depreciation_schedule`, `proforma_statements` (income statement, cash flow and balance sheet with the balance refusal) and `sensitivity_table`; college adds `tax_declared`, `cap_table_round` and `cost_effectiveness`. Brief upload reads PDF text, `.docx` and TXT; the strict entry is the Entrepreneurship page and open composition is Home; export is blocked until every required field and block is complete. Remaining: monthly statements, multi-product mix, disposals, group consolidation, jurisdiction tax law and a structured period-table editor. |
| Time value, debt instruments and working capital | **Built** (B-090): `time_value` (T1), `loan_amortization` (T1), `bond_analysis` (T1) and `working_capital` (T1: cash conversion cycle, EOQ, reorder point, trade-credit cost), each with a second route and frozen checks. Remaining: a rate/term solver, accrued interest and day-count conventions, quantity discounts and a cash budget (P2). |
| Investments, derivatives, risk and international finance | **Built** (B-090): `portfolio_analysis` (T1: two-asset return/risk, correlation, Sharpe, beta, Treynor, Jensen), `option_pricing` (T2: Black-Scholes and Greeks with a binomial cross-check), `risk_metrics` (T1: parametric/historical VaR and expected shortfall), `fx_parity` (T1: interest and purchasing-power parity plus a one-forward hedge comparison), `scenario_analysis` (T1) and `leverage_analysis` (T1: EPS, DFL, interest cover, tax shield, two-plan EBIT-EPS indifference, Altman Z). Remaining: multi-asset optimisation and the efficient frontier, American exercise and implied volatility, a volatility model/backtest, credit and liquidity risk, multi-input scenarios and Monte Carlo, and more than two financing plans (P2). |
| Multi-currency: ISO 4217 registry, per-currency precision, declared-rate conversion | **Built** (B-069): `currency_convert` (T1) and a currency-aware intake/precision layer; 160+ codes. **Still open:** FX retrieval/verification and statement translation or consolidation (needs retrieved rates and a translation standard). |
| Cost-benefit / cost-effectiveness / SROI | **Built** (B-073): `cost_benefit`, `cost_effectiveness`, `sroi`, T2, five frozen checks each; declared valuations only, no monetisation or threshold invented. Remaining: sensitivity distributions, discounting/timing conventions, expertise review (B-005). |
| Accounting: books, statements, ratios, costing, variances and declared tax | **Built** (B-114/B-115/B-118/B-119): `management_accounts` (T2 engagement), `trial_balance_check` (T2), `ratio_analysis`, `standard_cost_variances`, `abc_costing`, `sales_variances`, `tax_declared`, `working_capital`, `loan_amortization` and `trend_analysis`, with an accounting guide and glossary. Remaining: jurisdiction tax rules, audit opinion/sampling, group consolidation, target/life-cycle costing, budget/planning variances. |
| Operations: capacity, queueing, inventory, line balancing, OEE and quality | **Built** (B-114/B-118/B-119): `capacity_analysis`, `queue_analysis` (M/M/c), `inventory_policy`, `line_balancing`, `oee_analysis`, `process_control` (I-MR and Cp/Cpk), with the operations guide and glossary. Remaining: mixed-model or optimal balancing, subgroup charts, FMEA, simulation, multi-echelon inventory. |
| Project management: appraisal, scheduling, control and delivery frameworks | **Built** (B-116/B-118): the shelf reuses `npv`, `irr`, `discounted_payback`, `project_metrics`, `scenario_analysis`, `case_decision` and `trend_forecast`, and adds `cpm_schedule` (early/late dates, float, critical path, PERT) and `earned_value` (SV, CV, SPI, CPI, EAC/ETC/VAC/TCPI); `PM-01..14` are read-only framework records with a guide and glossary. The charter, WBS, RACI and risk-register worksheets are built (B-131), the stakeholder/communication and lessons-learned worksheets are built (B-136), and a deterministic Gantt chart and Schedule sheet are built (B-135). Batch A adds `resource_leveling`, `project_crashing` and `calendar_schedule` (B-139); batch B adds `multi_project_schedule` and `schedule_risk` (B-140); batch C adds `decision_tree`, `real_option` and `multi_criteria` (B-141); generic Monte Carlo adds `monte_carlo` (B-143); renderer extras add Gantt dependency arrows, a client preview and an XLSX bar strip (B-144). Remaining: arbitrary-formula simulation, correlated inputs and fitted distributions. |

### C2. Economics — micro core (P1)

| Gap | Tier / verification note |
|---|---|
| Demand, supply and equilibrium | **Built** (B-097): `demand_supply_equilibrium` (T1) returns P*, Q*, choke and floor prices, consumer and producer surplus, five frozen checks. Linear curves only; no estimation. |
| Price elasticity and revenue | **Built** (B-097): `elasticity` (T1), arc/midpoint between two observations, absolute value and elastic/inelastic flags, five checks. Income and cross-price elasticity remain open. |
| Tax incidence and deadweight loss | **Built** (B-097): `tax_incidence` (T1), per-unit tax on sellers, burden split, revenue and DWL, five checks. Ad valorem tax remains open. |
| Price ceilings and floors | **Built** (B-097): `price_control` (T1), binding test, quantity traded, shortage/surplus, DWL, five checks. |
| Market concentration | **Built** (B-097): `market_concentration` (T1), HHI from percentage shares, CR1, CR4, equivalent number of firms, five checks. Market definition remains the user's. |
| Cost curves, profit maximisation, market power | **Built** (B-098): `cost_curves` (T1, AC/AVC/AFC/MC with a shutdown test), `profit_maximization` (T1, MR = MC with profit and Lerner) and `market_power` (T1, markup and Lerner index), five checks each. |
| National income and growth | **Built** (B-098): `national_income` (T1, expenditure-approach GDP, GNP, NNP, real GDP and GDP per capita) and `growth_rate` (T1, total growth, CAGR and rule-of-72 doubling time), five checks each. |
| Inflation and unemployment | **Built** (B-098): `inflation_cpi` (T1, inflation, exact and approximate real interest, real wage growth) and `unemployment_rate` (T1, unemployment, participation and employment-population rates), five checks each. |
| Money, fiscal policy and debt | **Built** (B-098): `money_multiplier` (T1, simple and currency-adjusted multipliers), `fiscal_multiplier` (T1, government, tax and balanced-budget multipliers) and `budget_debt` (T1, balances, debt ratio and debt dynamics), five checks each. |
| Welfare, public and development | **Built** (B-099): `externality_pigouvian`, `public_good`, `social_welfare`, `gini_coefficient`, `poverty_measures`, `tax_progressivity`, `optimal_pollution`, `output_gap_okun`, `hdi`, five checks each. |
| International and behavioural | **Built** (B-099): `comparative_advantage`, `tariff_welfare`, `exchange_rate_ppp`, `interest_rate_parity`, `balance_of_payments`, `expected_utility`, `prospect_theory` and `labour_market`, five checks each. |
| Electives and game theory | **Built** (B-099): `price_discrimination`, `cournot_duopoly`, `difference_in_differences` and `nash_equilibrium` (2x2 pure strategies), five checks each. |
| Advanced econometrics | **Built** (B-100): `panel_regression` (balanced fixed effects), `instrumental_variables` (just-identified IV), `regression_discontinuity` (sharp local-linear RDD) and `probit` (binary probit), five checks each. VAR, cointegration and the remaining time-series estimators remain parked. |

### D. Catalogue breadth — marketing, operations, risk, people (P2)

Most of these start as **T4 structure-only** evidence templates (organise the owner's evidence, compute nothing), promotable to T2 once the underlying quant from section C exists. B-028 is answered for the strategy core by B-113: PESTEL, Value Chain, VRIO, Ansoff, ERRC, scenario planning, strategic groups and activity-system fit are now T4 worksheets, together with the three canvases and the marketing plan. MCDA and the remaining templates are still open.

- **Marketing/customer**: STP, 4Ps/7Ps, Kano, RFM, cohort/churn/LTV, pricing & demand, media planning and the digital lane. **Closed for the digital lane by B-117**, **for RFM and media planning by B-121**, and **for the remaining assignment gaps by B-133**: `market_share`, `clv_model` and `customer_profitability` close the last quantitative records (`QNT-MKT-02/-03/-07`), and five T4 worksheets - customer journey map (`MKT-04`), Kano classification (`MKT-06`), SERVQUAL gap grid (`MKT-07`), paid media plan (`MKT-15`) and web/app measurement plan (`MKT-18`) - turn the most-used frameworks into documents a student can hand in. No marketing record now reads "not built". **Still open**: ad-platform and analytics connectors (import the export instead), incrementality/holdout tests, multi-touch causal attribution, budget optimisation, segment stability and clustering, fitted churn and cohort models, and source-drafting into the five new worksheets.
- **Operations/supply chain**: EOQ + safety stock, queueing/capacity, theory of constraints, SPC/OEE, CPM/PERT, linear/integer optimization.
- **Risk/decision**: decision trees + expected value, Monte Carlo, scenario/stress, FMEA/Bow-tie, ISO 31000/COSO.
- **People/org**: Kotter, Lewin, ADKAR, 9-box, OKR/BSC — registry only today.

### E. Non-computational product gaps (manual §15B, §16)

These are requirements the manual already flags as [OPEN](sources/business_pipeline_v0_3.md#L522), not methods:

- Multi-period comparatives, restated prior periods, report versioning with diffs.
- Academic-integrity / AI-use **disclosure-ready export** and a **reviewer sign-off workflow** ([line 544](sources/business_pipeline_v0_3.md#L544)).
- Case workspace: retention/privacy, returning users, shared source caching ([§5.9](sources/business_pipeline_v0_3.md#L185)).
- **Model version pinning + drift gate** ([line 528](sources/business_pipeline_v0_3.md#L528)); security/hostile content + privacy-law review ([line 526](sources/business_pipeline_v0_3.md#L526)); budgets/observability.
- **Research & Evidence Workflow (REW, formerly Stage 7)** — the living manual is the ratified working authority (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`, B-053 / R11) and proposes stages R0–R8, but no stage is built and R1–R10 remain unratified proposals; only the literature retrieval boundary (B-040) is real.

## Recommended order

1. **Ratify the remaining research-manual proposals (R1–R10)** — free, unblocks the REW track and turns proposals into a build spec; R11 (the manual as working authority) is already ratified, and the original Smart Researcher manuals remain welcome and would be reconciled against it.
2. **Retrieval + citation (P0)** — the highest-leverage single item; it unlocks tax, REW, framework citation and valuation, and is the one thing the manual treats as non-negotiable. Literature retrieval, audit log, APA/Harvard, failover and drift are built (B-040/B-054/B-058/B-059/B-064); **market lookups** are built (B-106/B-109: Frankfurter FX, U.S. Treasury yields, Alpha Vantage quotes/fundamentals with the user's free key, SEC EDGAR filings, World Bank macro); **standards and tax sources** remain a source and licensing decision, and anything uncovered (PSE, private companies) is manual entry.
3. ~~Statement ratio analysis (P1/C)~~ — **done** (B-056, commit for 0.31).
4. **9B.3 upgrades (P1/B)** — disclosure layer (B-057), multiple-comparison correction (B-060), power/minimum-effect (B-061), missing-data bounds (B-062) and weighted summaries (B-063) are done; **imputation and complex-design inference are the remaining statistical items**, each needing a declared model/design choice.
5. **Ingestion (P0/A)** — structured ingestion is built (B-065: CSV/TSV and XLSX → typed table with provenance, caps refused); **PDF text-layer reading and scanned-PDF OCR** are built (B-107/B-110: pypdf, pypdfium2 and a local Tesseract), with images OCR'd when the engine is installed; SPSS and DOCX remain refused by design.
6. **Breadth (P2)** once templates are chosen (B-028); reviewer naming is not planned (B-112), and methods stay disclosed as not reviewed.

## Owner asks to un-block this

- ~~Name expert reviewers (B-005)~~ - **resolved by B-112**: no third-party reviewer is required; methods keep the not-reviewed disclosure.
- Pick the **next framework templates** (B-028) for section D.
- Decide the **ledger engine** (B-032) before tax/valuation sit on the ledger for real.
- **Ratify the remaining research-manual proposals** R1–R10 (B-053; R11 already ratified), or supply the original Smart Researcher manuals and it will be reconciled against them.

## Accounting - the statements tile (B-204)
- **Present:** one instruction in; four problem types (trial balance, transactions, adjustments,
  incomplete records); income statement, statement of changes in equity, balance sheet and trial
  balance from the core; journal, T-accounts, derivations and assumptions behind a toggle; imbalance
  diagnosed and never plugged; the missing capital of an incomplete record derived from the core's own
  difference; ratios on request; a frozen, replayable record; four routes on the case route.
- **Named gaps:** the cash-flow statement is withheld for a trial-balance input (a prior balance sheet
  or the flows are needed); intangible amortisation, suspense and error correction; market, cash-flow,
  quality and growth ratios; DOCX export; comparatives, segments and multi-currency; consolidated
  statements (B-032 stays open).
- **Not a gap:** a ratio the registry cannot support is printed with the input it needs, and a label the
  vocabulary does not know is shown rather than dropped.
- **Refused rather than merged (B-212):** two sets of balances, more than one period, a comparative
  column or a consolidation mention. Each refusal names the cause and what to do instead.

## Research routing (B-258, 2026-11-10)
- **Built:** every profile that retrieves evidence declares a research block (topic, tier order,
  query budget, needs, required tiers): PESTEL, Five Forces, the business plan, the quality modules,
  the portfolio/canvas modules, the strategy/management batch, the marketing batch, the people/change
  batch, the project/operations batch and the leadership/culture/ethics batch. The retriever routes,
  ranks and records a ledger; completion and chat grade identically.
- **Deliberate exceptions:** VRIO (no external evidence by design), the value stream map
  (quote/gap only), and four quote-only leadership profiles (ethical decision process, leader
  effectiveness, leadership development, organisational culture).
- **Not a gap:** a profile without a research block keeps the old behaviour. The block is optional
  so an untuned framework is never refused or silently given another framework's words.








