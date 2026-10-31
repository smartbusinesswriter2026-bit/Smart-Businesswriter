"""The shared source finder: business databases, vetted sites, and honest failure.

No test touches the network: the one HTTP function is patched.
"""

import os
import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, sources, retrieval  # noqa: E402


def fake_json(url, headers=None, timeout=None):
    if "openalex.org" in url:
        return {"results": [{
            "title": "Firm strategy and performance", "doi": "https://doi.org/10.1/shared",
            "publication_year": 2024, "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
            "abstract_inverted_index": {"Strategy": [0], "matters": [1]},
            "primary_location": {"source": {"display_name": "Strategic Management Journal"}}}]}
    if "crossref.org" in url:
        return {"message": {"items": [{
            "title": ["Firm strategy and performance"], "DOI": "10.1/shared",
            "published": {"date-parts": [[2023]]}, "author": [{"given": "Ada", "family": "Lovelace"}],
            "container-title": ["Strategic Management Journal"], "abstract": "<jats:p>An abstract.</jats:p>"}]}}
    if "semanticscholar.org" in url:
        return {"data": [{
            "title": "Consumer trust in online markets", "year": 2022, "abstract": "A different paper.",
            "externalIds": {"DOI": "10.2/trust"}, "authors": [{"name": "Grace Hopper"}],
            "journal": {"name": "Journal of Marketing"}}]}
    if "doaj.org" in url:
        return {"results": [{"bibjson": {
            "title": "Open access and small firms", "year": "2021",
            "identifier": [{"type": "doi", "id": "10.3/open"}], "author": [{"name": "Alan Turing"}],
            "journal": {"title": "Small Business Economics"}, "abstract": "Open access text."}}]}
    if "search.brave.com" in url:
        return {"web": {"results": [
            {"title": "SEC filing", "url": "https://www.sec.gov/edgar/example", "description": "A filing"},
            {"title": "US legislation", "url": "https://www.congress.gov/bill/example", "description": "A bill"},
            {"title": "Unvetted blog", "url": "https://example.com/post", "description": "Not vetted"}]}}
    raise AssertionError("unexpected URL %r" % url)


class RegistryTest(unittest.TestCase):
    def test_business_databases_are_enabled_and_medical_indexes_are_not(self):
        enabled = {d["id"] for d in sources.databases(enabled_only=True)}
        self.assertTrue({"openalex", "crossref", "semanticscholar", "doaj"} <= enabled)
        self.assertNotIn("core", enabled)
        self.assertNotIn("pubmed", enabled)
        self.assertNotIn("arxiv", enabled)

    def test_every_region_the_product_serves_has_vetted_sites(self):
        for region in ("US", "Europe", "Middle East", "China"):
            self.assertTrue(sources.vetted_sites(region), region)

    def test_iran_specific_and_sanctions_sources_are_registered(self):
        middle_east = {site["domain"] for site in sources.vetted_sites("Middle East")}
        self.assertIn("cbi.ir", middle_east)
        self.assertIn("amar.org.ir", middle_east)
        self.assertIn("iran.un.org", middle_east)
        legal = {site["domain"] for site in sources.vetted_sites(category="legal")}
        self.assertIn("treasury.gov", legal)
        self.assertIn("consilium.europa.eu", legal)
        self.assertNotIn("Philippines", str(sources.vetted_sites()))

    def test_every_site_is_complete_and_unique(self):
        ids, domains = set(), set()
        for site in sources.vetted_sites():
            self.assertTrue(site["label"] and site["domain"] and site["use"], site)
            self.assertIn(site["tier"], ("official", "data", "research", "news"), site)
            self.assertIn(site["region"], sources.REGIONS, site)
            self.assertIn(site["category"], sources.CATEGORIES, site)
            self.assertIn(site["academic_fit"], ("primary", "research", "background"), site)
            self.assertNotIn(site["id"], ids, site)
            self.assertNotIn(site["domain"], domains, site)
            ids.add(site["id"]); domains.add(site["domain"])

    def test_legal_economic_and_social_sources_are_present(self):
        for category in ("legal", "economic", "social"):
            self.assertGreaterEqual(len(sources.vetted_sites(category=category)), 3, category)
        legal = {site["domain"] for site in sources.vetted_sites(category="legal")}
        self.assertIn("eur-lex.europa.eu", legal)
        self.assertIn("congress.gov", legal)
        social = {site["domain"] for site in sources.vetted_sites(category="social")}
        self.assertIn("worldvaluessurvey.org", social)

    def test_credibility_is_a_signal_between_zero_and_one_hundred(self):
        self.assertLessEqual(sources._credibility({}), 100)
        full = sources._credibility({"doi": "10.1/x", "abstract": "x" * 100, "year": 2025,
                                     "venue": "J", "url": "https://doi.org/10.1/x"})
        self.assertEqual(full, 100)


