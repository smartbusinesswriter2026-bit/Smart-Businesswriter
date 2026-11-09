"""PESTEL completion: the second framework on the shared engine.

The tests are the behaviour the Five Forces pilot proved, applied to PESTEL:
six dimensions, sourced items or a named gap, no invented country fact, one
paper, the same evidence in the chat and on the worksheet.
"""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, chat, completion  # noqa: E402

BRIEF = ("A smartphone manufacturer is considering entering the Iranian market and needs the political, "
         "economic, social, technological, environmental and legal picture.")

COUNTRIES = ("Iran", "Saudi Arabia", "China", "United States", "United Kingdom", "Germany")


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query, so the dimension gate can judge it."""
    return {"results": [{
        "title": "Iran " + query[:70],
        "abstract": "Evidence on the conditions named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Public Policy", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def no_corpus_academic(query, databases=None, limit=10, year_from=None):
    """The corpus misses; the journal APIs answer as before."""
    if databases == ["corpus"]:
        return {"results": [], "errors": [], "skipped": []}
    return academic(query, databases, limit, year_from)


def news_web(query, region="Global", limit=10, category=None, fast=False, **kwargs):
    """A vetted page whose tier is press, so the source-type rule can see it."""
    return {"results": [{
        "title": "Iran " + query[:60],
        "description": "Iran evidence on the conditions named in the query.",
        "url": "https://example.org/news", "site": "Example Press", "tier": "news",
        "year": 2024,
    }], "sites": []}


def complete_news(**kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=no_corpus_academic), \
            mock.patch("bp.product.sources.search_web", side_effect=news_web):
        return completion.complete("template_pestel", kwargs.pop("instruction", BRIEF), **kwargs)


def blocks(result):
    return {block["key"]: block for block in result["blocks"]}


def complete(**kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete("template_pestel", kwargs.pop("instruction", BRIEF), **kwargs)


class PestelCompletionTest(unittest.TestCase):
    def test_six_dimensions_each_carry_a_sourced_item_or_a_named_gap(self):
        result = complete()
        self.assertEqual(result["template"], "template_pestel")
        self.assertEqual(result["framework"], "PESTEL")
        self.assertEqual(len(result["blocks"]), 6)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"], block["key"])
                    self.assertTrue(item["citation"], block["key"])

    def test_the_country_is_the_unit_of_analysis(self):
        result = complete()
        self.assertEqual(result["unit"]["field"], "country")
        self.assertEqual(result["unit"]["value"], "Iran")
        self.assertEqual(result["region"], "Middle East")
        self.assertTrue(result["blocks"][0]["query"].startswith("Iran "))

    def test_a_brief_without_a_country_is_refused_with_an_actionable_reason(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="A firm is weighing an expansion and needs the external environment.")
        self.assertIn("country", str(refused.exception).lower())

    def test_global_is_an_explicit_choice_never_a_default(self):
        result = complete(instruction=BRIEF, country="Global")
        self.assertEqual(result["unit"]["value"], "Global")
        self.assertEqual(result["region"], "Global")

    def test_an_accounting_brief_is_refused_not_filled_with_evidence(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="Prepare the trial balance and the journal entries for the month.")
        self.assertIn("accounting", str(refused.exception).lower())

    def test_a_student_item_is_preserved(self):
        result = complete(student_items=[{"block": "legal", "text": "The 2024 licensing rule applies."}])
        legal = blocks(result)["legal"]
        self.assertEqual(legal["items"][0]["text"], "The 2024 licensing rule applies.")
        self.assertEqual(legal["items"][0]["provenance"], "student")

    def test_no_evidence_is_written_from_general_background(self):
        with mock.patch("bp.product.sources.search_academic", return_value={"results": [], "errors": [], "skipped": []}), \
                mock.patch("bp.product.sources.search_web", side_effect=web), \
                mock.patch("bp.product.prose._call", side_effect=AssertionError("the model must not run")):
            result = completion.complete("template_pestel", BRIEF)
        self.assertEqual(len(result["blocks"]), 6)
        for block in result["blocks"]:
            self.assertEqual(len(block["items"]), 1, block["key"])
            self.assertEqual(block["items"][0]["provenance"], "background", block["key"])
            self.assertFalse(block["items"][0]["source"], block["key"])
            self.assertFalse(block["gap"], block["key"])
            self.assertFalse(any(char.isdigit() for char in block["items"][0]["text"]), block["key"])

    def test_a_source_cannot_fill_two_dimensions(self):
        def everything(query, databases=None, limit=10, year_from=None):
            return {"results": [{
                "title": "Iran policy regulation economic growth inflation demographics technology climate law",
                "abstract": "Government policy and regulation meet economic growth, inflation, demographics, "
                            "technology and legislation in one market.",
                "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
                "venue": "Journal", "doi": "10.1/same", "url": "https://doi.org/10.1/same",
                "database": "OpenAlex"}], "errors": [], "skipped": []}

        with mock.patch("bp.product.sources.search_academic", side_effect=everything), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            result = completion.complete("template_pestel", BRIEF)
        sourced = [block for block in result["blocks"]
                   if any(item["provenance"] == "sourced" for item in block["items"])]
        self.assertEqual(len(sourced), 1)

    def test_a_dimension_with_only_news_is_a_named_gap_not_a_weaker_source(self):
        """The source-type rule: a press page cannot stand in for official data."""
        result = complete_news()
        for block in result["blocks"]:
            self.assertFalse([item for item in block["items"]
                              if item["provenance"] == "sourced"], block["key"])
            self.assertTrue(block["gap"], block["key"])
            reasons = [row["reason"] for row in block["ledger"]["rejected"]]
            self.assertIn("tier_missing", reasons, block["key"])

    def test_the_ledger_records_the_accepted_and_rejected_candidates(self):
        result = complete()
        for block in result["blocks"]:
            self.assertIn("ledger", block)
            self.assertEqual(block["ledger"]["dimension"], block["key"])
            self.assertTrue(block["ledger"]["accepted"] or block["ledger"]["gaps"], block["key"])

    def test_the_paper_has_the_pestel_outline_and_a_pestel_title(self):
        result = complete()
        report = completion.draft(result, "apa", "draft", "mid")
        headings = [section["heading"] for section in report["sections"]]
        for required in ("Introduction", "Case and Country Context", "PESTEL", "Political", "Economic",
                         "Social", "Technological", "Environmental", "Legal", "Discussion",
                         "What the Evidence Shows", "Implications for the Decision", "Limitations",
                         "Conclusion", "References"):
            self.assertIn(required, headings)
        self.assertTrue(report["title"].startswith("PESTEL Analysis: "))
        self.assertEqual(report["framework"], "PESTEL")
        self.assertGreaterEqual(report["words"], 700)

    def test_the_title_drops_the_trailing_period(self):
        result = complete(instruction=BRIEF + ".")
        report = completion.draft(result, "apa", "draft")
        self.assertFalse(report["title"].endswith("."))

    def test_the_byline_reaches_the_title_page_and_the_length_is_reported(self):
        result = dict(complete(), byline=["A Student", "Example University"])
        report = completion.draft(result, "apa", "draft", "long")
        self.assertEqual(report["byline"], ["A Student", "Example University"])
        self.assertEqual(report["length"], "long")
        self.assertEqual(report["length_label"], "Long")
        self.assertEqual(report["length_applies_to"], "full")

    def test_a_failed_full_paper_falls_back_to_the_evidence_led_draft(self):
        result = complete()
        with mock.patch("bp.product.completion._model_sections", return_value=None):
            report = completion.draft(result, "apa", "full")
        self.assertFalse(report["model_used"])
        self.assertEqual(report["fallback"], "draft")
        self.assertTrue(report["sections"])
        self.assertGreaterEqual(report["words"], 700)

    def test_the_model_prompt_speaks_pestel_and_keeps_the_safety_rules(self):
        profile = dict(completion.LENGTHS["mid"])
        system = completion._system(completion.HEAD_SYSTEM, profile,
                                   completion._profile("template_pestel"))
        self.assertIn("PESTEL", system)
        self.assertNotIn("Porter", system)
        self.assertIn("Do not add facts, numbers, names, sources or citations", system)
        self.assertIn("country", system)

    def test_an_empty_dimension_does_not_block_the_paper(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"] if block["key"] != "environmental"]
        result["blocks"].append({"key": "environmental", "label": "Environmental", "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])

    def test_the_route_generates_a_paper_with_an_empty_dimension(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"] if block["key"] != "legal"]
        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": result, "version": "draft"})
        self.assertEqual(status, 200, payload)

    def test_the_route_returns_a_pestel_completion(self):
        with mock.patch("bp.product.completion.complete") as fake:
            fake.return_value = {"format": "bp-framework-completion/1", "template": "template_pestel",
                                 "blocks": []}
            status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                         {"template": "template_pestel", "instruction": BRIEF,
                                          "country": "Iran"})
        self.assertEqual(status, 200)
        self.assertEqual(payload["template"], "template_pestel")

    def test_a_framework_without_a_profile_is_refused_and_names_the_real_options(self):
        # case_decision is a template with no completion profile, so it is refused
        # and the message names the frameworks that do run.
        with self.assertRaises(ValueError) as refused:
            completion.complete("case_decision", BRIEF)
        self.assertIn("PESTEL", str(refused.exception))
        self.assertIn("Porter's Five Forces", str(refused.exception))


class SameEvidenceTest(unittest.TestCase):
    """The invariant: one engine, so the two surfaces cannot disagree."""

    def _titles(self, items):
        return sorted({item.get("title") for item in items})

    def test_the_chat_and_the_worksheet_return_the_same_sources(self):
        brief = ("A grocery chain is considering entering the Iranian market and needs to assess the "
                 "political, economic, social, technological, environmental and legal context.")
        with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            state = chat.start(brief, framework="pestel")
            for question_id, value in (("decision", "Should the chain enter Iran?"),
                                       ("geography", "Middle East"), ("period", "10"), ("style", "apa")):
                state = chat.answer(state, question_id, value)
            state = chat.research(chat.confirm_plan(state))
            worksheet = completion.complete("template_pestel", brief, country="Iran")
        by_source = {source["id"]: source["title"] for source in state["sources"]}
        chat_by_dimension = {}
        for item in state["evidence"]:
            chat_by_dimension.setdefault(item["dimension"], set()).add(by_source[item["source_id"]])
        chat_queries = {dimension["key"]: dimension["query"] for dimension in state["plan"]["dimensions"]}
        for block in worksheet["blocks"]:
            self.assertEqual(chat_queries[block["key"]], block["query"], block["key"])
            self.assertEqual(chat_by_dimension.get(block["key"], set()),
                             set(self._titles(block["items"])), block["key"])


class SharedCallTest(unittest.TestCase):
    """The one model call, and what happens when the reply is not JSON."""

    def test_a_reply_that_is_not_json_is_asked_for_once_more(self):
        replies = iter(["I am sorry, I cannot return JSON.", '{"paragraphs": ["One."]}'])
        with mock.patch("bp.product.prose._call", side_effect=lambda *a, **k: next(replies)) as call:
            out = completion._ask("system", {"a": 1})
        self.assertEqual(out, {"paragraphs": ["One."]})
        self.assertEqual(call.call_count, 2)

    def test_two_replies_that_are_not_json_raise_rather_than_return_an_empty_paper(self):
        from bp.product import prose
        with mock.patch("bp.product.prose._call", side_effect=lambda *a, **k: "still not JSON"):
            with self.assertRaises(prose.ProseError):
                completion._ask("system", {"a": 1})

    def test_a_dimension_label_is_not_an_invented_name(self):
        """The paper says "Social conditions"; that is the heading, not a new fact."""
        facts = completion._facts([{
            "key": "social", "label": "Social",
            "items": [{"text": "Hospitality firms rely on relationship marketing.", "provenance": "user"}]}])
        data = {"introduction": ["Social conditions shape adoption in Morocco."], "context": [""],
                "lead": "lead", "groups": {"social": ["Social conditions matter."]},
                "discussion": [""], "implications": [""], "limitations": [""], "conclusion": [""]}
        allow = completion._allowed_names(completion._profile("template_pestel"),
                                          {"unit": {"value": "Morocco"}, "region": "Global"})
        problems = completion._problems(data, facts, "A case in Morocco.", "short", ["social"], allow=allow)
        self.assertFalse([p for p in problems if p.startswith("name Social")], problems)


if __name__ == "__main__":
    unittest.main()
