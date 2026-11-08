"""Downloads must reach the browser: a file, not a path on the server (E-dl-001…004).

Reported by the owner: the accounting result panel answered "Spreadsheet exported to
exports\\<id>.xlsx" and nothing arrived, and Word/Markdown refused because they asked for a
live session the accounting flow does not keep.  These tests pin the three things that
made that possible.
"""

import base64
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

import product_fixtures  # noqa: E402
from bp.product import api, cases, deliverables  # noqa: E402

PAGE = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
API = (ROOT / "src" / "bp" / "product" / "api.py").read_text(encoding="utf-8")


class ExportDownloadRouteTest(unittest.TestCase):
    """The route itself, in process: bytes come back, and Word is a real package."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-download-")
        self.previous = os.environ.get("BP_STATE_DIR")
        self.grant = os.environ.get("BP_CREDITS_GRANT")
        os.environ["BP_STATE_DIR"] = self.root
        os.environ["BP_CREDITS_GRANT"] = "5"
        self.case_id = cases.save(product_fixtures.make_bundle())

    def tearDown(self):
        for name, value in (("BP_STATE_DIR", self.previous), ("BP_CREDITS_GRANT", self.grant)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def test_e_dl_005__the_spreadsheet_mode_returns_bytes_a_browser_can_save(self):
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "xlsx", "deliverable": "workpapers",
                                      "download": True})
        self.assertEqual(status, 200, payload)
        for key in ("data", "mime", "filename"):
            self.assertIn(key, payload, "a download response carries what the page needs")
        self.assertNotIn("path", payload, "the browser cannot fetch a server path")
        raw = base64.b64decode(payload["data"])
        self.assertTrue(raw.startswith(b"PK"), "an .xlsx is a zip package, not a text stub")
        self.assertTrue(payload["filename"].endswith(".xlsx"), payload["filename"])

    def test_e_dl_006__the_words_paper_downloads_and_carries_a_real_docx(self):
        status, payload = api.handle("POST", "/api/cases/%s/export" % self.case_id,
                                     {"kind": "docx", "deliverable": "submission",
                                      "download": True})
        self.assertEqual(status, 200, payload)
        raw = base64.b64decode(payload["data"])
        self.assertTrue(raw.startswith(b"PK"), "a real .docx (or its ZIP) is a zip package")
        if payload["filename"].endswith(".zip"):
            # A submission that carries a computation ships with its teachable
            # companion in one ZIP: the Word file is inside it.
            import io
            import zipfile
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                names = archive.namelist()
            self.assertTrue(any(name.endswith(".docx") for name in names), names)
        else:
            self.assertTrue(payload["filename"].endswith(".docx"), payload["filename"])
            self.assertGreater(len(raw), 1000, "an empty package is not a paper")



class DownloadsReachTheBrowserTest(unittest.TestCase):
    def test_e_dl_001__the_results_panel_downloads_bytes_not_a_server_path(self):
        self.assertNotIn("Spreadsheet exported to", PAGE,
                         "a path on the server is not a download")
        self.assertIn('{ kind: "xlsx", deliverable: "workpapers", download: true }', PAGE,
                      "the results panel asks for the bytes")
        self.assertIn("function saveDownload", PAGE,
                      "one helper turns an export response into a file")

    def test_e_dl_002__word_falls_back_to_the_saved_case_when_no_session_is_live(self):
        self.assertIn("const sessionId = state.session && state.session.id", PAGE)
        self.assertIn('{ kind: "docx", deliverable: "submission", download: true }', PAGE,
                      "a saved case can still produce its Word paper")

    def test_e_dl_007__the_accounting_statements_download_as_a_word_file(self):
        """The management-accounts panel's statements button: bytes, not a server path.

        Reported by the owner: "users cannot download the result of their computation in
        accounting".  The button posted to `/api/cases//export` with an empty id and a
        destination path, so nothing ever reached the browser.
        """
        bundle = product_fixtures.make_bundle()
        bundle["delivery"].setdefault("appendix", {})["accounts"] = {
            "statements_export": {"trial_balance": "TRIAL BALANCE\n  Cash 100.00",
                                  "income_statement": "INCOME STATEMENT\n  Net income 50.00"}}
        case_id = cases.save(bundle)
        status, payload = api.handle("POST", "/api/cases/%s/export" % case_id,
                                     {"kind": "docx", "deliverable": "statements",
                                      "download": True})
        self.assertEqual(status, 200, payload)
        self.assertNotIn("path", payload, "the browser cannot fetch a server path")
        raw = base64.b64decode(payload["data"])
        self.assertTrue(raw.startswith(b"PK"), "a real .docx is a zip package")
        self.assertTrue(payload["filename"].endswith(".docx"), payload["filename"])
        self.assertEqual(payload["deliverable"], "statements")

    def test_e_dl_008__the_accounting_panel_asks_for_the_statements_as_bytes(self):
        self.assertIn('{ kind: "docx", deliverable: "statements", download: true }', PAGE,
                      "the statements button asks the route for a file")
        self.assertNotIn('destination: "exports/statements.html"', PAGE,
                         "a destination path is not a download")
        self.assertIn("async function exportStatements()", PAGE)
        self.assertIn("ensureSavedCase()", PAGE,
                      "the statements come from a saved case, as every download does")

    def test_e_dl_009__a_delivered_tool_shows_its_downloads_on_its_own_page(self):
        """The tool page a student ran the calculation on carries the result and its files.

        Reported by the owner: the downloads sat at the bottom of the containers
        "except for Tool - management accounts and others".  A delivered run used to
        leave the tool page with no result at all, so the only route to a file was the
        Result page; now the report and the download row are rendered there.
        """
        self.assertIn('id="toolresult"', PAGE)
        for button in ('id="toolsavecase"', 'id="toolxlsx"', 'id="tooldocx"',
                       'id="toolexplain"', 'id="toolopenresult"'):
            self.assertIn(button, PAGE)
        self.assertIn('id="toolstatements"', PAGE,
                      "management accounts can download its statements from its own page")
        self.assertIn("if (delivered) {", PAGE)

    def test_e_dl_010__every_saved_file_is_named_subject_tile_and_a_number(self):
        """The owner's format: subject_subtile_NNN.ext, on every file the page saves."""
        self.assertIn("function downloadName(tile, filename, subject)", PAGE)
        self.assertIn("function nextFileNumber(subject, tile)", PAGE)
        self.assertIn('padStart(3, "0")', PAGE)
        self.assertIn("link.download = downloadName(", PAGE)
        self.assertIn('downloadName("Statements"', PAGE,
                      "the statements tile names its files Accounting_Statements_NNN")
        self.assertIn('downloadName(d.problem_label', PAGE,
                      "an economics file is named Economics_<problem>_NNN")
        self.assertIn('downloadName(b.title', PAGE,
                      "a case report is named by its own title")

    def test_e_dl_003__the_pairs_the_page_requests_are_pairs_the_core_allows(self):
        for deliverable, kind in (("workpapers", "xlsx"), ("submission", "docx"),
                                  ("submission", "html"), ("worksheet", "docx"),
                                  ("statements", "docx"), ("statements", "html")):
            deliverables.check_pair(deliverable, kind)  # raises on an impossible pair

    def test_e_dl_004__the_export_route_still_serves_the_bytes_and_hides_the_path(self):
        self.assertIn('if body.get("download"):', API,
                      "the route must keep a bytes mode the browser can use")
        self.assertIn('result.pop("path", None)', API,
                      "a download response never advertises a server path")


if __name__ == "__main__":
    unittest.main()
