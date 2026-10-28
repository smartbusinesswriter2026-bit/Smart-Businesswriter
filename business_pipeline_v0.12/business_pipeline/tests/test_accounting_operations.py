"""Accounting and Operations shelf: the standard-cost, inventory, queue and
capacity methods, and the page wiring (B-110)."""

import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, "src")
from bp import server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.product import subjects

YES = lambda spec: True

SCV = {"actual_units": "4800", "standard_material_per_unit": "2", "standard_material_price": "15",
       "actual_material_quantity": "9800", "actual_material_price": "15.5",
       "standard_hours_per_unit": "1.5", "standard_labour_rate": "40",
       "actual_hours": "7300", "actual_labour_rate": "41",
       "standard_variable_overhead_rate": "10", "actual_variable_overhead": "70000",
       "budgeted_fixed_overhead": "240000", "actual_fixed_overhead": "245000", "denominator_hours": "8000"}
INVENTORY = {"annual_demand": "12000", "order_cost": "500", "holding_cost_per_unit": "30",
             "lead_time_days": "10", "service_level": "0.95", "daily_demand_sd": "20"}
QUEUE = {"arrival_rate": "18", "service_rate": "24"}
CAPACITY = {"resources": [{"name": "cutting", "available_hours": "8", "minutes_per_unit": "5"},
                          {"name": "assembly", "available_hours": "8", "minutes_per_unit": "8"},
                          {"name": "packing", "available_hours": "8", "minutes_per_unit": "3"}],
            "demand": "50"}

NEW = ("standard_cost_variances", "inventory_policy", "queue_analysis", "capacity_analysis")
PRESETS = ("scv", "inventory", "queue", "capacity")


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


