"""The research contract: closed vocabularies, the ledger, the grading rule.

The pipeline's research layer must be framework-aware and auditable.  These
tests pin the closed vocabularies (a research need, a rejection reason), the
ledger record every dimension carries, and the source-type grading rule.  They
are deliberately small: the contract is data and pure functions, so a future
framework can declare its research needs without touching the engine.
"""

import unittest

import sys
sys.path.insert(0, "src")

from bp.product import research_contract as rc  # noqa: E402


class VocabularyTest(unittest.TestCase):
    def test_the_research_needs_are_the_declared_starter_set(self):
        self.assertEqual(
            set(rc.ALL_NEEDS),
            {"market_size", "regulation", "competitor", "customer",
             "technology_trend", "industry_structure", "country_macro",
             "cost_price", "sustainability", "methodology"},
        )

    def test_is_need_accepts_a_declared_need_and_refuses_anything_else(self):
        self.assertTrue(rc.is_need("market_size"))
        self.assertFalse(rc.is_need("market size"))
        self.assertFalse(rc.is_need(""))

    def test_the_rejection_reasons_are_the_declared_set(self):
        self.assertEqual(
            set(rc.ALL_REASONS),
            {"no_cue", "no_geography", "tier_missing", "blocked_domain",
             "below_floor", "duplicate", "full_text_cue_missing"},
        )

    def test_is_reason_accepts_a_declared_reason_and_refuses_anything_else(self):
        self.assertTrue(rc.is_reason("no_cue"))
        self.assertFalse(rc.is_reason("not_a_reason"))


class LedgerTest(unittest.TestCase):
    def test_a_ledger_carries_accepted_rejected_gaps_and_background(self):
        ledger = rc.build_ledger(
            "political",
            accepted=[{"title": "A source", "source": "vetted web"}],
            rejected=[{"candidate": {"title": "B source"}, "reason": "no_geography"}],
            gaps=["no citable evidence"],
            background=[{"title": "C source"}],
        )
        self.assertEqual(ledger["dimension"], "political")
        self.assertEqual(len(ledger["accepted"]), 1)
        self.assertEqual(ledger["rejected"][0]["reason"], "no_geography")
        self.assertEqual(ledger["gaps"], ["no citable evidence"])
        self.assertEqual(len(ledger["background"]), 1)

    def test_a_rejected_entry_without_a_declared_reason_is_refused(self):
        with self.assertRaises(ValueError):
            rc.build_ledger("political", rejected=[{"candidate": {"title": "B"}, "reason": "made_up"}])

    def test_the_ledger_is_deterministic(self):
        first = rc.build_ledger("x", accepted=[{"title": "A"}], rejected=[])
        second = rc.build_ledger("x", accepted=[{"title": "A"}], rejected=[])
        self.assertEqual(first, second)


class GradingTest(unittest.TestCase):
    def test_a_dimension_with_an_official_source_passes(self):
        verdict = rc.grade_dimension(
            [{"tier": "news"}, {"tier": "official"}], ["official", "data"])
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["missing_tiers"], [])

    def test_a_dimension_with_only_news_fails_and_names_the_missing_tier(self):
        verdict = rc.grade_dimension([{"tier": "news"}], ["official", "data"])
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["missing_tiers"], ["official", "data"])

    def test_no_required_tiers_means_no_grading(self):
        verdict = rc.grade_dimension([{"tier": "news"}], [])
        self.assertTrue(verdict["ok"])
        self.assertEqual(verdict["missing_tiers"], [])

    def test_an_item_with_no_source_tier_is_not_graded(self):
        verdict = rc.grade_dimension([{"tier": "C"}], ["official", "data"])
        self.assertTrue(verdict["ok"])

    def test_the_source_tier_is_read_before_the_audit_tier(self):
        self.assertEqual(rc.source_tier_of({"source_tier": "official", "tier": "C"}), "official")
        self.assertEqual(rc.source_tier_of({"tier": "news"}), "news")
        self.assertEqual(rc.source_tier_of({"tier": "A"}), "")

    def test_filter_by_grade_drops_a_known_weaker_tier_and_keeps_an_unknown_one(self):
        kept, rejected = rc.filter_by_grade(
            [{"source_tier": "news"}, {"tier": "C"}, {"source_tier": "official"}],
            ["official", "data"])
        self.assertEqual([item.get("source_tier") for item in rejected], ["news"])
        self.assertEqual(len(kept), 2)


class SchemaTest(unittest.TestCase):
    def test_a_valid_research_block_has_no_problems(self):
        problems = rc.validate_research({
            "topics": {"political": "law"},
            "tiers": {"political": ["official", "data"]},
            "budget": 2,
            "needs": {"political": ["regulation"]},
            "required_tiers": {"political": ["official", "data"]},
        })
        self.assertEqual(problems, [])

    def test_an_unknown_need_is_a_problem(self):
        problems = rc.validate_research({"needs": {"political": ["made_up"]}})
        self.assertTrue(problems)
        self.assertIn("made_up", " ".join(problems))

    def test_an_unknown_tier_is_a_problem(self):
        problems = rc.validate_research({"tiers": {"political": ["primary"]}})
        self.assertTrue(problems)

    def test_a_budget_outside_the_band_is_a_problem(self):
        self.assertTrue(rc.validate_research({"budget": 0}))
        self.assertTrue(rc.validate_research({"budget": 9}))
        self.assertEqual(rc.validate_research({"budget": 3}), [])

    def test_an_unknown_key_is_a_problem(self):
        problems = rc.validate_research({"made_up": 1})
        self.assertTrue(problems)

    def test_absent_research_is_valid(self):
        self.assertEqual(rc.validate_research(None), [])


if __name__ == "__main__":
    unittest.main()
