"""Quality modules: the guideline's tables and an existing chart where values exist."""

import re
import sys
import unittest

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, paper  # noqa: E402

CASES = {
    "template_root_cause": {
        "keys": ["problem", "people", "process", "equipment", "materials",
                 "measurement", "environment", "root_cause"],
        "tables": [{"heading": "Verification audit",
                    "columns": ["Cause", "Status"],
                    "rows": [["Seal leaks", "Verified"]]}],
        "chart": {"kind": "tree", "title": "Why chain", "root": "Seal leaks",
                  "children": ["Worn tool", "Wrong torque"]},
        "chart_head": "Why-Chain Tree",
        "audit_head": "Verification Audit",
    },
    "template_fmea": {
        "keys": ["failure_modes", "effects", "causes", "controls", "actions", "owners"],
        "tables": [{"heading": "FMEA worksheet",
                    "columns": ["Failure mode", "RPN"],
                    "rows": [["Seal leaks", "120"]]}],
        "chart": {"kind": "pareto", "title": "RPN by failure mode",
                  "points": [{"label": "Seal leaks", "value": "120",
                              "cumulative": "120"},
                             {"label": "Wrong part", "value": "80",
                              "cumulative": "200"}]},
        "chart_head": "RPN Pareto",
        "audit_head": "Calculation Audit",
    },
    "template_pdca": {
        "keys": ["plan", "do", "check", "act"],
        "tables": [{"heading": "Cycle log", "columns": ["Stage", "Status"],
                    "rows": [["Plan", "Completed"]]}],
        "chart": {"kind": "line", "title": "Measure by stage",
                  "points": [{"label": "Baseline", "value": "4.2"},
                             {"label": "Result", "value": "1.1"}]},
        "chart_head": "Cycle Measures",
        "audit_head": "Required Checks",
    },
    "template_5s": {
        "keys": ["sort", "set_in_order", "shine", "standardize", "sustain"],
        "tables": [{"heading": "Scorecard", "columns": ["S", "Score"],
                    "rows": [["Sort", "3"]]}],
        "chart": {"kind": "bar", "title": "Score by S",
                  "points": [{"label": "Sort", "value": "3"},
                             {"label": "Shine", "value": "4"}]},
        "chart_head": "Score by S",
        "audit_head": "Required Checks",
    },
}


def norm(text):
    clean = re.sub(r"[^a-z0-9 ]+", " ", str(text).lower())
    return re.sub(r"\s+", " ", clean).strip()


def a_completion(template):
    case = CASES[template]
    profile = framework_profiles.profile_for(template)
    labels = {block["key"]: block["label"] for block in profile["blocks"]}
    blocks = []
    for index, key in enumerate(case["keys"]):
        item = {"text": "The record states an observation.",
                "provenance": "sourced", "source": "Source %s (2024)." % chr(65 + index),
                "citation": "(Source, 2024)", "title": "Record %s" % chr(65 + index),
                "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
                "source_id": "S%d" % (index + 1)}
        reading = {"status": "proposed", "rating": "Strong",
                   "rating_label": "Evidence strength",
                   "drivers": [{"driver": "the stated observation", "evidence": 0, "type": "F"}],
                   "trend": "Stable", "trend_reason": "One observation.",
                   "profitability_impact": "The finding shapes the action.",
                   "confidence": "Medium", "confidence_reason": "One record.",
                   "so_what": "The action follows the finding.",
                   "rationale": "The record states the observation.", "contradictions": []}
        blocks.append({"key": key, "label": labels.get(key, key), "items": [item],
                       "gap": None, "fill": "research", "reading": reading})
    return {"format": "bp-framework-completion/1", "template": template,
            "framework": profile["label"],
            "unit": {"field": "process", "value": "the lunch service"},
            "instruction": "The lunch service is being reviewed.",
            "country": "", "region": "Global", "blocks": blocks, "notes": [],
            "tables": case["tables"], "chart": case["chart"]}


