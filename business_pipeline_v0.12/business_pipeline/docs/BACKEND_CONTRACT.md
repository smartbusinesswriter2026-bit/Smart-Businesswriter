# Backend contract — frozen core, product-backend lane

**Status: the core deterministic backend is FROZEN** (B-079, owner instruction 2026-10-21). The product backend is the design owner's lane (B-080), extending this contract without changing it.

Read with: [`CONTRIBUTORS.md`](CONTRIBUTORS.md) §1A (ownership), [`HOME.md`](HOME.md) (map), [`DECISIONS.md`](DECISIONS.md) B-066/B-079/B-080.

## 1. What "frozen" means

The public behaviour of the deterministic core no longer changes except by a deliberate **unfreeze** (§3). Frozen means:

- the same inputs produce the same spec hash, outputs, checks and delivery;
- no number is computed outside the method library;
- the declared contract of every method (tier, metric, unit, test names and order, claim ceiling, category, input names) is fixed;
- the API route surface and preset surface are fixed;
- the delivery shape (`report` + `appendix`) is fixed.

The guard is `tests/test_frozen_contract.py` against `tests/fixtures/frozen_contract.json`. If the fixture and the code disagree, the test fails with a message naming the freeze. **Do not edit the fixture to turn the test green** — that is the unfreeze, and it needs the owner.

## 2. What is frozen (the core)

| Area | Modules | Contract |
|---|---|---|
| Flow and stages | `orchestrator.py`, `session.py` | create → confirm/reject → deliver; stages, checkpoints, blocked reasons, event log |
| Spec | `spec.py` | draft → confirm → frozen + hashed; sensitivity ranges, assumptions, thresholds |
| Verification | `methods.py` (library + checks), `sandbox.py`, `sandbox_child.py` | second implementation routes, frozen check names and order, sandbox parity, fail-closed refusal |
| Numbers and provenance | `quantity.py`, `artifacts.py`, `claims.py` | typed quantities, source/period/entity/scope, claim ceiling wording, licence checks |
| Re-performance | `reperform.py`, `envpin.py` | delivered bundle re-runs and matches, environment fingerprint pinned |
| Methods | `methods.py` `LIBRARY` | **124 methods**: id, tier, metric, unit, `test_names` order, claim ceiling, category, declared input names |
| Presets | `server.py` `PRESETS` | **126 presets**: ids and their method/input pairs |
| API (read/write) | `server.py` | **12 route families**: `/`, `/api/presets`, `/api/methods`, `/api/frameworks`, `/api/templates`, `/api/currencies`, `/api/assist`, `/api/sessions`, `/api/ingest`, `/api/literature/sources`, `/api/literature/verify`, `/api/literature/log`, `/api/literature/drift` |
| Delivery shape | `orchestrator.py` | `report` text + `appendix` with `artifacts`, `tests`, `honesty`, `limitations`, `assumptions`, `caveats`, `reperform`, `spec_hash`, `tier`, `code_hash`, `sandbox`, `environment` |
| Deterministic inputs | `ingest.py`, `currency.py`, `literature.py` | CSV/XLSX → typed table + provenance; ISO 4217 + declared-rate conversion; DOI retrieval audit + APA/Harvard |
| Accounting core | `ledger.py`, `schedules.py`, `accounts.py`, `reconcile.py`, `report.py` | double-entry, two-route cash flow, closing, statements, exports |
| Model boundary | `llm.py`, `assist.py` | proposals-only validation; the model never writes a number |

Invariants that no change may break: numbers only from code; a number is not trusted until it survives a second route; checks never loosened or deleted; claim wording never upgraded beyond the tier; unknown/unsupported input blocks with a reason; declared-but-unverified inputs stay labelled; outputs are deterministic and re-performable.

## 3. Unfreeze policy

An unfreeze is a decision, not a commit:

1. **Owner approval** for any change in behaviour (a bug fix that restores the declared behaviour is not an unfreeze, but it must ship with a trap test that fails on the old code).
2. **Computation owner** (DeepSeek, B-066) writes the B-decision, changes the code and tests, and updates `tests/fixtures/frozen_contract.json` **in the same commit**.
3. **Product-backend owner** (MiniMax, B-080) never edits frozen files or the fixture to make a UI need pass. It records the need in `WORKLOG.md` tagged `[design]`; the owner instructs the computation owner.
4. Cross-domain features land in two commits: computation contract first, presentation second (B-066).

## 4. Product-backend lane (B-080, design owner)

