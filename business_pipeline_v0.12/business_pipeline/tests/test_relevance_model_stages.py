"""Tests for the RRA model-driven stages: model helper, discovery, extraction, drafting, job."""
import unittest
from unittest import mock

from tests.relevance_base import RelevanceTestCase  # noqa: E402

from bp.product.relevance import config as rconfig  # noqa: E402
from bp.product.relevance import discovery as rdiscovery  # noqa: E402
from bp.product.relevance import job as rjob  # noqa: E402
from bp.product.relevance import model as rmodel  # noqa: E402
from bp.product.relevance import s2_reader as rreader  # noqa: E402
from bp.product.relevance import s5_designer as rdesigner  # noqa: E402


class ModelHelperTest(RelevanceTestCase):
    def test_a_plain_object_is_parsed(self):
        self.assertEqual(rmodel.parse_json('{"a": 1}'), {"a": 1})

    def test_a_fenced_answer_is_parsed(self):
        self.assertEqual(rmodel.parse_json('Here you go:\n```json\n{"a": 2}\n```'), {"a": 2})

    def test_prose_before_the_object_is_skipped(self):
        self.assertEqual(rmodel.parse_json('The answer is {"a": 3} — hope that helps.'), {"a": 3})

    def test_an_array_stays_an_array(self):
        self.assertEqual(rmodel.parse_json('[{"a": 1}]'), [{"a": 1}])

    def test_a_non_json_answer_is_refused(self):
        self.assertIsNone(rmodel.parse_json("not json at all"))
        self.assertIsNone(rmodel.parse_json(""))

    def test_the_model_is_off_when_the_owner_says_so(self):
        self.set_env(BP_RELEVANCE_ENABLED="0")
        text, _record, err = rmodel.call("sys", "user")
        self.assertEqual(text, "")
        self.assertTrue(err)

    def test_no_provider_is_a_clear_error(self):
        self.unset_env("BP_RELEVANCE_PROVIDER", "BP_LLM_PROVIDER",
                       "BP_RELEVANCE_MODEL", "BP_LLM_MODEL")
        text, _record, err = rmodel.call("sys", "user")
        self.assertEqual(text, "")
        self.assertIn("provider", err.lower())

    def test_the_description_never_carries_a_key(self):
        info = rmodel.describe()
        self.assertIn("enabled", info)
        self.assertIn("budget_tokens", info)
        self.assertNotIn("api_key", info)
        self.assertNotIn("key", info)


class PerStageModelTest(RelevanceTestCase):
    """Decision D-4: two stages may read and write with different models."""

    def test_the_default_model_is_used_when_no_stage_override_is_set(self):
        self.set_env(BP_RELEVANCE_MODEL="model-a")
        self.unset_env("BP_RELEVANCE_EXTRACT_MODEL", "BP_RELEVANCE_DESIGN_MODEL",
                       "BP_RELEVANCE_DISCOVERY_MODEL")
        _provider, model = rmodel.model_names("relevance-extract")
        self.assertEqual(model, "model-a")

    def test_a_stage_override_wins(self):
        self.set_env(BP_RELEVANCE_MODEL="model-a",
                     BP_RELEVANCE_EXTRACT_MODEL="model-b")
        _provider, model = rmodel.model_names("relevance-extract")
        self.assertEqual(model, "model-b")
        _provider, other = rmodel.model_names("relevance-design")
        self.assertEqual(other, "model-a")

    def test_the_three_reading_stages_can_be_separated(self):
        self.set_env(BP_RELEVANCE_MODEL="model-a",
                     BP_RELEVANCE_EXTRACT_MODEL="model-b",
                     BP_RELEVANCE_DESIGN_MODEL="model-c",
                     BP_RELEVANCE_DISCOVERY_MODEL="model-d")
        self.assertEqual(rmodel.model_names("relevance-extract")[1], "model-b")
        self.assertEqual(rmodel.model_names("relevance-design")[1], "model-c")
        self.assertEqual(rmodel.model_names("relevance-discovery-query")[1], "model-d")

    def test_the_description_names_the_stage_variables(self):
        info = rmodel.describe()
        self.assertIn("stages", info)
        self.assertIn("extract", info["stages"])
        self.assertEqual(info["stages"]["extract"]["variable"],
                         "BP_RELEVANCE_EXTRACT_MODEL")


