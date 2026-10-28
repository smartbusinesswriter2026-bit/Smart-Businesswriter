"""The reading verifier, the input normaliser and the frozen plan record.

These are the parts that make a reading checkable without a model: a closed
catalogue, exact quotes, figures normalised by code, and a plan that hashes.
"""

import unittest
from decimal import Decimal

from bp import methods
from bp.product import api as product_api
from bp.product import capabilities, chat, paper, verify

BRIEF = ("The grocery chain is assessing the Saudi market for a second branch; will it pay for itself? "
         "fixed cost 40000, price 25, variable 12.")


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


def setUpModule():
    product_api.attach_compute(lambda values: methods.breakeven(values))
    product_api.attach_methods(_run, methods.describe)


def answer_all(state):
    for _ in range(60):
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
    return state


class NormaliserTest(unittest.TestCase):
    def test_it_reads_the_ways_people_write_figures(self):
        cases = [("40000", "amount", "40000"), ("40,000", "amount", "40000"),
                 ("SAR 1.2m", "amount", "1200000"), ("1.2 million", "amount", "1200000"),
                 ("about 40k", "amount", "40000"), ("12%", "rate", "0.12"),
                 ("0.12", "rate", "0.12"), ("2.5bn", "amount", "2500000000")]
        for written, kind, expected in cases:
            value, steps = verify.normalise_number(written, kind)
            self.assertEqual(Decimal(value), Decimal(expected), written)
            self.assertIsInstance(steps, list)

    def test_it_refuses_the_classic_misreadings(self):
        with self.assertRaises(verify.VerifyError):
            verify.normalise_number("12", "rate")           # a bare rate above one
        with self.assertRaises(verify.VerifyError):
            verify.normalise_number("12%", "amount")        # a percentage for an amount
        with self.assertRaises(verify.VerifyError):
            verify.normalise_number("USD 500", "amount", currency="SAR")
        with self.assertRaises(verify.VerifyError):
            verify.normalise_number("40000 to 50000", "amount")
        with self.assertRaises(verify.VerifyError):
            verify.normalise_number("about", "amount")

    def test_it_uses_the_schema_description_to_classify_an_input(self):
        schema = methods.describe("breakeven")["input_schema"]
        self.assertEqual(verify.input_kind("fixed", schema["fixed"]), "amount")
        self.assertEqual(verify.input_kind("price", schema["price"]), "amount")
        wacc = methods.describe("wacc")["input_schema"]
        self.assertEqual(verify.input_kind("cost_of_equity", wacc["cost_of_equity"]), "rate")
        self.assertEqual(verify.input_kind("cost_of_debt_after_tax", wacc["cost_of_debt_after_tax"]), "rate")
        # "interest-bearing debt" is a quantity of money, not a rate.
        self.assertEqual(verify.input_kind("debt_value", wacc["debt_value"]), "amount")
        self.assertEqual(verify.input_kind("equity_value", wacc["equity_value"]), "amount")
        leverage = methods.describe("leverage_analysis")["input_schema"]
        self.assertEqual(verify.input_kind("interest_expense", leverage["interest_expense"]), "amount")


