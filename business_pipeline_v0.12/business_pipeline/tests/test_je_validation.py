import unittest
from decimal import Decimal

from bp import je_validation as jv


class JEValidationTests(unittest.TestCase):
    def test_balanced_ok(self):
        lines = [("1000", "Dr", Decimal("50")), ("4000", "Cr", Decimal("50"))]
        self.assertEqual(jv.validate_je("JE1", lines, {"1000": {}, "4000": {}}), [])

    def test_unbalanced(self):
        lines = [("1000", "Dr", Decimal("50")), ("4000", "Cr", Decimal("40"))]
        issues = jv.validate_je("JE1", lines, {"1000": {}, "4000": {}})
        self.assertTrue(any(i.check == "balanced" for i in issues))

    def test_unknown_account(self):
        lines = [("9999", "Dr", Decimal("50")), ("4000", "Cr", Decimal("50"))]
        issues = jv.validate_je("JE1", lines, {"4000": {}})
        self.assertTrue(any(i.check == "account_exists" for i in issues))

    def test_zero_line(self):
        lines = [("1000", "Dr", Decimal("0")), ("4000", "Cr", Decimal("0"))]
        issues = jv.validate_je("JE1", lines, {"1000": {}, "4000": {}})
        self.assertTrue(any(i.check == "no_zero" for i in issues))


if __name__ == "__main__":
    unittest.main()
