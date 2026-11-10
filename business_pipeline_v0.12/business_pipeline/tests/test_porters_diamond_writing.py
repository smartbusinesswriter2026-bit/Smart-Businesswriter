"""Porter's Diamond writing module: outcome, conditions, interactions and audit.

The unit is the nation or region and its industry; the reading is a condition
(Advantage/Neutral/Disadvantage).  The audit is Module 3: outcome evidence,
determinant coverage, causal link, industry specificity, counter-evidence and
recency, with an explanatory-hypothesis verdict when the outcome is not evidenced.
"""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, framework_writing, paper  # noqa: E402

LABELS = {
    "factor_conditions": "Factor Conditions",
    "demand_conditions": "Demand Conditions",
    "related_industries": "Related and Supporting Industries",
    "firm_strategy": "Firm Strategy, Structure and Rivalry",
    "government": "Government",
    "chance": "Chance",
}

CONDITIONS = {"factor_conditions": "Advantage", "demand_conditions": "Advantage",
              "related_industries": "Neutral", "firm_strategy": "Advantage",
              "government": "Neutral"}


def profile():
    return framework_profiles.profile_for("template_porters_diamond")


def a_completion():
    blocks = []
    for index, key in enumerate(["factor_conditions", "demand_conditions",
                                 "related_industries", "firm_strategy", "government",
                                 "chance"]):
        item = {
            "text": "The industry in Germany competes on a distinct capability.",
            "provenance": "sourced", "source": "Source %s (2024)." % chr(65 + index),
            "citation": "(Source, 2024)", "title": "Study %s" % chr(65 + index),
            "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
            "source_id": "S%d" % (index + 1),
        }
        block = {"key": key, "label": LABELS[key], "items": [item], "gap": None,
                 "fill": "research"}
        if key in CONDITIONS:
            block["reading"] = {
                "status": "proposed", "rating": CONDITIONS[key], "rating_label": "Condition",
                "drivers": [{"driver": "skilled labour", "evidence": 0, "type": "F",
                             "area": "factor", "bias": "not classified",
                             "causal": "Plausible"}],
                "trend": "Stable", "trend_reason": "The condition is described at one point.",
                "profitability_impact": "The condition shapes the cost of competing.",
                "confidence": "Medium",
                "confidence_reason": "One current study supports the reading.",
                "so_what": "The determinant shapes the industry's competitive position.",
                "rationale": "The evidence describes a condition in the industry.",
            }
        blocks.append(block)
    return {"format": "bp-framework-completion/1",
            "template": "template_porters_diamond", "framework": "Porters Diamond",
            "unit": {"field": "country_industry", "value": "Germany: grocery retail",
                     "country": "Germany", "industry": "grocery retail",
                     "region": "Europe", "context": "Germany grocery retail"},
            "instruction": "Kestrel Retail is reviewing its grocery retail position in Germany.",
            "country": "Germany", "region": "Europe", "blocks": blocks, "notes": []}


class PortersDiamondWritingTest(unittest.TestCase):
    def test_the_profile_declares_the_module3_sections(self):
        writing = profile().get("writing") or {}
        self.assertEqual(writing.get("module"), "porters_diamond")
        for part in ("scope", "outcome", "summary", "dimensions", "synthesis",
                     "assessment", "implications", "audit"):
            self.assertIn(part, writing.get("sections") or [])
        self.assertEqual(writing.get("scale"), "condition")
        self.assertEqual(writing.get("rating_label"), "Condition")

    def test_the_summary_table_uses_condition(self):
        table = framework_writing.summary_table(profile(), a_completion()["blocks"])
        self.assertEqual(table["columns"][0], "Determinant")
        self.assertEqual(table["columns"][1], "Condition")
        self.assertEqual(table["rows"][0][1], "Advantage")
        self.assertEqual(table["rows"][5][1], "Not rated")

    def test_the_reading_paragraph_speaks_condition(self):
        line = framework_writing.reading_paragraph(a_completion()["blocks"][0])
        self.assertTrue(line.startswith("Condition: Advantage."), line)

    def test_the_audit_columns_include_the_causal_link(self):
        report = framework_writing.audit(profile(), a_completion())
        self.assertIn("Causal link", report["columns"])
        self.assertTrue(any(row["causal"] == "Plausible" for row in report["rows"]))

    def test_no_outcome_evidence_is_an_explanatory_hypothesis(self):
        report = framework_writing.audit(profile(), a_completion(), outcome_evidenced=False)
        self.assertEqual(report["verdict"], "Weakly supported")
        lines = " ".join(framework_writing.audit_lines(profile(), a_completion(), report,
                                                        outcome_evidenced=False))
        self.assertIn("explanatory hypothesis", lines)

    def test_the_draft_has_the_module3_shape(self):
        report = completion.draft(a_completion(), version="draft")
        headings = [section["heading"] for section in report["sections"]]
        for required in ("Scope of the Analysis", "Competitiveness Outcome Evidence",
                         "Diamond Summary Table", "Factor Conditions", "Demand Conditions",
                         "Related and Supporting Industries",
                         "Firm Strategy, Structure and Rivalry", "Government", "Chance",
                         "Discussion", "Interaction Analysis",
                         "Overall Assessment and Sustainability", "Implications",
                         "Limitations", "Conclusion", "Evidence Audit", "References"):
            self.assertIn(required, headings)

    def test_the_draft_prints_the_diamond_table(self):
        report = completion.draft(a_completion(), version="draft")
        summary = [section for section in report["sections"]
                   if section["heading"] == "Diamond Summary Table"][0]
        self.assertEqual(summary["table"]["rows"][0][1], "Advantage")
        self.assertEqual(summary["table"]["columns"][0], "Determinant")

    def test_the_draft_passes_the_structural_check(self):
        report = completion.draft(a_completion(), version="draft")
        issues = paper.check(report["sections"], framework="porters_diamond",
                             implications="The decision remains the student's.")
        self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [])


if __name__ == "__main__":
    unittest.main()
