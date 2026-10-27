import sys, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline

YES = lambda s: True

COST = {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5", "quantity": "20", "price": "40"}
PROFIT = {"demand_intercept": "100", "demand_slope": "2", "fixed_cost": "100", "linear_cost": "10", "quadratic_cost": "0.5"}
POWER = {"price": "50", "marginal_cost": "20"}
NATIONAL = {"consumption": "600", "investment": "150", "government_spending": "200", "exports": "120", "imports": "170",
            "net_factor_income": "20", "depreciation": "50", "population": "100", "gdp_deflator": "120"}
GROWTH = {"start_value": "100", "end_value": "200", "periods": "10"}
INFLATION = {"cpi_start": "100", "cpi_end": "105", "nominal_interest_rate": "0.08", "wage_start": "100", "wage_end": "104"}
UNEMPLOYMENT = {"labour_force": "1000", "employed": "920", "working_age_population": "1500"}
MONEY = {"monetary_base": "100", "reserve_ratio": "0.10", "currency_drain_ratio": "0.05"}
FISCAL = {"mpc": "0.8", "tax_rate": "0.25", "government_spending_change": "100", "tax_change": "0"}
BUDGET = {"government_revenue": "500", "government_spending": "520", "interest_payments": "30",
          "debt_stock": "1000", "nominal_gdp": "2000", "nominal_growth_rate": "0.05", "inflation_rate": "0.02"}


def delivered(req):
    d = Pipeline().run(req, YES)
    assert d.status == "delivered", d.blocked_reason
    return d


def blocked(method, inputs):
    return Pipeline().run({"objective": "x", "method": method, "inputs": inputs}, YES).status == "blocked"


class CostCurves(unittest.TestCase):
    def m(self): return LIBRARY["cost_curves"]

    def test_arithmetic(self):
        out = self.m().impl(COST)
        self.assertEqual((out["total_cost"], out["average_cost"], out["average_variable_cost"],
                          out["average_fixed_cost"], out["marginal_cost"], out["profit"]),
                         (D("1400.0"), D("70.0"), D("20.0"), D("50"), D("30.0"), D("-600.0")))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(COST, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(COST, self.m().impl)))
        for inputs in ({"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5", "quantity": "0"},
                       {"fixed_cost": "-1", "linear_cost": "10", "quadratic_cost": "0.5", "quantity": "20"},
                       {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "-0.5", "quantity": "20"}):
            self.assertTrue(blocked("cost_curves", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Costs", "method": "cost_curves", "currency": "PHP", "period": "annual", "inputs": COST})
        self.assertIn("average cost", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class ProfitMaximization(unittest.TestCase):
    def m(self): return LIBRARY["profit_maximization"]

    def test_arithmetic(self):
        out = self.m().impl(PROFIT)
        self.assertEqual((out["profit_maximizing_quantity"], out["profit_maximizing_price"], out["profit"]),
                         (D(18), D(64), D("710.0")))
        self.assertEqual(out["lerner_index"], D("0.5625"))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(PROFIT, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(PROFIT, self.m().impl)))
        for inputs in ({"demand_intercept": "100", "demand_slope": "0", "fixed_cost": "100", "linear_cost": "10", "quadratic_cost": "0.5"},
                       {"demand_intercept": "10", "demand_slope": "2", "fixed_cost": "100", "linear_cost": "20", "quadratic_cost": "0.5"}):
            self.assertTrue(blocked("profit_maximization", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Profit", "method": "profit_maximization", "currency": "PHP", "period": "annual", "inputs": PROFIT})
        self.assertIn("profit", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class MarketPower(unittest.TestCase):
    def m(self): return LIBRARY["market_power"]

    def test_arithmetic(self):
        out = self.m().impl(POWER)
        self.assertEqual((out["markup"], out["lerner_index"]), (D(30), D("0.6")))
        self.assertAlmostEqual(float(out["implied_demand_elasticity"]), 1.6666666667, places=8)

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(POWER, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(POWER, self.m().impl)))
        for inputs in ({"price": "0", "marginal_cost": "20"}, {"price": "50", "marginal_cost": "60"}):
            self.assertTrue(blocked("market_power", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Market power", "method": "market_power", "currency": "PHP", "period": "annual", "inputs": POWER})
        self.assertIn("lerner", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class NationalIncome(unittest.TestCase):
    def m(self): return LIBRARY["national_income"]

    def test_arithmetic(self):
        out = self.m().impl(NATIONAL)
        self.assertEqual((out["gdp"], out["gnp"], out["nnp"], out["net_exports"]), (D(900), D(920), D(870), D(-50)))
        self.assertEqual((out["real_gdp"], out["gdp_per_capita"]), (D(750), D(9)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(NATIONAL, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(NATIONAL, self.m().impl)))
        for inputs in ({**NATIONAL, "consumption": "-1"}, {**NATIONAL, "gdp_deflator": "0"}, {**NATIONAL, "population": "0"}):
            self.assertTrue(blocked("national_income", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "GDP", "method": "national_income", "currency": "PHP", "period": "annual", "inputs": NATIONAL})
        self.assertIn("gdp", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class GrowthRate(unittest.TestCase):
    def m(self): return LIBRARY["growth_rate"]

    def test_arithmetic(self):
        out = self.m().impl(GROWTH)
        self.assertEqual(out["total_growth"], D(1))
        self.assertAlmostEqual(float(out["cagr"]), 0.0717734625, places=9)
        self.assertAlmostEqual(float(out["doubling_time_years"]), 10.0315628, places=5)

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(GROWTH, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(GROWTH, self.m().impl)))
        for inputs in ({"start_value": "0", "end_value": "200", "periods": "10"},
                       {"start_value": "100", "end_value": "200", "periods": "0"}):
            self.assertTrue(blocked("growth_rate", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Growth", "method": "growth_rate", "currency": "PHP", "period": "annual", "inputs": GROWTH})
        self.assertIn("growth", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class InflationCpi(unittest.TestCase):
    def m(self): return LIBRARY["inflation_cpi"]

    def test_arithmetic(self):
        out = self.m().impl(INFLATION)
        self.assertEqual(out["inflation_rate"], D("0.05"))
        self.assertAlmostEqual(float(out["real_interest_rate"]), 0.0285714286, places=9)
        self.assertAlmostEqual(float(out["real_wage_growth"]), -0.0095238095, places=9)

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(INFLATION, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(INFLATION, self.m().impl)))
        for inputs in ({"cpi_start": "0", "cpi_end": "105"}, {**INFLATION, "nominal_interest_rate": "-1"}):
            self.assertTrue(blocked("inflation_cpi", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Inflation", "method": "inflation_cpi", "currency": "PHP", "period": "annual", "inputs": INFLATION})
        self.assertIn("inflation", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class UnemploymentRate(unittest.TestCase):
    def m(self): return LIBRARY["unemployment_rate"]

    def test_arithmetic(self):
        out = self.m().impl(UNEMPLOYMENT)
        self.assertEqual(out["unemployed"], D(80))
        self.assertEqual(out["unemployment_rate"], D("0.08"))
        self.assertAlmostEqual(float(out["labour_force_participation_rate"]), 2 / 3, places=12)

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(UNEMPLOYMENT, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(UNEMPLOYMENT, self.m().impl)))
        for inputs in ({**UNEMPLOYMENT, "employed": "1100"}, {**UNEMPLOYMENT, "labour_force": "1600"}):
            self.assertTrue(blocked("unemployment_rate", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Unemployment", "method": "unemployment_rate", "period": "annual", "inputs": UNEMPLOYMENT})
        self.assertIn("unemployment", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class MoneyMultiplier(unittest.TestCase):
    def m(self): return LIBRARY["money_multiplier"]

    def test_arithmetic(self):
        out = self.m().impl(MONEY)
        self.assertEqual((out["simple_money_multiplier"], out["extended_money_multiplier"],
                          out["money_supply_simple"], out["money_supply_extended"]),
                         (D(10), D(7), D(1000), D(700)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(MONEY, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(MONEY, self.m().impl)))
        for inputs in ({"monetary_base": "100", "reserve_ratio": "0"},
                       {"monetary_base": "100", "reserve_ratio": "1.2"},
                       {"monetary_base": "100", "reserve_ratio": "0.1", "currency_drain_ratio": "1"}):
            self.assertTrue(blocked("money_multiplier", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Money", "method": "money_multiplier", "currency": "PHP", "period": "annual", "inputs": MONEY})
        self.assertIn("multiplier", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class FiscalMultiplier(unittest.TestCase):
    def m(self): return LIBRARY["fiscal_multiplier"]

    def test_arithmetic(self):
        out = self.m().impl(FISCAL)
        self.assertEqual((out["government_spending_multiplier"], out["tax_multiplier"],
                          out["balanced_budget_multiplier"], out["output_change"]),
                         (D("2.5"), D(-2), D("0.5"), D(250)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(FISCAL, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(FISCAL, self.m().impl)))
        for inputs in ({"mpc": "0"}, {"mpc": "1"}, {"mpc": "0.8", "tax_rate": "1"}):
            self.assertTrue(blocked("fiscal_multiplier", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Fiscal", "method": "fiscal_multiplier", "currency": "PHP", "period": "annual", "inputs": FISCAL})
        self.assertIn("multiplier", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


class BudgetDebt(unittest.TestCase):
    def m(self): return LIBRARY["budget_debt"]

    def test_arithmetic(self):
        out = self.m().impl(BUDGET)
        self.assertEqual((out["total_spending"], out["overall_balance"], out["primary_balance"]),
                         (D(550), D(-50), D(-20)))
        self.assertEqual((out["debt_to_gdp"], out["debt_ratio_change"]), (D("0.5"), D(0)))

    def test_checks_and_refusals(self):
        self.assertEqual(tuple(n for n, _ in self.m().tests(BUDGET, self.m().impl)), self.m().test_names)
        self.assertTrue(all(ok for _, ok in self.m().tests(BUDGET, self.m().impl)))
        for inputs in ({**BUDGET, "nominal_gdp": "0"},
                       {**BUDGET, "debt_stock": "0"},
                       {**BUDGET, "nominal_growth_rate": "-1"}):
            self.assertTrue(blocked("budget_debt", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Budget", "method": "budget_debt", "currency": "PHP", "period": "annual", "inputs": BUDGET})
        self.assertIn("balance", d.report.lower())
        self.assertTrue(all(ok for ok in d.appendix["tests"]))


if __name__ == "__main__":
    unittest.main()
