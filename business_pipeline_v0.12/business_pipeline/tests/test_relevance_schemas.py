"""Tests for RRA schemas and storage."""
import unittest

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import schemas as S  # noqa: E402
from bp.product.relevance import storage  # noqa: E402
from bp.product.relevance.s7_gate import decision_summary  # noqa: E402


class EvidenceRecordTest(RelevanceTestCase):
    def test_a_complete_record_is_valid(self):
        rec = S.EvidenceRecord(
            source_url="https://insead.edu/mba/curriculum",
            retrieved_at_utc="2026-11-09T00:00:00+00:00",
            sha256="abc123",
            tier="T1",
            excerpt="Introduction to Strategy",
        )
        ok, reason = rec.validate()
        self.assertTrue(ok, reason)

    def test_the_source_url_is_required(self):
        rec = S.EvidenceRecord(
            retrieved_at_utc="2026-11-09T00:00:00+00:00",
            sha256="abc123", tier="T1", excerpt="test")
        ok, reason = rec.validate()
        self.assertFalse(ok)
        self.assertIn("source_url", reason)

    def test_the_timestamp_is_required(self):
        rec = S.EvidenceRecord(source_url="https://example.com",
                               sha256="abc123", tier="T1", excerpt="test")
        ok, reason = rec.validate()
        self.assertFalse(ok)
        self.assertIn("retrieved_at_utc", reason)

    def test_the_hash_is_required(self):
        rec = S.EvidenceRecord(source_url="https://example.com",
                               retrieved_at_utc="2026-11-09T00:00:00+00:00",
                               tier="T1", excerpt="test")
        ok, reason = rec.validate()
        self.assertFalse(ok)
        self.assertIn("sha256", reason)

    def test_a_blocked_domain_is_refused(self):
        rec = S.EvidenceRecord(source_url="https://wikipedia.org/wiki/Test",
                               retrieved_at_utc="2026-11-09T00:00:00+00:00",
                               sha256="abc", tier="T1", excerpt="test")
        ok, reason = rec.validate()
        self.assertFalse(ok)
        self.assertIn("blocked", reason.lower())

    def test_an_over_long_excerpt_is_refused(self):
        rec = S.EvidenceRecord(source_url="https://example.com",
                               retrieved_at_utc="2026-11-09T00:00:00+00:00",
                               sha256="abc", tier="T1",
                               excerpt=" ".join(["word"] * 30))
        ok, reason = rec.validate()
        self.assertFalse(ok)
        self.assertIn("under", reason)

    def test_the_record_survives_a_round_trip(self):
        rec = S.EvidenceRecord(source_url="https://example.com",
                               retrieved_at_utc="2026-11-09T00:00:00+00:00",
                               sha256="abc", tier="T2", excerpt="test excerpt",
                               topic_tags=["finance"])
        again = S.EvidenceRecord.from_dict(rec.to_dict())
        self.assertIsNotNone(again)
        self.assertEqual(again.source_url, rec.source_url)
        self.assertEqual(again.tier, rec.tier)
        self.assertEqual(again.topic_tags, rec.topic_tags)


class BlockedDomainTest(RelevanceTestCase):
    def test_the_wikipedia_class_is_blocked(self):
        for domain in ("wikipedia.org", "en.wikipedia.org", "wikimedia.org",
                       "reddit.com", "quora.com", "slideshare.net"):
            self.assertTrue(S._is_blocked_domain(domain), domain)

    def test_a_real_school_is_not_blocked(self):
        for domain in ("insead.edu", "ifrs.org", "aacsb.edu"):
            self.assertFalse(S._is_blocked_domain(domain), domain)


class CoverageRowTest(RelevanceTestCase):
    def test_a_valid_row_passes(self):
        ok, reason = S.CoverageRow(taxonomy_item="PESTEL", status="covered").validate()
        self.assertTrue(ok, reason)

    def test_an_unknown_status_is_refused(self):
        ok, _reason = S.CoverageRow(taxonomy_item="PESTEL", status="bogus").validate()
        self.assertFalse(ok)

    def test_the_item_is_required(self):
        ok, _reason = S.CoverageRow(status="covered").validate()
        self.assertFalse(ok)


