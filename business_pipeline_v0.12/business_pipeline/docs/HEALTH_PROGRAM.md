# The health program — what is wrong with the pipeline, named

**Status:** built. The checks are the computation lane's; the panel and the
route are the design lane's.

`/api/health` reports the **server**: the build, the case store, the request
log. That is not the **pipeline**. A pipeline can be perfectly up while its
corpus is down, its cases are failing, its repair loop is idle, and its own
test suite is red. This program reads the signals that already exist and says
which of them are wrong.

## The shape: a list, not a score

Each check returns its own verdict, and the **overall bit** is the conjunction
of the rows that are required. A percentage of checks that pass is a metric
that invites turning off the checks you cannot pass; a list is read.

```json
{
  "format": "bp-pipeline-health/1",
  "overall": false,
  "checked_at": "2026-11-10T05:12:44+00:00",
  "build": "1.154",
  "checks": [
    {"name": "corpus", "ok": false, "severity": "required",
     "reason": "the corpus index is not reachable, so retrieval is not measured",
     "checked_at": "2026-11-10T05:12:44+00:00"}
  ],
  "failing": ["corpus"],
  "advisory": []
}
```

**Two kinds of "not ok" are kept apart.** A `severity` of `required` means
the signal is missing or wrong and the overall bit is affected. A `severity` of
`advisory` means the signal is informational: the model is off, the relevance
sweep has never run, the suites have never been run here. The pipeline is not
degraded by a measurement nobody took — but it says so plainly.

**A missing signal is never a green.** A check that cannot be run returns
`ok: false` with a reason.

## The twelve checks

| Check | It is ok when |
|---|---|
| `server` | it answered (always true; it is reported) |
| `case_store` | the store returns a count, not `null` |
| `case_pass_rate` | open **pipeline** failures are within the budget (≤2); invalid fixtures are counted separately and never against the budget |
| `regressions` | no case that passed before fails now |
| `corpus` | the index answers `/health` — a down index is a hard gate, because the retrieval is then *not measured*, not empty |
| `repair_loop` | nothing waits for it, or it is running, or it is **switched off** (a reason, not a failure) |
| `causes` | no cause is `recurring` |
| `eval_baseline` | the last Direction 1 run is within the budget, has no regression, and is not older than the build |
| `test_suite` | the last run of each suite is green and not older than the build; never run is advisory |
| `relevance` | the last sweep's controls held; never run is advisory |
| `model_assistance` | reported, never a failure |
| `switches` | reported, never a failure |

## Freshness is per signal

Every signal carries `signal_checked_at` and an `age` in words ("2 hour(s)
ago"), and the panel shows it. There is no global window, because a rule that
fits the corpus is wrong for the test suite.

**A measurement taken before the code changed says nothing about the code
that is there now.** The eval baseline and the test suite are therefore stale
when they are older than the tree's newest build, and a stale signal is
`required`, not `advisory`: the pipeline's correctness is unmeasured for this
build.

## A finding is logged once

A failing check is written into the ops log under its own lane,
`pipeline-health`, with the check's name as the label. **A check that fails
twice in a row is one issue, not two** — the second failure carries no new
information, and a second id would give the repair loop something to re-fix.
A check that recovers is marked resolved with a note, so the history keeps
both the failure and the recovery; the log is never rewritten.

The findings are **attended**, not open. A health finding is a fact for the
owner ("the corpus index is not reachable"), not something the auto-fixer can
repair by replaying a case. Attending it stops the repair loop from spending
model calls on it, and the cause ledger from counting it as a defect.

## Nothing here acts

The health check reads. It never starts a loop, never repairs anything, never
applies a gap, and never writes outside `state/health/`. The switches on the
Loops tab decide what runs; the panel's button (design lane) is an explicit
action, never an automatic one.

## Where the code is

- `src/bp/product/health.py` — the checks, `health()`, `log_issues()`,
  `health_record()`, `history()`. The computation lane.
- `src/bp/server.py` — `GET /api/ops/health` (additive). The design lane.
- `web/admin-sbw.html` — the panel: one row per check, its verdict, its reason
  and the age of the signal behind it. The design lane.
- `state/health/health.jsonl` — the record of every check, so a run can be
  compared with the previous one without re-running anything.

## Calling it

```python
from bp.product import health

report = health.health()          # read the real signals
health.health_record(report)      # write one record
health.log_issues(report)         # log the failing checks, once each
history = health.history()        # the stored reports, newest first
```

Every check takes its signal as an argument, so a test calls it with a
prepared signal and never needs a server, a model, or a network beyond the
corpus probe.
