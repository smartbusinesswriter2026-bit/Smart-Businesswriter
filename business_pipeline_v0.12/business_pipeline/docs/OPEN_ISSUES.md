# Open issues (not fixed in this session)

## Item 17 — The Business Bundle's live charge is not taken (2026-11-03)
- **The code is built and unit-tested; the live merchant account has not been used.** Every claim
  about PayPal's behaviour in the bundle path is verified against **fixtures**, not against a real
  charge. `docs/BUNDLE_PRICING_HANDOFF.md` §6 lists the seven checks that must be proved:
  one approved $99.99 charge; the Write Smarter-side record never bills; an upgrade prorates and
  the recorded tier changes; cancelling one side stops both; annual bills $959.90 once; a bundle
  holder is never blocked; the same credentials sign in on both products.
- **Three settings the owner must supply** (the code fails closed without them, naming each one):
  `BP_WRITE_SMARTER_URL` (the hosted Write Smarter service) and `BP_BUNDLE_HANDOFF_SECRET` (the
  same value on both products), plus `PAYPAL_PLAN_ID_BUNDLE_RECORD` — a **$0** PayPal plan on the
  Write Smarter side, so that even a failed switch-off could not take a second payment. The $0
  plan is the one setting this product cannot create for itself, because a $0 plan is not a plan it
  would ever sell.
- **The shared login is not built** (B-208 promises it; B-209 records it as the amendment to D1).
  It waits on the live charge, by the owner's instruction: the payment first, then the identity.
- **The lower rungs are deferred** (B-180a, B-180b): the $18.99 / $35.99 / $59.99 rungs, the
  per-tier allowances and the per-cycle credit refill. Nothing about them is estimated or shown.
- **The Write Smarter pricing page band waits on the owner's hosted URL** (§4.3 of the bundle
  handoff): advertise it as a pointer to Smart Business Writer, or leave it off.

## Item 11 — People computations defects — **SETTLED 2026-11-03**, three defects ledgered

Settled by session 10 (`qa/manual/people.md` §2.1 Q2, §5, §9). The three sub-items did not
describe three defects: **11a is not a defect at all**, and the two real ones are worse than the
ledger said.

- **11a — the `icer` key is correct; the unit is not.** `cea_impl` and its reference route build
  `icer_<slug>` from the same regex and the appendix carries `icer_intensive` intact
  (`test_E_ppl_049`). What is wrong is that `_cea_typing` declares `icer_*` as `currency`, so a cost
  **per unit of effect** prints "USD 400.00"; and `src/bp/orchestrator.py:233` takes the request's
  currency for an `@unit` output **before** it resolves the unit, so an effect of 40 prints
  "USD 40.00" and a delta "USD 20.000". Ledgered **D-PPL-01** (BLOCKER).
- **11b — a real defect, and the doc is the one that is right.** `labour_market_impl` divides
  `vacancies` by `unemployment_rate`: ten vacancies over 5% gives **200.0000**. The documented route
  cannot even be entered — `unemployed` is refused as an unknown input (`test_E_ppl_047`). The fix
  changes the input schema, the impl, the template and the checks, so it is a core change and was
  **not** made; the work order puts it behind stop-and-ask. Ledgered **D-PPL-01**.
- **11c — the serialization is half right and half missing.** `ratio` is in the currency-exempt
  tuple, so the figure prints as a bare ratio with no money prefix (`test_E_ppl_053`). But the
  **number never reaches the paper**: `labour_market_template` interpolates only the real wage and
  the wage share, so a tool called "Labour market tightness" delivers a report that never states
  tightness (`test_E_ppl_048`).
- Also found while settling the above, on shared core methods: `power_analysis.mde`/`se` are typed
  `probability` when they are outcome-scale quantities, and `return_on_investment.years` is typed
  `count` at zero decimals so a 2.5-year holding prints "2 years" (**D-PPL-02**), and two option
  names that normalise to the same slug collapse into one `icer` key (**D-PPL-03**).
