"""Every delivered computation has a downloadable paper, and declared sources stay cited-only.

The paper is the same record the screen shows.  These tests assert that it carries the figures,
the honesty block and the checks, that the declared sources have their own section headed
"not evidence" (B-182), and that the route refuses to write a paper before a result exists.
"""

import json
import os
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import chat, session_paper  # noqa: E402

DELIVERY = {
    "status": "delivered",
    "report": "Under the stated assumptions, the npv is USD (5.26). The result is not positive.",
    "appendix": {"tier": "T1", "method": {"id": "npv", "version": "1.0.0"},
                 "spec_hash": "abc123",
                 "honesty": {"missing_data": "No missing-value handling was needed.",
                             "power": None},
                 "assumptions": ["Cash flows occur at period end."],
                 "limitations": ["The rate is the student's declaration."],
                 "reperform": {"inputs": {"rate": "0.10"}, "outputs": {"npv": "1.00"}},
        "tests": ["second_implementation_agrees", "boundary_zero_rate_equals_sum"]},
}
DECLARED = ["Smith, J. (2019). Retail expansion. https://doi.org/10.1/xyz"]


class ThePaperCarriesTheRecord(unittest.TestCase):
    def test_the_report_and_its_blocks_are_all_present(self):
        headings = [heading for heading, _lines in session_paper.sections(DELIVERY)]
        self.assertIn("Result", headings)
        self.assertIn("Honesty: what was not done", headings)
        self.assertIn("Inputs and results", headings)
        self.assertIn("Assumptions made", headings)
        self.assertIn("Limitations", headings)
        self.assertIn("How the figures were checked", headings)
        self.assertIn("Audit record", headings)

    def test_a_non_applicable_disclosure_is_omitted_not_printed_blank(self):
        honesty = dict(session_paper.sections(DELIVERY))["Honesty: what was not done"]
        self.assertTrue(any("missing data" in line for line in honesty))
        self.assertFalse(any(line.strip().endswith(":") for line in honesty))

    def test_the_markdown_carries_the_figure_and_the_checks(self):
        text = session_paper.markdown(DELIVERY)
        self.assertIn("(5.26)", text)
        self.assertIn("Second implementation agrees", text)
        self.assertNotIn("second_implementation_agrees", text,
                         "the paper must not show a raw check identifier")
        self.assertIn("Record identifier: abc123", text)

    def test_the_word_file_is_a_real_document(self):
        data = session_paper.docx_bytes(DELIVERY)
        self.assertTrue(data.startswith(b"PK"), "a .docx is a zip container")
        self.assertGreater(len(data), 1000)

    def test_the_download_name_is_readable_not_an_id(self):
        self.assertEqual(session_paper.filename(DELIVERY, "docx"), "Computation npv.docx")
        self.assertEqual(session_paper.filename(DELIVERY, "xlsx"), "Computation npv.xlsx")


class DeclaredSourcesStayCitedOnly(unittest.TestCase):
    def test_declared_sources_have_their_own_section_headed_not_evidence(self):
        sections = dict(session_paper.sections(DELIVERY, DECLARED))
        heading = "Sources you declared (not evidence)"
        self.assertIn(heading, sections)
        self.assertEqual(sections[heading][-1], DECLARED[0])
        self.assertIn("not evidence", sections[heading][0])

    def test_they_are_never_merged_into_the_result_or_the_checks(self):
        sections = dict(session_paper.sections(DELIVERY, DECLARED))
        for heading in ("Result", "How the figures were checked", "Assumptions made"):
            self.assertFalse(any("Smith, J." in line for line in sections[heading]),
                             "%s must not carry a declared citation" % heading)

    def test_no_declared_sources_means_no_section(self):
        self.assertNotIn("Sources you declared (not evidence)", dict(session_paper.sections(DELIVERY)))

    def test_the_conductor_paper_appends_the_section_exactly_once(self):
        state = {"draft": {"sections": [["Conclusion", ["The decision is stated."]]]},
                 "declared_sources": DECLARED}
        once = chat._append_declared_sources(dict(state, draft={"sections": list(state["draft"]["sections"])}))
        headings = [item[0] for item in once["draft"]["sections"]]
        self.assertEqual(headings, ["Conclusion", "Sources you declared (not evidence)"])
        twice = chat._append_declared_sources(once)
        self.assertEqual([item[0] for item in twice["draft"]["sections"]], headings,
                         "drafting twice must not duplicate the section")

    def test_a_paper_without_declared_sources_is_unchanged(self):
        state = {"draft": {"sections": [["Conclusion", ["The decision is stated."]]]}}
        self.assertEqual(chat._append_declared_sources(dict(state))["draft"]["sections"],
                         [["Conclusion", ["The decision is stated."]]])


class TheDownloadRouteTest(unittest.TestCase):
    """E-fin-051: every delivered computation can be downloaded, and only after delivery."""

    @classmethod
    def setUpClass(cls):
        from bp import server
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H)
        cls.base = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def call(self, path, body=None, raw=False):
        data = None if body is None else json.dumps(body).encode()
        request = urllib.request.Request(self.base + path, data=data,
                                         headers={"Content-Type": "application/json"},
                                         method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(request) as stream:
                payload = stream.read()
                return (stream.status, payload) if raw else (stream.status, json.loads(payload))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read() or b"{}")

    def session(self):
        status, created = self.call("/api/sessions", {"objective": "download acceptance",
                                                      "method": "npv", "currency": "USD",
                                                      "inputs": {"rate": "0.10",
                                                                 "cashflows": ["-1000", "400", "400"]}})
        self.assertEqual(status, 201)
        return created["id"]

    def test_a_paper_cannot_be_written_before_the_result_is_delivered(self):
        session_id = self.session()
        status, refused = self.call("/api/sessions/%s/paper" % session_id, {"format": "docx"})
        self.assertEqual(status, 409)
        self.assertIn("after the result is delivered", refused["error"])

    def test_a_delivered_computation_downloads_a_word_paper(self):
        session_id = self.session()
        self.call("/api/sessions/%s/confirm" % session_id, {})
        status, data = self.call("/api/sessions/%s/paper" % session_id, {"format": "docx"}, raw=True)
        self.assertEqual(status, 200)
        self.assertTrue(data.startswith(b"PK"), "a .docx is a zip container")

    def test_a_delivered_computation_downloads_excel_with_its_figure(self):
        session_id = self.session()
        self.call("/api/sessions/%s/confirm" % session_id, {})
        status, data = self.call("/api/sessions/%s/paper" % session_id, {"format": "xlsx"}, raw=True)
        self.assertEqual(status, 200)
        self.assertTrue(data.startswith(b"PK"), "an .xlsx is a zip container")
        self.assertGreater(len(data), 1000,
                           "a workbook with content, not an empty shell")

    def test_an_unknown_format_is_refused(self):
        session_id = self.session()
        self.call("/api/sessions/%s/confirm" % session_id, {})
        status, refused = self.call("/api/sessions/%s/paper" % session_id, {"format": "pdf"})
        self.assertEqual(status, 422)
        self.assertIn("docx or xlsx", refused["error"])

    def test_an_unknown_session_is_a_404(self):
        self.assertEqual(self.call("/api/sessions/nosuch/paper", {"format": "xlsx"})[0], 404)


if __name__ == "__main__":
    unittest.main()

