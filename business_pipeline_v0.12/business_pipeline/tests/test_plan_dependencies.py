"""Chained computations: a figure the core already computed is offered, not retyped.

The chain lives in `capabilities.NEEDS_FROM`, so the test also pins the rule that
only registered pairs are offered — the product never guesses that one method's
output is another's input.
"""

import unittest

from bp import methods
from bp.product import api, capabilities, chat

BRIEF = ("The grocery chain is appraising a branch in the Saudi market: net present value of an "
         "outlay of 100000 that returns 40000 a year for four years at a discount rate of "
         "10 percent.")

WACC = {"equity_value": "1000", "debt_value": "500", "cost_of_equity": "0.11",
        "cost_of_debt_after_tax": "0.05"}
CASHFLOWS = ["-100000", "40000", "40000", "40000"]


def _run(method_id, values):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, values)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(values)


def setUpModule():
    api.attach_compute(lambda values: methods.breakeven(values))
    api.attach_methods(_run, methods.describe)


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


def planned():
    """A paper carrying NPV, with WACC added to the plan."""
    state = answer_all(chat.start(BRIEF, "management", "pestel"))
    state = chat.set_capability(state, "wacc")
    return state


class DependencyTest(unittest.TestCase):
    def test_the_graph_names_the_source_and_whether_it_is_in_the_paper(self):
        state = chat.start(BRIEF, "management", "pestel")
        rows = capabilities.dependencies(state["selection"])
        npv = [row for row in rows if row["key"] == "npv"]
        self.assertEqual(len(npv), 1)
        self.assertEqual((npv[0]["input"], npv[0]["from"], npv[0]["output"]),
                         ("rate", "wacc", "wacc"))
        self.assertFalse(npv[0]["selected"])
        self.assertFalse(npv[0]["recorded"])
        self.assertIsNone(npv[0]["value"])

    def test_only_registered_pairs_are_offered(self):
        state = planned()
        keys = {(row["key"], row["input"]) for row in state["dependency_graph"]}
        self.assertIn(("npv", "rate"), keys)
        # A pair nobody registered is never invented.
        self.assertNotIn(("npv", "cashflows"), keys)
        for row in state["dependency_graph"]:
            self.assertIn(row["input"], capabilities.NEEDS_FROM[row["key"]])

    def test_a_computed_source_offers_its_value_in_a_readable_form(self):
        state = chat.confirm_plan(planned())
        state = chat.run_capability(state, "wacc", WACC)
        self.assertEqual(state["dependency_inputs"], {"npv": {"rate": "0.09"}})
        row = [item for item in state["dependency_graph"] if item["key"] == "npv"][0]
        self.assertTrue(row["recorded"])
        self.assertEqual(row["value"], "0.09")
        self.assertEqual(row["from_label"], "Cost of capital")

    def test_a_refused_source_offers_nothing(self):
        state = chat.confirm_plan(planned())
        state["computations"]["wacc"] = {"ok": False, "method": "wacc",
                                         "inputs": WACC, "error": "declared a negative value"}
        chat.apply_dependencies(state)
        self.assertEqual(state["dependency_inputs"], {})

    def test_a_chained_input_is_recorded_with_its_source_and_the_paper_says_so(self):
        state = chat.confirm_plan(planned())
        state = chat.run_capability(state, "wacc", WACC)
        rate = state["dependency_inputs"]["npv"]["rate"]
        state = chat.run_capability(state, "npv", {"rate": rate, "cashflows": CASHFLOWS})
        self.assertTrue(state["computations"]["npv"]["ok"])
        self.assertEqual(state["computations"]["npv"]["from"], {"rate": "wacc"})
        line = chat._declared_inputs_line(state["computations"]["npv"])
        self.assertIn("rate 0.09 (from the cost of capital result)", line)
        self.assertEqual(chat._recompute_guard(state), [])

    def test_a_student_rate_is_not_marked_as_chained(self):
        state = chat.confirm_plan(planned())
        state = chat.run_capability(state, "wacc", WACC)
        state = chat.run_capability(state, "npv", {"rate": "0.12", "cashflows": CASHFLOWS})
        self.assertEqual(state["computations"]["npv"]["from"], {})
        self.assertNotIn("from the cost of capital", chat._declared_inputs_line(state["computations"]["npv"]))

    def test_the_frozen_plan_records_which_inputs_came_from_another_result(self):
        state = chat.confirm_plan(planned())
        state = chat.run_capability(state, "wacc", WACC)
        state = chat.run_capability(state, "npv",
                                    {"rate": state["dependency_inputs"]["npv"]["rate"],
                                     "cashflows": CASHFLOWS})
        state = chat.confirm_plan(state) if state.get("stage") == "plan" else state
        record = chat._freeze_plan(state)
        npv = [row for row in record["capabilities"] if row["key"] == "npv"][0]
        self.assertEqual(npv["from"], {"rate": "wacc"})
        self.assertTrue(chat.replay_check({"plan_record": record})["match"])

    def test_the_plan_card_carries_the_offer_for_the_ui(self):
        state = chat.confirm_plan(planned())
        state = chat.run_capability(state, "wacc", WACC)
        card = [row for row in state["plan"]["capabilities"] if row["key"] == "npv"][0]
        self.assertEqual(card["chained"], {"rate": "0.09"})
        self.assertEqual([(row["input"], row["selected"], row["recorded"])
                          for row in card["needs_from"]], [("rate", True, True)])


if __name__ == "__main__":
    unittest.main()