class GapSpecTest(RelevanceTestCase):
    def _complete(self, **overrides):
        spec = S.GapSpec(
            title="Balanced Scorecard",
            category="A",
            general_capability_statement="A Balanced Scorecard framework for strategic management",
            evidence_ids=["ev_1"],
            authoritative_reference="Kaplan & Norton (1992), The Balanced Scorecard",
            owner_lane="design",
            proposed_acceptance_criterion="Framework profile with four perspectives and a KPI mapping",
            constraint_check={rule: True for rule in [
                "no_invented_evidence", "no_invented_numbers", "no_silent_substitution",
                "global_product", "no_template_text", "model_never_does_math",
                "stdlib_only", "human_approval_at_gates", "no_patch_fixes",
                "no_autonomous_code_writing", "frozen_core_respected"]},
        )
        for name, value in overrides.items():
            setattr(spec, name, value)
        spec.id = spec.make_id()
        return spec

    def test_a_complete_spec_passes_the_strict_check(self):
        ok, failures = self._complete().validate_strict()
        self.assertTrue(ok, failures)

    def test_a_spec_without_evidence_fails_g1(self):
        ok, failures = self._complete(evidence_ids=[]).validate_strict()
        self.assertFalse(ok)
        self.assertTrue(any("G1" in f for f in failures))

    def test_a_spec_without_an_acceptance_criterion_fails_g4(self):
        ok, failures = self._complete(proposed_acceptance_criterion="").validate_strict()
        self.assertFalse(ok)
        self.assertTrue(any("G4" in f for f in failures))

    def test_a_spec_without_a_reference_fails_g5(self):
        ok, failures = self._complete(authoritative_reference="").validate_strict()
        self.assertFalse(ok)
        self.assertTrue(any("G5" in f for f in failures))

    def test_a_spec_without_a_constraint_check_fails_g3(self):
        ok, failures = self._complete(constraint_check={}).validate_strict()
        self.assertFalse(ok)
        self.assertTrue(any("G3" in f for f in failures))

    def test_a_spec_with_a_violated_non_negotiable_fails_g3(self):
        spec = self._complete()
        spec.constraint_check["global_product"] = False
        ok, failures = spec.validate_strict()
        self.assertFalse(ok)
        self.assertTrue(any("global_product" in f for f in failures))

    def test_the_spec_survives_a_round_trip(self):
        spec = self._complete()
        again = S.GapSpec.from_dict(spec.to_dict())
        self.assertIsNotNone(again)
        self.assertEqual(again.title, spec.title)


class WatchItemTest(RelevanceTestCase):
    def test_a_valid_item_passes(self):
        ok, reason = S.WatchItem(item="IFRS 18",
                                 why_at_risk="Replaces IAS 1 from 1 Jan 2027").validate()
        self.assertTrue(ok, reason)

    def test_the_item_is_required(self):
        ok, _reason = S.WatchItem(why_at_risk="test").validate()
        self.assertFalse(ok)


class StorageTest(RelevanceTestCase):
    def test_the_state_paths_stay_inside_the_relevance_folder(self):
        self.assertTrue(storage.is_confined_path(storage.state_dir() / "runs.jsonl"))
        self.assertTrue(storage.is_confined_path(storage.qa_dir() / "schools.json"))

    def test_a_path_outside_the_folder_is_not_confined(self):
        from pathlib import Path
        self.assertFalse(storage.is_confined_path(Path("/tmp/evil.jsonl")))
        self.assertFalse(storage.is_confined_path(Path("C:/Windows/system32")))

    def test_a_run_is_appended_and_read_back(self):
        self.assertTrue(storage.append_run({"id": "test1", "value": 42}))
        runs = storage.read_runs()
        self.assertGreaterEqual(len(runs), 1)
        self.assertEqual(runs[-1]["id"], "test1")

    def test_evidence_is_appended_and_read_back(self):
        self.assertTrue(storage.append_evidence(
            {"id": "ev1", "tier": "T1", "source_url": "https://example.com"}))
        self.assertGreaterEqual(len(storage.read_evidence()), 1)

    def test_a_gap_is_appended_and_read_back(self):
        self.assertTrue(storage.append_gap({"id": "gap1", "title": "Test gap", "status": "open"}))
        self.assertGreaterEqual(len(storage.read_gaps()), 1)

    def test_a_watch_item_is_appended_and_read_back(self):
        self.assertTrue(storage.append_watchitem(
            {"item": "IFRS 18", "why_at_risk": "test", "status": "watching"}))
        self.assertGreaterEqual(len(storage.read_watchlist()), 1)

    def test_the_latest_record_wins(self):
        storage.append_gap({"id": "g1", "title": "first", "status": "open"})
        storage.append_gap({"id": "g1", "title": "first", "status": "approved"})
        latest = storage.read_latest_gap("g1")
        self.assertIsNotNone(latest)
        self.assertEqual(latest["status"], "approved")

    def test_one_record_per_gap_id(self):
        storage.append_gap({"id": "g1", "title": "a", "status": "open"})
        storage.append_gap({"id": "g1", "title": "a", "status": "approved"})
        storage.append_gap({"id": "g2", "title": "b", "status": "open"})
        latest = storage.read_latest_gaps()
        self.assertEqual(len(latest), 2)
        by_id = {g.get("id"): g for g in latest}
        self.assertEqual(by_id["g1"]["status"], "approved")
        self.assertEqual(by_id["g2"]["status"], "open")

    def test_the_decision_summary_counts_by_state(self):
        storage.append_gap({"id": "g1", "title": "a", "status": "open"})
        storage.append_gap({"id": "g2", "title": "b", "status": "open"})
        storage.append_gap({"id": "g2", "title": "b", "status": "approved"})
        summary = decision_summary()
        self.assertGreaterEqual(summary["open"], 1)
        self.assertGreaterEqual(summary["approved"], 1)


if __name__ == "__main__":
    unittest.main()
