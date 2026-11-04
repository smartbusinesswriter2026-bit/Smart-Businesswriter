import unittest
from datetime import date
from decimal import Decimal

from bp import timing


class TimingTests(unittest.TestCase):
    def test_months_expired_11(self):
        self.assertEqual(timing.months_expired(date(2025, 2, 1), date(2026, 1, 31), date(2025, 12, 31)), 11)

    def test_depreciation_full_year(self):
        self.assertEqual(timing.depreciation_for_year(Decimal("60000"), Decimal("0"), 5,
                                                     date(2025, 1, 1), date(2025, 12, 31), "full_year"),
                         Decimal("12000.00"))

    def test_resolve_none(self):
        self.assertIsNone(timing.resolve_depreciation_convention("no convention here"))
        self.assertEqual(timing.resolve_depreciation_convention("A full year of depreciation is recorded."),
                         "full_year")

    def test_interest_at_maturity(self):
        self.assertEqual(timing.resolve_interest_timing("interest is paid in full at maturity"), "at_maturity")


if __name__ == "__main__":
    unittest.main()
