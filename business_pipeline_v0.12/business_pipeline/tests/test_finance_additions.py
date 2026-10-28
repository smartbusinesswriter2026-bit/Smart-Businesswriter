"""Student-facing finance additions (B-090): goldens, refusals, presets and subject wiring.

These tests are deliberately written from a student's point of view: each one asks whether the
method gives the number a textbook would give, refuses an input it cannot honestly handle, and
says what it assumes in language a learner can act on.
"""

import sys
import os
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods, server  # noqa: E402
from bp.methods import DataError, LIBRARY  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402
from bp.product import subjects  # noqa: E402

NEW = ["time_value", "loan_amortization", "bond_analysis", "capm", "dupont_analysis",
       "multiples_valuation", "working_capital", "portfolio_analysis", "project_metrics",
       "option_pricing", "risk_metrics", "fx_parity", "leverage_analysis", "scenario_analysis",
       "trend_analysis"]

INPUTS = {
    "time_value": {"present_value": "100000", "payment": "12000", "rate": "0.06", "periods": "5",
                   "compounding": "quarterly", "timing": "end"},
    "loan_amortization": {"principal": "200000", "annual_rate": "0.09", "years": "5", "payments_per_year": "12"},
    "bond_analysis": {"face_value": "1000", "coupon_rate": "0.08", "years_to_maturity": "10",
                      "yield_to_maturity": "0.06", "payments_per_year": "2"},
    "capm": {"risk_free_rate": "0.04", "market_return": "0.10", "beta": "1.2",
             "debt_to_equity": "0.6", "tax_rate": "0.30"},
    "dupont_analysis": {"revenue": "20000", "net_income": "1800", "total_assets": "12000", "equity": "5000",
                        "cost_of_sales": "12000", "ebit": "3000", "pretax_income": "2400", "tax_expense": "600",
                        "prior_revenue": "18000", "prior_net_income": "1500", "prior_total_assets": "11000", "prior_equity": "4700"},
    "multiples_valuation": {"metric": "ebitda", "subject_value": "500000",
                            "comparables": [{"name": "A", "multiple": "8"}, {"name": "B", "multiple": "10"},
                                            {"name": "C", "multiple": "12"}],
                            "net_debt": "300000", "shares_outstanding": "100000"},
    "working_capital": {"revenue": "20000", "cost_of_sales": "12000", "inventory": "1200",
                        "receivables": "1500", "payables": "900", "annual_demand": "5000",
                        "order_cost": "50", "holding_cost_per_unit": "4", "discount_percent": "0.02",
                        "credit_terms_days": "30", "discount_days": "10",
                        "lead_time_days": "7", "safety_stock": "100"},
    "portfolio_analysis": {"returns_a": ["0.02", "0.03", "-0.01", "0.04", "0.01", "0.02"],
                           "returns_b": ["0.01", "0.02", "0.00", "0.03", "0.02", "0.01"],
                           "weight_a": "0.6", "risk_free_rate": "0.02",
                           "returns_market": ["0.01", "0.02", "-0.02", "0.03", "0.00", "0.02"]},
    "project_metrics": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10", "finance_rate": "0.08"},
    "option_pricing": {"option_type": "call", "spot_price": "100", "strike_price": "100", "volatility": "0.25",
                       "risk_free_rate": "0.05", "time_to_maturity": "1", "steps": "200"},
    "risk_metrics": {"returns": ["0.01", "-0.02", "0.015", "0.00", "-0.03", "0.025", "0.01", "-0.01", "0.02", "-0.005"],
                     "confidence": "0.95", "portfolio_value": "1000000", "horizon_days": "1", "stress_return": "-0.05"},
    "fx_parity": {"spot_rate": "56", "domestic_rate": "0.05", "foreign_rate": "0.03",
                  "domestic_inflation": "0.04", "foreign_inflation": "0.02",
                  "time_to_maturity": "1", "forward_rate": "57",
                  "exposure_amount": "100000", "hedge_forward": "57", "expected_spot": "57.5"},
    "leverage_analysis": {"ebit": "500000", "interest_expense": "100000", "tax_rate": "0.30", "debt": "800000",
                          "equity": "1200000", "shares_outstanding": "100000", "working_capital": "300000",
                          "retained_earnings": "400000", "total_assets": "2000000", "total_liabilities": "800000",
                          "sales": "3000000", "market_value_equity": "1800000",
                          "alternative_interest_expense": "200000", "alternative_shares_outstanding": "60000"},
    "scenario_analysis": {"cashflows": ["-1000", "400", "400", "400", "400"], "discount_rate": "0.10",
                          "rate_low": "0.05", "rate_high": "0.20"},
    "trend_analysis": {"years": ["2022", "2023", "2024", "2025"], "revenue": ["1000", "1100", "1210", "1331"],
                       "cost_of_sales": ["600", "650", "710", "760"], "operating_expenses": ["200", "220", "240", "260"],
                       "net_income": ["120", "140", "160", "190"], "total_assets": ["2000", "2100", "2250", "2400"],
                       "equity": ["900", "980", "1080", "1200"]},
}

