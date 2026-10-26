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
| Methods | `methods.py` `LIBRARY` | **36 methods**: id, tier, metric, unit, `test_names` order, claim ceiling, category, declared input names |
| Presets | `server.py` `PRESETS` | **38 presets**: ids and their method/input pairs |
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

**May build, additively:** presentation and interaction (`web/**`), new product routes/modules/storage/workflows that *use* the frozen computation through the session/preset/API contracts, product documentation, and product-surface entries in §6.

**Must not:**
- edit the frozen core modules listed in §2, `tests/**` (including the frozen contract fixture), or the factual content of `docs/**`;
- compute, round, re-derive, infer or adjust any business number, threshold, rating or claim wording;
- change caveats, honesty notices, refusal messages, tier labels, provenance notes or disclaimers;
- bypass the method library to produce a number (any displayed number must be an artifact or a preset input the user typed).

**Boundary note — persistence and the case workspace.** A durable case store should serialize the existing JSON contracts (`session.to_dict()`, the delivery `appendix`, the `reperform` bundle) and treat them as opaque documents. If persistence genuinely requires changing `session.py`/`orchestrator.py` behaviour, that is an unfreeze request to the owner, not a product change.

**Boundary note — new endpoints.** Additive endpoints are allowed when they only present or persist existing contract data. An endpoint that computes must call the method library through the existing pipeline; it may not reimplement a formula. Every new endpoint is listed in §6 and covered by the product-backend owner's tests.

## 5. Frozen inventory (details in code and `/api/methods`)

- **Methods (36).** T1: npv, irr, discounted_payback, breakeven, descriptive_stats, pearson, spearman, ols, ols_robust, welch_t, mann_whitney, anova, kruskal_wallis, chi_square, trend_forecast, ratio_analysis, paired_t, one_sample_t, two_way_anova, posthoc_pairwise, wacc, currency_convert, unit_economics, multi_product_breakeven, logistic_regression, reliability_alpha, multiple_comparison, power_analysis, missing_data_bounds, weighted_summary. T2: cost_benefit, cost_effectiveness, sroi, dcf_valuation, equity_bridge, management_accounts.
- **Presets (38).** See `GET /api/presets`; each preset names a method, a period, optional unit/currency and a valid declared input set.
- **Templates (T4/T2).** swot, five_forces, case_decision (registry-linked, evidence-only).
- **Test suite:** 618 tests. The guard adds three contract tests.

## 6. Product surface added by the design owner (B-080)

*Empty at freeze time. Add one row per new product route/feature: route or feature · what it does · which frozen contract it consumes. Never add a row that computes.*

| Product feature | Route / surface | Consumes (frozen) |
|---|---|---|
| — | — | — |
