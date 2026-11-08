# The cause loop — what counts as a fix

The repair loop used to treat every error message alike: replay it, close it, move on.
It closed **instances**, so the same class of failure came back as a new id, and the
panel showed "94 % closed" while the causes were untouched. This manual is the contract
for the replacement.

## Three scopes

`src/bp/product/causes.py` classifies every failure before it is written:

| Scope | Meaning | Written to the error log? | Closed how |
|---|---|---|---|
| `transient` | provider timeout, rate limit, unreachable host | **no** | retried; a re-run reopens it |
| `input` | the student's or the generator's figures: unbalanced trial balance, missing figures, not an accounting problem, unsupported consolidated accounts, a malformed request | **no** | refused to the caller with the reason |
| `pipeline` | a real defect in the pipeline | **yes** | only with a durable artifact (below) |

Only a pipeline cause is a defect. A burst of 18 timeouts is one transient condition,
not 18 bugs; a trial balance that does not balance is the student's figures. Writing
either to the error list fills the panel with work no repair can do.

## A cause is fixed only with a durable artifact

`REMEDIES` names, per cause, the durable change a fix must write:

| Cause | Remedy | Artifact |
|---|---|---|
| `pipeline.vocabulary` | add a vocabulary rule typed from the label's keywords | `tier1_rule` |
| `pipeline.parser_shape` | a normalizer change, pinned as a golden case | `golden_case` |
| `pipeline.case_expectation` | refresh the stored case expectation | *(human)* |
| `pipeline.journal_human` | a human decides the abnormal balances | *(human)* |
| `pipeline.method_contract` | fix the method | `code` |
| `pipeline.core_missing` | wire the tile to the frozen core | *(human)* |
| `pipeline.unknown` | investigate | *(none)* |

A replay that passes **once** closes the instance and is recorded with
`artifact: ""`. The ledger calls that `closed_instance`, never `fixed`. This is the
line that was missing: a passing replay is proof for one problem, not for the class.

Causes with no artifact (`case_expectation`, `journal_human`, `core_missing`,
`unknown`) are marked **attended** with the remedy they need, so the loop stops
retrying them and the owner sees what kind of change would fix them.

## The recurrence ledger

`src/bp/product/cause_ledger.py` reads the append-only error log and reports, per
pipeline cause:

- `occurrences` — how many instances were logged
- `artifacts` — the durable fixes recorded
- `fixed_at` — the earliest close that carried an artifact
- `recurrences` — instances logged **after** `fixed_at`
- `status` — `fixed` (no recurrence), `recurring` (the fix did not hold),
  `unfixed` (open, no durable fix), `closed_instance` (all closed, no artifact)

`fixed_pct = fixed / causes` is the only percentage that says the pipeline learned
something. It drops when a class comes back. The admin Autoresearch panel shows the
table and `/api/ops/causes` serves it.

## Recording a cause fix

A fix lives in the repository (a paper heading, a refreshed case expectation, a
vocabulary rule, a reviewed code change). Record it once, with the artifact named:

```python
ops_log.log_cause_fix("pipeline.case_expectation", "case_expectation",
                      "the paper carries 'What you declared'; the checker maps the old "
                      "phrase and never demands a reference list")
```

The ledger dates the class from that record. Every occurrence **before** it is
history; every occurrence **after** it is a recurrence. This is how a class leaves
`closed_instance` and becomes `fixed` without pretending an instance close was a fix.

Worked example (2026-11-08): 61 stored cases were replayed; 52 passed, 9 referenced a
case that no longer exists (closed as invalid), 0 failed. The paper's headings and the
checker's phrase map were already in the code, so the fix was recorded and the class
moved from `closed_instance` (76 occurrences) to `fixed` with 0 recurrences.

## Intake guards: stop the class before it is solved

A durable fix is usually a gate, not a better repair:

- **Narrative trial balance** (`problem_norm.narrative_balance`): reads
  `Account $amount` pairs, types each by its normal side (`normal_side`), and returns
  debits − credits. It is conservative: it applies only when the problem asks for a
  trial balance, carries no adjusting entry, has at least four recognised accounts,
  and every amount-bearing label is recognised. `trial_balance_imbalance` falls back
  to it when the tabular reader sees no journal — the case that walked past the old
  guard and failed in the journal builder.
- **Request validation** and **transient provider** failures are answered to the
  caller and never written as errors.
- `ops_log.log_error(..., force=True)` records a legacy input error anyway; only a
  test of the fixer's handling of an existing record needs it.

## Adding a cause

1. Add one row to `REMEDIES` in `src/bp/product/causes.py` with its scope, remedy,
   artifact and title.
2. Add the message pattern to `_RULES`, ordered before any broader pattern it would
   otherwise match.
3. Add the classification and closure assertions to `tests/test_causes.py`.
4. If the remedy is an intake guard, wire it where the problem enters (the tile route
   and `chat_heal`), not only in the fixer.
5. If the remedy is a code change, the loop may **propose** it (`/api/ops/findings/*/propose-code`)
   but never applies it: approval is a human action, and the change ships with a test.

## What this does not do

The loop does not edit code. `autoresearch` replays, writes vocabulary rules and
golden cases, and records what it could not fix; it never commits a patch. A cause
that needs a code change stays `unfixed` until someone writes it. The panel says so
instead of counting a dismissal as a win.
