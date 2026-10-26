# Home — map of the repository

**Start here when you are lost.** This is a curated map (a "MOC" — map of content), not a duplicate: it points at the document or module that actually holds the truth. Last verified with build **0.56**, **625 tests**, 2026-10-21. Update the count and date when you change them.

## Read in 30 seconds

| You want to… | Go to |
|---|---|
| **Use** the system | [`../README.md`](../README.md) — commands, workbench, API routes |
| **Change** the system safely | [`CONTRIBUTORS.md`](CONTRIBUTORS.md) — the rules any model or person must follow |
| **Know what is decided / open** | [`DECISIONS.md`](DECISIONS.md) — every B-xxx with status |
| **Know what is broken or absent** | [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) + [`PRODUCT_GAP_MAP.md`](PRODUCT_GAP_MAP.md) |
| **Know what happened** | [`WORKLOG.md`](WORKLOG.md) — append-only session log |
| **Know what is parked and why** | [`PARKED_QUEUE.md`](PARKED_QUEUE.md) — frontier-model work; do not start without the owner's grant |
| **Know what is frozen / what the product may rely on** | [`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md) — frozen core, unfreeze policy, product-backend lane (B-079/B-080) |
| **Understand the research capability** | [`RESEARCH_EVIDENCE_WORKFLOW.md`](RESEARCH_EVIDENCE_WORKFLOW.md) — ratified living manual (R11) |

## 1. By task

| Task | Read first | Then touch |
|---|---|---|
| Run the workbench | `README.md` | `src/bp/server.py` (`PRESETS`), `web/index.html` |
| Add a statistical method | `CONTRIBUTORS.md` §3 | `src/bp/methods.py`, golden fixture, `tests/test_sandbox.py` `CASES`, `PRESETS` |
| Fix a wrong number | `CONTRIBUTORS.md` §4 | The method's impl **and** its independent second route; add the trap test |
| Change what the model may do | `CONTRIBUTORS.md` §5, `DECISIONS.md` B-037/B-038 | `src/bp/llm.py`, `src/bp/assist.py`, privacy notice |
| Change retrieval/citation | `RESEARCH_EVIDENCE_WORKFLOW.md` §9, B-040/B-054 | `src/bp/literature.py` + both literature test files |
| Change the accounting engine | `CONTRIBUTORS.md` §4/§5, B-032/B-044–B-051 | `src/bp/ledger.py`, `schedules.py`, `accounts.py`, `reconcile.py`, `report.py` |
| Add a framework template | `DECISIONS.md` B-028 (owner decision first!) | `src/bp/templates.py`, registry, `tests/test_templates.py` |
| Ingest a data file | `KNOWN_LIMITATIONS.md` (B-065/B-076) | `src/bp/ingest.py`, `POST /api/ingest`, `python -m bp.ingest` |
| Add a catalogue record / regenerate registry | `docs/STAGE6_REPORT.md` | `src/bp/catalogue_import.py`, `src/bp/data/registry_v0_2.json` |
| Compute ratios from a balance sheet / income statement | `KNOWN_LIMITATIONS.md` (B-056) | `src/bp/methods.py` (`ratio_analysis`), preset `ratios` |
| Review what a deliverable claims | `src/bp/claims.py` | claim ceiling per method in `LIBRARY` |

## 2. By module

Everything lives under `src/bp/`. "Authority" is the manual section or decision that governs it.

| Module | Owns | Main tests | Authority |
|---|---|---|---|
| [`orchestrator.py`](../src/bp/orchestrator.py) | Stage order, `Pipeline.start/resume/run`, `Delivery`, `Pause`, `_appendix`/`_checks` | `test_pipeline`, `test_stage5` | steps 4, 5.2 (P4, P8) |
| [`methods.py`](../src/bp/methods.py) | T1 method library, contract, independent second routes, assumption checks | `test_stage5`, `test_groups`, `test_correlation`, `test_regression`, `test_anova`, `test_chisquare`, `test_forecast`, `test_ratio`, `test_multicomp`, `test_power`, `test_missing`, `test_weighted`, `test_inference_more`, `test_factorial_posthoc`, `test_economics`, `test_appraisal`, `test_logit_reliability`, `test_investment`, `test_valuation`, `test_currency`, `test_literature_failover` | 5.3, 5.5, 9B; B-042/B-043/B-056/B-060/B-061/B-062/B-063/B-067/B-068/B-070/B-077 |
| [`spec.py`](../src/bp/spec.py) | Problem Spec: draft → confirm → frozen + hashed | `test_stage5` | 5.2 |
| [`session.py`](../src/bp/session.py) | Session/work-plan states, checkpoints, JSON contracts | `test_session_api` | 4, 5.2 |
| [`sandbox.py`](../src/bp/sandbox.py), [`sandbox_child.py`](../src/bp/sandbox_child.py) | Guarded subprocess execution, parent/child protocol | `test_sandbox` | 5.4 |
| [`envpin.py`](../src/bp/envpin.py) | Environment fingerprint (what actually ran) | `test_sandbox` | 5.4 |
| [`reperform.py`](../src/bp/reperform.py) | Re-run a delivered bundle and compare | `test_sandbox` | P9 |
| [`artifacts.py`](../src/bp/artifacts.py) | Immutable hashed artifacts with metric/period/entity/scope | `test_stage5` | 5.4, 6, App. B |
| [`quantity.py`](../src/bp/quantity.py) | Decimal typed quantities + provenance tags | `test_stage5` | 6 |
| [`claims.py`](../src/bp/claims.py) | Wording ceilings, `license_check` | `test_stage5` | 7 |
| [`templates.py`](../src/bp/templates.py) | T4 structure-only templates (SWOT, Five Forces) | `test_templates` | B-027, charter 6 |
| [`case_decision.py`](../src/bp/case_decision.py) | Business-case NPV comparison (T2) | `test_case_decision` | charter Stage 4 |
| [`registry.py`](../src/bp/registry.py), [`catalogue_import.py`](../src/bp/catalogue_import.py) | Catalogue v0.2 registry (140 records, all unreviewed) | `test_registry`, `test_framework_flow` | B-021/B-023/B-026 |
| [`ledger.py`](../src/bp/ledger.py) | Double-entry kernel, trial balance, statements, two-route cash flow, closing | `test_ledger`, `test_cashflow`, `test_closing` | 9.1–9.5; B-045/B-046 |
| [`schedules.py`](../src/bp/schedules.py) | Depreciation, amortization, accruals | `test_schedules` | B-044, B-050 |
| [`accounts.py`](../src/bp/accounts.py) | Declarative engagement spec, account mapping checkpoint, `management_accounts` (T2) | `test_accounts` | B-047, B-049 |
| [`reconcile.py`](../src/bp/reconcile.py) | Statement-vs-ledger reconciliation | `test_reconcile` | B-048 |
| [`report.py`](../src/bp/report.py) | Plain-text statement exports | `test_report` | B-051 |
| [`llm.py`](../src/bp/llm.py) | Provider boundary (DeepSeek/OpenAI-compatible/Anthropic) | `test_assist` | B-031/B-036/B-038/B-041 |
| [`assist.py`](../src/bp/assist.py) | Model proposals under code validation | `test_assist` | 10, 11; B-037 |
| [`evaluate.py`](../src/bp/evaluate.py) | Held-out evaluation scaffold (synthetic fixtures) | `test_evaluate` | B-039 |
| [`currency.py`](../src/bp/currency.py) | ISO 4217 registry with minor units; declared-rate conversion; no FX source | `test_currency` | B-069 |
| [`ingest.py`](../src/bp/ingest.py) | Structured-file ingestion: CSV/TSV + XLSX to a typed table with provenance; XLSX sheet selection and a declared merged-cell policy (refuse by default); PDF/OCR/SPSS refused | `test_ingest`, `test_ingest_api` | B-065, B-076; gap map P0 |
| [`literature.py`](../src/bp/literature.py) | DOI retrieval + verification, response audit, durable retrieval log, provisional citation | `test_literature`, `test_literature_api`, `test_literature_log` | B-040, B-054, B-058; REW §9 |
| [`server.py`](../src/bp/server.py) | Stdlib HTTP API, `PRESETS` | `test_session_api`, `test_literature_api` | B-002 |
| [`../web/index.html`](../web/index.html) | Workbench shell (vanilla JS) | route tests assert key strings | — |

## 3. By capability and status

| Capability | Status | Decisions |
|---|---|---|
| Deterministic compute → verified report pipeline | Built, T1 methods with independent routes | B-003/B-004 |
| Core deterministic backend | **FROZEN** (B-079): method contracts, presets, API routes and delivery shape pinned by `test_frozen_contract` | B-079 |
| Product backend / product surface | Delegated to the design owner (B-080): additive features over the frozen core; numbers and claim wording stay computation-owned | B-080 |
| Framework-only (T4) answers + registry | Built; catalogue records unreviewed | B-021, B-023, B-026, B-027 |
| Model assistance (proposals only) | Built; quality unmeasured | B-031, B-036, B-037, B-038, B-039, B-041 |
| Statistics: descriptive, correlation, regression, paired/one-sample t, two-group ANOVA/KW, chi-square, multiple-comparison correction, power/minimum effect, missing-data bounds, weighted summaries | Built; conventions `[UNVERIFIED]`; 9B.3 disclosure layer in every delivery | B-042, B-057, B-060, B-061, B-062, B-063, B-067 |
| Forecasting: linear trend + holdout | Built; linear only | B-043 |
| Management accounts (ledger → statements) | Built on the custom kernel; T2 until B-032 | B-032, B-044–B-051 |
| Ratio analysis (statements) | Built, T1; descriptive only, no benchmarks | B-056 |
| Valuation: WACC, DCF, equity bridge | Built, T1/T2; declared timing (end or mid-year), declared claims only, no tax computed | B-068, B-078 |
| Capital budgeting: NPV, IRR, discounted payback | Built, T1; IRR refuses multiple sign changes, payback blocks when the outlay is never recovered | B-077 |
| Logistic regression, Cronbach's alpha | Built, T1; separation blocks, listwise deletion declared | B-074 |
| Appraisal: CBA, CEA, SROI | Built, T2; declared valuations, no monetisation or threshold invented | B-073 |
| Unit economics / multi-product break-even | Built, T1; declared costs, churn and mix | B-072 |
| Currencies | Built: 160+ ISO codes, per-currency precision, declared-rate conversion; no FX retrieval | B-069 |
| Literature retrieval/verification | Built; PROVISIONAL match rule; durable log with failover attempts, APA/Harvard citations, drift sweep | B-040, B-054, B-058, B-059, B-064 |
| Research & Evidence Workflow (REW) | Manual ratified (R11); **no stage built** | B-053, R1–R10 proposals |
| Taxation | Deliberately deferred | B-052 |
| Ingestion (CSV/TSV/XLSX) | Built (B-065, B-071, B-076); sheet selection + declared merged-cell policy; PDF/scan/OCR and SPSS refused explicitly | P0 gap map |
| Statistics remainder: range procedures, unbalanced/ANCOVA/repeated measures, clustering, factor analysis, non-linear time series | **Parked** for the frontier-model lane — registered, not built | B-075; [`PARKED_QUEUE.md`](PARKED_QUEUE.md) |
| Breadth templates | Not built | B-028 gate |

## 4. The documentation spine

| Document | Kind | Rule |
|---|---|---|
| [`CONTRIBUTORS.md`](CONTRIBUTORS.md) | Living — how to work here | Update when a rule changes |
| [`HANDOFF.md`](HANDOFF.md) | Handoff brief for the next coding agent | Read first after CONTRIBUTORS; keep current when state changes |
| [`HOME.md`](HOME.md) | Living — this map | Add a row when you add a module/document |
| [`WORKLOG.md`](WORKLOG.md) | Append-only log | Never rewrite; newest first |
| [`PARKED_QUEUE.md`](PARKED_QUEUE.md) | Living — parked frontier-model computation queue | Remove an item only when the owner un-parks it and it ships |
| [`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md) | Living — frozen core contract + product-backend lane | Frozen surface changes only by an owner-approved unfreeze; product additions recorded in its §6 |
| [`PRODUCT_BACKEND_PLAN.md`](PRODUCT_BACKEND_PLAN.md) | Living — product-backend sequence, slices and boundary rules | Update when a phase ships or an owner decision resolves (B-081) |
| [`DECISIONS.md`](DECISIONS.md) | Append-only decision register | Supersede, never delete; status must be current |
| [`CHANGELOG.md`](CHANGELOG.md) | Append-only build log | Newest first; one entry per increment |
| [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) | Living | Remove a limitation only when a test proves otherwise |
| [`PRODUCT_GAP_MAP.md`](PRODUCT_GAP_MAP.md) | Living backlog | Status changes only with verification + commit |
| [`RESEARCH_EVIDENCE_WORKFLOW.md`](RESEARCH_EVIDENCE_WORKFLOW.md) | Living manual, ratified R11 | Proposals stay tagged until ratified |
| [`MODEL_PROVIDER_REPORT.md`](MODEL_PROVIDER_REPORT.md), `STAGE*_REPORT.md` | Historical snapshots | Never rewrite; describe as "at the time of the stage" |
| [`SOURCE_INVENTORY.md`](SOURCE_INVENTORY.md) | Historical snapshot — which supplied documents had been read, at the time | Never rewrite; it records that point in time, not the current inventory |
| [`proposals/`](proposals/) | Draft proposals for owner review (not authority) | Marked DRAFT; never cite as a decision, and never as the computation owner's advice |
| [`sources/`](sources/) | Supplied authority material | **Read-only** — never edit; amend via decisions |

## 5. Conventions for this map

- Plain Markdown relative links only (no Obsidian `[[wikilinks]]`) so it renders in the repo and the workbench alike.
- One row per module or document; link the authoritative file, never a copy of its content.
- Every new document gets a row in §4 and (if it is part of the work) a WORKLOG entry.
- Every new module gets a row in §2 with its main tests and the decision that governs it.
- If a link target is deleted, this map is updated in the same commit — a broken map is worse than no map.
