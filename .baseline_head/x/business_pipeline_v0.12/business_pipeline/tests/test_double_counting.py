import unittest
from decimal import Decimal

from bp import double_counting as dc


class DoubleCountingTests(unittest.TestCase):
    def test_bad_debt(self):
        self.assertEqual(dc.bad_debt_expense(Decimal("5000"), Decimal("1000")), Decimal("4000"))

    def test_addback_list(self):
        self.assertEqual(dc.check_non_operating_addbacks(["gain_on_disposal"]), ["gain_on_disposal"])


if __name__ == "__main__":
    unittest.main()
