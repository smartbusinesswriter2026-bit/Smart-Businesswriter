# The statements tile (accounting, tile 1) — approved build instruction

**Status: APPROVED for build (owner, 2026-11-03).** This is the instruction the increment is built
against, rewritten after checking the first draft against the code. Every rule below is grounded in
a source file or a probe that was actually run; the probed facts are in §2 so they never have to be
derived again, and the traps in §16 are the failure modes that were found by running the core.

Read with: [`HANDOFF.md`](HANDOFF.md) (commands, non-negotiables, B-197 standing unfreeze),
[`BACKEND_CONTRACT.md`](BACKEND_CONTRACT.md) §1-§4 (what is frozen, the product lane),
[`CONTRIBUTORS.md`](CONTRIBUTORS.md) §1A/§1B (lane split), [`CONDUCTOR_MANUAL.md`](CONDUCTOR_MANUAL.md)
§4, §7, §7.6 (non-negotiables, capabilities, the verifier and the frozen plan).

## 0. What is being built

One standalone accounting tile — the first on the Accounting shelf. One instruction box, one
optional CSV/XLSX (PDF/scan/OCR/SPSS stay refused by the existing ingester). No field-filling, no
balance-it-yourself, and **no blocking question before the answer exists**.

It identifies the problem type, extracts every figure with its provenance, compiles a verified
reading into the engagement spec the core accepts, calls the core, presents the statements with the
full working behind a toggle, diagnoses an imbalance instead of plugging it, computes ratios only
when asked, and freezes the result into a replayable record.

Standalone-first: the record's shape is exposed so paper-bound capabilities can consume it later.
Nothing consumes it in this increment.

## 1. The deliverable is type-dependent (corrected)

A single trial balance cannot produce a cash-flow statement: a cash flow needs a period's flows or a
prior balance sheet. Presenting one from a TB produces a figure that is internally consistent and
substantively false (§16 T2). So:

| Problem type | IS | SOCE | BS | Cash flow | Note |
|---|---|---|---|---|---|
| `trial_balance` | yes | yes | yes | **withheld, named** | unless the instruction also declares flows or a prior TB |
| `transactions` | yes | yes | yes | yes | opening balances + flows are declared, so both routes agree |
| `adjustments` | yes | yes | yes | conditional | only when the base type supplies flows |
| `incomplete_records` | yes | yes | yes | **withheld, named** | plus the statement of affairs and the derivation |

The withheld item is named in the output and in the record — *"a cash flow statement needs the
period's flows or a prior balance sheet; the instruction supplies one trial balance"* — never
silently omitted and never faked.

## 2. Probed facts (do not re-derive)

| Fact | How it was established |
|---|---|
| `accounts.build(spec)` returns scalars plus `_appendix` with `statements`, `trial_balance`, `cash_flow`, `checks`, `flags`, `journal`, `journal_export`, `t_accounts_export`, `equity_statement_export`, `statements_export`, `closing_balances` | probe on `EXAMPLE_SPEC` |
| `EXAMPLE_SPEC` builds 11/11 checks | probe |
| A TB posted as **opening** entries gives **7/11** with two real failures (`net_income_agrees_across_routes`, `cash_flow_agrees_across_routes`) | probe (§16 T1) |
| A TB posted as **one period entry** gives **9/11 with `checks_na = 2`** — every applicable check passes | probe |
| TB + straight-line depreciation schedule gives 9/11, na 2, and SOCE `total_closing` equals balance-sheet equity | probe |
| `framework` in `IFRS`/`US_GAAP`/`local` is **required**, no default | probe: "reporting framework is a required input and has no default" |
| An unbalanced opening is refused at validate time with the debit/credit totals | probe |
| `methods.LIBRARY["management_accounts"]` takes `{"spec": ...}` and `methods.validate_inputs` accepts it | probe |
| `check.compare(None, tb, places)` returns the imbalance in `amounts.submitted_balance_difference` with the /9 transposition hint, a verdict and `cannot_prove` | probe |
| `methods._RATIOS` is 15 ratios in 4 groups; `dupont_analysis` already does 3-step and 5-step | read |
| `test_frozen_contract` pins presets exactly and requires the 12 frozen routes to be present | read |
| `test_product_boundary` forbids the product package importing any `bp.*` module | read |
| `accounts._s()` stringifies Decimals, so the appendix is JSON-safe and hashable | read |
| `schedules.amortization` is **loan** amortisation, not intangibles | read |
| `schedules.depreciation.life` counts **monthly periods**; keys are `dep_account` / `accum_account` | read + probe |

