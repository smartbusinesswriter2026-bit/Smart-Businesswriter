"""Generic Strategies writing module: fit table, classification and audit.

The unit is the firm or business unit in its market; the reading is a fit
(Strong/Partial/Weak/None), not an intensity.  The audit is Module 2 of the
owner's guideline: coverage, triangulation, quantification, bias, contradictions,
gaps and a verdict.
"""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, framework_writing, paper  # noqa: E402

LABELS = {"low_cost": "Low-Cost", "differentiation": "Differentiation",
          "focus_low_cost": "Focused Low-Cost",
          "focus_differentiation": "Focused Differentiation"}

FITS = {"low_cost": "Strong", "differentiation": "Partial", "focus_low_cost": "Weak"}

AREAS = {"low_cost": "pricing", "differentiation": "operations",
         "focus_low_cost": "marketing"}


def profile():
    return framework_profiles.profile_for("template_generic_strategies")


def a_completion():
    blocks = []
    for index, key in enumerate(["low_cost", "differentiation", "focus_low_cost",
                                 "focus_differentiation"]):
        item = {
            "text": "The firm competes on a clear position in its market.",
            "provenance": "sourced", "source": "Source %s (2024)." % chr(65 + index),
            "citation": "(Source, 2024)", "title": "Study %s" % chr(65 + index),
            "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
            "source_id": "S%d" % (index + 1),
        }
        block = {"key": key, "label": LABELS[key], "items": [item], "gap": None,
                 "fill": "research"}
        if key in FITS:
            block["reading"] = {
                "status": "proposed", "rating": FITS[key], "rating_label": "Fit",
                "drivers": [{"driver": "unit cost against peers", "evidence": 0, "type": "F",
                             "area": AREAS[key], "bias": "not classified"}],
                "trend": "Stable", "trend_reason": "The position is described at one point.",
                "profitability_impact": "The position shapes the margin the firm can keep.",
                "confidence": "Medium",
                "confidence_reason": "One current study supports the reading.",
                "so_what": "The choice must be matched by the activity system.",
                "rationale": "The evidence describes a position in the market.",
            }
        blocks.append(block)
    return {"format": "bp-framework-completion/1",
            "template": "template_generic_strategies",
            "framework": "Generic Strategies",
            "unit": {"field": "firm", "value": "Kestrel Retail", "firm": "Kestrel Retail",
                     "market": "grocery retail", "context": "Kestrel Retail grocery retail"},
            "instruction": "Kestrel Retail is reviewing its competitive position.",
            "country": "", "region": "Global", "blocks": blocks, "notes": []}


class GenericStrategiesWritingTest(unittest.TestCase):
    def test_the_profile_declares_the_module2_sections(self):
        writing = profile().get("writing") or {}
        self.assertEqual(writing.get("module"), "generic_strategies")
        for part in ("scope", "summary", "dimensions", "synthesis", "coherence",
                     "stuck", "implications", "audit"):
            self.assertIn(part, writing.get("sections") or [])
        self.assertEqual(writing.get("scale"), "fit")
        self.assertEqual(writing.get("rating_label"), "Fit")

    def test_the_fit_table_uses_fit_not_intensity(self):
        table = framework_writing.summary_table(profile(), a_completion()["blocks"])
        self.assertEqual(table["columns"],
                         ["Strategy", "Fit", "Confidence", "One-line rationale"])
        self.assertEqual(table["rows"][0][1], "Strong")
        self.assertEqual(table["rows"][3][1], "Not rated")

    def test_the_reading_paragraph_speaks_fit(self):
        line = framework_writing.reading_paragraph(a_completion()["blocks"][0])
        self.assertTrue(line.startswith("Fit: Strong."), line)

    def test_the_coverage_check_counts_value_chain_areas(self):
        report = framework_writing.audit(profile(), a_completion())
        self.assertTrue(report["coverage"]["pass"])
        self.assertEqual(set(report["coverage"]["areas"]),
                         {"pricing", "operations", "marketing"})

    def test_the_audit_records_the_strategy_and_the_verdict(self):
        report = framework_writing.audit(profile(), a_completion())
        self.assertEqual(report["rows"][0]["dimension"], "Low-Cost")
        self.assertEqual(report["rows"][0]["type"], "F")
        self.assertIn(report["verdict"],
                      ("Well-supported", "Partially supported", "Weakly supported"))

    def test_bias_and_contradictions_are_recorded(self):
        result = a_completion()
        result["blocks"][0]["reading"]["drivers"][0]["bias"] = "firm"
        result["blocks"][0]["reading"]["contradictions"] = [
            "A second study reports stable prices."]
        report = framework_writing.audit(profile(), result)
        self.assertTrue(report["bias"])
        self.assertIn("bias: firm", " ".join(row["notes"] for row in report["rows"]))
        lines = " ".join(framework_writing.audit_lines(profile(), result, report))
        self.assertIn("A second study reports stable prices", lines)

    def test_the_draft_has_the_module2_shape(self):
        report = completion.draft(a_completion(), version="draft")
        headings = [section["heading"] for section in report["sections"]]
        for required in ("Scope of the Analysis", "Strategy Fit Summary",
                         "Low-Cost", "Differentiation", "Focused Low-Cost",
                         "Focused Differentiation", "Discussion",
                         "Classification and Reasoning", "Coherence and Sustainability",
                         "Stuck in the Middle", "Implications and Recommendations",
                         "Limitations", "Conclusion", "Evidence Audit", "References"):
            self.assertIn(required, headings)

    def test_the_draft_prints_the_fit_table_and_the_audit(self):
        report = completion.draft(a_completion(), version="draft")
        summary = [section for section in report["sections"]
                   if section["heading"] == "Strategy Fit Summary"][0]
        self.assertEqual(summary["table"]["rows"][0][1], "Strong")
        audit = [section for section in report["sections"]
                 if section["heading"] == "Evidence Audit"][0]
        self.assertIn("Coverage:", " ".join(audit["lines"]))
        self.assertIn("Overall verdict:", " ".join(audit["lines"]))

    def test_the_draft_passes_the_structural_check(self):
        report = completion.draft(a_completion(), version="draft")
        issues = paper.check(report["sections"], framework="generic_strategies",
                             implications="The decision remains the student's.")
        self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [])


if __name__ == "__main__":
    unittest.main()
