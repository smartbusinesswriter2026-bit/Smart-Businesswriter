"""Acceptance criteria tests for the RRA (AC1-AC10)."""
import unittest
from pathlib import Path

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import (record_decision, run_sweep,  # noqa: E402
                                  storage)
from bp.product.relevance.schemas import EvidenceRecord  # noqa: E402


class Ac1EvidenceProvenanceTest(RelevanceTestCase):
    def test_a_complete_record_passes(self):
        rec = EvidenceRecord(source_url="https://example.com",
                             retrieved_at_utc="2026-11-09T00:00:00+00:00",
                             sha256="abc", tier="T1", excerpt="test")
        ok, reason = rec.validate()
        self.assertTrue(ok, reason)

    def test_every_provenance_field_is_required(self):
        base = {"source_url": "https://example.com",
                "retrieved_at_utc": "2026-11-09T00:00:00+00:00",
                "sha256": "abc", "tier": "T1", "excerpt": "test"}
        for name in ("source_url", "retrieved_at_utc", "sha256", "excerpt"):
            values = dict(base)
            values[name] = ""
            ok, _reason = EvidenceRecord(**values).validate()
            self.assertFalse(ok, "AC1: %s must be required" % name)

    def test_the_tier_must_be_one_of_the_three(self):
        rec = EvidenceRecord(source_url="https://example.com",
                             retrieved_at_utc="2026-11-09T00:00:00+00:00",
                             sha256="abc", tier="T9", excerpt="test")
        ok, _reason = rec.validate()
        self.assertFalse(ok)


class Ac2TierRuleTest(RelevanceTestCase):
    def test_a_candidate_with_no_evidence_does_not_survive(self):
        from bp.product.relevance.s4_skeptic import challenge_gap
        cand = {"taxonomy_item": "Test", "pipeline_artefact_id": "", "taxonomy_id": "t1"}
        survives, _challenges = challenge_gap(cand, evidence_records=[])
        self.assertFalse(survives)

    def test_a_candidate_with_only_t3_evidence_does_not_survive(self):
        from bp.product.relevance.s4_skeptic import challenge_gap
        cand = {"taxonomy_item": "Test", "pipeline_artefact_id": "", "taxonomy_id": "t1"}
        survives, _challenges = challenge_gap(
            cand, evidence_records=[{"tier": "T3", "school_or_body": "blog.example"}])
        self.assertFalse(survives)

    def test_a_candidate_with_two_t1_sources_survives(self):
        from bp.product.relevance.s4_skeptic import challenge_gap
        cand = {"taxonomy_item": "Test", "pipeline_artefact_id": "", "taxonomy_id": "t1"}
        survives, challenges = challenge_gap(
            cand, evidence_records=[{"tier": "T1", "school_or_body": "INSEAD"},
                                    {"tier": "T1", "school_or_body": "HEC"}])
        self.assertTrue(survives, challenges)


class Ac3FilesystemConfinementTest(RelevanceTestCase):
    def test_the_write_paths_stay_inside_the_folders(self):
        self.assertTrue(storage.is_confined_path(storage.state_dir() / "test.jsonl"))
        self.assertFalse(storage.is_confined_path(Path("/tmp/evil.jsonl")))
        self.assertFalse(storage.is_confined_path(Path("C:/Windows")))


class Ac4ImportGraphTest(RelevanceTestCase):
    def test_the_paper_path_does_not_import_the_relevance_package(self):
        import bp.product.chat as chat_module
        import bp.product.paper as paper_module
        import bp.product.paper_batch as batch_module
        for module in (chat_module, paper_module, batch_module):
            self.assertNotIn("relevance", getattr(module, "__dict__", {}),
                             "relevance must not be imported by %s" % module.__name__)


class Ac6DeterminismTest(RelevanceTestCase):
    def test_two_sweeps_produce_the_same_verdicts(self):
        first = run_sweep(discover=False, use_model=False)
        second = run_sweep(discover=False, use_model=False)
        left = [(c["taxonomy_item"], c["status"]) for c in first.get("coverage", [])]
        right = [(c["taxonomy_item"], c["status"]) for c in second.get("coverage", [])]
        self.assertEqual(left, right)


class Ac7DecisionTest(RelevanceTestCase):
    def test_a_decision_is_recorded_with_a_reason_and_a_user(self):
        storage.append_gap({"id": "test_gap_ac7", "title": "Test", "status": "open"})
        ok, err = record_decision("test_gap_ac7", "approve",
                                  reason="test reason", user="tester")
        self.assertTrue(ok, err)
        latest = storage.read_latest_gap("test_gap_ac7")
        self.assertIsNotNone(latest)
        self.assertEqual(latest.get("status"), "approved")
        self.assertEqual(latest.get("reason"), "test reason")
        self.assertEqual(latest.get("user"), "tester")

    def test_an_unknown_decision_is_refused(self):
        storage.append_gap({"id": "test_gap_ac7b", "title": "Test", "status": "open"})
        ok, err = record_decision("test_gap_ac7b", "apply")
        self.assertFalse(ok)
        self.assertIn("approve/reject/defer", err)

    def test_a_decision_on_an_unknown_gap_is_refused(self):
        ok, err = record_decision("no_such_gap", "approve")
        self.assertFalse(ok)
        self.assertIn("not found", err)


class Ac8BlockedSourcesTest(RelevanceTestCase):
    def test_the_wikipedia_class_is_blocked(self):
        from bp.product.relevance.schemas import _is_blocked_domain
        for domain in ("wikipedia.org", "reddit.com", "quora.com", "slideshare.net"):
            self.assertTrue(_is_blocked_domain(domain), domain)

    def test_a_real_source_is_not_blocked(self):
        from bp.product.relevance.schemas import _is_blocked_domain
        for domain in ("insead.edu", "ifrs.org", "aacsb.edu"):
            self.assertFalse(_is_blocked_domain(domain), domain)


class Ac9ReportTest(RelevanceTestCase):
    def test_the_sweep_leaves_a_readable_record(self):
        result = run_sweep(discover=False, use_model=False)
        self.assertEqual(result.get("status"), "completed")
        self.assertGreaterEqual(len(storage.read_runs()), 1)
        self.assertIn("backtest", result)


class Ac10FrozenCoreTest(RelevanceTestCase):
    def test_every_relevance_module_imports_cleanly(self):
        import bp.product.relevance
        import bp.product.relevance.backtest
        import bp.product.relevance.catalogue_snapshot
        import bp.product.relevance.config
        import bp.product.relevance.discovery
        import bp.product.relevance.job
        import bp.product.relevance.model
        import bp.product.relevance.runner
        import bp.product.relevance.s0_scope
        import bp.product.relevance.s1_scout
        import bp.product.relevance.s2_reader
        import bp.product.relevance.s3_mapper
        import bp.product.relevance.s4_skeptic
        import bp.product.relevance.s5_designer
        import bp.product.relevance.s6_evaluator
        import bp.product.relevance.s7_gate
        import bp.product.relevance.schemas
        import bp.product.relevance.storage
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
