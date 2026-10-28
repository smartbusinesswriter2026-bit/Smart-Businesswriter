import sys, os, json, socket, subprocess, tempfile, threading, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods, server, envpin
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.reperform import reperform
from bp.sandbox import SubprocessSandbox, SandboxError
from bp.session import SessionManager

yes = lambda s: True
SB = SubprocessSandbox(timeout=60)
NPV = {"objective": "Invest?", "method": "npv", "currency": "USD", "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}, "sensitivity": {"rate": ["0.05", "0.25"]}}
CASES = {"npv": NPV["inputs"], "irr": {"cashflows": ["-1000", "400", "400", "400", "400"]},
         "discounted_payback": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10"},
         "breakeven": {"fixed": "1000", "price": "20", "variable": "10"},
         "descriptive_stats": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"]},
         "pearson": {"x": [str(i) for i in range(1, 9)], "y": ["52", "55", "61", "58", "70", "72", "69", "80"]},
         "spearman": {"x": ["3", "1", "4", "1", "5", "9", "2", "6", "5", "3"], "y": ["2", "7", "1", "8", "2", "8", "1", "8", "2", "8"]},
         "ols": {"y": ["52", "55", "61", "58", "70", "72", "69", "80", "66", "74"], "predictors": {"study_hours": ["1", "2", "3", "4", "5", "6", "7", "8", "4", "6"], "sleep_hours": ["6", "7", "5", "8", "6", "7", "8", "6", "7", "7"]}},
         "welch_t": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"]}},
         "mann_whitney": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"]}},
         "anova": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"], "online": ["60", "63", "58", "66", "61", "65", "60"]}},
         "kruskal_wallis": {"groups": {"a": ["1", "2", "2", "3", "4", "4"], "b": ["2", "3", "3", "4", "5", "6"], "c": ["5", "6", "6", "7", "8", "8"]}},
         "chi_square": {"table": [[45, 30, 25], [20, 40, 40], [10, 20, 70]]},
         "trend_forecast": {"values": ["10", "12", "11", "14", "13", "16", "15", "18", "17", "20", "19", "22"]},
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
         "standard_cost_variances": {"actual_units": "1000", "standard_material_per_unit": "2", "standard_material_price": "10", "actual_material_quantity": "2100", "actual_material_price": "11", "standard_hours_per_unit": "1", "standard_labour_rate": "20", "actual_hours": "950", "actual_labour_rate": "21"},
         "inventory_policy": {"annual_demand": "5000", "order_cost": "200", "holding_cost_per_unit": "10", "lead_time_days": "7", "service_level": "0.95", "daily_demand_sd": "5"},
         "queue_analysis": {"arrival_rate": "12", "service_rate": "20"},
         "capacity_analysis": {"resources": [{"name": "a", "available_hours": "8", "minutes_per_unit": "5"}, {"name": "b", "available_hours": "8", "minutes_per_unit": "10"}], "demand": "40"},
         "cpm_schedule": {"estimate": "single", "activities": [{"id": "a", "duration": "2", "predecessors": ""}, {"id": "b", "duration": "3", "predecessors": "a"}]},
         "earned_value": {"planned_value": "1000", "earned_value": "900", "actual_cost": "950", "budget_at_completion": "2000"},
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
         "management_accounts": {"spec": {"period": {"start": "2026-01-01", "end": "2026-03-31"}, "currency": "USD", "framework": "local", "places": 2,
                                           "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"}, {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
                                                     {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"}, {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"}],
                                           "prior_closing": {"1000": "1000", "3000": "1000"},
                                           "opening": [{"lines": [{"account": "1000", "debit": "1000"}, {"account": "3000", "credit": "1000"}]}],
                                           "entries": [{"date": "2026-01-15", "description": "sale", "lines": [{"account": "1000", "debit": "500"}, {"account": "4000", "credit": "500"}]}], "schedules": []}}}

