"""The plan council: advocates propose, code verifies, an examiner decides.

No network is used here: a fake provider stands in for the model, so the
council's contract — closed catalogue, exact quotes, verified figures, a verdict
among approved readings only, and a fallback when nothing can be approved — is
tested as behaviour rather than described in prose.
"""

import json
import os
import unittest
from unittest import mock

from bp.product import capabilities, chat, council, verify

BRIEF = ("The grocery chain is assessing the Saudi market for a second branch; will it pay for itself? "
         "fixed cost 40000, price 25, variable 12.")


def reading(**overrides):
    base = {
        "reading": "cost-cover",
        "why": "the brief asks whether the branch pays for itself and gives its cost structure",
        "anchors": [{"quote": "will it pay for itself?", "answers": "decision"}],
        "frameworks": ["pestel"],
        "capabilities": [{"key": "breakeven", "because": "it tests whether the declared price covers costs"}],
        "figures": [{"input": "fixed", "written": "40000", "kind": "amount", "quote": "fixed cost 40000"}],
        "missing": ["the expected volume, for a margin of safety"],
        "not_included": [{"key": "npv", "reason": "no cash flows are given"}],
    }
    base.update(overrides)
    return json.dumps(base)


class FakeProvider:
    """Answers the advocates' calls with prepared texts, then the examiner's."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        if not self.answers:
            raise AssertionError("the council called the provider more often than expected")
        return self.answers.pop(0)

    def as_prose(self, messages, **kwargs):
        return self(messages)


class CouncilTest(unittest.TestCase):
    def test_three_advocates_and_an_examiner_choose_among_approved_readings(self):
        provider = FakeProvider([
            reading(),
            reading(reading="appraisal", frameworks=["pestel"],
                    capabilities=[{"key": "npv"}],
                    figures=[{"input": "rate", "written": "10%", "kind": "rate",
                              "quote": "will it pay for itself?"}],
                    not_included=[]),
            json.dumps({"reading": "nonsense", "why": "the branch will definitely succeed",
                        "anchors": [], "frameworks": ["pestel"],
                        "capabilities": [{"key": "astrology"}], "figures": [], "missing": []}),
            json.dumps({"chosen": 1, "criteria": {"coverage": "full"}, "dissent": "appraisal is defensible",
                        "confidence": "high"}),
        ])
        result = council.advise(BRIEF, capabilities.ENTRIES, ("pestel", "swot"), provider=provider)
        self.assertEqual(len(result["approved"]), 2)
        self.assertEqual(len(result["rejected"]), 1)
        self.assertEqual(result["rejected"][0]["reasons"][0]["check"], "catalogue")
        self.assertEqual(result["verdict"]["chosen"], 1)
        self.assertEqual(result["reading"]["reading"], "cost-cover")
        self.assertEqual(result["verdict"]["dissent"], "appraisal is defensible")
        # The third advocate's text never reached the examiner.
        examiner_prompt = json.dumps(provider.calls[-1])
        self.assertNotIn("astrology", examiner_prompt)

    def test_a_lone_approved_reading_needs_no_examiner(self):
        bad_quote = reading(anchors=[{"quote": "a sentence nobody wrote"}], figures=[])
        overclaim = reading(why="this will prove entry works", figures=[])
        provider = FakeProvider([reading(), bad_quote, overclaim])
        result = council.advise(BRIEF, capabilities.ENTRIES, ("pestel",), provider=provider)
        self.assertEqual(len(result["approved"]), 1)
        self.assertEqual(result["verdict"]["by"], "single approved reading")
        self.assertEqual(len(provider.calls), 3)

    def test_when_nothing_survives_verification_the_council_asks_instead(self):
        bad = json.dumps({"reading": "x", "why": "x", "anchors": [], "frameworks": ["pestel"],
                          "capabilities": [{"key": "astrology"}], "figures": [], "missing": []})
        result = council.advise(BRIEF, capabilities.ENTRIES, ("pestel",),
                                provider=FakeProvider([bad, bad, bad]))
        self.assertTrue(result["needs_question"])
        self.assertEqual(result["approved"], [])
        self.assertEqual(len(result["rejected"]), 3)

    def test_an_unreadable_answer_is_rejected_not_repaired(self):
        result = council.advise(BRIEF, capabilities.ENTRIES, ("pestel",),
                                provider=FakeProvider(["I think break-even is best."] * 3))
        self.assertTrue(result["needs_question"])
        self.assertEqual(result["rejected"][0]["reasons"][0]["detail"],
                         "the model returned no JSON object")

    def test_the_examiner_cannot_choose_an_unapproved_reading(self):
        provider = FakeProvider([reading(), reading(reading="appraisal",
                                                    capabilities=[{"key": "npv"}], not_included=[]),
                                 "not JSON at all",
                                 json.dumps({"chosen": 9, "confidence": "high", "dissent": ""})])
        result = council.advise(BRIEF, capabilities.ENTRIES, ("pestel",), provider=provider)
        self.assertEqual(result["verdict"]["chosen"], 1)


class ChatCouncilTest(unittest.TestCase):
    def test_without_the_flag_the_resolver_decides(self):
        with mock.patch.dict(os.environ, {"BP_PLAN_COUNCIL": "0"}, clear=False):
            state = chat.start(BRIEF, "management", "pestel")
        self.assertIsNone(state.get("council"))
        self.assertEqual([row["key"] for row in state["selection"]["selected"]], ["breakeven"])

    def test_with_the_flag_a_verified_reading_decides_and_is_recorded(self):
        provider = FakeProvider([reading(), reading(), reading(),
                                 json.dumps({"chosen": 1, "confidence": "high", "dissent": ""})])
        with mock.patch.dict(os.environ, {"BP_PLAN_COUNCIL": "1", "BP_OPENGO_API_KEY": "test"},
                             clear=False), \
                mock.patch.object(council.prose, "_call", side_effect=provider.as_prose):
            state = chat.start(BRIEF, "management")
        self.assertEqual([row["key"] for row in state["selection"]["selected"]], ["breakeven"])
        self.assertTrue(state["selection"]["selected"][0]["because"]["rule"].startswith("council:"))
        self.assertEqual(state["plan_models"][0]["role"], "council")
        self.assertTrue(state["plan_figures"])
        self.assertIn("approved", state["council"])

    def test_a_council_failure_falls_back_to_the_resolver_and_says_so(self):
        with mock.patch.dict(os.environ, {"BP_PLAN_COUNCIL": "1", "BP_OPENGO_API_KEY": "test"},
                             clear=False), \
                mock.patch.object(council, "advise", side_effect=council.CouncilError("no examiner")):
            state = chat.start(BRIEF, "management", "pestel")
        self.assertEqual([row["key"] for row in state["selection"]["selected"]], ["breakeven"])
        self.assertIn("could not decide", state["council"]["note"])

    def test_the_frozen_plan_records_the_council_as_the_reason(self):
        provider = FakeProvider([reading(), reading(), reading(),
                                 json.dumps({"chosen": 1, "confidence": "high", "dissent": ""})])
        with mock.patch.dict(os.environ, {"BP_PLAN_COUNCIL": "1", "BP_OPENGO_API_KEY": "test"},
                             clear=False), \
                mock.patch.object(council.prose, "_call", side_effect=provider.as_prose):
            state = chat.start(BRIEF, "management")
        for _ in range(20):
            question = chat.current_question(state)
            if not question:
                break
            if question["type"] == "choice":
                first = question["choices"][0]
                value = first[0] if isinstance(first, (list, tuple)) else first
            elif question["type"] == "number":
                value = "5"
            elif question["type"] == "items":
                value = "one; two"
            else:
                value = "the board decision"
            state = chat.answer(state, question["id"], value)
        state = chat.confirm_plan(state)
        record = state["plan_record"]
        self.assertEqual(record["models"][0]["role"], "council")
        self.assertEqual(record["capabilities"][0]["key"], "breakeven")
        self.assertTrue(record["figures"])
        self.assertTrue(chat.replay_check(state)["match"])


if __name__ == "__main__":
    unittest.main()
