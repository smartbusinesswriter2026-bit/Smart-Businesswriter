"""Cause keys, remedies and the closure rule for the repair loop (product layer).

An **error message is not a cause**.  The same wording can come from a transient
provider, from the student's own figures, or from a defect in the pipeline.  The
repair loop used to treat every message alike: replay it, close it, move on.  So
the same class of failure kept coming back, because closing an instance never
changed the thing that produced it.

This module draws the line the panel needs:

* **transient** - a provider timeout, a rate limit, an unreachable host.  Retried,
  never written to the error list, never counted as a fix.
* **input** - the student's or the generator's figures: a trial balance that does
  not balance, an instruction that is not an accounting problem.  The tile refuses
  it; it is not a pipeline defect and is not written to the error list.
* **pipeline** - a real defect.  A pipeline cause may only be called **fixed**
  when a durable artifact was written: a vocabulary rule, a normalizer/golden case,
  a refreshed case expectation, or a reviewed code change.  A replay that merely
  passes once is an *instance* close, not a cause fix.

`REMEDIES` is the small, reviewable registry the loop and the admin read.  Adding
a new failure class means adding one row here and one test in
`tests/test_causes.py`; the loop then knows whether it may close it and what the
panel should say.
"""

TRANSIENT = "transient"
INPUT = "input"
PIPELINE = "pipeline"

#: One row per cause.  `artifact` is what a *durable* fix writes; "" means the
#: cause cannot be auto-fixed and the error stays open with `remedy` named.
REMEDIES = {
    "transient.provider": {
        "scope": TRANSIENT, "remedy": "retry",
        "artifact": "", "title": "Provider timeout or unreachable host",
    },
    "input.validation": {
        "scope": INPUT, "remedy": "refuse",
        "artifact": "", "title": "Refused request (malformed field, unknown ticker)",
    },
    "input.unbalanced": {
        "scope": INPUT, "remedy": "refuse",
        "artifact": "narrative_balance",
        "title": "Trial balance whose two sides do not agree",
    },
    "input.not_accounting": {
        "scope": INPUT, "remedy": "refuse",
        "artifact": "",
        "title": "Instruction is not an accounting problem",
    },
    "input.incomplete": {
        "scope": INPUT, "remedy": "ask_for_figures",
        "artifact": "",
        "title": "Instruction omits the figures the method needs",
    },
    "input.unsupported_group": {
        "scope": INPUT, "remedy": "refuse",
        "artifact": "",
        "title": "Consolidated or group accounts are not supported",
    },
    "pipeline.parser_shape": {
        "scope": PIPELINE, "remedy": "normalizer",
        "artifact": "golden_case",
        "title": "The reader cannot parse the problem's shape",
    },
    "pipeline.vocabulary": {
        "scope": PIPELINE, "remedy": "vocabulary_rule",
        "artifact": "tier1_rule",
        "title": "An account label is outside the statement vocabulary",
    },
    "pipeline.case_expectation": {
        "scope": PIPELINE, "remedy": "refresh_case_expectation",
        "artifact": "",
        "title": "A stored tile case expects a value the engine no longer produces",
    },
    "pipeline.journal_human": {
        "scope": PIPELINE, "remedy": "human_decision",
        "artifact": "",
        "title": "Closing entries leave abnormal balances; a human must decide",
    },
    "pipeline.core_missing": {
        "scope": PIPELINE, "remedy": "wire_the_core",
        "artifact": "",
        "title": "The statements tile is not attached to the frozen core",
    },
    "pipeline.method_contract": {
        "scope": PIPELINE, "remedy": "fix_the_method",
        "artifact": "code",
        "title": "A method did not return a value its contract declares",
    },
    "pipeline.unknown": {
        "scope": PIPELINE, "remedy": "investigate",
        "artifact": "",
        "title": "Unclassified pipeline failure",
    },
}

# Ordered: the first row whose pattern appears wins.  Transient and input rows come
# first so a timeout inside a reader message is still a timeout, and an input
# refusal is never mistaken for a parser defect.
_RULES = (
    ("transient.provider", (
        "timeout", "timed out", "could not reach", "failed to fetch", "no answer within",
        "rate limit", "429", "too many requests", "connection", "provider returned http",
    )),
    ("pipeline.core_missing", ("not attached to the frozen core", "core is not attached")),
    ("input.unbalanced", ("does not balance", "do not balance", "accounts do not build")),
    ("input.not_accounting", (
        "names no transaction", "not an accounting problem",
        "does not read as an accounting problem", "declares no figure",
    )),
    ("input.incomplete", (
        "does not state:", "declares none of the figures", "does not look like",
        "declares no figure", "omits the figures",
    )),
    ("input.unsupported_group", ("consolidated", "group accounts")),
    ("input.validation", (
        "case id must be", "unknown deliverable", "unknown route", "not allowed",
        "is required", "must be one of", "unknown method", "unknown subject",
        "a request object is required", "no sourced price", "no price was stored",
        "the symbol must be",
    )),
    ("pipeline.case_expectation", (
        "status error, expected", "status needs_input, expected", "expected ok",
        "the paper does not", "the workbook does not", "does not show any of the computed values",
        "declared inputs", "break-even point",
    )),
    ("pipeline.vocabulary", ("could not find an account",)),
    ("pipeline.parser_shape", (
        "could not read this as a journal", "not in the expected format",
        "try restating as a trial balance", "appears twice", "appears more than once",
    )),
    ("pipeline.journal_human", ("journal did not build", "abnormal balances", "human decision")),
    ("pipeline.method_contract", ("the method did not return",)),
)


def classify_cause(error_text, problem_text=None):
    """Return the cause row for one error message.

    The result is a plain dict so it can travel through JSON and the admin page:

        {"cause", "scope", "remedy", "artifact", "title", "reason"}

    `artifact` is the durable change a *fix* must write; "" means the cause cannot
    be closed by the loop alone.
    """
    text = str(error_text or "").lower()
    for cause, patterns in _RULES:
        for pattern in patterns:
            if pattern in text:
                row = dict(REMEDIES[cause])
                row["cause"] = cause
                row["reason"] = pattern
                return row
    row = dict(REMEDIES["pipeline.unknown"])
    row["cause"] = "pipeline.unknown"
    row["reason"] = ""
    return row


def is_defect(error_text, problem_text=None):
    """Whether this failure belongs in the error list at all.

    Only a **pipeline** cause is a defect.  A transient provider failure and the
    student's own figures are answered to the caller and kept out of the queue, so
    the panel never fills with errors no repair can fix.
    """
    return classify_cause(error_text, problem_text)["scope"] == PIPELINE


def closure(cause):
    """How a cause may be closed: `instance`, `invalid`, `dismiss` or `keep_open`."""
    row = REMEDIES.get(cause) or REMEDIES["pipeline.unknown"]
    if row["scope"] == TRANSIENT:
        return "dismiss"
    if row["scope"] == INPUT:
        return "invalid"
    return "instance" if row["artifact"] else "keep_open"


def durable_artifacts():
    """The artifact kinds that count as a cause fix (for the ledger)."""
    return {row["artifact"] for row in REMEDIES.values() if row.get("artifact")}
