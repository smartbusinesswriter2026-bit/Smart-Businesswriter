"""The business plan's four evidence blocks are researched by the same contract.

The plan is a profile, not a framework, so its research block lives beside its
dimensions in `chat.PLAN_RESEARCH`.  These tests pin the block, the routing of
each block to its topic, and the source-type grading the chat applies.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import chat, research_contract, retrieval  # noqa: E402


def _page(title, description, tier, url="https://example.org/x"):
    return {"title": title, "description": description, "tier": tier,
            "url": url, "site": "Example", "year": 2024}


class PlanResearchBlockTest(unittest.TestCase):
    def test_the_plan_research_block_is_valid(self):
        self.assertEqual(research_contract.validate_research(chat.PLAN_RESEARCH), [])

    def test_the_block_covers_the_four_evidence_blocks(self):
        self.assertEqual(set(chat.PLAN_RESEARCH["topics"]),
                         {"market", "customers", "competition", "regulation"})
        self.assertEqual(chat.PLAN_RESEARCH["budget"], 2)

    def test_the_topics_are_the_vetted_registry_keys(self):
        self.assertEqual(chat.PLAN_RESEARCH["topics"]["market"], "industry")
        self.assertEqual(chat.PLAN_RESEARCH["topics"]["customers"], "marketing")
        self.assertEqual(chat.PLAN_RESEARCH["topics"]["competition"], "industry")
        self.assertEqual(chat.PLAN_RESEARCH["topics"]["regulation"], "law")

    def test_the_needs_are_the_closed_vocabulary(self):
        for needs in chat.PLAN_RESEARCH["needs"].values():
            for need in needs:
                self.assertTrue(research_contract.is_need(need), need)

    def test_research_for_returns_the_plan_block_for_a_business_plan_profile(self):
        state = {"profile": "business_plan", "framework": None,
                 "selection": {"selected": []}}
        self.assertIs(chat._research_for(state), chat.PLAN_RESEARCH)


class PlanRoutingTest(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.patch.object(retrieval, "_log_learning")
        self.log.start()
        self.addCleanup(self.log.stop)

    def _run(self, block_key, cues, title):
        with unittest.mock.patch.object(
                retrieval.source_finder, "search_academic",
                return_value={"results": [], "errors": [], "skipped": []}), \
             unittest.mock.patch.object(
                retrieval.source_finder, "search_web",
                return_value={"results": [_page(title, title, "news")]}) as web:
            found = retrieval.retrieve(
                key=block_key, cues=cues, queries=[title], context=[],
                geography="Global",
                gate={"title_cue": False, "title_context": False, "require_geography": False},
                research=chat.PLAN_RESEARCH, block_key=block_key)
        return found, web

    def test_market_routes_to_industry(self):
        _found, web = self._run("market", "market size growth demand industry spending",
                                "Market size growth demand industry spending")
        self.assertEqual(web.call_args.kwargs.get("topic"), "industry")

    def test_regulation_routes_to_law(self):
        _found, web = self._run("regulation", "regulation policy licence compliance permits",
                                "Regulation policy licence compliance permits")
        self.assertEqual(web.call_args.kwargs.get("topic"), "law")

    def test_a_press_only_market_block_fails_the_source_type_rule(self):
        found, _web = self._run("market", "market size growth demand industry spending",
                                "Market size growth demand industry spending")
        verdict = research_contract.grade_dimension(
            found["items"], chat.PLAN_RESEARCH["required_tiers"]["market"])
        self.assertFalse(verdict["ok"])
        self.assertEqual(verdict["missing_tiers"], ["official", "data", "research"])


if __name__ == "__main__":
    unittest.main()
