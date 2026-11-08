"""Trap test: a problem with nothing to adjust must not report a missing adjustment.

Before the fix, `_solve_transactions` unconditionally wrote
"no adjusting entries were derived (prepaids, depreciation, COGS, tax); only the
stated transactions were posted" into `working.missing`, even for a one-line
problem that contains no adjustment cue at all.  That false gap polluted the
statement-library gap report (51 distinct problems) and told the student
something was missing when nothing was.

The rule: the message is reported only when the instruction actually mentions an
adjustment kind (accrued, prepaid, depreciat, allowance, warranty, ...).
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp import statement_plan  # noqa: E402
from bp.product import statements  # noqa: E402

ADJUSTMENT_GAP = "no adjusting entries were derived"


def attach():
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs),
        build=lambda plan: statement_plan.build(plan))


class GapNoiseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        attach()

    @classmethod
    def tearDownClass(cls):
        statements.reset_core()

    def test_a_simple_transaction_reports_no_missing_adjustment(self):
        record = statements.solve(
            "The owner invested 50,000 cash in the business for shares on 1 January 2025.",
            currency="USD")
        self.assertTrue(record["solved"], record.get("refusal"))
        missing = (record.get("working") or {}).get("missing") or []
        self.assertFalse(
            any(ADJUSTMENT_GAP in str(item) for item in missing),
            "a problem with no adjustment cue must not report a missing adjustment: %r" % (missing,))

    def test_the_cue_helper_separates_the_two_cases(self):
        self.assertFalse(statements._needs_adjustments("Issued common stock for 80,000 cash."))
        self.assertTrue(statements._needs_adjustments("Accrued salaries of 3,000 are unpaid at year end."))
        self.assertTrue(statements._needs_adjustments("Depreciation for the year is 2,000."))
        self.assertTrue(statements._needs_adjustments("Prepaid insurance of 6,000 for 12 months."))


if __name__ == "__main__":
    unittest.main()
