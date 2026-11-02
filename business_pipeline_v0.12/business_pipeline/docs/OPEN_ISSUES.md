# Open issues (not fixed in this session)

## Item 11 — People computations defects
- 11a CEA icer key: code writes `icer_{slug}`; verify serializer/UI/render consumers expect same key.
- 11b labour-market tightness formula: code uses `vacancies / unemployment_rate`; docs say `vacancies / unemployed`. Resolve intended denominator/units.
- 11c tightness output: verify serialization/rounding/attachment to output.

## Item 12 — People computations test coverage
- New test module for 8 frameworks × 3 engines not added.

## Item 14 — Live verification
- 24-combo matrix not run against live deployment.

## Item 15 — 18 worksheets are built and offered on no shelf page
- Measured in session 7: `set(subjects.WORKSHEETS) - {every shelf's worksheets list}` = 18.
- The 16 marketing ones (MKT-01, MKT-03, MKT-05, MKT-07, MKT-08, MKT-09, MKT-10, MKT-11, MKT-12,
  MKT-13, MKT-14, MKT-16, MKT-17, MKT-19, MKT-20, MKT-21) show on the marketing page as record rows
  carrying the status "Worksheet" that cannot be opened; the shelf offers five (MKT-02, MKT-04,
  MKT-06, MKT-15, MKT-18).
- STR-19 (strategic positioning) and CHG-15 (change and organisation review) appear on no page in
  any form.
- MKT-07 (SERVQUAL) is deliberately hidden by B-198 until its block form is repaired.
- Not a defect in the engine: every one of them completes through the conductor. It needs a
  curriculum decision about which shelf owns each worksheet, then one line per shelf list.
- Ledgered as D-PLAN-02 in `qa/QA_DEFECTS.md`.

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
