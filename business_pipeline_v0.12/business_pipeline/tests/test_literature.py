import sys, json, unittest, urllib.request, urllib.error, io, hashlib
sys.path.insert(0, "src")
from bp import literature
from bp.literature import CrossrefSource, OpenAlexSource, verify_reference, SourceError, Reference

CROSSREF_MSG = {"message": {"title": [" A Study of Markets "], "author": [{"given": "A.", "family": "Author"}, {"given": "B.", "family": "Baker"}],
                            "issued": {"date-parts": [[2024]]}, "container-title": ["Journal of Business"],
                            "type": "journal-article", "volume": "12", "issue": "3", "page": "45-60", "publisher": "Test Press"}}
OPENALEX = {"title": "A Study of Markets", "authorships": [{"author": {"display_name": "A. Author"}}], "publication_year": 2024, "type": "article",
            "biblio": {"volume": "12", "issue": "3", "first_page": "45", "last_page": "60"},
            "primary_location": {"source": {"display_name": "Journal of Business", "host_organization_name": "Test Press"}}}

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
    def test_crossref_bibliographic_fields_for_citations(self):
        r = CrossrefSource(opener=self.opener(CROSSREF_MSG)).resolve("10.1234/abc")
        self.assertEqual((r["reference_type"], r["volume"], r["issue"], r["pages"], r["publisher"]), ("journal-article", "12", "3", "45-60", "Test Press"))
        self.assertEqual(r["authors_structured"], (("Author", "A."), ("Baker", "B.")))
    def test_openalex_bibliographic_fields_and_type_mapping(self):
        r = OpenAlexSource(opener=self.opener(OPENALEX)).resolve("10.1234/abc")
        self.assertEqual((r["reference_type"], r["volume"], r["issue"], r["pages"], r["publisher"]), ("journal-article", "12", "3", "45-60", "Test Press"))
        self.assertEqual(r["authors_structured"], ())          # OpenAlex returns display names only; declared as such
    def raw_opener(self, raw):
        def op(req, timeout=None): return io.BytesIO(raw)
        return op
    def test_resolved_retrieval_records_hash_and_utc_time(self):
        raw = json.dumps(CROSSREF_MSG).encode()
        r = verify_reference("A Study of Markets", "10.1234/abc", CrossrefSource(opener=self.raw_opener(raw), clock=lambda: "2026-10-21T00:00:00Z"))
        self.assertEqual((r.status, r.retrieved_at), ("verified", "2026-10-21T00:00:00Z"))
        self.assertEqual(r.response_hash, hashlib.sha256(raw).hexdigest())
    def test_audit_fields_survive_a_title_mismatch(self):
        raw = json.dumps(CROSSREF_MSG).encode()
        r = verify_reference("A Different Paper", "10.1234/abc", CrossrefSource(opener=self.raw_opener(raw), clock=lambda: "T"))
        self.assertEqual((r.status, r.retrieved_at, r.response_hash), ("unverified_user_supplied", "T", hashlib.sha256(raw).hexdigest()))
    def test_unresolved_doi_or_no_doi_records_no_audit(self):
        a = verify_reference("Any title"); self.assertEqual((a.retrieved_at, a.response_hash), (None, None))
        r = verify_reference("A Study of Markets", "10.1234/missing", CrossrefSource(opener=self.opener(exc=urllib.error.HTTPError("u", 404, "no", {}, io.BytesIO(b"")))))
        self.assertEqual((r.status, r.retrieved_at, r.response_hash), ("unverified_user_supplied", None, None))
    def test_hash_pins_the_exact_bytes_not_the_parsed_record(self):
        one = b'{"message": {"title": ["A Study of Markets"]}}'
        two = b'{"message":  {"title": ["A Study of Markets"]}}'   # same JSON meaning, different bytes
        ra = verify_reference("A Study of Markets", "10.1/x", CrossrefSource(opener=self.raw_opener(one)))
        rb = verify_reference("A Study of Markets", "10.1/x", CrossrefSource(opener=self.raw_opener(two)))
        self.assertEqual((ra.status, rb.status), ("verified", "verified"))
        self.assertEqual(ra.response_hash, hashlib.sha256(one).hexdigest())
        self.assertNotEqual(ra.response_hash, rb.response_hash)
    def test_default_clock_is_iso_utc_and_openalex_also_audits(self):
        r = verify_reference("A Study of Markets", "10.1234/abc", CrossrefSource(opener=self.opener(CROSSREF_MSG)))
        self.assertRegex(r.retrieved_at, r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        raw = json.dumps(OPENALEX).encode()
        rec = OpenAlexSource(opener=self.raw_opener(raw), clock=lambda: "X").resolve("10.1234/abc")
        self.assertEqual((rec["retrieved_at"], rec["response_hash"]), ("X", hashlib.sha256(raw).hexdigest()))
    def test_errors_are_mapped(self):
        for exc in (urllib.error.URLError("net"), TimeoutError(), io.UnsupportedOperation("x")):
            with self.assertRaises(SourceError): CrossrefSource(opener=self.opener(exc=exc)).resolve("10.1234/abc")
        with self.assertRaises(SourceError): CrossrefSource(opener=self.opener("not json")).resolve("10.1234/abc")
        with self.assertRaises(SourceError): CrossrefSource(opener=self.opener({"message": "x"})).resolve("10.1234/abc")
        with self.assertRaises(SourceError): verify_reference("  ")
    def test_non_404_http_error_is_mapped(self):
        with self.assertRaises(SourceError): CrossrefSource(opener=self.opener(exc=urllib.error.HTTPError("u", 429, "no", {}, io.BytesIO(b"")))).resolve("10.1234/abc")
if __name__ == "__main__": unittest.main()
