"""The model helps a student who is unsure; it never invents the answer."""

import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import api, assist, chat, completion  # noqa: E402


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


def _chat_state():
    return {
        "brief": "A bakery in Intramuros with three outlets and repeat customers.",
        "answers": {"decision": "should the bakery open a fourth outlet",
                    "strengths": []},
        "framework": "swot",
        "evidence": [],
        "sources": [],
        "profile": "academic",
        "stage": "evidence",
    }


def propose(candidate, available=True):
    state = _chat_state()
    with mock.patch("bp.product.prose.available", return_value=available), \
            mock.patch("bp.product.prose._call",
                       return_value=json.dumps({"candidates": [candidate]})), \
            mock.patch("bp.product.prose._parse", side_effect=json.loads):
        return assist.propose(state, "strengths", "Strengths")


class ChatAssistTest(unittest.TestCase):
    def test_a_proposal_uses_only_the_students_own_words(self):
        out = propose("The bakery already serves repeat customers in Intramuros.")
        self.assertEqual(len(out["candidates"]), 1)
        self.assertIn("repeat customers", out["candidates"][0])

    def test_a_proposal_that_invents_a_number_is_refused(self):
        self.assertEqual(propose("The bakery has 92% customer retention.")["candidates"], [])

    def test_a_proposal_that_invents_a_name_is_refused(self):
        self.assertEqual(propose("Almarai already dominates this district.")["candidates"], [])

    def test_a_proposal_that_adds_a_link_is_refused(self):
        self.assertEqual(
            propose("See https://example.com/report for the data.")["candidates"], [])

    def test_a_proposal_without_the_students_words_is_refused(self):
        self.assertEqual(propose("Synergies will unlock shareholder value.")["candidates"], [])

    def test_no_model_configured_returns_no_proposal_and_no_error(self):
        self.assertEqual(propose("Three outlets in Intramuros.", available=False)["candidates"],
                         [])

    def test_the_proposal_records_which_cell_it_is_for(self):
        out = propose("Three outlets in Intramuros.")
        self.assertEqual(out["key"], "strengths")
        self.assertEqual(out["label"], "Strengths")

    def test_an_accepted_proposal_becomes_a_student_input(self):
        state = _chat_state()
        state["assist"] = {"strengths": {"candidates": ["Three outlets in Intramuros."]}}
        chat.accept_assist(state, "strengths", "Three outlets in Intramuros.")
        self.assertIn("Three outlets in Intramuros.",
                      " ".join(state["answers"]["strengths"]))

    def test_a_dismissed_proposal_is_not_added(self):
        state = _chat_state()
        state["assist"] = {"strengths": {"candidates": ["Three outlets in Intramuros."]}}
        chat.accept_assist(state, "strengths", None)
        self.assertEqual(state["answers"].get("strengths") or [], [])

    def test_the_students_own_wording_is_what_is_stored(self):
        state = _chat_state()
        state["answers"]["strengths"] = ["We bake on site every morning."]
        chat.accept_assist(state, "strengths", "Our bakers start before dawn.")
        self.assertEqual(state["answers"]["strengths"],
                         ["We bake on site every morning.", "Our bakers start before dawn."])


class AssistRouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-assist-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _case(self):
        status, state = api.handle("POST", "/api/cases/chat",
                                   {"brief": "A bakery in Intramuros with three outlets "
                                             "and repeat customers.",
                                    "framework": "swot"})
        self.assertEqual(status, 201, state)
        return state["id"]

    def test_the_route_offers_and_then_accepts_a_proposal(self):
        case_id = self._case()
        with mock.patch("bp.product.prose.available", return_value=True), \
                mock.patch("bp.product.prose._call",
                           return_value=json.dumps({"candidates": ["Three outlets in Intramuros."]})), \
                mock.patch("bp.product.prose._parse", side_effect=json.loads):
            status, offered = api.handle("POST", "/api/cases/chat/" + case_id + "/assist",
                                         {"key": "strengths", "label": "Strengths"})
            self.assertEqual(status, 200, offered)
            self.assertEqual(offered["assist"]["strengths"]["candidates"],
                             ["Three outlets in Intramuros."])
            status, accepted = api.handle("POST", "/api/cases/chat/" + case_id + "/assist",
                                          {"key": "strengths",
                                           "text": "Three outlets in Intramuros."})
        self.assertEqual(status, 200, accepted)
        self.assertIn("Three outlets in Intramuros.", accepted["answers"]["strengths"])

    def test_the_route_reports_a_missing_cell_key(self):
        case_id = self._case()
        status, body = api.handle("POST", "/api/cases/chat/" + case_id + "/assist", {})
        self.assertEqual(status, 422, body)
        self.assertIn("cell key", body["error"])

    def test_the_route_refuses_an_unknown_case(self):
        status, _body = api.handle("POST", "/api/cases/chat/000000000000/assist",
                                   {"key": "strengths"})
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