PRESETS = ["tvm", "loan", "bond", "capm", "dupont", "multiples", "workingcapital", "portfolio",
           "projectmetrics", "options", "risk", "fx", "leverage", "scenario", "trendanalysis"]


class FinanceGoldens(unittest.TestCase):
    """Textbook figures, computed independently of the method's own second route."""

    def near(self, got, want, places=6):
        self.assertAlmostEqual(float(got), want, places=places)

    def test_time_value_matches_the_compound_and_annuity_formula(self):
        out = LIBRARY["time_value"].impl(INPUTS["time_value"])
        self.near(out["future_value"], 412169.505895, 5)
        self.near(out["present_value_payments"], 206023.665421, 5)
        self.near(out["effective_annual_rate"], 0.061363550625, 10)
        self.assertEqual(out["n_periods"], D(20))

    def test_loan_payment_matches_the_amortizing_formula(self):
        out = LIBRARY["loan_amortization"].impl(INPUTS["loan_amortization"])
        self.near(out["payment"], 4151.67104527, 6)
        self.near(out["total_interest"], 49100.2627162, 4)
        self.assertEqual(out["n_payments"], D(60))

    def test_bond_price_duration_and_solved_yield(self):
        out = LIBRARY["bond_analysis"].impl(INPUTS["bond_analysis"])
        self.near(out["price"], 1148.77474860, 6)
        self.near(out["macaulay_duration"], 7.286267593996, 8)
        self.near(out["convexity"], 63.9233459126, 6)
        solved = LIBRARY["bond_analysis"].impl({**INPUTS["bond_analysis"], "yield_to_maturity": "",
                                                "price": str(out["price"])})
        self.assertAlmostEqual(float(solved["yield_to_maturity"]), 0.06, places=8)

    def test_capm_and_hamada(self):
        out = LIBRARY["capm"].impl(INPUTS["capm"])
        self.near(out["cost_of_equity"], 0.112, 12)
        self.near(out["unlevered_beta"], 0.845070422535, 10)
        self.near(out["relevered_beta"], 1.2, 12)

    def test_dupont_three_and_five_step_agree(self):
        out = LIBRARY["dupont_analysis"].impl(INPUTS["dupont_analysis"])
        self.near(out["return_on_equity"], 0.36, 12)
        self.near(out["roe_three_step"], 0.36, 12)
        self.near(out["roe_five_step"], 0.36, 12)
        self.near(out["revenue_growth"], 0.111111111111, 10)
        self.near(out["return_on_equity_prior"], 0.319148936170, 10)

    def test_multiples_bridge_to_equity_and_per_share(self):
        out = LIBRARY["multiples_valuation"].impl(INPUTS["multiples_valuation"])
        self.assertEqual(out["implied_enterprise_value"], D("5000000"))
        self.assertEqual(out["implied_equity_value"], D("4700000"))
        self.assertEqual(out["per_share_value"], D("47"))

    def test_working_capital_cycle_and_order_quantity(self):
        out = LIBRARY["working_capital"].impl(INPUTS["working_capital"])
        self.near(out["cash_conversion_cycle"], 36.5, 10)
        self.near(out["eoq"], 353.553390593, 8)
        self.near(out["cost_of_trade_credit"], 0.372448979592, 10)

    def test_portfolio_return_risk_and_performance(self):
        out = LIBRARY["portfolio_analysis"].impl(INPUTS["portfolio_analysis"])
        self.near(out["portfolio_return"], 0.017, 12)
        self.near(out["portfolio_sd"], 0.0140142784331, 10)
        self.near(out["beta"], 0.9375, 12)
        self.near(out["correlation"], 0.830348758213, 10)

    def test_project_metrics_pi_mirr_payback_and_eaa(self):
        out = LIBRARY["project_metrics"].impl(INPUTS["project_metrics"])
        self.near(out["npv"], 267.946178540, 6)
        self.near(out["profitability_index"], 1.26794617854, 8)
        self.near(out["mirr"], 0.158685289670, 8)
        self.assertEqual(out["payback_period"], D("2.5"))
        self.near(out["irr"], 0.218622696098, 8)

    def test_option_price_is_black_scholes(self):
        out = LIBRARY["option_pricing"].impl(INPUTS["option_pricing"])
        self.near(out["option_price"], 12.33599893, 6)
        self.near(out["delta"], 0.62740946, 6)
        self.assertLess(abs(float(out["put_call_parity_gap"])), 1e-9)
        self.assertGreater(out["binomial_price"], D(0))

    def test_risk_var_and_shortfall(self):
        out = LIBRARY["risk_metrics"].impl(INPUTS["risk_metrics"])
        self.near(out["historical_var"], 0.0255, 10)
        self.near(out["historical_cvar"], 0.03, 10)
        self.near(out["stress_loss"], 50000, 6)

    def test_fx_parities(self):
        out = LIBRARY["fx_parity"].impl(INPUTS["fx_parity"])
        self.near(out["ppp_expected_spot"], 57.0980392157, 8)
        self.near(out["interest_rate_parity_forward"], 57.0873786408, 8)
        self.near(out["forward_premium"], 0.0178571428571, 10)
        self.near(out["hedged_domestic"], 5700000, 6)
        self.near(out["unhedged_domestic"], 5750000, 6)
        self.near(out["hedge_gain_loss"], -50000, 6)

    def test_leverage_eps_and_altman(self):
        out = LIBRARY["leverage_analysis"].impl(INPUTS["leverage_analysis"])
        self.near(out["eps"], 2.80, 10)
        self.near(out["degree_of_financial_leverage"], 1.25, 10)
        self.near(out["altman_z"], 4.135, 10)
        self.near(out["indifference_ebit"], 350000, 6)
        self.near(out["eps_at_indifference"], 1.75, 10)
        self.near(out["alternative_eps"], 3.50, 10)

    def test_scenario_swing_and_breakeven(self):
        out = LIBRARY["scenario_analysis"].impl(INPUTS["scenario_analysis"])
        self.near(out["npv_at_low_rate"], 418.380201665, 6)
        self.near(out["npv_at_high_rate"], 35.4938271605, 6)
        self.near(out["breakeven_rate"], 0.218622696098, 8)

    def test_multi_year_trend_and_common_size(self):
        out = LIBRARY["trend_analysis"].impl(INPUTS["trend_analysis"])
        self.near(out["revenue_cagr"], 0.10, 10)
        self.near(out["revenue_index_latest"], 133.10, 8)
        self.near(out["net_income_cagr"], 0.165531776, 8)
        self.near(out["common_size_cost_of_sales"], 760 / 1331, 10)
        self.near(out["net_margin_change"], 190 / 1331 - 120 / 1000, 10)


