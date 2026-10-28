"""Every capability family must produce a paper that passes the export gate."""
import unittest
from decimal import Decimal

from bp import methods
from bp.product import api as product_api, chat, paper


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


def setUpModule():
    product_api.attach_compute(lambda values: methods.breakeven(values))
    product_api.attach_methods(_run, methods.describe)


CASES = {
    "breakeven": ({"fixed": "40000", "price": "25", "variable": "12"}, "pestel"),
    "npv": ({"rate": "0.10", "cashflows": ["-100000", "40000", "40000", "40000", "40000"]}, "pestel"),
    "dcf_valuation": ({"cashflows": ["100000", "120000"], "discount_rate": "0.10"}, "pestel"),
    "wacc": ({"equity_value": "600000", "debt_value": "400000", "cost_of_equity": "0.12",
              "cost_of_debt_after_tax": "0.06"}, "five_forces"),
    "market_sizing": ({"target_population": "500000", "annual_spend_per_customer": "240",
                       "serviceable_share": "0.4", "obtainable_share": "0.1"}, "ansoff"),
    "unit_economics": ({"price": "50", "variable_cost": "30", "acquisition_cost": "200"}, "value_chain"),
    "multi_product_breakeven": ({"fixed_costs": "50000", "products": [
        {"name": "A", "price": "25", "variable_cost": "15", "mix_units": "3"},
        {"name": "B", "price": "40", "variable_cost": "28", "mix_units": "1"}]}, "pestel"),
    "welch_t": ({"groups": {"control": ["10", "11", "12", "13", "14"],
                            "treated": ["14", "15", "16", "17", "18"]}}, "pestel"),
    "chi_square": ({"table": [["10", "20"], ["30", "15"]]}, "pestel"),
    "ols": ({"y": ["10", "12", "13", "15", "16", "18"],
             "predictors": {"advertising": ["1", "2", "3", "4", "5", "6"]}}, "pestel"),
    "capacity_analysis": ({"demand": "500", "resources": [
        {"name": "line A", "available_hours": "8", "minutes_per_unit": "2"}]}, "operations" and "pestel"),
    "cohort_retention": ({"cohort_sizes": ["1000", "800"],
                          "retained": [["1000", "600"], ["800", "480"]]}, "swot"),
    "line_balancing": ({"tasks": [{"name": "cut", "time": "3"}, {"name": "sew", "time": "5"}],
                        "cycle_time": "6"}, "pestel"),
    "capm": ({"risk_free_rate": "0.04", "market_return": "0.10", "beta": "1.2"}, "pestel"),
    "bond_analysis": ({"face_value": "1000", "coupon_rate": "0.08", "years_to_maturity": "5",
                       "yield_to_maturity": "0.06"}, "pestel"),
}

BRIEF = ("The grocery chain is assessing the Saudi market and the figures it declared, "
         "with {label} as the analysis it needs.")


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


class EveryFamilyTest(unittest.TestCase):
    def test_every_family_drafts_a_paper_that_passes_the_export_gate(self):
        for key, (values, framework) in CASES.items():
            with self.subTest(capability=key):
                label = chat.capabilities.ENTRIES[key]["label"].lower()
                state = chat.start(BRIEF.format(label=label), "management", "pestel")
                if state.get("stage") == "not_supported":
                    self.skipTest("brief refused by the subject guard: " + key)
                state = answer_all(state)
                state = chat.confirm_plan(state)
                state = chat.attach_computation(state, key, values)
                state["stage"] = "evidence"
                state["evidence"] = []
                state["gaps"] = []
                state = chat.draft(state, accepted_ids=[],
                                   implications="The declared figures support the stated position.")
                self.assertEqual(state["draft"]["missing"], [], key)
                report = paper.check(state["draft"]["outline"], state.get("framework") or "pestel",
                                     state["draft"].get("implications", ""),
                                     state.get("answers") or {}, state=state)
                self.assertTrue(report["pass"], key + ": " + str(report["issues"]))

    def test_every_registered_capability_has_a_formatter_or_the_generic_one(self):
        for key in chat.capabilities.ENTRIES:
            if key in chat.CAPABILITY_LINES:
                self.assertTrue(callable(chat.CAPABILITY_LINES[key]), key)
            else:
                self.assertTrue(callable(chat._generic_lines), key)


if __name__ == "__main__":
    unittest.main()
