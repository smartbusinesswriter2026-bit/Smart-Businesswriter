"""The eval rubric: the checks are the code's, not a model's (product layer).

The rubric reuses the product's own readers, so these tests check that the
rubric reads a document the way the paper path reads it.
"""
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp.product import eval_rubric  # noqa: E402
from bp.product import paper_batch  # noqa: E402


class RubricTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="eval-rubric-")
        self._saved_env = dict(os.environ)
        os.environ["BP_STATE_DIR"] = os.path.join(self._tmp, "state")
        os.environ["BP_OPS_LOG"] = os.path.join(self._tmp, "ops_log")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved_env)
        shutil.rmtree(self._tmp, ignore_errors=True)


class SectionTest(RubricTestCase):
    def test_a_missing_section_is_named(self):
        result = eval_rubric.score_sections("Result\nThe figure.", contract={"sections": ["Result", "Inputs and results"]})
        self.assertFalse(result["ok"])
        self.assertEqual(result["missing"], ["Inputs and results"])

    def test_the_legacy_phrase_is_mapped_onto_the_heading_the_paper_carries(self):
        result = eval_rubric.score_sections("What you declared", contains=["Declared inputs"])
        self.assertTrue(result["ok"])

    def test_a_reference_list_is_never_demanded(self):
        """The tile paper deliberately omits one; the rubric must not ask for it."""
        result = eval_rubric.score_sections("Result", contains=["References", "Bibliography"])
        self.assertTrue(result["ok"])


class ValueTest(RubricTestCase):
    def test_a_computed_value_in_the_paper_is_found(self):
        result = eval_rubric.score_values("The breakeven point is 1,250 units.", {"breakeven": "1250"})
        self.assertTrue(result["ok"])
        self.assertTrue(result["in_paper"])

    def test_a_computed_value_that_is_absent_is_caught(self):
        result = eval_rubric.score_values("Nothing was computed here.", {"breakeven": "1250"})
        self.assertFalse(result["ok"])

    def test_a_zero_is_not_looked_for(self):
        """A padded zero is not a value the paper must show."""
        result = eval_rubric.score_values("The paper says nothing.", {"padding": "0"})
        self.assertEqual(result["values"], [])
        self.assertFalse(result["ok"])

    def test_the_workbook_is_checked_separately(self):
        result = eval_rubric.score_values("text", {"x": "42"}, workbook_text="the result 42")
        self.assertTrue(result["in_workbook"])


class TemplateTest(RubricTestCase):
    def test_a_template_instruction_is_caught(self):
        result = eval_rubric.score_template_instructions("Result\n[your name]\nThe figure.")
        self.assertFalse(result["ok"])
        self.assertTrue(result["found"])

    def test_a_clean_paper_passes(self):
        result = eval_rubric.score_template_instructions("Result\nThe breakeven point is 1,250 units.")
        self.assertTrue(result["ok"])


class LengthTest(RubricTestCase):
    def test_the_word_count_and_the_band_are_recorded(self):
        result = eval_rubric.score_length("one two three four five")
        self.assertEqual(result["words"], 5)
        self.assertEqual(result["band"], "short")

    def test_a_tile_paper_is_not_failed_for_being_short(self):
        """The tile paper is the computation record; its length is an observation."""
        result = eval_rubric.score_length("one two three four five", target=1200)
        self.assertFalse(result["scored"])
        self.assertFalse(result["met_target"])


class SentenceTest(RubricTestCase):
    def test_a_fragment_is_not_a_sentence(self):
        self.assertFalse(eval_rubric._is_sentence("Total pool cost: 200000"))

    def test_a_complete_sentence_is_a_sentence(self):
        self.assertTrue(eval_rubric._is_sentence(
            "The break-even point is reached when the contribution covers the fixed cost."))

    def test_the_product_extractor_returns_a_verbatim_sentence_of_the_page(self):
        """The 'must be capable of direct quotes' requirement, proved on the product."""
        page = ("Activity-based costing allocates the cost of each activity to the products "
                "that consume it. The rate is the pool cost divided by the driver volume. "
                "Each product is then charged at that rate for the drivers it uses.")
        quote, score = paper_batch._best_sentence(page, ["activity", "pool", "cost", "driver"])
        self.assertIn(quote, page)
        self.assertTrue(quote.endswith((".", "!", "?")))
        self.assertGreaterEqual(score, 2)