class Policy(unittest.TestCase):
    def test_guards_block_escape_routes(self):
        escape = os.path.join(tempfile.gettempdir(), "bp_sandbox_escape.txt")
        if os.path.exists(escape): os.remove(escape)
        probes = SB.selftest()
        for k in ("network_connect", "name_resolution", "write_outside_workdir", "os_system", "subprocess"): self.assertEqual(probes[k], "blocked", k)
        self.assertTrue(probes["write_inside_workdir"].startswith("allowed")); self.assertFalse(os.path.exists(escape))
    def test_child_cannot_reach_a_real_listener(self):
        srv = socket.socket(); srv.bind(("127.0.0.1", 0)); srv.listen(5); srv.settimeout(0.5); hits = []
        def acc():
            try: c, _ = srv.accept(); hits.append(1); c.close()
            except OSError: pass
        t = threading.Thread(target=acc); t.start()
        try: self.assertEqual(SB.selftest(srv.getsockname()[1])["network_connect"], "blocked")
        finally: t.join(); srv.close()
        self.assertEqual(hits, [])
    def test_timeout_kills_runaway_process(self):
        with self.assertRaises(SandboxError) as c: SubprocessSandbox(timeout=1.5).spin()
        self.assertIn("timed out", str(c.exception))
    def test_policy_reported(self):
        _, _, meta = SB.verify_execute("npv", NPV["inputs"]); p = meta["policy"]
        self.assertEqual((p["network"], p["process_spawn"], p["seed"]), ("blocked", "blocked", 0)); self.assertIn(p["memory_limit_mb"], (None, 1024)); self.assertIn("not a security boundary", p["isolation"])

class Parity(unittest.TestCase):
    def test_sandbox_outputs_equal_in_process_for_every_method(self):
        for name, inp in CASES.items():
            m = LIBRARY[name]; results, outputs, meta = SB.verify_execute(name, inp); self.assertTrue(all(ok for _, ok in results), name)
            local = m.impl(inp); local = local if isinstance(local, dict) else {m.metric: local}
            local = {k: v for k, v in local.items() if k not in ("_appendix", "_checks")}
            self.assertEqual({k: str(v) for k, v in outputs.items()}, {k: str(v) for k, v in local.items()}, name)
    def test_deterministic_across_processes(self):
        a = SB.verify_execute("ols", CASES["ols"]); b = SB.verify_execute("ols", CASES["ols"])
        self.assertEqual({k: str(v) for k, v in a[1].items()}, {k: str(v) for k, v in b[1].items()}); self.assertEqual(a[2]["env_hash"], b[2]["env_hash"])
    def test_pipeline_report_identical_with_and_without_sandbox(self):
        r = {"objective": "x", "method": "welch_t", "unit": "points", "inputs": CASES["welch_t"]}
        d1 = Pipeline().run(r, yes); d2 = Pipeline(sandbox=SB).run(r, yes)
        self.assertEqual(d1.report, d2.report); self.assertIsInstance(d2.appendix["sandbox"], dict); self.assertIsInstance(d1.appendix["sandbox"], str)
    def test_fallback_and_blocks_work_through_sandbox(self):
        sk = {"a": ["1", "1", "1", "2", "1", "1", "2", "3", "30"], "b": ["2", "3", "4", "5", "3", "4", "6", "5", "4"]}
        d = Pipeline(sandbox=SB).run({"objective": "x", "method": "welch_t", "unit": "points", "inputs": {"groups": sk}}, yes)
        self.assertEqual(d.status, "delivered"); self.assertEqual(d.appendix["fallback_used"]["to"], "mann_whitney"); self.assertIn("Hodges-Lehmann", d.report)
        c = Pipeline(sandbox=SB).run({"objective": "x", "method": "ols", "inputs": {"y": ["3", "5", "4", "7", "8", "6", "9", "11", "10", "12", "14", "13"], "predictors": {"a": [str(i) for i in range(1, 13)], "b": [str(i + (0.01 if i % 2 else -0.01)) for i in range(1, 13)]}}}, yes)
        self.assertEqual(c.status, "blocked"); self.assertIn("multicollinearity_screen", c.blocked_reason)
        e = Pipeline(sandbox=SB).run({"objective": "x", "method": "pearson", "inputs": {"x": ["1", "2", "3", "4"], "y": ["2", "4", "6", "8"]}}, yes)
        self.assertEqual(e.status, "blocked"); self.assertIn("perfect correlation", e.blocked_reason)