class ReadingTest(unittest.TestCase):
    def _reading(self, **overrides):
        reading = {
            "reading": "cost-cover",
            "why": "the brief asks whether the branch pays for itself and gives the cost structure",
            "anchors": [{"quote": "will it pay for itself?", "answers": "decision"}],
            "frameworks": ["pestel"],
            "capabilities": [{"key": "breakeven"}],
            "figures": [{"input": "fixed", "written": "40000", "kind": "amount",
                         "quote": "fixed cost 40000"}],
            "missing": [],
        }
        reading.update(overrides)
        return reading

    def test_a_clean_reading_is_approved(self):
        problems = verify.verify_reading(self._reading(), capabilities.ENTRIES,
                                         ("pestel", "swot", "five_forces"), BRIEF)
        self.assertEqual(problems, [])

    def test_an_unknown_capability_is_refused(self):
        reading = self._reading(capabilities=[{"key": "astrology"}])
        problems = verify.verify_reading(reading, capabilities.ENTRIES, ("pestel",), BRIEF)
        self.assertEqual([problem["check"] for problem in problems], ["catalogue"])

    def test_a_capability_that_does_not_fit_the_framework_is_refused(self):
        reading = self._reading(frameworks=["vrio"])
        problems = verify.verify_reading(reading, capabilities.ENTRIES, ("vrio",), BRIEF)
        self.assertIn("does not fit", problems[0]["detail"])

    def test_a_quote_that_is_not_in_the_brief_is_refused(self):
        reading = self._reading(anchors=[{"quote": "a sentence nobody wrote"}])
        problems = verify.verify_reading(reading, capabilities.ENTRIES, ("pestel",), BRIEF)
        self.assertEqual([problem["check"] for problem in problems], ["provenance"])

    def test_a_figure_without_a_quote_or_with_a_bad_unit_is_refused(self):
        problems = verify.verify_reading(self._reading(figures=[{"input": "fixed", "written": "40000"}]),
                                         capabilities.ENTRIES, ("pestel",), BRIEF)
        self.assertEqual([problem["check"] for problem in problems], ["provenance"])
        problems = verify.verify_reading(
            self._reading(figures=[{"input": "fixed", "written": "12%", "kind": "amount",
                                    "quote": "fixed cost 40000"}]),
            capabilities.ENTRIES, ("pestel",), BRIEF)
        self.assertEqual([problem["check"] for problem in problems], ["filing"])

    def test_a_rationale_that_overclaims_is_refused(self):
        reading = self._reading(why="this will prove the branch is profitable and recommend entry")
        problems = verify.verify_reading(reading, capabilities.ENTRIES, ("pestel",), BRIEF)
        self.assertEqual([problem["check"] for problem in problems], ["licence"])

    def test_a_reading_must_say_what_is_missing(self):
        reading = self._reading()
        reading.pop("missing")
        problems = verify.verify_reading(reading, capabilities.ENTRIES, ("pestel",), BRIEF)
        self.assertEqual([problem["check"] for problem in problems], ["completeness"])


class PlanRecordTest(unittest.TestCase):
    def _confirmed(self):
        state = answer_all(chat.start(BRIEF, "management", "pestel"))
        return chat.confirm_plan(state)

    def test_confirming_freezes_a_plan_that_replays(self):
        state = self._confirmed()
        record = state["plan_record"]
        self.assertEqual(record["format"], verify.FORMAT)
        self.assertEqual(record["brief_hash"], verify.brief_hash(BRIEF))
        self.assertEqual([row["key"] for row in record["capabilities"]], ["breakeven"])
        self.assertTrue(chat.replay_check(state)["match"])

    def test_tampering_with_the_record_is_visible(self):
        state = self._confirmed()
        state["plan_record"]["capabilities"].append({"key": "npv", "because": None})
        self.assertFalse(chat.replay_check(state)["match"])

    def test_a_figure_that_no_longer_reproduces_blocks_the_paper(self):
        state = self._confirmed()
        state = chat.attach_computation(state, "breakeven",
                                        {"fixed": "40000", "price": "25", "variable": "12"})
        state["computations"]["breakeven"]["result"]["breakeven_units"] = "1"
        state["stage"] = "evidence"
        state["evidence"] = []
        state["gaps"] = []
        state = chat.draft(state, accepted_ids=[], implications="The branch must reach its volume.")
        self.assertTrue(state["recompute_problems"])
        self.assertIn("no longer reproduces", " ".join(state["draft"]["missing"]))
        with self.assertRaises(paper.ExportBlocked):
            chat.docx_bytes(state)

    def test_a_computation_section_opens_with_its_declared_inputs(self):
        state = self._confirmed()
        state = chat.attach_computation(state, "breakeven",
                                        {"fixed": "40000", "price": "25", "variable": "12"})
        state["stage"] = "evidence"
        state["evidence"] = []
        state["gaps"] = []
        state = chat.draft(state, accepted_ids=[], implications="The branch must reach its volume.")
        section = [row for row in state["draft"]["outline"]
                   if row.get("heading") == "Break-even Analysis"][0]
        self.assertEqual(section["lines"][0],
                         "Declared inputs: fixed 40,000; price 25; variable 12.")


if __name__ == "__main__":
    unittest.main()
