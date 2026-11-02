# Open issues (not fixed in this session)

## Item 11 — People computations defects
- 11a CEA icer key: code writes `icer_{slug}`; verify serializer/UI/render consumers expect same key.
- 11b labour-market tightness formula: code uses `vacancies / unemployment_rate`; docs say `vacancies / unemployed`. Resolve intended denominator/units.
- 11c tightness output: verify serialization/rounding/attachment to output.

## Item 12 — People computations test coverage
- New test module for 8 frameworks × 3 engines not added.

## Item 14 — Live verification
- 24-combo matrix not run against live deployment.

## Full-suite failures (58)
- Project worksheets: `template_raci` was in both CANVAS_BLOCKS and MATRIX_META (fixed by removal from CANVAS). `template_customer_journey` was the same defect and is now fixed — it is a grid and is declared only as one (D-MKT-04, B-198). `template_servqual` is **still** declared in both; its marketing tile is hidden until its form is repaired (D-MKT-07), so the page offers five worksheets and the framework still completes through the conductor.
- Value-chain (and RFM/SERVQUAL/social-media/STP/TAM): block key naming mismatch between implementation (long names: inbound_logistics, firm_infrastructure, …) and tests (short names: inbound, infrastructure, …). Needs coordinated rename.
- Sources: Brave→Firecrawl fallback test failing (env/API key handling).
- Project-worksheet registration guards and model-prompt tests: investigate.
- Pre-existing network-dependent failures: report, do not fix silently.

## Research & statistics / subjects
- All subject backends pass; no missing wiring detected.
- Chat paper completion supported by tests.

## Notes
- Scaffolding files deleted: install_people_profiles.py, _people_profiles_source.py.
- Test command: `PYTHONPATH=src python -m pytest` from business_pipeline_v0.12/business_pipeline.
