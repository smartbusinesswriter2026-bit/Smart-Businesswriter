"""Tests for the RRA runner and stages."""
import json
import unittest
from pathlib import Path

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import build_run_plan, run_sweep, storage  # noqa: E402
from bp.product.relevance.s1_scout import _is_allowed  # noqa: E402
from bp.product.relevance.s2_reader import snapshot_to_evidence  # noqa: E402
from bp.product.relevance.s4_skeptic import challenge_gap  # noqa: E402
from bp.product.relevance.s6_evaluator import evaluate_gap_spec  # noqa: E402
from bp.product.relevance.schemas import GapSpec  # noqa: E402


class ScopeTest(RelevanceTestCase):
    def test_a_plan_needs_a_school_list(self):
        plan, err = build_run_plan(school_list=None)
        if err:
            self.assertIn("school list is required", err)
        else:
            self.assertIsNotNone(plan)
            self.assertGreater(plan["school_count"], 0)

    def test_the_page_budget_must_be_positive(self):
        plan, err = build_run_plan(school_list={"regions": {"US": [{"name": "Test"}]}},
                                   page_budget=0)
        self.assertIsNone(plan)
        self.assertIn("page_budget", err)

    def test_the_token_budget_must_be_positive(self):
        plan, err = build_run_plan(school_list={"regions": {"US": [{"name": "Test"}]}},
                                   token_budget=-1)
        self.assertIsNone(plan)
        self.assertIn("token_budget", err)

    def test_the_plan_counts_the_schools(self):
        plan, err = build_run_plan(school_list={
            "regions": {"US": [{"name": "A"}, {"name": "B"}], "Europe": [{"name": "C"}]},
            "bodies_to_watch": ["AACSB"]})
        self.assertEqual(err, "")
        self.assertEqual(plan["school_count"], 3)


class SweepTest(RelevanceTestCase):
    def test_a_sweep_completes(self):
        result = run_sweep(discover=False, use_model=False)
        self.assertEqual(result.get("status"), "completed")
        self.assertTrue(str(result.get("run_id", "")).startswith("run_"))

    def test_two_sweeps_produce_the_same_coverage_verdicts(self):
        first = run_sweep(discover=False, use_model=False)
        second = run_sweep(discover=False, use_model=False)
        left = [(c["taxonomy_item"], c["status"]) for c in first.get("coverage", [])]
        right = [(c["taxonomy_item"], c["status"]) for c in second.get("coverage", [])]
        self.assertEqual(left, right)

    def test_no_gap_is_ever_approved_by_the_pipeline(self):
        result = run_sweep(discover=False, use_model=False)
        for gap in result.get("strict_pass_gaps", []):
            self.assertEqual(gap.get("status"), "open")

    def test_the_run_record_is_written(self):
        run_sweep(discover=False, use_model=False)
        runs = storage.read_runs()
        self.assertGreaterEqual(len(runs), 1)
        self.assertEqual(runs[-1].get("status"), "completed")

    def test_the_coverage_covers_every_taxonomy_topic(self):
        from bp.product.relevance.s0_scope import load_taxonomy
        taxonomy = load_taxonomy()
        result = run_sweep(discover=False, use_model=False)
        self.assertEqual(result.get("coverage_count"), len(taxonomy.get("topics", [])))


class ScoutTest(RelevanceTestCase):
    def test_a_blocked_domain_is_refused(self):
        allowlist = {"allowed": [{"domain": "example.com", "tier": "T1"}],
                     "blocked": ["wikipedia.org"]}
        ok, reason = _is_allowed("wikipedia.org", allowlist)
        self.assertFalse(ok)
        self.assertIn("blocked", reason)

    def test_an_unlisted_domain_is_refused(self):
        allowlist = {"allowed": [{"domain": "example.com", "tier": "T1"}]}
        ok, reason = _is_allowed("evil.com", allowlist)
        self.assertFalse(ok)
        self.assertIn("not on allowlist", reason)

    def test_an_allowlisted_domain_is_accepted(self):
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1"}]}
        ok, _reason = _is_allowed("insead.edu", allowlist)
        self.assertTrue(ok)


class ReaderTest(RelevanceTestCase):
    def test_a_blocked_snapshot_produces_no_record(self):
        snap = {
            "url": "https://wikipedia.org/wiki/Test",
            "domain": "wikipedia.org",
            "fetched_at": "2026-11-09T00:00:00+00:00",
            "sha256": "abc",
            "paywalled": False,
            "_text": "some text here",
        }
        rec, err = snapshot_to_evidence(snap, excerpt="some text here")
        self.assertIsNone(rec)
        self.assertTrue("blocked" in err.lower() or "excerpt" in err.lower())

    def test_a_snapshot_without_a_hash_is_refused(self):
        snap = {"url": "https://insead.edu/x", "domain": "insead.edu",
                "fetched_at": "2026-11-09T00:00:00+00:00", "sha256": "",
                "_text": "text"}
        rec, err = snapshot_to_evidence(snap)
        self.assertIsNone(rec)
        self.assertIn("sha256", err)


class SkepticTest(RelevanceTestCase):
    def test_a_candidate_without_evidence_does_not_survive(self):
        cand = {"taxonomy_item": "Test", "pipeline_artefact_id": "", "taxonomy_id": "test_id"}
        survives, challenges = challenge_gap(cand, evidence_records=[])
        self.assertFalse(survives)
        self.assertTrue(any("insufficient T1" in c for c in challenges))

    def test_a_candidate_with_an_artefact_is_not_a_duplicate_when_partial(self):
        cand = {"taxonomy_item": "Test", "pipeline_artefact_id": "test",
                "status": "partial", "taxonomy_id": "test_id"}
        survives, challenges = challenge_gap(
            cand, evidence_records=[{"tier": "T1", "school_or_body": "INSEAD"},
                                    {"tier": "T1", "school_or_body": "HEC"}])
        self.assertTrue(survives, challenges)


class EvaluatorTest(RelevanceTestCase):
    def test_an_empty_spec_does_not_pass(self):
        spec = GapSpec(title="Test", category="A",
                        general_capability_statement="test",
                        evidence_ids=[], authoritative_reference="",
                        owner_lane="design", proposed_acceptance_criterion="")
        strict, failures, credit = evaluate_gap_spec(spec)
        self.assertFalse(strict)
        self.assertGreater(len(failures), 0)
        self.assertLess(credit, 1.0)


class ConfinementTest(RelevanceTestCase):
    def test_the_write_paths_stay_inside_the_folders(self):
        self.assertTrue(storage.is_confined_path(storage.state_dir() / "test.jsonl"))
        self.assertFalse(storage.is_confined_path(Path("/tmp/evil.jsonl")))
        self.assertFalse(storage.is_confined_path(Path("C:/Windows/system32")))


if __name__ == "__main__":
    unittest.main()
