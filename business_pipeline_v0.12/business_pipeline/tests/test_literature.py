import sys, json, unittest, urllib.request, urllib.error, io
sys.path.insert(0, "src")
from bp import literature
from bp.literature import CrossrefSource, OpenAlexSource, verify_reference, SourceError, Reference

CROSSREF_MSG = {"message": {"title": [" A Study of Markets "], "author": [{"given": "A.", "family": "Author"}, {"given": "B.", "family": "Baker"}],
                            "issued": {"date-parts": [[2024]]}, "container-title": ["Journal of Business"]}}
OPENALEX = {"title": "A Study of Markets", "authorships": [{"author": {"display_name": "A. Author"}}], "publication_year": 2024,
            "primary_location": {"source": {"display_name": "Journal of Business"}}}

class Verify(unittest.TestCase):
    def opener(self, payload=None, exc=None, seen=None):
        def op(req, timeout=None):
            if seen is not None: seen.update(url=req.full_url, headers={k.lower(): v for k, v in req.header_items()}, timeout=timeout)
            if exc: raise exc
            return io.BytesIO(json.dumps(payload).encode())
        return op
    def test_no_doi_is_held_unverified_without_any_call(self):
        r = verify_reference("Any title"); self.assertEqual((r.status, r.doi, r.source, r.resolved_title), ("unverified_user_supplied", None, None, None))
    def test_title_match_marks_verified_and_canonicalizes(self):
        r = verify_reference("A Study of Markets", "10.1234/abc", CrossrefSource(opener=self.opener(CROSSREF_MSG)))
        self.assertEqual((r.status, r.title, r.year, r.container, r.source), ("verified", "A Study of Markets", "2024", "Journal of Business", "crossref"))
        self.assertEqual(r.authors, ("A. Author", "B. Baker"))
    def test_title_mismatch_stays_unverified_but_returns_resolved_title(self):
        r = verify_reference("A Different Paper", "10.1234/abc", CrossrefSource(opener=self.opener(CROSSREF_MSG)))
        self.assertEqual((r.status, r.title, r.resolved_title, r.source), ("unverified_user_supplied", "A Different Paper", "A Study of Markets", "crossref"))
    def test_unresolved_doi_stays_unverified(self):
        r = verify_reference("A Study of Markets", "10.1234/missing", CrossrefSource(opener=self.opener(exc=urllib.error.HTTPError("u", 404, "no", {}, io.BytesIO(b"")))))
        self.assertEqual(r.status, "unverified_user_supplied")
    def test_request_construction(self):
        seen = {}; CrossrefSource(mailto="a@b.c", timeout=19, opener=self.opener(CROSSREF_MSG, seen=seen)).resolve("10.1234/abc")
        self.assertEqual(seen["url"], "https://api.crossref.org/works/10.1234%2Fabc"); self.assertEqual(seen["timeout"], 19); self.assertIn("mailto:a@b.c", seen["headers"]["user-agent"])
        seen = {}; OpenAlexSource(timeout=7, opener=self.opener(OPENALEX, seen=seen)).resolve("10.1234/abc")
        self.assertEqual(seen["url"], "https://api.openalex.org/works/doi:10.1234/abc"); self.assertEqual(seen["timeout"], 7)
    def test_openalex_mapping(self):
        r = OpenAlexSource(opener=self.opener(OPENALEX)).resolve("10.1234/abc")
        self.assertEqual((r["title"], r["year"], r["container"], r["authors"]), ("A Study of Markets", "2024", "Journal of Business", ("A. Author",)))
    def test_errors_are_mapped(self):
        for exc in (urllib.error.URLError("net"), TimeoutError(), io.UnsupportedOperation("x")):
            with self.assertRaises(SourceError): CrossrefSource(opener=self.opener(exc=exc)).resolve("10.1234/abc")
        with self.assertRaises(SourceError): CrossrefSource(opener=self.opener("not json")).resolve("10.1234/abc")
        with self.assertRaises(SourceError): CrossrefSource(opener=self.opener({"message": "x"})).resolve("10.1234/abc")
        with self.assertRaises(SourceError): verify_reference("  ")
    def test_non_404_http_error_is_mapped(self):
        with self.assertRaises(SourceError): CrossrefSource(opener=self.opener(exc=urllib.error.HTTPError("u", 429, "no", {}, io.BytesIO(b"")))).resolve("10.1234/abc")
if __name__ == "__main__": unittest.main()
