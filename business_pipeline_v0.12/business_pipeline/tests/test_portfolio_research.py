"""The portfolio and canvas frameworks route their research to their topic.

Ansoff, BCG, GE-McKinsey, ERRC, the Business Model Canvas, the Lean Canvas and
the Value Proposition Canvas all retrieve evidence.  Their research blocks route
each block to the vetted registry; BCG and GE require industry data or research,
while the canvases require no tier because the canvas is a design artefact and
its cells are the student's.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


PORTFOLIO = ("ANSOFF", "BCG", "GE_MCKINSEY", "ERRC",
             "BMC", "LEAN_CANVAS", "VALUE_PROPOSITION_CANVAS")


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class PortfolioResearchBlockTest(unittest.TestCase):
    def test_each_profile_declares_a_valid_research_block(self):
        for name in PORTFOLIO:
            profile = getattr(framework_profiles, name)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_the_topics_are_the_expected_registry_keys(self):
        expected = {
            "ANSOFF": "industry", "BCG": "industry", "GE_MCKINSEY": "industry",
            "ERRC": "industry", "BMC": "management", "LEAN_CANVAS": "entrepreneurship",
            "VALUE_PROPOSITION_CANVAS": "marketing",
        }
        for name, topic in expected.items():
            block = getattr(framework_profiles, name)["research"]
            self.assertEqual(set(block["topics"].values()), {topic}, name)

    def test_bcg_and_ge_require_industry_data_or_research(self):
        for name in ("BCG", "GE_MCKINSEY"):
            block = getattr(framework_profiles, name)["research"]
            for tiers in block["required_tiers"].values():
                self.assertEqual(tiers, ["data", "research"], name)

    def test_the_canvases_require_no_tier(self):
        for name in ("BMC", "LEAN_CANVAS", "VALUE_PROPOSITION_CANVAS"):
            block = getattr(framework_profiles, name)["research"]
            self.assertFalse(block.get("required_tiers"), name)


class PortfolioRoutingTest(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.patch.object(retrieval, "_log_learning")
        self.log.start()
        self.addCleanup(self.log.stop)

    def _topic_for(self, profile_name, block_key, cues, title):
        profile = getattr(framework_profiles, profile_name)
        with unittest.mock.patch.object(
                retrieval.source_finder, "search_academic",
                return_value={"results": [], "errors": [], "skipped": []}), \
             unittest.mock.patch.object(
                retrieval.source_finder, "search_web",
                return_value={"results": [_page(title, title)]}) as web:
            retrieval.retrieve(
                key=block_key, cues=cues, queries=[title], context=[],
                geography="Global",
                gate={"title_cue": False, "title_context": False, "require_geography": False},
                research=profile.get("research"), block_key=block_key)
        return web.call_args.kwargs.get("topic")

    def test_bcg_routes_to_industry(self):
        self.assertEqual(
            self._topic_for("BCG", "stars", "star high growth high share invest",
                            "Star high growth high share invest"),
            "industry")

    def test_the_business_model_canvas_routes_to_management(self):
        self.assertEqual(
            self._topic_for("BMC", "customer_segments", "customer segments market",
                            "Customer segments market"),
            "management")

    def test_the_value_proposition_canvas_routes_to_marketing(self):
        self.assertEqual(
            self._topic_for("VALUE_PROPOSITION_CANVAS", "customer_jobs",
                            "customer jobs task need", "Customer jobs task need"),
            "marketing")


if __name__ == "__main__":
    unittest.main()
