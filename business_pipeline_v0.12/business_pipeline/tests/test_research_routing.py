"""The retrieval engine consumes a profile's research block.

These are the trap tests for Direction 1: a profile that declares a topic
routes the dimension to that topic, a declared tier order ranks official/data
sources first, a budget caps the queries, and every rejected candidate carries a
reason in the ledger.  Without the block the old behaviour is unchanged.
"""

import unittest
import unittest.mock

import sys
sys.path.insert(0, "src")

from bp.product import retrieval  # noqa: E402


def _page(title, description, tier, url="https://example.org/x"):
    return {"title": title, "description": description, "tier": tier,
            "url": url, "site": "Example", "year": 2024}


class RoutingTest(unittest.TestCase):
    def setUp(self):
        self.log = unittest.mock.patch.object(retrieval, "_log_learning")
        self.log.start()
        self.addCleanup(self.log.stop)

    def _run(self, web_results, research=None, block_key="political", queries=None):
        with unittest.mock.patch.object(
                retrieval.source_finder, "search_academic",
                return_value={"results": [], "errors": [], "skipped": []}) as academic, \
             unittest.mock.patch.object(
                retrieval.source_finder, "search_web",
                return_value={"results": web_results}) as web:
            found = retrieval.retrieve(
                key="political", cues="government policy regulation trade stability",
                queries=queries or ["government policy regulation"],
                context=[], geography="Global",
                gate={"title_cue": False, "title_context": False, "require_geography": False},
                research=research, block_key=block_key)
        return found, academic, web

    def test_a_declared_topic_routes_the_dimension_to_that_topic(self):
        _found, _academic, web = self._run(
            [_page("Government policy and trade regulation", "government policy regulation trade", "official")],
            research={"topics": {"political": "law"}})
        self.assertTrue(web.called)
        self.assertEqual(web.call_args.kwargs.get("topic"), "law")

    def test_a_declared_tier_order_puts_official_before_a_higher_scoring_news_page(self):
        found, _academic, _web = self._run(
            [_page("Government policy regulation trade stability", "government policy regulation trade", "news",
                  "https://example.org/news"),
             _page("Trade regulation", "government policy", "official", "https://example.org/official")],
            research={"tiers": {"political": ["official", "data"]}})
        self.assertTrue(found["items"])
        self.assertEqual(found["items"][0]["tier"], "official")

    def test_a_declared_budget_caps_the_queries(self):
        _found, academic, _web = self._run(
            [_page("Government policy regulation", "government policy regulation trade", "official")],
            research={"budget": 1},
            queries=["first query", "second query", "third query"])
        corpus_calls = [call for call in academic.call_args_list
                        if call.kwargs.get("databases") == ["corpus"]]
        self.assertEqual(len(corpus_calls), 1)
        self.assertEqual(corpus_calls[0].args[0], "first query")

    def test_a_rejected_candidate_is_recorded_with_its_reason(self):
        found, _academic, _web = self._run(
            [_page("Cooking recipes for winter", "a recipe for soup", "news", "https://example.org/cook"),
             _page("Government policy and trade regulation", "government policy regulation trade", "official")])
        reasons = [row["reason"] for row in found["ledger"]["rejected"]]
        self.assertIn("no_cue", reasons)

    def test_without_a_research_block_the_old_behaviour_is_unchanged(self):
        found, _academic, web = self._run(
            [_page("Government policy and trade regulation", "government policy regulation trade", "official")],
            research=None)
        self.assertEqual(web.call_args.kwargs.get("topic"), None)
        self.assertTrue(found["items"])


if __name__ == "__main__":
    unittest.main()