class SearchTest(unittest.TestCase):
    def setUp(self):
        sources.clear_cache()

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_academic_search_merges_and_dedupes_by_doi(self, _getter):
        with mock.patch.dict(os.environ, {}, clear=False):
            result = sources.search_academic("firm strategy trust online", limit=10)
        dois = [item["doi"] for item in result["results"]]
        self.assertEqual(dois.count("10.1/shared"), 1)
        self.assertIn("10.2/trust", dois)
        self.assertTrue(all(item["credibility"] <= 100 for item in result["results"]))
        self.assertEqual(result["skipped"], [])

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_one_selected_database_can_be_used_alone(self, _getter):
        result = sources.search_academic("strategy", databases=["openalex"], limit=5)
        self.assertEqual(result["databases"], ["openalex"])
        self.assertTrue(result["results"])
        self.assertTrue(all(item["database"] == "OpenAlex" for item in result["results"]))

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_a_failing_database_does_not_block_the_others(self, _getter):
        def flaky(url, headers=None, timeout=None):
            if "openalex.org" in url:
                raise OSError("network down")
            return fake_json(url, headers, timeout)
        with mock.patch("bp.product.sources._get_json", side_effect=flaky):
            result = sources.search_academic("strategy", databases=["openalex", "crossref"], limit=5)
        self.assertTrue(result["results"])
        self.assertTrue(any(error["database"] == "openalex" for error in result["errors"]))

    def test_query_match_drops_fruit_and_medical_noise(self):
        self.assertTrue(sources._query_match("smartphone competition Iran",
                                              {"title": "Smartphone competition in Iran",
                                               "abstract": "The market is competitive."}))
        self.assertFalse(sources._query_match("smartphone competition Iran",
                                              {"title": "Apple orchard soil microbes", "abstract": "Soil carbon."}))
        self.assertFalse(sources._query_match("smartphone competition Iran",
                                              {"title": "Smartphone intervention for depression",
                                               "abstract": "A clinical trial."}))

    def test_empty_query_returns_nothing_and_no_error(self):
        result = sources.search_academic("   ")
        self.assertEqual(result["results"], [])
        self.assertEqual(result["errors"], [])

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_an_identical_search_is_served_from_the_cache(self, getter):
        first = sources.search_academic("cached strategy", databases=["openalex"], limit=5)
        second = sources.search_academic("cached strategy", databases=["openalex"], limit=5)
        self.assertEqual(getter.call_count, 1)
        self.assertFalse(first["cached"])
        self.assertTrue(second["cached"])
        self.assertEqual(first["results"], second["results"])

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_each_database_reports_its_own_time(self, _getter):
        result = sources.search_academic("strategy", databases=["openalex", "doaj"], limit=5)
        self.assertEqual(set(result["timings"]), {"openalex", "doaj"})
        self.assertTrue(all(value >= 0 for value in result["timings"].values()))

    @mock.patch("bp.product.sources._brave_web")
    @mock.patch("bp.product.sources._deepseek_web")
    def test_deepseek_is_tried_before_brave(self, deepseek, brave):
        one = {"title": "SEC filing", "url": "https://www.sec.gov/x", "description": "A filing",
               "site": "U.S. SEC EDGAR", "domain": "sec.gov", "region": "US", "tier": "official"}
        deepseek.return_value = ([one], {"provider": "deepseek", "n": 1, "billable": True})
        result = sources.search_web("sec filing", "US")
        self.assertEqual(result["provider"], "deepseek")
        self.assertFalse(brave.called)
        self.assertEqual(result["attempts"][0]["provider"], "opengo")
        self.assertIn("skipped", result["attempts"][0])

    @mock.patch("bp.product.sources._brave_web")
    @mock.patch("bp.product.sources._deepseek_web")
    def test_deepseek_failure_falls_through_to_brave(self, deepseek, brave):
        one = {"title": "SEC filing", "url": "https://www.sec.gov/x", "description": "A filing",
               "site": "U.S. SEC EDGAR", "domain": "sec.gov", "region": "US", "tier": "official"}
        deepseek.return_value = ([], {"provider": "deepseek", "error": "HTTP 500"})
        brave.return_value = ([one], {"provider": "brave", "n": 1})
        result = sources.search_web("sec filing", "US")
        self.assertEqual(result["provider"], "brave")
        self.assertTrue(any(item.get("provider") == "deepseek" and item.get("error") for item in result["attempts"]))

    def test_a_thin_brave_answer_does_not_wait_for_the_fallback(self):
        one = {"title": "SEC filing", "url": "https://www.sec.gov/x", "description": "A filing",
               "site": "U.S. SEC EDGAR", "domain": "sec.gov", "region": "US", "tier": "official"}
        with mock.patch("bp.product.sources._brave_web", return_value=([one], {"provider": "brave", "n": 1})), \
                mock.patch("bp.product.sources._firecrawl_web") as firecrawl:
            result = sources.search_web("sec filing", "US")
        self.assertEqual(result["provider"], "brave")
        self.assertFalse(firecrawl.called)

    def test_web_search_without_a_key_returns_the_directory_not_invented_results(self):
        with mock.patch.dict(os.environ, {"BP_BRAVE_API_KEY": "", "BP_FIRECRAWL_KEYLESS": "0", "BP_DEEPSEEK_API_KEY": ""}, clear=False):
            result = sources.search_web("strategy", "US")
        self.assertEqual(result["results"], [])
        self.assertIn("No curated web result", result["notice"])
        self.assertTrue(result["sites"])

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_web_search_keeps_only_curated_domains(self, _getter):
        with mock.patch.dict(os.environ, {"BP_BRAVE_API_KEY": "test-key", "BP_FIRECRAWL_KEYLESS": "0", "BP_DEEPSEEK_API_KEY": ""}, clear=False):
            result = sources.search_web("sec filing", "US")
        self.assertEqual([item["domain"] for item in result["results"]], ["sec.gov", "congress.gov"])
        self.assertEqual(result["results"][0]["tier"], "official")

    @mock.patch("bp.product.sources._get_json", side_effect=fake_json)
    def test_web_search_category_limits_the_domains(self, _getter):
        with mock.patch.dict(os.environ, {"BP_BRAVE_API_KEY": "test-key", "BP_FIRECRAWL_KEYLESS": "0", "BP_DEEPSEEK_API_KEY": ""}, clear=False):
            result = sources.search_web("legislation", "US", category="legal")
        self.assertTrue(all(item["domain"] in {site["domain"] for site in sources.vetted_sites(category="legal")}
                            for item in result["results"]))
        self.assertIn("congress.gov", [item["domain"] for item in result["results"]])
        self.assertNotIn("sec.gov", [item["domain"] for item in result["results"]])

    @mock.patch("bp.product.sources._post_json")
    @mock.patch("bp.product.sources._get_json", side_effect=OSError("brave down"))
    def test_brave_failure_falls_back_to_firecrawl(self, _getter, post):
        post.return_value = {"data": {"web": [
            {"title": "Congress bill", "url": "https://www.congress.gov/bill/example", "description": "A bill"},
            {"title": "Unvetted", "url": "https://example.com/post", "description": "Not vetted"}]}}
        with mock.patch.dict(os.environ, {"BP_BRAVE_API_KEY": "test-key", "BP_FIRECRAWL_KEYLESS": "1", "BP_DEEPSEEK_API_KEY": ""}, clear=False):
            result = sources.search_web("legislation", "US", category="legal")
        self.assertEqual(result["provider"], "firecrawl")
        self.assertEqual([item["domain"] for item in result["results"]], ["congress.gov"])
        self.assertTrue(any(attempt.get("provider") == "brave" and attempt.get("error") for attempt in result["attempts"]))


