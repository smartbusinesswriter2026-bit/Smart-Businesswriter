"""The people and change frameworks route their research to the people registry.

These are organisation frameworks: the evidence is usually the student's own
organisation, so the block routes each dimension to the people topic and names
the methodology need, but requires no source tier.  A few dimensions read the
wider environment and are routed to economics, management, operations or culture.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


PEOPLE = {
    "ADKAR": "template_adkar",
    "KOTTER": "template_kotter",
    "LEWIN": "template_lewin",
    "TUCKMAN": "template_tuckman",
    "AMO": "template_amo",
    "BURKE_LITWIN": "template_burke_litwin",
    "COMPETING_VALUES": "template_competing_values",
    "JOB_CHARACTERISTICS": "template_job_characteristics",
    "KIRKPATRICK": "template_kirkpatrick",
    "NINE_BOX": "template_nine_box",
    "ORG_DESIGN": "template_org_design",
    "MCKINSEY_7S": "template_mckinsey_7s",
    "GALBRAITH_STAR": "template_galbraith_star",
    "MINTZBERG": "template_mintzberg",
}


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class PeopleResearchBlockTest(unittest.TestCase):
    def test_each_people_profile_declares_a_valid_research_block(self):
        for name, template in PEOPLE.items():
            profile = framework_profiles.get(template)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_the_uniform_profiles_route_to_people(self):
        for name in ("ADKAR", "KOTTER", "LEWIN", "TUCKMAN", "AMO",
                     "COMPETING_VALUES", "JOB_CHARACTERISTICS", "KIRKPATRICK",
                     "NINE_BOX"):
            block = framework_profiles.get(PEOPLE[name])["research"]
            self.assertEqual(set(block["topics"].values()), {"people"}, name)

    def test_burke_litwin_reads_the_wider_environment(self):
        topics = framework_profiles.get(PEOPLE["BURKE_LITWIN"])["research"]["topics"]
        self.assertEqual(topics["external_environment"], "economics")
        self.assertEqual(topics["mission_strategy"], "management")
        self.assertEqual(topics["task_requirements"], "operations")
        self.assertEqual(topics["individual_values"], "culture")
        self.assertEqual(topics["leadership"], "people")

    def test_org_design_and_galbraith_split_management_and_operations(self):
        org = framework_profiles.get(PEOPLE["ORG_DESIGN"])["research"]["topics"]
        star = framework_profiles.get(PEOPLE["GALBRAITH_STAR"])["research"]["topics"]
        self.assertEqual(org["strategy"], "management")
        self.assertEqual(org["processes"], "operations")
        self.assertEqual(star["strategy"], "management")
        self.assertEqual(star["processes"], "operations")

    def test_mckinsey_splits_management_from_people(self):
        topics = framework_profiles.get(PEOPLE["MCKINSEY_7S"])["research"]["topics"]
        self.assertEqual(topics["strategy"], "management")
        self.assertEqual(topics["systems"], "management")
        self.assertEqual(topics["skills"], "people")

    def test_mintzberg_routes_to_management(self):
        block = framework_profiles.get(PEOPLE["MINTZBERG"])["research"]
        self.assertEqual(set(block["topics"].values()), {"management"})

    def test_no_people_profile_requires_a_tier(self):
        for name, template in PEOPLE.items():
            block = framework_profiles.get(template)["research"]
            self.assertFalse(block.get("required_tiers"), name)

    def test_the_default_need_is_methodology(self):
        block = framework_profiles.get(PEOPLE["ADKAR"])["research"]
        for needs in block["needs"].values():
            self.assertEqual(needs, ["methodology"])


class PeopleRoutingTest(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.patch.object(retrieval, "_log_learning")
        self.log.start()
        self.addCleanup(self.log.stop)

    def _topic_for(self, template, block_key, cues, title):
        profile = framework_profiles.get(template)
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

    def test_adkar_routes_to_people(self):
        self.assertEqual(
            self._topic_for("template_adkar", "awareness", "awareness change communication",
                            "Awareness change communication"),
            "people")

    def test_burke_external_environment_routes_to_economics(self):
        self.assertEqual(
            self._topic_for("template_burke_litwin", "external_environment",
                            "external environment economy policy",
                            "External environment economy policy"),
            "economics")

    def test_mckinsey_strategy_routes_to_management(self):
        self.assertEqual(
            self._topic_for("template_mckinsey_7s", "strategy", "strategy aim goal",
                            "Strategy aim goal"),
            "management")

    def test_mintzberg_routes_to_management(self):
        self.assertEqual(
            self._topic_for("template_mintzberg", "strategic_apex", "strategic apex leadership",
                            "Strategic apex leadership"),
            "management")


if __name__ == "__main__":
    unittest.main()
