"""Model-written commentary for the Portfolio Lab (student-confirmed).

The model may interpret the stored figures; it may not add a number, a fact or
advice.  These tests pin the guard, the confirmation and the report section.
"""

import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from bp.product import portfolio_prose  # noqa: E402


SNAPSHOT = {
    "date": "2026-11-09",
    "outputs": {"nav": "14541.93", "invested_value": "14541.93", "cash": "0",
                "top_weight": "0.4740", "top3_concentration": "1", "n_holdings": "3"},
    "positions": [{"symbol": "AAPL", "shares": "20", "price": "344.63", "value": "6892.60",
                   "weight": "0.4740"},
                  {"symbol": "MSFT", "shares": "8", "price": "521.91", "value": "4175.28",
                   "weight": "0.2871"},
                  {"symbol": "VOO", "shares": "5", "price": "694.81", "value": "3474.05",
                   "weight": "0.2389"}],
    "prices": {"AAPL": {"price": "344.63", "source": "user", "as_of": "2026-11-09"}},
    "checks": [], "method": "portfolio_valuation",
}


class ContextTest(unittest.TestCase):
    def test_the_context_carries_the_stored_figures_and_the_selection(self):
        context = portfolio_prose.build_context(
            SNAPSHOT, selection={"set": "finance", "parameters": ["pe_ratio"],
                                 "rows": [{"symbol": "AAPL", "values": {"pe_ratio": "44.90"},
                                           "reason": "core exposure"}]},
            holdings=[{"symbol": "AAPL", "rationale": "core exposure"}])
        self.assertEqual(context["figures"]["nav"], "14,541.93")
        self.assertEqual(context["selection"]["parameters"], ["pe_ratio"])
        self.assertIn("core exposure", context["holdings"]["AAPL"]["rationale"])

    def test_the_context_names_no_figure_that_is_not_stored(self):
        context = portfolio_prose.build_context(SNAPSHOT)
        allowed = portfolio_prose.allowed_numbers(context)
        self.assertIn("14541.930000", allowed)
        self.assertIn("0.474000", allowed)
        self.assertNotIn("999.000000", allowed)


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.context = portfolio_prose.build_context(SNAPSHOT)

    def test_text_that_adds_a_number_is_refused(self):
        with self.assertRaises(portfolio_prose.CommentaryRejected):
            portfolio_prose.audit("The book returned 12 percent last year.",
                                  self.context)

    def test_text_that_reuses_a_stored_number_passes(self):
        portfolio_prose.audit("The book's net asset value is 14541.93 across three holdings.",
                              self.context)

    def test_text_that_advises_is_refused(self):
        with self.assertRaises(portfolio_prose.CommentaryRejected):
            portfolio_prose.audit("The student should buy more of the largest holding.",
                                  self.context)

    def test_text_with_a_link_is_refused(self):
        with self.assertRaises(portfolio_prose.CommentaryRejected):
            portfolio_prose.audit("See https://example.com for the data.",
                                  self.context)

    def test_a_percentage_form_of_a_stored_ratio_is_allowed(self):
        portfolio_prose.audit("The largest holding carries 47.40% of the book.",
                              self.context)

    def test_an_empty_text_is_refused(self):
        with self.assertRaises(portfolio_prose.CommentaryRejected):
            portfolio_prose.audit("   ", self.context)


class DraftTest(unittest.TestCase):
    def setUp(self):
        self.context = portfolio_prose.build_context(SNAPSHOT)

    def test_a_draft_comes_from_the_model_and_passes_the_guard(self):
        with mock.patch("bp.product.prose.available", return_value=True):
            with mock.patch("bp.product.prose.propose_portfolio_paragraph",
                            return_value="The largest holding carries 47.40% of the book."):
                result = portfolio_prose.draft(self.context)
        self.assertIn("47.40%", result["text"])
        self.assertEqual(result["status"], "proposed")

    def test_a_draft_that_breaks_the_guard_is_refused(self):
        with mock.patch("bp.product.prose.available", return_value=True):
            with mock.patch("bp.product.prose.propose_portfolio_paragraph",
                            return_value="The book returned 12 percent last year."):
                with self.assertRaises(portfolio_prose.CommentaryRejected):
                    portfolio_prose.draft(self.context)

    def test_without_a_model_the_draft_is_a_named_gap(self):
        with mock.patch("bp.product.prose.available", return_value=False):
            with self.assertRaises(portfolio_prose.CommentaryRejected):
                portfolio_prose.draft(self.context)


if __name__ == "__main__":
    unittest.main()
