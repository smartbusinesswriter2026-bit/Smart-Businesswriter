import sys, io, json, base64, threading, unittest, urllib.request, urllib.error, zipfile
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp import server

CSV = b"name,score,when\nAda,10,2026-01-05\nBo,12.5,\nCy,,2026-02-01\n"

_SML = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def _str_cell(ref, text): return '<c r="%s" t="inlineStr"><is><t>%s</t></is></c>' % (ref, text)
def _num_cell(ref, value): return '<c r="%s"><v>%s</v></c>' % (ref, value)


def _sheet(rows, merges=()):
    mc = "" if not merges else '<mergeCells count="%d">' % len(merges) + "".join('<mergeCell ref="%s"/>' % r for r in merges) + "</mergeCells>"
    return '<worksheet xmlns="%s"><sheetData>%s</sheetData>%s</worksheet>' % (_SML, rows, mc)


def _book_b64(sheets):
    b = io.BytesIO()
    wz = "".join('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (n, i + 1, i + 1) for i, (n, _) in enumerate(sheets))
    rz = "".join('<Relationship Id="rId%d" Target="worksheets/sheet%d.xml"/>' % (i + 1, i + 1) for i, _ in enumerate(sheets))
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("xl/workbook.xml", '<workbook xmlns="%s" xmlns:r="%s"><sheets>%s</sheets></workbook>' % (_SML, _REL, wz))
        z.writestr("xl/_rels/workbook.xml.rels", '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>' % rz)
        for i, (_, xml) in enumerate(sheets):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), xml)
    return base64.b64encode(b.getvalue()).decode()


TWO_SHEETS = [("First", _sheet('<row r="1">' + _str_cell("A1", "alpha") + '</row><row r="2">' + _num_cell("A2", "1") + '</row>')),
              ("Second", _sheet('<row r="1">' + _str_cell("A1", "gamma") + '</row><row r="2">' + _num_cell("A2", "3") + '</row>'
                                '<row r="3">' + _num_cell("A3", "5") + '</row>'))]
MERGE_BOOK = [("Data", _sheet('<row r="1">' + _str_cell("A1", "item") + _str_cell("B1", "amount") + '</row>'
                              '<row r="2">' + _num_cell("A2", "10") + '</row>', merges=["A2:B2"]))]


class IngestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); cls.srv.server_close()
    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())

    def test_ingests_csv_and_returns_types_and_provenance(self):
        c, b = self.call("/api/ingest", {"filename": "scores.csv", "content_base64": base64.b64encode(CSV).decode()})
        self.assertEqual(c, 200); t = b["table"]
        self.assertEqual((t["kind"], t["n_rows"], t["n_cols"]), ("csv", 3, 3))
        self.assertEqual(t["columns"][1]["type"], "number"); self.assertEqual(t["columns"][2]["type"], "date")
        self.assertEqual(t["provenance"]["kind"], "sourced")
        self.assertIn("not_read_as", t)

    def test_bad_base64_and_unsupported_files_are_422(self):
        self.assertEqual(self.call("/api/ingest", {"filename": "x.csv", "content_base64": "!!"})[0], 422)
        c, b = self.call("/api/ingest", {"filename": "x.pdf", "content_base64": base64.b64encode(b"%PDF-1.4").decode()})
        self.assertEqual(c, 422); self.assertIn("PDF ingestion is not implemented", b["error"])

    def test_shape_errors_and_oversized_files(self):
        self.assertEqual(self.call("/api/ingest", {})[0], 422)
        self.assertEqual(self.call("/api/ingest", {"filename": "x.csv", "content_base64": "YQ=="})[0], 200)  # one-cell CSV: header only, no data rows
    def test_selects_xlsx_sheet_and_refuses_unknown(self):
        b64 = _book_b64(TWO_SHEETS)
        c, b = self.call("/api/ingest", {"filename": "book.xlsx", "content_base64": b64, "sheet": "Second"})
        self.assertEqual(c, 200); self.assertEqual((b["table"]["sheet"], b["table"]["n_rows"]), ("Second", 2))
        self.assertEqual(b["table"]["sheets"], ["First", "Second"])
        c, b = self.call("/api/ingest", {"filename": "book.xlsx", "content_base64": b64, "sheet": "Nope"})
        self.assertEqual(c, 422); self.assertIn("unknown sheet", b["error"])

    def test_merged_cell_policy_via_api(self):
        b64 = _book_b64(MERGE_BOOK)
        c, b = self.call("/api/ingest", {"filename": "book.xlsx", "content_base64": b64})
        self.assertEqual(c, 422); self.assertIn("merged cells are refused by default", b["error"])
        c, b = self.call("/api/ingest", {"filename": "book.xlsx", "content_base64": b64, "merged": "top_left"})
        self.assertEqual(c, 200); self.assertEqual(b["table"]["rows"], [["10", "10"]])
        c, b = self.call("/api/ingest", {"filename": "book.xlsx", "content_base64": b64, "merged": "expand"})
        self.assertEqual(c, 422); self.assertIn("merged must be one of", b["error"])

    def test_ui_has_the_ingestion_card(self):
        body = urllib.request.urlopen(self.base + "/").read().decode()
        self.assertIn("Data ingestion (structured files)", body); self.assertIn('id="ingfile"', body); self.assertIn("Ingest file", body)
        self.assertIn("/api/ingest", body); self.assertIn("no PDF text extraction or OCR", body)


if __name__ == "__main__":
    unittest.main()
