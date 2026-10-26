import sys, io, json, os, tempfile, unittest, urllib.error
sys.path.insert(0, "src")
from bp import literature
from bp.literature import verify_reference, read_log, reverify, format_citation, CrossrefSource, SourceError, LOG_FORMAT

MSG = {"message": {"title": ["A Study of Markets"], "author": [{"given": "A.", "family": "Author"}, {"given": "B.", "family": "Baker"}],
                   "issued": {"date-parts": [[2024]]}, "container-title": ["Journal of Business"]}}


def opener_for(raw):
    def op(req, timeout=None): return io.BytesIO(raw)
    return op


def opener_404():
    def op(req, timeout=None): raise urllib.error.HTTPError("u", 404, "no", {}, io.BytesIO(b""))
    return op


RAW = json.dumps(MSG).encode()


class RetrievalLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.path = os.path.join(self.tmp.name, "retrieval_log.jsonl")
    def tearDown(self): self.tmp.cleanup()

    def verified(self, title="A Study of Markets", raw=RAW):
        return verify_reference(title, "10.1234/abc", CrossrefSource(opener=opener_for(raw)), log=self.path)

    def test_resolved_retrieval_is_appended_with_its_audit_fields(self):
        ref = self.verified()
        with open(self.path, encoding="utf-8") as f: lines = f.read().splitlines()
        self.assertEqual(len(lines), 1); rec = json.loads(lines[0])
        self.assertEqual(rec["format"], LOG_FORMAT)
        self.assertEqual((rec["source"], rec["doi"], rec["status"]), ("crossref", "10.1234/abc", "verified"))
        self.assertEqual((rec["title_supplied"], rec["title_resolved"]), ("A Study of Markets", "A Study of Markets"))
        self.assertEqual(rec["response_hash"], ref.response_hash)
        self.assertEqual(rec["retrieved_at"], ref.retrieved_at)
        self.assertIn("logged_at", rec); self.assertEqual(rec["authors"], ["A. Author", "B. Baker"])
        self.assertEqual(rec["year"], "2024")

    def test_title_mismatch_is_logged_as_unverified_and_not_laundered(self):
        self.verified(title="A Different Paper"); rec = read_log(self.path)[-1]
        self.assertEqual(rec["status"], "unverified_user_supplied")
        self.assertEqual(rec["title_supplied"], "A Different Paper")
        self.assertEqual(rec["title_resolved"], "A Study of Markets")

    def test_only_retrievals_are_logged(self):
        verify_reference("A Study of Markets", log=self.path)                                  # no DOI: no retrieval
        verify_reference("A Study of Markets", "10.1234/missing", CrossrefSource(opener=opener_404()), log=self.path)
        self.assertEqual(read_log(self.path), [])

    def test_unwritable_log_fails_closed(self):
        with self.assertRaises(SourceError):
            verify_reference("A Study of Markets", "10.1234/abc", CrossrefSource(opener=opener_for(RAW)),
                             log=os.path.join(self.tmp.name, "no_such_dir", "log.jsonl"))

    def test_missing_log_reads_empty_and_corrupt_log_raises(self):
        self.assertEqual(read_log(self.path), [])
        with open(self.path, "w", encoding="utf-8") as f: f.write("{not json}\n")
        with self.assertRaises(SourceError): read_log(self.path)
        with open(self.path, "w", encoding="utf-8") as f: f.write('{"format": "something-else"}\n')
        with self.assertRaises(SourceError): read_log(self.path)

    def test_log_is_append_only_and_ordered(self):
        for i in range(3): self.verified()
        self.assertEqual(len(read_log(self.path)), 3)
        self.assertEqual([r["format"] for r in read_log(self.path, 2)], [LOG_FORMAT, LOG_FORMAT])

    def test_reverify_detects_same_bytes_changed_bytes_and_gone(self):
        self.verified(); entry = read_log(self.path)[-1]
        same = reverify(entry, CrossrefSource(opener=opener_for(RAW)))
        self.assertEqual((same["state"], same["title_still_matches"]), ("hash_match", True))
        changed = reverify(entry, CrossrefSource(opener=opener_for(RAW.replace(b"Markets", b"Markets "))))
        self.assertEqual(changed["state"], "hash_differs"); self.assertEqual(changed["logged_hash"], entry["response_hash"])
        gone = reverify(entry, CrossrefSource(opener=opener_404()))
        self.assertEqual(gone["state"], "unresolvable_now")
        self.assertEqual(reverify({"doi": None})["state"], "no_doi_logged")


class Citations(unittest.TestCase):
    def verified(self, raw=RAW):
        return verify_reference("A Study of Markets", "10.1234/abc", CrossrefSource(opener=opener_for(raw)))

    def test_verified_citation_carries_structure_and_is_declared_provisional(self):
        c = format_citation(self.verified())
        self.assertTrue(c["verified"])
        self.assertIn("A. Author; B. Baker (2024). A Study of Markets. Journal of Business.", c["text"])
        self.assertIn("https://doi.org/10.1234/abc", c["text"])
        self.assertIn("PROVISIONAL", c["notice"])
        self.assertIn("not an endorsed APA", c["notice"])

    def test_unverified_citation_is_labelled_and_never_looks_checked(self):
        ref = verify_reference("A Different Paper", "10.1234/abc", CrossrefSource(opener=opener_for(RAW)))
        c = format_citation(ref)
        self.assertFalse(c["verified"]); self.assertTrue(c["text"].startswith("[unverified user-supplied"))
        self.assertIn("A Different Paper", c["text"]); self.assertIn("not confirmed", c["text"])
        self.assertIn("different title", c["note"])
        ref = verify_reference("Anything", log=None)
        self.assertTrue(format_citation(ref)["text"].startswith("[unverified user-supplied"))

    def test_placeholders_instead_of_invented_authors_or_years(self):
        from bp.literature import Reference
        c = format_citation(Reference(title="Untitled", status="verified", doi=None, authors=(), year=None))
        self.assertIn("[no author] ([n.d.]). Untitled.", c["text"])

    def test_unknown_style_is_refused(self):
        with self.assertRaises(SourceError): format_citation(self.verified(), "apa")

    def test_formatting_is_deterministic(self):
        self.assertEqual(format_citation(self.verified()), format_citation(self.verified()))


if __name__ == "__main__":
    unittest.main()
