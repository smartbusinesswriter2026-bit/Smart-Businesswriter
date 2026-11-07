"""The statements tile's Excel export: a workbook Excel can open.

`bp.product.xlsx` is the export the tile offers the student (`POST
/api/cases/statements/{id}/export` with `format: "xlsx"`).  It writes the workbook by
hand, with `zipfile` and XML only, because the product layer may not import a
third-party package (`tests/test_product_boundary.py`).

A hand-rolled workbook fails in a way no other test catches: the file is a valid zip
of valid XML, so `openpyxl` reads it, but Excel refuses it - "we found a problem with
some content" and an empty workbook.  Excel enforces the OPC package rules and the
`CT_Worksheet` element order; openpyxl does not.

So these tests check the package the way Excel reads it:

* every part is declared exactly once in `[Content_Types].xml`;
* every relationship points at a part that exists;
* the sheet names are unique and legal;
* the worksheet children are in the order `CT_Worksheet` requires;
* and the workbook itself is the one the render brief asks for: one sheet per
  requested statement, then `Working`, then `Notes`, with typed amounts.

`qa/manual/audit_xlsx_structure.py` is the same audit as a probe, and
`qa/manual/excel_open_check.ps1` opens the file in Excel itself.
"""

import io
import os
import sys
import unittest
import zipfile
from collections import Counter
from decimal import Decimal
from xml.etree import ElementTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.join(ROOT, "src"), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp.product import xlsx as xlsx_export  # noqa: E402
import product_statements_fixture as fixture  # noqa: E402
import xlsx_read  # noqa: E402

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

#: `CT_Worksheet`'s element sequence (ECMA-376 Part 1, 18.3.1.99).  Excel rejects a
#: worksheet whose children are out of this order.
WORKSHEET_ORDER = (
    "sheetPr", "dimension", "sheetViews", "sheetFormatPr", "cols", "sheetData",
    "sheetCalcPr", "sheetProtection", "protectedRanges", "scenarios", "autoFilter",
    "sortState", "dataConsolidate", "customSheetViews", "mergeCells", "phoneticPr",
    "conditionalFormatting", "dataValidations", "hyperlinks", "printOptions",
    "pageMargins", "pageSetup", "headerFooter", "rowBreaks", "colBreaks",
    "customProperties", "cellWatches", "ignoredErrors", "smartTags", "drawing",
)

#: The sheet names the render brief asks for (docs/MINIMAX_STATEMENT_RENDER.md §9).
STATEMENT_SHEETS = ("Income statement", "Changes in equity", "Balance sheet", "Cash flow")


def _local(tag):
    return tag.split("}")[-1] if "}" in tag else tag