## 3. The reading an advocate proposes

```json
{
  "problem_type": "trial_balance | transactions | adjustments | incomplete_records",
  "why": "one sentence: the cue that decided the type",
  "currency": "USD",
  "framework": "US_GAAP | IFRS | local",
  "places": 2,
  "period": {"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"} | null,
  "period_source": "declared | derived | assumed",
  "chart": [{"code": "1000", "name": "Cash",
             "type": "asset | liability | equity | income | expense | oci",
             "line": "Cash", "section": "current | non_current | null",
             "role": "cash | capital | retained_earnings | dividends | oci_reserve | null",
             "activity": "operating | investing | financing | null", "contra": false,
             "quote": "the text that names this account"}],
  "opening":    [{"account": "1000", "debit": "5000", "quote": "..."}],
  "journal":    [{"date": "YYYY-MM-DD", "description": "...",
                  "lines": [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}],
                  "quote": "..."}],
  "schedules":  [{"kind": "depreciation | amortization | accrual | prepayment | deferred_income | bad_debt | revaluation | disposal",
                  "the core's own field names for that kind": "...", "quote": "..."}],
  "figures":    [{"written": "...", "value": "...", "kind": "amount | rate | count", "quote": "exact text"}],
  "derivations":[{"figure": "capital", "identity": "capital = assets - liabilities", "working": "...", "derived": true}],
  "ratio_map":  {"inventory": "1200", "receivables": "1100", "payables": "2100", "cost_of_sales": "5000"},
  "diagnosis":  {"difference": "...", "cause": "...", "confidence": "likely | possible | no-conclusion"} | null,
  "missing":    [{"what": "...", "why": "..."}],
  "assumptions":[{"text": "...", "basis": "..."}]
}
```

Advocate rules, verbatim into the prompt:

1. Choose exactly one `problem_type`.
2. Every figure, account, entry and schedule carries the exact text it came from.
3. Never invent a figure, an account, a date or a source.
4. Say what is missing; an empty `missing` is a claim that the statements can be completed, and it is tested.
5. A derived figure names its identity and is marked `derived`.
6. A **schedule** states the core's schedule parameters, never a journal the model computed. `life` is monthly periods: "five years" is `60`, and the conversion appears in `derivations`.
7. `type`, `section` and `role` are classifications you must state. `type` is `income` (not `revenue`); `section` decides the balance sheet **and** the cash-flow classification.
8. No claim beyond arithmetic: no forecast, no recommendation, no "will", "proves", "causes".

## 4. The verifier (code, not opinion)

`statements_verify.verify_reading(reading, instruction, currency)` returns `[{check, detail}]`;
empty means approved. Six checks, each tested:

1. **Provenance** — every quote is an exact substring of the instruction (the same rule
   `verify.verify_reading` uses; no whitespace normalisation is added, or the two verifiers disagree).
2. **Normalisation** — every figure passes `verify.normalise_number(written, kind, currency)`; its
   refusal text becomes the finding.
3. **Chart completeness** — valid types, a `line` on every account, no duplicate code or name,
   exactly one `retained_earnings` role, and `section` present on every asset and liability.
4. **Balance** — the journal and the opening trial balance balance, or a `diagnosis`/`derivation`
   explains the difference.
5. **Articulation** — every applicable core check passes (`checks_na` is not a failure), SOCE
   `total_closing` equals balance-sheet equity, and the presented statements carry no cash-flow
   section when the type cannot support one.
6. **Completeness** — compile and build; if the core refuses, `missing` is non-empty **and** quotes
   the refusal. An invented figure (no quote, no derivation, no declared input) is a refusal.

The verifier is the veto. Nothing reaches the record unless it passes.

## 5. The council — aimed at the contested items

- **Primary reading**: one model (default `kimi-k3`, `BP_PROSE_MODEL`).
- **Dissent seat**: a second model (`BP_COUNCIL_MODEL`, default `deepseek-v4-pro`) argues the
  *opposite placement* of each **contested item only** — not the whole reading.
- A **contested item** is one whose label matches two vocabulary rules, matches none, or whose
  placement would change a statement line, section, role or ratio input.