class QueryFallbackBudgetTest(RelevanceTestCase):
    """The model fallback is a proposal, not a requirement — it is bounded."""

    def test_the_budget_is_spent_and_then_refuses(self):
        from bp.product.relevance import discovery as rdiscovery
        budget = rdiscovery._Budget(2)
        self.assertTrue(budget.take())
        self.assertTrue(budget.take())
        self.assertFalse(budget.take())
        self.assertEqual(budget.used, 2)

    def test_the_search_budget_is_spent_and_then_refuses(self):
        """The provider rate-limits; a sweep that keeps asking gets nothing."""
        from bp.product.relevance import discovery as rdiscovery
        budget = rdiscovery._Budget(4, query_limit=2)
        self.assertTrue(budget.take_query())
        self.assertTrue(budget.take_query())
        self.assertFalse(budget.take_query())
        self.assertTrue(budget.query_stopped)

    def test_a_spent_search_budget_says_so(self):
        from bp.product.relevance import discovery as rdiscovery
        budget = rdiscovery._Budget(4, query_limit=0)
        results, error = rdiscovery._search("anything", [], budget=budget)
        self.assertEqual(results, [])
        self.assertIn("budget", error)

    def test_a_school_without_a_budget_still_gets_a_fallback(self):
        from bp.product.relevance import discovery as rdiscovery
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1"}]}
        with mock.patch.object(rdiscovery, "_search", return_value=([], "")):
            with mock.patch.object(rdiscovery, "_propose_query", return_value="") as proposer:
                rdiscovery.discover_for_school("INSEAD", allowlist=allowlist,
                                              use_model=True, budget=None)
        self.assertTrue(proposer.called)

    def test_an_exhausted_budget_skips_the_fallback(self):
        from bp.product.relevance import discovery as rdiscovery
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1"}]}
        with mock.patch.object(rdiscovery, "_search", return_value=([], "")):
            with mock.patch.object(rdiscovery, "_propose_query", return_value="") as proposer:
                urls, notes = rdiscovery.discover_for_school(
                    "INSEAD", allowlist=allowlist, use_model=True,
                    budget=rdiscovery._Budget(0))
        self.assertFalse(proposer.called)
        self.assertTrue(any("no query fallback left" in n for n in notes))


class TopicMatcherTest(RelevanceTestCase):
    """Which taxonomy topics a page names — and which it does not."""

    def _check(self, label, text, expected):
        from bp.product.relevance.s2_reader import _label_present
        got = _label_present(label, text)
        self.assertEqual(got, expected, "%r in %r" % (label, text[:60]))

    def test_a_short_label_must_sit_on_a_word_boundary(self):
        # "5S" stripped of its punctuation is "5s", which appears by chance in
        # almost any long page.  A label that matches everything matches
        # nothing.
        self._check("5S", "The course catalogue 2024/07 lists 2015 students.",
                    False)
        self._check("5S", "The workplace is organised by the 5S method.", True)

    def test_an_acronym_in_a_longer_label_is_matched(self):
        self._check("PESTEL analysis", "We teach PESTEL and SWOT.", True)
        self._check("SWOT analysis", "A SWOT is drawn.", True)
        self._check("BCG Growth-Share Matrix", "The BCG matrix is used.", True)

    def test_a_parenthetical_is_matched_on_either_side(self):
        self._check("OKR (Objectives and Key Results)",
                    "Objectives and Key Results are set.", True)
        self._check("OKR (Objectives and Key Results)",
                    "The OKR is reviewed each quarter.", True)

    def test_the_possessive_is_optional(self):
        self._check("Porter's Five Forces", "Porter Five Forces are applied.", True)
        self._check("Porter's Five Forces", "Porter's Five Forces are applied.", True)

    def test_a_multi_word_label_matches(self):
        self._check("Balanced Scorecard", "The Balanced Scorecard is used.", True)
        self._check("Financial Accounting", "Financial accounting is examined.", True)

    def test_named_topics_ignores_a_page_that_names_none(self):
        from bp.product.relevance.s2_reader import _named_topics
        self.assertEqual(_named_topics("Nothing relevant here."), [])
        found = _named_topics("We teach PESTEL and SWOT.")
        self.assertIn("PESTEL analysis", found)
        self.assertIn("SWOT analysis", found)


class WebCredentialTest(RelevanceTestCase):
    def test_the_loader_reports_names_and_never_values(self):
        from bp.product.relevance import discovery as rdiscovery
        loaded = rdiscovery.ensure_web_credentials()
        self.assertIsInstance(loaded, list)
        for name in loaded:
            self.assertIsInstance(name, str)
            self.assertNotIn("=", name)

    def test_the_loader_never_overrides_a_set_value(self):
        import os
        from bp.product import source_env as _source_env
        self.set_env(BP_BRAVE_API_KEY="a-key-already-set")
        _source_env.load_web_credentials()
        self.assertEqual(os.environ.get("BP_BRAVE_API_KEY"), "a-key-already-set")


