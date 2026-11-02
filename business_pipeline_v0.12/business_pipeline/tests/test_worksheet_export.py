"""The worksheet export artefact (B-121).

A completed framework is its own deliverable: the narrative and verbatim listing,
the checks, the limitations and the citation. It is not an assignment submission
with statements and workings that do not exist for a template.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, "src")
from bp import templates as T
from bp.orchestrator import Pipeline
from bp.product import deliverables as D


def template_bundle():
    request = T.EXAMPLES["template_business_model_canvas"]
    delivery = Pipeline().run(request, lambda spec: True)
    assert delivery.status == "delivered", delivery.blocked_reason
    return {"title": "Business model canvas", "id": "case00000001",
            "delivery": {"report": delivery.report, "appendix": delivery.appendix}}


class WorksheetProfile(unittest.TestCase):
    def test_the_profile_is_available_with_word_and_print_ready_html(self):
        entry = D.profile("worksheet")
        self.assertEqual(entry["label"], "Worksheet submission")
        self.assertEqual(entry["formats"], ["docx", "html"])
        self.assertEqual(entry["default"], "docx")
        self.assertIn("report", entry["blocks"])
        self.assertEqual(D.check_pair("worksheet", "docx")["label"], "Worksheet submission")
        self.assertEqual(D.check_pair("worksheet", "html")["label"], "Worksheet submission")

    def test_the_sections_carry_the_report_checks_limits_and_citation(self):
        bundle = template_bundle()
        headings = [heading for heading, _ in D.sections(bundle, "worksheet")]
        self.assertIn("Report", headings)
        self.assertIn("Verification checks", headings)
        self.assertIn("Limitations", headings)
        self.assertIn("How this was produced", headings)
        report = dict(D.sections(bundle, "worksheet"))["Report"]
        text = "\n".join(report)
        self.assertIn("business model canvas organizes", text)
        self.assertIn("A hot rice meal under eighty pesos", text)

    def test_the_word_file_is_written_and_not_empty(self):
        bundle = template_bundle()
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "worksheet.docx")
            result = D.write_export(bundle, "worksheet", "docx", path)
            self.assertEqual(result["deliverable"], "worksheet")
            self.assertTrue(os.path.exists(path))
            self.assertGreater(os.path.getsize(path), 1000)
            with open(path, "rb") as stream:
                self.assertEqual(stream.read(2), b"PK")

    def test_the_blocks_are_empty_for_a_bundle_without_a_report(self):
        self.assertEqual(D.block({"delivery": {}}, "report"), [])


if __name__ == "__main__":
    unittest.main()