- **Not fixed here**: every one of them is a change in `src/bp/methods.py` (and one ordering bug in
  `src/bp/orchestrator.py`). `qa/manual/people.md` §4 ranks them with their cost.

## Item 12 — People computations test coverage — **CLOSED as superseded 2026-11-03**

The "8 frameworks × 3 engines" module was never added and is no longer needed.
`tests/test_people_frameworks.py` loops **all eighteen** people frameworks through each drafting
variant — outline (`test_the_outline_headings_are_title_cased`), draft
(`test_the_title_carries_the_framework_prefix_and_drops_the_trailing_period`) and long
(`test_the_byline_reaches_the_title_page_and_the_length_is_reported`) — and runs a paper with an
empty block for every one. The 8 × 3 plan predates the shelf growing to 18 frameworks; writing it
now would cover 8 of 18. The missing limb was a **real `.docx`** produced through
`completion.draft_bytes` and read back out of the zip, and
`tests/test_subject_people_acceptance.py` (`test_E_ppl_075`) now does exactly that.

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
- Ledgered as D-PLAN-02 in `qa/QA_DEFECTS.md`, and pinned by
  `tests/test_worksheet_reachability.py`: the test holds the measured set, so wiring one
  of them fails until the list is updated and a *new* unserved worksheet fails at once.

## Full-suite failures (58)
- Project worksheets: `template_raci` was in both CANVAS_BLOCKS and MATRIX_META (fixed by removal from CANVAS). `template_customer_journey` was the same defect and is now fixed — it is a grid and is declared only as one (D-MKT-04, B-198). `template_servqual` is **still** declared in both; its marketing tile is hidden until its form is repaired (D-MKT-07), so the page offers five worksheets and the framework still completes through the conductor.
- Value-chain (and RFM/SERVQUAL/social-media/STP/TAM): block key naming mismatch between implementation (long names: inbound_logistics, firm_infrastructure, …) and tests (short names: inbound, infrastructure, …). Needs coordinated rename.
- Sources: Brave→Firecrawl fallback test failing (env/API key handling).
- Project-worksheet registration guards and model-prompt tests: investigate.
- Pre-existing network-dependent failures: report, do not fix silently.

## Item 16 — full-suite failures inherited by the statements-tile lane (2026-11-03) — **CLOSED 2026-11-03**
- **Closed: the whole suite is green — `Ran 3369 tests`, `OK`.** What each failure turned out to be:
  - `test_product_billing.CatalogueTest.test_four_tiers_in_order` and
    `test_credits_are_absent_rather_than_invented`: **stale assertions, not a defect.** The owner
    renamed the fourth tier to **Business Bundle** (one subscription covering both products, keeping
    the `agency` key so the PayPal plan cache and existing ledgers stay valid) and declared its
    allowance **Unlimited**. The tests now assert the stable keys and the new name, and one of them is
    stricter than before: no credits label may carry a digit, on any tier.
  - `test_subject_finance_acceptance…test_032` and both `docs_sync` checks: fixed by the other lane
    (the `B-180a`/`B-180b` decision rows and the `BUNDLE_PRICING_HANDOFF.md` spine row now exist);
    verified green from here.
  - `test_subject_accounting_acceptance…test_E_acc_002`: **mine, and deliberate.** It required
    `detail["tiles"] == []` ("the shelf declares no tiles"); the owner's instruction for the
    statements tile supersedes that design (B-205), so the expectation changed visibly and the bite it
    carried moved to `tests/test_product_statements_tile.py` (every accounting tool in exactly one
    tile, every group tiled, no other subject gaining the tile).
- Kept for the record: at 09:50 the working tree was written by another process — `src/bp/accounts.py`
  and `tests/test_accounts.py` were reverted to HEAD (edits lost) while this lane's doc edits were
  swept into commit `f7eba21`. Everything is committed now, so the same loss cannot recur; the lesson
  stands: only one writer may own this tree at a time.

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
