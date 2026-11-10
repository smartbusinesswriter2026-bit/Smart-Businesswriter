"""Tests for the owner's switches and the growth loop.

Every loop is **off by default**.  A switch that is turned on works
immediately; a switch that is turned off stops the thing.
"""
import json
import os
import time
import unittest
from pathlib import Path

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product import ops_switches as switches  # noqa: E402


class SwitchDispatchTest(RelevanceTestCase):
    """Each switch must reach the loop it names."""

    def test_the_repair_switch_reaches_the_repair_loop(self):
        from unittest import mock
        from bp.product import autoresearch
        with mock.patch.object(autoresearch, "start", return_value=(True, "started")) as start:
            ok, message = switches.set_switch("loop.repair", True)
        self.assertTrue(ok, message)
        start.assert_called_once()

    def test_the_relevance_switch_reaches_the_relevance_loop(self):
        from unittest import mock
        from bp.product.relevance import job
        with mock.patch.object(job, "start", return_value=(True, "started")) as start:
            ok, message = switches.set_switch("loop.relevance", True)
        self.assertTrue(ok, message)
        start.assert_called_once()

    def test_a_loop_switch_turned_off_stops_its_loop(self):
        from unittest import mock
        from bp.product import autoresearch
        with mock.patch.object(autoresearch, "stop", return_value=(True, "stopped")) as stop:
            ok, message = switches.set_switch("loop.repair", False)
        self.assertTrue(ok, message)
        stop.assert_called_once()

    def test_a_search_switch_does_not_touch_a_loop(self):
        from unittest import mock
        from bp.product import autoresearch
        with mock.patch.object(autoresearch, "start") as start:
            switches.set_switch("search.opengo", False)
        start.assert_not_called()


class SwitchDefaultsTest(RelevanceTestCase):
    def test_every_loop_is_off_by_default(self):
        for key, entry in switches.CAPABILITIES.items():
            if entry["kind"] == "loop":
                self.assertFalse(entry["default"], "%s must default to off" % key)

    def test_the_search_chain_is_on_by_default(self):
        for key, entry in switches.CAPABILITIES.items():
            if entry["kind"] == "search":
                self.assertTrue(entry["default"], "%s must default to on" % key)

    def test_there_are_three_loops(self):
        loops = [k for k, v in switches.CAPABILITIES.items() if v["kind"] == "loop"]
        self.assertIn("loop.repair", loops)
        self.assertIn("loop.growth", loops)
        self.assertIn("loop.relevance", loops)

    def test_the_search_chain_has_the_owners_backup(self):
        order = switches.search_order()
        self.assertIn("opengo", order)
        self.assertEqual(order.index("brave"), 0)

    def test_a_switched_off_provider_leaves_the_chain(self):
        switches.set_switch("search.firecrawl", False)
        order = switches.search_order()
        self.assertNotIn("firecrawl", order)
        self.assertIn("brave", order)
        self.assertIn("opengo", order)

    def test_the_state_survives_a_read(self):
        switches.set_switch("search.firecrawl", False)
        self.assertNotIn("firecrawl", switches.search_order())
        self.assertFalse(switches.get("search.firecrawl"))


class SwitchBehaviourTest(RelevanceTestCase):
    def test_an_unknown_capability_is_refused(self):
        ok, message = switches.set_switch("loop.nonexistent", True)
        self.assertFalse(ok)
        self.assertIn("unknown capability", message)

    def test_turning_a_loop_on_starts_it_immediately(self):
        os.environ["BP_GROWTH_INTERVAL"] = "2"
        ok, message = switches.set_switch("loop.growth", True)
        self.assertTrue(ok, message)
        try:
            from bp.product import growth_loop
            deadline = time.time() + 5
            while time.time() < deadline and not growth_loop.status()["running"]:
                time.sleep(0.1)
            self.assertTrue(growth_loop.status()["running"],
                            "the growth loop must start the moment the switch is on")
        finally:
            switches.set_switch("loop.growth", False)

    def test_turning_a_loop_off_stops_it(self):
        os.environ["BP_GROWTH_INTERVAL"] = "2"
        switches.set_switch("loop.growth", True)
        deadline = time.time() + 5
        from bp.product import growth_loop
        while time.time() < deadline and not growth_loop.status()["running"]:
            time.sleep(0.1)
        switches.set_switch("loop.growth", False)
        deadline = time.time() + 8
        while time.time() < deadline and growth_loop.status()["running"]:
            time.sleep(0.2)
        self.assertFalse(growth_loop.status()["running"])

    def test_the_switch_is_persisted(self):
        switches.set_switch("loop.repair", False)
        path = Path(os.environ["BP_STATE_DIR"]) / "ops_switches.json"
        self.assertTrue(path.is_file())
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
        self.assertIn("loop.repair", data["switches"])