class ConfigTest(RelevanceTestCase):
    def test_the_defaults_are_the_documented_ones(self):
        for name in ("BP_RELEVANCE_MAX_PAGES", "BP_RELEVANCE_BUDGET_TOKENS",
                     "BP_RELEVANCE_INTERVAL", "BP_RELEVANCE_AUTOSTART"):
            self.unset_env(name)
        self.assertEqual(rconfig.max_pages(), 50)
        self.assertEqual(rconfig.budget_tokens(), 200000)
        self.assertFalse(rconfig.autostart())
        self.assertTrue(rconfig.discover())

    def test_the_description_carries_the_switches(self):
        info = rconfig.describe()
        self.assertIn("max_pages", info)
        self.assertIn("autostart", info)
        self.assertIn("budget_tokens", info)


class DiscoveryTest(RelevanceTestCase):
    def test_the_allowlist_becomes_a_site_list(self):
        sites = rdiscovery._allowlist_sites({"allowed": [{"domain": "insead.edu", "tier": "T1"}]})
        self.assertEqual(len(sites), 1)
        self.assertEqual(sites[0]["domain"], "insead.edu")

    def test_a_result_outside_the_allowlist_is_dropped(self):
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1"}]}
        results = [{"url": "https://insead.edu/mba/curriculum"},
                   {"url": "https://evil.com/page"},
                   {"url": "https://en.wikipedia.org/wiki/MBA"}]
        kept = rdiscovery._allowed_results(results, allowlist)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["url"], "https://insead.edu/mba/curriculum")

    def test_nothing_is_searched_without_an_allowlist(self):
        urls, notes = rdiscovery.discover_for_school("INSEAD", allowlist={})
        self.assertEqual(urls, [])
        self.assertTrue(notes)

    def test_the_search_result_is_filtered_before_it_is_kept(self):
        allowlist = {"allowed": [{"domain": "insead.edu", "tier": "T1"}]}
        with mock.patch.object(rdiscovery, "_search",
                               return_value=([{"url": "https://insead.edu/mba/curriculum"},
                                              {"url": "https://other.example/x"}], "")):
            urls, _notes = rdiscovery.discover_for_school("INSEAD", allowlist=allowlist,
                                                          use_model=False)
        self.assertEqual(urls, ["https://insead.edu/mba/curriculum"])

    def test_the_discovered_urls_are_saved_and_loaded(self):
        import tempfile
        from pathlib import Path
        target = Path(tempfile.mkdtemp()) / "discovered.json"
        path, err = rdiscovery.save_discovered(path=target, urls=["https://insead.edu/x"],
                                               notes=["n"], per_school=[{"name": "INSEAD"}])
        self.assertEqual(err, "")
        self.assertTrue(path.is_file())
        self.assertEqual(rdiscovery.load_discovered(path=target), ["https://insead.edu/x"])


class ReadingTest(RelevanceTestCase):
    def test_the_markup_is_stripped(self):
        html = ("<html><head><style>x{}</style></head>"
                "<body><p>Hello</p><p>World</p></body></html>")
        text = rreader._html_to_text(html)
        self.assertIn("Hello", text)
        self.assertIn("World", text)
        self.assertNotIn("<p>", text)
        self.assertNotIn("x{}", text)

    def test_a_model_excerpt_that_is_not_verbatim_is_dropped(self):
        with mock.patch.object(rmodel, "call_json",
                               return_value=({"excerpt": "not in the page", "topics": ["x"]}, None, "")):
            excerpt, topics = rreader._model_excerpt("the actual page text here", "https://x.test")
        self.assertEqual(excerpt, "")
        self.assertEqual(topics, ["x"])

    def test_a_verbatim_model_excerpt_is_kept(self):
        with mock.patch.object(rmodel, "call_json",
                               return_value=({"excerpt": "actual page text", "topics": ["Finance"]}, None, "")):
            excerpt, topics = rreader._model_excerpt("the actual page text here", "https://x.test")
        self.assertEqual(excerpt, "actual page text")
        self.assertEqual(topics, ["finance"])

    def test_the_reader_uses_the_model_excerpt(self):
        with mock.patch.object(rmodel, "call_json",
                               return_value=({"excerpt": "Required courses", "topics": ["curriculum"]}, None, "")):
            snap = {"url": "https://insead.edu/mba/curriculum", "domain": "insead.edu",
                    "fetched_at": "2026-11-09T00:00:00+00:00", "sha256": "abc",
                    "paywalled": False, "_text": "<p>Required courses for the MBA programme</p>"}
            rec, err = rreader.snapshot_to_evidence(snap, use_model=True)
        self.assertEqual(err, "")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.excerpt, "Required courses")
        self.assertIn("curriculum", rec.topic_tags)

    def test_without_a_model_the_opening_words_are_used(self):
        snap = {"url": "https://insead.edu/mba/curriculum", "domain": "insead.edu",
                "fetched_at": "2026-11-09T00:00:00+00:00", "sha256": "abc",
                "paywalled": False, "_text": "one two three four five"}
        rec, err = rreader.snapshot_to_evidence(snap, use_model=False)
        self.assertEqual(err, "")
        self.assertTrue(rec.excerpt.startswith("one two"))

    def test_the_first_words_are_a_literal_substring(self):
        text = "alpha\nbeta\ngamma\ndelta"
        excerpt = rreader._first_words(text, 2)
        self.assertIn(excerpt, text)


