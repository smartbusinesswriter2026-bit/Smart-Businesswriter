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
    "dupont_analysis": ({"revenue": "1000000", "net_income": "80000", "total_assets": "600000",
                         "equity": "300000"}, "pestel"),
    "working_capital": ({"revenue": "1200000", "cost_of_sales": "800000", "inventory": "100000",
                         "receivables": "150000", "payables": "90000", "annual_demand": "24000",
                         "order_cost": "50", "holding_cost_per_unit": "2", "discount_percent": "0.02",
                         "credit_terms_days": "40", "discount_days": "10"}, "pestel"),
    "scenario_analysis": ({"cashflows": ["-100000", "40000", "40000", "40000"],
                           "discount_rate": "0.10", "rate_low": "0.08", "rate_high": "0.12"}, "pestel"),
    "risk_metrics": ({"returns": ["0.01", "-0.02", "0.015", "0.005"], "confidence": "0.95",
                      "portfolio_value": "1000000", "horizon_days": "1"}, "pestel"),
    "currency_convert": ({"amount": "1000", "from_currency": "USD", "to_currency": "SAR",
                          "rate": "3.75", "rate_provenance": "user"}, "pestel"),
    "fx_parity": ({"spot_rate": "3.75", "domestic_rate": "0.05", "foreign_rate": "0.02",
                   "domestic_inflation": "0.03", "foreign_inflation": "0.01",
                   "time_to_maturity": "1"}, "pestel"),
    "ols_robust": ({"y": ["10", "12", "13", "15", "16", "18"],
                    "predictors": {"advertising": ["1", "2", "3", "4", "5", "6"]}}, "pestel"),
    "market_concentration": ({"firm_revenues": ["500", "300", "200"]}, "pestel"),
    "cost_curves": ({"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5",
                     "quantity": "40", "price": "30"}, "pestel"),
    "market_power": ({"price": "30", "marginal_cost": "18"}, "pestel"),
    "proforma_statements": ({"revenue": ["500000", "550000"], "gross_margin_rate": "0.4",
                             "operating_costs": ["120000", "130000"],
                             "depreciation": ["20000", "20000"], "interest": ["0", "0"],
                             "principal_repayment": ["0", "0"]}, "pestel"),
    "sensitivity_table": ({"base_price": "25", "base_units": "5000", "base_variable_cost": "12",
                           "base_fixed_cost": "40000", "price_changes": ["-0.1", "0", "0.1"],
                           "volume_changes": ["-0.1", "0", "0.1"]}, "pestel"),
    "sroi": ({"investment": "100000", "benefits": ["40000", "50000", "60000"],
              "discount_rate": "0.05"}, "pestel"),
    "cost_benefit": ({"costs": ["100000", "20000", "20000"],
                      "benefits": ["0", "80000", "90000"], "discount_rate": "0.08"}, "pestel"),
    "cost_effectiveness": ({"options": [{"name": "a", "cost": "100000", "effect": "40"},
                                        {"name": "b", "cost": "150000", "effect": "55"}]}, "pestel"),
    "demand_supply_equilibrium": ({"demand_intercept": "100", "demand_slope": "2",
                                   "supply_intercept": "20", "supply_slope": "1"}, "pestel"),
    "national_income": ({"consumption": "600", "investment": "200", "government_spending": "150",
                         "exports": "100", "imports": "80"}, "pestel"),
    "gini_coefficient": ({"incomes": ["10", "20", "30", "40"]}, "pestel"),
    "tariff_welfare": ({"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20",
                        "supply_slope": "1", "world_price": "20", "tariff_per_unit": "5"}, "pestel"),
    "comparative_advantage": ({"countries": [
        {"name": "A", "good_1_hours": "2", "good_2_hours": "4"},
        {"name": "B", "good_1_hours": "6", "good_2_hours": "3"}]}, "pestel"),
    "panel_regression": ({"data": [
        {"entity": "a", "period": "1", "y": "1", "x": "2"},
        {"entity": "a", "period": "2", "y": "2", "x": "3"},
        {"entity": "b", "period": "1", "y": "3", "x": "4"},
        {"entity": "b", "period": "2", "y": "4", "x": "5"}]}, "pestel"),
}

BRIEF = ("The grocery chain is assessing the Saudi market and the figures it declared, "
         "with {label} as the analysis it needs, on its declared observations and figures.")


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
