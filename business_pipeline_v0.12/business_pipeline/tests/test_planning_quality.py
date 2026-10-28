"""Scheduling, project control, quality, costing and sales-variance methods (B-116)."""

import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, "src")
from bp import server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.product import subjects

YES = lambda spec: True

CPM = {"estimate": "single", "activities": [
    {"id": "A", "duration": "3", "predecessors": ""},
    {"id": "B", "duration": "4", "predecessors": "A"},
    {"id": "C", "duration": "2", "predecessors": "A"},
    {"id": "D", "duration": "5", "predecessors": "B,C"}]}
PERT = {"estimate": "three_point", "activities": [
    {"id": "A", "optimistic": "2", "most_likely": "3", "pessimistic": "4", "predecessors": ""},
    {"id": "B", "optimistic": "3", "most_likely": "4", "pessimistic": "5", "predecessors": "A"}]}
EVM = {"planned_value": "100000", "earned_value": "90000", "actual_cost": "95000", "budget_at_completion": "200000"}
OEE = {"planned_production_time": "480", "downtime": "40", "ideal_cycle_time": "0.5", "total_units": "760", "good_units": "740"}
SPC = {"values": ["10", "11", "9", "10", "12", "9", "10", "11"], "spec_lower": "7", "spec_upper": "13"}
ABC = {"activities": [{"name": "setup", "pool_cost": "50000"}, {"name": "inspection", "pool_cost": "30000"}],
       "products": [{"name": "X", "units": "1000"}, {"name": "Y", "units": "500"}],
       "allocations": [{"activity": "setup", "product": "X", "driver_quantity": "40"},
                       {"activity": "setup", "product": "Y", "driver_quantity": "60"},
                       {"activity": "inspection", "product": "X", "driver_quantity": "20"},
                       {"activity": "inspection", "product": "Y", "driver_quantity": "10"}]}
SALES = {"products": [{"name": "X", "budget_units": "100", "budget_price": "10", "actual_units": "120", "actual_price": "11"},
                      {"name": "Y", "budget_units": "100", "budget_price": "20", "actual_units": "80", "actual_price": "18"}]}
QUEUE2 = {"arrival_rate": "18", "service_rate": "12", "servers": "2"}

NEW = ("cpm_schedule", "earned_value", "oee_analysis", "process_control", "abc_costing", "sales_variances")
PRESETS = ("cpm", "evm", "oee", "spc", "abc", "salesvar")


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


