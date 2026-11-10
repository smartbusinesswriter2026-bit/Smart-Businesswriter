"""Portfolio, growth and canvas writing: the guideline's shape for five modules.

Ansoff, ERRC and the three canvases are data.  This test builds one completion
per module with a sourced item and a proposed reading, then asserts the sections,
the summary table, the canvas grid and the assumption register.
"""

import re
import sys
import unittest

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, framework_writing, paper  # noqa: E402

TEMPLATES = ("template_ansoff", "template_blue_ocean_errc",
             "template_business_model_canvas", "template_lean_canvas",
             "template_value_proposition_canvas")


def norm(text):
    clean = re.sub(r"[^a-z0-9 ]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", clean).strip()


def a_completion(template):
    profile = framework_profiles.profile_for(template)
    writing = profile["writing"]
    scale = framework_writing.scale_for(writing)
    blocks = []
    for index, block in enumerate(profile["blocks"]):
        item = {
            "text": "The case states a position in the market.",
            "provenance": "sourced", "source": "Source %s (2024)." % chr(65 + index),
            "citation": "(Source, 2024)", "title": "Study %s" % chr(65 + index),
            "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
            "source_id": "S%d" % (index + 1),
        }
        drivers = [{"driver": "the stated factor", "evidence": 0, "type": "F"}]
        if index == 0:
            drivers.append({"driver": "buyers will switch", "evidence": None, "type": "H",
                            "test": "a pilot with twenty buyers"})
        reading = {
            "status": "proposed", "rating": scale[0],
            "rating_label": writing["rating_label"],
            "drivers": drivers, "trend": "Stable",
            "trend_reason": "The position is described at one point.",
            "profitability_impact": "The position shapes the margin the business can keep.",
            "confidence": "Medium",
            "confidence_reason": "One current study supports the reading.",
            "so_what": "The choice must be matched by the activity system.",
            "rationale": "The evidence describes a position in the market.",
            "contradictions": [],
        }
        blocks.append({"key": block["key"], "label": block["label"], "items": [item],
                       "gap": None, "fill": "research", "reading": reading})
    if template == "template_ansoff":
        unit = {"field": "firm", "value": "Kestrel Retail", "firm": "Kestrel Retail",
                "market": "grocery retail", "context": "Kestrel Retail grocery retail"}
    elif template == "template_blue_ocean_errc":
        unit = {"field": "firm", "value": "a subscription box", "firm": "a subscription box",
                "market": "grocery retail", "context": "a subscription box grocery retail"}
    else:
        unit = {"field": "business", "value": "a subscription grocery box",
                "context": "a subscription grocery box"}
    return {"format": "bp-framework-completion/1", "template": template,
            "framework": profile["label"], "unit": unit,
            "instruction": "Kestrel Retail is reviewing its position in grocery retail.",
            "country": "", "region": "Global", "blocks": blocks, "notes": []}


class PortfolioCanvasWritingTest(unittest.TestCase):
    def test_every_module_declares_a_writing_block_and_its_scale(self):
        for template in TEMPLATES:
            writing = framework_profiles.profile_for(template).get("writing") or {}
            self.assertTrue(writing, template)
            self.assertIn(writing["scale"], framework_writing.SCALES, template)
            self.assertTrue(writing["sections"], template)

    def test_each_draft_carries_the_guideline_headings(self):
        for template in TEMPLATES:
            profile = framework_profiles.profile_for(template)
            report = completion.draft(a_completion(template), version="draft")
            headings = [norm(section["heading"]) for section in report["sections"]]
            for part in profile["writing"]["sections"]:
                if part == "dimensions":
                    continue  # the part group; each block has its own heading
                head = profile["writing"]["section_heads"].get(part, part)
                self.assertIn(norm(head), headings, "%s: %s" % (template, head))
            self.assertIn("references", headings, template)

    def test_each_draft_prints_the_summary_table(self):
        for template in TEMPLATES:
            profile = framework_profiles.profile_for(template)
            report = completion.draft(a_completion(template), version="draft")
            summary = [section for section in report["sections"]
                       if norm(section["heading"]) ==
                       norm(profile["writing"]["section_heads"]["summary"])][0]
            self.assertEqual(summary["table"]["columns"],
                             profile["writing"]["summary_columns"], template)

    def test_the_register_lists_the_hypothesis_and_its_test(self):
        for template in TEMPLATES:
            profile = framework_profiles.profile_for(template)
            report = completion.draft(a_completion(template), version="draft")
            register = [section for section in report["sections"]
                        if norm(section["heading"]) ==
                        norm(profile["writing"]["section_heads"]["register"])][0]
            self.assertEqual(len(register["table"]["rows"]), 1, template)
            self.assertIn("a pilot with twenty buyers", register["table"]["rows"][0])

    def test_the_canvas_grid_reaches_the_paper(self):
        for template in ("template_business_model_canvas", "template_lean_canvas",
                         "template_value_proposition_canvas"):
            report = completion.draft(a_completion(template), version="draft")
            framework_section = [section for section in report["sections"]
                                 if section.get("figure")][0]
            self.assertEqual(framework_section["figure"]["kind"], "canvas", template)

    def test_each_draft_passes_the_structural_check(self):
        for template in TEMPLATES:
            report = completion.draft(a_completion(template), version="draft")
            issues = paper.check(report["sections"], framework=template,
                                 implications="The decision remains the student's.")
            self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [],
                             template)


if __name__ == "__main__":
    unittest.main()
