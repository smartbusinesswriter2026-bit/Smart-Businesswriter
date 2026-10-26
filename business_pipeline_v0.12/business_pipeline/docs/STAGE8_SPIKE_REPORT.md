# Stage 8 ledger-engine spike (manual 9.2, decision D-007, open decision B-032)
**Status: PARTIAL. Only the custom-kernel arm was run. The Beancount arm was NOT run** (Beancount is not installed and this environment has no network). The comparison the manual requires is therefore incomplete, and the engine decision stays OPEN.

## What was built
- `src/bp/ledger.py`: a minimal double-entry kernel (167 non-blank lines): typed accounts with normal sides and contra accounts; entries that cannot be constructed unbalanced; Decimal-only amounts with no silent rounding; an append-only journal with a hash chain; trial balance; income statement and balance sheet as derived views; six invariants recomputed from the journal lines by a different route; judgment flags; a plain-text export; a required reporting framework with no default (D-010). **It is not wired into the pipeline.**
- `spike/trap_cases.py`: 12 neutral trap cases as plain data, so any arm can run them. `spike/run_custom_arm.py` runs the custom arm.

## Results, custom arm (12 cases)
| How the problem was handled | Cases |
|---|---|
| Rejected when the entry is built | unbalanced entry, binary-float amount, silent rounding (three decimals), unknown account, date outside the period |
| Caught by an invariant | opening balances differ from prior closing; journal edited after posting |
| Flagged for a human (balanced, so no invariant can see it) | flipped sign on an expense; contra account set up as an ordinary asset; recurring expense missing in the last month |
| Not detectable from the data | undisclosed mid-year depreciation policy change (needs a declared policy-change input; no arm can infer it) |
| Nothing reported, correctly | the clean baseline |
Tests: `tests/test_ledger.py`, 22 tests including 300 seeded random journals that must always satisfy the invariants.

## Defects found while building (both fixed)
1. A retained-earnings rollforward "invariant" I first wrote could not fail (it compared a quantity with itself). I removed it. **This deviates from manual 9.3**, which lists it; it only becomes meaningful with multi-period closing entries (B-034).
2. My first net-income cross-check assumed all non-earnings equity movement was capital or dividends. The random-journal test showed it fails when something posts directly to retained earnings. The second route now subtracts every equity movement, so it no longer depends on account roles. Separately, a dividends account was wrongly flagged as an abnormal balance; accounts with the dividends role are now treated as debit-normal contra equity.

## The Beancount arm: not run, how to run it
Protocol: install Beancount 3 in a normal environment; feed each case in `spike/trap_cases.py` through its data structures (not generated text, per manual 9.2); record for each case whether it is rejected, flagged by a plugin, caught by a check, or missed; count the glue code needed; export the same journal and judge readability with an accountant. The manual's claims about Beancount (Decimal amounts, no native schedules, sign convention, licence) remain **[UNVERIFIED]**, and the GPLv2 licensing question needs legal review before any distribution.

## Provisional recommendation (not a decision)
Use the custom kernel as the ledger of record for the first release of management accounts: it is small, it enforces the manual's central rule by construction, and it has no copyleft question. The cost is building schedules, reconciliation, cash flow and multi-period closing ourselves, and I have not evaluated what Beancount's ecosystem would save. Record the decision only after the Beancount arm has been run.

## Increment: schedule engines (2026-10-21)
**Built on the custom kernel (B-044).** `src/bp/schedules.py` generates balanced journal lines from declarative specs:
- **Straight-line depreciation**: one Dr expense / Cr accumulated-depreciation entry per period; the final period absorbs the rounding remainder so the schedule sums exactly to cost minus residual.
- **Loan amortization**: Dr interest / Dr loan / Cr cash per period. Interest rounds half-even to the currency places; a payment never exceeds the balance due, so the final payment absorbs the remainder and a large fixed payment repays early; without a payment the level annuity is rounded up so the loan pays off within the term.
- **Straight accruals**: a constant Dr expense / Cr accrued-liability entry per period.

Amounts with more than the currency places are rejected, never silently rounded. Tests (`tests/test_schedules.py`, 13): hand-checked schedules (including the 0.33/0.33/0.34 depreciation remainder and the 10.00/78.85/88.85 first loan payment), exact balance-walk reconstruction of every interest amount, validation traps (binary floats, negative costs, too-small payments, over-places amounts), and end-to-end posting of every schedule into the ledger kernel where all six invariants pass and statement totals are hand-checked.

## Increment: cash flow statement by two routes (2026-10-21)
`ledger.cash_flow(j, st)` (B-045). The **direct route** classifies each non-opening entry's cash delta by its non-cash counterpart activity — an explicit per-account `activity` tag (new Account field) wins, otherwise declared type defaults (income/expense operating, asset investing, liability/equity financing); entries with mixed counterparts are classified operating-first and flagged, cash-to-cash transfers are flagged. The **indirect route** derives the same total from net income + non-earnings equity movements + liability changes − change in non-cash assets. The two totals must agree; a `cash_flow_agrees_across_routes` check reports the comparison, and 300 seeded random journals always satisfy it. Cash accounts are identified by a new `role "cash"`. Hand-checked: operating 1500 / investing −500 / financing 700 / net 1700, with the indirect route recomputed independently. Non-cash entries (credit sales, depreciation, accruals) leave both routes unchanged; collecting a tagged receivable and settling a tagged accrual classify as operating.

## Increment: multi-period closing and the retained-earnings rollforward (2026-10-21)
`ledger.closing_entries(j)` (B-046) generates the period-end entries (dated `j.end`, marked `closing` inside the hash chain): income balances close to retained earnings, expense balances close against it, and declared dividends close against it. Abnormal balances among the closed accounts block with a request for a human decision. `retained_earnings_rollforward(j, pre)` implements the manual 9.3 invariant that was deliberately deferred in the spike (B-034, now resolved): closing retained earnings must equal opening retained earnings + pre-closing net income − declared dividends + direct non-closing postings, and it also checks that closing zeroed the income, expense and dividend accounts. `closing_balances(j)` and `opening_lines(j)` chain periods: the next period's opening entry carries every closing balance on its natural side (abnormal balances on the opposite side with a positive amount), and the existing `opening_balances_equal_prior_closing` invariant verifies the hand-off. Tampered closing lines, a corrupted pre-closing net income, and a mismatched next-period opening are all detected. `statements` now omits zero-net accounts, so closed accounts and fully repaid loans disappear from the statements.

## What Stage 8 still needs
The declarative layer with an interpreter and the pipeline wiring for the schedule engines, the cash flow statement and closing (built above but not yet in the pipeline), a reconciliation engine, the account-mapping confirmation checkpoint in the pipeline (the manual's second mandatory checkpoint), framework-aware standards retrieval and citation, a policy-change input, accountant-readable exports, and the pipeline integration with the sandbox. Output must be positioned as management accounts, not GAAP or IFRS statements and not assurance.
