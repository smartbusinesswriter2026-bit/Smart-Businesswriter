"""A chart in a spreadsheet, as a real drawing anchored to a cell.

The workbook is checked the way Excel reads it: the worksheet's `drawing` child
in the position `CT_Worksheet` requires, a drawing part that resolves to its
picture, every part declared once, and stable bytes.  A figure with no PNG is
skipped, so a workbook never carries a picture it cannot show.
"""

import base64
import io
import os
import posixpath
import sys
import unittest
import xml.etree.ElementTree as ET
import zipfile

sys.path.insert(0, "src")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import spreadsheets  # noqa: E402

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def sheets_with_figure(png=PNG_1X1):
    return [
        ("Summary", [["A"], ["B"]], {}),
        ("Results", [["Metric", "Value"], ["Revenue", 10]],
         {"figures": [{"png": png, "row": 4}]}),
    ]


def parts(data):
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def fake_png(width, height):
    """A PNG header with a declared size, for the sizing rules only."""
    return (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
            + width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x06\x00\x00\x00")


class DrawingTest(unittest.TestCase):

    def test_a_figure_reaches_the_sheet_as_a_drawing(self):
        names = parts(spreadsheets.write_xlsx(sheets_with_figure()))
        self.assertIn("xl/drawings/drawing1.xml", names)
        self.assertIn("xl/drawings/_rels/drawing1.xml.rels", names)
        self.assertIn("xl/worksheets/_rels/sheet2.xml.rels", names)
        self.assertIn("xl/media/image1.png", names)

    def test_the_worksheet_declares_the_drawing(self):
        names = parts(spreadsheets.write_xlsx(sheets_with_figure()))
        sheet = names["xl/worksheets/sheet2.xml"]
        self.assertIn(b'<drawing r:id="rId1"/>', sheet)
        # the drawing child comes after sheetData, as CT_Worksheet requires
        self.assertGreater(sheet.index(b"<drawing"), sheet.index(b"</sheetData>"))
        self.assertLess(sheet.index(b"<drawing"), sheet.index(b"</worksheet>"))

    def test_the_sheet_without_a_figure_carries_no_drawing(self):
        names = parts(spreadsheets.write_xlsx(sheets_with_figure()))
        self.assertNotIn(b"<drawing", names["xl/worksheets/sheet1.xml"])
        self.assertNotIn("xl/worksheets/_rels/sheet1.xml.rels", names)

    def test_every_part_is_well_formed_xml(self):
        for name, body in parts(spreadsheets.write_xlsx(sheets_with_figure())).items():
            if name.endswith(".xml") or name.endswith(".rels"):
                ET.fromstring(body)

    def test_every_relationship_resolves_to_a_part(self):
        names = parts(spreadsheets.write_xlsx(sheets_with_figure()))
        for name, body in names.items():
            if not name.endswith(".rels"):
                continue
            base = posixpath.dirname(posixpath.dirname(name))
            for relationship in ET.fromstring(body):
                target = relationship.get("Target")
                resolved = posixpath.normpath(posixpath.join(base, target))
                self.assertIn(resolved, names, "%s -> %s" % (name, target))

    def test_the_content_types_declare_the_picture_and_the_drawing(self):
        declared = parts(spreadsheets.write_xlsx(sheets_with_figure()))["[Content_Types].xml"].decode()
        self.assertIn('Extension="png"', declared)
        self.assertIn("/xl/drawings/drawing1.xml", declared)

    def test_the_bytes_are_stable(self):
        one = spreadsheets.write_xlsx(sheets_with_figure())
        two = spreadsheets.write_xlsx(sheets_with_figure())
        self.assertEqual(one, two)

    def test_a_figure_with_no_png_is_skipped(self):
        sheets = [("Results", [["A"]], {"figures": [{"png": None, "row": 2}]})]
        names = parts(spreadsheets.write_xlsx(sheets))
        self.assertNotIn("xl/drawings/drawing1.xml", names)
        self.assertNotIn(b"<drawing", names["xl/worksheets/sheet1.xml"])

    def test_a_workbook_with_no_figure_keeps_its_old_bytes(self):
        plain = [("Summary", [["A"], ["B"]], {}),
                 ("Results", [["Metric", "Value"], ["Revenue", 10]], {})]
        names = parts(spreadsheets.write_xlsx(plain))
        self.assertFalse([name for name in names if "drawing" in name or "media" in name])

    def test_a_chart_is_capped_to_the_sheet_width_and_keeps_its_aspect(self):
        width, height = spreadsheets._drawing_ext(fake_png(1440, 600))
        self.assertEqual(width, spreadsheets._MAX_IMAGE_EMU)
        self.assertEqual(height, int(spreadsheets._MAX_IMAGE_EMU * 600 / 1440))

    def test_two_figures_on_one_sheet_are_two_anchors_and_two_pictures(self):
        sheets = [("Results", [["A"]],
                   {"figures": [{"png": PNG_1X1, "row": 2}, {"png": PNG_1X1, "row": 6}]})]
        names = parts(spreadsheets.write_xlsx(sheets))
        drawing = names["xl/drawings/drawing1.xml"]
        self.assertEqual(drawing.count(b"<xdr:oneCellAnchor>"), 2)
        self.assertIn("xl/media/image1.png", names)
        self.assertIn("xl/media/image2.png", names)


class BundleTest(unittest.TestCase):

    def test_a_bundle_carries_a_figure_when_one_is_supplied(self):
        bundle = product_fixtures.make_bundle()
        figure = {"id": "fig_abc123", "place": "",
                  "asset": {"png": PNG_1X1}, "rows": [("Net present value", "50.00")]}
        names = parts(spreadsheets.to_xlsx(bundle, [figure]))
        self.assertIn("xl/media/image1.png", names)
        self.assertTrue([name for name in names if name.startswith("xl/drawings/")])

    def test_a_figure_with_no_png_leaves_the_workbook_alone(self):
        bundle = product_fixtures.make_bundle()
        plain = spreadsheets.to_xlsx(bundle)
        figure = {"id": "fig_abc123", "place": "", "asset": {"png": None}, "rows": []}
        self.assertEqual(spreadsheets.to_xlsx(bundle, [figure]), plain)


if __name__ == "__main__":
    unittest.main()
