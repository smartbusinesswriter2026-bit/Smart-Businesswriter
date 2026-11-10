# The eval program — how the pipeline is measured

**Status:** built (computation lane). The styled report and the admin panel are the design lane's.

This is the manual for `src/bp/product/eval_runner.py`, `eval_rubric.py`,
`eval_faults.py` and `usage.py`. The spec is `plans/eval-spec.md`; this file
is the *how*, and it records what the spec got wrong.

## What the eval is for

Three questions, one manifest:

1. **Does the pipeline still compute what it says it computes?**  Direction 1
   replays every stored tile case and checks the result, the invariants, the
   paper and the workbook against what the case recorded.
2. **Does the delivered paper hold up?**  Direction 2 builds a tile's paper and
   scores the document with a code-only rubric: sections, computed values in
   the paper *and* the workbook, no template instructions, and the retrieval.
3. **Does the repair loop work, and what does it cost?**  Direction 3 reads the
   cause ledger, the experiments and the ops log: which causes closed, how
   many consecutive green replays each fix has, what it cost, and what came
   back.

## Six corrections to the spec (all measured, not argued)

| The spec says | The repo does |
|---|---|
| 246 seeded cases | **915 cases** over **246 tiles** (`qa/cases/<subject>/<tile>/case_NNN.json`) |
| ≤2 failures out of 246 | ≤2 **pipeline** failures out of 915; the budget counts `fail` only |
| a failure is a failure | the count is split by scope: `pass`, `fail`, `invalid`, `error` |
| the rubric checks the paper's citations | the tile paper renders **no reference list**, so the RAG is scored **corpus-side** and the paper check is recorded as not observable |
| Direction 2 spends model calls | the tile path is **model-free**: `generate_one` makes no provider call, so Direction 2 costs **0 tokens** and the manifest says so |
| a missing corpus is a run with no evidence | the corpus adapter **fails open**, so the eval probes the index itself: a down index is `corpus_available: false` and the RAG score is **`not_measured`**, never a green |

The baseline on the current tree: **906 pass, 9 invalid, 0 pipeline failures**.
The nine are `accounting/ratios/002–010`, whose own figures break the
accounting identity — invalid fixtures, not defects.

## The count is split by scope

| scope | meaning | counted against the budget |
|---|---|---|
| `pass` | the case replayed and every check agreed | no |
| `fail` | a **pipeline** defect: the computation, the invariants, the paper or the workbook disagreed | **yes** |
| `invalid` | the case's **own figures** are inconsistent | no |
| `error` | the case could not be replayed at all | no |
| `skipped` | (Direction 2) a tile with no declared figures to build it from | no |

`case_runner.run_cases` counts an invalid case in its own `failed` number. The
eval does not inherit that counter: it reads the runner's **verdict** per case
and places it in a scope of its own.

**A regression is a blocker.** A case that passed in the previous run and
fails now is named in `manifest["regressions"]` with `blocker: true`, whatever
the budget says. The budget is for failures that were always there.

## Running it

```python
from bp.product import eval_runner

# Direction 1: the whole case store.  Zero model calls.
manifest = eval_runner.run_direction1()

# Direction 2: one tile per subject by default; "all" for every tile.
manifest = eval_runner.run_direction2(budget="all")

# Direction 3: the repair loop's ledger, cost and durability.
manifest = eval_runner.run_direction3()
```

