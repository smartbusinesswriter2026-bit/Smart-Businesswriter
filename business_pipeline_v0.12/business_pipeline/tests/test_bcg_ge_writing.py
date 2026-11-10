"""BCG and GE-McKinsey: the calculation table is the core's, the audit is the paper's."""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, paper  # noqa: E402


def a_completion(template, calculation):
    profile = framework_profiles.profile_for(template)
    blocks = []
    for index, block in enumerate(profile["blocks"]):
        item = {
            "text": "The unit holds a position in its market.",
            "provenance": "sourced", "source": "Source %s (2024)." % chr(65 + index),
            "citation": "(Source, 2024)", "title": "Study %s" % chr(65 + index),
            "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
            "source_id": "S%d" % (index + 1),
        }
        reading = {
            "status": "proposed", "rating": "Strong", "rating_label": "Evidence strength",
            "drivers": [{"driver": "the stated factor", "evidence": 0, "type": "F"}],
            "trend": "Stable", "trend_reason": "The position is described at one point.",
            "profitability_impact": "The position shapes the cash the unit can generate.",
            "confidence": "Medium", "confidence_reason": "One current study supports it.",
            "so_what": "The placement is a starting hypothesis.",
            "rationale": "The evidence describes a position in the market.",
            "contradictions": [],
        }
        blocks.append({"key": block["key"], "label": block["label"], "items": [item],
                       "gap": None, "fill": "research", "reading": reading})
    if template == "template_bcg":
        chart = {"kind": "bar", "title": "Relative share by unit",
                 "points": [{"label": row[0], "value": row[3]}
                            for row in calculation.get("rows") or []]}
    else:
        chart = {"kind": "bar", "title": "Attractiveness by unit",
                 "points": [{"label": row[0], "value": row[1]}
                            for row in calculation.get("rows") or []]}
    return {"format": "bp-framework-completion/1", "template": template,
            "framework": profile["label"],
            "unit": {"field": "business", "value": "Kestrel Retail group",
                     "context": "Kestrel Retail group"},
            "instruction": "Kestrel Retail group is reviewing its portfolio.",
            "country": "", "region": "Global", "blocks": blocks, "notes": [],
            "calculation": calculation, "chart": chart}


BCG_CALC = {
    "ok": True, "method": "bcg",
    "columns": ["Unit", "Market", "Growth", "Relative share", "Quadrant", "Borderline"],
    "rows": [["Fresh", "grocery", "8.0%", "2.00", "Star", ""],
             ["Home", "household", "1.0%", "0.50", "Dog", ""]],
    "lines": ["Relative share is the frozen core's output."],
}
GE_CALC = {
    "ok": True, "method": "ge_mckinsey",
    "columns": ["Unit", "Attractiveness", "Strength", "Zone"],
    "rows": [["Fresh", "4.50", "4.00", "Invest / grow"],
             ["Home", "2.20", "2.00", "Harvest / divest"]],
    "lines": ["Weighted totals are the frozen core's output."],
}


class BcgTableTest(unittest.TestCase):
    def test_a_pasted_table_survives_the_prompt_cleanup(self):
        from unittest import mock
        from bp.product import framework_calc

        def core(name, inputs):
            if name == "market_share":
                firm = float(inputs["firm_sales"])
                rival = float(inputs["largest_competitor_sales"])
                return {"relative_market_share": firm / rival,
                        "market_share": firm / float(inputs["market_sales"])}
            if name == "weighted_summary":
                values = [float(value) for value in inputs["values"]]
                weights = [float(weight) for weight in inputs["weights"]]
                return {"weighted_mean": sum(v * w for v, w in zip(values, weights))
                        / sum(weights)}
            raise KeyError(name)

        framework_calc.set_method_compute(core)
        brief = ("Kestrel Retail group is reviewing its portfolio.\n"
                 "Portfolio | Market | Market growth | Own share | Top competitor share\n"
                 "Kestrel Fresh | grocery retail | 8% | 30% | 15%\n")
        with mock.patch("bp.product.sources.search_academic",
                        side_effect=lambda *a, **k: {"results": [], "errors": [], "skipped": []}), \
                mock.patch("bp.product.sources.search_web",
                           side_effect=lambda *a, **k: {"results": [], "notice": "off", "sites": []}):
            result = completion.complete("template_bcg", brief, unit_value="Kestrel Retail group")
        self.assertTrue(result["calculation"]["ok"], result["calculation"])
        self.assertEqual(result["calculation"]["rows"][0][4], "Star")
        framework_calc.set_method_compute(None)


class BcgGeWritingTest(unittest.TestCase):
    def test_bcg_carries_the_guideline_shape_and_the_calculation_table(self):
        report = completion.draft(a_completion("template_bcg", BCG_CALC), version="draft")
        headings = [section["heading"] for section in report["sections"]]
        for required in ("Scope, Portfolio and Market Definitions",
                         "Metric Definitions and Thresholds", "Calculation Table",
                         "Relative Share by Unit", "Discussion", "Portfolio Balance",
                         "Strategic Hypotheses", "Evidence Audit", "References"):
            self.assertIn(required, headings)
        chart = [section for section in report["sections"]
                 if section["heading"] == "Relative Share by Unit"][0]
        self.assertIsNotNone(chart.get("figure"))
        calc = [section for section in report["sections"]
                if section["heading"] == "Calculation Table"][0]
        self.assertEqual(calc["table"]["columns"][0], "Unit")
        self.assertEqual(calc["table"]["rows"][0][4], "Star")

    def test_ge_carries_the_calculation_and_the_audit(self):
        report = completion.draft(a_completion("template_ge_mckinsey", GE_CALC),
                                  version="draft")
        headings = [section["heading"] for section in report["sections"]]
        for required in ("Scope and Portfolio",
                         "Factors, Weights and Scoring Anchors",
                         "Weighted Totals and Grid Placement", "Attractiveness by Unit",
                         "Discussion", "Portfolio View and Resource Prioritisation",
                         "Per-Unit Posture", "Evidence Audit", "References"):
            self.assertIn(required, headings)
        chart = [section for section in report["sections"]
                 if section["heading"] == "Attractiveness by Unit"][0]
        self.assertIsNotNone(chart.get("figure"))
        calc = [section for section in report["sections"]
                if section["heading"] == "Weighted Totals and Grid Placement"][0]
        self.assertEqual(calc["table"]["rows"][0][3], "Invest / grow")

    def test_a_missing_calculation_is_named_not_invented(self):
        report = completion.draft(
            a_completion("template_bcg", {"ok": False, "columns": [], "rows": [],
                                          "error": "No portfolio table was found."}),
            version="draft")
        calc = [section for section in report["sections"]
                if section["heading"] == "Calculation Table"][0]
        self.assertIn("No portfolio table was found.", " ".join(calc["lines"]))

    def test_the_paper_passes_the_structural_check(self):
        for template, calc in (("template_bcg", BCG_CALC),
                               ("template_ge_mckinsey", GE_CALC)):
            report = completion.draft(a_completion(template, calc), version="draft")
            issues = paper.check(report["sections"], framework=template,
                                 implications="The decision remains the student's.")
            self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [],
                             template)


if __name__ == "__main__":
    unittest.main()
