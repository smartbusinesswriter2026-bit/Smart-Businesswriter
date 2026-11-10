"""Five Forces writing module: the guideline's sections and driver checklists.

The framework is still data.  This test holds the data the writing engine reads:
the sections the paper must carry, the driver checklist for each force, and the
rule that no two forces share one generic note.
"""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import completion, framework_profiles, framework_writing, paper  # noqa: E402

LABELS = {"rivalry": "Industry rivalry", "entrants": "Threat of new entrants",
          "substitutes": "Threat of substitutes", "buyers": "Buyer power",
          "suppliers": "Supplier power"}


def profile():
    return framework_profiles.profile_for("template_five_forces")


def a_completion():
    """Five forces with one sourced item each; rivalry carries a proposed reading."""
    blocks = []
    for index, key in enumerate(["rivalry", "entrants", "substitutes", "buyers", "suppliers"]):
        item = {
            "text": "Price competition is intense in grocery retail.",
            "provenance": "sourced", "source": "Source %s (2024)." % chr(65 + index),
            "citation": "(Source, 2024)", "title": "Study %s" % chr(65 + index),
            "database": "OpenAlex", "year": 2024, "tier": "B", "recency": "current",
            "source_id": "S%d" % (index + 1),
        }
        block = {"key": key, "label": LABELS[key], "items": [item], "gap": None,
                 "fill": "research"}
        if key == "rivalry":
            block["reading"] = {
                "status": "proposed", "rating": "High",
                "drivers": [{"driver": "price competition", "evidence": 0, "type": "F",
                             "area": "pricing", "bias": "not classified"}],
                "trend": "Rising", "trend_reason": "Price competition is intense.",
                "profitability_impact": "Margins fall as buyers compare prices.",
                "confidence": "Medium",
                "confidence_reason": "One current study supports the reading.",
                "so_what": "A new entrant must justify its price.",
                "rationale": "The evidence names price competition directly.",
                "rating_scale": ["Low", "Moderate", "High"],
            }
        blocks.append(block)
    return {"format": "bp-framework-completion/1", "template": "template_five_forces",
            "framework": "Porter's Five Forces",
            "unit": {"field": "industry", "value": "grocery retail",
                     "context": "grocery retail"},
            "instruction": "Kestrel Retail is reviewing its grocery retail position.",
            "country": "", "region": "Global", "blocks": blocks, "notes": []}


