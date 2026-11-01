"""The model helps a student who is unsure; it never invents the answer."""

import json
import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import completion  # noqa: E402


def _profile(mode="probe"):
    return {"blocks": [{"key": "S", "label": "Strengths", "fill": "quote"}],
            "voice": {"block_plural": "dimensions"},
            "assumption": mode}


def _blocks():
    return [{"key": "S", "label": "Strengths", "items": []}]


def _model_reply(payload, error=None):
    """Patch the prose layer so the model's answer is under the test's control."""
    def call(_messages, **_kwargs):
        if error:
            raise error
        return json.dumps(payload)

    return (mock.patch("bp.product.prose.available", return_value=True),
            mock.patch("bp.product.prose._call", side_effect=call),
            mock.patch("bp.product.prose._parse", side_effect=json.loads))


def suggest(payload, mode="question", error=None):
    available, call, parse = _model_reply(payload, error)
    with available, call, parse:
        return completion._suggest(_profile("probe" if mode == "question" else "case"),
                                   ["S"], "A bakery in Intramuros with three outlets.",
                                   {"value": "bakery"}, _blocks(), mode=mode)


class SuggestModeTest(unittest.TestCase):
    def test_a_probe_profile_gets_a_line_of_enquiry_not_an_assumption(self):
        out = suggest({"S": "Which of the three outlets serves the highest repeat demand?"})
        self.assertIn("S", out)
        self.assertTrue(out["S"].endswith("?"))

    def test_a_reply_with_a_number_is_refused(self):
        out = suggest({"S": "The bakery has 45% repeat customers."})
        self.assertNotIn("S", out)

    def test_a_reply_with_a_link_is_refused(self):
        out = suggest({"S": "See https://example.com for the study."})
        self.assertNotIn("S", out)

    def test_a_never_answered_model_returns_nothing_and_the_cell_falls_back(self):
        out = suggest({}, error=RuntimeError("no model"))
        self.assertEqual(out, {})

    def test_the_case_mode_still_returns_an_assumption_not_a_question(self):
        out = suggest({"S": "The bakery serves a dense catchment on foot."}, mode="assumption")
        self.assertIn("S", out)
        self.assertFalse(out["S"].endswith("?"))

    def test_an_assumption_mode_reply_that_is_a_question_is_refused(self):
        out = suggest({"S": "Which outlet serves the most customers?"}, mode="assumption")
        self.assertEqual(out, {})


def no_sources(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def no_web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


#: The value stream map is the catalogue's probe profile whose cells are
#: judgement calls: the pipeline leaves them to the student by design, which is
#: exactly the cell where a student who is unsure needs to be asked.
MAP_BRIEF = ("The campus catering team wants to map the lunch orders at the meal "
             "counter, from the request to the handover.")
JUDGEMENT_KEYS = ("value_added", "improvements")


def complete_map(payload):
    available, call, parse = _model_reply(payload)
    with mock.patch("bp.product.sources.search_academic", side_effect=no_sources), \
            mock.patch("bp.product.sources.search_web", side_effect=no_web), \
            available, call, parse:
        return completion.complete("template_value_stream_map", MAP_BRIEF,
                                   unit_value="the lunch orders at the meal counter")


class QuestionModeCompletionTest(unittest.TestCase):
    def setUp(self):
        self.result = complete_map({key: "How many orders wait for a till before being served?"
                                    for key in JUDGEMENT_KEYS})

    def test_a_judgement_cell_asks_a_question_instead_of_going_silent(self):
        for block in self.result["blocks"]:
            if block["key"] in JUDGEMENT_KEYS:
                self.assertTrue(block.get("proposal"), block["key"])
                self.assertIn("line of enquiry", block["gap"].lower())

    def test_the_gap_text_is_kept_and_the_question_is_added_to_it(self):
        for block in self.result["blocks"]:
            if block["key"] in JUDGEMENT_KEYS:
                self.assertIn("only you can state", block["gap"])
                self.assertIn("?", block["gap"])

    def test_the_question_is_not_written_into_the_paper_as_a_case_assumption(self):
        report = completion.draft(self.result)
        body = " ".join(" ".join(section.get("lines") or []) for section in report["sections"])
        self.assertNotIn("Case assumption: How many orders", body)

    def test_the_cell_carries_the_question_and_is_never_blank(self):
        cells = completion._figure_cells(self.result["blocks"])
        for key in JUDGEMENT_KEYS:
            self.assertEqual(cells[key]["bullets"], [], key)
            self.assertIn("line of enquiry", cells[key]["gap"].lower(), key)

    def test_a_gap_stays_a_gap_so_it_is_still_counted(self):
        for block in self.result["blocks"]:
            if block["key"] in JUDGEMENT_KEYS:
                self.assertEqual(block["items"], [], block["key"])
        # a proposed question does not close the gate: the cell is still a gap
        missing = completion.missing(self.result)
        self.assertIn("Value-added assessment", missing)
        self.assertIn("Improvement opportunities", missing)


if __name__ == "__main__":
    unittest.main()
