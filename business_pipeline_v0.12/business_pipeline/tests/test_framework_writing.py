"""Framework writing: source tier, recency, strength and source IDs.

These are the rules the evidence audit is built on.  They are product
conventions, not facts about a source, so each one is declared here once and
printed in the audit note.  A missing tier must never be guessed as strong.
"""

import datetime
import sys
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp.product import completion, framework_writing  # noqa: E402

NOW = datetime.datetime(2026, 11, 9, tzinfo=datetime.timezone.utc)


class TierTest(unittest.TestCase):
    def test_scholarly_indexes_are_tier_b(self):
        for database in ("OpenAlex", "Crossref", "Semantic Scholar", "DOAJ"):
            self.assertEqual(
                framework_writing.tier_for({"database": database, "title": "A study"}),
                "B", database)

    def test_a_corpus_book_is_tier_b(self):
        self.assertEqual(
            framework_writing.tier_for({"database": "Proprietary corpus",
                                        "title": "Strategy", "abstract": "Text."}),
            "B")

    def test_a_primary_filing_is_tier_a(self):
        for database in ("SEC EDGAR", "World Bank", "IMF", "OECD"):
            self.assertEqual(
                framework_writing.tier_for({"database": database, "title": "Annual report"}),
                "A", database)

    def test_vetted_industry_or_journalism_is_tier_b(self):
        self.assertEqual(
            framework_writing.tier_for({"database": "vetted web",
                                        "title": "The state of grocery retail",
                                        "url": "https://example.org/report"}),
            "B")

    def test_vetted_press_release_vendor_page_and_blog_are_tier_c(self):
        for item in (
            {"database": "vetted web", "title": "Press release: new plant",
             "url": "https://example.org/newsroom/x"},
            {"database": "vetted web", "title": "Why our product leads",
             "url": "https://vendor.example/blog/post"},
            {"database": "vetted web", "title": "Opinion: the market",
             "url": "https://example.org/opinion/x"},
        ):
            self.assertEqual(framework_writing.tier_for(item), "C", item["title"])

    def test_orientation_and_preprint_are_tier_c(self):
        self.assertEqual(framework_writing.tier_for({"database": "orientation web",
                                                     "title": "Explainer"}), "C")
        self.assertEqual(framework_writing.tier_for({"database": "arXiv",
                                                     "title": "Preprint"}), "C")

    def test_an_unknown_database_is_weak_not_strong(self):
        self.assertEqual(framework_writing.tier_for({"database": "Some index",
                                                     "title": "A study"}), "C")

    def test_a_source_with_no_database_or_title_is_tier_d(self):
        self.assertEqual(framework_writing.tier_for({}), "D")
        self.assertEqual(framework_writing.tier_for(None), "D")


class RecencyTest(unittest.TestCase):
    def test_three_year_window_is_current(self):
        for year in (2026, 2025, 2024, 2023):
            self.assertEqual(framework_writing.recency_for({"year": year}, NOW),
                             "current", year)

    def test_older_than_three_years_is_stale(self):
        for year in (2022, 2019, 1990):
            self.assertEqual(framework_writing.recency_for({"year": year}, NOW),
                             "stale", year)

    def test_no_year_is_undated(self):
        self.assertEqual(framework_writing.recency_for({}, NOW), "undated")
        self.assertEqual(framework_writing.recency_for({"year": ""}, NOW), "undated")
        self.assertEqual(framework_writing.recency_for({"year": "n.d."}, NOW), "undated")


class StrengthTest(unittest.TestCase):
    def test_primary_current_and_quantified_is_strong(self):
        self.assertEqual(framework_writing.strength_for("A", "current", quantified=True),
                         "Strong")
        self.assertEqual(framework_writing.strength_for("B", "current", quantified=True),
                         "Strong")

    def test_unquantified_claim_is_capped_at_moderate(self):
        self.assertEqual(framework_writing.strength_for("A", "current", quantified=False),
                         "Moderate")

    def test_stale_evidence_caps_at_moderate(self):
        self.assertEqual(framework_writing.strength_for("A", "stale", quantified=True),
                         "Moderate")

    def test_weak_or_undated_is_weak(self):
        self.assertEqual(framework_writing.strength_for("C", "current", quantified=True),
                         "Weak")
        self.assertEqual(framework_writing.strength_for("D", "current", quantified=True),
                         "Weak")
        self.assertEqual(framework_writing.strength_for("A", "undated", quantified=True),
                         "Weak")


