"""The quality frameworks route their research to operations.

Five-S, RCA, FMEA and PDCA are `auto` profiles: the worksheet is the student's
own, and a source is a supplement.  Their research block therefore routes to
the operations topic and names the methodology need, but requires no source
tier, so nothing the student wrote is graded away.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import framework_profiles, research_contract, retrieval  # noqa: E402


QUALITY = ("FIVE_S", "ROOT_CAUSE", "FMEA", "PDCA")


def _page(title, description, tier="news"):
    return {"title": title, "description": description, "tier": tier,
            "url": "https://example.org/x", "site": "Example", "year": 2024}


class QualityResearchBlockTest(unittest.TestCase):
    def test_each_quality_profile_declares_a_valid_research_block(self):
        for name in QUALITY:
            profile = getattr(framework_profiles, name)
            block = profile.get("research")
            self.assertIsInstance(block, dict, name)
            self.assertEqual(research_contract.validate_research(block), [], name)

    def test_each_block_routes_to_operations_and_names_methodology(self):
        for name in QUALITY:
            block = getattr(framework_profiles, name)["research"]
            self.assertTrue(block["topics"], name)
            self.assertEqual(set(block["topics"].values()), {"operations"}, name)
            for needs in block["needs"].values():
                self.assertEqual(needs, ["methodology"], name)

    def test_no_quality_block_requires_a_tier(self):
        for name in QUALITY:
            block = getattr(framework_profiles, name)["research"]
            self.assertFalse(block.get("required_tiers"), name)


class QualityRoutingTest(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.patch.object(retrieval, "_log_learning")
        self.log.start()
        self.addCleanup(self.log.stop)

    def test_a_quality_dimension_routes_to_operations(self):
        profile = framework_profiles.get("template_5s")
        with unittest.mock.patch.object(
                retrieval.source_finder, "search_academic",
                return_value={"results": [], "errors": [], "skipped": []}), \
             unittest.mock.patch.object(
                retrieval.source_finder, "search_web",
                return_value={"results": [_page("Workplace organisation and sorting",
                                                "workplace organisation sorting")]}) as web:
            found = retrieval.retrieve(
                key="sort", cues="sort remove unnecessary clutter",
                queries=["workplace organisation and sorting"], context=[],
                geography="Global",
                gate={"title_cue": False, "title_context": False, "require_geography": False},
                research=profile.get("research"), block_key="sort")
        self.assertEqual(web.call_args.kwargs.get("topic"), "operations")
        self.assertTrue(found["items"])


if __name__ == "__main__":
    unittest.main()
