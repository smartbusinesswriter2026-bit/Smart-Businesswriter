"""Acceptance net for the marketing shelf's completion profiles — the alignment trap (D-MKT-01).

The shelf's sixteen completion profiles were re-tested in session 6 and every failure was a
stale expectation, not a product defect: the profile, `templates.CANVAS_BLOCKS`/`MATRIX_META`
and the paper all agreed, and only the tests still named the older, shorter frameworks.  This
file is the net under that repair: it asserts the agreement directly, so a profile that grows
(or is renamed) cannot leave a test, a form or a prompt behind again.

Run:  PYTHONPATH=src python -m pytest tests/test_subject_marketing_acceptance.py -q
"""

import os
import sys
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import templates                                        # noqa: E402
from bp.product import completion, framework_profiles, subjects  # noqa: E402

TEMPLATES = {
    "template_aida": "aida", "template_attribution": "attribution",
    "template_brand_equity": "brand_equity", "template_cro": "cro",
    "template_customer_journey": "customer_journey", "template_digital_mix": "digital_mix",
    "template_email_crm": "email_crm", "template_funnel": "funnel", "template_kano": "kano",
    "template_marketing_automation": "marketing_automation",
    "template_marketing_plan": "marketing_plan", "template_measurement_plan": "measurement_plan",
    "template_paid_media_plan": "paid_media_plan", "template_rfm": "rfm",
    "template_seo_content": "seo_content", "template_servqual": "servqual",
    "template_social_media": "social_media", "template_stp": "stp",
    "template_stp_evidence": "stp_evidence", "template_tam": "tam", "template_utaut": "utaut",
}
BRIEF = ("A supermarket chain is reviewing its marketing plan for a new breakfast range before deciding "
         "whether to launch it nationally.")
INDUSTRY = "grocery retail"


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": INDUSTRY + " " + query[:70],
        "abstract": "Evidence on the element named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Marketing", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(template):
    profile = framework_profiles.PROFILES[template]
    kwargs = {}
    field = (profile.get("unit") or {}).get("field")
    if field == "industry":
        kwargs["industry"] = INDUSTRY
    else:
        kwargs["unit_value"] = "the breakfast range"
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, BRIEF, **kwargs)


class MarketingProfileAlignmentTest(unittest.TestCase):
    """D-MKT-01: one declaration, and the product, the form and the prompt all read it."""

    def test_E_mkt_001__every_profile_declares_the_blocks_its_form_declares(self):
        for template in TEMPLATES:
            profile = framework_profiles.PROFILES[template]
            if template in templates.MATRIX_META and template not in templates.CANVAS_BLOCKS:
                # A grid names its own axes: the profile's blocks are the framework's
                # dimensions (the paper's sections), while the worksheet's rows and
                # columns are the student's.  They are different by design, so what the
                # form must declare here is its two axis labels.
                meta = templates.MATRIX_META[template]
                self.assertTrue(meta.get("row_label"), template)
                self.assertTrue(meta.get("column_label"), template)
                continue
            form = templates.CANVAS_BLOCKS.get(template) or templates.MATRIX_META.get(template) or {}
            self.assertTrue(form, template)
            self.assertEqual(sorted(block["key"] for block in profile["blocks"]), sorted(form),
                             "%s: profile and form disagree" % template)

    def test_E_mkt_002__every_completion_returns_exactly_the_declared_blocks(self):
        for template in TEMPLATES:
            result = complete(template)
            self.assertEqual([block["key"] for block in result["blocks"]],
                             [block["key"] for block in
                              framework_profiles.PROFILES[template]["blocks"]], template)
            self.assertEqual(result["framework"], framework_profiles.PROFILES[template]["label"],
                             template)

    def test_E_mkt_003__every_prompt_names_the_profile_label_and_the_unit(self):
        for template in TEMPLATES:
            profile = framework_profiles.PROFILES[template]
            system = completion._system(completion.HEAD_SYSTEM, dict(completion.LENGTHS["mid"]), profile)
            self.assertIn(profile["label"], system, template)
            field = (profile.get("unit") or {}).get("field")
            if field == "industry":
                self.assertIn("industry", system.lower(), template)

    def test_E_mkt_004__every_shelf_worksheet_resolves_to_a_profile(self):
        page = subjects.detail("marketing")
        # Twenty: the fifteen worksheets that D-PLAN-02 held dark are wired now, and the
        # five that were always offered are still first.  The SERVQUAL gap grid (MKT-07)
        # is the one that stays hidden - its form is repaired (D-MKT-07) but its tile is
        # still hidden by the owner's B-198, so it is carried as a record.  Its template,
        # record and completion profile are untouched, so the framework still runs
        # through the conductor.
        self.assertEqual(len(page["worksheets"]), 20)
        self.assertNotIn("MKT-07", [sheet["catalogue_id"] for sheet in page["worksheets"]])
        for sheet in page["worksheets"]:
            self.assertIn(sheet["template"], framework_profiles.PROFILES, sheet["catalogue_id"])

    def test_E_mkt_005__this_file_covers_every_marketing_profile_the_tests_name(self):
        named = sorted(TEMPLATES)
        marketing = sorted(template for template in framework_profiles.PROFILES
                           if framework_profiles.PROFILES[template].get("subject") == "marketing")
        self.assertEqual(named, marketing,
                         "a marketing profile exists that this net does not cover")


if __name__ == "__main__":
    unittest.main()