Each run writes `state/eval_runs/<run_id>/manifest.json` and
`state/eval_runs/<run_id>/explainer.docx` — the plain, owner-readable account
of the run (the styled report and the admin tab are the design lane's).
`BP_STATE_DIR` moves the state, so a test never writes into the real state.

## The manifest

```json
{
  "format": "bp-eval-run/1",
  "run_id": "8f5a4ad78501",
  "direction": "direction1",
  "created_at": "...", "started_at": "...", "finished_at": "...",
  "status": "running | done",
  "counts": {"pass": 0, "fail": 0, "invalid": 0, "error": 0, "total": 0},
  "cases": [{"case_id": "...", "status": "...", "scope": "...", "error": "..."}],
  "cost": {"model_calls": 0, "tokens_in": 0, "tokens_out": 0, "usd": null, "seconds": 0},
  "environment": {"build": "1.152", "corpus_available": false}
}
```

`usd` is `null` when the model is not priced. **An unknown price is an unknown
cost, never `0.00`**, which would read as "free" and be wrong. The owner
supplies the prices in `BP_MODEL_PRICES` (a JSON file of
`{"model-id": {"input": 1.0, "output": 3.0}}`, in dollars per million tokens).

## Direction 2 needs figures

`generate_one` refuses a tile with no published defaults, and **255 of the 256
tiles have none** in a bare process (the workbench configures the presets; a
CLI or a test does not). Direction 2 therefore takes its figures from the
first source that has them, and records which one it used in
`inputs_source`:

1. `declared` — what the caller declared for the run;
2. `preset` — the tile's published defaults, when the process has them;
3. `case` — the tile's first stored case, the representative figures the case
   store already holds.

A tile with none of the three is **skipped**, not failed.

## The rubric is code, not a model

`eval_rubric` reuses the product's own readers rather than re-implementing
them: the readable text of a .docx and a .xlsx (`case_runner._docx_text`,
`_xlsx_text`), whether a computed value appears in the text
(`case_runner._paper_has_value`), and what counts as a template instruction
(`paper.META`).

**The RAG score is corpus-side.** The rubric calls `paper_batch._seed_corpus`
and checks the pages the tile's own vocabulary matched: each cited page
carries the corpus's own title and database, each quote is a complete
sentence, each quote carries the tile's vocabulary, a weakly-matched page is
**background** and is never cited, and when nothing is citable the gap is
named rather than filled. The quote is a sentence from the page **by
construction** — the product's extractor returns a sentence of the page's own
text and nothing else — and that extractor is proved by a test in
`tests/test_eval_rubric.py`.

**A tile paper's length is an observation, not a defect.** A tile paper is the
computation record, and it is short by design. The rubric records the word
count and the band; it does not fail a tile paper for being short.

## The fault harness never touches the owner's cases

`eval_faults` seeds four known faults into a **copy** of the case store
(`BP_CASE_ROOT`) with the error log redirected (`BP_OPS_LOG`), and checks
that the pipeline classifies each one the way the cause rules say it must:

| fault | scope it must produce | what it proves |
|---|---|---|
| `broken_inputs` | `invalid` | the case's own figures are refused at intake and never reach the ledger as a defect |
| `tampered_expectation` | `fail` | a wrong recorded expectation is a pipeline problem |
| `missing_phrase` | `fail` | a paper that lost a required phrase is caught |
| `bad_corpus_query` | `pass` + `not_measured` | a corpus that answers nothing produces no green RAG score |

`broken_inputs` is found by the method's **own invariants**, and the
perturbation has to survive the re-recording of the expectation: a break the
re-recording repairs would replay as a pass, not as an invalid fixture.

The harness fingerprints the live error log before and after and reports
`live_log_untouched`.

## What the repair loop spent

`usage.py` reads the model's own log and sums the token counts of the calls a
repair made. `auto_resolve` copies them into the fix ladder's steps and into
the result (`usage`, `cost`), and `autoresearch` records them with the
experiment. The dollar figure needs the owner's price table.

**Durability is three consecutive green replays.** One passing replay closes
an *instance*; it does not prove the class. `eval_runner.durability` counts
the run of verified replays per pipeline cause, resets it on a failure, and
calls a cause durable only when it also has a durable artifact.

## What the eval does not do

- It does not repair anything.  It measures.
- It does not approve a gap.  A capability gap still waits for the owner in
  the Relevance panel, and the growth loop still writes PROVISIONAL scaffolds
  for a human to finish.
- It does not loosen a check to get green.  The rubric reuses the product's
  checkers; the fault harness expects the *pipeline's* own verdict.
