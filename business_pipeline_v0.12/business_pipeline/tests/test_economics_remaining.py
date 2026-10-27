import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp import server
from bp.product import subjects

YES = lambda s: True

PRESET_KEYS = [
    "externality", "publicgood", "socialwelfare", "gini", "poverty", "taxprogressivity",
    "optimalpollution", "okun", "comparative", "tariff", "ppp", "irp", "bop", "hdi",
    "expectedutility", "prospect", "labour", "pricediscrimination", "cournot", "did", "nash",
]
CASES = {server.PRESETS[key]["method"]: server.PRESETS[key]["inputs"] for key in PRESET_KEYS}

BAD = {
    "externality_pigouvian": {**CASES["externality_pigouvian"], "marginal_external_cost": "-1"},
    "public_good": {**CASES["public_good"], "mb1_slope": "0"},
    "social_welfare": {"incomes": ["0", "10"], "welfare_function": "utilitarian"},
    "gini_coefficient": {"incomes": ["10"]},
    "poverty_measures": {**CASES["poverty_measures"], "poverty_line": "0"},
    "tax_progressivity": {"incomes": ["10", "20"], "taxes": ["1"]},
    "optimal_pollution": {**CASES["optimal_pollution"], "marginal_damage_slope": "0"},
    "output_gap_okun": {**CASES["output_gap_okun"], "potential_gdp": "0"},
    "comparative_advantage": {"countries": [{"name": "A", "good_1_hours": "1", "good_2_hours": "1"}]},
    "tariff_welfare": {**CASES["tariff_welfare"], "tariff_per_unit": "-1"},
    "exchange_rate_ppp": {**CASES["exchange_rate_ppp"], "nominal_rate": "0"},
    "interest_rate_parity": {**CASES["interest_rate_parity"], "spot_rate": "0"},
    "balance_of_payments": {**CASES["balance_of_payments"], "gdp": "0"},
    "hdi": {**CASES["hdi"], "gni_per_capita": "0"},
    "expected_utility": {**CASES["expected_utility"], "probabilities": ["0.5", "0.6"]},
    "prospect_theory": {"reference_point": "100", "outcomes": ["150", "50"], "probabilities": ["0.5"]},
    "labour_market": {**CASES["labour_market"], "cpi": "0"},
    "price_discrimination": {**CASES["price_discrimination"], "marginal_cost": "200"},
    "cournot_duopoly": {**CASES["cournot_duopoly"], "demand_slope": "0"},
    "difference_in_differences": {"treated_pre": "1", "treated_post": "2", "control_pre": "1"},
    "nash_equilibrium": {"row_payoffs": ["1", "2", "3"], "column_payoffs": ["1", "2", "3", "4"]},
}


class ArithmeticAndChecks(unittest.TestCase):
    def test_every_remaining_method_computes_and_passes_its_frozen_checks(self):
        for method_id, inputs in CASES.items():
            method = LIBRARY[method_id]
            checks = method.tests(inputs, method.impl)
            self.assertEqual(tuple(n for n, _ in checks), method.test_names, method_id)
            self.assertTrue(all(ok for _, ok in checks), (method_id, checks))

    def test_expected_headline_values(self):
        cases = {
            "externality_pigouvian": {"social_quantity": D(56), "deadweight_loss": D(8)},
            "social_welfare": {"utilitarian_welfare": D(100), "rawlsian_welfare": D(10)},
            "gini_coefficient": {"gini": D("0.25")},
            "poverty_measures": {"headcount_ratio": D("0.5"), "poverty_gap": D("0.2")},
            "tax_progressivity": {"average_tax_rate": D("0.2"), "progressivity_gap": D("0.1")},
            "optimal_pollution": {"optimal_emissions": D(18), "pollution_tax": D(46)},
            "output_gap_okun": {"output_gap": D("0.05"), "predicted_unemployment_change_pp": D("-2.500")},
            "comparative_advantage": {"oc_a_good1": D(2), "a_has_advantage_good1": D(0)},
            "tariff_welfare": {"domestic_price": D(15), "imports": D(20), "tariff_revenue": D(100), "total_dwloss": D(50)},
            "exchange_rate_ppp": {"ppp_rate": D(50), "real_exchange_rate": D("1.1")},
            "balance_of_payments": {"net_balance": D(0), "balanced": D(1)},
            "price_discrimination": {"quantity_1": D("22.5"), "price_1": D("55.0"), "total_profit": D("2237.50")},
            "difference_in_differences": {"did_estimate": D(15)},
            "nash_equilibrium": {"nash_count": D(1), "nash_22": D(1)},
        }
        for method_id, expected in cases.items():
            out = LIBRARY[method_id].impl(CASES[method_id])
            for key, value in expected.items():
                self.assertEqual(out[key], value, (method_id, key, out[key], value))

    def test_approximate_headline_values(self):
        cases = {
            "public_good": ("efficient_quantity", 160 / 6),
            "interest_rate_parity": ("implied_forward", 50 * (1.06 / 1.04)),
            "hdi": ("hdi", 0.648508245),
            "expected_utility": ("certainty_equivalent", 75.0),
            "prospect_theory": ("prospect_value", -19.5422075),
            "labour_market": ("real_wage", 100 / 1.05),
            "cournot_duopoly": ("price", 100 - 2 * ((100 - 20 + 20) / 6 + (100 - 40 + 10) / 6)),
        }
        for method_id, (key, value) in cases.items():
            out = LIBRARY[method_id].impl(CASES[method_id])
            self.assertAlmostEqual(float(out[key]), value, places=5, msg=(method_id, key))

    def test_every_remaining_method_refuses_a_bad_case(self):
        for method_id, inputs in BAD.items():
            self.assertEqual(Pipeline().run({"objective": "x", "method": method_id, "inputs": inputs}, YES).status,
                             "blocked", method_id)


class Delivery(unittest.TestCase):
    def test_every_remaining_preset_delivers(self):
        for key in PRESET_KEYS:
            preset = server.PRESETS[key]
            delivery = Pipeline().run({"objective": preset["objective"], "method": preset["method"],
                                       "currency": preset.get("currency", "USD"),
                                       "period": preset.get("period", "annual"),
                                       "inputs": preset["inputs"]}, YES)
            self.assertEqual(delivery.status, "delivered", (key, delivery.blocked_reason))
            self.assertTrue(all(ok for ok in delivery.appendix["tests"]), key)

    def test_the_economics_page_carries_every_remaining_tool(self):
        page = subjects.detail("economics")
        keys = {tool["key"] for tool in page["tools"]}
        for key in PRESET_KEYS:
            self.assertIn(key, keys)
        self.assertGreaterEqual(len(page["tools"]), 51)
        self.assertGreaterEqual(len(page["glossary"]), 25)


if __name__ == "__main__":
    unittest.main()