class FinanceRefusals(unittest.TestCase):
    """A student's wrong input must block with a reason, not produce a plausible number."""

    def refuses(self, method, changes):
        inp = {**INPUTS[method], **changes}
        with self.assertRaises(DataError):
            LIBRARY[method].impl(inp)

    def test_inputs_that_cannot_be_computed_are_refused(self):
        self.refuses("bond_analysis", {"yield_to_maturity": "", "price": ""})
        self.refuses("loan_amortization", {"principal": "0"})
        self.refuses("time_value", {"rate": "-1.5"})
        self.refuses("capm", {"beta": "", "returns_asset": ["1"], "returns_market": ["2"]})
        self.refuses("dupont_analysis", {"equity": "0"})
        self.refuses("multiples_valuation", {"comparables": [], "peer_multiple": ""})
        self.refuses("working_capital", {"holding_cost_per_unit": "0"})
        self.refuses("project_metrics", {"cashflows": ["1000", "-400"]})
        self.refuses("option_pricing", {"time_to_maturity": "0"})
        self.refuses("risk_metrics", {"confidence": "1.5"})
        self.refuses("fx_parity", {"spot_rate": "0"})
        self.refuses("leverage_analysis", {"shares_outstanding": "0"})
        self.refuses("scenario_analysis", {"rate_low": "0.30", "rate_high": "0.10"})
        self.refuses("trend_analysis", {"revenue": ["1000", "1100", "1210"]})
        self.refuses("leverage_analysis", {"alternative_interest_expense": "200000", "alternative_shares_outstanding": "100000"})
        self.refuses("dupont_analysis", {"prior_revenue": "18000", "prior_net_income": "", "prior_total_assets": "", "prior_equity": ""})
        self.refuses("fx_parity", {"hedge_forward": ""})

    def test_profile_reports_the_reason_before_execution(self):
        issues = LIBRARY["scenario_analysis"].profile({**INPUTS["scenario_analysis"], "rate_low": "0.30"})
        self.assertTrue(issues)
        self.assertIn("rate_low", issues[0])


