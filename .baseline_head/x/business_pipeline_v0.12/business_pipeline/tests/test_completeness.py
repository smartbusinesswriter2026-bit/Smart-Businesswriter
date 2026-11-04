import unittest

from bp import completeness as cp


class _Claim:
    def __init__(self, text, kind="adjustment_info"):
        self.text = text
        self.kind = kind


class CompletenessTests(unittest.TestCase):
    def test_missing(self):
        claims = [_Claim("Employees earned $3,000 of salaries in late December that remain unpaid.")]
        missing = cp.check_adjustment_completeness(claims, [])
        self.assertIn("record_accrued_salaries", missing)

    def test_complete(self):
        claims = [_Claim("Employees earned $3,000 of salaries in late December that remain unpaid.")]
        missing = cp.check_adjustment_completeness(claims, ["record_accrued_salaries"])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