def _parts(data):
    """The workbook's parts, as {name: bytes}."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


class PackageTest(unittest.TestCase):
    """The package rules Excel enforces when it opens the file."""

    @classmethod
    def setUpClass(cls):
        cls.record = fixture.load()
        cls.data = xlsx_export.render_bytes(cls.record)
        cls.parts = _parts(cls.data)

    def test_it_is_a_readable_package(self):
        self.assertIn("[Content_Types].xml", self.parts)
        self.assertIn("xl/workbook.xml", self.parts)
        self.assertIn("_rels/.rels", self.parts)

    def test_every_part_is_declared_exactly_once(self):
        """A part declared twice is a package Excel refuses to open.

        The content type stream may carry one `Override` per part name; a second one
        for the same part makes the package invalid.
        """
        root = ElementTree.fromstring(self.parts["[Content_Types].xml"])
        overrides = [node.get("PartName") for node in root.findall("{%s}Override" % CT)]
        counted = Counter(overrides)
        duplicated = sorted(name for name, count in counted.items() if count > 1)
        self.assertEqual(duplicated, [], "a part is declared more than once: %s" % duplicated)

    def test_every_part_has_a_content_type(self):
        root = ElementTree.fromstring(self.parts["[Content_Types].xml"])
        overrides = {node.get("PartName") for node in root.findall("{%s}Override" % CT)}
        defaults = {node.get("Extension") for node in root.findall("{%s}Default" % CT)}
        for name in self.parts:
            if name == "[Content_Types].xml":
                continue
            extension = name.rsplit(".", 1)[-1].lower()
            self.assertTrue("/" + name in overrides or extension in defaults,
                            "%s has no content type" % name)

    def test_every_relationship_points_at_a_part_that_exists(self):
        for rels_name in [name for name in self.parts if name.endswith(".rels")]:
            base = rels_name.rsplit("_rels/", 1)[0]
            root = ElementTree.fromstring(self.parts[rels_name])
            for link in root.findall("{%s}Relationship" % PKG):
                if link.get("TargetMode") == "External":
                    continue
                target = link.get("Target") or ""
                if target.startswith("/"):
                    target = target.lstrip("/")
                else:
                    target = base + target
                self.assertIn(target, self.parts,
                              "%s points at %s, which is not in the package" % (rels_name, target))

    def test_the_sheet_names_are_unique_and_legal(self):
        root = ElementTree.fromstring(self.parts["xl/workbook.xml"])
        names = [sheet.get("name") for sheet in root.iter("{%s}sheet" % MAIN)]
        counted = Counter(names)
        self.assertEqual(sorted(name for name, count in counted.items() if count > 1), [],
                         "a sheet name is used twice: %s" % names)
        for name in names:
            self.assertLessEqual(len(name), 31, "%r is longer than 31 characters" % name)
            for bad in "[]:*?/\\":
                self.assertNotIn(bad, name, "%r carries the illegal character %r" % (name, bad))

    def test_every_sheet_has_a_relationship(self):
        root = ElementTree.fromstring(self.parts["xl/workbook.xml"])
        rels = ElementTree.fromstring(self.parts["xl/_rels/workbook.xml.rels"])
        known = {link.get("Id") for link in rels.findall("{%s}Relationship" % PKG)}
        for sheet in root.iter("{%s}sheet" % MAIN):
            self.assertIn(sheet.get("{%s}id" % REL), known,
                          "the sheet %r has no relationship" % sheet.get("name"))

    def test_the_worksheet_children_are_in_the_order_excel_requires(self):
        """`cols` comes before `sheetData`; a worksheet with them the other way round is rejected."""
        for name in sorted(part for part in self.parts if part.startswith("xl/worksheets/")):
            root = ElementTree.fromstring(self.parts[name])
            children = [_local(child.tag) for child in root]
            positions = []
            for child in children:
                self.assertIn(child, WORKSHEET_ORDER, "%s: unknown child <%s>" % (name, child))
                positions.append(WORKSHEET_ORDER.index(child))
            self.assertEqual(positions, sorted(positions),
                             "%s: the children are out of order: %s" % (name, children))

    def test_the_workbook_declares_its_own_parts(self):
        rels = ElementTree.fromstring(self.parts["xl/_rels/workbook.xml.rels"])
        kinds = Counter(link.get("Type").rsplit("/", 1)[-1] for link in rels.findall("{%s}Relationship" % PKG))
        self.assertGreaterEqual(kinds.get("worksheet", 0), 1)
        self.assertEqual(kinds.get("styles", 0), 1, "the workbook has no styles relationship")

    def test_the_package_points_at_the_workbook(self):
        root = ElementTree.fromstring(self.parts["_rels/.rels"])
        targets = [link.get("Target") for link in root.findall("{%s}Relationship" % PKG)]
        self.assertIn("xl/workbook.xml", targets)


class WorkbookTest(unittest.TestCase):
    """The workbook the render brief asks for (docs/MINIMAX_STATEMENT_RENDER.md §9)."""

    @classmethod
    def setUpClass(cls):
        cls.record = fixture.load()
        cls.data = xlsx_export.render_bytes(cls.record)
        cls.sheets = xlsx_read.read(cls.data)
        cls.parts = _parts(cls.data)

    def test_it_has_one_sheet_per_requested_statement_then_working_and_notes(self):
        self.assertEqual(self.record["requested"], ["IS", "RE", "BS", "CF"])
        for name in STATEMENT_SHEETS:
            self.assertIn(name, self.sheets, "the workbook has no %r sheet" % name)
        self.assertIn("Working", self.sheets)
        self.assertIn("Notes", self.sheets)

    def test_the_amounts_are_numbers_and_not_text(self):
        """Column B is a number, so Excel can total and sort it."""
        rows = self.sheets["Income statement"]
        found = xlsx_read.numbers(rows)
        self.assertTrue(found, "no amount on the income statement is a number")
        self.assertIn(Decimal("200000"), found)

    def test_the_amount_format_carries_the_places_and_parentheses(self):
        root = ElementTree.fromstring(self.parts["xl/styles.xml"])
        formats = [node.get("formatCode") for node in root.iter("{%s}numFmt" % MAIN)]
        self.assertTrue(formats, "the workbook declares no number format")
        self.assertIn("#,##0.00;(#,##0.00)", formats,
                      "the amount format does not follow the record's places")

    def test_the_header_is_frozen_and_the_label_column_is_sized(self):
        for name in STATEMENT_SHEETS:
            root = ElementTree.fromstring(self.parts["xl/worksheets/sheet%d.xml"
                                                    % (STATEMENT_SHEETS.index(name) + 1)])
            views = root.find("{%s}sheetViews" % MAIN)
            self.assertIsNotNone(views, "%s has no sheet views" % name)
            self.assertIsNotNone(views.find("{%s}sheetView/{%s}pane" % (MAIN, MAIN)),
                                 "%s does not freeze the header row" % name)
            self.assertIsNotNone(root.find("{%s}cols" % MAIN), "%s has no column widths" % name)

    def test_no_cell_is_merged(self):
        for name in STATEMENT_SHEETS:
            root = ElementTree.fromstring(self.parts["xl/worksheets/sheet%d.xml"
                                                    % (STATEMENT_SHEETS.index(name) + 1)])
            self.assertIsNone(root.find("{%s}mergeCells" % MAIN), "%s merges cells" % name)

    def test_two_exports_of_the_same_record_are_identical(self):
        self.assertEqual(xlsx_export.render_bytes(self.record), self.data)

    def test_no_figure_is_invented_by_the_renderer(self):
        held = fixture.typed_numbers(self.record)
        rendered = set()
        for rows in self.sheets.values():
            rendered.update(xlsx_read.numbers(rows))
            rendered.update(xlsx_read.numbers_in_text(rows))
        invented = sorted(value for value in rendered if value not in held)
        self.assertEqual(invented, [], "the workbook shows figures the record does not hold")

    def test_the_figures_the_statements_must_show_are_there(self):
        shown = {}
        for rows in self.sheets.values():
            for row in rows:
                for index, cell in enumerate(row):
                    if not (isinstance(cell, str) and cell.strip()):
                        continue
                    value = xlsx_read.find(rows, cell)
                    if value is not None:
                        shown.setdefault(cell.strip().lower(), value)
        for label, value in (("total revenue", Decimal("200000")),
                              ("net income", Decimal("52575")),
                              ("total assets", Decimal("178100")),
                              ("total liabilities and equity", Decimal("178100"))):
            self.assertEqual(shown.get(label), value, "%s reads %s" % (label, shown.get(label)))


class PartialRequestTest(unittest.TestCase):
    """A statement that was not asked for is not a sheet."""

    def test_an_income_statement_only_request_produces_one_statement_sheet(self):
        record = fixture.record(["IS"])
        sheets = xlsx_read.read(xlsx_export.render_bytes(record))
        written = [name for name in sheets if name in STATEMENT_SHEETS]
        self.assertEqual(written, ["Income statement"])


class ThinRecordTest(unittest.TestCase):
    """A record whose appendix cannot supply the typed figures keeps its own statements.

    The tile stores thinner records too - a schedule, an analysis - whose appendix
    carries no `income_groups` or `balance_sheet_groups`.  The statements are still
    in the record, as the record rendered them, so the workbook shows them rather
    than a sheet of named gaps.

    The rendering is **not** re-typed into numbers: a figure the record only renders
    is not a figure the record holds as a value, and re-reading a rendered line is
    how a figure stops being the record's.
    """

    @classmethod
    def setUpClass(cls):
        cls.record = fixture.load()
        appendix = dict(cls.record["core"]["appendix"])
        for key in ("income_groups", "balance_sheet_groups", "cash_flow", "equity_statement"):
            appendix.pop(key, None)
        cls.thin = dict(cls.record)
        cls.thin["core"] = {"scalars": cls.record["core"]["scalars"], "appendix": appendix}
        cls.data = xlsx_export.render_bytes(cls.thin)
        cls.sheets = xlsx_read.read(cls.data)

    def test_the_statements_are_still_sheets(self):
        for name in STATEMENT_SHEETS:
            self.assertIn(name, self.sheets, "the workbook has no %r sheet" % name)

    def test_a_statement_the_appendix_cannot_supply_carries_the_records_own_lines(self):
        lines = [str(cell) for row in self.sheets["Income statement"] for cell in row]
        self.assertTrue(any("Total revenue" in line and "200,000.00" in line for line in lines),
                        "the income statement does not carry the record's own line")

    def test_no_figure_is_re_typed_out_of_the_record_s_text(self):
        """The income statement is the one the appendix cannot supply: it stays text."""
        self.assertEqual(xlsx_read.numbers(self.sheets["Income statement"]), [],
                         "the income statement re-typed a figure the record only renders")

    def test_a_statement_the_appendix_can_supply_stays_typed(self):
        self.assertTrue(xlsx_read.numbers(self.sheets["Balance sheet"]),
                        "the balance sheet lost the appendix's typed figures")

    def test_no_cell_claims_a_figure_the_record_does_not_hold(self):
        held = fixture.typed_numbers(self.thin)
        rendered = set()
        for rows in self.sheets.values():
            rendered.update(xlsx_read.numbers(rows))
            rendered.update(xlsx_read.numbers_in_text(rows))
        invented = sorted(value for value in rendered if value not in held)
        self.assertEqual(invented, [], "the workbook shows figures the record does not hold")

    def test_two_exports_of_the_same_record_are_identical(self):
        self.assertEqual(xlsx_export.render_bytes(self.thin), self.data)


if __name__ == "__main__":
    unittest.main()
