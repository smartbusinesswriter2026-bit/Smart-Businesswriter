"""The report is assembled from retrieved sources and exports as Word."""

import base64
import io
import unittest
import zipfile

import sys
sys.path.insert(0, "src")

from bp.product import api, writing  # noqa: E402


SOURCES = [
    {"title": "Competition in grocery retail", "abstract": "New entrants and price competition changed the market. "
                                                           "A second sentence.",
     "authors": "Ada Lovelace", "year": 2024, "venue": "Journal of Retailing", "doi": "10.1/grocery"},
    {"title": "Consumer demand after the pandemic", "abstract": "Demand shifted towards online delivery.",
     "authors": "Grace Hopper", "year": 2023, "venue": "Marketing Science", "doi": "10.1/demand"},
]


class ComposeTest(unittest.TestCase):
    def setUp(self):
        self.report = writing.compose("template_swot", "competition in grocery retail", SOURCES)

    def test_report_has_the_expected_sections_and_citations(self):
        headings = [heading for heading, _lines in self.report["sections"]]
        self.assertIn("Purpose and method", headings)
        self.assertIn("Summary", headings)
        self.assertIn("Gaps and limits", headings)
        self.assertIn("References", headings)
        self.assertEqual(len(self.report["references"]), 2)
        text = "\n".join(line for _heading, lines in self.report["sections"] for line in lines)
        self.assertIn("Competition in grocery retail", text)
        self.assertIn("Lovelace, A.", text)
        self.assertIn("Hopper, G.", text)
        self.assertNotIn("[E1]", text)
        self.assertNotIn("provenance", text)

    def test_an_empty_dimension_is_a_gap_not_a_conclusion(self):
        section = dict((heading, lines) for heading, lines in self.report["sections"])
        self.assertTrue(any("gap" in line.lower() for line in section["Weaknesses"]))

    def test_apa_and_harvard_references_differ(self):
        apa = writing.compose("template_swot", "competition in grocery retail", SOURCES, style="apa")
        harvard = writing.compose("template_swot", "competition in grocery retail", SOURCES, style="harvard")
        self.assertEqual(apa["style"], "apa")
        self.assertEqual(harvard["style"], "harvard")
        apa_headings = [heading for heading, _lines in apa["sections"]]
        harvard_headings = [heading for heading, _lines in harvard["sections"]]
        self.assertIn("References", apa_headings)
        self.assertIn("Bibliography", harvard_headings)
        apa_text = "\n".join(apa["references"])
        harvard_text = "\n".join(harvard["references"])
        self.assertIn("Lovelace, A. (2024).", apa_text)
        self.assertIn("Lovelace, A. (2024)", harvard_text)
        self.assertIn("doi: 10.1/grocery", harvard_text)
        evidence = "\n".join(line for _h, lines in apa["sections"] for line in lines)
        self.assertIn("(Lovelace, 2024)", evidence)

    def test_a_group_author_is_not_split_into_a_family_and_initial(self):
        source = {"authors_list": ["World Bank"], "authors": "World Bank", "year": 2026,
                  "title": "Islamic Republic of Iran: Overview", "venue": "",
                  "url": "https://www.worldbank.org/ext/en/country/iran"}
        self.assertEqual(writing.in_text(source, "apa"), "(World Bank, 2026)")
        reference = writing.reference(source, "apa")
        self.assertIn("World Bank (2026)", reference)
        self.assertNotIn("Bank, W.", reference)

    def test_word_bytes_are_a_real_docx_and_deterministic(self):
        first = writing.docx_bytes(self.report)
        second = writing.docx_bytes(self.report)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            self.assertIn("word/footer1.xml", archive.namelist())
            document = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Research report", document)
        self.assertIn("Competition in grocery retail", document)
        self.assertIn("Times New Roman", document)
        self.assertIn('w:pgMar', document)
        self.assertNotIn("Consolas", document)  # a written report uses the normal face

    def test_filename_is_safe(self):
        name = writing.filename(self.report)
        self.assertTrue(name.endswith(".docx"))
        self.assertNotIn(" ", name)
        self.assertNotIn("/", name)


class ReportRouteTest(unittest.TestCase):
    def test_the_route_returns_the_report_and_downloadable_word_bytes(self):
        body = {"template": "template_swot", "objective": "competition in grocery retail", "sources": SOURCES}
        status, payload = api.handle("POST", "/api/cases/worksheets/report", body)
        self.assertEqual(status, 200)
        self.assertIn("report", payload)
        self.assertTrue(payload["docx"]["filename"].endswith(".docx"))
        data = base64.b64decode(payload["docx"]["data"])
        self.assertTrue(data.startswith(b"PK"))
        self.assertEqual(len(payload["docx"]["sha256"]), 64)
        harvard = api.handle("POST", "/api/cases/worksheets/report", dict(body, style="harvard"))[1]
        self.assertEqual(harvard["report"]["style"], "harvard")
        self.assertIn("Bibliography", [heading for heading, _lines in harvard["report"]["sections"]])

    def test_the_route_validates_the_template_and_the_draft(self):
        body = {"template": "template_vrio", "objective": "x", "sources": SOURCES}
        self.assertEqual(api.handle("POST", "/api/cases/worksheets/report", body)[0], 422)
        self.assertEqual(api.handle("POST", "/api/cases/worksheets/report",
                                    {"template": "template_swot", "sources": SOURCES, "draft": "no"})[0], 422)
        self.assertEqual(api.handle("GET", "/api/cases/worksheets/report")[0], 405)


if __name__ == "__main__":
    unittest.main()
