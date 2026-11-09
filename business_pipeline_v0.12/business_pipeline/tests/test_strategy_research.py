"""The strategy and management frameworks route their research by dimension.

Generic Strategies, Porter's Diamond, the Value Chain, SWOT, Scenario
Planning, Strategic Groups and Activity-System fit each declare a research
block.  The block names the topic each dimension belongs to, the need it serves
and, where the dimension is externally evidenced, the tiers that make it
citable.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


STRATEGY = ("GENERIC_STRATEGIES", "PORTERS_DIAMOND", "VALUE_CHAIN", "SWOT",
            "SCENARIO", "STRATEGIC_GROUP", "ACTIVITY_SYSTEM")


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class StrategyResearchBlockTest(unittest.TestCase):
    def test_each_profile_declares_a_valid_research_block(self):
        for name in STRATEGY:
            profile = getattr(framework_profiles, name)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_swot_researches_only_the_external_dimensions(self):
        block = framework_profiles.get("template_swot")["research"]
        self.assertEqual(set(block["topics"]), {"O", "T"})
        self.assertFalse(block.get("required_tiers"))

    def test_the_value_chain_maps_each_activity_to_its_topic(self):
        topics = framework_profiles.get("template_value_chain")["research"]["topics"]
        self.assertEqual(topics["marketing_and_sales"], "marketing")
        self.assertEqual(topics["procurement"], "supply_chain")
        self.assertEqual(topics["technology_development"], "technology")
        self.assertEqual(topics["human_resource_management"], "people")
        self.assertEqual(topics["operations"], "operations")

    def test_porters_diamond_routes_government_to_law(self):
        topics = framework_profiles.get("template_porters_diamond")["research"]["topics"]
        self.assertEqual(topics["government"], "law")
        self.assertEqual(topics["factor_conditions"], "economics")
        self.assertEqual(topics["related_industries"], "industry")

    def test_the_externally_evidenced_dimensions_require_a_source_type(self):
        for name in ("GENERIC_STRATEGIES", "STRATEGIC_GROUP"):
            block = getattr(framework_profiles, name)["research"]
            self.assertTrue(block.get("required_tiers"), name)
            for tiers in block["required_tiers"].values():
                self.assertIn("official", tiers, name)


class StrategyRoutingTest(unittest.TestCase):
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

    def test_generic_strategies_routes_to_industry(self):
        self.assertEqual(
            self._topic_for("GENERIC_STRATEGIES", "low_cost", "cost low cost efficiency scale",
                            "Cost low cost efficiency scale"),
            "industry")

    def test_value_chain_marketing_routes_to_marketing(self):
        self.assertEqual(
            self._topic_for("VALUE_CHAIN", "marketing_and_sales", "marketing sales branding pricing channel",
                            "Marketing sales branding pricing channel"),
            "marketing")

    def test_porters_diamond_government_routes_to_law(self):
        self.assertEqual(
            self._topic_for("PORTERS_DIAMOND", "government", "government policy regulation subsidy",
                            "Government policy regulation subsidy"),
            "law")


if __name__ == "__main__":
    unittest.main()
