"""The academic .docx renderer: title page, heading styles and page numbering."""

import datetime
import io
import re
import unittest
import zipfile

from bp.product import docx


def _parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name).decode("utf-8") for name in archive.namelist()}


class AcademicDocxTest(unittest.TestCase):
    def setUp(self):
        self.data = docx.render_academic(
            "Porter's Five Forces: A Case",
            [{"heading": "Introduction", "level": 1, "lines": ["Body paragraph."]},
             {"heading": "Industry rivalry", "level": 2, "lines": ["Force paragraph."]},
             {"heading": "References", "level": 1, "lines": ["Lovelace, A. (2024). Competition."]}],
            "apa", byline=["A Student", "Example University", "BUS301", "Dr A Instructor"])
        self.parts = _parts(self.data)

    def test_the_title_page_carries_the_title_then_the_byline_then_the_date(self):
        body = self.parts["word/document.xml"]
        paragraphs = re.findall(r"<w:p>.*?</w:p>", body, re.S)
        texts = [re.sub(r"<[^>]+>", "", p).strip() for p in paragraphs]
        title = "Porter's Five Forces: A Case"
        self.assertEqual(texts.count(title), 2)  # title page and first page of text
        first = texts.index(title)
        self.assertEqual(texts[:first], ["", "", ""])  # title begins three lines down
        self.assertEqual(texts[first + 2:first + 6],
                         ["A Student", "Example University", "BUS301", "Dr A Instructor"])
        self.assertEqual(texts[first + 6],
                         datetime.datetime.now(datetime.timezone.utc).strftime("%d %B %Y"))

    def test_the_title_page_is_followed_by_a_page_break(self):
        body = self.parts["word/document.xml"]
        self.assertIn('<w:br w:type="page"/>', body)
        break_at = body.index('<w:br w:type="page"/>')
        self.assertLess(body.index("Dr A Instructor"), break_at)
        self.assertGreater(body.index("Introduction"), break_at)

    def test_headings_use_real_word_styles(self):
        body = self.parts["word/document.xml"]
        self.assertIn('<w:pStyle w:val="Heading1"/>', body)
        self.assertIn('<w:pStyle w:val="Heading2"/>', body)
        styles = self.parts["word/styles.xml"]
        self.assertIn('w:styleId="Heading1"', styles)
        self.assertIn('w:styleId="Heading2"', styles)
        self.assertIn('<w:outlineLvl w:val="0"/>', styles)
        self.assertIn('<w:outlineLvl w:val="1"/>', styles)

    def test_the_page_number_is_in_the_header_not_the_footer(self):
        body = self.parts["word/document.xml"]
        self.assertIn('<w:headerReference w:type="default" r:id="rId1"/>', body)
        self.assertNotIn("footerReference", body)
        header = self.parts["word/header1.xml"]
        self.assertIn("PAGE", header)
        self.assertIn('<w:jc w:val="right"/>', header)
        rels = self.parts["word/_rels/document.xml.rels"]
        self.assertIn("header1.xml", rels)
        self.assertIn("styles.xml", rels)

    def test_a_paper_without_a_byline_still_renders_a_clean_title_page(self):
        data = docx.render_academic("A Title", [{"heading": "Introduction", "level": 1,
                                                 "lines": ["Body."]}], "apa")
        body = _parts(data)["word/document.xml"]
        self.assertNotIn("[your name]", body)
        self.assertIn("A Title", body)

    def test_the_same_title_and_sections_render_identical_bytes(self):
        again = docx.render_academic(
            "Porter's Five Forces: A Case",
            [{"heading": "Introduction", "level": 1, "lines": ["Body paragraph."]},
             {"heading": "Industry rivalry", "level": 2, "lines": ["Force paragraph."]},
             {"heading": "References", "level": 1, "lines": ["Lovelace, A. (2024). Competition."]}],
            "apa", byline=["A Student", "Example University", "BUS301", "Dr A Instructor"])
        self.assertEqual(self.data, again)


if __name__ == "__main__":
    unittest.main()