class SourceIdTest(unittest.TestCase):
    def test_the_same_source_keeps_one_id_across_dimensions(self):
        blocks = [
            {"key": "a", "items": [
                {"text": "One.", "provenance": "sourced", "source": "Lovelace (2024)."},
                {"text": "Two.", "provenance": "sourced", "source": "Turing (2023)."},
            ]},
            {"key": "b", "items": [
                {"text": "Three.", "provenance": "sourced", "source": "Lovelace (2024)."},
                {"text": "Mine.", "provenance": "student", "source": ""},
            ]},
        ]
        mapping = framework_writing.assign_source_ids(blocks)
        self.assertEqual(mapping["Lovelace (2024)."], "S1")
        self.assertEqual(mapping["Turing (2023)."], "S2")
        self.assertEqual(blocks[0]["items"][0]["source_id"], "S1")
        self.assertEqual(blocks[1]["items"][0]["source_id"], "S1")
        self.assertFalse(blocks[1]["items"][1].get("source_id"))

    def test_ids_are_stable_for_the_same_order(self):
        blocks = [{"key": "a", "items": [
            {"text": "One.", "provenance": "sourced", "source": "A."},
            {"text": "Two.", "provenance": "sourced", "source": "B."}]}]
        first = framework_writing.assign_source_ids(blocks)
        second = framework_writing.assign_source_ids(blocks)
        self.assertEqual(first, second)
        self.assertEqual(list(first.values()), ["S1", "S2"])


def a_reading(**over):
    """A complete reading; each test changes one field to prove one refusal."""
    base = {
        "rating": "High",
        "drivers": [{"driver": "price competition", "evidence": 0, "type": "F"}],
        "trend": "Rising",
        "trend_reason": "Price competition is intense.",
        "profitability_impact": "Margins fall as buyers compare prices.",
        "confidence": "Medium",
        "confidence_reason": "One current study supports the reading.",
        "so_what": "A new entrant must justify its price.",
        "rationale": "The evidence names price competition directly.",
    }
    base.update(over)
    return base


ITEMS = [{
    "text": "Price competition is intense in grocery retail.",
    "provenance": "sourced", "source": "Lovelace (2024).",
    "citation": "(Lovelace, 2024)", "title": "Rivalry in grocery retail",
    "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
}]


