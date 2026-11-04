import sys, io, json, os, tempfile, unittest, urllib.error
sys.path.insert(0, "src")
from bp import literature
from bp.literature import verify_reference, read_log, drift_check, SourceError, Reference, Source, LOG_FORMAT

REC = {"title": "A Study of Markets", "authors": ("A. Author",), "year": "2024", "container": "Journal",
       "retrieved_at": "2026-10-21T00:00:00Z", "response_hash": "a" * 64}


def rec_with(hash_="a" * 64, title="A Study of Markets"):
    return {**REC, "response_hash": hash_, "title": title}


class Fake(Source):
    def __init__(self, name, rec=None, exc=None): self.name, self.rec, self.exc = name, rec, exc
    def resolve(self, doi):
        if self.exc: raise self.exc
        return self.rec


class Failover(unittest.TestCase):
    def test_second_source_resolves_when_the_first_errors(self):
        ref = verify_reference("A Study of Markets", "10.1/x", sources=(Fake("one", exc=SourceError("down")), Fake("two", rec=REC)))
        self.assertEqual((ref.status, ref.source), ("verified", "two"))

    def test_second_source_resolves_when_the_first_does_not_find_the_doi(self):
        ref = verify_reference("A Study of Markets", "10.1/x", sources=(Fake("one", rec=None), Fake("two", rec=REC)))
        self.assertEqual((ref.status, ref.source), ("verified", "two"))

    def test_all_sources_not_found_leaves_the_reference_unverified(self):
        ref = verify_reference("A Study of Markets", "10.1/x", sources=(Fake("one", rec=None), Fake("two", rec=None)))
        self.assertEqual((ref.status, ref.source), ("unverified_user_supplied", None))

    def test_all_sources_erroring_fails_closed(self):
        with self.assertRaises(SourceError) as cm:
            verify_reference("A Study of Markets", "10.1/x", sources=(Fake("one", exc=SourceError("down")), Fake("two", exc=SourceError("also down"))))
        self.assertIn("every retrieval source failed", str(cm.exception))

    def test_attempts_are_recorded_in_the_log(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "log.jsonl")
            verify_reference("A Study of Markets", "10.1/x", sources=(Fake("one", exc=SourceError("down")), Fake("two", rec=REC)), log=p)
            rec = read_log(p)[-1]
            self.assertEqual(rec["source"], "two")
            self.assertEqual([a["source"] for a in rec["attempts"]], ["one", "two"])
            self.assertEqual([a["outcome"] for a in rec["attempts"]], ["error", "resolved"])


class Drift(unittest.TestCase):
    def setUp(self): self.tmp = tempfile.TemporaryDirectory(); self.path = os.path.join(self.tmp.name, "log.jsonl")
    def tearDown(self): self.tmp.cleanup()

    def log_one(self, rec=None):
        verify_reference("A Study of Markets", "10.1/x", sources=(Fake("fake", rec=rec or REC),), log=self.path)

    def test_unchanged_source_reports_hash_match(self):
        self.log_one(); rep = drift_check(self.path, 10, sources=(Fake("fake", rec=REC),))
        self.assertEqual((rep["checked"], rep["hash_match"], rep["hash_differs"]), (1, 1, []))

    def test_changed_bytes_are_reported_not_rewritten(self):
        self.log_one(); rep = drift_check(self.path, 10, sources=(Fake("fake", rec=rec_with(hash_="b" * 64)),))
        self.assertEqual(rep["hash_differs"], ["10.1/x"]); self.assertEqual(len(read_log(self.path)), 1)

    def test_unresolvable_and_unreachable_are_distinguished(self):
        self.log_one(); self.log_one()
        rep = drift_check(self.path, 10, sources=(Fake("fake", rec=None),))
        self.assertEqual(len(rep["unresolvable_now"]), 2)
        rep = drift_check(self.path, 10, sources=(Fake("fake", exc=SourceError("down")),))
        self.assertEqual(len(rep["unreachable"]), 2)

    def test_empty_or_missing_log_checks_nothing(self):
        rep = drift_check(self.path, 10, sources=(Fake("fake", rec=REC),))
        self.assertEqual((rep["checked"], rep["hash_match"]), (0, 0))
        self.assertIn("never rewritten", rep["notice"])

    def test_drift_tries_sources_in_order(self):
        self.log_one(); rep = drift_check(self.path, 10, sources=(Fake("one", exc=SourceError("down")), Fake("two", rec=REC)))
        self.assertEqual(rep["hash_match"], 1); self.assertEqual(rep["results"][0]["checked_with"], "two")


if __name__ == "__main__":
    unittest.main()
