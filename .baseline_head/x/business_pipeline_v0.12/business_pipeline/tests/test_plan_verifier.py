"""The reading verifier, the input normaliser and the frozen plan record.

These are the parts that make a reading checkable without a model: a closed
catalogue, exact quotes, figures normalised by code, and a plan that hashes.
"""

import io
import unittest
import zipfile
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


class FigureApplicationTest(unittest.TestCase):
    """The brief's own figures reach the plan; nothing is typed twice, guessed or dropped."""

    def _planned(self, figures):
        state = answer_all(chat.start(BRIEF, "management", "pestel"))
        state["plan_figures"] = figures
        chat.apply_figures(state)
        return state

    def _figures(self, **overrides):
        base = [{"input": "fixed", "written": "40,000", "kind": "amount", "quote": "fixed cost 40000"},
                {"input": "price", "written": "25", "kind": "amount", "quote": "price 25"},
                {"input": "variable", "written": "12", "kind": "amount", "quote": "variable 12"}]
        for row in base:
            row.update(overrides.get(row["input"]) or {})
        return base

    def test_a_declared_figure_lands_in_the_inputs_and_in_the_plan_card(self):
        state = self._planned(self._figures())
        applied = state["plan_figures_applied"]["breakeven"]
        self.assertEqual(applied, {"fixed": "40000", "price": "25", "variable": "12"})
        card = [row for row in state["plan"]["capabilities"] if row["key"] == "breakeven"][0]
        self.assertEqual(card["figures"]["fixed"], "40000")
        self.assertEqual(card["figure_quotes"]["fixed"], "fixed cost 40000")
        self.assertEqual(state["plan"]["figure_problems"], [])

    def test_the_offered_figures_still_pass_through_the_core_and_the_guard(self):
        state = self._planned(self._figures())
        state = chat.attach_computation(state, "breakeven", state["plan_figures_applied"]["breakeven"])
        self.assertTrue(state["computations"]["breakeven"]["ok"])
        self.assertEqual(chat._recompute_guard(state), [])

    def test_a_figure_the_case_does_not_support_is_refused_and_named(self):
        state = self._planned(self._figures(fixed={"written": "12%"}))
        self.assertNotIn("fixed", state["plan_figures_applied"]["breakeven"])
        problems = state["plan"]["figure_problems"]
        self.assertEqual(len(problems), 1)
        self.assertEqual(problems[0]["input"], "fixed")
        self.assertIn("percentage", problems[0]["refused"])

    def test_two_figures_for_one_input_are_refused_rather_than_chosen_between(self):
        figures = self._figures()
        figures.append({"input": "fixed", "written": "50000", "kind": "amount", "quote": "fixed cost 40000"})
        state = self._planned(figures)
        self.assertNotIn("fixed", state["plan_figures_applied"]["breakeven"])
        self.assertIn("more than one figure",
                      " ".join(row.get("refused", "") for row in state["plan"]["figure_problems"]))

    def test_a_figure_no_selected_computation_needs_is_recorded_as_unused(self):
        figures = self._figures() + [{"input": "discount_rate", "written": "10%", "kind": "rate",
                                      "quote": "a discount rate of 10 percent"}]
        state = self._planned(figures)
        unused = [row for row in state["plan"]["figure_problems"] if row.get("unused")]
        self.assertEqual(len(unused), 1)
        self.assertIn("discount_rate", unused[0]["unused"])

    def test_without_a_reading_nothing_is_offered(self):
        state = answer_all(chat.start(BRIEF, "management", "pestel"))
        self.assertEqual(state["plan_figures_applied"], {})
        self.assertEqual(state["plan"]["capabilities"][0]["figures"], {})


