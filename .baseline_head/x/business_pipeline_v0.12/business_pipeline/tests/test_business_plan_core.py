"""The business-plan spine: depreciation, pro-forma statements, sales from market
and the sensitivity table (B-121).

Hand-checked arithmetic for the four plan-level methods, the refusal paths that
matter for a business plan (an opening balance sheet that does not balance, a
loan repaid faster than it is owed, a share above the whole market) and the
Entrepreneurship page wiring that exposes them.
"""

import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, "src")
from bp import server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.product import subjects

YES = lambda spec: True

DEPRECIATION = {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"}
PROFORMA = {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
            "operating_costs": ["300000", "320000", "340000"],
            "depreciation": ["90000", "90000", "90000"],
            "interest": ["40000", "30000", "20000"],
            "principal_repayment": ["100000", "100000", "100000"], "capex": ["0", "0", "0"],
            "tax_rate": "0.25", "receivable_days": "30", "inventory_days": "45", "payable_days": "30",
            "opening_cash": "200000", "opening_fixed_assets": "450000",
            "opening_receivables": "0", "opening_inventory": "0", "opening_payables": "0",
            "opening_loan": "400000", "opening_equity": "250000"}
FROM_MARKET = {"market_size": "60000000", "target_share": "0.03", "price": "120"}
PROFORMA_LOAN = {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "90000", "90000"],
                 "loan_principal": "400000", "loan_annual_rate": "0.09", "loan_years": "3",
                 "tax_rate": "0.25",
                 "opening_cash": "200000", "opening_fixed_assets": "450000",
                 "opening_loan": "400000", "opening_equity": "250000"}
SENSITIVITY = {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
               "base_fixed_cost": "300000",
               "price_changes": ["-0.1", "0", "0.1"], "volume_changes": ["-0.2", "0", "0.2"]}

NEW_METHODS = ("depreciation_schedule", "proforma_statements", "sales_from_market", "sensitivity_table")
NEW_PRESETS = ("depreciation", "proforma", "frommarket", "sensitivity")


