"""Why does the new route test pass alone and fail in the full suite?

Hypothesis: `bp.server` wires the product module when it is imported, and the
product's behaviour then differs from the unwired module the test exercises.

    python qa/manual/probe_route_test_order.py
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from bp.product import statements  # noqa: E402

TEXT = "Compute the cash conversion cycle for the period."


def attempt(label):
    try:
        record = statements.solve(TEXT)
    except statements.StatementError as exc:
        print("%-28s StatementError: %s" % (label, str(exc)[:90]))
        return
    except Exception as exc:  # noqa: BLE001
        print("%-28s other error: %s: %s" % (label, type(exc).__name__, str(exc)[:90]))
        return
    print("%-28s ANSWERED: problem_type=%r keys=%s"
          % (label, record.get("problem_type"), sorted(record)[:8]))


print("--- the product module on its own ---")
attempt("unwired")

print("")
print("--- after importing bp.server (what the full suite does) ---")
from bp import server  # noqa: E402,F401
attempt("after bp.server import")

print("")
print("--- the test itself, alone ---")
suite = unittest.TestLoader().loadTestsFromName(
    "tests.test_statement_reader_seams.RouteTest.test_a_route_that_computed_nothing_does_not_answer")
result = unittest.TextTestRunner(verbosity=2).run(suite)
print("alone -> failures=%d errors=%d" % (len(result.failures), len(result.errors)))

print("")
print("--- the test again, now that bp.server is imported ---")
suite = unittest.TestLoader().loadTestsFromName(
    "tests.test_statement_reader_seams.RouteTest.test_a_route_that_computed_nothing_does_not_answer")
result = unittest.TextTestRunner(verbosity=2).run(suite)
print("after import -> failures=%d errors=%d" % (len(result.failures), len(result.errors)))
