"""The leadership, culture and ethics frameworks route their researched parts.

These profiles are mostly the student's own argument (`quote`/`gap`).  Only the
`auto` blocks and the logic-model / theory-of-change rows are researched, so the
research block lists exactly those dimensions and the quote-only profiles are
left without a block.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


RESEARCHED = {
    "change_organization": "template_change_organization",
    "cross_cultural_leadership": "template_cross_cultural_leadership",
    "culture_framework_comparison": "template_culture_framework_comparison",
    "ethical_dilemma": "template_ethical_dilemma",
    "leadership_theory_comparison": "template_leadership_theory_comparison",
    "logic_model": "template_logic_model",
    "situational_leadership": "template_situational_leadership",
    "stakeholder_csr": "template_stakeholder_csr",
    "theory_of_change": "template_theory_of_change",
}

QUOTE_ONLY = ("ethical_decision_process", "leader_effectiveness",
              "leadership_development", "organisational_culture")


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class LeadershipResearchBlockTest(unittest.TestCase):
    def test_each_researched_profile_declares_a_valid_block(self):
        for name, template in RESEARCHED.items():
            profile = framework_profiles.get(template)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_change_and_logic_models_route_to_people(self):
        for name in ("change_organization", "logic_model", "theory_of_change",
                     "leadership_theory_comparison", "situational_leadership"):
            block = framework_profiles.profile_for(name)["research"]
            self.assertEqual(set(block["topics"].values()), {"people"}, name)

    def test_culture_profiles_route_to_culture(self):
        for name in ("cross_cultural_leadership", "culture_framework_comparison"):
            block = framework_profiles.profile_for(name)["research"]
            self.assertEqual(set(block["topics"].values()), {"culture"}, name)

    def test_ethics_profiles_route_to_ethics(self):
        for name in ("ethical_dilemma", "stakeholder_csr"):
            block = framework_profiles.profile_for(name)["research"]
            self.assertEqual(set(block["topics"].values()), {"ethics"}, name)

    def test_no_leadership_profile_requires_a_tier(self):
        for name in RESEARCHED:
            block = framework_profiles.profile_for(name)["research"]
            self.assertFalse(block.get("required_tiers"), name)

    def test_the_quote_only_profiles_have_no_research_block(self):
        for name in QUOTE_ONLY:
            profile = framework_profiles.profile_for(name)
            self.assertFalse(profile.get("research"), name)


class LeadershipRoutingTest(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.patch.object(retrieval, "_log_learning")
        self.log.start()
        self.addCleanup(self.log.stop)

    def _topic_for(self, key, block_key, cues, title):
        profile = framework_profiles.profile_for(key)
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

    def test_ethical_dilemma_theory_routes_to_ethics(self):
        self.assertEqual(
            self._topic_for("ethical_dilemma", "theory_a",
                            "utilitarian deontology virtue ethics",
                            "Utilitarian deontology virtue ethics"),
            "ethics")

    def test_cross_cultural_framework_routes_to_culture(self):
        self.assertEqual(
            self._topic_for("cross_cultural_leadership", "framework",
                            "cross-cultural leadership culture dimension",
                            "Cross-cultural leadership culture dimension"),
            "culture")

    def test_logic_model_routes_to_people(self):
        self.assertEqual(
            self._topic_for("logic_model", "inputs", "input resource activity",
                            "Input resource activity"),
            "people")


if __name__ == "__main__":
    unittest.main()
