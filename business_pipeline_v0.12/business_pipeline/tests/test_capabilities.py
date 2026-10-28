"""Capability model: the paper carries a computation only when the brief needs one.

These tests cover the five rows of the matrix in docs/CONDUCTOR_MANUAL.md §7.5
for the registered capabilities: not selected, selected and valid, refused,
selected without figures, and the one ambiguity question.  They also cover the
generic invariants (one per intent, hash reproducibility, drop removes the
requirement) so a new catalogue entry is covered by the matrix rather than by a
new file.

The frozen core is attached exactly as the server attaches it; nothing is
computed in the product layer.
"""

import unittest
from decimal import Decimal

from bp import methods
from bp.product import api as product_api
from bp.product import capabilities, chat, paper

BRIEF = ("The grocery chain is assessing the Saudi market for a second branch; "
         "it needs to know whether the branch will pay for itself. fixed cost 40000, "
         "price 25, variable 12.")


def _run_method(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


def setUpModule():
    product_api.attach_compute(lambda values: methods.breakeven(values))
    product_api.attach_methods(_run_method, methods.describe)


def answer_all(state):
    """Answer the question bank the way a student would, first option each time."""
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


def draftable(state):
    """Skip the network: the paper is drafted from no accepted evidence."""
    state["stage"] = "evidence"
    state["evidence"] = []
    state["gaps"] = []
    state = chat.confirm_plan(state) if state.get("stage") == "plan" else state
    return state


def headings(state):
    return [section.get("heading") for section in state["draft"].get("outline") or []]


class ResolutionTest(unittest.TestCase):
    def test_a_framework_only_brief_selects_nothing(self):
        selection = capabilities.resolve("Assess the Saudi market for a grocery chain entering the country.",
                                         "pestel")
        self.assertEqual(selection["selected"], [])
        self.assertIsNone(selection["question"])

    def test_a_cost_question_selects_break_even(self):
        selection = capabilities.resolve(BRIEF, "pestel")
        self.assertEqual([row["key"] for row in selection["selected"]], ["breakeven"])
        because = selection["selected"][0]["because"]
        self.assertTrue(because["rule"].startswith("cue:"))
        self.assertIn("pay for itself", because["quote"])

    def test_a_cue_without_figures_asks_exactly_one_question(self):
        state = chat.start("The grocery chain is assessing the Saudi market; will the branch pay for itself?",
                           "management")
        self.assertIsNotNone(state["selection"]["question"])
        self.assertEqual(state["selection"]["selected"], [])
        self.assertTrue(chat.current_question(state)["id"].startswith("capability:"))

    def test_the_question_answer_is_recorded_both_ways(self):
        state = chat.start("The grocery chain is assessing the Saudi market; will the branch pay for itself?",
                           "management")
        answered = chat.answer(state, "capability:breakeven", "yes")
        self.assertEqual([row["key"] for row in answered["selection"]["selected"]], ["breakeven"])
        again = chat.start("The grocery chain is assessing the Saudi market; will the branch pay for itself?",
                           "management")
        declined = chat.answer(again, "capability:breakeven", "no")
        self.assertEqual(declined["selection"]["selected"], [])
        self.assertEqual(declined["selection"]["not_included"][0]["key"], "breakeven")

    def test_one_capability_per_intent_and_the_rest_are_named(self):
        brief = ("The grocery chain appraises a branch in the Saudi market with a net present value and an "
                 "internal rate of return on the same declared cash flows.")
        selection = capabilities.resolve(brief, "pestel")
        self.assertEqual([row["key"] for row in selection["selected"]], ["npv"])
        self.assertIn("irr", [row["key"] for row in selection["not_included"]])

    def test_the_selection_is_hashed_and_reproducible(self):
        first = capabilities.resolve(BRIEF, "pestel")
        second = capabilities.resolve(BRIEF, "pestel")
        self.assertEqual(first["hash"], second["hash"])
        self.assertTrue(first["hash"].startswith("sha256:"))
        other = capabilities.resolve(BRIEF, "swot")
        self.assertNotEqual(first["hash"], other["hash"])

    def test_every_registered_entry_declares_what_the_checklist_requires(self):
        for key, row in capabilities.ENTRIES.items():
            self.assertTrue(row["any_of"], key)
            self.assertTrue(row["slot"] and len(row["slot"]) == 2, key)
            self.assertIn(row["intent"], row["intent"], key)
            self.assertIsInstance(row["priority"], int, key)
            self.assertTrue(row["applies_to"], key)


class RunnerTest(unittest.TestCase):
    def _ready(self, brief=BRIEF):
        state = answer_all(chat.start(brief, "management"))
        return chat.confirm_plan(state)

    def test_a_capability_the_paper_does_not_carry_is_refused(self):
        state = self._ready("The grocery chain is assessing the Saudi market for a second branch.")
        self.assertEqual(state["selection"]["selected"], [])
        with self.assertRaises(chat.ChatError):
            chat.run_capability(state, "breakeven",
                                {"fixed": "40000", "price": "25", "variable": "12"})

    def test_the_declared_figures_are_validated_against_the_frozen_schema(self):
        state = self._ready()
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "breakeven", {"fixed": "40000", "price": "25"})
        self.assertIn("variable cost per unit", str(caught.exception))

    def test_a_bad_series_item_is_named_not_guessed(self):
        brief = ("The grocery chain appraises a branch in the Saudi market: net present value of an outlay of "
                 "100000 that returns 40000 a year at a discount rate of 10 percent.")
        state = self._ready(brief)
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "npv", {"rate": "0.10", "cashflows": ["-100000", "abc"]})
        self.assertIn("cash flows", str(caught.exception))

    def test_the_core_result_is_stored_verbatim(self):
        brief = ("The grocery chain appraises a branch in the Saudi market: net present value of an outlay of "
                 "100000 that returns 40000 a year for four years at a discount rate of 10 percent.")
        state = self._ready(brief)
        chat.run_capability(state, "npv", {"rate": "0.10",
                                           "cashflows": ["-100000", "40000", "40000", "40000", "40000"]})
        recorded = state["computations"]["npv"]
        self.assertTrue(recorded["ok"])
        # the initial-test case in docs: NPV 26,794.62 on these flows
        self.assertEqual(round(Decimal(recorded["result"]["npv"]), 2), Decimal("26794.62"))

    def test_a_refused_figure_keeps_the_core_message_and_reports_no_number(self):
        state = self._ready(BRIEF)
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "breakeven", {"fixed": "40000", "price": "10", "variable": "12"})
        self.assertIn("price must exceed variable cost", str(caught.exception))
        self.assertFalse(state["computations"]["breakeven"]["ok"])
        self.assertIn("error", state["computations"]["breakeven"])

    def test_records_rows_are_validated(self):
        brief = ("The grocery chain is assessing the two products in its Saudi market and their product mix, "
                 "with fixed cost 50000 and declared unit costs.")
        state = self._ready(brief)
        self.assertIn("multi_product_breakeven", [row["key"] for row in state["selection"]["selected"]])
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "multi_product_breakeven",
                                {"fixed_costs": "50000",
                                 "products": [{"name": "A", "price": "25", "variable_cost": "15",
                                               "mix_units": "3"}]})
        self.assertIn("at least 2 rows", str(caught.exception))
        chat.run_capability(state, "multi_product_breakeven", {
            "fixed_costs": "50000",
            "products": [{"name": "A", "price": "25", "variable_cost": "15", "mix_units": "3"},
                         {"name": "B", "price": "40", "variable_cost": "28", "mix_units": "1"}]})
        self.assertTrue(state["computations"]["multi_product_breakeven"]["ok"])

    def test_an_either_or_input_is_enforced(self):
        brief = ("The grocery chain is assessing the Saudi market and the cost of equity for the branch, "
                 "with capm on a declared risk-free rate and market return.")
        state = self._ready(brief)
        self.assertIn("capm", [row["key"] for row in state["selection"]["selected"]])
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "capm", {"risk_free_rate": "0.04", "market_return": "0.10"})
        self.assertIn("beta", str(caught.exception))
        chat.run_capability(state, "capm", {"risk_free_rate": "0.04", "market_return": "0.10",
                                            "beta": "1.2"})
        self.assertTrue(state["computations"]["capm"]["ok"])

    def test_a_bond_takes_a_price_or_a_yield_but_not_neither(self):
        brief = ("The grocery chain is entering the Saudi market and financing the expansion with a bond: price "
                 "and yield on the declared face value, coupon and maturity.")
        state = self._ready(brief)
        self.assertIn("bond_analysis", [row["key"] for row in state["selection"]["selected"]])
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "bond_analysis",
                                {"face_value": "1000", "coupon_rate": "0.08", "years_to_maturity": "5"})
        self.assertIn("yield to maturity", str(caught.exception))
        chat.run_capability(state, "bond_analysis",
                            {"face_value": "1000", "coupon_rate": "0.08", "years_to_maturity": "5",
                             "yield_to_maturity": "0.06"})
        self.assertTrue(state["computations"]["bond_analysis"]["ok"])

    def test_a_minimum_number_of_figures_is_required(self):
        brief = ("The grocery chain is assessing the Saudi market and needs a ratio analysis of the branch's "
                 "declared statement figures.")
        state = self._ready(brief)
        self.assertIn("ratio_analysis", [row["key"] for row in state["selection"]["selected"]])
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "ratio_analysis", {"current_assets": "200000"})
        self.assertIn("at least 2", str(caught.exception))

    def test_an_enum_input_is_required_and_checked(self):
        brief = ("The grocery chain is entering the Saudi market and needs a multiples valuation against a "
                 "declared peer multiple for its ebitda.")
        state = self._ready(brief)
        self.assertIn("multiples_valuation", [row["key"] for row in state["selection"]["selected"]])
        with self.assertRaises(chat.ChatError) as caught:
            chat.run_capability(state, "multiples_valuation",
                                {"subject_value": "500000", "peer_multiple": "8"})
        self.assertIn("earnings", str(caught.exception))
        chat.run_capability(state, "multiples_valuation",
                            {"metric": "ebitda", "subject_value": "500000", "peer_multiple": "8"})
        self.assertTrue(state["computations"]["multiples_valuation"]["ok"])

    def test_a_group_comparison_takes_named_columns(self):
        brief = ("The grocery chain is entering the Saudi market and the pilot compares the means of a control "
                 "and a treated group of observations.")
        state = self._ready(brief)
        self.assertIn("welch_t", [row["key"] for row in state["selection"]["selected"]])
        chat.run_capability(state, "welch_t",
                            {"groups": {"control": ["10", "11", "12", "13", "14"],
                                        "treated": ["14", "15", "16", "17", "18"]}})
        self.assertTrue(state["computations"]["welch_t"]["ok"])

    def test_a_regression_brief_is_not_refused_as_an_accounting_computation(self):
        brief = ("The grocery chain is entering the Saudi market and a regression on the declared observations "
                 "of sales against advertising.")
        state = chat.start(brief, "management")
        self.assertEqual(state["stage"], "clarify")
        self.assertIn("ols", [row["key"] for row in state["selection"]["selected"]])

    def test_a_statistical_paper_states_the_result_without_causation(self):
        brief = ("The grocery chain is entering the Saudi market and needs a chi-square association between two "
                 "categories of declared counts.")
        state = draftable(answer_all(chat.start(brief, "management")))
        chat.attach_computation(state, "chi_square", {"table": [[10, 20], [30, 15]]})
        state = chat.draft(state, accepted_ids=[], implications="The counts suggest an association.")
        section = [row for row in state["draft"]["outline"]
                   if row.get("heading") == "Association Between Categories"][0]
        text = " ".join(section.get("lines") or [])
        self.assertIn("chi-square", text)
        self.assertIn("does not establish", text)
        self.assertNotIn("causes", text.replace("one causes the other", ""))

    def test_an_operations_paper_names_the_bottleneck(self):
        brief = ("The grocery chain is entering the Saudi market and the packing line capacity is the bottleneck "
                 "against declared demand.")
        state = draftable(answer_all(chat.start(brief, "management")))
        chat.attach_computation(state, "capacity_analysis", {
            "demand": "500",
            "resources": [{"name": "line A", "available_hours": "8", "minutes_per_unit": "2"},
                          {"name": "line B", "available_hours": "8", "minutes_per_unit": "1"}]})
        state = chat.draft(state, accepted_ids=[], implications="The line constrains the entry plan.")
        section = [row for row in state["draft"]["outline"]
                   if row.get("heading") == "Capacity and Bottleneck"][0]
        text = " ".join(section.get("lines") or [])
        self.assertIn("line A", text)
        self.assertIn("short of the declared demand", text)

    def test_a_cohort_paper_takes_a_retention_matrix(self):
        brief = ("The grocery chain is entering the Saudi market and the loyalty cohorts need their cohort "
                 "retention read from declared sizes and retained counts.")
        state = draftable(answer_all(chat.start(brief, "management")))
        chat.attach_computation(state, "cohort_retention",
                                {"cohort_sizes": ["1000", "800", "600"],
                                 "retained": [["1000", "600", "420"], ["800", "480", "300"],
                                              ["600", "360", "180"]]})
        state = chat.draft(state, accepted_ids=[], implications="Retention falls quickly after the first period.")
        section = [row for row in state["draft"]["outline"]
                   if row.get("heading") == "Cohort Retention"][0]
        text = " ".join(section.get("lines") or [])
        self.assertIn("average", text.lower())
        self.assertIn("65.83", text)

    def test_ltv_cac_belongs_to_channel_economics_not_clv(self):
        brief = ("The grocery chain is entering the Saudi market and the channel economics need reading: CAC and "
                 "LTV/CAC on declared channels.")
        selection = capabilities.resolve(brief, "pestel")
        self.assertEqual([row["key"] for row in selection["selected"]], ["channel_economics"])

    def test_a_survey_reliability_paper_takes_named_columns(self):
        brief = ("The grocery chain is entering the Saudi market and the staff survey needs its reliability "
                 "(Cronbach) read on declared items.")
        state = draftable(answer_all(chat.start(brief, "management")))
        chat.attach_computation(state, "reliability_alpha", {"items": {
            "quality": ["4", "5", "3", "4"], "speed": ["5", "5", "4", "4"], "care": ["3", "4", "3", "5"]}})
        state = chat.draft(state, accepted_ids=[], implications="The scale is not yet dependable.")
        section = [row for row in state["draft"]["outline"]
                   if row.get("heading") == "Survey Reliability"][0]
        text = " ".join(section.get("lines") or [])
        self.assertIn("Cronbach's alpha", text)
        self.assertIn("0.51", text)

    def test_a_dcf_paper_reports_the_core_value(self):
        brief = ("The grocery chain is entering the Saudi market and needs a dcf on its declared free cash "
                 "flows at a declared discount rate.")
        state = draftable(answer_all(chat.start(brief, "management")))
        chat.attach_computation(state, "dcf_valuation",
                                {"cashflows": ["100000", "120000", "140000"], "discount_rate": "0.10"})
        state = chat.draft(state, accepted_ids=[], implications="The declared flows support the proposal.")
        section = [row for row in state["draft"]["outline"]
                   if row.get("heading") == "Discounted Cash Flow Valuation"][0]
        text = " ".join(section.get("lines") or [])
        self.assertIn("295,266.72", text)
        self.assertIn("not a forecast", text)


