"""The project and operations frameworks route their research by dimension.

A project plan's evidence is its own record, so most project dimensions route to
`project` with a methodology need and require no tier.  Operations frameworks
route to operations or supply chain; the balanced scorecard and strategy map
split finance, marketing, operations and people; Strategic Positioning reads the
industry and requires an external source type.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


PROJECT_OPS = {
    "BALANCED_SCORECARD": "template_balanced_scorecard",
    "LESSONS_LEARNED": "template_lessons_learned",
    "OKRS": "template_okrs",
    "PROJECT_CHARTER": "template_project_charter",
    "RACI": "template_raci",
    "RISK_REGISTER": "template_risk_register",
    "STAKEHOLDER_PLAN": "template_stakeholder_plan",
    "STRATEGY_MAP": "template_strategy_map",
    "WBS": "template_wbs",
    "A3": "template_a3",
    "DMAIC": "template_dmaic",
    "KRALJIC": "template_kraljic",
    "PDSA": "template_pdsa",
    "SCOR": "template_scor",
    "SIPOC": "template_sipoc",
    "SALES_AND_OPERATIONS": "template_sop",
    "TOC": "template_toc",
    "STRATEGIC_POSITIONING": "template_strategic_positioning",
}


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class ProjectOpsResearchBlockTest(unittest.TestCase):
    def test_each_profile_declares_a_valid_research_block(self):
        for name, template in PROJECT_OPS.items():
            profile = framework_profiles.get(template)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_the_project_profiles_route_to_project(self):
        for name in ("LESSONS_LEARNED", "OKRS", "PROJECT_CHARTER", "RACI",
                     "RISK_REGISTER", "STAKEHOLDER_PLAN", "WBS"):
            block = framework_profiles.get(PROJECT_OPS[name])["research"]
            self.assertEqual(set(block["topics"].values()), {"project"}, name)

    def test_the_balanced_scorecard_and_strategy_map_split_their_topics(self):
        scorecard = framework_profiles.get(PROJECT_OPS["BALANCED_SCORECARD"])["research"]["topics"]
        strategy = framework_profiles.get(PROJECT_OPS["STRATEGY_MAP"])["research"]["topics"]
        self.assertEqual(scorecard["financial"], "finance")
        self.assertEqual(scorecard["customer"], "marketing")
        self.assertEqual(scorecard["internal_process"], "operations")
        self.assertEqual(scorecard["organisational_capacity"], "people")
        self.assertEqual(set(strategy.values()), {"management"})

    def test_the_operations_profiles_route_to_operations_or_supply_chain(self):
        for name in ("A3", "DMAIC", "PDSA", "SIPOC", "TOC"):
            block = framework_profiles.get(PROJECT_OPS[name])["research"]
            self.assertEqual(set(block["topics"].values()), {"operations"}, name)
        for name in ("KRALJIC", "SCOR"):
            block = framework_profiles.get(PROJECT_OPS[name])["research"]
            self.assertEqual(set(block["topics"].values()), {"supply_chain"}, name)

    def test_strategic_positioning_routes_to_industry_and_is_graded(self):
        block = framework_profiles.get(PROJECT_OPS["STRATEGIC_POSITIONING"])["research"]
        self.assertEqual(set(block["topics"].values()), {"industry"})
        self.assertTrue(block.get("required_tiers"))
        for tiers in block["required_tiers"].values():
            self.assertIn("official", tiers)

    def test_the_project_and_operations_profiles_require_no_tier(self):
        for name in ("LESSONS_LEARNED", "OKRS", "PROJECT_CHARTER", "RACI",
                     "RISK_REGISTER", "STAKEHOLDER_PLAN", "WBS", "A3", "DMAIC",
                     "KRALJIC", "PDSA", "SCOR", "SIPOC", "SALES_AND_OPERATIONS", "TOC"):
            block = framework_profiles.get(PROJECT_OPS[name])["research"]
            self.assertFalse(block.get("required_tiers"), name)

    def test_the_default_need_is_methodology(self):
        block = framework_profiles.get(PROJECT_OPS["WBS"])["research"]
        for needs in block["needs"].values():
            self.assertEqual(needs, ["methodology"])


class ProjectOpsRoutingTest(unittest.TestCase):
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

    def test_wbs_routes_to_project(self):
        self.assertEqual(
            self._topic_for("template_wbs", "deliverables", "deliverable work package",
                            "Deliverable work package"),
            "project")

    def test_a3_routes_to_operations(self):
        self.assertEqual(
            self._topic_for("template_a3", "problem", "problem defect delay",
                            "Problem defect delay"),
            "operations")

    def test_kraljic_routes_to_supply_chain(self):
        self.assertEqual(
            self._topic_for("template_kraljic", "criteria", "supply risk profit impact",
                            "Supply risk profit impact"),
            "supply_chain")

    def test_strategic_positioning_routes_to_industry(self):
        self.assertEqual(
            self._topic_for("template_strategic_positioning", "position",
                            "position strategy choice differentiation",
                            "Position strategy choice differentiation"),
            "industry")


if __name__ == "__main__":
    unittest.main()