class QualityTableTest(unittest.TestCase):
    def test_a_pasted_fmea_table_is_computed_by_the_core(self):
        from unittest import mock
        from bp.product import framework_calc

        def core(name, inputs):
            if name == "fmea_rpn":
                severity = float(inputs["severity"])
                occurrence = float(inputs["occurrence"])
                detection = float(inputs["detection"])
                return {"severity": severity, "occurrence": occurrence,
                        "detection": detection,
                        "rpn": severity * occurrence * detection}
            raise KeyError(name)

        framework_calc.set_method_compute(core)
        brief = ("The line is reviewed.\n"
                 "ID | Failure mode | S | O | D\n"
                 "1 | Seal leaks | 7 | 4 | 3\n"
                 "2 | Wrong part | 4 | 6 | 2\n")
        with mock.patch("bp.product.sources.search_academic",
                        side_effect=lambda *a, **k: {"results": [], "errors": [], "skipped": []}), \
                mock.patch("bp.product.sources.search_web",
                           side_effect=lambda *a, **k: {"results": [], "notice": "off", "sites": []}):
            result = completion.complete("template_fmea", brief, unit_value="the line")
        self.assertTrue(result["calculation"]["ok"], result["calculation"])
        self.assertEqual(result["chart"]["kind"], "pareto")
        framework_calc.set_method_compute(None)


class QualityWritingTest(unittest.TestCase):
    def test_each_module_prints_its_table_and_chart(self):
        for template, case in CASES.items():
            report = completion.draft(a_completion(template), version="draft")
            headings = [norm(section["heading"]) for section in report["sections"]]
            self.assertIn(norm(case["chart_head"]), headings, template)
            self.assertIn(norm(case["audit_head"]), headings, template)
            chart = [section for section in report["sections"]
                     if norm(section["heading"]) == norm(case["chart_head"])][0]
            self.assertIsNotNone(chart.get("figure"), template)
            table = [section for section in report["sections"]
                     if norm(section["heading"]) == norm(case["tables"][0]["heading"])][0]
            self.assertEqual(table["table"]["columns"], case["tables"][0]["columns"])

    def test_each_draft_passes_the_structural_check(self):
        for template in CASES:
            report = completion.draft(a_completion(template), version="draft")
            issues = paper.check(report["sections"], framework=template,
                                 implications="The decision remains the student's.")
            self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [],
                             template)

    def test_a_malformed_table_is_dropped_not_printed_half_built(self):
        from bp.product import framework_writing
        clean = framework_writing.clean_tables([
            {"heading": "Bad", "columns": ["A", "B"], "rows": [["one"]]},
            {"heading": "Good", "columns": ["A", "B"], "rows": [["one", "two"]]},
        ])
        self.assertEqual([entry["heading"] for entry in clean], ["Good"])

    def test_the_report_json_carries_no_binary_asset(self):
        from bp.product import api
        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": a_completion("template_5s"),
                                      "version": "draft"})
        self.assertEqual(status, 200, payload)
        chart = [section for section in payload["report"]["sections"]
                 if norm(section["heading"]) == norm("Score by S")][0]
        self.assertIsNotNone(chart.get("figure"))
        self.assertIsNone((chart["figure"].get("asset") or {}).get("png"))

    def test_the_json_view_handles_bytes_and_decimal(self):
        from decimal import Decimal
        from bp.product import api
        safe = api._json_safe({"asset": b"png", "value": Decimal("1.50")})
        self.assertIsNone(safe["asset"])
        self.assertEqual(safe["value"], "1.50")

    def test_no_chart_is_a_sentence_not_an_empty_figure(self):
        result = a_completion("template_5s")
        result["chart"] = None
        report = completion.draft(result, version="draft")
        chart = [section for section in report["sections"]
                 if norm(section["heading"]) == norm("Score by S")][0]
        self.assertIsNone(chart.get("figure"))
        self.assertIn("No chart was recorded", " ".join(chart["lines"]))


if __name__ == "__main__":
    unittest.main()
