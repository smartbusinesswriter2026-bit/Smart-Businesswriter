"""A planned break-even with no figures must not refuse the whole paper."""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

from bp.product import chat  # noqa: E402


class BreakEvenPaperTest(unittest.TestCase):
    def test_no_figures_names_the_gap_instead_of_refusing(self):
        lines = chat._break_even_paper_lines({}, {})
        self.assertTrue(lines)
        self.assertIn("No figure is reported", lines[0])
        self.assertIn("fixed costs", lines[0])

    def test_a_run_computation_prints_its_own_result(self):
        state = {"computations": {"breakeven": {
            "ok": True,
            "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
            "result": {"breakeven_units": "100", "breakeven_revenue": "2000",
                       "contribution_margin": "10", "contribution_margin_ratio": "0.5"},
        }}}
        lines = chat._break_even_paper_lines(state, {})
        self.assertIn("100", lines[0])
        self.assertIn("2,000", lines[0])

    def test_a_refused_computation_names_the_core_message(self):
        state = {"computations": {"breakeven": {"ok": False, "error": "the declared figures do not give a positive price"}}}
        lines = chat._break_even_paper_lines(state, {})
        self.assertIn("could not be run", lines[0])
        self.assertIn("positive price", lines[0])


if __name__ == "__main__":
    unittest.main()
