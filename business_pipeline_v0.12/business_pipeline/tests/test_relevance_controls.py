"""Tests for the RRA control set — the measurement's own check on itself."""
import unittest

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import controls as rcontrols  # noqa: E402


def rows(*pairs):
    """Build coverage rows from (taxonomy_id, label, status) triples."""
    out = []
    for tid, label, status in pairs:
        out.append({"taxonomy_id": tid, "taxonomy_item": label, "status": status})
    return out


class ControlRegistryTest(RelevanceTestCase):
    def test_the_registry_is_present(self):
        controls, rules = rcontrols.load_controls()
        self.assertGreaterEqual(len(controls), 8)
        self.assertIn("min_controls_held", rules)

    def test_the_controls_are_the_things_the_system_already_has(self):
        controls, _rules = rcontrols.load_controls()
        ids = {c.get("taxonomy_id") for c in controls}
        for expected in ("framework_pestel", "framework_swot", "computation_breakeven"):
            self.assertIn(expected, ids)


class ControlCheckTest(RelevanceTestCase):
    def test_a_control_seen_in_the_evidence_is_held(self):
        coverage = rows(("framework_pestel", "PESTEL analysis", "covered"))
        evidence = [{"excerpt": "The course teaches PESTEL analysis in Period 1"}]
        result = rcontrols.check(coverage, evidence_records=evidence)
        held = {h["label"] for h in result["held_items"]}
        self.assertIn("PESTEL", held)

    def test_a_framework_control_with_no_evidence_does_not_hold(self):
        coverage = rows(("framework_pestel", "PESTEL analysis", "partial"))
        result = rcontrols.check(coverage, evidence_records=[])
        self.assertFalse(result["passed"])
        reasons = {m["label"]: m["reason"] for m in result["missing_items"]}
        self.assertIn("PESTEL", reasons)
        self.assertIn("no evidence", reasons["PESTEL"])

    def test_a_framework_control_not_in_the_evidence_does_not_hold(self):
        coverage = rows(("framework_pestel", "PESTEL analysis", "covered"))
        evidence = [{"excerpt": "A page about financial accounting only"}]
        result = rcontrols.check(coverage, evidence_records=evidence)
        reasons = {m["label"]: m["reason"] for m in result["missing_items"]}
        self.assertIn("PESTEL", reasons)
        self.assertIn("not found", reasons["PESTEL"])

    def test_a_named_topic_on_the_page_counts_as_seen(self):
        """The reader records which topics a page names, so a 25-word excerpt
        that misses the name does not hide the page from the control."""
        coverage = rows(("framework_pestel", "PESTEL analysis", "covered"))
        evidence = [{"excerpt": "Financial accounting is assessed by examination.",
                     "mentions": ["PESTEL analysis"]}]
        result = rcontrols.check(coverage, evidence_records=evidence)
        held = {h["label"] for h in result["held_items"]}
        self.assertIn("PESTEL", held)

    def test_a_capability_control_holds_on_the_catalogue_alone(self):
        coverage = rows(("computation_breakeven", "Break-even", "partial"))
        result = rcontrols.check(coverage, evidence_records=[])
        held = {h["id"] for h in result["held_items"]}
        self.assertIn("ctrl_breakeven", held)

    def test_a_control_reported_missing_is_not_held(self):
        coverage = rows(("framework_pestel", "PESTEL analysis", "missing"))
        evidence = [{"excerpt": "PESTEL is taught"}]
        result = rcontrols.check(coverage, evidence_records=evidence)
        reasons = {m["label"]: m["reason"] for m in result["missing_items"]}
        self.assertIn("reported missing", reasons["PESTEL"])

    def test_the_ratio_and_the_verdict_are_reported(self):
        coverage = rows(("framework_pestel", "PESTEL analysis", "covered"),
                        ("computation_breakeven", "Break-even", "partial"))
        evidence = [{"excerpt": "PESTEL analysis"}]
        result = rcontrols.check(coverage, evidence_records=evidence)
        self.assertIn("ratio", result)
        self.assertIn("verdict", result)
        self.assertGreaterEqual(result["total"], 8)

    def test_a_measurement_that_fails_its_controls_says_so(self):
        coverage = rows(("framework_pestel", "PESTEL analysis", "covered"))
        result = rcontrols.check(coverage, evidence_records=[])
        self.assertFalse(result["passed"])
        self.assertIn("FAILED", result["verdict"])


class SweepGateTest(RelevanceTestCase):
    def test_a_failed_measurement_promotes_no_gap(self):
        from bp.product.relevance import run_sweep
        result = run_sweep(discover=False, use_model=False)
        self.assertFalse(result.get("measurement_held"))
        self.assertEqual(result.get("strict_pass_count"), 0)
        self.assertIn("controls", result)
        self.assertFalse(result["controls"]["passed"])


if __name__ == "__main__":
    unittest.main()
