"""The framework engine coexists with every worksheet, and a replaced one keeps its door.

This is the integration contract:
- every profile that declares a writing module has a coherent one;
- every declared section actually reaches the paper;
- every profile without a writing module keeps the old outline unchanged;
- every subject worksheet template and every matrix layout resolves to a profile;
- a worksheet that stayed in the subject list keeps its template key.
"""

import re
import sys
import unittest

sys.path.insert(0, "src")

from bp.product import (completion, framework_figures, framework_profiles, framework_writing,
                        matrix, paper, subjects)  # noqa: E402

WRITING = ("template_five_forces", "template_generic_strategies", "template_porters_diamond",
           "template_ansoff", "template_bcg", "template_ge_mckinsey",
           "template_blue_ocean_errc", "template_business_model_canvas",
           "template_lean_canvas", "template_value_proposition_canvas",
           "template_root_cause", "template_fmea", "template_pdca", "template_5s")

#: Every profile that does NOT declare a writing module.  The coexistence guard
#: is exhaustive: a new profile cannot quietly gain a module heading.
CLASSIC = tuple(profile["template"] for profile in framework_profiles.PROFILES.values()
                if not profile.get("writing"))

MODULE_HEADINGS = ("Evidence Audit", "Framework Chart", "Calculation Table",
                   "Required Checks", "Assumption Register", "RPN Calculation",
                   "Score Calculation")


def norm(text):
    clean = re.sub(r"[^a-z0-9 ]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", clean).strip()


def a_unit(profile):
    field = (profile.get("unit") or {}).get("field")
    if field == "industry":
        return {"field": "industry", "value": "grocery retail", "context": "grocery retail"}
    if field == "firm":
        return {"field": "firm", "value": "Kestrel Retail", "firm": "Kestrel Retail",
                "market": "grocery retail", "context": "Kestrel Retail grocery retail"}
    if field == "country_industry":
        return {"field": field, "value": "Germany: grocery retail", "country": "Germany",
                "industry": "grocery retail", "context": "Germany grocery retail"}
    if field == "business":
        return {"field": field, "value": "Kestrel Retail group",
                "context": "Kestrel Retail group"}
    if field == "country":
        return {"field": field, "value": "Germany", "country": "Germany", "context": "Germany"}
    return {"field": "process", "value": "the lunch service", "context": "the lunch service"}


def a_completion(template):
    profile = framework_profiles.profile_for(template)
    writing = profile.get("writing") or {}
    scale = framework_writing.scale_for(writing)
    blocks = []
    for index, block in enumerate(profile["blocks"]):
        item = {"text": "The record states an observation.", "provenance": "sourced",
                "source": "Source %s (2024)." % chr(65 + index),
                "citation": "(Source, 2024)", "title": "Record %s" % chr(65 + index),
                "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
                "source_id": "S%d" % (index + 1)}
        reading = {"status": "proposed", "rating": scale[0],
                   "rating_label": writing.get("rating_label") or "Rating",
                   "drivers": [{"driver": "the stated observation", "evidence": 0, "type": "F"}],
                   "trend": "Stable", "trend_reason": "One observation.",
                   "profitability_impact": "The finding shapes the action.",
                   "confidence": "Medium", "confidence_reason": "One record.",
                   "so_what": "The action follows the finding.",
                   "rationale": "The record states the observation.", "contradictions": []}
        blocks.append({"key": block["key"], "label": block["label"], "items": [item],
                       "gap": None, "fill": "research", "reading": reading})
    result = {"format": "bp-framework-completion/1", "template": template,
              "framework": profile["label"], "unit": a_unit(profile),
              "instruction": "The case is being reviewed.", "country": "", "region": "Global",
              "blocks": blocks, "notes": []}
    if "tables" in writing.get("sections", []):
        result["tables"] = [{"heading": "Worksheet", "columns": ["Item", "Value"],
                             "rows": [["A", "B"]]}]
    if "chart" in writing.get("sections", []):
        kind = writing.get("chart") or "bar"
        if kind == "tree":
            result["chart"] = {"kind": "tree", "title": "Why chain",
                               "root": "Seal leaks", "children": ["Worn tool", "Wrong torque"]}
        elif kind == "pareto":
            result["chart"] = {"kind": "pareto", "title": "RPN by failure mode",
                               "points": [{"label": "Seal leaks", "value": "84",
                                           "cumulative": "84"},
                                          {"label": "Wrong part", "value": "48",
                                           "cumulative": "132"}]}
        else:
            result["chart"] = {"kind": kind, "title": "Score by S",
                               "points": [{"label": "One", "value": "3"},
                                          {"label": "Two", "value": "2"}]}
    if template in ("template_bcg", "template_ge_mckinsey"):
        result["calculation"] = {"columns": ["Unit", "A"], "rows": [["Fresh", "4.00"],
                                                                   ["Home", "2.00"]]}
    return result