class StudentFacingContract(unittest.TestCase):
    def test_every_new_method_explains_itself_in_plain_language(self):
        for name in NEW:
            m = LIBRARY[name]
            self.assertTrue(m.intended_use, name)
            self.assertTrue(m.unsupported_use, name)
            self.assertTrue(m.limitations, name)
            self.assertTrue(m.defaults, name)
            self.assertTrue(m.caveats, name)
            self.assertTrue(m.template, name)
            self.assertEqual(m.claim_ceiling, "descriptive", name)
            for key, spec in m.input_schema.items():
                self.assertTrue(spec.get("desc"), "%s.%s has no description" % (name, key))

    def test_every_new_method_has_a_preset_and_a_finance_tile(self):
        by_method = {tool["method"] for tool in subjects.detail("finance")["tools"]}
        for name in NEW:
            self.assertIn(name, LIBRARY)
            self.assertIn(name, by_method)
        for preset in PRESETS:
            self.assertIn(preset, server.PRESETS)
            self.assertIn(server.PRESETS[preset]["method"], LIBRARY)

    def test_the_finance_page_now_carries_statements_risk_and_investments(self):
        page = subjects.detail("finance")
        ids = {row["id"] for row in page["catalogue"]}
        for record in ("QNT-FIN-02", "QNT-FIN-05", "RSK-01", "RSK-04"):
            self.assertIn(record, ids)
        methods = {tool["method"] for tool in page["tools"]}
        for required in ("ratio_analysis", "breakeven", "ols", "pearson", "bond_analysis", "option_pricing"):
            self.assertIn(required, methods)

    def test_the_finance_page_groups_tools_and_carries_study_notes(self):
        page = subjects.detail("finance")
        order = []
        for tool in page["tools"]:
            self.assertTrue(tool["group"], tool["key"])
            self.assertTrue(tool["period"], tool["key"])
            self.assertTrue(tool["formula"], tool["key"])
            self.assertTrue(tool["steps"], tool["key"])
            self.assertTrue(tool["common_mistakes"], tool["key"])
            if tool["group"] not in order:
                order.append(tool["group"])
        self.assertEqual(order, ["Foundations", "Corporate finance", "Valuation",
                                 "Investments", "Risk & derivatives", "International"])
        self.assertTrue(page["glossary"])
        self.assertTrue(any(row["term"] == "WACC" for row in page["glossary"]))
        economics = subjects.detail("economics")
        self.assertTrue(all(tool["group"] is None for tool in economics["tools"]),
                        "the finance grouping must not leak onto the economics page")

    def test_a_percent_typed_as_a_whole_number_is_flagged(self):
        bad = Pipeline().run({"objective": "x", "method": "time_value", "currency": "USD",
                              "inputs": {"present_value": "1000", "rate": "6", "periods": "1",
                                         "compounding": "annual"}}, lambda spec: True)
        self.assertEqual(bad.status, "delivered")
        self.assertIn("6% is 0.06", bad.report)
        good = Pipeline().run({"objective": "x", "method": "time_value", "currency": "USD",
                               "inputs": {"present_value": "1000", "rate": "0.06", "periods": "1",
                                          "compounding": "annual"}}, lambda spec: True)
        self.assertNotIn("6% is 0.06", good.report)


class PresetDelivery(unittest.TestCase):
    """The whole student path: preset -> spec -> template -> delivery, with no raw digits leaking."""

    def test_every_new_preset_delivers(self):
        for preset in PRESETS:
            p = server.PRESETS[preset]
            request = {"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                       "currency": p.get("currency"), "period": p.get("period")}
            d = Pipeline().run(request, lambda spec: True)
            self.assertEqual(d.status, "delivered", "%s: %s" % (preset, d.blocked_reason))
            self.assertTrue(d.report)
            self.assertNotIn("{{ref:", d.report)


if __name__ == "__main__":
    unittest.main()