class RagTest(RubricTestCase):
    """The corpus is asked before it is believed."""

    def test_a_down_corpus_is_not_measured_and_never_a_pass(self):
        with mock.patch("bp.product.eval_rubric.paper_batch._seed_corpus") as seed:
            seed.return_value = (0, [], [])
            with mock.patch("bp.product.eval_runner.corpus_available", return_value=False):
                result = eval_rubric.score_rag("accounting", "abc")
        self.assertFalse(result["measured"])
        self.assertFalse(result["corpus_available"])
        self.assertIn("corpus", result["reason"].lower())

    def test_a_cited_page_must_carry_a_title_and_a_quote(self):
        state = {"sources": [{"title": "", "abstract": "A short fragment", "database": "Proprietary corpus"}],
                 "background": [], "gaps": []}
        with mock.patch("bp.product.eval_rubric.paper_batch._seed_corpus") as seed:
            seed.side_effect = lambda s, *a, **k: (s.update(state), (1, [], []))[1]
            with mock.patch("bp.product.eval_runner.corpus_available", return_value=True):
                result = eval_rubric.score_rag("accounting", "abc")
        self.assertTrue(result["measured"])
        self.assertTrue(result["problems"])

    def test_a_background_page_is_never_cited(self):
        state = {
            "sources": [{"title": "Cost Accounting", "abstract": "Activity based costing is used when a single volume measure distorts product cost.",
                         "database": "Proprietary corpus"}],
            "background": [{"title": "Cost Accounting", "quote": "Cost accounting is old.", "database": "Proprietary corpus"}],
            "gaps": [],
        }
        with mock.patch("bp.product.eval_rubric.paper_batch._seed_corpus") as seed:
            seed.side_effect = lambda s, *a, **k: (s.update(state), (1, [], []))[1]
            with mock.patch("bp.product.eval_runner.corpus_available", return_value=True):
                result = eval_rubric.score_rag("accounting", "abc")
        self.assertTrue(any("background page is cited" in p for p in result["problems"]))

    def test_no_evidence_and_no_gap_is_a_problem(self):
        state = {"sources": [], "background": [], "gaps": []}
        with mock.patch("bp.product.eval_rubric.paper_batch._seed_corpus") as seed:
            seed.side_effect = lambda s, *a, **k: (s.update(state), (0, [], []))[1]
            with mock.patch("bp.product.eval_runner.corpus_available", return_value=True):
                result = eval_rubric.score_rag("accounting", "abc")
        self.assertTrue(any("no gap was named" in p for p in result["problems"]))


class WholePaperTest(RubricTestCase):
    def test_a_clean_paper_passes_the_rubric(self):
        text = ("Result\nThe break-even point is 1,250 units.\n"
                "Inputs and results\nWhat you declared\n")
        result = eval_rubric.score_paper(text, computed={"breakeven": "1250"},
                                         contract={"sections": ["Result", "Inputs and results"]})
        self.assertTrue(result["passed"])
        self.assertEqual(result["problems"], [])

    def test_a_paper_with_a_template_instruction_fails(self):
        text = "Result\n[your name]\nThe break-even point is 1,250 units.\n"
        result = eval_rubric.score_paper(text, computed={"breakeven": "1250"},
                                         contract={"sections": ["Result"]})
        self.assertFalse(result["passed"])

    def test_a_paper_without_its_values_fails(self):
        text = "Result\nNothing was computed here.\n"
        result = eval_rubric.score_paper(text, computed={"breakeven": "1250"},
                                         contract={"sections": ["Result"]})
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