class PaperTest(unittest.TestCase):
    def test_a_framework_only_paper_has_no_computation_section_and_no_figure_gate(self):
        state = draftable(answer_all(chat.start(
            "Assess the Saudi market for a grocery chain entering the country.", "management")))
        state = chat.draft(state, accepted_ids=[], implications="Entry is workable if costs hold.")
        found = headings(state)
        self.assertNotIn("Financial Feasibility", found)
        self.assertEqual(state["draft"]["missing"], [])

    def test_a_selected_capability_adds_its_section_and_its_gate(self):
        state = draftable(answer_all(chat.start(BRIEF, "management")))
        self.assertIn("the break-even figures", paper.missing(state, "A position."))
        chat.attach_computation(state, "breakeven", {"fixed": "40000", "price": "25", "variable": "12"})
        state = chat.draft(state, accepted_ids=[], implications="The branch must reach the break-even volume.")
        found = headings(state)
        self.assertIn("Financial Feasibility", found)
        self.assertIn("Break-even Analysis", found)
        self.assertEqual(state["draft"]["missing"], [])

    def test_dropping_removes_the_section_and_the_requirement(self):
        state = draftable(answer_all(chat.start(BRIEF, "management")))
        chat.attach_computation(state, "breakeven", {"fixed": "40000", "price": "25", "variable": "12"})
        state = chat.set_capability(state, "breakeven", False, "the figures are not available")
        self.assertEqual(state["selection"]["selected"], [])
        self.assertEqual(paper.missing(state, "A position."), [])
        state = chat.draft(state, accepted_ids=[], implications="The cost position was not assessed.")
        self.assertNotIn("Financial Feasibility", headings(state))

    def test_a_bespoke_formatter_reports_the_core_numbers_as_money(self):
        brief = ("The grocery chain appraises a branch in the Saudi market: net present value of an outlay of "
                 "100000 that returns 40000 a year for four years at a discount rate of 10 percent.")
        state = draftable(answer_all(chat.start(brief, "management")))
        chat.attach_computation(state, "npv", {"rate": "0.10",
                                               "cashflows": ["-100000", "40000", "40000", "40000", "40000"]})
        state = chat.draft(state, accepted_ids=[], implications="The branch clears the declared hurdle.")
        section = [row for row in state["draft"]["outline"] if row.get("heading") == "Net Present Value"][0]
        text = " ".join(section.get("lines") or [])
        self.assertIn("26,794.62", text)
        self.assertIn("not a forecast", text)
        self.assertNotIn("recommend", text.lower())


if __name__ == "__main__":
    unittest.main()
