# Stage 0 report and first slice (SR-BUILD-001 v0.1)

## Source inventory
| Source | Version / date | Status |
|---|---|---|
| business_pipeline.docx (architecture manual) | **header says v0.1 (2026-10-19)**; diagram PDF and addendum cite **v0.3** | CONFLICT: content read is v0.1 only (D-001..D-010). v0.3 decisions D-011..D-016 (incl. D-012 SPSS policy) were not readable. |
| business_pipeline_architecture_preview.pdf | diagram v0.3, 2026-10-19 | Read |
| Business_Pipeline_Agentic_Integration_Review_v0.1.docx | addendum, proposed | Read; not DECIDED |
| Unified_Adaptive_Workbench_UI_Review_v0.1.docx | proposed | Read |
| Smart_Researcher_Adaptive_Workbench_Prototype_v0.1.html | mockup, no backend | Read |
| Initial_Build_Charter v0.1 | this guide | Read |
| **Smart Researcher research-pipeline manuals** | n/a | **MISSING** (Stage 7 blocked) |
| **Frameworks & Quantitative Methods Catalogue v0.2** | n/a | **MISSING** (Stage 6 blocked) |
| Existing application code / tests | none found | Greenfield |

## Capability map
- Specified, now implemented (this slice): typed Decimal quantities and provenance tags (s6); hashed immutable artifacts with label-matched references (s6); frozen/hashed Problem Spec with versioned amendments (5.2); T1 methods NPV and break-even with independent reference implementations (5.3); frozen test plan, amendment budget N=3 with escalation (5.5); decision-flip on discount rate (5.6); digit ban + reference tokens + draft audit (s11); claim-wording ceilings (s7, illustrative phrase lists); fail-closed delivery (P8); event log the UI can read (s11).
- Specified, not implemented: accounting kernel and invariants (s9, Stage 8), statistics module (9B), real model-assisted intake/formalization/drafting, sandbox with pinned env and no network, T2/T3 tiers, case workspace, learning loop, workbench UI backend, claim typing by a reviewer model, ingestion controls for PDFs.
- Implemented but thin: spec confirmation is a callback; the test plan is frozen by name only; the builder is a stub callable; sandbox isolation is NOT implemented (tests use in-process Python).

## Conflicts / open questions
1. Manual version mismatch (v0.1 header vs v0.3 references). Need the v0.3 file.
2. Ledger engine (s9.2 spike), stakes/first users, meaning of "papers": still OPEN in manual; untouched.
3. Charter says Stage 0 only, then report; you asked to build, so I added a minimal Stage 1/3/4 foundation. No domain beyond NPV/break-even.
4. Amendment budget N=3 is PROVISIONAL; claim phrase lists are my placeholders [UNVERIFIED], not manual text.

## Recommended next stage
Provide the missing manuals and v0.3 docx. Then Stage 2 (workbench shell wired to `Pipeline.events`), and Stage 5 additions (regression with diagnostics, forecasting) with golden tests.

## Decisions needing the product owner
Stack/deployment for the UI; sandbox technology; first-slice confirmation (business case + NPV/break-even vs another).
