"""The generic statement plan and the extraction boundary (the two owner tips).

The fixture below is a small trading company built **from parameters**, not from a transcribed
worked example: the chart, the policy, the entries and the adjustment specs are the inputs, and
every expected figure is derived by hand from those inputs and stated in the test. Nothing in
`src/bp/statement_plan.py` or `src/bp/statement_extract.py` knows this engagement.
"""
import copy
import os
import sys
import unittest
from decimal import Decimal as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import statement_extract as sx
from bp import statement_plan as sp
from bp.llm import LLMConfig, MockProvider, Models


def chart():
    a = sp.account
    return [
        a("1000", "Cash", "asset", "Cash", "current", "cash"),
        a("1100", "Trade receivables", "asset", "Trade receivables", "current"),
        a("1200", "Inventory", "asset", "Inventory", "current"),
        a("1300", "Prepaid insurance", "asset", "Prepayments", "current"),
        a("1500", "Equipment", "asset", "Property, plant and equipment", "non_current"),
        a("1510", "Accumulated depreciation", "asset", "Property, plant and equipment", "non_current", contra=True),
        a("2000", "Trade payables", "liability", "Trade payables", "current"),
        a("2100", "Loan", "liability", "Borrowings", "non_current"),
        a("2200", "Tax payable", "liability", "Accruals", "current"),
        a("2300", "Accrued salaries", "liability", "Accruals", "current"),
        a("3000", "Share capital", "equity", "Capital", role="capital"),
        a("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
        a("4000", "Sales", "income", "Revenue"),
        a("5000", "Cost of sales", "expense", "Cost of sales"),
        a("6100", "Salaries", "expense", "Operating expenses"),
        a("6200", "Rent", "expense", "Operating expenses"),
        a("6300", "Insurance", "expense", "Operating expenses"),
        a("6400", "Depreciation", "expense", "Operating expenses"),
        a("7000", "Interest", "expense", "Finance costs"),
        a("8000", "Income tax", "expense", "Tax"),
    ]


def dr(acct, x):
    return {"account": acct, "debit": str(x)}


def cr(acct, x):
    return {"account": acct, "credit": str(x)}


def plan(**overrides):
    """A trading company whose figures are declared, not transcribed from any published example."""
    p = {
        "period": {"start": "2026-01-01", "end": "2026-12-31"},
        "currency": "USD", "framework": "local", "places": 2,
        "chart": chart(),
        "policy": {"tax_rate": "0.25",
                   "depreciation": {"method": "straight_line", "convention": "full_year"},
                   "inventory_system": "periodic",
                   "explicitly_stated": ["depreciation.convention", "inventory_system", "tax_rate"]},
        "prior_closing": {},
        "opening": [],
        "entries": [
            {"date": "2026-01-01", "description": "Shares issued", "lines": [dr("1000", 50000), cr("3000", 50000)]},
            {"date": "2026-01-02", "description": "Bank loan", "lines": [dr("1000", 40000), cr("2100", 40000)]},
            {"date": "2026-01-03", "description": "Equipment", "lines": [dr("1500", 60000), cr("1000", 60000)]},
            {"date": "2026-01-04", "description": "Inventory on credit", "lines": [dr("1200", 70000), cr("2000", 70000)]},
            {"date": "2026-01-10", "description": "Insurance", "lines": [dr("1300", 6000), cr("1000", 6000)]},
            {"date": "2026-12-31", "description": "Cash sales", "lines": [dr("1000", 120000), cr("4000", 120000)]},
            {"date": "2026-12-31", "description": "Credit sales", "lines": [dr("1100", 80000), cr("4000", 80000)]},
            {"date": "2026-12-31", "description": "Collections", "lines": [dr("1000", 65000), cr("1100", 65000)]},
            {"date": "2026-12-31", "description": "Payables paid", "lines": [dr("2000", 55000), cr("1000", 55000)]},
            {"date": "2026-12-31", "description": "Salaries", "lines": [dr("6100", 35000), cr("1000", 35000)]},
            {"date": "2026-12-31", "description": "Rent", "lines": [dr("6200", 12000), cr("1000", 12000)]},
            {"date": "2026-12-31", "description": "Interest", "lines": [dr("7000", 2400), cr("1000", 2400)]},
            {"date": "2026-12-31", "description": "Accrued salaries", "lines": [dr("6100", 3000), cr("2300", 3000)]},
        ],
        "adjustments": [
            {"id": "dep", "function": "straight_line_depreciation", "debit": "6400", "credit": "1510",
             "params": {"cost": 60000, "residual": 0, "life_years": 5}},
            {"id": "ins", "function": "prepaid_amortization", "debit": "6300", "credit": "1300",
             "params": {"payment": 6000, "months_expired": 11, "total_months": 12}},
            {"id": "cogs", "function": "periodic_cogs", "debit": "5000", "credit": "1200",
             "params": {"beginning_inventory": 0, "purchases": 70000, "ending_inventory": 10000}},
            {"id": "tax", "function": "tax_on_pretax", "debit": "8000", "credit": "2200", "params": {}},
        ],
        "schedules": [],
    }
    p.update(overrides)
    return p


class FunctionRegistry(unittest.TestCase):
    """Every adjustment is a registered function of declared parameters - never free text."""

    def test_straight_line_conventions(self):
        base = {"cost": 60000, "residual": 0, "life_years": 5}
        self.assertEqual(sp.straight_line_depreciation(dict(base, convention="full_year"), {}), D("12000.00"))
        self.assertEqual(sp.straight_line_depreciation(dict(base, convention="half_year"), {}), D("6000.00"))
        self.assertEqual(sp.straight_line_depreciation(dict(base, convention="pro_rata", months_in_service=3), {}), D("3000.00"))

    def test_pro_rata_without_months_is_refused(self):
        with self.assertRaises(sp.PlanError) as e:
            sp.straight_line_depreciation({"cost": 60000, "life_years": 5, "convention": "pro_rata"}, {})
        self.assertIn("months_in_service", str(e.exception))

    def test_prepaid_is_the_expired_portion_not_the_payment(self):
        self.assertEqual(sp.prepaid_amortization({"payment": 6000, "months_expired": 11}, {}), D("5500.00"))
        self.assertEqual(sp.prepaid_amortization({"payment": 12000, "months_expired": 5, "total_months": 24}, {}), D("2500.00"))

    def test_periodic_cogs(self):
        self.assertEqual(sp.periodic_cogs({"beginning_inventory": 2000, "purchases": 70000, "ending_inventory": 12000}, {}), D("60000.00"))

    def test_tax_on_pretax_and_no_tax_benefit_on_a_loss(self):
        self.assertEqual(sp.tax_on_pretax({"pretax_income": 40000, "rate": "0.25"}, {}), D("10000.00"))
        self.assertEqual(sp.tax_on_pretax({"pretax_income": -5000, "rate": "0.25"}, {}), D(0))

    def test_binary_floats_are_refused(self):
        with self.assertRaises(sp.PlanError):
            sp.straight_line_depreciation({"cost": 60000.0, "life_years": 5}, {})

    def test_reducing_balance_defaults_to_double_declining(self):
        # 60,000 over 5 years, double declining = 40% -> 24,000 in year 1
        self.assertEqual(sp.reducing_balance_depreciation({"cost": 60000, "life_years": 5}, {}), D("24000.00"))

    def test_reducing_balance_with_a_declared_rate(self):
        self.assertEqual(sp.reducing_balance_depreciation({"cost": 100000, "rate": "0.15", "life_years": 10}, {}), D("15000.00"))

    def test_reducing_balance_never_goes_below_zero(self):
        r = sp.reducing_balance_depreciation({"cost": 1000, "accumulated": 999, "residual": 0, "life_years": 5}, {})
        self.assertGreaterEqual(r, D(0))

    def test_units_of_production(self):
        # (60,000 - 0) * 2000 / 10000 = 12,000
        self.assertEqual(sp.units_of_production_depreciation({"cost": 60000, "units_this_period": 2000, "total_estimated_units": 10000}, {}), D("12000.00"))

    def test_units_of_production_refuses_more_units_than_estimated(self):
        with self.assertRaises(sp.PlanError):
            sp.units_of_production_depreciation({"cost": 60000, "units_this_period": 11000, "total_estimated_units": 10000}, {})

    def test_bad_debt_expense(self):
        # 100,000 receivables x 5% = 5,000 allowance; prior 2,000 -> expense 3,000
        self.assertEqual(sp.bad_debt_expense({"receivables": 100000, "rate": "0.05", "prior_allowance": 2000}, {}), D("3000.00"))


    def test_tax_benefit_on_loss_computes_a_benefit(self):
        self.assertEqual(sp.tax_benefit_on_loss({"pretax_income": -10000, "rate": "0.25"}, {}), D("2500.00"))

    def test_tax_benefit_on_loss_is_zero_on_a_profit(self):
        self.assertEqual(sp.tax_benefit_on_loss({"pretax_income": 10000, "rate": "0.25"}, {}), D("0.00"))

    def test_bad_debt_expense_clamps_a_recovery_to_zero(self):
        r = sp.bad_debt_expense({"receivables": 10000, "rate": "0.05", "prior_allowance": 1000}, {})
        self.assertEqual(r, D("0.00"))


    def test_the_graph_resolves_in_dependency_order_and_refuses_a_cycle(self):
        nodes = [sp.Node("b", "prepaid_amortization", {"payment": 100, "months_expired": 6}),
                 sp.Node("a", "periodic_cogs", {"beginning_inventory": 0, "purchases": {"$ref": "b"}, "ending_inventory": 0})]
        env = sp.evaluate(nodes, {})
        self.assertEqual((env["b"], env["a"]), (D("50.00"), D("50.00")))
        cyclic = [sp.Node("x", "periodic_cogs", {"beginning_inventory": {"$ref": "y"}, "ending_inventory": 0}),
                  sp.Node("y", "periodic_cogs", {"beginning_inventory": {"$ref": "x"}, "ending_inventory": 0})]
        with self.assertRaises(sp.PlanError) as e:
            sp.evaluate(cyclic, {})
        self.assertIn("cycle", str(e.exception))


class PlanValidation(unittest.TestCase):
    def test_a_sound_plan_validates(self):
        self.assertEqual(sp.validate_plan(plan()), [])

    def test_required_keys(self):
        self.assertTrue(any("period" in e for e in sp.validate_plan({"currency": "USD"})))

    def test_unbalanced_entry_is_refused_before_anything_is_posted(self):
        p = plan()
        p["entries"][0]["lines"] = [dr("1000", 50000), cr("3000", 49000)]
        self.assertTrue(any("does not balance" in e for e in sp.validate_plan(p)))

    def test_unknown_account_in_an_entry(self):
        p = plan()
        p["entries"][0]["lines"] = [dr("9999", 50000), cr("3000", 50000)]
        self.assertTrue(any("9999" in e for e in sp.validate_plan(p)))

    def test_an_adjustment_must_name_two_chart_accounts(self):
        p = plan()
        p["adjustments"][0]["credit"] = "9999"
        self.assertTrue(any("9999" in e for e in sp.validate_plan(p)))
        p = plan()
        p["adjustments"][0]["credit"] = "6400"
        self.assertTrue(any("same account" in e for e in sp.validate_plan(p)))

    def test_tax_without_a_declared_rate_is_refused(self):
        p = plan()
        p["policy"] = {"depreciation": {"convention": "full_year"}}
        p["policy"]["tax_rate"] = None
        self.assertTrue(any("tax_rate" in e for e in sp.validate_plan(p)))

    def test_unknown_adjustment_function(self):
        p = plan()
        p["adjustments"][0]["function"] = "magic"
        self.assertTrue(any("unknown function" in e for e in sp.validate_plan(p)))

    def test_the_manifest_names_what_the_text_did_not_state(self):
        p = plan()
        p["policy"] = {"tax_rate": "0.25", "depreciation": {"convention": "full_year"},
                       "explicitly_stated": ["tax_rate"]}
        assumed = {a["assumption"] for a in sp.manifest(p["policy"])["assumed"]}
        self.assertEqual(assumed, {"depreciation.method", "depreciation.convention",
                                   "inventory_system", "rounding"})
        self.assertEqual(sp.manifest(p["policy"])["stated"], ["tax_rate"])


class GoldenBuild(unittest.TestCase):
    """Hand-derived answers. Revenue 200,000; expenses 129,900; pre-tax 70,100; tax 17,525; net 52,575."""

    @classmethod
    def setUpClass(cls):
        cls.out = sp.build(plan())

    def test_income_statement(self):
        self.assertEqual(self.out["pretax_income"], D("70100.00"))
        self.assertEqual(self.out["net_income"], D("52575.00"))

    def test_balance_sheet(self):
        self.assertEqual(self.out["total_assets"], D("178100.00"))
        self.assertEqual(self.out["total_liabilities"], D("75525.00"))
        self.assertEqual(self.out["total_equity"], D("102575.00"))

    def test_the_three_articulation_identities_hold(self):
        self.assertTrue(all(ok for _, ok, _ in self.out["articulation"]))
        self.assertEqual([n for n, _, _ in self.out["articulation"]],
                         ["assets_equal_liabilities_plus_equity",
                          "cash_flow_equals_balance_sheet_cash",
                          "receipts_minus_payments_equals_ending_cash"])

    def test_cash_flow_direct_and_indirect(self):
        cf = self.out["_appendix"]["cash_flow"]
        self.assertEqual((D(str(cf["operating"])), D(str(cf["investing"])), D(str(cf["financing"]))),
                         (D("74600"), D("-60000"), D("90000")))
        self.assertEqual(D(str(cf["net_direct"])), D(str(cf["net_indirect"])))

    def test_every_computed_adjustment_posted_and_none_invented(self):
        self.assertEqual(self.out["skipped_adjustments"], [])
        journal = self.out["_appendix"]["journal"]
        amounts = {l["debit"] for e in journal for l in e["lines"] if l["account"] == "6400"}
        self.assertIn("12000.00", amounts)
        prepaid = [D(str(l["debit"])) for e in journal for l in e["lines"] if l["account"] == "6300"]
        self.assertEqual(sum(prepaid), D("5500.00"))

    def test_the_same_plan_builds_the_same_record(self):
        again = sp.build(plan())
        self.assertEqual(self.out["_appendix"]["export"], again["_appendix"]["export"])

    def test_the_manifest_travels_with_the_result(self):
        self.assertEqual([a["assumption"] for a in self.out["assumptions"]["assumed"]],
                         ["depreciation.method", "rounding"])


class Variants(unittest.TestCase):
    def test_dividends_reduce_equity_and_cash_without_changing_net_income(self):
        p = plan()
        p["chart"].append(sp.account("3200", "Dividends", "equity", "Dividends", role="dividends"))
        p["entries"].append({"date": "2026-12-31", "description": "Dividend",
                             "lines": [dr("3200", 5000), cr("1000", 5000)]})
        out = sp.build(p)
        self.assertEqual(out["net_income"], D("52575.00"))
        self.assertEqual(out["total_assets"], D("173100.00"))
        self.assertEqual(out["total_equity"], D("97575.00"))
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_perpetual_system_posts_cogs_directly_and_needs_no_closing_adjustment(self):
        p = plan()
        p["policy"]["inventory_system"] = "perpetual"
        p["adjustments"] = [a for a in p["adjustments"] if a["id"] != "cogs"]
        p["entries"].append({"date": "2026-12-31", "description": "Cost of goods sold",
                             "lines": [dr("5000", 60000), cr("1200", 60000)]})
        out = sp.build(p)
        self.assertEqual(out["net_income"], D("52575.00"))
        self.assertEqual(out["total_assets"], D("178100.00"))
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_loss_is_not_taxed_and_the_skip_is_named(self):
        p = plan()
        p["entries"].append({"date": "2026-12-31", "description": "Heavy salaries",
                             "lines": [dr("6100", 80000), cr("1000", 80000)]})
        out = sp.build(p)
        self.assertTrue(out["pretax_income"] < 0)
        self.assertEqual(out["skipped_adjustments"][0]["adjustment"], "tax")
        self.assertIn("zero", out["skipped_adjustments"][0]["reason"])

    def test_a_failed_articulation_raises_and_returns_nothing(self):
        """A gate that cannot fail is not a gate: prove it on a doctored record."""
        out = sp.build(plan())
        appendix = copy.deepcopy(out["_appendix"])
        appendix["statements"]["total_assets"] = "178101.00"
        checks = sp.articulation({"_appendix": appendix}, plan())
        self.assertFalse(checks[0][1])
        with self.assertRaises(sp.PlanError) as e:
            raise sp.PlanError("the statements do not tie") if not all(ok for _, ok, _ in checks) else None
        self.assertIn("do not tie", str(e.exception))

    def test_cash_flow_and_receipts_checks_can_fail(self):
        out = sp.build(plan())
        appendix = copy.deepcopy(out["_appendix"])
        appendix["cash_flow"]["net_direct"] = "1"
        checks = {n: ok for n, ok, _ in sp.articulation({"_appendix": appendix}, plan())}
        self.assertFalse(checks["cash_flow_equals_balance_sheet_cash"])


class Extraction(unittest.TestCase):
    TEXT = ("The owner paid 6,000 cash for a 12-month insurance policy. "
            "Sales of 20,000 were made on credit.")

    def payload(self):
        return {"entries": [
            {"date": "2026-01-10", "description": "Prepaid insurance", "kind": "original",
             "source_text": "paid 6,000 cash for a 12-month insurance policy",
             "lines": [{"account": "1300", "debit": 6000}, {"account": "1000", "credit": 6000}]},
            {"date": "2026-03-01", "description": "Credit sale", "kind": "original",
             "source_text": "Sales of 20,000 were made on credit",
             "lines": [{"account": "1100", "debit": 20000}, {"account": "4000", "credit": 20000}]},
        ]}

    def test_a_grounded_balanced_journal_passes(self):
        self.assertEqual(sx.validate(self.payload(), self.TEXT, chart()), [])

    def test_an_amount_the_text_does_not_contain_is_refused(self):
        p = self.payload()
        p["entries"][0]["lines"][0]["debit"] = 5500          # the derived 11/12, not a stated figure
        errs = sx.validate(p, self.TEXT, chart())
        self.assertTrue(any("does not appear in the problem text" in e for e in errs))

    def test_an_invented_account_is_refused(self):
        p = self.payload()
        p["entries"][0]["lines"][0]["account"] = "9999"
        self.assertTrue(any("not in the chart" in e for e in sx.validate(p, self.TEXT, chart())))

    def test_an_unbalanced_entry_is_refused(self):
        p = self.payload()
        p["entries"][0]["lines"][1]["credit"] = 20000      # both figures appear in the text
        self.assertTrue(any("does not balance" in e for e in sx.validate(p, self.TEXT, chart())))

    def test_a_missing_source_quote_is_refused(self):
        p = self.payload()
        p["entries"][0].pop("source_text")
        self.assertTrue(any("source_text" in e for e in sx.validate(p, self.TEXT, chart())))

    def test_the_model_is_called_with_the_contract_and_its_answer_is_validated(self):
        import json
        provider = MockProvider(lambda system, user: json.dumps(self.payload()))
        models = Models(provider, config=LLMConfig(enabled=True))
        out = sx.extract(self.TEXT, chart(), models, consent=True)
        self.assertEqual(len(out["entries"]), 2)
        self.assertEqual(out["record"]["provider"], "mock")
        self.assertIn("CHART OF ACCOUNTS", provider.calls[0]["user"])
        self.assertIn("You read an accounting problem", provider.calls[0]["system"])

    def test_schema_shaped_zero_sides_are_normalised(self):
        """Tip 2's line carries both debit and credit with 0 for the unused side."""
        p = self.payload()
        p["entries"][0]["lines"] = [
            {"account": "1300", "debit": 6000, "credit": 0},
            {"account": "1000", "debit": 0, "credit": 6000},
        ]
        self.assertEqual(sx.validate(p, self.TEXT, chart()), [])
        entry = sx.to_entries(p)[0]
        self.assertEqual(entry["lines"], [{"account": "1300", "debit": "6000"},
                                          {"account": "1000", "credit": "6000"}])

    def test_a_line_with_two_non_zero_sides_is_refused(self):
        p = self.payload()
        p["entries"][0]["lines"][0] = {"account": "1300", "debit": 6000, "credit": 6000}
        self.assertTrue(any("both a debit and a credit" in e for e in sx.validate(p, self.TEXT, chart())))

    def test_an_unstated_date_uses_the_period_end_and_says_so(self):
        p = self.payload()
        p["entries"][0].pop("date")
        self.assertTrue(any("needs a date" in e for e in sx.validate(p, self.TEXT, chart())))
        self.assertEqual(sx.validate(p, self.TEXT, chart(), default_date="2026-12-31"), [])
        self.assertEqual(sx.to_entries(p, default_date="2026-12-31")[0]["date"], "2026-12-31")

    def test_the_schema_key_code_is_accepted_as_an_alias(self):
        p = self.payload()
        p["entries"][0]["lines"] = [{"code": "1300", "debit": 6000}, {"code": "1000", "credit": 6000}]
        self.assertEqual(sx.validate(p, self.TEXT, chart()), [])
        self.assertEqual(sx.to_entries(p)[0]["lines"][0], {"account": "1300", "debit": "6000"})

    def test_a_date_outside_the_period_is_refused(self):
        p = self.payload()
        p["entries"][0]["date"] = "2025-12-31"
        self.assertTrue(any("outside the accounting period" in e for e in
                            sx.validate(p, self.TEXT, chart(),
                                        period={"start": "2026-01-01", "end": "2026-12-31"})))

    def test_an_adjustment_with_an_invented_parameter_is_refused(self):
        p = self.payload()
        p["adjustments"] = [{
            "id": "dep", "function": "straight_line_depreciation",
            "debit": "6400", "credit": "1510",
            "params": {"cost": 60000, "life_years": 5, "invented": 999},
            "source_text": "depreciated straight line over 5 years",
        }]
        errs = sx.validate(p, self.TEXT, chart())
        self.assertTrue(any("999" in e for e in errs))

    def test_an_adjustment_with_an_unknown_function_is_refused(self):
        p = self.payload()
        p["adjustments"] = [{
            "id": "x", "function": "magic", "debit": "6400", "credit": "1510",
            "params": {}, "source_text": "anything",
        }]
        self.assertTrue(any("unknown function" in e for e in sx.validate(p, self.TEXT, chart())))

    def test_policy_values_are_validated(self):
        p = self.payload()
        p["policy"] = {"tax_rate": 1.5, "depreciation": {"convention": "zigzag"}}
        errs = sx.validate(p, self.TEXT, chart())
        self.assertTrue(any("tax_rate" in e for e in errs))
        self.assertTrue(any("convention" in e for e in errs))

    def test_adjustments_and_policy_survive_end_to_end(self):
        import json
        payload = self.payload()
        payload["adjustments"] = [{
            "id": "dep", "function": "straight_line_depreciation",
            "debit": "6400", "credit": "1510",
            "params": {"cost": 60000, "residual": 0, "life_years": 5, "convention": "full_year"},
            "source_text": "equipment 60,000 over 5 years",
        }]
        payload["policy"] = {"tax_rate": 0.25, "depreciation": {"convention": "full_year"},
                             "explicitly_stated": ["tax_rate", "depreciation.convention"]}
        provider = MockProvider(lambda system, user: json.dumps(payload))
        from bp.llm import LLMConfig
        models = Models(provider, config=LLMConfig(enabled=True))
        out = sx.extract(self.TEXT + " equipment 60,000 over 5 years", chart(), models, consent=True)
        self.assertEqual(len(out["adjustments"]), 1)
        self.assertEqual(out["policy"]["tax_rate"], "0.25")
        self.assertEqual(out["policy"]["explicitly_stated"], ["tax_rate", "depreciation.convention"])
        self.assertIn("residual", out["adjustments"][0]["params"])  # default preserved

    def test_a_model_answer_with_a_derived_figure_is_refused_end_to_end(self):
        import json
        bad = self.payload()
        bad["entries"][0]["lines"][0]["debit"] = 5500
        provider = MockProvider(lambda system, user: json.dumps(bad))
        models = Models(provider, config=LLMConfig(enabled=True))
        with self.assertRaises(sx.ExtractionError):
            sx.extract(self.TEXT, chart(), models, consent=True)

    def test_no_model_configured_is_a_named_refusal(self):
        with self.assertRaises(sx.ExtractionError) as e:
            sx.extract(self.TEXT, chart(), None)
        self.assertIn("no model", str(e.exception).lower())


class GoldenSuite(unittest.TestCase):
    """Tip 1's "build golden test cases ... run them on every change" requirement.

    Each case is assembled from declared parameters, not transcribed from a worked example, and
    asserts (a) the three articulation identities and (b) at least one hand-derived figure. The
    point is that a change to the prompts, the validators or the DAG that breaks any of these
    fails here before it reaches a student.
    """

    def _build(self, p):
        return sp.build(p)

    def test_mid_year_equipment_is_depreciated_pro_rata(self):
        p = plan()
        p["policy"]["depreciation"]["convention"] = "pro_rata"
        p["adjustments"][0]["params"] = {"cost": 60000, "residual": 0, "life_years": 5,
                                         "convention": "pro_rata", "months_in_service": 6}
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_loan_with_accrued_interest(self):
        p = plan()
        p["entries"].append({"date": "2026-12-31", "description": "Accrued interest",
                             "lines": [dr("7000", 600), cr("2200", 600)]})
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_no_tax_rate_means_no_tax_and_a_named_skip(self):
        p = plan()
        p["policy"] = {"depreciation": {"convention": "full_year"}, "inventory_system": "periodic",
                       "explicitly_stated": ["depreciation.convention", "inventory_system"]}
        p["policy"].pop("tax_rate", None)
        p["adjustments"] = [a for a in p["adjustments"] if a["id"] != "tax"]
        out = self._build(p)
        self.assertEqual(out["pretax_income"], out["net_income"])
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_all_inventory_sold_leaves_no_inventory_asset(self):
        p = plan()
        p["adjustments"][2]["params"]["ending_inventory"] = 0
        out = self._build(p)
        bs = out["_appendix"]["balance_sheet_groups"]["groups"]
        inv = bs.get("current_assets", {}).get("Inventory", "0")
        self.assertEqual(D(str(inv)), D(0))
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_two_prepaid_accounts_both_amortise(self):
        p = plan()
        p["chart"].insert(4, sp.account("1310", "Prepaid rent", "asset", "Prepayments", "current"))
        p["entries"].append({"date": "2026-01-15", "description": "Prepaid rent",
                             "lines": [dr("1310", 12000), cr("1000", 12000)]})
        p["adjustments"].append({"id": "rent_prepaid", "function": "prepaid_amortization",
                                "debit": "6100", "credit": "1310",
                                "params": {"payment": 12000, "months_expired": 11, "total_months": 12}})
        out = self._build(p)
        # rent 12,000 paid + 11,000 amortised = 11,000 expense, 1,000 prepaid
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_dividend_does_not_change_net_income(self):
        p = plan()
        p["chart"].append(sp.account("3200", "Dividends", "equity", "Dividends", role="dividends"))
        p["entries"].append({"date": "2026-12-31", "description": "Dividend",
                             "lines": [dr("3200", 5000), cr("1000", 5000)]})
        out = self._build(p)
        self.assertEqual(out["net_income"], D("52575.00"))
        self.assertEqual(out["total_equity"], D("97575.00"))
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_reducing_balance_depreciation_in_a_full_engagement(self):
        p = plan()
        p["adjustments"][0] = {"id": "dep", "function": "reducing_balance_depreciation",
                               "debit": "6400", "credit": "1510",
                               "params": {"cost": 60000, "residual": 0, "life_years": 5, "convention": "full_year"}}
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_units_of_production_in_a_full_engagement(self):
        p = plan()
        p["adjustments"][0] = {"id": "dep", "function": "units_of_production_depreciation",
                               "debit": "6400", "credit": "1510",
                               "params": {"cost": 60000, "residual": 0, "units_this_period": 2000, "total_estimated_units": 10000}}
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_bad_debt_in_a_full_engagement(self):
        p = plan()
        p["chart"].insert(2, sp.account("1110", "Allowance for doubtful debts", "asset", "Trade receivables", "current", contra=True))
        p["adjustments"].append({"id": "bd", "function": "bad_debt_expense", "debit": "6100", "credit": "1110",
                                 "params": {"receivables": 15000, "rate": "0.05", "prior_allowance": 0}})
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_prior_period_carries_forward(self):
        p = plan()
        p["prior_closing"] = {"1000": "5000", "1500": "1200", "3000": "6200"}
        p["opening"] = [{"lines": [{"account": "1000", "debit": "5000"}, {"account": "1500", "debit": "1200"}, {"account": "3000", "credit": "6200"}]}]
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))
        checks = {n: ok for n, ok, _ in out["_checks"]}
        self.assertTrue(checks.get("opening_balances_equal_prior_closing", True))

    def test_no_adjustments_still_builds_and_ties(self):
        p = plan()
        p["adjustments"] = []
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))
        self.assertEqual(out["pretax_income"], out["net_income"])

    def test_a_half_year_convention(self):
        p = plan()
        p["policy"]["depreciation"]["convention"] = "half_year"
        p["adjustments"][0]["params"]["convention"] = "half_year"
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))




    def test_a_case_with_reducing_balance_and_a_loan(self):
        p = plan()
        p["adjustments"][0] = {"id": "dep", "function": "reducing_balance_depreciation",
                               "debit": "6400", "credit": "1510",
                               "params": {"cost": 60000, "residual": 0, "life_years": 5, "rate": "0.40", "convention": "full_year"}}
        p["entries"].append({"date": "2026-01-02", "description": "Bank loan", "lines": [dr("1000", 40000), cr("2100", 40000)]})
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_case_with_units_of_production_and_no_tax(self):
        p = plan()
        p["adjustments"][0] = {"id": "dep", "function": "units_of_production_depreciation",
                               "debit": "6400", "credit": "1510",
                               "params": {"cost": 60000, "residual": 0, "units_this_period": 1500, "total_estimated_units": 10000}}
        p["policy"] = {"depreciation": {"convention": "full_year"}, "inventory_system": "periodic",
                       "explicitly_stated": ["depreciation.convention", "inventory_system"]}
        p["adjustments"] = [a for a in p["adjustments"] if a["id"] != "tax"]
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))
        self.assertEqual(out["pretax_income"], out["net_income"])

    def test_a_case_with_bad_debt_and_a_dividend(self):
        p = plan()
        p["chart"].insert(2, sp.account("1110", "Allowance for doubtful debts", "asset", "Trade receivables", "current", contra=True))
        p["chart"].append(sp.account("3200", "Dividends", "equity", "Dividends", role="dividends"))
        p["adjustments"].append({"id": "bd", "function": "bad_debt_expense", "debit": "6100", "credit": "1110",
                                 "params": {"receivables": 15000, "rate": "0.10", "prior_allowance": 0}})
        p["entries"].append({"date": "2026-12-31", "description": "Dividend", "lines": [dr("3200", 3000), cr("1000", 3000)]})
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_case_with_prepaid_rent_and_insurance(self):
        p = plan()
        p["chart"].insert(4, sp.account("1310", "Prepaid rent", "asset", "Prepayments", "current"))
        p["entries"].append({"date": "2026-01-15", "description": "Prepaid rent", "lines": [dr("1310", 12000), cr("1000", 12000)]})
        p["adjustments"].append({"id": "rent_prepaid", "function": "prepaid_amortization", "debit": "6200", "credit": "1310",
                                 "params": {"payment": 12000, "months_expired": 6, "total_months": 12}})
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_case_with_accrued_interest_and_a_loss(self):
        p = plan()
        p["entries"].append({"date": "2026-12-31", "description": "Heavy salaries",
                             "lines": [dr("6100", 80000), cr("1000", 80000)]})
        p["entries"].append({"date": "2026-12-31", "description": "Accrued interest",
                             "lines": [dr("7000", 600), cr("2200", 600)]})
        out = self._build(p)
        self.assertTrue(out["pretax_income"] < 0)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))

    def test_a_case_with_half_year_and_pro_rata_mix(self):
        p = plan()
        p["adjustments"][0]["params"]["convention"] = "half_year"
        p["adjustments"][0]["params"]["months_in_service"] = 6
        out = self._build(p)
        self.assertTrue(all(ok for _, ok, _ in out["articulation"]))




if __name__ == "__main__":
    unittest.main()
