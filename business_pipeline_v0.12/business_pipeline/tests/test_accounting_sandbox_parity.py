"""Sandbox parity for the accounting engagement, including the new schedule kinds.

The pipeline runs computations in a guarded subprocess in production, and `tests/test_sandbox.py` proves
parity for each method's own case. The accounting engagement grew eight schedule kinds and several new
appendix blocks after that case was written, so parity for those inputs was unproven - it was checked by
hand once and nothing would have noticed a regression.

This makes it permanent: the same specification is built in-process and inside the subprocess, and the
scalars and check results must agree exactly.
"""

import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from bp import accounts as accounts_mod         # noqa: E402
from bp.sandbox import SubprocessSandbox        # noqa: E402
from test_accounting_pipeline_integration import the_engagement   # noqa: E402


class TheEngagementAgreesAcrossTheSandbox(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = the_engagement()
        cls.local = accounts_mod.build(cls.spec)
        cls.sandbox = SubprocessSandbox()
        cls.results, cls.outputs, cls.meta = cls.sandbox.verify_execute(
            "management_accounts", {"spec": cls.spec})

    def test_every_check_passes_in_the_sandbox(self):
        failed = [name for name, ok in self.results if not ok]
        self.assertEqual(failed, [], "checks failed inside the sandbox: %r" % (failed,))
        self.assertEqual(len(self.results), 11, "all eleven frozen checks must run")

    def test_the_check_results_match_in_process(self):
        local = [(n, ok) for n, ok, _ in self.local["_checks"]]
        self.assertEqual([n for n, _ in local], [n for n, _ in self.results])
        self.assertEqual([ok for _, ok in local], [ok for _, ok in self.results])

    def test_every_scalar_matches_in_process(self):
        mismatches = []
        for key, value in self.outputs.items():
            if key not in self.local:
                continue
            if D(str(self.local[key])) != D(str(value)):
                mismatches.append((key, str(self.local[key]), str(value)))
        self.assertEqual(mismatches, [], "in-process and sandbox scalars differ: %r" % (mismatches,))

    def test_the_delivered_scalars_are_all_present(self):
        for key in ("net_income", "total_assets", "total_liabilities", "total_equity",
                    "retained_earnings_closing", "cash_net", "n_entries"):
            self.assertIn(key, self.outputs, "%s missing from the sandbox output" % key)


if __name__ == "__main__":
    unittest.main()