class GrowthLoopTest(RelevanceTestCase):
    def _finding(self, **overrides):
        from bp.product import ops_log
        args = {"rule": "capability_gap", "subject": "marketing",
                "feature": "A framework the product lacks",
                "section": "relevance:gap_test", "source": "relevance",
                "message": "The product has no framework for this analysis."}
        args.update(overrides)
        return ops_log.log_finding(**args)

    def test_a_capability_gap_is_picked_up_from_any_source(self):
        self._finding(source="capability_gap")
        self._finding(section="relevance:gap_two", source="relevance")
        from bp.product import growth_loop
        self.assertEqual(len(growth_loop.pending_gaps()), 2)

    def test_a_finding_that_is_not_a_capability_gap_is_ignored(self):
        self._finding(rule="validation")
        from bp.product import growth_loop
        self.assertEqual(len(growth_loop.pending_gaps()), 0)

    def test_one_pass_scaffolds_the_gap_and_does_not_repeat_it(self):
        self._finding()
        from bp.product import growth_loop
        result = growth_loop.run_pass()
        self.assertEqual(result["scaffolded"], 1)
        self.assertTrue(result["folders"])
        self.assertTrue(Path(result["folders"][0]).is_dir())
        # The scaffold is a draft: the method stub says so.
        stub = Path(result["folders"][0]) / "method_stub.py"
        self.assertTrue(stub.is_file())
        self.assertIn("PROVISIONAL", stub.read_text(encoding="utf-8"))
        # A second pass does not scaffold it again.
        self.assertEqual(growth_loop.run_pass()["scaffolded"], 0)

    def test_the_scaffold_carries_the_gap_and_the_prior_lessons(self):
        self._finding()
        from bp.product import growth_loop
        result = growth_loop.run_pass()
        readme = Path(result["folders"][0]) / "README.md"
        self.assertTrue(readme.is_file())
        text = readme.read_text(encoding="utf-8")
        self.assertIn("no framework for this analysis", text)
        self.assertIn("PROVISIONAL", text)


class SearchBackupTest(RelevanceTestCase):
    def test_the_opencode_backup_is_a_registered_capability(self):
        entry = switches.CAPABILITIES["search.opengo"]
        self.assertIn("DeepSeek", entry["label"])
        self.assertEqual(entry["kind"], "search")

    def test_the_discovery_reads_the_switches(self):
        from bp.product.relevance import discovery
        order = discovery.search_provider_order()
        self.assertIn("opengo", order)

    def test_the_parser_reads_the_websearch_json(self):
        """The websearch tool answers in JSON now; the old text shape still works."""
        from bp.product import sources
        sites = [{"domain": "insead.edu", "label": "INSEAD", "region": "Global",
                  "tier": "official"}]
        payload = {"results": [{"url": "https://www.insead.edu/mba/curriculum",
                                "title": "MBA Curriculum | INSEAD",
                                "excerpts": ["the core courses"]}]}
        event = {"type": "tool_use", "part": {"type": "tool", "tool": "websearch",
                                              "state": {"output": json.dumps(payload)}}}
        parsed = sources._parse_opencode_results(json.dumps(event), sites, 5)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["url"], "https://www.insead.edu/mba/curriculum")

    def test_the_parser_still_reads_the_old_text_shape(self):
        from bp.product import sources
        sites = [{"domain": "insead.edu", "label": "INSEAD", "region": "Global",
                  "tier": "official"}]
        output = "Title: MBA Curriculum | INSEAD\nURL: https://www.insead.edu/mba/curriculum\nHighlights:\nthe core courses"
        event = {"type": "tool_use", "part": {"type": "tool", "tool": "websearch",
                                              "state": {"output": output}}}
        parsed = sources._parse_opencode_results(json.dumps(event), sites, 5)
        self.assertEqual(len(parsed), 1)

    def test_a_refused_search_is_not_cached(self):
        """A rate-limited search must not be cached as "this source has nothing"."""
        from bp.product import sources
        sources.clear_cache()
        calls = []

        def fake(*args, **kwargs):
            calls.append(1)
            return [], {"provider": "brave", "error": "HTTP 429"}

        original = sources._brave_web
        sources._brave_web = fake
        try:
            sources.search_web("a query nothing answers", limit=5,
                               sites=[{"domain": "insead.edu", "label": "INSEAD",
                                       "region": "Global", "tier": "official"}],
                               providers=("brave",), fast=False)
            sources.search_web("a query nothing answers", limit=5,
                               sites=[{"domain": "insead.edu", "label": "INSEAD",
                                       "region": "Global", "tier": "official"}],
                               providers=("brave",), fast=False)
        finally:
            sources._brave_web = original
        self.assertEqual(len(calls), 2,
                         "a refused search must be asked again, not served from the cache")


if __name__ == "__main__":
    unittest.main()
