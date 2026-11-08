import os, sys, json, threading, unittest, urllib.request
sys.path.insert(0, "src")
from http.server import ThreadingHTTPServer
from bp.session import SessionManager, stage_states, STATES
from bp import server, methods
from bp.orchestrator import STAGES
from test_pipeline import REQ

class S(unittest.TestCase):
    def test_plan_before_execution_nothing_computed(self):
        s = SessionManager().create(REQ); d = s.to_dict()
        self.assertEqual(d["status"], "awaiting_confirmation"); self.assertIsNone(d["delivery"])
        self.assertEqual(d["stage_states"]["formalization"], "awaiting_user")
        self.assertEqual(d["stage_states"]["execution"], "planned")
        self.assertFalse(any(e["stage"] == "execution" for e in d["events"]))
        self.assertEqual(d["work_plan"]["planned_checks"], list(methods.LIBRARY["npv"].test_names))
        self.assertIsNone(d["spec"]["hash"])
    def test_confirm_runs_and_states_from_events(self):
        s = SessionManager().create(REQ); s.confirm(True); d = s.to_dict()
        self.assertEqual(d["status"], "delivered"); self.assertTrue(d["spec"]["hash"])
        self.assertTrue(all(v == "passed" for v in d["stage_states"].values()), d["stage_states"])
        json.dumps(d)  # fully serializable
    def test_reject_blocks_and_marks_rest_not_run(self):
        s = SessionManager().create(REQ); s.confirm(False); d = s.to_dict()
        self.assertEqual(d["stage_states"]["formalization"], "blocked"); self.assertEqual(d["stage_states"]["execution"], "not_run")
        with self.assertRaises(ValueError): s.confirm(True)
    def test_declared_test_names_match_real_tests(self):
        for m in methods.LIBRARY.values():
            inp = {"npv": REQ["inputs"], "irr": {"cashflows": ["-1000", "400", "400", "400", "400"]},
               "discounted_payback": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10"},
               "breakeven": {"fixed": "1000", "price": "20", "variable": "10"}, "descriptive_stats": {"values": ["1", "2", "4"], "missing_codes": []},
               "pearson": {"x": ["1","2","3","4","5"], "y": ["2","4","5","4","5"]}, "spearman": {"x": ["1","2","3","4","5"], "y": ["1","4","9","16","10"]},
               "welch_t": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"]}}, "mann_whitney": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"]}},
               "anova": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"], "c": ["1","2","3","4","5"]}}, "kruskal_wallis": {"groups": {"a": ["1","2","3","4","5"], "b": ["2","4","6","8","10"], "c": ["3","1","5","2","4"]}},
               "chi_square": {"table": [[10, 20, 30], [20, 40, 60]]},
               "trend_forecast": {"values": ["10", "12", "11", "14", "13", "16", "15", "18"]},
               "ratio_analysis": {"current_assets": "5000", "current_liabilities": "2000", "cash": "800", "inventory": "1200",
                                  "receivables": "1500", "payables": "900", "total_assets": "12000", "total_liabilities": "7000", "equity": "5000",
                                  "revenue": "20000", "cost_of_sales": "12000", "operating_profit": "3000", "net_income": "1800", "interest_expense": "400"},
               "wacc": {"equity_value": "800000", "debt_value": "200000", "cost_of_equity": "0.12", "cost_of_debt_after_tax": "0.05"},
               "dcf_valuation": {"cashflows": ["100000", "120000", "140000", "155000"], "discount_rate": "0.10", "terminal_growth": "0.02"},
               "equity_bridge": {"enterprise_value": "1750939.14", "debt": "300000", "cash": "150000", "minority_interest": "20000", "preferred_equity": "10000", "shares_outstanding": "100000"},
               "logistic_regression": {"y": ["0", "0", "0", "1", "0", "1", "1", "1", "1", "1", "1", "1", "0", "1", "1", "0", "1", "0", "0", "1", "0", "0", "0", "1", "1", "0", "0", "1", "1", "0", "1", "1", "1", "1", "0", "1", "1", "1", "1", "0"], "predictors": {"size": ["-1.72", "-0.26", "-0.74", "-0.01", "0.2", "-0.72", "-0.74", "-0.28", "-0.8", "1.32", "0.48", "1.3", "-1.0", "-0.02", "0.62", "0.8", "3.11", "-0.84", "-0.01", "0.17", "-0.15", "0.42", "-0.17", "-0.96", "0.79", "-0.95", "-1.79", "-0.16", "0.26", "0.47", "2.23", "0.64", "0.92", "0.22", "0.89", "-0.08", "2.05", "1.76", "0.01", "0.15"], "group": ["0", "0", "0", "0", "1", "0", "0", "0", "1", "1", "1", "0", "0", "1", "1", "0", "1", "0", "0", "1", "0", "0", "1", "1", "0", "0", "0", "0", "1", "0", "0", "0", "0", "0", "1", "1", "1", "0", "1", "1"]}},
               "reliability_alpha": {"items": {"one": ["4", "5", "3", "4", "5", "2", "4", "3"], "two": ["4", "4", "3", "5", "4", "3", "4", "2"], "three": ["3", "4", "2", "4", "5", "3", "4", "3"], "four": ["4", "5", "3", "4", "4", "2", "3", "3"]}},
               "cost_benefit": {"costs": ["50000", "10000", "10000"], "benefits": ["20000", "30000", "40000"], "discount_rate": "0.05"},
               "cost_effectiveness": {"options": [{"name": "basic", "cost": "10000", "effect": "40"}, {"name": "intensive", "cost": "18000", "effect": "60"}]},
               "sroi": {"investment": "60000", "benefits": ["20000", "25000", "30000"], "discount_rate": "0.04"},
               "unit_economics": {"price": "49", "variable_cost": "12", "acquisition_cost": "80", "churn_rate": "0.04"},
               "multi_product_breakeven": {"fixed_costs": "6000", "products": [{"name": "coffee", "price": "5", "variable_cost": "2", "mix_units": "3"}, {"name": "cake", "price": "6", "variable_cost": "3", "mix_units": "1"}]},
               "two_way_anova": {"data": [{"response": "1", "factor_a": "low", "factor_b": "x"}, {"response": "3", "factor_a": "low", "factor_b": "x"}, {"response": "5", "factor_a": "low", "factor_b": "y"}, {"response": "7", "factor_a": "low", "factor_b": "y"}, {"response": "3", "factor_a": "high", "factor_b": "x"}, {"response": "5", "factor_a": "high", "factor_b": "x"}, {"response": "7", "factor_a": "high", "factor_b": "y"}, {"response": "9", "factor_a": "high", "factor_b": "y"}]},
               "posthoc_pairwise": {"groups": {"a": ["10", "12", "11", "13"], "b": ["14", "15", "16", "14"], "c": ["18", "17", "19", "20"]}, "adjust": "holm", "alpha": "0.05"},
               "currency_convert": {"amount": "1000", "from_currency": "USD", "to_currency": "EUR", "rate": "0.92", "rate_provenance": "user"},
               "paired_t": {"pairs": {"before": ["10", "12", "11", "9", "13"], "after": ["12", "13", "12", "10", "14"]}},
               "one_sample_t": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"], "mu0": "75"},
               "multiple_comparison": {"p_values": ["0.01", "0.04", "0.03", "0.005"], "method": "holm"},
               "power_analysis": {"design": "two_sample", "effect": "5", "n1": "30", "n2": "40", "sd1": "10", "sd2": "12", "alpha": "0.05", "tails": "two_sided", "target_power": "0.8"},
               "missing_data_bounds": {"values": ["10", "12", "", "14", "99", "16"], "missing_codes": ["99"], "mechanism": "unknown"},
               "weighted_summary": {"values": ["1", "2", "3", "4"], "weights": ["1", "1", "1", "3"], "weight_kind": "reliability"},
               "time_value": {"present_value": "100000", "payment": "12000", "rate": "0.06", "periods": "5", "compounding": "quarterly", "timing": "end"},
               "loan_amortization": {"principal": "200000", "annual_rate": "0.09", "years": "5", "payments_per_year": "12"},
               "bond_analysis": {"face_value": "1000", "coupon_rate": "0.08", "years_to_maturity": "10", "yield_to_maturity": "0.06", "payments_per_year": "2"},
               "capm": {"risk_free_rate": "0.04", "market_return": "0.10", "beta": "1.2", "debt_to_equity": "0.6", "tax_rate": "0.30"},
               "dupont_analysis": {"revenue": "20000", "net_income": "1800", "total_assets": "12000", "equity": "5000", "cost_of_sales": "12000", "ebit": "3000", "pretax_income": "2400", "tax_expense": "600"},
               "multiples_valuation": {"metric": "ebitda", "subject_value": "500000", "comparables": [{"name": "A", "multiple": "8"}, {"name": "B", "multiple": "10"}, {"name": "C", "multiple": "12"}], "net_debt": "300000", "shares_outstanding": "100000"},
               "working_capital": {"revenue": "20000", "cost_of_sales": "12000", "inventory": "1200", "receivables": "1500", "payables": "900", "annual_demand": "5000", "order_cost": "50", "holding_cost_per_unit": "4", "discount_percent": "0.02", "credit_terms_days": "30", "discount_days": "10", "lead_time_days": "7", "safety_stock": "100"},
               "portfolio_analysis": {"returns_a": ["0.02", "0.03", "-0.01", "0.04", "0.01", "0.02"], "returns_b": ["0.01", "0.02", "0.00", "0.03", "0.02", "0.01"], "weight_a": "0.6", "risk_free_rate": "0.02", "returns_market": ["0.01", "0.02", "-0.02", "0.03", "0.00", "0.02"]},
               "project_metrics": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10", "finance_rate": "0.08"},
               "option_pricing": {"option_type": "call", "spot_price": "100", "strike_price": "100", "volatility": "0.25", "risk_free_rate": "0.05", "time_to_maturity": "1", "steps": "200"},
               "risk_metrics": {"returns": ["0.01", "-0.02", "0.015", "0.00", "-0.03", "0.025", "0.01", "-0.01", "0.02", "-0.005"], "confidence": "0.95", "portfolio_value": "1000000", "horizon_days": "1", "stress_return": "-0.05"},
               "fx_parity": {"spot_rate": "56", "domestic_rate": "0.05", "foreign_rate": "0.03", "domestic_inflation": "0.04", "foreign_inflation": "0.02", "time_to_maturity": "1", "forward_rate": "57"},
               "leverage_analysis": {"ebit": "500000", "interest_expense": "100000", "tax_rate": "0.30", "debt": "800000", "equity": "1200000", "shares_outstanding": "100000", "working_capital": "300000", "retained_earnings": "400000", "total_assets": "2000000", "total_liabilities": "800000", "sales": "3000000", "market_value_equity": "1800000"},
               "scenario_analysis": {"cashflows": ["-1000", "400", "400", "400", "400"], "discount_rate": "0.10", "rate_low": "0.05", "rate_high": "0.20"},
               "trend_analysis": {"years": ["2022", "2023", "2024", "2025"], "revenue": ["1000", "1100", "1210", "1331"], "cost_of_sales": ["600", "650", "710", "760"], "operating_expenses": ["200", "220", "240", "260"], "net_income": ["120", "140", "160", "190"], "total_assets": ["2000", "2100", "2250", "2400"], "equity": ["900", "980", "1080", "1200"]},
               "portfolio_valuation": {"holdings": [{"symbol": "AAPL", "shares": "10", "price": "200"},
                                        {"symbol": "MSFT", "shares": "5", "price": "400"}], "cash": "1000"},
               "portfolio_performance": {"periods": [{"label": "week 1", "start_nav": "10000", "end_nav": "10250", "flow": "0"}, {"label": "week 2", "start_nav": "10250", "end_nav": "10100", "flow": "0"}]},
               "market_sizing": {"target_population": "100000", "annual_spend_per_customer": "500", "serviceable_share": "0.4", "obtainable_share": "0.1"},
               "startup_capital": {"start_up_costs": "500000", "working_capital": "100000", "contingency_rate": "0.1", "owner_equity": "300000", "loan_amount": "200000"},
               "cash_runway": {"opening_cash": "500000", "monthly_net_cash_flow": "-50000", "monthly_growth": "0", "target_months": "12"},
               "pricing_decision": {"unit_cost": "100", "fixed_cost": "50000", "expected_units": "1000", "markup_rate": "0.2", "target_margin_rate": "0.15", "target_profit": "20000"},
               "return_on_investment": {"total_investment": "100000", "net_gain": "30000", "years": "3"},
               "sales_projection": {"start_units": "100", "price": "50", "unit_variable_cost": "20", "fixed_cost_per_period": "1000", "growth_rate": "0.02", "periods": "6"},
               "cap_table_round": {"pre_money_valuation": "2000000", "investment": "500000", "founders_shares": "1000000", "option_pool_pct": "0.05"},
               "sales_funnel": {"stages": [{"name": "visits", "count": "1000"}, {"name": "leads", "count": "200"}, {"name": "sales", "count": "50"}], "spend": "5000"},
               "cohort_retention": {"cohort_sizes": ["100", "80"], "retained": [["100", "70", "55"], ["80", "60", "45"]]},
               "demand_curve": {"prices": ["10", "15", "20", "25"], "quantities": ["200", "170", "140", "110"]},
               "purchase_intent": {"definitely": "60", "probably": "40", "maybe": "50", "never": "50", "target_population": "10000", "price": "20"},
               "campaign_efficiency": {"impressions": "10000", "clicks": "400", "conversions": "20", "spend": "5000", "revenue": "15000", "contribution_margin_rate": "0.4"},
               "ab_test_two_proportion": {"visitors_a": "1000", "conversions_a": "50", "visitors_b": "1000", "conversions_b": "70", "minimum_effect": "0.1"},
               "attribution_split": {"channels": [{"name": "search", "first_click": "40", "last_click": "25", "linear": "32"}, {"name": "social", "first_click": "18", "last_click": "31", "linear": "29"}]},
               "channel_economics": {"channels": [{"name": "search", "spend": "6000", "new_customers": "40", "contribution_margin": "150", "churn_rate": "0.04"}, {"name": "social", "spend": "3500", "new_customers": "18", "contribution_margin": "95", "churn_rate": "0.06"}]},
               "email_list_health": {"list_start": "800", "new_subscribers": "60", "unsubscribes": "9", "bounces": "4", "sends": "750", "opens": "225", "clicks": "45", "revenue": "3800"},
               "social_engagement": {"impressions": "15000", "reach": "9500", "engagements": "570", "followers_start": "1800", "followers_gained": "90", "spend": "2500", "posts": "3"},
               "web_analytics": {"channels": [{"name": "organic", "sessions": "4200", "conversions": "135", "revenue": "68000"}, {"name": "paid", "sessions": "2400", "conversions": "96", "revenue": "43000"}], "organic_impressions": "60000", "organic_clicks": "2400"},
               "rfm_scoring": {"customers": [{"name": "C1", "recency_days": "3", "frequency": "9", "monetary": "15000"}, {"name": "C2", "recency_days": "9", "frequency": "7", "monetary": "11000"}, {"name": "C3", "recency_days": "18", "frequency": "5", "monetary": "7000"}, {"name": "C4", "recency_days": "40", "frequency": "3", "monetary": "3000"}, {"name": "C5", "recency_days": "90", "frequency": "1", "monetary": "800"}]},
               "media_plan": {"population": "1000000", "vehicles": [{"name": "TV", "reach": "450000", "insertions": "8", "cost": "1200000"}, {"name": "Radio", "reach": "300000", "insertions": "12", "cost": "450000"}]},
               "market_share": {"firm_sales": "2400000", "market_sales": "12000000", "prior_firm_sales": "2100000", "prior_market_sales": "11500000", "customers": "48000", "target_population": "400000", "largest_competitor_sales": "3600000"},
               "clv_model": {"margin_per_period": "1500", "churn_rate": "0.04", "discount_rate": "0.10", "horizon_periods": "24", "acquisition_cost": "9000"},
               "customer_profitability": {"segments": [{"name": "Enterprise", "revenue": "5000000", "direct_cost": "3000000", "allocated_cost": "600000"}, {"name": "SME", "revenue": "3000000", "direct_cost": "2100000", "allocated_cost": "400000"}, {"name": "Retail", "revenue": "1200000", "direct_cost": "1500000", "allocated_cost": "100000"}], "concentration_threshold": "0.8"},
               "standard_cost_variances": {"actual_units": "1000", "standard_material_per_unit": "2", "standard_material_price": "10", "actual_material_quantity": "2100", "actual_material_price": "11", "standard_hours_per_unit": "1", "standard_labour_rate": "20", "actual_hours": "950", "actual_labour_rate": "21"},
               "inventory_policy": {"annual_demand": "5000", "order_cost": "200", "holding_cost_per_unit": "10", "lead_time_days": "7", "service_level": "0.95", "daily_demand_sd": "5"},
               "queue_analysis": {"arrival_rate": "12", "service_rate": "20"},
               "capacity_analysis": {"resources": [{"name": "a", "available_hours": "8", "minutes_per_unit": "5"}, {"name": "b", "available_hours": "8", "minutes_per_unit": "10"}], "demand": "40"},
               "cpm_schedule": {"estimate": "single", "activities": [{"id": "a", "duration": "2", "predecessors": ""}, {"id": "b", "duration": "3", "predecessors": "a"}]},
               "earned_value": {"planned_value": "1000", "earned_value": "900", "actual_cost": "950", "budget_at_completion": "2000"},
               "resource_leveling": {"resources": [{"name": "crew", "capacity": "2"}], "activities": [
                   {"id": "a", "duration": "2", "resource": "crew", "demand": "2", "predecessors": ""},
                   {"id": "b", "duration": "2", "resource": "crew", "demand": "2", "predecessors": "a"}]},
               "project_crashing": {"target_duration": "4", "activities": [
                   {"id": "a", "normal_duration": "4", "crash_duration": "2", "crash_cost": "40", "predecessors": ""},
                   {"id": "b", "normal_duration": "3", "crash_duration": "2", "crash_cost": "20", "predecessors": "a"}]},
               "calendar_schedule": {"working_periods": "0,1,2,5,6,7", "activities": [
                   {"id": "a", "duration": "2", "predecessors": ""},
                   {"id": "b", "duration": "2", "predecessors": "a"}]},
               "multi_project_schedule": {"resources": [{"name": "crew", "capacity": "2"}], "projects": [
                   {"name": "alpha", "priority": "1", "activities": [
                       {"id": "a", "duration": "2", "resource": "crew", "demand": "2", "predecessors": ""},
                       {"id": "b", "duration": "2", "resource": "crew", "demand": "2", "predecessors": "a"}]},
                   {"name": "beta", "priority": "2", "activities": [
                       {"id": "x", "duration": "2", "resource": "crew", "demand": "1", "predecessors": ""},
                       {"id": "y", "duration": "2", "resource": "crew", "demand": "1", "predecessors": "x"}]}]},
               "schedule_risk": {"iterations": "200", "seed": "7", "activities": [
                   {"id": "a", "optimistic": "1", "most_likely": "2", "pessimistic": "4", "predecessors": ""},
                   {"id": "b", "optimistic": "2", "most_likely": "3", "pessimistic": "5", "predecessors": "a"}]},
               "decision_tree": {"tree": {"type": "decision", "alternatives": [
                   {"name": "A", "node": {"type": "terminal", "value": "10"}},
                   {"name": "B", "node": {"type": "terminal", "value": "5"}}]}},
               "real_option": {"underlying_value": "100", "investment_cost": "100", "volatility": "0.30",
                               "risk_free_rate": "0.05", "steps": "5", "option_type": "call", "exercise": "european"},
               "multi_criteria": {"scale_max": "10", "criteria": [{"name": "cost", "weight": "0.6"}, {"name": "speed", "weight": "0.4"}],
                                  "alternatives": [{"name": "A", "scores": {"cost": "9", "speed": "5"}},
                                                   {"name": "B", "scores": {"cost": "6", "speed": "9"}}]},
               "monte_carlo": {"model": "npv", "iterations": "100", "seed": "7", "discount_rate": "0.10",
                               "cashflows": [{"name": "outlay", "period": "0", "distribution": "fixed", "value": "-100"},
                                             {"name": "year_one", "period": "1", "distribution": "uniform", "low": "50", "high": "150"}]},
               "oee_analysis": {"planned_production_time": "480", "downtime": "40", "ideal_cycle_time": "0.5", "total_units": "700", "good_units": "680"},
               "process_control": {"values": ["10", "11", "9", "10", "12", "9", "10", "11"]},
               "abc_costing": {"activities": [{"name": "setup", "pool_cost": "1000"}], "products": [{"name": "x", "units": "100"}, {"name": "y", "units": "50"}], "allocations": [{"activity": "setup", "product": "x", "driver_quantity": "2"}, {"activity": "setup", "product": "y", "driver_quantity": "3"}]},
               "sales_variances": {"products": [{"name": "x", "budget_units": "10", "budget_price": "5", "actual_units": "12", "actual_price": "6"}, {"name": "y", "budget_units": "10", "budget_price": "8", "actual_units": "8", "actual_price": "7"}]},
               "line_balancing": {"cycle_time": "10", "tasks": [{"id": "a", "time": "4", "predecessors": ""}, {"id": "b", "time": "5", "predecessors": "a"}]},
               "tax_declared": {"taxable_income": "1000", "income_tax_rate": "0.25", "vat_output_tax": "120", "vat_input_tax": "70"},
               "depreciation_schedule": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
               "proforma_statements": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                                       "operating_costs": ["300000", "320000", "340000"],
                                       "depreciation": ["90000", "90000", "90000"],
                                       "interest": ["40000", "30000", "20000"],
                                       "principal_repayment": ["100000", "100000", "100000"], "capex": ["0", "0", "0"],
                                       "tax_rate": "0.25", "receivable_days": "30", "inventory_days": "45", "payable_days": "30",
                                       "opening_cash": "200000", "opening_fixed_assets": "450000",
                                       "opening_receivables": "0", "opening_inventory": "0", "opening_payables": "0",
                                       "opening_loan": "400000", "opening_equity": "250000"},
               "sales_from_market": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
               "sensitivity_table": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                                     "base_fixed_cost": "300000",
                                     "price_changes": ["-0.1", "0", "0.1"], "volume_changes": ["-0.2", "0", "0.2"]},
               "demand_supply_equilibrium": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2"},
               "elasticity": {"quantity_1": "100", "price_1": "10", "quantity_2": "140", "price_2": "8"},
               "tax_incidence": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "tax_per_unit": "6"},
               "price_control": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "control_price": "15", "control_type": "ceiling"},
               "market_concentration": {"firm_revenues": ["40", "25", "15", "10", "10"]},
               "cost_curves": {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5", "quantity": "20", "price": "40"},
               "profit_maximization": {"demand_intercept": "100", "demand_slope": "2", "fixed_cost": "100", "linear_cost": "10", "quadratic_cost": "0.5"},
               "market_power": {"price": "50", "marginal_cost": "20"},
               "national_income": {"consumption": "600", "investment": "150", "government_spending": "200", "exports": "120", "imports": "170", "net_factor_income": "20", "depreciation": "50", "population": "100", "gdp_deflator": "120"},
               "growth_rate": {"start_value": "100", "end_value": "200", "periods": "10"},
               "inflation_cpi": {"cpi_start": "100", "cpi_end": "105", "nominal_interest_rate": "0.08", "wage_start": "100", "wage_end": "104"},
               "unemployment_rate": {"labour_force": "1000", "employed": "920", "working_age_population": "1500"},
               "money_multiplier": {"monetary_base": "100", "reserve_ratio": "0.10", "currency_drain_ratio": "0.05"},
               "fiscal_multiplier": {"mpc": "0.8", "tax_rate": "0.25", "government_spending_change": "100", "tax_change": "0"},
               "budget_debt": {"government_revenue": "500", "government_spending": "520", "interest_payments": "30", "debt_stock": "1000", "nominal_gdp": "2000", "nominal_growth_rate": "0.05", "inflation_rate": "0.02"},
               "externality_pigouvian": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "marginal_external_cost": "4"},
               "public_good": {"mb1_intercept": "100", "mb1_slope": "2", "mb2_intercept": "80", "mb2_slope": "3", "mc_intercept": "20", "mc_slope": "1"},
               "social_welfare": {"incomes": ["10", "20", "30", "40"], "welfare_function": "utilitarian"},
               "gini_coefficient": {"incomes": ["10", "20", "30", "40"]},
               "poverty_measures": {"incomes": ["10", "20", "30", "40"], "poverty_line": "25"},
               "tax_progressivity": {"incomes": ["10", "20", "30", "40"], "taxes": ["1", "3", "6", "10"]},
               "optimal_pollution": {"marginal_damage_intercept": "10", "marginal_damage_slope": "2", "marginal_abatement_intercept": "100", "marginal_abatement_slope": "3"},
               "output_gap_okun": {"actual_gdp": "1050", "potential_gdp": "1000", "current_unemployment_rate": "0.06", "okun_coefficient": "0.5"},
               "comparative_advantage": {"countries": [{"name": "A", "good_1_hours": "2", "good_2_hours": "1"}, {"name": "B", "good_1_hours": "5", "good_2_hours": "3"}]},
               "tariff_welfare": {"demand_intercept": "100", "demand_slope": "2", "supply_intercept": "20", "supply_slope": "2", "world_price": "10", "tariff_per_unit": "5"},
               "exchange_rate_ppp": {"price_domestic": "5000", "price_foreign": "100", "nominal_rate": "55", "domestic_inflation": "0.04", "foreign_inflation": "0.02"},
               "interest_rate_parity": {"spot_rate": "50", "domestic_rate": "0.06", "foreign_rate": "0.04", "time_to_maturity": "1", "forward_rate": "51", "domestic_inflation": "0.04", "foreign_inflation": "0.02"},
               "balance_of_payments": {"current_account": "-50", "capital_account": "0", "financial_account": "50", "gdp": "1000"},
               "hdi": {"life_expectancy": "70", "expected_years_schooling": "12", "mean_years_schooling": "8", "gni_per_capita": "5000"},
               "expected_utility": {"outcomes": ["50", "150"], "probabilities": ["0.5", "0.5"], "utility_function": "crra", "risk_aversion": "2"},
               "prospect_theory": {"reference_point": "100", "outcomes": ["150", "50"], "probabilities": ["0.5", "0.5"]},
               "labour_market": {"nominal_wage": "100", "cpi": "105", "labour_productivity": "120", "vacancies": "10", "unemployment_rate": "0.05"},
               "price_discrimination": {"demand_intercept_1": "100", "demand_slope_1": "2", "demand_intercept_2": "80", "demand_slope_2": "1", "marginal_cost": "10"},
               "cournot_duopoly": {"demand_intercept": "100", "demand_slope": "2", "marginal_cost_1": "10", "marginal_cost_2": "20"},
               "difference_in_differences": {"treated_pre": "50", "treated_post": "70", "control_pre": "40", "control_post": "45"},
               "nash_equilibrium": {"row_payoffs": ["3", "0", "5", "1"], "column_payoffs": ["3", "5", "0", "1"]},
               "panel_regression": {"data": [{"entity": "A", "period": "1", "y": "2", "x": "1"}, {"entity": "A", "period": "2", "y": "4", "x": "2"}, {"entity": "A", "period": "3", "y": "6", "x": "3"}, {"entity": "B", "period": "1", "y": "5", "x": "2"}, {"entity": "B", "period": "2", "y": "7", "x": "3"}, {"entity": "B", "period": "3", "y": "9", "x": "4"}, {"entity": "C", "period": "1", "y": "1", "x": "1"}, {"entity": "C", "period": "2", "y": "5", "x": "3"}, {"entity": "C", "period": "3", "y": "9", "x": "5"}]},
               "instrumental_variables": {"y": ["3", "5", "7", "6", "8", "10", "11", "13"], "x": ["2", "4", "5", "4", "5", "7", "8", "9"], "z": ["1", "2", "3", "4", "5", "6", "7", "8"]},
               "regression_discontinuity": {"data": [{"running": "-3", "outcome": "0"}, {"running": "-2", "outcome": "1"}, {"running": "-1", "outcome": "2"}, {"running": "1", "outcome": "10"}, {"running": "2", "outcome": "11"}, {"running": "3", "outcome": "12"}], "cutoff": "0", "bandwidth": "2.5"},
               "probit": {"y": ["0", "1", "0", "1", "0", "1", "0", "1", "1", "0"], "x": ["-2", "-1.5", "-1", "-0.5", "0", "0.5", "1", "1.5", "2", "2.5"]},
               "management_accounts": {"spec": {"period": {"start": "2026-01-01", "end": "2026-03-31"}, "currency": "USD", "framework": "local",
                                                 "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"}, {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
                                                           {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"}, {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"}],
                                                 "prior_closing": {"1000": "1000", "3000": "1000"},
                                                 "opening": [{"lines": [{"account": "1000", "debit": "1000"}, {"account": "3000", "credit": "1000"}]}],
                                                 "entries": [{"date": "2026-01-15", "description": "sale", "lines": [{"account": "1000", "debit": "500"}, {"account": "4000", "credit": "500"}]}], "schedules": []}},
               "ols": {"y": ["52","55","61","58","70","72","69","80"], "predictors": {"a": ["1","2","3","4","5","6","7","8"], "b": ["6","7","5","8","6","7","8","6"]}},
               "trial_balance_check": {"journal": {"period": {"start": "2026-01-01", "end": "2026-03-31"}, "currency": "USD", "framework": "IFRS", "places": 2,
                                                     "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"},
                                                               {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "role": "capital"},
                                                               {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"}],
                                                     "prior_closing": {"1000": "1000", "3000": "1000"},
                                                     "opening": [{"lines": [{"account": "1000", "debit": "1000"}, {"account": "3000", "credit": "1000"}]}],
                                                     "entries": [{"date": "2026-02-01", "description": "capital", "lines": [{"account": "1000", "debit": "500"}, {"account": "3000", "credit": "500"}]}],
                                                     "schedules": []},
                                        "trial_balance": [{"code": "1000", "debit": "1500"}, {"code": "3000", "credit": "1500"}]}}
            # `bp.finance_methods` registers more methods into `methods.LIBRARY` when it is
            # imported, and the server imports it. Those are covered by their own suite, so a
            # method this map does not know is skipped rather than failing the whole run.
            name = {"ols_robust": "ols"}.get(m.name, m.name)
            if name not in inp:
                continue
            self.assertEqual(tuple(n for n, _ in m.tests(inp[name], m.impl)), m.test_names)
    def test_malformed_input_blocks_not_crashes(self):
        s = SessionManager().create({**REQ, "inputs": {"rate": "abc", "cashflows": ["1", "2"]}})
        self.assertEqual(s.to_dict()["status"], "blocked")
    def test_missing_field_rejected(self):
        with self.assertRaises(ValueError): SessionManager().create({"method": "npv"})
    def test_skipped_sensitivity_is_not_run(self):
        r = {k: v for k, v in REQ.items() if k != "sensitivity"}
        s = SessionManager().create(r); s.confirm(True); self.assertEqual(s.to_dict()["stage_states"]["sensitivity"], "not_run")

