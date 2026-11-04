import unittest
from decimal import Decimal

from bp import statement_runtime as rt


class RuntimeBasic(unittest.TestCase):
    def test_ok_path(self):
        r = rt.run("Cash sales of $50,000. Credit sales of $30,000.")
        self.assertEqual(r.status, "ok")
        self.assertTrue(r.gates["tb_balanced"])
        self.assertEqual(r.trial_balance["1000"], Decimal("50000"))
        self.assertEqual(r.trial_balance["1100"], Decimal("30000"))

    def test_empty_routes_to_review(self):
        r = rt.run("")
        self.assertEqual(r.status, "review")
        self.assertEqual(r.review.stage, "INGEST")

    def test_conflict_routes_to_review(self):
        r = rt.run("Interest paid annually. Interest is paid in full at maturity.")
        self.assertEqual(r.status, "review")
        self.assertEqual(r.review.stage, "RESOLVE")

    def test_unknown_account_routes_to_review(self):
        chart = {"4000": {}}  # missing 1000
        r = rt.run("Cash sales of $50,000.", chart=chart)
        self.assertEqual(r.status, "review")
        self.assertEqual(r.review.stage, "JOURNALIZE")


if __name__ == "__main__":
    unittest.main()