**May build, additively:** presentation and interaction (`web/**`), a **new product package `src/bp/product/**`** (new files only, importing the frozen core), **new flat product test files `tests/test_product_*.py`** (existing tests and fixtures are frozen), new product routes/modules/storage/workflows that *use* the frozen computation through the session/preset/API contracts, product documentation, and product-surface entries in §6. Per increment the design owner may also update **only the count/version digits** in `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, add one `CHANGELOG.md` entry and one `WORKLOG.md` entry tagged `[product]`, and its own §6 rows; the computation owner verifies those digits at review. The sequence is in [`PRODUCT_BACKEND_PLAN.md`](PRODUCT_BACKEND_PLAN.md) (B-081).

**Must not:**
- edit the frozen core modules listed in §2, `tests/**` (including the frozen contract fixture), or the factual content of `docs/**`;
- compute, round, re-derive, infer or adjust any business number, threshold, rating or claim wording;
- change caveats, honesty notices, refusal messages, tier labels, provenance notes or disclaimers;
- bypass the method library to produce a number (any displayed number must be an artifact or a preset input the user typed).

**Boundary note — persistence and the case workspace.** A durable case store should serialize the existing JSON contracts (`session.to_dict()`, the delivery `appendix`, the `reperform` bundle) and treat them as opaque documents. If persistence genuinely requires changing `session.py`/`orchestrator.py` behaviour, that is an unfreeze request to the owner, not a product change.

**Boundary note — new endpoints.** Additive endpoints are allowed when they only present or persist existing contract data. An endpoint that computes must call the method library through the existing pipeline; it may not reimplement a formula. Every new endpoint is listed in §6 and covered by the product-backend owner's tests.

## 5. Frozen inventory (details in code and `/api/methods`)

- **Methods (124).** T1: npv, irr, discounted_payback, breakeven, descriptive_stats, pearson, spearman, ols, ols_robust, welch_t, mann_whitney, anova, kruskal_wallis, chi_square, trend_forecast, ratio_analysis, paired_t, one_sample_t, two_way_anova, posthoc_pairwise, wacc, currency_convert, unit_economics, multi_product_breakeven, logistic_regression, reliability_alpha, multiple_comparison, power_analysis, missing_data_bounds, weighted_summary, time_value, loan_amortization, bond_analysis, capm, dupont_analysis, working_capital, portfolio_analysis, project_metrics, risk_metrics, fx_parity, leverage_analysis, scenario_analysis, demand_supply_equilibrium, elasticity, tax_incidence, price_control, market_concentration, cost_curves, profit_maximization, market_power, national_income, growth_rate, inflation_cpi, unemployment_rate, money_multiplier, fiscal_multiplier, budget_debt, externality_pigouvian, public_good, social_welfare, gini_coefficient, poverty_measures, tax_progressivity, optimal_pollution, output_gap_okun, comparative_advantage, tariff_welfare, exchange_rate_ppp, interest_rate_parity, balance_of_payments, hdi, expected_utility, prospect_theory, labour_market, price_discrimination, cournot_duopoly, difference_in_differences, nash_equilibrium, panel_regression, instrumental_variables, regression_discontinuity, probit, trend_analysis, market_sizing, startup_capital, cash_runway, pricing_decision, return_on_investment, sales_projection, cap_table_round, sales_funnel, cohort_retention, demand_curve, purchase_intent, standard_cost_variances, inventory_policy, queue_analysis, capacity_analysis, campaign_efficiency, attribution_split, channel_economics, email_list_health, social_engagement, web_analytics, ab_test_two_proportion, cpm_schedule, earned_value, oee_analysis, process_control, abc_costing, sales_variances, line_balancing, tax_declared. T2: cost_benefit, cost_effectiveness, sroi, dcf_valuation, equity_bridge, management_accounts, trial_balance_check, multiples_valuation, option_pricing. **breakeven is additive since B-104:** the quantity is unchanged and the revenue, contribution-margin, margin-of-safety and target-profit figures appear only when those optional inputs are declared.
- **Presets (126).** See `GET /api/presets`; each preset names a method, a period, optional unit/currency and a valid declared input set.
- **Templates (T4/T2).** swot, five_forces, case_decision (registry-linked, evidence-only) and, added in B-108, the canvases `template_business_model_canvas`, `template_lean_canvas`, `template_value_proposition_canvas` and `template_marketing_plan` (structure and evidence audit only; no score or invented content).
- **Test suite:** 1419 tests. The guard adds three contract tests.

## 6. Product surface added by the design owner (B-080)

*Empty at freeze time. Add one row per new product route/feature: route or feature · what it does · which frozen contract it consumes. Never add a row that computes.*

| Product feature | Route / surface | Consumes (frozen) |
|---|---|---|
| Local durable case store (`src/bp/product/cases.py`) | `BP_CASES_DIR` (default `cases/`), one JSON bundle per case, atomic writes | `session.to_dict()`, the delivery `report` + `appendix` and the re-perform bundle, stored as opaque documents |
| Case listing and retrieval (wired into the frozen server in 0.60, B-085) | `GET /api/cases`, `GET /api/cases/{id}` | the stored case bundles, returned verbatim |
| Case capture and deletion (wired into the frozen server in 0.60, B-085) | `POST /api/cases`, `DELETE /api/cases/{id}` | the session/delivery bundle supplied by the caller, stored as given |
| Self-contained HTML export of a stored case | `bp.product.export.export_html(bundle, path)` (standard library only) | the stored report text and the stored artifact values, copied and not recomputed |
| Case versions (B-086) | `GET/POST /api/cases/{id}/versions`, `GET /api/cases/{id}/versions/{n}`; `bp.product.versions` | immutable version envelopes over the stored bundle, with canonical bundle hashes |
| Multi-period comparison (B-086, Option A) | `GET /api/cases/{id}/compare?versions=1,2`; `bp.product.compare` | stored versions only: rows aligned by metric, stored values verbatim, missing metrics reported as not computed |
| Reviewer sign-off (B-086) | `POST/GET /api/cases/{id}/signoff`; `bp.product.signoff` | version hashes + the owner-approved Option-A signature text, append-only |
| Health and request log (B-088) | `GET /api/health`; `bp.product.ops`; additive timing hook in the server | case-store counts, state/log paths, sandbox/model flags; JSONL of method/query-free path/status/duration only (opt-in via `BP_REQUEST_LOG`) |
| Case backup/restore (B-088) | `POST /api/cases/backup`, `POST /api/cases/restore`, `GET /api/cases/backups`; `bp.product.ops` | the case store's JSON documents only, with a manifest + SHA-256; zip-slip/non-JSON refused |
| Local launcher (B-088) | `scripts/serve.py` (`--port`, `--host`, `--no-sandbox`, `--check`) | starts the frozen server; resolves `BP_CASES_DIR`/`BP_STATE_DIR`/`BP_REQUEST_LOG` |
| Charts, spreadsheets, diagrams (B-089) | `POST /api/cases/{id}/render`, `POST /api/cases/{id}/export`; `bp.product.charts`, `.spreadsheets`, `.diagrams` | stored artifact values only: SVG charts and structure-only diagrams with digit-free labels, CSV/SpreadsheetML cells copied as strings; deterministic; no model call |
| Subject index and Calculator (B-090, B-091, B-092) | `GET /api/cases/subjects`, `GET /api/cases/subjects/{id}`, `GET /api/cases/calculator`, `GET /api/cases?subject=<id>`; `bp.product.subjects`, `scripts/generate_subjects.py` | **launcher descriptors only**: frozen preset ids, method ids and template ids, grouped by business subject and business function; each subject also carries a presentation `icon` key and its gallery counts. The rail lists the eleven subjects (Entrepreneurship and Project management included) with icons and pins the Calculator at the foot; Case, Catalogue, Assistant and Status are not rail items, and in 0.67 the Catalogue and Assistant **panels** were removed from the served UI too (their backend routes and tests remain), while Status is reached from the health pill. Stored case summaries are filtered by their recorded method. No formula, no scoring, no product-layer arithmetic; the Calculator calls the normal `POST /api/sessions` -> `confirm` pipeline |
| Free market-data lookups (B-106, B-109) | `GET /api/market/fx`, `/api/market/riskfree`, `/api/market/quote`, `/api/market/fundamentals`, `/api/market/filings`, `/api/market/macro`; `bp.product.marketdata` | published FX, Treasury, Alpha Vantage quote, SEC EDGAR filings/XBRL fundamentals and World Bank values with source, as-of date and response SHA-256 (API keys redacted); no method input is filled |
| Document text reading (B-107, B-110) | `POST /api/intake/{id}/extract`, `GET /api/intake/{id}/text`; `bp.product.documents` | the stored file bytes; optional `pypdf`/`pypdfium2`/Tesseract readers (text layer or OCR); extracted text is unverified and never enters a method input |

**Wiring note.** The `/api/cases` routes are served by the frozen server through an additive extension (B-085): `server.py` imports `bp.product.api`, delegates GET/POST/DELETE to `api.handle`, and adds `do_DELETE`; the frozen route fixture is unchanged because the product surface is tracked **here**, not among the frozen 12. New product routes are added in `product/api.py` and need no further core edit. The store holds an opaque bundle; the product layer computes nothing.

**Planned for Phase 2b/2c** (not yet shipped; sequence and acceptance in [`PRODUCT_BACKEND_PLAN.md`](PRODUCT_BACKEND_PLAN.md)): deliverable graphics and spreadsheets — **deterministic SVG charts and diagram templates rendered from stored artifacts, plus CSV/XLSX table export (B-087)**; ops/observability counters; offline packaging. The **AI-use disclosure export is deferred by the owner (D3)** and is not planned here until its audience and wording are decided. None of these may compute a number.