def delivered(request):
    d = Pipeline().run(request, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


def blocked(method, inputs):
    return Pipeline().run({"objective": "x", "method": method, "inputs": inputs}, YES).status == "blocked"


def checks_pass(method, inputs):
    m = LIBRARY[method]
    result = m.tests(inputs, m.impl)
    assert tuple(name for name, _ in result) == m.test_names, (method, result)
    return all(ok for _, ok in result)


class DepreciationSchedule(unittest.TestCase):
    def m(self):
        return LIBRARY["depreciation_schedule"]

    def test_straight_line_arithmetic(self):
        out = self.m().impl(DEPRECIATION)
        self.assertEqual(out["depreciation_1"], D(90000))
        self.assertEqual(out["depreciation_5"], D(90000))
        self.assertEqual(out["accumulated_3"], D(270000))
        self.assertEqual(out["carrying_5"], D(50000))
        self.assertEqual(out["total_depreciation"], D(450000))

    def test_declining_balance_plugs_the_final_period_to_salvage(self):
        out = self.m().impl({**DEPRECIATION, "method": "declining_balance"})
        self.assertEqual(out["depreciation_1"], D(200000))
        self.assertEqual(out["carrying_5"], D(50000))
        self.assertEqual(out["total_depreciation"], D(450000))
        self.assertTrue(all(out["carrying_%d" % p] >= D(50000) for p in range(1, 6)))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("depreciation_schedule", DEPRECIATION))
        self.assertTrue(checks_pass("depreciation_schedule", {**DEPRECIATION, "method": "declining_balance"}))
        for inputs in ({**DEPRECIATION, "cost": "0"}, {**DEPRECIATION, "salvage": "-1"},
                       {**DEPRECIATION, "salvage": "500001"}, {**DEPRECIATION, "life": "0"},
                       {**DEPRECIATION, "life": "41"}, {**DEPRECIATION, "method": "sum_of_digits"},
                       {**DEPRECIATION, "method": "declining_balance", "declining_rate": "0"},
                       {**DEPRECIATION, "method": "declining_balance", "declining_rate": "2"}):
            self.assertTrue(blocked("depreciation_schedule", inputs), inputs)

    def test_pipeline_delivers_without_template_tokens(self):
        d = delivered({"objective": "Depreciation", "method": "depreciation_schedule",
                       "currency": "PHP", "period": "annual", "inputs": DEPRECIATION})
        self.assertIn("depreciation", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class ProformaStatements(unittest.TestCase):
    def m(self):
        return LIBRARY["proforma_statements"]

    def test_income_statement_arithmetic(self):
        out = self.m().impl(PROFORMA)
        self.assertEqual(out["revenue_1"], D(1200000))
        self.assertEqual(out["gross_profit_1"], D(480000))
        self.assertEqual(out["operating_profit_1"], D(90000))
        self.assertEqual(out["pre_tax_profit_1"], D(50000))
        self.assertEqual(out["tax_1"], D(12500))
        self.assertEqual(out["net_income_1"], D(37500))
        self.assertEqual(out["total_net_income"], D(360000))
        self.assertAlmostEqual(float(out["closing_cash_final"]), 337671.2328767, places=6)
        self.assertEqual(out["closing_equity_final"], D(610000))

    def test_every_period_balances_and_rolls_forward(self):
        out = self.m().impl(PROFORMA)
        for period in range(1, 4):
            self.assertAlmostEqual(float(out["total_assets_%d" % period]),
                                   float(out["total_liabilities_%d" % period] + out["equity_%d" % period]), places=6)
        self.assertEqual(out["closing_equity_final"], D(250000) + out["total_net_income"])

    def test_an_opening_loan_supplies_the_interest_and_principal(self):
        out = self.m().impl(PROFORMA_LOAN)
        self.assertEqual(out["interest_1"], D("36000.00"))
        self.assertEqual(out["principal_repayment_3"], D("144974.22287300570452396205118818827979622342210427"))
        self.assertLess(abs(out["loan_3"]), D("1e-9"))
        self.assertAlmostEqual(float(sum(out["principal_repayment_%d" % p] for p in range(1, 4))), 400000.0, places=6)
        self.assertTrue(checks_pass("proforma_statements", PROFORMA_LOAN))

    def test_loan_terms_and_declared_lists_are_never_mixed(self):
        mixed = {**PROFORMA_LOAN, "interest": ["40000", "30000", "20000"],
                 "principal_repayment": ["1", "1", "1"]}
        self.assertTrue(blocked("proforma_statements", mixed))
        partial = {**PROFORMA_LOAN, "loan_years": ""}
        self.assertTrue(blocked("proforma_statements", partial))
        wrong_years = {**PROFORMA_LOAN, "loan_years": "2"}
        self.assertTrue(blocked("proforma_statements", wrong_years))
        wrong_opening = {**PROFORMA_LOAN, "opening_loan": "300000"}
        self.assertTrue(blocked("proforma_statements", wrong_opening))

    def test_an_unbalanced_opening_balance_is_refused_with_the_fix(self):
        inputs = {**PROFORMA, "opening_equity": "200000"}
        self.assertTrue(blocked("proforma_statements", inputs))
        errors = self.m().profile(inputs)
        self.assertTrue(any("250000" in e for e in errors), errors)

    def test_repaying_more_loan_than_is_owed_is_refused(self):
        inputs = {**PROFORMA, "opening_loan": "50000", "opening_equity": "0",
                  "principal_repayment": ["100000"]}
        inputs["revenue"] = inputs["revenue"][:1]
        for name in ("operating_costs", "depreciation", "interest"):
            inputs[name] = inputs[name][:1]
        self.assertTrue(blocked("proforma_statements", inputs))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("proforma_statements", PROFORMA))
        for inputs in ({**PROFORMA, "gross_margin_rate": "1.5"}, {**PROFORMA, "tax_rate": "-0.1"},
                       {**PROFORMA, "revenue": []}, {**PROFORMA, "revenue": ["-1"]},
                       {**PROFORMA, "operating_costs": ["1"]},
                       {**PROFORMA, "receivable_days": "-1"},
                       {**PROFORMA_LOAN, "loan_annual_rate": "-0.01"},
                       {**PROFORMA_LOAN, "loan_principal": "0"}):
            self.assertTrue(blocked("proforma_statements", inputs), inputs)

    def test_pipeline_delivers_without_template_tokens(self):
        d = delivered({"objective": "Projected statements", "method": "proforma_statements",
                       "currency": "PHP", "period": "annual", "inputs": PROFORMA})
        self.assertIn("net income", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class SalesFromMarket(unittest.TestCase):
    def m(self):
        return LIBRARY["sales_from_market"]

    def test_arithmetic(self):
        out = self.m().impl(FROM_MARKET)
        self.assertEqual(out["target_revenue"], D(1800000))
        self.assertEqual(out["target_units"], D(15000))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("sales_from_market", FROM_MARKET))
        for inputs in ({**FROM_MARKET, "market_size": "0"}, {**FROM_MARKET, "target_share": "0"},
                       {**FROM_MARKET, "target_share": "1.01"}, {**FROM_MARKET, "price": "0"}):
            self.assertTrue(blocked("sales_from_market", inputs), inputs)

    def test_pipeline_delivers_without_template_tokens(self):
        d = delivered({"objective": "Market share", "method": "sales_from_market",
                       "currency": "PHP", "period": "annual", "inputs": FROM_MARKET})
        self.assertIn("revenue", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class SensitivityTable(unittest.TestCase):
    def m(self):
        return LIBRARY["sensitivity_table"]

    def test_arithmetic(self):
        out = self.m().impl(SENSITIVITY)
        self.assertEqual(out["base_profit"], D(350000))
        self.assertEqual(out["profit_2_2"], D(350000))
        self.assertEqual(out["profit_1_1"], D(124000))
        self.assertEqual(out["profit_3_3"], D(624000))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("sensitivity_table", SENSITIVITY))
        for inputs in ({**SENSITIVITY, "base_price": "0"}, {**SENSITIVITY, "base_units": "0"},
                       {**SENSITIVITY, "base_variable_cost": "-1"}, {**SENSITIVITY, "base_fixed_cost": "-1"},
                       {**SENSITIVITY, "price_changes": []}, {**SENSITIVITY, "volume_changes": []},
                       {**SENSITIVITY, "price_changes": ["0", "0", "0", "0", "0", "0"]},
                       {**SENSITIVITY, "price_changes": ["-1"]}):
            self.assertTrue(blocked("sensitivity_table", inputs), inputs)

    def test_pipeline_delivers_without_template_tokens(self):
        d = delivered({"objective": "Sensitivity", "method": "sensitivity_table",
                       "currency": "PHP", "period": "annual", "inputs": SENSITIVITY})
        self.assertIn("profit", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class PresetDelivery(unittest.TestCase):
    def test_every_new_preset_delivers(self):
        for preset in NEW_PRESETS:
            p = server.PRESETS[preset]
            d = delivered({"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                           "currency": p.get("currency"), "period": p.get("period")})
            self.assertNotIn("{{ref:", d.report, preset)
            self.assertTrue(all(ok for _, ok, *_ in d.appendix["tests"]), preset)


class PageWiring(unittest.TestCase):
    def test_the_entrepreneurship_page_exposes_every_new_tile(self):
        keys = {t["key"]: t for t in subjects.detail("entrepreneurship")["tools"] if t["kind"] == "compute"}
        for key in ("capacity", "inventory", "concentration", "ratios", "costeffectiveness",
                    "depreciation", "proforma", "frommarket", "sensitivity"):
            self.assertIn(key, keys)
            self.assertTrue(keys[key]["group"], key)
            self.assertTrue(keys[key]["period"], key)
            self.assertTrue(keys[key]["formula"], key)

    def test_every_compute_tile_has_a_group_period_and_formula(self):
        for tool in subjects.detail("entrepreneurship")["tools"]:
            if tool["kind"] != "compute":
                continue
            for field in ("group", "period", "formula"):
                self.assertTrue(tool[field], (tool["key"], field))

    def test_every_method_is_in_the_library_and_every_preset_points_at_one(self):
        for method in NEW_METHODS:
            self.assertIn(method, LIBRARY)
        for preset in NEW_PRESETS:
            self.assertIn(server.PRESETS[preset]["method"], LIBRARY)


if __name__ == "__main__":
    unittest.main()
