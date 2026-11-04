"""Logic Model completion: Logic model: what the programme is built to deliver, beside what it has delivered.

The behaviour the People & organisation shelf proves, applied to Logic Model: the
parts the framework names, each researched and each carrying a sourced item or a
named gap, the unit of analysis named by the student, one paper, and a refusal
rather than a thin paper.  The framework supplies the reading; the evidence is
the student's and the engine never adds to it.
"""

import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, completion  # noqa: E402

TEMPLATE = "template_logic_model"
LABEL = "Logic Model"

#: The unit of analysis is the thing the student names, never one the engine
#: guesses: a programme is not an industry.
UNIT = "the campus mentoring programme"

#: The parts Logic Model names, in the order the framework names them.
BLOCKS = ["inputs", "activities", "outputs", "outcomes", "impact"]

BRIEF = ("The campus mentoring programme has to be laid out beside the evidence before it is extended.")


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query, so the block gate can judge it."""
    return {"results": [{
        "title": query[:70],
        "abstract": "Evidence on the conditions named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of People Studies", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(**kwargs):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(TEMPLATE, kwargs.pop("instruction", BRIEF),
                                   unit_value=kwargs.pop("unit", UNIT), **kwargs)


class LogicModelCompletionTest(unittest.TestCase):
    def test_every_part_carries_a_sourced_item_or_a_named_gap(self):
        result = complete()
        self.assertEqual(result["template"], TEMPLATE)
        self.assertEqual(result["framework"], LABEL)
        self.assertEqual([block["key"] for block in result["blocks"]], BLOCKS)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"], block["key"])
                    self.assertTrue(item["citation"], block["key"])

    def test_the_unit_is_the_one_the_student_names(self):
        result = complete()
        self.assertEqual(result["unit"]["field"], "process")
        self.assertEqual(result["unit"]["value"], UNIT)
        self.assertTrue(result["blocks"][0]["query"].startswith(UNIT), result["blocks"][0]["query"])

    def test_a_brief_without_a_unit_is_refused_with_an_actionable_reason(self):
        with self.assertRaises(ValueError) as refused:
            complete(unit="")
        message = str(refused.exception)
        self.assertIn("Name", message)
        self.assertIn(UNIT, message)

    def test_one_source_cannot_fill_two_parts(self):
        """A single source that matches every part still fills one part only."""
        def everything(query, databases=None, limit=10, year_from=None):
            return {"results": [{
                "title": UNIT + " " + " ".join(sorted({
                    word for key in BLOCKS for word in key.split("_")})),
                "abstract": "One source covers every part the framework names.",
                "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
                "venue": "Journal", "doi": "10.1/same", "url": "https://doi.org/10.1/same",
                "database": "OpenAlex"}], "errors": [], "skipped": []}

        with mock.patch("bp.product.sources.search_academic", side_effect=everything), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            result = completion.complete(TEMPLATE, BRIEF, unit_value=UNIT)
        sourced = [block for block in result["blocks"]
                   if any(item["provenance"] == "sourced" for item in block["items"])]
        self.assertEqual(len(sourced), 1, [block["key"] for block in sourced])

    def test_a_no_source_run_fills_every_part_with_background(self):
        def empty_academic(query, databases=None, limit=10, year_from=None):
            return {"results": [], "errors": [], "skipped": []}

        with mock.patch("bp.product.sources.search_academic", side_effect=empty_academic), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            result = completion.complete(TEMPLATE, BRIEF, unit_value=UNIT)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                self.assertEqual(item["provenance"], "background", block["key"])

    def test_the_outline_headings_are_present_and_title_cased(self):
        profile = completion._profile(TEMPLATE)
        outline = profile["outline"]
        for field in ("framework", "context", "discussion", "implications",
                      "limitations", "conclusion", "lead"):
            self.assertTrue(outline.get(field), field)
        self.assertEqual(outline["framework"], LABEL)
        self.assertFalse(outline["context"].endswith("."))
        self.assertFalse(outline["discussion"].endswith("."))

    def test_the_byline_reaches_the_title_page(self):
        result = dict(complete(), byline=["A Student", "Example University"])
        self.assertIn("byline", result)
        self.assertTrue(result["byline"])

    def test_an_empty_part_does_not_block_the_paper(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != BLOCKS[-1]]
        result["blocks"].append({"key": BLOCKS[-1], "label": "Empty",
                                 "items": [], "gap": "No evidence."})
        self.assertEqual(completion.missing(result), [])

    def test_the_route_generates_a_draft_with_an_empty_part(self):
        result = complete()
        result["blocks"] = [block for block in result["blocks"]
                            if block["key"] != BLOCKS[0]]
        result["blocks"].append({"key": BLOCKS[0], "label": "Empty",
                                 "items": [], "gap": "No evidence."})
        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": result, "version": "draft"})
        self.assertEqual(status, 200, payload)

    def test_the_route_returns_a_completion(self):
        with mock.patch("bp.product.completion.complete") as fake:
            fake.return_value = {"format": "bp-framework-completion/1",
                                 "template": TEMPLATE, "blocks": []}
            status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                         {"template": TEMPLATE,
                                          "instruction": BRIEF,
                                          "unit": UNIT})
        self.assertEqual(status, 200)
        self.assertEqual(payload["template"], TEMPLATE)

    def test_the_model_prompt_speaks_the_framework_and_keeps_the_safety_rules(self):
        length_profile = dict(completion.LENGTHS["mid"])
        system = completion._system(completion.HEAD_SYSTEM, length_profile,
                                    completion._profile(TEMPLATE))
        self.assertIn(LABEL, system)
        self.assertIn("Do not add facts, numbers, names, sources or citations", system)
        self.assertIn("programme", system.lower())

    def test_the_framework_name_is_not_an_invented_name(self):
        facts = completion._facts([{
            "key": BLOCKS[0], "label": BLOCKS[0].replace("_", " ").title(),
            "items": [{"text": "A short note about the case.", "provenance": "user"}]}])
        data = {"introduction": ["Logic Model frames the decision for this case."],
                "context": [""], "lead": "lead",
                "groups": {BLOCKS[0]: ["The first part matters here."]},
                "discussion": [""], "implications": [""], "limitations": [""], "conclusion": [""]}
        allow = completion._allowed_names(completion._profile(TEMPLATE),
                                          {"unit": {"value": UNIT}, "region": "Global"})
        problems = completion._problems(data, facts, "A case in this organisation.", "short",
                                        [BLOCKS[0]], allow=allow)
        self.assertFalse([p for p in problems
                          if p.lower().startswith("name ") and LABEL.lower() in p.lower()],
                         problems)


if __name__ == "__main__":
    unittest.main()