class ReadingTest(unittest.TestCase):
    def test_a_complete_reading_is_accepted(self):
        clean = framework_writing.validate_reading(a_reading(), ITEMS)
        self.assertEqual(clean["rating"], "High")
        self.assertEqual(clean["trend"], "Rising")
        self.assertEqual(clean["confidence"], "Medium")
        self.assertEqual(clean["drivers"][0]["evidence"], 0)

    def test_an_unknown_rating_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(a_reading(rating="Very High"), ITEMS)
        self.assertIn("rating", str(refused.exception).lower())

    def test_a_driver_outside_the_items_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(drivers=[{"driver": "price", "evidence": 4, "type": "F"}]), ITEMS)
        self.assertIn("evidence", str(refused.exception).lower())

    def test_a_fact_with_no_evidence_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(drivers=[{"driver": "price", "evidence": None, "type": "F"}]), ITEMS)
        self.assertIn("evidence", str(refused.exception).lower())

    def test_a_judgment_cannot_cite_an_item_as_its_evidence(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(drivers=[{"driver": "price", "evidence": 0, "type": "J"}]), ITEMS)
        self.assertIn("judgment", str(refused.exception).lower())

    def test_an_empty_so_what_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(a_reading(so_what="  "), ITEMS)
        self.assertIn("so_what", str(refused.exception).lower())

    def test_an_empty_confidence_reason_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(a_reading(confidence_reason=""), ITEMS)
        self.assertIn("confidence_reason", str(refused.exception).lower())

    def test_an_invented_number_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(profitability_impact="Margins fall 12% as buyers compare prices."), ITEMS)
        self.assertIn("number", str(refused.exception).lower())

    def test_an_invented_name_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(rationale="The evidence is the Amazon case."), ITEMS)
        self.assertIn("name", str(refused.exception).lower())

    def test_a_hypothesis_needs_a_test(self):
        clean = framework_writing.validate_reading(
            a_reading(drivers=[{"driver": "buyers will switch", "evidence": None, "type": "H",
                                "test": "a pilot with twenty buyers"}]), ITEMS)
        self.assertEqual(clean["drivers"][0]["type"], "H")
        self.assertIn("pilot", clean["drivers"][0]["test"])

    def test_a_hypothesis_without_a_test_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(drivers=[{"driver": "buyers will switch", "evidence": None,
                                    "type": "H"}]), ITEMS)
        self.assertIn("hypothesis", str(refused.exception).lower())

    def test_the_register_lists_hypotheses_with_their_tests(self):
        block = {"key": "x", "label": "Diversification", "items": list(ITEMS),
                 "reading": a_reading(
                     drivers=[{"driver": "buyers will switch", "evidence": None, "type": "H",
                               "test": "a pilot with twenty buyers"}],
                     confidence="Low", rationale="The move is untested.")}
        register = framework_writing.assumption_register([block])
        self.assertEqual(register["columns"][0], "Assumption")
        self.assertEqual(len(register["rows"]), 1)
        self.assertIn("a pilot with twenty buyers", register["rows"][0])

    def test_a_contradiction_is_recorded(self):
        clean = framework_writing.validate_reading(
            a_reading(contradictions=["A second study reports stable prices."]), ITEMS)
        self.assertEqual(len(clean["contradictions"]), 1)

    def test_a_contradiction_with_an_invented_number_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(
                a_reading(contradictions=["A study reports 37% growth."]), ITEMS)
        self.assertIn("contradiction", str(refused.exception).lower())

    def test_a_rating_on_an_empty_block_is_refused(self):
        with self.assertRaises(framework_writing.ReadingError) as refused:
            framework_writing.validate_reading(a_reading(), [])
        self.assertIn("accepted item", str(refused.exception).lower())

    def test_a_valid_reading_is_attached_as_proposed(self):
        block = {"key": "rivalry", "label": "Industry rivalry", "items": list(ITEMS)}
        stored = completion._attach_reading(block, {"reading": a_reading()}, None)
        self.assertEqual(stored["status"], "proposed")
        self.assertEqual(block["reading"]["rating"], "High")

    def test_an_invalid_reading_is_dropped_and_named(self):
        block = {"key": "rivalry", "label": "Industry rivalry", "items": list(ITEMS)}
        stored = completion._attach_reading(block, {"reading": a_reading(rating="Very High")}, None)
        self.assertIsNone(stored)
        self.assertEqual(block["reading"]["status"], "absent")
        self.assertIn("rating", block["reading"]["reason"].lower())

    def test_a_reply_without_a_reading_leaves_the_block_alone(self):
        block = {"key": "rivalry", "label": "Industry rivalry", "items": list(ITEMS)}
        self.assertIsNone(completion._attach_reading(block, {"paragraphs": ["Text."]}, None))
        self.assertNotIn("reading", block)


class ItemMetadataTest(unittest.TestCase):
    def test_one_block_keeps_the_metadata_the_audit_needs(self):
        source = {
            "title": "Rivalry in smartphones",
            "abstract": "Price competition is intense. A second sentence follows.",
            "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"],
            "year": 2024, "venue": "Journal of Strategy",
            "doi": "10.1/abc", "url": "https://doi.org/10.1/abc",
            "database": "OpenAlex",
        }
        found = {"items": [source], "queries": ["q"], "dropped": 0, "errors": [],
                 "skipped": [], "notices": [], "timed_out": False}
        profile = completion._profile("template_five_forces")
        block = profile["blocks"][0]
        with mock.patch("bp.product.retrieval.retrieve", return_value=found):
            result = completion._one_block(profile, block, "smartphones", "Global", 2016)
        item = result["items"][0]
        self.assertEqual(item["year"], 2024)
        self.assertEqual(item["database"], "OpenAlex")
        self.assertEqual(item["url"], "https://doi.org/10.1/abc")
        self.assertEqual(item["doi"], "10.1/abc")
        self.assertEqual(item["tier"], "B")
        self.assertEqual(item["recency"], "current")


if __name__ == "__main__":
    unittest.main()