- **Adjudication is deterministic and ranked**: a declared vocabulary rule beats a model opinion
  unless the model supplies a quote that overrides it; the literal standard rule beats the marker
  convention, which beats the dissent; the dissent wins only if the literal reading fails the
  verifier. If two readings both pass and differ, the literal rule is used and the alternative is
  printed with its figures already computed.
- The **examiner** is called only to break a tie between two passing readings.
- **Same-model disclosure**: if both seats resolve to the same model id, the record says so — a
  second opinion from one model is not one.
- **Gate**: on whenever a model gateway is configured (`prose.available()`, resolved by
  `product/providers.py`). No separate flag. `BP_OPENGO_API_KEY` is one way; any provider below works.
- Provider failure falls back to the deterministic parser and records why; the instruction is never
  lost. Cost note in the module docstring: one advocate call per contested item plus an examiner
  only on a tie, `max_tokens` 8,000 (the paper council's 2,000 truncates a statement reading — T12).

## 6. Routing and the compile strategy

| Type | `opening` | `entries` | `prior_closing` |
|---|---|---|---|
| `trial_balance` | `[]` | **one** entry dated `period.end` carrying the whole TB | `{}` |
| `transactions` | the "started with" balances, `opening: true` | one entry per transaction | the opening accounts' natural balances |
| `adjustments` | as the base type | TB entry + transaction entries | as the base type |
| `incomplete_records` | `[]` | the TB entry **including** the derived figure | `{}` |

- `framework`: **`US_GAAP`** by default; `IFRS` or `local` when the instruction says so. Never asked.
  Disclosed in one line, agreeing with the core's own note (management accounts, not audited).
- `places` = the largest number of decimals among the declared amounts, clamped 0-6.
- A negative declared balance moves to the other side (a side assignment, recorded), never passed as
  a negative amount.
- Amounts are strings; binary floats are refused by the core.
- No period declared: derive it from any stated date, else adopt a declared sentinel year, set
  `period_source: "assumed"` and disclose it.
- An unmatched label is carried as `unclassified` and reported; it is never guessed into "other".

**Imbalance diagnosis** always goes through `check.compare` (method `trial_balance_check`) and
surfaces `findings[0].detail` plus `cannot_prove` — not `verdict`, which branches on `has_journal`.

## 7. Statement assembly

1. Compile the verified reading, call the **injected** solver (§11), read the core's own output.
2. Present `statements_export["income_statement"]`, `["balance_sheet"]`, `["trial_balance"]`,
   `equity_statement_export`, `journal_export`, `t_accounts_export`.
3. Present `statements_export["cash_flow"]` only when §1 says the type supports it.
4. Never plug a difference. Determinable cause: state the cause and the correcting entry and re-run.
   Not determinable: name the difference and what is needed. `incomplete_records`: derive, label
   `derived`, show the identity.
5. Every refusal is a sentence a first-year student can act on: what is out, by how much, and the
   likely cause.

## 8. Working and the toggle

Statements plus the full working by default (journal, T-accounts, trial balance, adjustments,
derivations, the type-and-why line, the assumptions). A statements-only toggle for submission.
Both views render from the same frozen record; the toggle is presentation only, with no server-side
parameter, so no number can change (test: same `plan_hash`, same digits).

## 9. Ratios — on request only, fed by the core

1. Cue detection like `capabilities.resolve` ("ratio", "current ratio", "analyse liquidity",
   "DuPont", "profitability", "gearing"). No cue: no ratio section.
2. The product passes **account codes and names**; the core supplies the figures. Since B-203,
   `accounts.build` publishes `balance_sheet_groups`, `ratio_figures` and `ratio_gaps`.
3. Catalogue for v1: the core's 15 ratios plus DuPont 3-step and 5-step. Everything else is named
   from `RATIO_GAPS` with the input it needs.
4. A ratio the declared figures cannot support is named from the core's own `not_computed` reason.
5. **No preset is added** (`test_frozen_contract` pins presets exactly — T15).

## 10. Routes, storage, record shape

```
POST /api/cases/statements                 {instruction, file?, currency?, period?, ratios?}
GET  /api/cases/statements/{id}
POST /api/cases/statements/{id}/export      {format: "docx" | "text" | "statements_only"}
```

Handled as new segments in `product/api.py::handle` (`STATEMENTS_ROUTE`) — no new route in
`server.py`, so the frozen 12 are untouched.

One JSON document per record under the case store (`cases.cases_dir() / "statements"`), atomic write,
12-hex ids, the same rules as `cases.py`.

```json
{ "format": "bp-statements/1", "id": "...", "created_at": "...",
  "instruction": "...", "instruction_hash": "sha256:...",
  "problem_type": "...", "why": "...", "reading": {...},
  "reading_source": "parser | council(primary) | council(primary+dissent)",
  "same_model_disclosure": true,
  "rejected": [...], "spec": {...},
  "core": {"scalars": "...", "appendix": "..."},
  "statements": {"income_statement": "...", "balance_sheet": "...", "equity": "...",
                 "cash_flow": null, "cash_flow_withheld_because": "..."},
  "working": {"journal": "...", "t_accounts": {}, "trial_balance": "...",
              "derivations": [], "assumptions": []},
  "diagnosis": null,
  "ratios": {"requested": true, "computed": [], "named_unsupported": []},
  "checks": [], "plan_hash": "sha256:<16>" }
```

`plan_hash` is `verify.freeze(record)` reused. The hash excludes `id`, `created_at` and `plan_hash`,
or replay can never match (T18).

## 11. Architecture

The product layer never imports the core (T-boundary; `test_product_boundary.py`). The solver is
injected from `server.py`, exactly as `attach_compute` already is:

```python
product_statements.attach_core(
    solve          = lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
    diagnose       = lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
                         {"journal": None, "trial_balance": rows, "places": places}),
    ratio_analysis = lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
    dupont         = lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
)
```

`statements.py` raises a clear error if the solver is not attached (fail closed), and a boundary test
asserts it imports nothing from `bp`.

| File | Lane | Purpose |
|---|---|---|
| `src/bp/accounts.py` | computation | `balance_sheet_groups`, `ratio_figures`, `RATIO_GAPS` (B-203, shipped) |
| `src/bp/product/statements.py` | product | types, extraction, compile, assemble, working, freeze, replay check |
| `src/bp/product/statements_verify.py` | product | §4 |
| `src/bp/product/statements_council.py` | product | §5 |
| `src/bp/product/api.py` | product | `STATEMENTS_ROUTE` and dispatch |
| `src/bp/product/subjects.py` | product | `ACCOUNTING_TILES` plus the statements tile kind |
| `web/index.html` | design | tile, working toggle, diagnosis card, ratio-on-request |
| `tests/test_product_statements*.py` | product | §12 |

## 12. Tests

`tests/test_product_statements.py`: each of the four types solves end to end; the TB path presents
no cash-flow section and says why; an out-by-X TB is diagnosed and never plugged; the transaction
path articulates on every applicable check (`checks_na` read as not-applicable, never as failure);
the schedules are applied by the core and a wrong `life` is refused with the quote;
`incomplete_records` derives the figure from the core's own difference, labels it `derived`, and a
wrong figure is caught by the rebuild; no cue means no ratio section; a cue means the pack; an
unsupported ratio is named; the toggle changes no digit; replay re-derives a byte-identical
appendix; a trap test that field-filling and plugging cannot reappear; a Philippine currency or
place is refused or normalised with a reason and no such string reaches the output.

`tests/test_product_statements_council.py`: an approved reading is accepted; an untraceable figure, a
non-balancing journal and a mis-articulating statement are each rejected; the examiner clamps to the
approved set; provider failure falls back to the parser and records why; a truncated answer is a
rejection, not a partial reading; a fenced answer with trailing prose parses; same-model disclosure;
one dissent call per contested item, not per reading.

`tests/test_product_statements_api.py`: POST 201 + record, GET round-trip, export bytes, export
refused when the statement set is withheld, unknown id 404, corrupt record refused, the route family
served through `product_api.handle`, and `statements*.py` imports no `bp.*` module.

## 13. Docs per commit

CHANGELOG entry, WORKLOG entry tagged by lane, a B-row per behaviour decision (B-203 onwards),
KNOWN_LIMITATIONS and PRODUCT_GAP_MAP where the surface changed, a BACKEND_CONTRACT §6 row for the
route family, HOME only if the tile is marketed there.

## 14. Acceptance

1. One box, no field-filling, no balance-it-yourself, no blocking question.
2. Four problem types solve end to end from pasted text; CSV/XLSX for datasets.
3. The statement set of §1, from the core, articulating, with the withheld cash flow named.
4. Imbalance diagnosed with the core's finding, never plugged.
5. Working by default, a clean toggle that changes no digit.
6. Ratios only on request; unsupported ratios named with the input they need.
7. A frozen, replayable record with `plan_hash`.
8. `python -m unittest discover -s tests` reports OK; `scripts/econ_shelf.py --check` reports
   "frozen fixture: in sync"; `test_frozen_contract` green; no preset added.
9. No Philippine/PSE string in any new output, test or fixture.

## 15. Out of scope

Consolidated statements (B-032 stays open and untouched); leases, deferred tax, liquidation,
amalgamation, advanced instruments; manufacturing/COGS, budgeting, standard costing, process/ABC;
intangible amortisation (`schedules.amortization` is a loan — T10); suspense and error correction
(phase 2, needs a new core module first); wiring the record into paper-bound capabilities beyond
exposing its shape.

## 16. Traps found by probing the core (each one costs an afternoon)

| # | Trap | Correct behaviour |
|---|---|---|
| T1 | A TB posted as `opening` gives 7/11 with two real failures | post a TB as one period entry at `period.end` |
| T2 | A TB-derived cash-flow statement passes the checks and is false | withhold it and name why |
| T3 | `type` is `income`, not `revenue` | use `income` |
| T4 | `role` without `capital`/`dividends` makes every SOCE movement "other" | fill the roles |
| T5 | `section` omitted puts receivables movements in **investing** | declare `current`/`non_current` |
| T6 | `framework` has no default | infer, else `US_GAAP`, disclosed |
| T7 | `places` below the declared decimals makes the ledger refuse | `places` = max declared decimals |
| T8 | a negative amount is refused | move it to the other side and record it |
| T9 | `life` counts months; keys are `dep_account`/`accum_account` | 5 years is `life: 60`; show the conversion |
| T10 | `schedules.amortization` is a loan | intangible amortisation is a named gap |
| T11 | `check.recount` returns a different metric from `compare` | the second route for a derived figure is the rebuild's balance invariant |
| T12 | the paper council caps `max_tokens` at 2,000 | the statements council passes 8,000 |
| T13 | `_json_block`'s fence regex is non-greedy and fails on nested objects | require exactly one object; test the fenced case |
| T14 | **9/11 is a pass**: `checks_na = 2` are the reconciliation checks | read `checks_na`, never call 9/11 two failures |
| T15 | a new preset breaks `test_frozen_contract` | reuse `management_accounts`; add no preset |
| T16 | adding `ACCOUNTING_TILES` flips the page into tile mode and unmapped tools vanish | map every accounting tool into a tile; guard test |
| T17 | `subjects.py` is generated data guarded against ids disappearing | additions are fine |
| T18 | `_s()` stringifies Decimals, but `created_at`/`id` change per run | exclude them from the hash |

## 17. Model seats (owner decision)

| Variable | Value | Seat |
|---|---|---|
| `BP_OPENGO_API_KEY` | OpenCode Go key | the credential; `prose.available()` (one provider among several) |
| `BP_PROSE_MODEL` | `kimi-k3` | primary reading (no training, zero retention) |
| `BP_COUNCIL_MODEL` | `deepseek-v4-pro` | dissent seat |

The lane is provider-agnostic: `BP_LLM_PROVIDER` / `BP_LLM_MODEL` / `BP_LLM_KEY` /
`BP_LLM_BASE_URL` select OpenAI, DeepSeek, Anthropic, Ollama or any OpenAI-compatible gateway;
the OpenCode Go names above remain the default this plan was measured on.

Endpoint: `https://opencode.ai/inference/go/openai/v1/chat/completions` — Go's OpenAI-compatible path;
no OpenAI key is read anywhere in this pipeline. Confirm the ids with
`GET https://opencode.ai/inference/go/v1/models`. Operational note: DeepSeek requires the workspace
region to include Global, and its ZDR agreement is renewed monthly (current term to 2026-11-30).

## 18. Commit sequence

1. **`[computation]`** — `balance_sheet_groups`, `ratio_figures`, `RATIO_GAPS`; trap tests; B-203; CHANGELOG; WORKLOG. *(shipped)*
2. **`[product]`** — `statements.py`, `statements_verify.py`, `statements_council.py`, the route, the `attach_core` line, the three test files; its own B-rows (the next free numbers at the time); docs.
3. **`[design]`** — `ACCOUNTING_TILES`, the tile UI, the toggle, the diagnosis card, the guard test; full suite and `econ_shelf --check`.

