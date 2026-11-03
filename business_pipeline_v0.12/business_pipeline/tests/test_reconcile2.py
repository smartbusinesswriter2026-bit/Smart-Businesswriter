import unittest
from decimal import Decimal

from bp import reconcile2 as r2


class Reconcile2Tests(unittest.TestCase):
    def test_cash_ok(self):
        self.assertIsNone(r2.reconcile_cash_two_ways(Decimal("100"), Decimal("100")))

    def test_cash_fail(self):
        d = r2.reconcile_cash_two_ways(Decimal("100"), Decimal("90"))
        self.assertIsNotNone(d)
        self.assertEqual(d.gate, "cash_two_ways")

    def test_ni_ok(self):
        self.assertIsNone(r2.reconcile_ni_two_ways(Decimal("50"), Decimal("50")))

    def test_re_fail(self):
        d = r2.reconcile_re_two_ways(Decimal("10"), Decimal("9"))
        self.assertIsNotNone(d)


if __name__ == "__main__":
    unittest.main()
