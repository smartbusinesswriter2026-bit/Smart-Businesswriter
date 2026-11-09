"""The marketing frameworks route their research to the marketing registry.

Twenty-two marketing profiles share one research table attached after the
profile literals: most dimensions route to `marketing` and name the customer
need; positioning is competitive, price is a cost, TAM/UTAUT are technology
adoption, the measurement plan is research and the KPI tree is project work.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


MARKETING = {
    "STP": "template_stp",
    "STP_EVIDENCE": "template_stp_evidence",
    "AIDA": "template_aida",
    "CUSTOMER_JOURNEY": "template_customer_journey",
    "FUNNEL": "template_funnel",
    "SERVQUAL": "template_servqual",
    "RFM": "template_rfm",
    "TAM": "template_tam",
    "UTAUT": "template_utaut",
    "BRAND_EQUITY": "template_brand_equity",
    "DIGITAL_MIX": "template_digital_mix",
    "SEO_CONTENT": "template_seo_content",
    "EMAIL_CRM": "template_email_crm",
    "SOCIAL_MEDIA": "template_social_media",
    "ATTRIBUTION": "template_attribution",
    "CRO": "template_cro",
    "MARKETING_AUTOMATION": "template_marketing_automation",
    "KANO": "template_kano",
    "PAID_MEDIA_PLAN": "template_paid_media_plan",
    "MEASUREMENT_PLAN": "template_measurement_plan",
    "MARKETING_PLAN": "template_marketing_plan",
    "KPI_TREE": "template_kpi_tree",
}


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class MarketingResearchBlockTest(unittest.TestCase):
    def test_each_marketing_profile_declares_a_valid_research_block(self):
        for name, template in MARKETING.items():
            profile = framework_profiles.get(template)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_most_dimensions_route_to_marketing(self):
        for name in ("STP", "AIDA", "CUSTOMER_JOURNEY", "FUNNEL", "SERVQUAL",
                     "RFM", "BRAND_EQUITY", "DIGITAL_MIX", "SEO_CONTENT",
                     "EMAIL_CRM", "SOCIAL_MEDIA", "ATTRIBUTION", "PAID_MEDIA_PLAN",
                     "MARKETING_PLAN"):
            block = framework_profiles.get(MARKETING[name])["research"]
            self.assertEqual(set(block["topics"].values()), {"marketing"}, name)

    def test_tam_and_utaut_route_to_technology(self):
        for name in ("TAM", "UTAUT"):
            block = framework_profiles.get(MARKETING[name])["research"]
            self.assertEqual(set(block["topics"].values()), {"technology"}, name)

    def test_the_measurement_plan_routes_to_research_and_the_kpi_tree_to_project(self):
        measurement = framework_profiles.get(MARKETING["MEASUREMENT_PLAN"])["research"]
        kpi = framework_profiles.get(MARKETING["KPI_TREE"])["research"]
        self.assertEqual(set(measurement["topics"].values()), {"research"})
        self.assertEqual(set(kpi["topics"].values()), {"project"})

    def test_positioning_is_competitive_and_price_is_a_cost(self):
        block = framework_profiles.get(MARKETING["MARKETING_PLAN"])["research"]
        self.assertEqual(block["needs"]["positioning"], ["competitor"])
        self.assertEqual(block["needs"]["price"], ["cost_price"])

    def test_the_analysis_only_profiles_require_no_tier(self):
        for name in ("CRO", "MARKETING_AUTOMATION", "KANO", "MEASUREMENT_PLAN", "KPI_TREE"):
            block = framework_profiles.get(MARKETING[name])["research"]
            self.assertFalse(block.get("required_tiers"), name)

    def test_the_evidence_profiles_require_a_source_type(self):
        for name in ("STP", "AIDA", "CUSTOMER_JOURNEY", "PAID_MEDIA_PLAN", "MARKETING_PLAN"):
            block = framework_profiles.get(MARKETING[name])["research"]
            self.assertTrue(block.get("required_tiers"), name)
            for tiers in block["required_tiers"].values():
                self.assertIn("official", tiers, name)


class MarketingRoutingTest(unittest.TestCase):
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

    def test_stp_positioning_routes_to_marketing(self):
        self.assertEqual(
            self._topic_for("template_stp", "positioning", "positioning brand competitive",
                            "Positioning brand competitive"),
            "marketing")

    def test_tam_routes_to_technology(self):
        self.assertEqual(
            self._topic_for("template_tam", "perceived_usefulness",
                            "usefulness technology adoption", "Usefulness technology adoption"),
            "technology")

    def test_kpi_tree_routes_to_project(self):
        self.assertEqual(
            self._topic_for("template_kpi_tree", "outcome", "outcome metric project",
                            "Outcome metric project"),
            "project")


if __name__ == "__main__":
    unittest.main()