def headings(report):
    return [section["heading"] for section in report["sections"]]


class WritingModuleCoherenceTest(unittest.TestCase):
    def test_every_writing_module_has_a_coherent_declaration(self):
        handled = {"scope", "outcome", "summary", "dimensions", "synthesis", "forward",
                   "coherence", "stuck", "assessment", "fit", "risks", "hypotheses",
                   "implications", "limitations", "conclusion", "audit", "register",
                   "tables", "chart", "calculation", "metrics"}
        for template in WRITING:
            writing = framework_profiles.profile_for(template).get("writing") or {}
            self.assertTrue(writing, template)
            self.assertIn(writing.get("scale"), framework_writing.SCALES, template)
            for part in writing.get("sections") or []:
                self.assertIn(part, handled, (template, part))
            if "chart" in writing.get("sections", []):
                caption = writing.get("chart_caption") or ""
                self.assertTrue(caption, template)
                self.assertFalse(any(char.isdigit() for char in caption), template)
                self.assertIn(writing.get("chart"), framework_figures.CHART_KINDS, template)
            for part in ("limitations", "conclusion"):
                self.assertIn(part, writing.get("sections") or [], template)

    def test_each_declared_section_reaches_the_paper(self):
        for template in WRITING:
            profile = framework_profiles.profile_for(template)
            writing = profile["writing"]
            report = completion.draft(a_completion(template), version="draft")
            seen = [norm(heading) for heading in headings(report)]
            for part in writing["sections"]:
                if part == "dimensions":
                    continue
                if part == "tables":
                    # A table carries its own heading; the group label is not a
                    # printed heading.
                    for entry in a_completion(template).get("tables") or []:
                        self.assertIn(norm(entry["heading"]), seen, template)
                    continue
                head = ((writing.get("section_heads") or {}).get(part)
                        or writing.get(part + "_heading")
                        or (profile.get("outline") or {}).get(part))
                self.assertIsNotNone(head, (template, part))
                self.assertIn(norm(head), seen, (template, part))
            issues = paper.check(report["sections"], framework=template,
                                 implications="The decision remains the student's.")
            self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [],
                             template)


class ClassicWorksheetTest(unittest.TestCase):
    def test_a_profile_without_writing_keeps_the_old_outline(self):
        for template in CLASSIC:
            profile = framework_profiles.profile_for(template)
            self.assertFalse(profile.get("writing"), template)
            result = {"template": template, "instruction": "The case is being reviewed.",
                      "unit": a_unit(profile),
                      "blocks": [{"key": block["key"], "label": block["label"],
                                  "items": [{"text": "A statement.", "provenance": "student",
                                             "source": ""}]}
                                 for block in profile["blocks"]]}
            report = completion.draft(result, version="draft")
            seen = [norm(heading) for heading in headings(report)]
            self.assertIn(norm(profile["outline"]["framework"]), seen, template)
            for forbidden in MODULE_HEADINGS:
                self.assertNotIn(norm(forbidden), seen, "%s gained %s" % (template, forbidden))

    def test_a_worksheet_that_stayed_keeps_its_template_key(self):
        # The quality shelf replaced the hand-filled 5S/RCA/FMEA/PDCA papers with
        # the writing modules, but the subject door and its template key are the
        # same, so an old link or a saved case still resolves.
        for _key, sheet in subjects.WORKSHEETS.items():
            template = sheet.get("template")
            if not template:
                continue
            self.assertTrue(framework_profiles.has(template), (sheet.get("catalogue_id"), template))


class OfflineSuiteTest(unittest.TestCase):
    def test_the_suite_never_writes_the_learning_log(self):
        from bp.product import retrieval
        self.assertFalse(retrieval.LEARNING_LOG_ENABLED,
                         "a test run must not call the live corpus learning log")


class CatalogueCoexistenceTest(unittest.TestCase):
    def test_every_subject_worksheet_template_has_a_profile(self):
        for _key, sheet in subjects.WORKSHEETS.items():
            template = sheet.get("template")
            if template:
                self.assertTrue(framework_profiles.has(template), (sheet.get("catalogue_id"), template))

    def test_every_matrix_layout_has_a_profile(self):
        for template in matrix.LAYOUTS:
            self.assertTrue(framework_profiles.has(template), template)

    def test_no_profile_has_a_duplicate_template_or_block_key(self):
        templates = [profile["template"] for profile in framework_profiles.PROFILES.values()]
        self.assertEqual(len(templates), len(set(templates)))
        for profile in framework_profiles.PROFILES.values():
            keys = [block["key"] for block in profile["blocks"]]
            self.assertEqual(len(keys), len(set(keys)), profile["template"])


if __name__ == "__main__":
    unittest.main()
