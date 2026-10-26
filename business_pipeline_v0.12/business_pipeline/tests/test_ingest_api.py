import sys, json, base64, threading, unittest, urllib.request, urllib.error
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp import server

CSV = b"name,score,when\nAda,10,2026-01-05\nBo,12.5,\nCy,,2026-02-01\n"


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
    def test_ui_has_the_ingestion_card(self):
        body = urllib.request.urlopen(self.base + "/").read().decode()
        self.assertIn("Data ingestion (structured files)", body); self.assertIn('id="ingfile"', body); self.assertIn("Ingest file", body)
        self.assertIn("/api/ingest", body); self.assertIn("no PDF text extraction or OCR", body)


if __name__ == "__main__":
    unittest.main()
