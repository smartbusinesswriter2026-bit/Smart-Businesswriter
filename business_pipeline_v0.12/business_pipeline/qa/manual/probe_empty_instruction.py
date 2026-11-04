"""Does the tile ever answer an instruction that declares nothing?

`tests/test_product_statements_api.py` (`RouteTest.test_an_instruction_the_tile_cannot_read_is_a_named_refusal`
and the three subtests of `test_no_input_shape_produces_a_server_error`) say it must not: an instruction the
tile cannot read is a 4xx with a reason, never a record.  In the full suite those four tests went red — and
they are right.  Wired the way the workbench wires it (`bp.server` attaches the plan layer), the tile used
to build a plan with no entries, post it to the ledger, and return a full set of statements whose every
figure was zero, marked `solved`.  Three shapes were enough to show it:

    "hello there"                                   no account and no figure
    "Trial balance at 31 December 2026.\\nCash\\n"    the header of a trial balance with no rows
    "Cash 5,000"                                     one figure with no side and nothing to post

The fix is in `_solve_narrative`: if no line of the extracted entries or adjustments carries a non-zero
figure, there is nothing to post and the tile refuses with the reason.  The probe prints, for each shape,
whether the tile answered or refused and, when it answered, the figures it published.

    python qa/manual/probe_empty_instruction.py
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

SHAPES = (
    ("hello there", "no account and no figure"),
    ("Trial balance at 31 December 2026.\nCash\n", "a trial-balance header with no rows"),
    ("Cash 5,000", "one figure, no side, nothing to post"),
)


def report(record):
    scalars = (record.get("core") or {}).get("scalars") or {}
    published = {key: value for key, value in scalars.items()
                 if key in ("total_assets", "net_income", "total_equity")}
    return "ANSWERED problem_type=%r source=%r %s" % (
        record.get("problem_type"), record.get("reading_source"), json.dumps(published))


def run(label):
    from bp.product import statements
    print("--- %s ---" % label)
    for text, why in SHAPES:
        try:
            record = statements.solve(text)
        except statements.StatementError as exc:
            print("  %-46r REFUSED  %s" % (text[:44], str(exc)[:88]))
            continue
        print("  %-46r %s" % (text[:44], report(record)))
        print("  %-46s   (%s)" % ("", why))
    print("")


run("the product module on its own")

from bp import server  # noqa: E402,F401

run("with the plan layer attached, as the workbench attaches it")
