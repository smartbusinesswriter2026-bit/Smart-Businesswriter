"""Line balancing and declared-rate tax (B-119)."""

import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, "src")
from bp import server
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.product import subjects

YES = lambda spec: True

BALANCE = {"cycle_time": "10", "rule": "longest_time", "tasks": [
    {"id": "A", "time": "5", "predecessors": ""},
    {"id": "B", "time": "3", "predecessors": "A"},
    {"id": "C", "time": "4", "predecessors": "A"},
    {"id": "D", "time": "2", "predecessors": "B"},
    {"id": "E", "time": "3", "predecessors": "C"},
    {"id": "F", "time": "4", "predecessors": "D,E"}]}
TAX = {"taxable_income": "1000000", "income_tax_rate": "0.25",
       "vat_output_tax": "144000", "vat_input_tax": "84000",
       "temporary_difference": "100000", "deferred_tax_rate": "0.25"}


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


class LineBalancing(unittest.TestCase):
    def m(self):
        return LIBRARY["line_balancing"]

    def test_arithmetic(self):
        out = self.m().impl(BALANCE)
        self.assertEqual(out["total_time"], D(21))
        self.assertEqual(out["lower_bound_stations"], D(3))
        self.assertEqual(out["stations"], D(3))
        self.assertEqual([out["load_1"], out["load_2"], out["load_3"]], [D(9), D(8), D(4)])
        self.assertEqual(out["idle_time"], D(9))
        self.assertEqual(out["efficiency"], D("0.7"))
        self.assertEqual((out["station_A"], out["station_C"], out["station_F"]), (D(1), D(1), D(3)))

    def test_ranked_positional_weight_also_balances(self):
        out = self.m().impl({**BALANCE, "rule": "ranked_positional"})
        self.assertEqual(out["stations"], D(3))
        self.assertTrue(all(out["load_%d" % i] <= D(10) for i in range(1, int(out["stations"]) + 1)))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("line_balancing", BALANCE))
        for inputs in ({**BALANCE, "cycle_time": "0"},
                       {**BALANCE, "tasks": [{"id": "A", "time": "11", "predecessors": ""}]},
                       {**BALANCE, "tasks": [{"id": "A", "time": "1", "predecessors": "Z"}]},
                       {**BALANCE, "rule": "other"},
                       {"cycle_time": "10", "tasks": [{"id": "A", "time": "1", "predecessors": "B"},
                                                      {"id": "B", "time": "1", "predecessors": "A"}]}):
            self.assertTrue(blocked("line_balancing", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Balance", "method": "line_balancing", "currency": "PHP", "period": "per period", "inputs": BALANCE})
        self.assertIn("stations", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class TaxDeclared(unittest.TestCase):
    def m(self):
        return LIBRARY["tax_declared"]

    def test_arithmetic(self):
        out = self.m().impl(TAX)
        self.assertEqual((out["income_tax"], out["vat_payable"], out["deferred_tax"]), (D(250000), D(60000), D(25000)))
        self.assertEqual(out["total_tax_charge"], D(275000))
        self.assertEqual(out["net_income_after_tax"], D(750000))

    def test_a_loss_carries_no_positive_income_tax(self):
        out = self.m().impl({"taxable_income": "-50000", "income_tax_rate": "0.25"})
        self.assertEqual(out["income_tax"], D(0))
        self.assertEqual(out["net_income_after_tax"], D(-50000))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("tax_declared", TAX))
        self.assertTrue(checks_pass("tax_declared", {"taxable_income": "-50000", "income_tax_rate": "0.25"}))
        for inputs in ({"taxable_income": "1", "income_tax_rate": "1.2"},
                       {**TAX, "vat_input_tax": ""},
                       {**TAX, "deferred_tax_rate": ""},
                       {"taxable_income": "1", "income_tax_rate": "0.25", "temporary_difference": "100"}):
            self.assertTrue(blocked("tax_declared", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Tax", "method": "tax_declared", "currency": "PHP", "period": "annual", "inputs": TAX})
        self.assertIn("total tax charge", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class Presets(unittest.TestCase):
    def test_presets_deliver(self):
        for preset in ("linebalance", "tax"):
            p = server.PRESETS[preset]
            d = delivered({"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                           "currency": p.get("currency"), "period": p.get("period")})
            self.assertTrue(all(ok for _, ok, *_ in d.appendix["tests"]), preset)
            self.assertNotIn("{{ref:", d.report, preset)


class Wiring(unittest.TestCase):
    def test_shelves_carry_the_new_tools(self):
        accounting = subjects.detail("accounting")
        operations = subjects.detail("operations")
        entrepreneurship = subjects.detail("entrepreneurship")
        self.assertIn("tax", {t["key"] for t in accounting["tools"]})
        self.assertIn("linebalance", {t["key"] for t in operations["tools"]})
        self.assertIn("tax", {t["key"] for t in entrepreneurship["tools"]})
        groups = list(dict.fromkeys(t["group"] for t in accounting["tools"]))
        self.assertIn("Tax and reporting", groups)
        for page in (accounting, operations, entrepreneurship):
            for tool in page["tools"]:
                self.assertTrue(tool["formula"], tool["key"])
                self.assertTrue(tool["group"], tool["key"])
                self.assertTrue(tool["period"], tool["key"])

    def test_glossaries_explain_the_new_terms(self):
        accounting = {row["term"] for row in subjects.detail("accounting")["glossary"]}
        operations = {row["term"] for row in subjects.detail("operations")["glossary"]}
        self.assertTrue({"Taxable income", "VAT", "Deferred tax"} <= accounting)
        self.assertIn("Line balancing", operations)


if __name__ == "__main__":
    unittest.main()
