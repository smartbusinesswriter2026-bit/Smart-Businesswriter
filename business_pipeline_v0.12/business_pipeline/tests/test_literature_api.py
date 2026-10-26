import sys, json, threading, unittest, urllib.request, urllib.error
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp import server, literature

REC = {"title": "A Study of Markets", "authors": ("A. Author",), "year": "2024", "container": "Journal of Business"}

class FakeSource(literature.Source):
    name = "fake"
    def __init__(self, rec=None, exc=None): self.rec, self.exc = rec, exc
    def resolve(self, doi):
        if self.exc: raise self.exc
        return self.rec

class LiteratureApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old = (server.LITERATURE_SOURCES, server.LITERATURE_CALLS)
        server.LITERATURE_SOURCES = {"fake": FakeSource(REC)}; server.LITERATURE_CALLS = 0
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close(); server.LITERATURE_SOURCES, server.LITERATURE_CALLS = cls.old
    def call(self, path, body=None):
        req = urllib.request.Request(self.base + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, json.loads(e.read())
    def test_sources_are_listed_with_a_notice(self):
        c, b = self.call("/api/literature/sources"); self.assertEqual(c, 200); self.assertEqual([s["name"] for s in b["sources"]], ["fake"])
        self.assertIn("bibliographic", b["notice"]); self.assertIn("Crossref", server.LITERATURE_NOTICE)
    def test_verified_on_exact_title(self):
        c, b = self.call("/api/literature/verify", {"title": "A Study of Markets", "doi": "10.1/x", "source": "fake"})
        self.assertEqual((c, b["reference"]["status"], b["reference"]["year"], b["reference"]["authors"]), (200, "verified", "2024", ["A. Author"]))
    def test_title_mismatch_is_kept_unverified(self):
        c, b = self.call("/api/literature/verify", {"title": "Something Else", "doi": "10.1/x", "source": "fake"})
        self.assertEqual((c, b["reference"]["status"], b["reference"]["resolved_title"]), (200, "unverified_user_supplied", "A Study of Markets"))
    def test_no_doi_is_unverified_without_resolving(self):
        c, b = self.call("/api/literature/verify", {"title": "Any title", "source": "fake"})
        self.assertEqual((c, b["reference"]["status"], b["reference"]["source"]), (200, "unverified_user_supplied", None))
    def test_validation_and_source_errors(self):
        self.assertEqual(self.call("/api/literature/verify", {})[0], 400)
        self.assertEqual(self.call("/api/literature/verify", {"title": "x", "source": "nope"})[0], 400)
        self.assertEqual(self.call("/api/literature/verify", [])[0], 400)
        server.LITERATURE_SOURCES = {"fake": FakeSource(exc=literature.SourceError("crossref returned HTTP 500"))}
        try:
            self.assertEqual(self.call("/api/literature/verify", {"title": "x", "doi": "10.1/x", "source": "fake"})[0], 502)
        finally:
            server.LITERATURE_SOURCES = {"fake": FakeSource(REC)}
    def test_cap_returns_429(self):
        server.LITERATURE_CALLS = server.LITERATURE_CAP
        try:
            self.assertEqual(self.call("/api/literature/verify", {"title": "x", "doi": "10.1/x", "source": "fake"})[0], 429)
        finally:
            server.LITERATURE_CALLS = 0
    def test_ui_has_the_references_panel(self):
        body = urllib.request.urlopen(self.base + "/").read().decode()
        self.assertIn("References (optional)", body); self.assertIn("Verify reference", body); self.assertIn("/api/literature/sources", body)
if __name__ == "__main__": unittest.main()