class FailClosed(unittest.TestCase):
    def test_unavailable_sandbox_blocks(self):
        d = Pipeline(sandbox=SubprocessSandbox(python=os.path.join(tempfile.gettempdir(), "no_such_python"))).run(NPV, yes)
        self.assertEqual(d.status, "blocked"); self.assertIn("sandbox", d.blocked_reason)
    def test_timeout_blocks_not_hangs(self):
        d = Pipeline(sandbox=SubprocessSandbox(timeout=0.01)).run(NPV, yes); self.assertEqual(d.status, "blocked"); self.assertIn("timed out", d.blocked_reason)
    def test_builder_not_allowed_with_sandbox(self):
        with self.assertRaises(ValueError): Pipeline(sandbox=SB).run(NPV, yes, builder=lambda impl, failed: impl)

class Reperform(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.d = Pipeline(sandbox=SB).run(NPV, yes); cls.b = cls.d.appendix["reperform"]
    def test_untouched_bundle_verifies_exactly(self):
        r = reperform(self.b, SB); self.assertTrue(r["verified"]); self.assertTrue(r["all_exact"]); self.assertTrue(r["environment_match"])
    def test_tampered_output_is_detected(self):
        t = json.loads(json.dumps(self.b)); t["outputs"]["npv"] = "123.45"; r = reperform(t, SB); self.assertFalse(r["verified"]); self.assertTrue(any("npv" in x for x in r["differences"]))
    def test_tampered_input_is_detected(self):
        t = json.loads(json.dumps(self.b)); t["inputs"]["cashflows"][1] = "401"; self.assertFalse(reperform(t, SB)["verified"])
    def test_environment_difference_is_reported_not_hidden(self):
        t = json.loads(json.dumps(self.b)); t["env_hash"] = "x"; t["fingerprint"]["python"] = "0.0.0"; r = reperform(t, SB)
        self.assertTrue(r["verified"]); self.assertFalse(r["environment_match"]); self.assertIn("python", r["environment_differences"])
    def test_unknown_method_fails_closed(self):
        t = json.loads(json.dumps(self.b)); t["method"]["id"] = "nope"; self.assertFalse(reperform(t, SB)["verified"])
    def test_command_line_tool(self):
        with tempfile.TemporaryDirectory() as td:
            f = os.path.join(td, "b.json"); json.dump(self.d.appendix["reperform"], open(f, "w"), default=str)
            env = {**os.environ, "PYTHONPATH": "src"}
            ok = subprocess.run([sys.executable, "-m", "bp.reperform", f], env=env, capture_output=True, text=True); self.assertEqual(ok.returncode, 0, ok.stderr)
            bad = json.load(open(f)); bad["outputs"]["npv"] = "1"; json.dump(bad, open(f, "w"))
            self.assertEqual(subprocess.run([sys.executable, "-m", "bp.reperform", f], env=env, capture_output=True, text=True).returncode, 1)
    def test_fingerprint_pins_source_and_has_no_third_party(self):
        fp = envpin.fingerprint(); self.assertEqual(fp["third_party_packages"], []); self.assertEqual(len(fp["bp_source"]), 64); self.assertEqual(envpin.env_hash(fp), envpin.env_hash())

class ServerWithSandbox(unittest.TestCase):
    def test_full_flow_over_http(self):
        from http.server import ThreadingHTTPServer; import urllib.request as u
        old = server.M; server.M = SessionManager(SB); srv = ThreadingHTTPServer(("127.0.0.1", 0), server.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            call = lambda path, b=None: json.load(u.urlopen(u.Request(f"http://127.0.0.1:{srv.server_address[1]}{path}", data=None if b is None else json.dumps(b).encode(), headers={"Content-Type": "application/json"})))
            s = call("/api/sessions", server.PRESETS["pearson"]); d = call(f"/api/sessions/{s['id']}/confirm", {})
            self.assertEqual(d["status"], "delivered"); self.assertEqual(d["delivery"]["appendix"]["sandbox"]["network"], "blocked"); self.assertIn("reperform", d["delivery"]["appendix"])
        finally: srv.shutdown(); server.M = old
if __name__ == "__main__": unittest.main()
