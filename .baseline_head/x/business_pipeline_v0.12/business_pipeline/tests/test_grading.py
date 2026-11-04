import unittest
from decimal import Decimal

from bp import grading as gr


class GradingTests(unittest.TestCase):
    def test_correct(self):
        exp = {"IS": {"lines": [{"label": "Net income", "value": "100", "kind": "line"}]}}
        usr = {"IS": {"lines": [{"label": "Net income", "value": "100"}]}}
        r = gr.grade(usr, exp)
        self.assertTrue(r.is_correct)
        self.assertEqual(r.overall_score, 1.0)

    def test_mismatch(self):
        exp = {"IS": {"lines": [{"label": "Net income", "value": "100", "kind": "line"}]}}
        usr = {"IS": {"lines": [{"label": "Net income", "value": "90"}]}}
        r = gr.grade(usr, exp)
        self.assertFalse(r.is_correct)
        self.assertEqual(len(r.mismatches), 1)


if __name__ == "__main__":
    unittest.main()
