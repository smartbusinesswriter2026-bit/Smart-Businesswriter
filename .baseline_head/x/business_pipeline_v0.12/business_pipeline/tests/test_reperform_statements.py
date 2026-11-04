"""Re-performance must cover the document, not only the scalars.

Re-performance re-runs a delivered bundle and compares what it delivered. Until now that comparison
covered the scalar outputs alone: net income, total assets, the check counts. But a student submits a
**document** - statements, T-accounts, the journal - and a change to how those render would leave every
scalar identical while the document drifted.

So the bundle now carries `statements_hash`, a hash over the rendered appendix, and re-performance compares
it. These tests prove it is present, that it verifies, that a tampered hash is caught, and that bundles
written before the field existed still verify on their scalars alone.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from bp.orchestrator import Pipeline          # noqa: E402
from bp.reperform import reperform            # noqa: E402
from bp.sandbox import SubprocessSandbox      # noqa: E402
from test_accounting_pipeline_integration import the_engagement   # noqa: E402


def request():
    return {"objective": "integration", "method": "management_accounts", "currency": "USD",
            "period": "annual", "inputs": {"spec": the_engagement()}}


class StatementsAreRePerformed(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sb = SubprocessSandbox()
        cls.delivery = Pipeline(sandbox=cls.sb).run(request(), lambda s: True)
        cls.bundle = cls.delivery.appendix["reperform"]

    def test_the_bundle_carries_a_statements_hash(self):
        self.assertIsNotNone(self.bundle.get("statements_hash"),
                             "an accounting delivery must hash its rendered appendix")

    def test_an_untouched_bundle_verifies_including_the_statements(self):
        r = reperform(self.bundle, self.sb)
        self.assertTrue(r["verified"], r["differences"])
        self.assertEqual(r["statements"], "exact")
        self.assertTrue(r["all_exact"])
        self.assertEqual(r["differences"], [])

    def test_a_tampered_statements_hash_is_detected(self):
        t = json.loads(json.dumps(self.bundle))
        t["statements_hash"] = "0" * 64
        r = reperform(t, self.sb)
        self.assertFalse(r["verified"])
        self.assertEqual(r["statements"], "mismatch")
        self.assertTrue(any("statements" in d for d in r["differences"]))

    def test_a_tampered_scalar_is_still_detected(self):
        t = json.loads(json.dumps(self.bundle))
        t["outputs"]["net_income"] = "999.99"
        r = reperform(t, self.sb)
        self.assertFalse(r["verified"])
        self.assertTrue(any("net_income" in d for d in r["differences"]))

    def test_a_bundle_without_the_field_still_verifies_on_its_scalars(self):
        """Bundles delivered before the field existed must keep working."""
        t = json.loads(json.dumps(self.bundle))
        t.pop("statements_hash", None)
        r = reperform(t, self.sb)
        self.assertTrue(r["verified"], r["differences"])
        self.assertIsNone(r["statements"], "no hash means the appendix was not checked")


class AMethodWithoutAnAppendix(unittest.TestCase):
    """A method that returns no rendered appendix has nothing to hash, and must not fail."""

    @classmethod
    def setUpClass(cls):
        cls.sb = SubprocessSandbox()

    def test_an_ordinary_method_bundle_has_no_statements_hash(self):
        req = {"objective": "Should we invest in this project?", "method": "npv", "currency": "USD",
               "period": "annual",
               "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}}
        d = Pipeline(sandbox=self.sb).run(req, lambda s: True)
        self.assertEqual(d.status, "delivered", d.report[:120])
        bundle = d.appendix["reperform"]
        self.assertIsNone(bundle.get("statements_hash"))
        r = reperform(bundle, self.sb)
        self.assertTrue(r["verified"], r["differences"])
        self.assertIsNone(r["statements"])


if __name__ == "__main__":
    unittest.main()