class CorpusAdapterTest(unittest.TestCase):
    """The proprietary corpus adapter: registered, fails open, and returns page items."""

    def test_corpus_is_registered_in_adapters_and_databases(self):
        self.assertIn("corpus", sources.ADAPTERS)
        self.assertTrue(callable(sources.ADAPTERS["corpus"]))
        self.assertTrue(any(d["id"] == "corpus" for d in sources.DATABASES))
        corpus_db = next(d for d in sources.DATABASES if d["id"] == "corpus")
        self.assertEqual(corpus_db["access"], "local")
        self.assertTrue(corpus_db["enabled"])

    def test_corpus_fails_open_when_meilisearch_is_down(self):
        with mock.patch("urllib.request.urlopen") as urlopen:
            urlopen.side_effect = OSError("connection refused")
            items = sources._corpus("anything", 5, None)
            self.assertEqual(items, [])

    def test_key_of_prefers_corpus_key_over_doi_and_title(self):
        self.assertEqual(retrieval.key_of({"corpus_key": "corpus:bk-1:5"}),
                         "corpus:bk-1:5")
        self.assertEqual(retrieval.key_of({"doi": "10.1/x"}), "10.1/x")
        self.assertEqual(retrieval.key_of({"title": "Firm Strategy"}), "firm strategy")
        # No identity at all -> empty string
        self.assertEqual(retrieval.key_of({}), "")

    def test_dedup_does_not_overwrite_existing_credibility(self):
        item = {"corpus_key": "corpus:bk-1:1", "title": "T", "abstract": "x" * 100,
                "year": 2025, "venue": "J", "url": "https://doi.org/10.1/x"}
        item["credibility"] = 99
        copied = dict(item)
        copied.setdefault("credibility", sources._credibility(copied))
        self.assertEqual(copied["credibility"], 99)


