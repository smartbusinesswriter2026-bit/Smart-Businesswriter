"""The simplified feasibility record: roll-up, the frozen break-even, and the tables."""

import unittest
from decimal import Decimal

from bp import methods
from bp.product import feasibility_plan


def record():
    return feasibility_plan.normalise({
        "project": {"name": "Riverside Kitchen", "description": "Open a kitchen.",
                    "location": "Riverside", "proponents": "Alex Rivera", "currency": "USD"},
        "market": {"target_market": "local households", "demand": 12000, "price": 8},
        "costs": [{"item": "Fit-out", "amount": 30000}, {"item": "Equipment", "amount": 18000}],
        "operating": {"fixed": 24000, "variable": 3},
        "declared": {"risks": ["Permit delay"]},
    })


def core(name, inputs):
    return methods.LIBRARY[name].impl(inputs)


class RollupTest(unittest.TestCase):

    def test_the_investment_is_the_declared_items_summed(self):
        rolled = feasibility_plan.rollup(record())
        self.assertEqual(rolled["total"], 48000)
        self.assertEqual(rolled["fixed"], 24000)
        self.assertEqual(rolled["variable"], 3)

    def test_the_variable_cost_must_be_below_the_price(self):
        data = record()
        data["operating"]["variable"] = 9
        problems = feasibility_plan.validate(data)
        self.assertTrue(any("below the price" in problem for problem in problems), problems)

    def test_a_missing_core_is_a_refusal_not_a_crash(self):
        out = feasibility_plan.run(record(), None)
        self.assertFalse(out["ok"])
        self.assertIn("not attached", out["error"])


class ScheduleTest(unittest.TestCase):

    def test_the_frozen_break_even_supplies_every_return(self):
        out = feasibility_plan.run(record(), core)
        self.assertTrue(out["ok"])
        result = out["result"]
        self.assertEqual(Decimal(str(result["breakeven_units"])), Decimal("4800"))
        self.assertEqual(Decimal(str(result["breakeven_revenue"])), Decimal("38400"))
        self.assertEqual(Decimal(str(result["expected_revenue"])), Decimal("96000"))
        self.assertEqual(Decimal(str(result["margin_of_safety_units"])), Decimal("7200"))

    def test_the_three_tables_print_the_record_and_the_core(self):
        data = record()
        computed = feasibility_plan.run(data, core)
        market = feasibility_plan.market_rows(data, computed)
        self.assertIn(["Declared demand (units a year)", "12,000.00"], market)
        self.assertIn(["Revenue at the declared demand", "USD 96,000.00"], market)
        costs = feasibility_plan.cost_rows(data)
        self.assertIn(["Total investment", "USD 48,000.00"], costs)
        returns = feasibility_plan.return_rows(data, computed)
        self.assertIn(["Break-even volume", "4,800.00 units"], returns)
        self.assertIn(["Margin of safety ratio", "60.0%"], returns)

    def test_a_refused_run_reports_no_return(self):
        data = record()
        data["operating"]["variable"] = 9

        def refuse(name, inputs):
            raise ValueError("variable cost must be below price")
        out = feasibility_plan.run(data, refuse)
        self.assertFalse(out["ok"])
        self.assertIn("below price", out["error"])


if __name__ == "__main__":
    unittest.main()