class DraftingTest(RelevanceTestCase):
    def test_only_the_valid_fields_are_kept(self):
        answer = {
            "general_capability_statement": "A capability that is jurisdiction-neutral",
            "authoritative_reference": "AACSB Global Standards 2026",
            "proposed_acceptance_criterion": "A profile exists and its tests pass",
            "trap_test_idea": "A test that fails today",
            "owner_lane": "computation", "priority": "P1", "effort": "M",
            "category": "B", "bogus_field": "ignored",
        }
        with mock.patch.object(rmodel, "call_json", return_value=(answer, None, "")):
            draft = rdesigner._model_draft({"title": "X"}, "A", [])
        self.assertEqual(draft.get("owner_lane"), "computation")
        self.assertEqual(draft.get("priority"), "P1")
        self.assertEqual(draft.get("effort"), "M")
        self.assertEqual(draft.get("category"), "B")
        self.assertNotIn("bogus_field", draft)

    def test_an_invalid_value_is_refused(self):
        answer = {"owner_lane": "wizard", "priority": "P9", "effort": "XL", "category": "Z"}
        with mock.patch.object(rmodel, "call_json", return_value=(answer, None, "")):
            draft = rdesigner._model_draft({"title": "X"}, "A", [])
        for name in ("owner_lane", "priority", "effort", "category"):
            self.assertNotIn(name, draft)

    def test_a_failed_call_returns_nothing(self):
        with mock.patch.object(rmodel, "call_json", return_value=(None, None, "no model")):
            self.assertEqual(rdesigner._model_draft({"title": "X"}, "A", []), {})

    def test_the_spec_takes_the_model_draft(self):
        answer = {
            "general_capability_statement": "A jurisdiction-neutral capability",
            "proposed_acceptance_criterion": "Tests pass after the capability is built",
            "authoritative_reference": "AACSB Global Standards 2026",
            "trap_test_idea": "A test that fails today",
            "owner_lane": "design", "priority": "P1", "effort": "S", "category": "A",
        }
        with mock.patch.object(rmodel, "call_json", return_value=(answer, None, "")):
            spec, err = rdesigner.design_gap_spec(
                {"title": "Balanced Scorecard", "category": "A",
                 "general_capability_statement": "Balanced Scorecard",
                 "evidence_ids": ["ev_1"]}, use_model=True, evidence_records=[])
        self.assertEqual(err, "")
        self.assertEqual(spec.general_capability_statement, "A jurisdiction-neutral capability")
        self.assertEqual(spec.priority, "P1")
        self.assertEqual(spec.effort, "S")
        self.assertEqual(spec.authoritative_reference, "AACSB Global Standards 2026")

    def test_without_a_model_the_deterministic_default_is_used(self):
        spec, err = rdesigner.design_gap_spec(
            {"title": "Balanced Scorecard", "category": "A",
             "general_capability_statement": "Balanced Scorecard",
             "evidence_ids": ["ev_1"]}, use_model=False, evidence_records=[])
        self.assertEqual(err, "")
        self.assertIn("framework profile", spec.proposed_acceptance_criterion)
        ok, failures = spec.validate_strict()
        self.assertTrue(ok, failures)


class JobTest(RelevanceTestCase):
    def test_the_status_carries_the_config(self):
        status = rjob.status()
        self.assertIn("running", status)
        self.assertIn("config", status)

    def test_one_sweep_runs_in_the_foreground(self):
        with mock.patch.object(rjob, "run_sweep",
                               return_value={"run_id": "run_x", "status": "completed",
                                             "evidence_count": 1, "error": ""}):
            result = rjob.run_once()
        self.assertEqual(result["run_id"], "run_x")
        self.assertGreaterEqual(rjob.status()["sweeps_run"], 1)

    def test_a_second_start_is_refused_while_one_is_running(self):
        ok, message = rjob.start()
        self.assertTrue(ok, message)
        again, _ = rjob.start()
        self.assertFalse(again)
        stopped, stop_message = rjob.stop()
        self.assertTrue(stopped, stop_message)

    def test_the_autostart_is_off_by_default(self):
        self.set_env(BP_RELEVANCE_AUTOSTART="0")
        ok, message = rjob.autostart()
        self.assertFalse(ok)
        self.assertIn("autostart is off", message)


if __name__ == "__main__":
    unittest.main()