class API(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
    @classmethod
    def tearDownClass(cls): cls.srv.shutdown(); cls.srv.server_close()
    def call(self, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r: return r.status, r.read()
        except urllib.error.HTTPError as e: return e.code, e.read()
    def test_full_flow(self):
        c, b = self.call("/api/sessions", REQ); self.assertEqual(c, 201); s = json.loads(b)
        c, b = self.call(f"/api/sessions/{s['id']}/confirm", {}); d = json.loads(b)
        self.assertEqual(d["status"], "delivered"); self.assertIn("USD (5.26)", d["delivery"]["report"])
        c, b = self.call(f"/api/sessions/{s['id']}"); self.assertEqual(json.loads(b)["status"], "delivered")
    def test_errors(self):
        self.assertEqual(self.call("/api/sessions", {"method": "npv"})[0], 400)
        self.assertEqual(self.call("/api/sessions/nope")[0], 404)
    def test_the_published_tree_is_served_here_too(self):
        """Cloudflare Pages serves the whole `web/` tree; so must this server.

        The page falls back to `/subjects.json` when the API does not answer, and that
        fallback is the deployed site's behaviour.  Serving the same tree at the same
        URLs is what makes a link work at both addresses.
        """
        c, b = self.call("/subjects.json")
        self.assertEqual(c, 200)
        with open(os.path.join(server.WEB, "subjects.json"), "rb") as stream:
            self.assertEqual(b, stream.read())
        self.assertEqual(len(json.loads(b)["subjects"]), 11)

    def test_a_baked_subject_page_is_served_here_too(self):
        c, b = self.call("/subject-economics.json")
        self.assertEqual(c, 200)
        self.assertEqual(json.loads(b)["id"], "economics")

    def test_a_file_cannot_escape_the_web_directory(self):
        c, b = self.call("/..%2Fsrc%2Fbp%2Fbuild.py")
        self.assertEqual(c, 404)
        self.assertNotIn(b"VERSION", b)

    def test_an_unknown_api_route_stays_json(self):
        c, b = self.call("/api/not-a-route")
        self.assertEqual(c, 404)
        self.assertEqual(json.loads(b)["error"], "not found")

    def test_index_served(self):
        c, b = self.call("/"); self.assertEqual(c, 200); self.assertIn(b"Draft work plan", b); self.assertIn(b"Account mapping", b); self.assertIn(b"Download financial statements", b)
    def test_two_phase_account_mapping_checkpoint(self):
        from bp import accounts
        c, b = self.call("/api/sessions", {"objective": "Prepare the management accounts.", "method": "management_accounts", "currency": "USD", "inputs": {"spec": accounts.EXAMPLE_SPEC}})
        s = json.loads(b); self.assertEqual((c, s["status"]), (201, "awaiting_confirmation"))
        c, b = self.call(f"/api/sessions/{s['id']}/confirm", {}); d = json.loads(b)
        self.assertEqual((c, d["status"]), (200, "awaiting_mapping_confirmation"))
        self.assertEqual([r["code"] for r in d["account_mapping"]["rows"]], ["1000", "3000", "3100", "4000", "5000"])
        self.assertEqual(d["stage_states"]["formalization"], "awaiting_user"); self.assertIsNone(d["delivery"])
        c, b = self.call(f"/api/sessions/{s['id']}/confirm", {}); d = json.loads(b)
        self.assertEqual((c, d["status"]), (200, "delivered")); self.assertIn("11 of 11 checks passed", d["delivery"]["report"])
        self.assertEqual(d["stage_states"]["formalization"], "passed")
        self.assertEqual(self.call(f"/api/sessions/{s['id']}/confirm", {})[0], 400)      # already finished
    def test_rejecting_the_account_mapping_blocks(self):
        from bp import accounts
        c, b = self.call("/api/sessions", {"objective": "x", "method": "management_accounts", "currency": "USD", "inputs": {"spec": accounts.EXAMPLE_SPEC}})
        s = json.loads(b); self.call(f"/api/sessions/{s['id']}/confirm", {})
        c, b = self.call(f"/api/sessions/{s['id']}/reject", {}); d = json.loads(b)
        self.assertEqual(d["delivery"]["status"], "blocked"); self.assertIn("account mapping", d["delivery"]["blocked_reason"])
if __name__ == "__main__": unittest.main()