class ClaimGateTest(unittest.TestCase):
    """A paper may name a limit; it may not claim more than a method licenses."""

    def test_an_unqualified_claim_is_named(self):
        problems = verify.overclaims("The analysis proves that the branch succeeds.")
        self.assertEqual(problems[0]["claim"], "proves")
        self.assertIn("branch succeeds", problems[0]["sentence"])

    def test_a_negated_limit_is_not_a_claim(self):
        for text in ("The analysis does not prove that entry succeeds.",
                     "The figure is not a guarantee about the future.",
                     "It cannot establish that entry is safe.",
                     "No calculation leads to that conclusion.",
                     "The figures do not change, and the analysis does not prove entry works."):
            self.assertEqual(verify.overclaims(text), [], text)

    def test_a_negated_clause_does_not_excuse_the_next_clause(self):
        problems = verify.overclaims("The figures do not change, and the analysis proves entry works.")
        self.assertEqual([problem["claim"] for problem in problems], ["proves"])

    def test_the_draft_scans_its_own_sentences_and_the_gate_blocks_the_export(self):
        state = answer_all(chat.start(BRIEF, "management", "pestel"))
        state = chat.attach_computation(state, "breakeven",
                                        {"fixed": "40000", "price": "25", "variable": "12"})
        state["stage"] = "evidence"
        state["evidence"] = []
        state["gaps"] = []
        state = chat.draft(state, accepted_ids=[],
                           implications="This analysis guarantees that the branch will pay for itself.")
        self.assertTrue(state["claim_problems"])
        self.assertIn("guarantees", " ".join(state["claim_problems"]))
        self.assertTrue(any("guarantees" in item for item in state["draft"]["missing"]))
        with self.assertRaises(paper.ExportBlocked):
            chat.docx_bytes(state)

    def test_a_source_sentence_or_a_limit_is_not_the_paper_s_own_claim(self):
        sections = [paper.section("Discussion", paper.H2,
                                  [paper.paragraph(["The study proves entry fails (Smith, 2020)."])]),
                    paper.section("Limitations", paper.H2,
                                  [paper.paragraph(["The method is not a guarantee that the P80 will hold."])]),
                    paper.section("Implications", paper.H1,
                                  [paper.paragraph(["The declared volume proves the branch pays."])])]
        problems = chat._claim_scan(sections)
        self.assertEqual(len(problems), 1)
        self.assertIn("Implications", problems[0])
        self.assertIn("proves", problems[0])

    def test_an_honest_limit_does_not_block_the_draft(self):
        state = answer_all(chat.start(BRIEF, "management", "pestel"))
        state = chat.attach_computation(state, "breakeven",
                                        {"fixed": "40000", "price": "25", "variable": "12"})
        state["stage"] = "evidence"
        state["evidence"] = []
        state["gaps"] = []
        state = chat.draft(state, accepted_ids=[],
                           implications="The break-even figure does not prove that the branch will reach its volume.")
        self.assertEqual(state["claim_problems"], [])


CHAIN_BRIEF = ("The grocery chain is entering the Saudi market and needs the net present value of a branch "
               "that costs 100000 and returns 40000 a year for four years, at its cost of capital. "
               "The equity is 1000 at a required return of 11%, the debt is 500 at 5% after tax.")


class PaperFormatTest(unittest.TestCase):
    """The paper's own wording: a quoted limitation is not punctuated twice, and a
    chained figure says where it came from in the export as well as on screen."""

    def _drafted(self):
        state = answer_all(chat.start(CHAIN_BRIEF, "management", "pestel"))
        for key in ("wacc", "npv"):
            if not capabilities.carries(state["selection"], key):
                state = chat.set_capability(state, key)
        if capabilities.carries(state["selection"], "capm"):
            state = chat.set_capability(state, "capm", False, "the rate is declared in the brief")
        state = chat.confirm_plan(state)
        state = chat.run_capability(state, "wacc", {"equity_value": "1000", "debt_value": "500",
                                                    "cost_of_equity": "0.11",
                                                    "cost_of_debt_after_tax": "0.05"})
        state = chat.run_capability(state, "npv",
                                    {"rate": state["dependency_inputs"]["npv"]["rate"],
                                     "cashflows": ["-100000", "40000", "40000", "40000", "40000"]})
        state["stage"] = "evidence"
        state["evidence"] = []
        state["gaps"] = []
        return chat.draft(state, accepted_ids=[],
                          implications="The appraisal depends on the five declared flows.")

    def test_a_quoted_limitation_is_not_given_a_second_full_stop(self):
        state = self._drafted()
        limitations = [line for heading, lines in state["draft"]["sections"]
                       if heading == "Limitations" for line in lines]
        self.assertTrue(limitations)
        for line in limitations:
            self.assertNotIn("..", line)

    def test_the_export_states_where_a_chained_figure_came_from(self):
        state = self._drafted()
        data = chat.docx_bytes(state, byline=["A Student", "Example University", "BUS301", "Dr A"])
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            body = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("from the cost of capital result", body)
        self.assertIn("29,588", body)


if __name__ == "__main__":
    unittest.main()