class CpmSchedule(unittest.TestCase):
    def m(self):
        return LIBRARY["cpm_schedule"]

    def test_arithmetic(self):
        out = self.m().impl(CPM)
        self.assertEqual(out["project_duration"], D(12))
        self.assertEqual(out["critical_count"], D(3))
        self.assertEqual((out["es_A"], out["ef_A"], out["float_A"], out["critical_A"]), (D(0), D(3), D(0), D(1)))
        self.assertEqual(out["float_C"], D(2))
        self.assertEqual(out["critical_C"], D(0))

    def test_pert_expected_duration_and_variance(self):
        out = self.m().impl(PERT)
        self.assertEqual(out["project_duration"], D(7))
        self.assertAlmostEqual(float(out["pert_variance"]), 2 / 9, places=9)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("cpm_schedule", CPM))
        self.assertTrue(checks_pass("cpm_schedule", PERT))
        for inputs in ({"activities": [{"id": "A", "duration": "1", "predecessors": "B"},
                                       {"id": "B", "duration": "1", "predecessors": "A"}]},
                       {"activities": [{"id": "A", "duration": "1", "predecessors": "Z"}]},
                       {"activities": [{"id": "A", "duration": "-1", "predecessors": ""}]},
                       {"activities": [{"id": "A", "duration": "1"}, {"id": "A", "duration": "2"}]}):
            self.assertTrue(blocked("cpm_schedule", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Schedule", "method": "cpm_schedule", "currency": "PHP", "period": "days", "inputs": CPM})
        self.assertIn("critical path", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class EarnedValue(unittest.TestCase):
    def m(self):
        return LIBRARY["earned_value"]

    def test_arithmetic(self):
        out = self.m().impl(EVM)
        self.assertEqual((out["schedule_variance"], out["cost_variance"]), (D(-10000), D(-5000)))
        self.assertEqual((out["spi"], out["cpi"]), (D("0.9"), D(90000) / D(95000)))
        self.assertAlmostEqual(float(out["estimate_at_completion"]), 200000 / (90000 / 95000), places=6)
        self.assertAlmostEqual(float(out["tcpi"]), 110000 / 105000, places=6)

    def test_budget_rate_eac_is_the_alternative(self):
        out = self.m().impl({**EVM, "eac_method": "budget_rate"})
        self.assertEqual(out["estimate_at_completion"], D(95000) + (D(200000) - D(90000)))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("earned_value", EVM))
        for inputs in ({**EVM, "budget_at_completion": "0"}, {**EVM, "planned_value": "0"},
                       {**EVM, "actual_cost": "0"}, {**EVM, "eac_method": "other"}):
            self.assertTrue(blocked("earned_value", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "EVM", "method": "earned_value", "currency": "PHP", "period": "point in time", "inputs": EVM})
        self.assertIn("estimate at completion", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class OeeAnalysis(unittest.TestCase):
    def m(self):
        return LIBRARY["oee_analysis"]

    def test_arithmetic(self):
        out = self.m().impl(OEE)
        self.assertAlmostEqual(float(out["availability"]), 440 / 480, places=9)
        self.assertAlmostEqual(float(out["performance"]), 380 / 440, places=9)
        self.assertAlmostEqual(float(out["quality"]), 740 / 760, places=9)
        self.assertAlmostEqual(float(out["oee"]), (440 / 480) * (380 / 440) * (740 / 760), places=9)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("oee_analysis", OEE))
        for inputs in ({**OEE, "downtime": "500"}, {**OEE, "good_units": "800"},
                       {**OEE, "ideal_cycle_time": "0"}, {**OEE, "planned_production_time": "0"}):
            self.assertTrue(blocked("oee_analysis", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "OEE", "method": "oee_analysis", "currency": "PHP", "period": "per period", "inputs": OEE})
        self.assertIn("oee", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class ProcessControl(unittest.TestCase):
    def m(self):
        return LIBRARY["process_control"]

    def test_arithmetic(self):
        out = self.m().impl(SPC)
        self.assertEqual(out["mean"], D("10.25"))
        self.assertAlmostEqual(float(out["sigma_estimate"]), (11 / 7) / 1.128, places=9)
        self.assertEqual(out["out_of_control"], D(0))
        self.assertAlmostEqual(float(out["cp"]), 6 / (6 * (11 / 7) / 1.128), places=9)
        self.assertAlmostEqual(float(out["cpk"]), min(2.75, 3.25) / (3 * (11 / 7) / 1.128), places=9)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("process_control", SPC))
        self.assertTrue(checks_pass("process_control", {"values": ["1", "2", "1", "3", "2"]}))
        for inputs in ({"values": ["1", "2", "3"]}, {"values": ["2", "2", "2", "2", "2"]},
                       {"values": ["1", "2", "1", "2", "1"], "spec_lower": "0"},
                       {"values": ["1", "2", "1", "2", "1"], "spec_lower": "5", "spec_upper": "1"}):
            self.assertTrue(blocked("process_control", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "SPC", "method": "process_control", "currency": "PHP", "period": "per observation", "inputs": SPC})
        self.assertIn("control limits", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class AbcCosting(unittest.TestCase):
    def m(self):
        return LIBRARY["abc_costing"]

    def test_arithmetic(self):
        out = self.m().impl(ABC)
        self.assertEqual((out["rate_setup"], out["rate_inspection"]), (D(500), D(1000)))
        self.assertEqual((out["allocated_X"], out["allocated_Y"]), (D(40000), D(40000)))
        self.assertEqual((out["unit_cost_X"], out["unit_cost_Y"]), (D(40), D(80)))
        self.assertEqual(out["total_allocated"], D(80000))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("abc_costing", ABC))
        for inputs in ({**ABC, "activities": [{"name": "setup", "pool_cost": "50000"}]},
                       {**ABC, "allocations": [{"activity": "nope", "product": "X", "driver_quantity": "1"}]},
                       {**ABC, "products": [{"name": "X", "units": "0"}, {"name": "Y", "units": "500"}]}):
            self.assertTrue(blocked("abc_costing", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "ABC", "method": "abc_costing", "currency": "PHP", "period": "annual", "inputs": ABC})
        self.assertIn("allocated", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class SalesVariances(unittest.TestCase):
    def m(self):
        return LIBRARY["sales_variances"]

    def test_arithmetic(self):
        out = self.m().impl(SALES)
        self.assertEqual(out["total_sales_variance"], D(-240))
        self.assertEqual(out["price_variance"], D(-40))
        self.assertEqual(out["mix_variance"], D(-200))
        self.assertEqual(out["yield_variance"], D(0))
        self.assertEqual(out["volume_variance"], D(-200))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("sales_variances", SALES))
        for inputs in ({"products": SALES["products"][:1]},
                       {"products": [{**SALES["products"][0], "budget_units": "-1"}, SALES["products"][1]]}):
            self.assertTrue(blocked("sales_variances", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Sales variances", "method": "sales_variances", "currency": "PHP", "period": "annual", "inputs": SALES})
        self.assertIn("mix variance", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class MultiServerQueue(unittest.TestCase):
    def test_two_servers(self):
        m = LIBRARY["queue_analysis"]
        out = m.impl(QUEUE2)
        self.assertEqual(out["servers"], D(2))
        self.assertEqual(out["utilisation"], D("0.75"))
        self.assertAlmostEqual(float(out["average_in_queue"]), 27 / 14, places=9)
        self.assertAlmostEqual(float(out["probability_waiting"]), 9 / 14, places=9)
        self.assertTrue(checks_pass("queue_analysis", QUEUE2))

    def test_more_servers_shorten_the_queue(self):
        m = LIBRARY["queue_analysis"]
        one = m.impl({**QUEUE2, "servers": "2"})
        two = m.impl({**QUEUE2, "servers": "3"})
        self.assertLess(two["average_in_queue"], one["average_in_queue"])

    def test_refusals(self):
        self.assertTrue(blocked("queue_analysis", {**QUEUE2, "servers": "0"}))
        self.assertTrue(blocked("queue_analysis", {"arrival_rate": "24", "service_rate": "12", "servers": "2"}))


class Presets(unittest.TestCase):
    def test_every_preset_delivers(self):
        for preset in PRESETS:
            p = server.PRESETS[preset]
            d = delivered({"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                           "currency": p.get("currency"), "period": p.get("period")})
            self.assertTrue(all(ok for _, ok, *_ in d.appendix["tests"]), preset)
            self.assertNotIn("{{ref:", d.report, preset)


class ShelfWiring(unittest.TestCase):
    def test_project_shelf_has_schedule_and_control(self):
        page = subjects.detail("project-management")
        keys = {tool["key"] for tool in page["tools"]}
        self.assertTrue({"cpm", "evm"} <= keys)
        groups = list(dict.fromkeys(tool["group"] for tool in page["tools"]))
        self.assertEqual(groups[0], "Schedule and control")

    def test_accounting_and_operations_carry_the_new_tools(self):
        accounting = {t["key"] for t in subjects.detail("accounting")["tools"]}
        operations = {t["key"] for t in subjects.detail("operations")["tools"]}
        self.assertTrue({"abc", "salesvar"} <= accounting)
        self.assertTrue({"oee", "spc"} <= operations)
        for sid in ("accounting", "operations", "project-management"):
            for tool in subjects.detail(sid)["tools"]:
                self.assertTrue(tool["formula"], (sid, tool["key"]))
                self.assertTrue(tool["group"], (sid, tool["key"]))
                self.assertTrue(tool["period"], (sid, tool["key"]))

    def test_catalogue_states_the_new_coverage(self):
        rows = {r["id"]: r["implementation_status"] for r in subjects.detail("operations")["catalogue"]}
        for rid in ("QNT-OPS-05", "QNT-OPS-06"):
            self.assertTrue(rows[rid].startswith("partial:"), rid)


if __name__ == "__main__":
    unittest.main()
