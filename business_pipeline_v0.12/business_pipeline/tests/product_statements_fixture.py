"""The frozen statements record the render lane builds against (a test helper, not a test).

The render layer needs a record that does not move underneath it: every statement, every typed
figure, the equity roll and the cash flow, produced by the same path the tile uses.  This module
builds that record deterministically from the **golden engagement** in
`tests/test_statement_plan.py` (hand-derived, already proved by the articulation identities), with
the model's extraction step stubbed by a declared journal.  No network, no key, no clock.

Why a stub rather than a live extraction: a fixture that needs a model is not a fixture.  What the
model contributes is *language structure* — which account, which amount, which date — and the golden
engagement already states exactly that.  Everything downstream (the DAG, the ledger, the closing, the
cash flow, the gate) runs for real.

Regenerate the committed fixture after an intended change to the pipeline:

    python qa/manual/make_statements_fixture.py

If you did not intend a change, the contract test fails and tells you so — do not regenerate to go
green.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.join(ROOT, "src"), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp import statement_plan as sp  # noqa: E402
from bp.product import statements  # noqa: E402
import test_statement_plan as golden  # noqa: E402
from xlsx_read import amount  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "statements-record.json")

#: Appendix keys that hold a pre-rendered *text*: they repeat the typed figures, so they cannot be
#: used to prove that a rendered figure exists.  `typed_numbers()` skips them.
TEXT_KEYS = ("statements_export", "journal_export", "equity_statement_export", "t_accounts_export")

#: The instruction the record was solved from.  It reads as a transaction narrative (so the plan
#: layer is the reader and the cash flow statement is rendered), and it names no figure: every
#: figure comes from the declared journal.
INSTRUCTION = ("The owner started the business and the transactions for the year ended "
               "31 December 2026 are listed below.")


def chart():
    """The golden engagement's chart, which is richer than `statement_plan.DEFAULT_CHART`."""
    return golden.chart()


def extract(text, period):
    """Stand in for the model's extraction: the golden engagement's declared journal."""
    declared = golden.plan()
    return {"entries": declared["entries"],
            "adjustments": declared["adjustments"],
            "policy": dict(declared["policy"]),
            "unplaceable": []}


def build(plan):
    """The real plan layer, with the golden chart attached (the extraction step does not carry it)."""
    plan = dict(plan)
    plan["chart"] = chart()
    return sp.build(plan)


def record(statements_requested=None):
    """The record, built the way `bp.server` builds it, with the model step stubbed.

    The core is reset first: another test may have imported `bp.server`, which attaches the
    guard runner and the case solver to the global core.  A fixture must not depend on which
    module another test imported, so this builder starts from a clean core every time.
    """
    statements.reset_core()
    statements.attach_core(extract=extract, build=build)
    return statements.solve(INSTRUCTION, statements=statements_requested)


def load():
    """The committed fixture, as a dict."""
    with open(FIXTURE, encoding="utf-8") as stream:
        return json.load(stream)


def typed_numbers(record):
    """Every figure the record holds as a *value*, as Decimals — never one from a text rendering.

    This is the set a renderer's cells are checked against: if a number is in the workbook and not in
    here, the renderer computed it, which it is not allowed to do.  Totals are included because the
    core stores them (`core.scalars`, `balance_sheet_groups.totals`, `cash_flow`), so a wrong total is
    a wrong core figure, not a rendering choice.
    """
    from decimal import Decimal

    found = set()

    def walk(node, key=None):
        if key in TEXT_KEYS:
            return
        if isinstance(node, dict):
            for name, child in node.items():
                walk(child, name)
        elif isinstance(node, (list, tuple)):
            for child in node:
                walk(child, key)
        elif isinstance(node, bool) or node is None:
            return
        elif isinstance(node, (int, float)):
            found.add(Decimal(str(node)))
        elif isinstance(node, str):
            value = amount(node)
            if value is not None:
                found.add(value)

    walk(record)
    return found


def write(path=None):
    """Regenerate the fixture and return the record that was written."""
    data = record()
    target = path or FIXTURE
    directory = os.path.dirname(target)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(data, stream, indent=1, ensure_ascii=False)
        stream.write("\n")
    return data
