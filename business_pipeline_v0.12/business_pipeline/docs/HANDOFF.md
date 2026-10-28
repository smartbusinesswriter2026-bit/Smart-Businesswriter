# HANDOFF — instructions for the next coding agent

You are taking over a working repo, not starting one. Read this file first, then `CONDUCTOR_MANUAL.md`, `CONTRIBUTORS.md`, `HOME.md`, and the top three entries of `WORKLOG.md`. Do not re-architect anything; the rules below are the product.

## 1. Where things are and how to run them

```
Project root : D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline
Python       : 3.14 (stdlib only at runtime; scipy/numpy are offline fixture generators, never imported by src/)
Git          : branch master, no remote, clean tree expected (hashes live in `git log`; do not hard-code them here)
Build        : 1.34 (see docs/CHANGELOG.md)
Tests        : 1644 tests, all passing
```

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python -m unittest discover -s tests     # expect the final line "OK"; pwsh may still print [exit code: 1] because ResourceWarnings go to stderr - read the "OK" line, not the exit code
python -m bp.server 8000                 # workbench at http://127.0.0.1:8000
python -m bp.ingest file.csv             # ingestion CLI
python -m bp.literature drift retrieval_log.jsonl 20
```

## 2. The non-negotiables (short version of CONTRIBUTORS.md)

1. A model may propose; **code computes every number**. No model-authored figures.
2. **No invented sources.** Citations are resolved-and-verified or labelled `unverified_user_supplied`.
3. **Never weaken the verifier** to get green: no loosened tolerances, no deleted checks, no edited expected values, no skipped tests.
4. **Fail closed**: unknown method, unsupported format, failed check, unwritable audit log â†’ block with a reason.
5. **Stdlib only at runtime.** No new runtime dependencies.
6. Every increment: tests + `CHANGELOG.md` + `WORKLOG.md` entry + `DECISIONS.md` B-number if a convention is chosen + updated `KNOWN_LIMITATIONS.md`/`PRODUCT_GAP_MAP.md` + README/HOME if the surface changed. One commit per increment.
7. `docs/sources/` is read-only authority material. Never edit it.
8. Do not mark a gap closed, or a PROPOSAL ratified, without the tests and an owner decision.
9. **Two model owners (B-066, extended by B-080).** The computation owner (DeepSeek) exclusively owns `src/bp/**`, `tests/**`, the factual docs and every rule/number/citation/claim; the design owner (MiniMax) owns the workbench's presentation and may now also build the **product backend** — additive routes/modules/storage/workflows over the frozen core. Read `CONTRIBUTORS.md` §1A/§1B before editing; write only in your domain, and split cross-domain features into a computation commit then a design commit.
10. **The core deterministic backend is FROZEN (B-079).** The stage contract, the 140 method contracts, the 142 presets, the 12 API route families and the delivery shape are pinned by `tests/test_frozen_contract.py` + `tests/fixtures/frozen_contract.json`. Never edit that fixture to go green; an unfreeze needs the owner's approval and a B-decision. Full rules: `docs/BACKEND_CONTRACT.md`.

## 3. What is already built (do not rebuild)

- **Core**: frozen spec/hashed artefacts, sandboxed execution, second-route verification, claim ceilings, re-performance bundles, deterministic reports (`spec.py`, `orchestrator.py`, `sandbox.py`, `artifacts.py`, `claims.py`, `reperform.py`).
- **Methods (T1 unless noted)**: npv, irr, discounted_payback, breakeven, descriptive_stats, pearson/spearman, ols/ols_robust, welch_t, mann_whitney, anova, kruskal_wallis, chi_square, trend_forecast, ratio_analysis, paired_t, one_sample_t, two_way_anova (balanced only), posthoc_pairwise, wacc, currency_convert, unit_economics, multi_product_breakeven, logistic_regression, reliability_alpha, multiple_comparison, power_analysis, missing_data_bounds, weighted_summary, demand_supply_equilibrium, elasticity, tax_incidence, price_control, market_concentration, cost_curves, profit_maximization, market_power, national_income, growth_rate, inflation_cpi, unemployment_rate, money_multiplier, fiscal_multiplier, budget_debt, externality_pigouvian, public_good, social_welfare, gini_coefficient, poverty_measures, tax_progressivity, optimal_pollution, output_gap_okun, comparative_advantage, tariff_welfare, exchange_rate_ppp, interest_rate_parity, balance_of_payments, hdi, expected_utility, prospect_theory, labour_market, price_discrimination, cournot_duopoly, difference_in_differences, nash_equilibrium, panel_regression, instrumental_variables, regression_discontinuity, probit; **T2**: cost_benefit, cost_effectiveness, sroi, dcf_valuation (end-of-period default or declared mid-year), equity_bridge, management_accounts. Plan-level T1: sales_from_market, depreciation_schedule, proforma_statements, sensitivity_table. Templates: SWOT, Five Forces, case_decision (T2/T4).
- **Business plan (B-148)**: the chat adds a `business_plan` paper profile. It composes student input, retrieved market evidence, plan-level computation and integration sections; the Financial Plan is one H1 whose H2s are the computation blocks. SHS core blocks are sales from market, break-even, depreciation, projected statements and sensitivity; college adds tax, the cap table and a cost-effectiveness impact ratio. The four plan-level methods (`sales_from_market`, `depreciation_schedule`, `proforma_statements`, `sensitivity_table`) live in the frozen core. The Entrepreneurship page opens the strict convention; Home opens open composition. `POST /api/cases/brief` reads a PDF text layer, Word `.docx`, TXT or an image when OCR is installed; `customise`, `inputs`, `compute` and `draft` drive the plan; export returns 409 with the missing list until every required field and block is complete. An unbalanced opening balance sheet is refused with the equity that would balance it.
- **Conductor frameworks (B-151)**: nine framework entries and two combinations - PESTEL, SWOT, PESTEL + SWOT, Five Forces, Five Forces + Break-even, Value Chain (nine activities), Ansoff (four options), VRIO (student resources and four judgments, no evidence) and Break-even (computation only). ttach_computation puts the frozen break-even section on any evidence framework, validated by the core before storage, via POST /api/cases/chat/{id}/computation; the export gate names missing VRIO judgments and missing break-even inputs. 	ests/test_conductor_frameworks.py is the contract; the UI affordance is the design lane.
- **Accounting (Stage 8, T2)**: ledger kernel, schedules (depreciation/amortization/accruals), two-route cash flow, closing + retained-earnings rollforward, declarative engagement spec, reconciliation, account-mapping checkpoint, plain-text statement exports. Ledger engine choice open (B-032).
- **Retrieval**: Crossrefâ†’OpenAlex with declared failover and recorded attempts, response SHA-256 + UTC time, durable append-only JSONL log, drift sweep, APA 7 + Harvard citation formatting.
- **Ingestion**: CSV/TSV + XLSX â†’ typed table with provenance; XLSX sheet selection by exact name or 1-based number, and merged cells refused by default (declared `top_left` expansion recorded when chosen) — B-076; PDF/scan/OCR/SPSS refused explicitly.
- **Model boundary**: DeepSeek/OpenAI-compatible/Anthropic adapters, proposals-only validation, held-out evaluation scaffold (synthetic fixtures only).
- **Research & Evidence Workflow (REW)**: living manual ratified as authority (R11) with stages R0–R8 **proposed**, none built.
- **Documentation spine**: CONTRIBUTORS, HOME, WORKLOG, DECISIONS (B-001…B-080, incl. B-075 the parked queue, B-079 the frozen core, B-080 the product-backend lane), CHANGELOG, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, **PARKED_QUEUE** (frontier-model work, do not start un-invited), **BACKEND_CONTRACT** (frozen surface + unfreeze policy; read before touching `src/bp/**`).

## 4. Owner decisions that gate work (ask before building)

| Id | Decision needed | Blocks |
|---|---|---|
| B-005/B-112 | Reviewer naming is **not required**; methods stay disclosed as not reviewed | Nothing is blocked by it |
| B-028 | Pick next framework templates (PESTEL, VRIO, Value Chain, BMC, MCDA) | P2 breadth |
| B-032 | Ledger engine: custom kernel vs Beancount arm | Accounting tier, tax/valuation |
| B-052 | Taxation deferred; do not build without resuming the decision | Tax work |
| REW R1–R10 | Ratify (or not) the proposed stages/checkpoints/taxonomy | Any REW stage build |

Do not invent answers to these. If the owner says "go", build only what is listed below as unblocked.

**Already resolved, do not re-litigate:** B-079 (core deterministic backend frozen; unfreeze policy in `BACKEND_CONTRACT.md`) and B-080 (product backend delegated to the design owner as additive work over the frozen core). The computation lane is drained: everything buildable without the frontier model or an owner decision is built and verified (36 methods, 1644 tests).

## 5. The work left, in priority order, with acceptance criteria

### A. ~~Ingestion â†’ method-input mapping~~ — done (B-071, build 0.46)
`ingest.to_method_inputs` maps named columns into a method's declared inputs (list and `column_map` shapes), validates through the method's own `validate_inputs`/`profile`, refuses scalars/unknown/text conflicts, and is exposed as the optional `map` on `POST /api/ingest` with a source-hash provenance note. No column semantics are invented.

### B. Standards / filings / tax retrieval sources (blocked on an owner source decision)
**Do not implement** until the owner names sources and licensing. Questions to ask: which accounting standards (and is retrieval licensed?), which filing source (e.g. SEC EDGAR is free; confirm jurisdiction), tax (B-052 deferred). When answered: add sources behind the existing `Source` boundary, keep fail-closed verification, extend `test_literature*`, docs.

### C. Statistics remainder — current status
Built and tested (do not rebuild): paired/one-sample t (B-067), balanced two-way ANOVA and posthoc Welch pairs with declared Holm/Bonferroni (B-070), logistic regression and Cronbach's alpha (B-074), plus the 9B.3 disclosure layer, multiple comparisons, power/MDE, missing-data bounds and weighted summaries (B-057/B-060/B-061/B-062/B-063).
**Not built, deliberately parked in [`PARKED_QUEUE.md`](PARKED_QUEUE.md)**: Tukey/Dunnett/Games-Howell (needs the studentized-range and multivariate-t distributions), unbalanced two-way/ANCOVA/three-way (needs a declared Type II/III SS convention), repeated measures (needs a declared sphericity rule), k-means clustering (T2, needs a labelled evaluation set), factor analysis (needs declared extraction/rotation defaults), non-linear time series (highest-risk conventions). **Do not start any of these without the owner granting the frontier-model budget** — see §F.
Imputation / complex-design inference stays blocked on an owner-declared model (recommended default: none; keep the extreme-case bounds only). Do not invent one.

### D. REW stages (blocked until R1–R10 ratified)
If ratified, start with the cheapest real slice: R0 intake â†’ R1 literature search with the existing retrieval + screening log â†’ R2 gap statement. Acceptance includes the stage contracts in the manual.

### E. Breadth (blocked on B-028 only; reviewer naming is not planned, B-112)
Framework templates as T4 structure-only, each with evidence schema + checks, registry linkage, docs.

### F. Product backend — design owner's lane (B-080; unblocked for the design owner)
Product-surface work now belongs to MiniMax: the workbench, plus additive routes/modules/storage/workflows that consume the frozen core. Candidate items (each still needs its own B-decision before building): AI-use disclosure export, reviewer sign-off workflow, multi-period comparatives/report versioning, case workspace retention/privacy, model pinning/drift gate, security/privacy review, budgets/observability, durable case storage (serializes the existing JSON contracts; a core change is an unfreeze request). The computation owner reviews the boundary and the frozen contract, and must not be asked to ship numbers or wording through this lane.

### G. Stage 8 remainder (blocked on B-032)
Beancount arm / final engine decision; standards retrieval feeding the statements; tax once resumed.

### H. Parked frontier-model queue (do not start without an explicit owner grant)
The remaining heavy statistics work is **parked, not forgotten**: Tukey/Dunnett/Games-Howell, unbalanced two-way/ANCOVA/three-way, repeated measures, k-means, factor analysis and non-linear time series. All of it is registered with its blocker, its offline oracle and its acceptance sketch in [`PARKED_QUEUE.md`](PARKED_QUEUE.md) (decision B-075). The owner has reserved these for the **DeepSeek Pro frontier-model lane** and will release them when credits allow; a "continue" from the owner does **not** un-park them — only an explicit grant of that lane does. Finishing one item is one commit, and for the convention-heavy ones the convention decision comes before the code.

## 6. Definition of done for the whole product (checklist)

- [ ] All owner decisions in §4 resolved.
- [ ] REW stages built and ratified (R1–R10).
- [ ] Statistics set complete per manual §9B.2/9B.3 (ipso facto no undisclosed under-reporting).
- [ ] Finance/valuation: DCF+WACC, unit economics, CBA/CEA/SROI.
- [ ] Accounting: engine decided, standards retrieval, tax (or explicit non-goal re-confirmed).
- [ ] Retrieval covers standards/filings/tax + literature; every number-bearing rule retrievable.
- [ ] Ingestion covers PDF/scan (with unverified-text labelling + human confirm) and SPSS.
- [ ] AI-use disclosure export + reviewer workflow + case workspace.
- [ ] Model quality measured on real held-out cases, not synthetic fixtures.
- [ ] Full suite green; KNOWN_LIMITATIONS matches reality; WORKLOG current.

## 7. Working style that keeps this repo healthy

- Run the full suite before and after; report the true count.
- Prefer editing over rewriting; read a file before changing it.
- Add the trap test for every bug fixed; never edit an expected value to go green.
- Keep new methods/templates behind the existing contract (`Method(...)` with tests, second route, checks, sandbox parity, preset).
- Commit with a message that states what changed, what verifies it, and the test count; update docs in the same commit.
- If you are unsure whether something is a convention decision, stop and log it as a B-decision question rather than inventing a default.