class FiveForcesWritingTest(unittest.TestCase):
    def test_the_profile_declares_the_guideline_sections(self):
        writing = profile().get("writing") or {}
        self.assertEqual(writing.get("module"), "five_forces")
        self.assertEqual(writing.get("sections", [None])[0], "scope")
        for name in ("summary", "dimensions", "synthesis", "forward", "audit"):
            self.assertIn(name, writing.get("sections") or [])

    def test_each_force_has_its_own_driver_checklist(self):
        drivers = (profile().get("writing") or {}).get("drivers") or {}
        self.assertEqual(set(drivers),
                         {"rivalry", "entrants", "substitutes", "buyers", "suppliers"})
        self.assertIn("expected retaliation", drivers["entrants"])
        self.assertIn("diversity of rivals' goals", drivers["rivalry"])
        self.assertIn("threat of forward integration", drivers["suppliers"])
        self.assertIn("threat of backward integration", drivers["buyers"])
        self.assertIn("buyers' propensity to substitute", drivers["substitutes"])

    def test_the_summary_and_audit_columns_are_declared(self):
        writing = profile().get("writing") or {}
        self.assertEqual(writing.get("summary_columns"),
                         ["Force", "Rating", "Trend", "Confidence", "One-line rationale"])
        for column in ("Claim", "Source", "Tier", "Recency", "Type", "Strength", "Notes"):
            self.assertIn(column, writing.get("audit_columns") or [])

    def test_no_two_forces_share_a_note(self):
        notes = profile()["notes"]
        keys = ["rivalry", "entrants", "substitutes", "buyers", "suppliers"]
        for field in ("analysis", "qualify", "short"):
            values = [notes[key][field] for key in keys]
            self.assertEqual(len(values), len(set(values)), field)

    def test_the_unit_is_still_an_industry(self):
        self.assertEqual(profile()["unit"]["field"], "industry")

    def test_the_profile_still_passes_its_completeness_check(self):
        self.assertIs(framework_profiles.profile_for("template_five_forces"), profile())

    def test_the_scope_names_the_unit_and_says_what_is_unstated(self):
        lines = framework_writing.scope_lines(profile(), a_completion())
        text = " ".join(lines)
        self.assertIn("industry", text.lower())
        self.assertIn("grocery retail", text)
        self.assertIn("no single country", text.lower())
        self.assertIn("2024", text)

    def test_the_summary_table_carries_every_force_and_the_rating(self):
        table = framework_writing.summary_table(profile(), a_completion()["blocks"])
        self.assertEqual(table["columns"],
                         ["Force", "Rating", "Trend", "Confidence", "One-line rationale"])
        self.assertEqual(len(table["rows"]), 5)
        self.assertEqual(table["rows"][0][0], "Industry rivalry")
        self.assertEqual(table["rows"][0][1], "High")
        self.assertEqual(table["rows"][1][1], "Not rated")

    def test_the_reading_paragraph_carries_every_required_part(self):
        line = framework_writing.reading_paragraph(a_completion()["blocks"][0])
        for part in ("Rating: High", "Drivers:", "Trend: Rising", "Profitability impact:",
                     "Confidence: Medium", "So what:"):
            self.assertIn(part, line)

    def test_the_audit_records_the_claim_tier_and_verdict(self):
        report = framework_writing.audit(profile(), a_completion())
        self.assertEqual(len(report["rows"]), 5)
        first = report["rows"][0]
        self.assertEqual(first["type"], "F")
        self.assertEqual(first["tier"], "B")
        self.assertEqual(first["recency"], "current")
        self.assertEqual(first["source_id"], "S1")
        self.assertIn(report["verdict"],
                      ("Well-supported", "Partially supported", "Weakly supported"))

    def test_the_draft_paper_carries_the_guideline_shape(self):
        report = completion.draft(a_completion(), version="draft")
        headings = [section["heading"] for section in report["sections"]]
        expected = ["Introduction", "Case and Industry Context", "Five Forces",
                    "Scope of the Analysis", "Force Ratings",
                    "Industry Rivalry", "Threat of New Entrants", "Threat of Substitutes",
                    "Buyer Power", "Supplier Power", "Discussion",
                    "Synthesis and Interactions", "Forward-Looking Shifts",
                    "Implications for the Decision", "Limitations",
                    "Conclusion", "Evidence Audit", "References"]
        self.assertEqual(headings, expected)

    def test_the_draft_prints_the_summary_and_audit_tables(self):
        report = completion.draft(a_completion(), version="draft")
        summary = [section for section in report["sections"]
                   if section["heading"] == "Force Ratings"][0]
        self.assertEqual(summary["table"]["columns"][1], "Rating")
        self.assertEqual(summary["table"]["rows"][0][1], "High")
        audit = [section for section in report["sections"]
                 if section["heading"] == "Evidence Audit"][0]
        self.assertIn("Overall verdict:", " ".join(audit["lines"]))
        self.assertEqual(audit["table"]["columns"][1], "Claim")

    def test_the_draft_reading_paragraph_reaches_the_force_section(self):
        report = completion.draft(a_completion(), version="draft")
        rivalry = [section for section in report["sections"]
                   if section["heading"] == "Industry Rivalry"][0]
        self.assertTrue(rivalry["lines"][0].startswith("Rating: High."), rivalry["lines"][0])

    def test_background_only_is_a_gap_not_evidence(self):
        result = a_completion()
        for block in result["blocks"]:
            block.pop("reading", None)
            block["items"] = [{"text": "General background, not a source.",
                               "provenance": "background", "source": ""}]
        table = framework_writing.summary_table(profile(), result["blocks"])
        self.assertIn("Insufficient evidence", table["rows"][0][4])
        report = framework_writing.audit(profile(), result)
        self.assertEqual(len(report["gaps"]), 5)
        self.assertEqual(report["verdict"], "Weakly supported")

    def test_the_draft_passes_the_structural_check(self):
        report = completion.draft(a_completion(), version="draft")
        issues = paper.check(report["sections"], framework="five_forces",
                             implications="The decision remains the student's.")
        self.assertEqual([i for i in issues["issues"] if i["severity"] == "high"], [])


if __name__ == "__main__":
    unittest.main()