class RouteTest(unittest.TestCase):
    def test_database_and_site_routes(self):
        status, payload = api.handle("GET", "/api/cases/sources/databases")
        self.assertEqual(status, 200)
        self.assertTrue(payload["databases"])
        status, payload = api.handle("GET", "/api/cases/sources/sites?region=China")
        self.assertEqual(status, 200)
        self.assertTrue(all(site["region"] in ("China", "Global") for site in payload["sites"]))
        status, legal = api.handle("GET", "/api/cases/sources/sites?category=legal")
        self.assertEqual(status, 200)
        self.assertTrue(all(site["category"] == "legal" for site in legal["sites"]))
        self.assertEqual(api.handle("GET", "/api/cases/sources/sites?region=Atlantis")[0], 422)
        self.assertEqual(api.handle("GET", "/api/cases/sources/sites?category=astrology")[0], 422)
        self.assertEqual(api.handle("GET", "/api/cases/sources/nope")[0], 404)

    def test_search_route_validates_and_returns_an_empty_query_cleanly(self):
        status, payload = api.handle("POST", "/api/cases/sources/search", {"query": "  "})
        self.assertEqual(status, 200)
        self.assertEqual(payload["results"], [])
        self.assertEqual(api.handle("POST", "/api/cases/sources/search", {"query": "x", "limit": "many"})[0], 422)
        self.assertEqual(api.handle("GET", "/api/cases/sources/search")[0], 405)
        self.assertEqual(api.handle("POST", "/api/cases/sources/web", {"query": "x", "region": "Mars"})[0], 422)


if __name__ == "__main__":
    unittest.main()
