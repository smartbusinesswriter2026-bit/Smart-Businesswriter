"""Student confirmation of proposed readings: confirm, override, drop.

The system proposes a rating; the student decides.  The decision is recorded on
the reading and printed beside it.  An unknown part, status or scale value is
refused rather than silently ignored.
"""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import api, completion, framework_profiles, framework_writing  # noqa: E402


def reading():
    return {
        "status": "proposed", "rating": "High", "rating_label": "Rating",
        "rating_scale": ["Low", "Moderate", "High"],
        "drivers": [{"driver": "price competition", "evidence": 0, "type": "F",
                     "area": "pricing", "bias": "not classified", "causal": "-"}],
        "trend": "Rising", "trend_reason": "Price competition is intense.",
        "profitability_impact": "Margins fall as buyers compare prices.",
        "confidence": "Medium", "confidence_reason": "One current study supports the reading.",
        "so_what": "A new entrant must justify its price.",
        "rationale": "The evidence names price competition directly.",
    }


def a_completion():
    return {"template": "template_five_forces", "blocks": [{
        "key": "rivalry", "label": "Industry rivalry",
        "items": [{"text": "Price competition is intense.", "provenance": "sourced",
                   "source": "Source A (2024).", "citation": "(Source, 2024)",
                   "title": "Study A", "database": "OpenAlex", "year": 2024,
                   "tier": "B", "recency": "current", "source_id": "S1"}],
        "reading": reading(),
    }]}


class ConfirmReadingsTest(unittest.TestCase):
    def test_confirm_records_the_student_and_keeps_the_value(self):
        out = completion.confirm_readings(a_completion(), {"rivalry": {"status": "confirmed"}})
        stored = out["blocks"][0]["reading"]
        self.assertEqual(stored["status"], "confirmed")
        self.assertEqual(stored["confirmed_by"], "student")
        self.assertEqual(stored["rating"], "High")
        self.assertIn("readings_confirmed_at", out)

    def test_override_records_the_new_value_and_the_proposal(self):
        out = completion.confirm_readings(
            a_completion(), {"rivalry": {"status": "overridden", "rating": "Moderate",
                                         "reason": "One study is not enough for High."}})
        stored = out["blocks"][0]["reading"]
        self.assertEqual(stored["status"], "overridden")
        self.assertEqual(stored["rating"], "Moderate")
        self.assertEqual(stored["override"]["rating"], "Moderate")

    def test_drop_removes_the_rating_from_the_summary_and_the_paragraph(self):
        out = completion.confirm_readings(a_completion(), {"rivalry": {"status": "dropped"}})
        block = out["blocks"][0]
        self.assertEqual(block["reading"]["status"], "dropped")
        table = framework_writing.summary_table(
            framework_profiles.profile_for("template_five_forces"), [block])
        self.assertEqual(table["rows"][0][1], "Not rated")
        self.assertEqual(framework_writing.reading_paragraph(block), "")

    def test_an_unknown_part_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            completion.confirm_readings(a_completion(), {"buyers": {"status": "confirmed"}})
        self.assertIn("no part", str(refused.exception).lower())

    def test_an_unknown_status_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            completion.confirm_readings(a_completion(), {"rivalry": {"status": "approved"}})
        self.assertIn("confirmed", str(refused.exception).lower())

    def test_an_override_outside_the_scale_is_refused(self):
        with self.assertRaises(ValueError) as refused:
            completion.confirm_readings(a_completion(),
                                        {"rivalry": {"status": "overridden",
                                                     "rating": "Very High"}})
        self.assertIn("override", str(refused.exception).lower())

    def test_a_part_with_no_proposed_reading_is_refused(self):
        completion_dict = a_completion()
        completion_dict["blocks"][0]["reading"] = {"status": "absent", "reason": "no items"}
        with self.assertRaises(ValueError) as refused:
            completion.confirm_readings(completion_dict, {"rivalry": {"status": "confirmed"}})
        self.assertIn("no proposed reading", str(refused.exception).lower())

    def test_the_api_route_confirms_and_refuses(self):
        status, payload = api.handle("POST", "/api/cases/frameworks/readings",
                                     {"completion": a_completion(),
                                      "decisions": {"rivalry": {"status": "confirmed"}}})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["blocks"][0]["reading"]["status"], "confirmed")
        status, payload = api.handle("POST", "/api/cases/frameworks/readings",
                                     {"completion": a_completion(),
                                      "decisions": {"buyers": {"status": "confirmed"}}})
        self.assertEqual(status, 422, payload)

    def test_the_audit_says_how_far_the_student_has_confirmed(self):
        out = completion.confirm_readings(a_completion(), {"rivalry": {"status": "confirmed"}})
        profile = framework_profiles.profile_for("template_five_forces")
        lines = " ".join(framework_writing.audit_lines(profile, out, outcome_evidenced=False))
        self.assertIn("Readings: 0 proposed, 1 confirmed", lines)


if __name__ == "__main__":
    unittest.main()
