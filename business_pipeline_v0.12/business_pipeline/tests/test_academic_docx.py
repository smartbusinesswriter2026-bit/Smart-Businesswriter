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
        self.assertEqual(texts[first + 2:first + 6],
                         ["A Student", "Example University", "BUS301", "Dr A Instructor"])
        self.assertEqual(texts[first + 6],
                         datetime.datetime.now(datetime.timezone.utc).strftime("%d %B %Y"))

    def test_the_title_page_is_vertically_centred_in_its_own_section(self):
        body = self.parts["word/document.xml"]
        self.assertIn('<w:vAlign w:val="center"/>', body)
        centre = body.index('<w:vAlign w:val="center"/>')
        self.assertGreater(body.index("Dr A Instructor"), centre - 4000)
        # the body is a second section, so it starts on a new page uncentred
        self.assertEqual(body.count("<w:sectPr>"), 2)
        self.assertNotIn('<w:vAlign w:val="center"/></w:sectPr>', body)

    def test_the_reference_list_starts_on_its_own_page(self):
        body = self.parts["word/document.xml"]
        start = body.rindex("<w:p>", 0, body.index(">References<"))
        paragraph = body[start:body.index(">References<")]
        self.assertIn("<w:pageBreakBefore/>", paragraph)

    def test_the_title_page_section_ends_before_the_body(self):
        body = self.parts["word/document.xml"]
        centre = body.index('<w:vAlign w:val="center"/>')
        self.assertLess(body.index("Dr A Instructor"), centre)
        self.assertLess(centre, body.index("Introduction"))

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