class StandardCostVariances(unittest.TestCase):
    def m(self):
        return LIBRARY["standard_cost_variances"]

    def test_arithmetic(self):
        out = self.m().impl(SCV)
        self.assertEqual(out["material_price_variance"], D(4900))
        self.assertEqual(out["material_usage_variance"], D(3000))
        self.assertEqual(out["labour_rate_variance"], D(7300))
        self.assertEqual(out["labour_efficiency_variance"], D(4000))
        self.assertEqual(out["variable_overhead_spending_variance"], D(-3000))
        self.assertEqual(out["variable_overhead_efficiency_variance"], D(1000))
        self.assertEqual(out["fixed_overhead_spending_variance"], D(5000))
        self.assertEqual(out["fixed_overhead_volume_variance"], D(24000))
        self.assertEqual(out["total_variance"], D(46200))

    def test_material_and_labour_only_when_overhead_is_omitted(self):
        out = self.m().impl({k: SCV[k] for k in ("actual_units", "standard_material_per_unit", "standard_material_price",
                                                  "actual_material_quantity", "actual_material_price",
                                                  "standard_hours_per_unit", "standard_labour_rate",
                                                  "actual_hours", "actual_labour_rate")})
        self.assertNotIn("fixed_overhead_volume_variance", out)
        self.assertEqual(out["total_variance"], D(4900 + 3000 + 7300 + 4000))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("standard_cost_variances", SCV))
        for inputs in ({**SCV, "actual_units": "0"},
                       {**SCV, "standard_material_price": "-1"},
                       {k: v for k, v in SCV.items() if k != "actual_variable_overhead"},
                       {**SCV, "denominator_hours": "0"}):
            self.assertTrue(blocked("standard_cost_variances", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Variances", "method": "standard_cost_variances", "currency": "PHP",
                       "period": "annual", "inputs": SCV})
        self.assertIn("total variance", d.report.lower())
        self.assertIn("unfavourable", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class InventoryPolicy(unittest.TestCase):
    def m(self):
        return LIBRARY["inventory_policy"]

    def test_arithmetic(self):
        out = self.m().impl(INVENTORY)
        self.assertAlmostEqual(float(out["economic_order_quantity"]), 632.455532, places=5)
        self.assertAlmostEqual(float(out["orders_per_year"]), 18.973666, places=5)
        self.assertAlmostEqual(float(out["safety_stock"]), 104.029677, places=5)
        self.assertAlmostEqual(float(out["reorder_point"]), 432.796800, places=5)

    def test_without_variability_the_reorder_point_is_lead_time_demand(self):
        out = self.m().impl({k: INVENTORY[k] for k in ("annual_demand", "order_cost", "holding_cost_per_unit", "lead_time_days")})
        self.assertEqual(out["safety_stock"], D(0))
        self.assertAlmostEqual(float(out["reorder_point"]), 12000 / 365 * 10, places=6)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("inventory_policy", INVENTORY))
        self.assertTrue(checks_pass("inventory_policy", {k: INVENTORY[k] for k in ("annual_demand", "order_cost", "holding_cost_per_unit", "lead_time_days")}))
        for inputs in ({**INVENTORY, "annual_demand": "0"}, {**INVENTORY, "order_cost": "0"},
                       {**INVENTORY, "holding_cost_per_unit": "0"}, {**INVENTORY, "lead_time_days": "0"},
                       {**INVENTORY, "service_level": "1"}, {**INVENTORY, "daily_demand_sd": "20", "service_level": ""}):
            self.assertTrue(blocked("inventory_policy", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Inventory", "method": "inventory_policy", "currency": "PHP",
                       "period": "annual", "inputs": INVENTORY})
        self.assertIn("economic order quantity", d.report.lower())
        self.assertIn("reorder point", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class QueueAnalysis(unittest.TestCase):
    def m(self):
        return LIBRARY["queue_analysis"]

    def test_arithmetic(self):
        out = self.m().impl(QUEUE)
        self.assertEqual(out["utilisation"], D("0.75"))
        self.assertEqual(out["average_in_queue"], D("2.25"))
        self.assertEqual(out["average_in_system"], D(3))
        self.assertEqual(out["average_wait_in_queue"], D("0.125"))
        self.assertEqual(out["probability_empty"], D("0.25"))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("queue_analysis", QUEUE))
        for inputs in ({"arrival_rate": "0", "service_rate": "10"},
                       {"arrival_rate": "10", "service_rate": "10"},
                       {"arrival_rate": "12", "service_rate": "10"}):
            self.assertTrue(blocked("queue_analysis", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Queue", "method": "queue_analysis", "currency": "PHP",
                       "period": "per period", "inputs": QUEUE})
        self.assertIn("utilisation", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class CapacityAnalysis(unittest.TestCase):
    def m(self):
        return LIBRARY["capacity_analysis"]

    def test_arithmetic(self):
        out = self.m().impl(CAPACITY)
        self.assertEqual((out["capacity_1"], out["capacity_2"], out["capacity_3"]), (D(96), D(60), D(160)))
        self.assertEqual(out["max_output"], D(60))
        self.assertEqual(out["bottleneck_index"], D(2))
        self.assertAlmostEqual(float(out["utilisation_2"]), 50 / 60, places=9)
        self.assertEqual(out["capacity_gap"], D(10))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("capacity_analysis", CAPACITY))
        self.assertTrue(checks_pass("capacity_analysis", {"resources": CAPACITY["resources"]}))
        for inputs in ({"resources": []},
                       {"resources": [{"name": "a", "available_hours": "0", "minutes_per_unit": "5"}]},
                       {"resources": [{"name": "a", "available_hours": "8", "minutes_per_unit": "0"}]},
                       {"resources": CAPACITY["resources"], "demand": "-1"}):
            self.assertTrue(blocked("capacity_analysis", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Capacity", "method": "capacity_analysis", "currency": "PHP",
                       "period": "per period", "inputs": CAPACITY})
        self.assertIn("bottleneck", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class Presets(unittest.TestCase):
    def test_every_preset_delivers(self):
        for preset in PRESETS:
            p = server.PRESETS[preset]
            d = delivered({"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                           "currency": p.get("currency"), "period": p.get("period")})
            self.assertTrue(all(ok for _, ok, *_ in d.appendix["tests"]), preset)
            self.assertNotIn("{{ref:", d.report, preset)


class ShelfWiring(unittest.TestCase):
    def test_accounting_page_is_a_course_not_a_list(self):
        page = subjects.detail("accounting")
        keys = {tool["key"] for tool in page["tools"]}
        for key in ("accounts", "tbcheck", "ratios", "scv", "breakeven", "workingcapital", "loan", "trendanalysis"):
            self.assertIn(key, keys)
        order = []
        for tool in page["tools"]:
            self.assertTrue(tool["group"], tool["key"])
            self.assertTrue(tool["period"], tool["key"])
            self.assertTrue(tool["formula"], tool["key"])
            if tool["group"] not in order:
                order.append(tool["group"])
        self.assertEqual(order, ["Bookkeeping and statements", "Cost and variance analysis",
                                 "Working capital and financing", "Tax and reporting"])
        self.assertGreaterEqual(len(page["glossary"]), 15)

    def test_operations_and_supply_chain_carry_the_process_tools(self):
        for sid in ("operations", "supply-chain"):
            page = subjects.detail(sid)
            keys = {tool["key"] for tool in page["tools"]}
            for key in ("inventory", "queue", "capacity"):
                self.assertIn(key, keys, sid)
            for tool in page["tools"]:
                self.assertTrue(tool["group"], (sid, tool["key"]))
                self.assertTrue(tool["period"], (sid, tool["key"]))
                self.assertTrue(tool["formula"], (sid, tool["key"]))
            self.assertGreaterEqual(len(page["glossary"]), 15)

    def test_the_catalogue_states_what_is_partial(self):
        rows = {row["id"]: row["implementation_status"] for row in subjects.detail("operations")["catalogue"]}
        for rid in ("QNT-OPS-01", "QNT-OPS-04", "QNT-OPS-08"):
            self.assertTrue(rows[rid].startswith("partial:"), rid)


if __name__ == "__main__":
    unittest.main()
