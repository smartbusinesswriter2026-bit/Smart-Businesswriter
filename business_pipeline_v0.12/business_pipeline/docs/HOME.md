# Home — map of the repository

**Start here when you are lost.** This is a curated map (a "MOC" — map of content), not a duplicate: it points at the document or module that actually holds the truth. Last verified with build **0.38**, **484 tests**, 2026-10-21. Update the count and date when you change them.

## Read in 30 seconds

| You want to… | Go to |
|---|---|
| **Use** the system | [`../README.md`](../README.md) — commands, workbench, API routes |
| **Change** the system safely | [`CONTRIBUTORS.md`](CONTRIBUTORS.md) — the rules any model or person must follow |
| **Know what is decided / open** | [`DECISIONS.md`](DECISIONS.md) — every B-xxx with status |
| **Know what is broken or absent** | [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) + [`PRODUCT_GAP_MAP.md`](PRODUCT_GAP_MAP.md) |
| **Know what happened** | [`WORKLOG.md`](WORKLOG.md) — append-only session log |
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
| Add a catalogue record / regenerate registry | `docs/STAGE6_REPORT.md` | `src/bp/catalogue_import.py`, `src/bp/data/registry_v0_2.json` |
| Compute ratios from a balance sheet / income statement | `KNOWN_LIMITATIONS.md` (B-056) | `src/bp/methods.py` (`ratio_analysis`), preset `ratios` |
| Review what a deliverable claims | `src/bp/claims.py` | claim ceiling per method in `LIBRARY` |

## 2. By module

Everything lives under `src/bp/`. "Authority" is the manual section or decision that governs it.

| Module | Owns | Main tests | Authority |
|---|---|---|---|
| [`orchestrator.py`](../src/bp/orchestrator.py) | Stage order, `Pipeline.start/resume/run`, `Delivery`, `Pause`, `_appendix`/`_checks` | `test_pipeline`, `test_stage5` | steps 4, 5.2 (P4, P8) |
| [`methods.py`](../src/bp/methods.py) | T1 method library, contract, independent second routes, assumption checks | `test_stage5`, `test_groups`, `test_correlation`, `test_regression`, `test_anova`, `test_chisquare`, `test_forecast`, `test_ratio`, `test_multicomp`, `test_power`, `test_missing`, `test_weighted` | 5.3, 5.5, 9B; B-042/B-043/B-056/B-060/B-061/B-062/B-063 |
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
| [`literature.py`](../src/bp/literature.py) | DOI retrieval + verification, response audit, durable retrieval log, provisional citation | `test_literature`, `test_literature_api`, `test_literature_log` | B-040, B-054, B-058; REW §9 |
| [`server.py`](../src/bp/server.py) | Stdlib HTTP API, `PRESETS` | `test_session_api`, `test_literature_api` | B-002 |
| [`../web/index.html`](../web/index.html) | Workbench shell (vanilla JS) | route tests assert key strings | — |

## 3. By capability and status

| Capability | Status | Decisions |
|---|---|---|
| Deterministic compute → verified report pipeline | Built, T1 methods with independent routes | B-003/B-004 |
| Framework-only (T4) answers + registry | Built; catalogue records unreviewed | B-021, B-023, B-026, B-027 |
| Model assistance (proposals only) | Built; quality unmeasured | B-031, B-036, B-037, B-038, B-039, B-041 |
| Statistics: descriptive, correlation, regression, two-group ANOVA/KW, chi-square, multiple-comparison correction, power/minimum effect, missing-data bounds, weighted summaries | Built; conventions `[UNVERIFIED]`; 9B.3 disclosure layer in every delivery | B-042, B-057, B-060, B-061, B-062, B-063 |
| Forecasting: linear trend + holdout | Built; linear only | B-043 |
| Management accounts (ledger → statements) | Built on the custom kernel; T2 until B-032 | B-032, B-044–B-051 |
| Ratio analysis (statements) | Built, T1; descriptive only, no benchmarks | B-056 |
| Literature retrieval/verification | Built; PROVISIONAL match rule; durable retrieval log and provisional citations | B-040, B-054, B-058 |
| Research & Evidence Workflow (REW) | Manual ratified (R11); **no stage built** | B-053, R1–R10 proposals |
| Taxation | Deliberately deferred | B-052 |
| Ingestion (PDF/Excel/SPSS) | Not built | P0 gap map |
| DCF/WACC, 9B.3 honesty upgrades, breadth templates | Not built | P1/P2 gap map; B-005/B-028 gates |

## 4. The documentation spine

| Document | Kind | Rule |
|---|---|---|
| [`CONTRIBUTORS.md`](CONTRIBUTORS.md) | Living — how to work here | Update when a rule changes |
| [`HOME.md`](HOME.md) | Living — this map | Add a row when you add a module/document |
| [`WORKLOG.md`](WORKLOG.md) | Append-only log | Never rewrite; newest first |
| [`DECISIONS.md`](DECISIONS.md) | Append-only decision register | Supersede, never delete; status must be current |
| [`CHANGELOG.md`](CHANGELOG.md) | Append-only build log | Newest first; one entry per increment |
| [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) | Living | Remove a limitation only when a test proves otherwise |
| [`PRODUCT_GAP_MAP.md`](PRODUCT_GAP_MAP.md) | Living backlog | Status changes only with verification + commit |
| [`RESEARCH_EVIDENCE_WORKFLOW.md`](RESEARCH_EVIDENCE_WORKFLOW.md) | Living manual, ratified R11 | Proposals stay tagged until ratified |
| [`MODEL_PROVIDER_REPORT.md`](MODEL_PROVIDER_REPORT.md), `STAGE*_REPORT.md` | Historical snapshots | Never rewrite; describe as "at the time of the stage" |
| [`sources/`](sources/) | Supplied authority material | **Read-only** — never edit; amend via decisions |

## 5. Conventions for this map

- Plain Markdown relative links only (no Obsidian `[[wikilinks]]`) so it renders in the repo and the workbench alike.
- One row per module or document; link the authoritative file, never a copy of its content.
- Every new document gets a row in §4 and (if it is part of the work) a WORKLOG entry.
- Every new module gets a row in §2 with its main tests and the decision that governs it.
- If a link target is deleted, this map is updated in the same commit — a broken map is worse than no map.
