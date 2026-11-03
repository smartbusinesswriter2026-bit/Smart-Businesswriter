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

## Item 16 — full-suite failures inherited by the statements-tile lane (2026-11-03)
- Measured at the end of statements-tile commit 1: `discover -s tests` = **3246 tests, 9 failures**.
  None is in `test_accounts`, `test_ledger`, `test_frozen_contract` or `test_product_boundary`
  (199 tests, OK), and none touches `accounts.ratio_figures` / `balance_sheet_groups`.
- **Fail in isolation** (so they are real defects, not order artefacts), all in the in-flight lanes:
  `test_paper_documents.DocumentRouteTest.test_generating_a_paper_saves_it_to_the_store`;
  `test_product_profile_cues.ProfileCueReachabilityTest.test_every_researched_block_accepts_its_own_query`;
  `test_product_subjects.ServedUiContractTest.test_the_rail_carries_the_portfolio_lab_above_the_calculator`;
  `test_subject_finance_acceptance.FinanceRecordsAndGuidance.test_032__the_shelf_declares_no_tiles_and_that_is_the_recorded_design`.
- **docs_sync, two failures, both other lanes' artefacts:** `docs/BUNDLE_PRICING_HANDOFF.md` has no row
  in the `docs/HOME.md` §4 spine; and `docs/HANDOFF.md` cites two historic sub-numbered decision ids
  (the lettered pair in the B-180 series) that have no row in `docs/DECISIONS.md`. Not fixed here: one is
  another lane's new document, the other is factual-doc content this lane does not own.
- **Order-dependent:** `test_product_billing.CatalogueTest.test_four_tiers_in_order` and
  `test_credits_are_absent_rather_than_invented` fail in the full run and pass alone.
- **Concurrency incident, recorded so it is not re-debugged:** at 09:50 the working tree was written by
  another process — `src/bp/accounts.py` and `tests/test_accounts.py` were reverted to HEAD (the
  uncommitted edits lost, the 8 new tests gone, discovery fell from 3246 to 3238), while this lane's doc
  edits were swept into commit `f7eba21` (a project-management commit). The code was re-applied and
  re-verified. Only one writer may own this tree at a time.

- All subject backends pass; no missing wiring detected.
- Chat paper completion supported by tests.

## Notes
- Scaffolding files deleted: install_people_profiles.py, _people_profiles_source.py.
- Test command: `PYTHONPATH=src python -m pytest` from business_pipeline_v0.12/business_pipeline.
