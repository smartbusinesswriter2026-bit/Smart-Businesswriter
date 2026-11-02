"""Value Chain completion: the third framework on the shared engine.

The behaviour the Five Forces and PESTEL builds proved, applied to Porter's nine
activities: nine dimensions, sourced items or a named gap with a probe, an
industry as the unit of analysis, one paper, and a refusal rather than a thin
paper.  The framework supplies everything; the engine is unchanged.
"""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, completion  # noqa: E402

BRIEF = ("A grocery retailer is reviewing how its value chain creates value and where cost and differentiation "
         "come from, before deciding whether to open a new store format.")

INDUSTRY = "grocery retail"


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query, so the dimension gate can judge it."""
    return {"results": [{
        "title": "Grocery retail " + query[:70],
        "abstract": "Evidence on the activity named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Operations Management", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def blocks(result):
    return {block["key"]: block for block in result["blocks"]}


def complete(**kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete("template_value_chain", kwargs.pop("instruction", BRIEF),
                                   industry=kwargs.pop("industry", INDUSTRY), **kwargs)


class ValueChainCompletionTest(unittest.TestCase):
    def test_nine_activities_each_carry_a_sourced_item_or_a_named_gap(self):
        result = complete()
        self.assertEqual(result["template"], "template_value_chain")
        self.assertEqual(result["framework"], "Porter's Value Chain")
        self.assertEqual([block["key"] for block in result["blocks"]],
                         ["firm_infrastructure", "human_resource_management", "technology_development",
                          "procurement", "inbound_logistics", "operations", "outbound_logistics",
                          "marketing_and_sales", "service"])
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"], block["key"])
                    self.assertTrue(item["citation"], block["key"])

    def test_the_industry_is_the_unit_of_analysis(self):
        result = complete()
        self.assertEqual(result["unit"]["field"], "industry")
        self.assertEqual(result["unit"]["value"], INDUSTRY)
        self.assertTrue(result["blocks"][0]["query"].startswith(INDUSTRY + " "))

    def test_a_brief_without_an_industry_is_refused_with_an_actionable_reason(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="A firm is reviewing its activities and needs the value chain.", industry="")
        self.assertIn("market", str(refused.exception).lower())

    def test_an_accounting_brief_is_refused_not_filled_with_evidence(self):
        with self.assertRaises(ValueError) as refused:
            complete(instruction="Prepare the trial balance and the journal entries for the month.")
        self.assertIn("accounting", str(refused.exception).lower())

    def test_a_student_item_is_preserved(self):
        result = complete(student_items=[{"block": "service", "text": "The 2024 service standard applies."}])
        service = blocks(result)["service"]
        self.assertEqual(service["items"][0]["text"], "The 2024 service standard applies.")
        self.assertEqual(service["items"][0]["provenance"], "student")

    def test_no_evidence_is_written_from_general_background(self):
        with mock.patch("bp.product.sources.search_academic",
                        return_value={"results": [], "errors": [], "skipped": []}), \
                mock.patch("bp.product.sources.search_web", side_effect=web), \
                mock.patch("bp.product.prose._call", side_effect=AssertionError("the model must not run")):
            result = completion.complete("template_value_chain", BRIEF, industry=INDUSTRY)
        self.assertEqual(len(result["blocks"]), 9)
        for block in result["blocks"]:
            self.assertEqual(len(block["items"]), 1, block["key"])
            self.assertEqual(block["items"][0]["provenance"], "background", block["key"])
            self.assertFalse(block["items"][0]["source"], block["key"])
            self.assertFalse(block["gap"], block["key"])
            self.assertFalse(any(char.isdigit() for char in block["items"][0]["text"]), block["key"])

    def test_a_source_cannot_fill_two_activities(self):
        def everything(query, databases=None, limit=10, year_from=None):
            return {"results": [{
                "title": ("Grocery retail inbound logistics operations outbound delivery marketing sales service "
                          "support procurement purchasing technology human resources management finance planning"),
                "abstract": ("Inbound logistics, operations, outbound delivery, marketing, service, procurement, "
                             "technology, human resources and firm infrastructure in one market."),
                "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
                "venue": "Journal", "doi": "10.1/same", "url": "https://doi.org/10.1/same",
                "database": "OpenAlex"}], "errors": [], "skipped": []}

        with mock.patch("bp.product.sources.search_academic", side_effect=everything), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            result = completion.complete("template_value_chain", BRIEF, industry=INDUSTRY)
        sourced = [block for block in result["blocks"]
                   if any(item["provenance"] == "sourced" for item in block["items"])]
        self.assertEqual(len(sourced), 1)

    def test_the_paper_has_the_value_chain_outline_and_a_value_chain_title(self):
        result = complete()
        report = completion.draft(result, "apa", "draft", "mid")
        headings = [section["heading"] for section in report["sections"]]
        for required in ("Introduction", "Case and Market Context", "Porter's Value Chain",
                         "Inbound Logistics", "Operations", "Outbound Logistics", "Marketing and Sales",
                         "Service", "Procurement", "Technology Development", "Human Resource Management",
                         "Firm Infrastructure", "Discussion", "What the Evidence Shows",
                         "Implications for the Decision", "Limitations", "Conclusion", "References"):
            self.assertIn(required, headings)
        self.assertTrue(report["title"].startswith("Porter's Value Chain: "))
        self.assertEqual(report["framework"], "Porter's Value Chain")
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

    def test_the_model_prompt_speaks_value_chain_and_keeps_the_safety_rules(self):
        profile = dict(completion.LENGTHS["mid"])
        system = completion._system(completion.HEAD_SYSTEM, profile,
                                    completion._profile("template_value_chain"))
        self.assertIn("Value Chain", system)
        self.assertNotIn("PESTEL", system)
        self.assertIn("Do not add facts, numbers, names, sources or citations", system)
        self.assertIn("market", system)
        self.assertIn("generic terms in lower case", system)

    def test_the_framework_name_is_not_an_invented_name(self):
        facts = completion._facts([{
            "key": "inbound_logistics", "label": "Inbound logistics",
            "items": [{"text": "Retailers receive stock at regional depots.", "provenance": "user"}]}])
        data = {"introduction": ["Porter's Value Chain frames the decision for the market."], "context": [""],
                "lead": "lead", "groups": {"inbound_logistics": ["Inbound logistics matters."]},
                "discussion": [""], "implications": [""], "limitations": [""], "conclusion": [""]}
        allow = completion._allowed_names(completion._profile("template_value_chain"),
                                          {"unit": {"value": INDUSTRY}, "region": "Global"})
        problems = completion._problems(data, facts, "A case in grocery retail.", "short",
                                        ["inbound_logistics"], allow=allow)
        self.assertFalse([p for p in problems if p.startswith("name Porter")
                          or p.startswith("name Value") or p.startswith("name Chain")], problems)

    def test_an_empty_activity_does_not_block_the_paper(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"] if block["key"] != "service"]
        result["blocks"].append({"key": "service", "label": "Service", "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])

    def test_the_route_generates_a_paper_with_an_empty_activity(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"] if block["key"] != "human_resource_management"]

        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": result, "version": "draft"})
        self.assertEqual(status, 200, payload)

    def test_the_route_returns_a_value_chain_completion(self):
        with mock.patch("bp.product.completion.complete") as fake:
            fake.return_value = {"format": "bp-framework-completion/1", "template": "template_value_chain",
                                 "blocks": []}
            status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                         {"template": "template_value_chain", "instruction": BRIEF,
                                          "industry": INDUSTRY})
        self.assertEqual(status, 200)
        self.assertEqual(payload["template"], "template_value_chain")

    def test_an_unfinished_framework_still_names_the_real_options(self):
        # case_decision is a template with no completion profile, so it is refused
        # and the message names the frameworks that do run.
        with self.assertRaises(ValueError) as refused:
            completion.complete("case_decision", BRIEF)
        self.assertIn("Porter's Value Chain", str(refused.exception))


if __name__ == "__main__":
    unittest.main()
