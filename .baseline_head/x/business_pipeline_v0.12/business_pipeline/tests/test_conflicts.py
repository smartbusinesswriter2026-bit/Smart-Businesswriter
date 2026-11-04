import unittest

from bp import conflicts as cf


class _Claim:
    def __init__(self, text, span=None):
        self.text = text
        self.span = span


class ConflictsTests(unittest.TestCase):
    def test_conflict_detected(self):
        claims = [_Claim("interest paid annually on Dec. 31"),
                  _Claim("interest is paid in full at maturity")]
        issues = cf.detect_convention_conflicts(claims)
        self.assertTrue(any(i.input_ref == "interest_timing" for i in issues))

    def test_no_conflict(self):
        claims = [_Claim("interest paid annually on Dec. 31")]
        issues = cf.detect_convention_conflicts(claims)
        self.assertEqual(issues, [])


if __name__ == "__main__":
    unittest.main()
