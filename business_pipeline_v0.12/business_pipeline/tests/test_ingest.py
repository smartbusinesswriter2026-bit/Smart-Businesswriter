import sys, io, base64, unittest, zipfile
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import ingest
from bp.ingest import read_table, IngestError

CSV = b"name,score,when\nAda,10,2026-01-05\nBo,12.5,\nCy,,2026-02-01\n"


def xlsx(sheet_xml, shared=None, styles=None):
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        if shared: z.writestr("xl/sharedStrings.xml", shared)
        if styles: z.writestr("xl/styles.xml", styles)
    return b.getvalue()


SHEET = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
         '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c><c r="C1" t="s"><v>2</v></c></row>'
         '<row r="2"><c r="A2" t="s"><v>3</v></c><c r="B2"><v>10</v></c><c r="C2" s="1"><v>46027</v></c></row>'
         '<row r="3"><c r="A3" t="s"><v>4</v></c><c r="B3"><v>12.5</v></c></row>'
         '</sheetData></worksheet>')
SHARED = '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><si><t>name</t></si><si><t>score</t></si><si><t>when</t></si><si><t>Ada</t></si><si><t>Bo</t></si></sst>'
STYLES = '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>'


class Csv(unittest.TestCase):
    def test_reads_a_typed_table_with_provenance(self):
        t = read_table("scores.csv", CSV)
        self.assertEqual((t["kind"], t["n_rows"], t["n_cols"]), ("csv", 3, 3))
        self.assertEqual([(c["name"], c["type"], c["n_missing"]) for c in t["columns"]],
                         [("name", "text", 0), ("score", "number", 1), ("when", "date", 1)])
        self.assertEqual(t["rows"][0], ["Ada", "10", "2026-01-05"]); self.assertIsNone(t["rows"][1][2])
        self.assertEqual(t["sha256"], ingest.sha(CSV)); self.assertEqual(t["provenance"]["kind"], "sourced")

    def test_delimiter_and_encoding_are_detected(self):
        t = read_table("semi.csv", "a;b\n1;2\n3;4\n".encode("cp1252"))
        self.assertEqual((t["delimiter"], t["n_cols"]), (";", 2))
        t = read_table("bom.csv", "\ufeffa,b\n1,2\n".encode("utf-8"))
        self.assertEqual(t["columns"][0]["name"], "a")

    def test_mixed_column_is_labelled_not_coerced(self):
        t = read_table("mixed.csv", b"value\n1\nx\n2\n")
        self.assertEqual(t["columns"][0]["type"], "mixed")
        self.assertEqual(t["rows"], [["1"], ["x"], ["2"]])

    def test_headers_must_be_present_and_unique(self):
        for raw in (b"a,a\n1,2\n", b"a,,c\n1,2,3\n", b""):
            with self.assertRaises(IngestError): read_table("x.csv", raw)

    def test_caps_are_refused_not_truncated(self):
        many = ("a\n" + "\n".join(str(i) for i in range(ingest.MAX_ROWS + 2))).encode()
        with self.assertRaises(IngestError) as cm: read_table("big.csv", many)
        self.assertIn("too many data rows", str(cm.exception))


class Xlsx(unittest.TestCase):
    def test_reads_shared_strings_numbers_and_dates(self):
        t = read_table("book.xlsx", xlsx(SHEET, SHARED, STYLES))
        self.assertEqual((t["kind"], t["sheet"], t["n_rows"], t["n_cols"]), ("xlsx", "Data", 2, 3))
        self.assertEqual([(c["name"], c["type"]) for c in t["columns"]], [("name", "text"), ("score", "number"), ("when", "date")])
        self.assertEqual(t["rows"][0], ["Ada", "10", "2026-01-05"])

    def test_corrupt_or_empty_workbooks_are_refused(self):
        with self.assertRaises(IngestError): read_table("bad.xlsx", b"not a zip")
        with self.assertRaises(IngestError): read_table("empty.xlsx", xlsx('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>'))


class Refusals(unittest.TestCase):
    def test_pdf_scan_and_spss_are_refused_with_reasons(self):
        for name, raw, words in (("a.pdf", b"%PDF-1.7", "PDF ingestion is not implemented"), ("scan.png", b"\x89PNG", "unsupported file type"),
                                 ("d.sav", b"abc", "SPSS")):
            with self.assertRaises(IngestError) as cm: read_table(name, raw)
            self.assertIn(words, str(cm.exception))

    def test_api_decoder_validates_shape_and_base64(self):
        t = ingest.decode_request({"filename": "scores.csv", "content_base64": base64.b64encode(CSV).decode()})
        self.assertEqual(t["n_rows"], 3)
        for body in ({}, {"filename": "x.csv"}, {"content_base64": "abc"}, {"filename": "x.csv", "content_base64": "!!notbase64!!"}):
            with self.assertRaises(IngestError): ingest.decode_request(body)

    def test_deterministic(self):
        a, b = read_table("scores.csv", CSV), read_table("scores.csv", CSV)
        self.assertEqual((a["rows"], a["columns"], a["sha256"]), (b["rows"], b["columns"], b["sha256"]))


if __name__ == "__main__":
    unittest.main()
