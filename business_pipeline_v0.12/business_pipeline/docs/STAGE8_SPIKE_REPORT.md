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

## What Stage 8 still needs
Schedule engines (depreciation, amortization, loans, accruals), a cash flow statement computed by two routes, a reconciliation engine, a declarative layer with an interpreter, the account-mapping confirmation checkpoint in the pipeline (the manual's second mandatory checkpoint), framework-aware standards retrieval and citation, multi-period closing and the retained-earnings rollforward, a policy-change input, accountant-readable exports, and the pipeline integration with the sandbox. Output must be positioned as management accounts, not GAAP or IFRS statements and not assurance.
