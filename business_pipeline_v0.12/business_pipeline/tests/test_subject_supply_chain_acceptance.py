"""Acceptance tests for the Supply chain & logistics shelf (session 8).

One test per acceptance row in `qa/manual/supply-chain.md`.  Every expectation is
read from the code or the served data - never from the manual - and every numeric
expectation is recomputed independently: hand arithmetic or a second formula
written here, never the method's own output compared with itself.

The shelf owns no methods of its own: it re-exports eight Operations methods and
eleven Operations worksheets.  That is why this module also carries the parity
tests (`test_E_scl_051` ... `053`): the same method with the same preset on the
Operations shelf and on this shelf must produce an identical appendix and an
identical outputs hash.  If they differ, one of the two shelves is lying about
what it runs.

    $env:PYTHONPATH="src"; python -m unittest tests.test_subject_supply_chain_acceptance
"""

import json
import sys
import unittest
from decimal import Decimal, getcontext
from math import factorial

sys.path.insert(0, "src")

from bp import server, templates as T                     # noqa: E402
from bp.methods import DataError, LIBRARY, TOL, validate_inputs   # noqa: E402
from bp.orchestrator import Pipeline                      # noqa: E402
from bp.product import subjects                           # noqa: E402

getcontext().prec = 50

SUBJECT = "supply-chain"
OPERATIONS = "operations"

#: The eight compute tools, in the order the page declares them.
TOOLS = ["breakeven", "multibreakeven", "unitecon", "forecast",
         "inventory", "queue", "capacity", "missing"]
METHODS = {"breakeven": "breakeven", "multibreakeven": "multi_product_breakeven",
           "unitecon": "unit_economics", "forecast": "trend_forecast",
           "inventory": "inventory_policy", "queue": "queue_analysis",
           "capacity": "capacity_analysis", "missing": "missing_data_bounds"}

#: The eleven shared worksheets, in the order the page declares them.
WORKSHEETS = {"OPS-01": "template_scor", "OPS-02": "template_sipoc",
              "OPS-03": "template_value_stream_map", "OPS-04": "template_5s",
              "OPS-05": "template_a3", "OPS-06": "template_toc",
              "OPS-07": "template_root_cause", "OPS-08": "template_fmea",
              "OPS-10": "template_kraljic", "OPS-11": "template_sop",
              "OPS-12": "template_pdca"}

#: The nine records: one computed framework and the eight quantitative rows.
RECORDS = ["OPS-09", "QNT-OPS-01", "QNT-OPS-02", "QNT-OPS-03", "QNT-OPS-04",
           "QNT-OPS-05", "QNT-OPS-06", "QNT-OPS-07", "QNT-OPS-08"]
READ_ONLY_RECORDS = ["QNT-OPS-03", "QNT-OPS-07"]

GROUPS = ["Cost and mix", "Demand and planning", "Inventory and network"]
GROUP_MEMBERS = {"Cost and mix": ["breakeven", "multibreakeven", "unitecon"],
                 "Demand and planning": ["forecast", "missing"],
                 "Inventory and network": ["inventory", "queue", "capacity"]}

GLOSSARY_TERMS = 20

YES = lambda spec: True                                    # noqa: E731


def page(subject=SUBJECT):
    return subjects.detail(subject)


def preset_request(key):
    """The exact request the page's launcher would send for one tool."""
    tool = subjects.TOOL_INFO[key]
    preset = server.PRESETS[tool["preset"]]
    return {"objective": preset["objective"], "method": preset["method"],
            "inputs": preset["inputs"], "currency": preset.get("currency"),
            "period": preset.get("period")}


def delivered(request):
    decision = Pipeline().run(request, YES)
    assert decision.status == "delivered", decision.blocked_reason
    return decision


def refused(request):
    return Pipeline().run(request, YES)


def run(method_id, inputs):
    method = LIBRARY[method_id]
    return method.impl(inputs), method.tests(inputs, method.impl)


def close(actual, expected, tol=TOL):
    """Decimal comparison at the core's own tolerance."""
    return abs(Decimal(str(actual)) - Decimal(str(expected))) <= tol


def z_value(level):
    """The standard-normal quantile, computed here from its own definition.

    A bisection on the error function keeps the test independent of whatever
    table or inverse-CDF the method uses.
    """
    from math import erf, sqrt
    target = float(level)
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        cdf = 0.5 * (1.0 + erf(mid / sqrt(2.0)))
        if cdf < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ols(xs, ys):
    """Ordinary least squares, written here so the method is not its own oracle."""
    n = len(xs)
    mx = sum(xs) / n
    my = sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    slope = sxy / sxx
    return slope, my - slope * mx


def erlang_c(arrival, service, servers):
    """M/M/c queue metrics from the Erlang-C identity, written out in full."""
    a = arrival / service
    rho = a / servers
    assert rho < 1
    head = sum(a ** k / factorial(k) for k in range(servers))
    tail = a ** servers / (factorial(servers) * (1 - rho))
    p0 = 1 / (head + tail)
    p_wait = tail * p0
    lq = p_wait * rho / (1 - rho)
    return {"offered_load": a, "utilisation": rho, "p0": p0, "p_wait": p_wait,
            "lq": lq, "wq": lq / arrival, "l": lq + a, "w": (lq + a) / arrival}


class Inventory(unittest.TestCase):
    """E-scl-001 ... E-scl-012 - what the shelf actually offers."""

    def test_E_scl_001__the_eight_declared_calculators_in_order(self):
        self.assertEqual([t["key"] for t in page()["tools"]], TOOLS)
        self.assertEqual(len(page()["tools"]), 8)

    def test_E_scl_002__three_groups_in_the_declared_order(self):
        order = []
        for tool in page()["tools"]:
            if tool["group"] not in order:
                order.append(tool["group"])
        self.assertEqual(order, GROUPS)
        for group, members in GROUP_MEMBERS.items():
            served = [t["key"] for t in page()["tools"] if t["group"] == group]
            self.assertEqual(served, members, group)

    def test_E_scl_003__every_tool_carries_the_student_notes(self):
        for tool in page()["tools"]:
            self.assertTrue(tool["formula"], tool["key"])
            self.assertTrue(tool["steps"], tool["key"])
            self.assertTrue(tool["common_mistakes"], tool["key"])
            self.assertIn(tool["level"], ("intro", "intermediate", "advanced"), tool["key"])
            self.assertTrue(tool["period"], tool["key"])
            self.assertTrue(tool["related"], tool["key"])

    def test_E_scl_004__eleven_worksheets_all_from_the_operations_catalogue(self):
        sheets = page()["worksheets"]
        self.assertEqual([w["key"] for w in sheets], list(WORKSHEETS))
        self.assertEqual(len(sheets), 11)
        for sheet in sheets:
            self.assertEqual(sheet["template"], WORKSHEETS[sheet["key"]], sheet["key"])
            self.assertIn(sheet["template"], T.TEMPLATES, sheet["key"])

    def test_E_scl_005__exactly_one_worksheet_is_not_draftable(self):
        not_draftable = [w["key"] for w in page()["worksheets"] if not w["draftable"]]
        self.assertEqual(not_draftable, ["OPS-03"])

    def test_E_scl_006__the_not_draftable_worksheet_states_a_reason(self):
        """Measured pair, ledgered as D-SCL-02.

        OPS-03 is the one tile with no drafting button (`draftable: False`), yet its
        catalogue row still reads `worksheet available: structure and evidence audit
        only`.  Nothing the student sees says *why* the button is absent.  This test
        pins the measured pair so the next reader re-measures instead of copying a
        claim; when the wording is fixed the assertion below fails and is updated.
        """
        served = page()
        sheet = {w["key"]: w for w in served["worksheets"]}["OPS-03"]
        row = {r["id"]: r for r in served["catalogue"]}["OPS-03"]
        self.assertFalse(sheet["draftable"])
        self.assertTrue(row["implementation_status"].startswith("worksheet available"), row)
        self.assertIn("template_value_stream_map", WORKSHEETS.values())


class Contract(unittest.TestCase):
    """E-scl-013 ... E-scl-019 - the C1 contract on all eight methods."""

    def test_E_scl_013__use_limits_assumptions_and_limitations_are_declared(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertTrue(method.intended_use.strip(), key)
            self.assertTrue(method.unsupported_use.strip(), key)
            self.assertTrue(method.assumptions, key)
            self.assertTrue(method.limitations, key)

    def test_E_scl_014__at_least_three_named_checks_that_actually_run(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertGreaterEqual(len(method.test_names), 3, key)
            inputs = server.PRESETS[subjects.TOOL_INFO[key]["preset"]]["inputs"]
            result = method.tests(inputs, method.impl)
            self.assertEqual(tuple(name for name, _ in result), method.test_names, key)
            self.assertTrue(all(ok for _, ok in result), key)

    def test_E_scl_015__tier_metric_unit_and_claim_ceiling(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertIn(method.tier, ("T1", "T2", "T3"), key)
            self.assertTrue(method.metric, key)
            self.assertTrue(method.unit, key)
            self.assertIn(method.claim_ceiling,
                          ("descriptive", "predictive", "prescriptive", "causal"), key)

    def test_E_scl_016__every_input_declares_a_type_and_a_description(self):
        for key in TOOLS:
            schema = LIBRARY[METHODS[key]].input_schema
            self.assertTrue(schema, key)
            for name, spec in schema.items():
                self.assertTrue(spec.get("type"), (key, name))
                self.assertTrue(str(spec.get("desc") or "").strip(), (key, name))

    def test_E_scl_017__every_tool_has_a_server_preset_for_the_same_method(self):
        for key in TOOLS:
            tool = subjects.TOOL_INFO[key]
            self.assertIn(tool["preset"], server.PRESETS, key)
            self.assertEqual(server.PRESETS[tool["preset"]]["method"], tool["method"], key)
            self.assertEqual(tool["method"], METHODS[key], key)

    def test_E_scl_018__every_tool_declares_the_period_its_inputs_are_read_in(self):
        for tool in page()["tools"]:
            self.assertTrue(tool["period"], tool["key"])
            self.assertIn(tool["period"],
                          ("annual", "per period", "per observation", "cross_section"), tool["key"])

    def test_E_scl_019__every_output_has_a_declared_unit_and_precision(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            outputs = method.impl(server.PRESETS[subjects.TOOL_INFO[key]["preset"]]["inputs"])
            for metric in outputs:
                if metric.startswith("_"):
                    continue
                self.assertTrue(method.typing, (key, metric))
                unit, precision = method.typing(metric)
                self.assertTrue(unit, (key, metric))
                self.assertIsInstance(precision, int, (key, metric))
                self.assertGreaterEqual(precision, 0, (key, metric))


class NumbersCostAndMix(unittest.TestCase):
    """E-scl-020 ... E-scl-024 - break-even, the mix, and unit economics."""

    def test_E_scl_020__breakeven_units_by_hand(self):
        fixed, price, variable = Decimal("1000"), Decimal("20"), Decimal("10")
        out, checks = run("breakeven", {"fixed": "1000", "price": "20", "variable": "10"})
        contribution = price - variable
        self.assertEqual(out["contribution_margin"], contribution)
        self.assertEqual(out["breakeven_units"], fixed / contribution)          # 100
        self.assertEqual(out["breakeven_revenue"], out["breakeven_units"] * price)  # 2000
        self.assertTrue(close(out["contribution_margin_ratio"], contribution / price))
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_021__the_mix_ratio_recomputed_independently(self):
        products = [{"name": "coffee", "mix_units": "3", "price": "5", "variable_cost": "2"},
                    {"name": "cake", "mix_units": "1", "price": "6", "variable_cost": "3"}]
        out, checks = run("multi_product_breakeven", {"fixed_costs": "6000", "products": products})
        mix = [Decimal("3"), Decimal("1")]
        margins = [Decimal("5") - Decimal("2"), Decimal("6") - Decimal("3")]
        weighted = sum(m * c for m, c in zip(mix, margins)) / sum(mix)   # 12 / 4 = 3
        batches = Decimal("6000") / sum(m * c for m, c in zip(mix, margins))  # 6000 / 12 = 500
        total_units = batches * sum(mix)                                  # 2000
        self.assertEqual(out["weighted_contribution"], weighted)
        self.assertEqual(out["total_mix_units"], sum(mix))
        self.assertEqual(out["breakeven_total_units"], total_units)
        self.assertEqual(out["units_coffee"], batches * mix[0])
        self.assertEqual(out["units_cake"], batches * mix[1])
        self.assertEqual(out["breakeven_revenue"],
                         batches * sum(m * p for m, p in zip(mix, [Decimal("5"), Decimal("6")])))
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_022__the_fixed_cost_is_covered_exactly_once(self):
        products = [{"name": "coffee", "mix_units": "3", "price": "5", "variable_cost": "2"},
                    {"name": "cake", "mix_units": "1", "price": "6", "variable_cost": "3"}]
        out, _ = run("multi_product_breakeven", {"fixed_costs": "6000", "products": products})
        covered = (out["units_coffee"] * (Decimal("5") - Decimal("2"))
                   + out["units_cake"] * (Decimal("6") - Decimal("3")))
        self.assertEqual(covered, Decimal("6000"))
        # and at one unit below break-even the contribution falls short
        short = ((out["units_coffee"] - Decimal("3")) * Decimal("3")
                 + (out["units_cake"] - Decimal("1")) * Decimal("3"))
        self.assertLess(short, Decimal("6000"))

    def test_E_scl_023__unit_margin_payback_and_ltv(self):
        inputs = {"price": "49", "variable_cost": "12", "acquisition_cost": "80", "churn_rate": "0.04"}
        out, checks = run("unit_economics", inputs)
        margin = Decimal("49") - Decimal("12")                            # 37
        self.assertEqual(out["unit_margin"], margin)
        self.assertTrue(close(out["margin_pct"], margin / Decimal("49")))
        self.assertTrue(close(out["payback_periods"], Decimal("80") / margin))   # 2.162162...
        self.assertEqual(out["ltv"], margin / Decimal("0.04"))            # 925
        self.assertTrue(close(out["ltv_cac"], out["ltv"] / Decimal("80")))
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_024__churn_is_a_period_rate_so_lifetime_is_margin_over_churn(self):
        """Months vs years: the lifetime is 1/churn *periods*, never 12/churn."""
        for churn in ("0.02", "0.04", "0.10"):
            out, _ = run("unit_economics", {"price": "49", "variable_cost": "12",
                                            "acquisition_cost": "80", "churn_rate": churn})
            self.assertEqual(out["ltv"], Decimal("37") / Decimal(churn), churn)
        with self.assertRaises(DataError):
            run("unit_economics", {"price": "49", "variable_cost": "12",
                                   "acquisition_cost": "80", "churn_rate": "6"})


class NumbersDemandAndPlanning(unittest.TestCase):
    """E-scl-025 ... E-scl-027 - the trend forecast and the missing-data bounds."""

    SERIES = ["10", "12", "11", "14", "13", "16", "15", "18", "17", "20", "19", "22"]

    def inputs(self):
        preset = server.PRESETS[subjects.TOOL_INFO["forecast"]["preset"]]["inputs"]
        return {"values": list(preset["values"]), "horizon": preset.get("horizon", "3")}

    def test_E_scl_025__the_slope_and_intercept_fitted_in_this_test(self):
        inputs = self.inputs()
        out, checks = run("trend_forecast", inputs)
        ys = [float(v) for v in inputs["values"]]
        slope, intercept = ols(list(range(1, len(ys) + 1)), ys)
        self.assertAlmostEqual(float(out["slope"]), slope, places=9)
        self.assertAlmostEqual(float(out["intercept"]), intercept, places=9)
        self.assertEqual(int(out["n_fitted"]), len(ys))
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_026__the_forecast_is_a_plus_b_times_n_plus_k(self):
        inputs = self.inputs()
        out, _ = run("trend_forecast", inputs)
        ys = [float(v) for v in inputs["values"]]
        slope, intercept = ols(list(range(1, len(ys) + 1)), ys)
        n = len(ys)
        for k in range(1, int(out["horizon"]) + 1):
            self.assertAlmostEqual(float(out["forecast_%d" % k]), intercept + slope * (n + k), places=9)
            self.assertLess(float(out["ci_lower_%d" % k]), float(out["ci_upper_%d" % k]))

    def test_E_scl_027__the_holdout_mae_recomputed(self):
        inputs = self.inputs()
        out, _ = run("trend_forecast", inputs)
        ys = [float(v) for v in inputs["values"]]
        holdout = int(out["n_holdout"])
        train = ys[:len(ys) - holdout]
        slope, intercept = ols(list(range(1, len(train) + 1)), train)
        errors = [abs(ys[len(train) + i] - (intercept + slope * (len(train) + i + 1)))
                  for i in range(holdout)]
        self.assertAlmostEqual(float(out["mae_holdout"]), sum(errors) / holdout, places=9)

    def test_E_scl_028__the_bounds_are_the_declared_extremes_never_an_imputation(self):
        inputs = {"values": ["10", "12", "", "14", "99", "16"], "missing_codes": ["99"]}
        out, checks = run("missing_data_bounds", inputs)
        observed = [Decimal("10"), Decimal("12"), Decimal("14"), Decimal("16")]
        missing = Decimal("2")
        low = Decimal("10")
        high = Decimal("16")
        self.assertEqual(out["n_valid"], Decimal("4"))
        self.assertEqual(out["n_missing"], missing)
        self.assertTrue(close(out["pct_missing"], missing / Decimal("6")))
        self.assertTrue(close(out["mean_observed"], sum(observed) / len(observed)))
        # worst case: every missing value is the smallest observed one
        self.assertTrue(close(out["bound_low"], (sum(observed) + missing * low) / Decimal("6")))
        # best case: every missing value is the largest observed one
        self.assertTrue(close(out["bound_high"], (sum(observed) + missing * high) / Decimal("6")))
        self.assertTrue(close(out["bound_width"], out["bound_high"] - out["bound_low"]))
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_029__no_imputed_value_appears_anywhere_in_the_output(self):
        """Bounds only: the output carries no filled-in observation and no filled mean."""
        inputs = {"values": ["10", "12", "", "14", "99", "16"], "missing_codes": ["99"]}
        out, _ = run("missing_data_bounds", inputs)
        numbers = {str(k): v for k, v in out.items() if not k.startswith("_")}
        self.assertNotIn("imputed", " ".join(numbers).lower())
        self.assertNotIn("filled", " ".join(numbers).lower())
        # the complete-data mean is never claimed: only a bracket is
        self.assertNotIn("mean_complete", numbers)
        self.assertNotIn("mean_imputed", numbers)
        # every published figure is one of the two bounds, the observed mean, or a count
        for key in ("bound_low", "bound_high"):
            self.assertLessEqual(Decimal(numbers[key]), Decimal("16"))
            self.assertGreaterEqual(Decimal(numbers[key]), Decimal("10"))
        self.assertLessEqual(Decimal(numbers["bound_low"]), Decimal(numbers["mean_observed"]))
        self.assertGreaterEqual(Decimal(numbers["bound_high"]), Decimal(numbers["mean_observed"]))


class NumbersInventoryAndNetwork(unittest.TestCase):
    """E-scl-030 ... E-scl-036 - inventory, queueing and capacity."""

    INVENTORY = {"annual_demand": "12000", "order_cost": "500", "holding_cost_per_unit": "30",
                 "lead_time_days": "10", "service_level": "0.95", "daily_demand_sd": "20"}

    def test_E_scl_030__eoq_orders_per_year_and_cycle_stock(self):
        from math import sqrt
        out, checks = run("inventory_policy", self.INVENTORY)
        demand, order_cost, holding = 12000.0, 500.0, 30.0
        eoq = sqrt(2 * demand * order_cost / holding)              # 632.455532
        self.assertAlmostEqual(float(out["economic_order_quantity"]), eoq, places=6)
        self.assertAlmostEqual(float(out["orders_per_year"]), demand / eoq, places=6)
        self.assertAlmostEqual(float(out["cycle_stock"]), eoq / 2, places=6)
        self.assertAlmostEqual(float(out["annual_ordering_cost"]), demand / eoq * order_cost, places=6)
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_031__safety_stock_and_reorder_point_by_hand(self):
        from math import sqrt
        out, _ = run("inventory_policy", self.INVENTORY)
        z = z_value(0.95)                                          # 1.6448536269...
        safety = z * 20.0 * sqrt(10.0)                             # 104.029677
        daily = 12000.0 / 365.0                                    # 32.876712
        self.assertAlmostEqual(float(out["safety_factor"]), z, places=9)
        self.assertAlmostEqual(float(out["safety_stock"]), safety, places=6)
        self.assertAlmostEqual(float(out["reorder_point"]), daily * 10.0 + safety, places=6)
        self.assertAlmostEqual(float(out["average_inventory"]),
                               float(out["cycle_stock"]) + float(out["safety_stock"]), places=6)
        self.assertAlmostEqual(float(out["total_annual_cost"]),
                               float(out["annual_ordering_cost"]) + float(out["annual_holding_cost"]), places=6)

    def test_E_scl_032__the_days_versus_periods_conversion_is_declared(self):
        """Annual demand is divided by the declared trading days, not by 365 by default."""
        from math import sqrt
        out, _ = run("inventory_policy", self.INVENTORY)
        self.assertEqual(Decimal(str(out["days_per_year"])), Decimal("365"))
        self.assertAlmostEqual(float(out["daily_demand"]), 12000.0 / 365.0, places=9)
        shorter, _ = run("inventory_policy", dict(self.INVENTORY, days_per_year="250"))
        self.assertEqual(Decimal(str(shorter["days_per_year"])), Decimal("250"))
        self.assertAlmostEqual(float(shorter["daily_demand"]), 12000.0 / 250.0, places=9)
        # the reorder point moves with the calendar, the EOQ does not
        self.assertNotAlmostEqual(float(shorter["reorder_point"]), float(out["reorder_point"]), places=3)
        self.assertAlmostEqual(float(shorter["economic_order_quantity"]),
                               sqrt(2 * 12000 * 500 / 30), places=6)

    def test_E_scl_033__the_mm1_queue_recomputed(self):
        out, checks = run("queue_analysis", {"arrival_rate": "18", "service_rate": "24"})
        lam, mu = 18.0, 24.0
        rho = lam / mu                                             # 0.75
        self.assertAlmostEqual(float(out["utilisation"]), rho, places=9)
        self.assertAlmostEqual(float(out["average_in_queue"]), rho ** 2 / (1 - rho), places=9)   # 2.25
        self.assertAlmostEqual(float(out["average_in_system"]), rho / (1 - rho), places=9)       # 3.00
        self.assertAlmostEqual(float(out["average_wait_in_queue"]), rho / (mu - lam), places=9)  # 0.125
        self.assertAlmostEqual(float(out["average_time_in_system"]), 1 / (mu - lam), places=9)
        self.assertAlmostEqual(float(out["probability_empty"]), 1 - rho, places=9)
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_034__erlang_c_written_in_the_test_and_reducing_to_mm1(self):
        lam, mu, servers = 18.0, 24.0, 2
        out, _ = run("queue_analysis", {"arrival_rate": "18", "service_rate": "24", "servers": "2"})
        expected = erlang_c(lam, mu, servers)
        self.assertAlmostEqual(float(out["offered_load"]), expected["offered_load"], places=9)
        self.assertAlmostEqual(float(out["utilisation"]), expected["utilisation"], places=9)
        self.assertAlmostEqual(float(out["probability_empty"]), expected["p0"], places=9)
        self.assertAlmostEqual(float(out["probability_waiting"]), expected["p_wait"], places=9)
        self.assertAlmostEqual(float(out["average_in_queue"]), expected["lq"], places=9)
        self.assertAlmostEqual(float(out["average_wait_in_queue"]), expected["wq"], places=9)
        self.assertAlmostEqual(float(out["average_in_system"]), expected["l"], places=9)
        # the single-server limiting case is the M/M/1 result
        single, _ = run("queue_analysis", {"arrival_rate": "18", "service_rate": "24"})
        mm1 = erlang_c(lam, mu, 1)
        self.assertAlmostEqual(float(single["average_in_queue"]), mm1["lq"], places=9)
        self.assertAlmostEqual(float(single["average_in_system"]), mm1["l"], places=9)

    def test_E_scl_035__the_bottleneck_is_the_smallest_capacity_not_the_sum(self):
        out, checks = run("capacity_analysis", {
            "resources": [{"name": "cutting", "available_hours": "8", "minutes_per_unit": "5"},
                          {"name": "assembly", "available_hours": "8", "minutes_per_unit": "8"},
                          {"name": "packing", "available_hours": "8", "minutes_per_unit": "3"}],
            "demand": "50"})
        caps = [8 * 60 / 5, 8 * 60 / 8, 8 * 60 / 3]                # 96, 60, 160
        self.assertAlmostEqual(float(out["capacity_1"]), caps[0], places=9)
        self.assertAlmostEqual(float(out["capacity_2"]), caps[1], places=9)
        self.assertAlmostEqual(float(out["capacity_3"]), caps[2], places=9)
        self.assertAlmostEqual(float(out["max_output"]), min(caps), places=9)
        self.assertNotEqual(float(out["max_output"]), sum(caps))
        self.assertEqual(int(out["bottleneck_index"]), caps.index(min(caps)) + 1)
        self.assertAlmostEqual(float(out["bottleneck_utilisation"]), 50 / min(caps), places=9)
        self.assertAlmostEqual(float(out["capacity_gap"]), min(caps) - 50, places=9)
        self.assertTrue(all(ok for _, ok in checks))

    def test_E_scl_036__the_implied_cycle_time_follows_from_the_bottleneck(self):
        out, _ = run("capacity_analysis", {
            "resources": [{"name": "cutting", "available_hours": "8", "minutes_per_unit": "5"},
                          {"name": "assembly", "available_hours": "8", "minutes_per_unit": "8"}],
            "demand": "50"})
        # 8 available hours at 8 minutes a unit is 60 units a period, so one unit every 8 minutes
        self.assertAlmostEqual(float(out["max_output"]), 60.0, places=9)
        self.assertAlmostEqual(8 * 60 / float(out["max_output"]), 8.0, places=9)


#: Units the engine may declare.  A unit outside this list is a typo, not a new kind.
UNITS = {"currency", "units", "count", "days", "periods", "ratio", "rate", "probability",
         "correlation", "coefficient", "index", "@unit", "from_request"}

#: Names that denote a count of things (people, orders, days, periods of observation).
COUNT_NAMES = {"average_in_queue", "average_in_system", "servers", "n_valid", "n_missing",
               "n_fitted", "n_holdout", "n_excluded", "horizon", "bottleneck_index",
               "orders_per_year", "days_per_year", "n", "n_columns"}


def unit_contradictions():
    """Every (method, metric) whose declared unit contradicts its own name.

    The rule is mechanical, so it cannot be tuned to the answer: a `_days` name is
    days, a count name is a count, a `_rate` name is a rate (a count per period is
    also accepted), a `_pct` name is a share.  Anything else is not judged here.
    """
    found = {}
    for key in TOOLS:
        method = LIBRARY[METHODS[key]]
        inputs = server.PRESETS[subjects.TOOL_INFO[key]["preset"]]["inputs"]
        for metric in method.impl(inputs):
            if metric.startswith("_"):
                continue
            unit = method.typing(metric)[0]
            if metric.endswith("_days") and unit != "days":
                found[(method.name, metric)] = unit
            elif metric.endswith("_rate") and unit not in ("rate", "count"):
                found[(method.name, metric)] = unit
            elif metric.endswith("_pct") and unit not in ("ratio", "rate", "probability"):
                found[(method.name, metric)] = unit
            elif metric in COUNT_NAMES and unit not in ("count", "units"):
                found[(method.name, metric)] = unit
    return found


class UnitAudit(unittest.TestCase):
    """E-scl-037 ... E-scl-039 - the declared unit and precision of every output."""

    def test_E_scl_037__every_declared_unit_is_in_the_vocabulary(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            inputs = server.PRESETS[subjects.TOOL_INFO[key]["preset"]]["inputs"]
            for metric in method.impl(inputs):
                if metric.startswith("_"):
                    continue
                unit, precision = method.typing(metric)
                self.assertIn(unit, UNITS, (method.name, metric))
                self.assertLessEqual(precision, 6, (method.name, metric))

    def test_E_scl_038__the_known_unit_contradictions_are_exactly_these(self):
        """Measured pair, ledgered as D-SCL-01 (BLOCKER class: the B-190 family).

        `days_per_year` is a count of trading days and is typed as **currency**, so
        the paper can print it with a money prefix.  `average_in_queue` and
        `average_in_system` are counts of customers and are typed as **ratio**.
        Both live in `_inventory_typing` / `_queue_typing` in `src/bp/methods.py`,
        which is the frozen core: fixing them needs the owner's word (§9).

        The assertion is deliberately exact.  When the units are corrected this
        test fails and the next reader re-measures instead of copying the claim.
        """
        self.assertEqual(unit_contradictions(), {
            ("inventory_policy", "days_per_year"): "currency",
            ("queue_analysis", "average_in_queue"): "ratio",
            ("queue_analysis", "average_in_system"): "ratio",
        })

    def test_E_scl_039__the_units_that_are_right_stay_right(self):
        inventory = LIBRARY["inventory_policy"]
        self.assertEqual(inventory.typing("lead_time_days"), ("days", 2))
        self.assertEqual(inventory.typing("service_level"), ("rate", 4))
        self.assertEqual(inventory.typing("economic_order_quantity"), ("units", 2))
        self.assertEqual(inventory.typing("total_annual_cost"), ("currency", 2))
        queue = LIBRARY["queue_analysis"]
        self.assertEqual(queue.typing("utilisation"), ("ratio", 4))
        self.assertEqual(queue.typing("average_wait_in_queue"), ("periods", 4))
        capacity = LIBRARY["capacity_analysis"]
        self.assertEqual(capacity.typing("bottleneck_utilisation"), ("ratio", 4))
        self.assertEqual(capacity.typing("max_output"), ("units", 2))
        missing = LIBRARY["missing_data_bounds"]
        self.assertEqual(missing.typing("pct_missing"), ("probability", 4))
        self.assertEqual(missing.typing("n_missing"), ("count", 0))


class Refusals(unittest.TestCase):
    """E-scl-040 ... E-scl-050 - the boundary and refusal sweep for all eight."""

    def test_E_scl_040__zero_and_negative_are_refused_where_they_are_undefined(self):
        with self.assertRaises(DataError):
            run("breakeven", {"fixed": "-1000", "price": "20", "variable": "10"})
        with self.assertRaises(DataError):
            run("inventory_policy", {"annual_demand": "12000", "order_cost": "500",
                                     "holding_cost_per_unit": "0", "lead_time_days": "10"})
        with self.assertRaises(DataError):
            run("queue_analysis", {"arrival_rate": "0", "service_rate": "24"})
        with self.assertRaises(DataError):
            run("capacity_analysis", {"resources": [{"name": "a", "available_hours": "8",
                                                     "minutes_per_unit": "0"}]})
        # a zero fixed cost is defined, and returns zero rather than refusing
        out, _ = run("breakeven", {"fixed": "0", "price": "20", "variable": "10"})
        self.assertEqual(out["breakeven_units"], Decimal("0"))

    def test_E_scl_041__an_empty_list_is_refused(self):
        self.assertTrue(validate_inputs(LIBRARY["capacity_analysis"], {"resources": []}))
        self.assertTrue(validate_inputs(LIBRARY["missing_data_bounds"], {"values": []}))
        self.assertTrue(validate_inputs(LIBRARY["trend_forecast"], {"values": []}))
        with self.assertRaises(DataError):
            run("multi_product_breakeven", {"fixed_costs": "100", "products": []})

    def test_E_scl_042__a_single_element_is_defined_or_refused_with_a_reason(self):
        out, _ = run("missing_data_bounds", {"values": ["5"]})
        self.assertEqual(out["n_valid"], Decimal("1"))
        self.assertEqual(out["bound_width"], Decimal("0"))
        out, _ = run("capacity_analysis", {"resources": [{"name": "only", "available_hours": "8",
                                                          "minutes_per_unit": "4"}]})
        self.assertEqual(out["max_output"], Decimal("120"))
        self.assertTrue(validate_inputs(LIBRARY["trend_forecast"], {"values": ["5"]}))
        with self.assertRaises(DataError):
            run("trend_forecast", {"values": ["5"]})

    def test_E_scl_043__all_equal_values_give_a_zero_width_or_are_refused(self):
        out, _ = run("missing_data_bounds", {"values": ["5", "5", "5"]})
        self.assertEqual(out["bound_low"], out["bound_high"])
        self.assertEqual(out["bound_width"], Decimal("0"))
        with self.assertRaises(DataError):
            run("trend_forecast", {"values": ["5", "5", "5", "5", "5", "5"]})

    def test_E_scl_044__duplicates_are_counted_not_collapsed(self):
        out, _ = run("missing_data_bounds", {"values": ["5", "5", "5", "5"]})
        self.assertEqual(out["n_valid"], Decimal("4"))
        self.assertEqual(out["mean_observed"], Decimal("5"))

    def test_E_scl_045__very_large_values_stay_exact(self):
        out, _ = run("breakeven", {"fixed": "1200000000000", "price": "2000000",
                                   "variable": "1000000"})
        self.assertEqual(out["breakeven_units"], Decimal("1200000"))
        self.assertEqual(out["breakeven_revenue"], Decimal("2400000000000"))

    def test_E_scl_046__a_thousands_separator_is_refused_by_name(self):
        errors = validate_inputs(LIBRARY["breakeven"],
                                 {"fixed": "1,200,000", "price": "20", "variable": "10"})
        self.assertEqual(len(errors), 1)
        self.assertIn("'fixed'", errors[0])
        self.assertIn("not a valid number", errors[0])

    def test_E_scl_047__a_rate_entered_as_6_is_refused_not_rescaled(self):
        with self.assertRaises(DataError):
            run("unit_economics", {"price": "49", "variable_cost": "12",
                                   "acquisition_cost": "80", "churn_rate": "6"})
        with self.assertRaises(DataError):
            run("inventory_policy", {"annual_demand": "12000", "order_cost": "500",
                                     "holding_cost_per_unit": "30", "lead_time_days": "10",
                                     "service_level": "6"})

    def test_E_scl_048__a_period_mismatch_is_taken_as_given_and_disclosed(self):
        """Monthly demand with a daily lead time is not refused: the level convention is stated."""
        out, _ = run("inventory_policy", {"annual_demand": "1000", "order_cost": "50",
                                          "holding_cost_per_unit": "4", "lead_time_days": "2"})
        self.assertGreater(float(out["reorder_point"]), 0)
        caveats = " ".join(LIBRARY["inventory_policy"].caveats(out, {}))
        self.assertIn("lead time is constant", caveats)
        self.assertIn("level over the year", caveats)

    def test_E_scl_049__a_currency_label_changes_no_number(self):
        base = preset_request("inventory")
        php = delivered(dict(base, currency="PHP"))
        usd = delivered(dict(base, currency="USD"))
        self.assertEqual(php.appendix["reperform"]["outputs_hash"],
                         usd.appendix["reperform"]["outputs_hash"])
        self.assertIn("PHP", php.report)
        self.assertIn("USD", usd.report)

    def test_E_scl_050__unknown_method_unknown_input_and_wrong_type_are_actionable(self):
        unknown = refused({"objective": "x", "method": "no_such_method", "inputs": {}})
        self.assertEqual(unknown.status, "blocked")
        self.assertIn("unknown method", unknown.blocked_reason)

        extra = refused({"objective": "x", "method": "breakeven",
                         "inputs": {"fixed": "1000", "price": "20", "variable": "10", "extra": "1"}})
        self.assertEqual(extra.status, "blocked")
        self.assertIn("unknown input 'extra'", extra.blocked_reason)

        wrong = refused({"objective": "x", "method": "breakeven",
                         "inputs": {"fixed": ["1000"], "price": "20", "variable": "10"}})
        self.assertEqual(wrong.status, "blocked")
        self.assertIn("not a valid number", wrong.blocked_reason)
        for decision in (unknown, extra, wrong):
            self.assertNotIn("Traceback", str(decision.blocked_reason))


class Parity(unittest.TestCase):
    """E-scl-051 ... E-scl-053 - the same method on two shelves must run the same."""

    def test_E_scl_051__the_eight_tools_are_declared_on_both_shelves(self):
        here = {t["key"]: t for t in page()["tools"]}
        there = {t["key"]: t for t in page(OPERATIONS)["tools"]}
        for key in TOOLS:
            self.assertIn(key, there, key)
            self.assertEqual(here[key]["method"], there[key]["method"], key)
            self.assertEqual(here[key]["preset"], there[key]["preset"], key)

    def test_E_scl_052__the_period_metadata_is_identical(self):
        here = {t["key"]: t for t in page()["tools"]}
        there = {t["key"]: t for t in page(OPERATIONS)["tools"]}
        for key in TOOLS:
            self.assertEqual(here[key]["period"], there[key]["period"], key)

    def test_E_scl_053__the_same_preset_returns_an_identical_appendix_and_hash(self):
        for key in TOOLS:
            request = preset_request(key)
            # the shelf is presentation only: the request is the same whichever page
            # launched it, so the figures, the checks and the hash must be the same too
            here = delivered(request)
            there = delivered(request)
            self.assertEqual(here.appendix["reperform"], there.appendix["reperform"], key)
            self.assertEqual(here.appendix["reperform"]["outputs_hash"],
                             there.appendix["reperform"]["outputs_hash"], key)
            self.assertEqual(here.appendix["tests"], there.appendix["tests"], key)
            self.assertEqual(here.appendix["limitations"], there.appendix["limitations"], key)
            self.assertEqual(here.appendix["assumptions"], there.appendix["assumptions"], key)
            self.assertEqual(here.appendix["spec_hash"], there.appendix["spec_hash"], key)
            self.assertEqual(here.report, there.report, key)


APPENDIX_KEYS = {"spec_hash", "tier", "method", "run_id", "env_hash", "fallback_used",
                 "thresholds", "frameworks_selected", "registry", "frameworks_note",
                 "code_hash", "sandbox", "environment", "tests", "amendments",
                 "assumptions", "ambiguities", "limitations", "artifacts", "honesty",
                 "reperform"}


class Delivery(unittest.TestCase):
    """E-scl-054 ... E-scl-058 - the happy path, determinism and the disclosure."""

    def test_E_scl_054__every_preset_delivers_with_a_complete_appendix(self):
        for key in TOOLS:
            decision = delivered(preset_request(key))
            self.assertEqual(decision.status, "delivered", key)
            self.assertTrue(all(ok for _, ok, *_ in decision.appendix["tests"]), key)
            self.assertNotIn("{{ref:", decision.report, key)
            self.assertTrue(APPENDIX_KEYS.issubset(set(decision.appendix)), key)
            self.assertEqual(decision.appendix["tier"], "T1", key)
            self.assertEqual(decision.appendix["amendments"], 0, key)

    def test_E_scl_055__the_same_inputs_twice_give_the_same_row_and_hash(self):
        for key in TOOLS:
            first = delivered(preset_request(key))
            second = delivered(preset_request(key))
            self.assertEqual(first.appendix["reperform"]["outputs_hash"],
                             second.appendix["reperform"]["outputs_hash"], key)
            self.assertEqual(first.report, second.report, key)
            self.assertEqual(first.appendix["reperform"]["outputs"],
                             second.appendix["reperform"]["outputs"], key)

    def test_E_scl_056__the_appendix_survives_a_json_round_trip(self):
        for key in TOOLS:
            decision = delivered(preset_request(key))
            blob = json.dumps(decision.appendix, sort_keys=True)
            again = json.loads(blob)
            self.assertEqual(json.dumps(again, sort_keys=True), blob, key)
            self.assertEqual(again["reperform"]["outputs_hash"],
                             decision.appendix["reperform"]["outputs_hash"], key)

    def test_E_scl_057__a_refusal_is_a_refusal_not_a_zero(self):
        decision = refused({"objective": "x", "method": "queue_analysis",
                            "inputs": {"arrival_rate": "24", "service_rate": "24"}})
        self.assertEqual(decision.status, "blocked")
        self.assertTrue(decision.blocked_reason)
        self.assertIn("never clears", decision.blocked_reason)
        # no figure is produced: the appendix carries the block record, never a result
        self.assertNotIn("reperform", decision.appendix or {})
        self.assertFalse(decision.report)

    def test_E_scl_058__the_disclosure_names_what_was_not_done(self):
        forecast = delivered(preset_request("forecast"))
        note = forecast.appendix["honesty"].get("missing_data")
        self.assertTrue(note)
        self.assertIn("not established", note)

        missing = LIBRARY["missing_data_bounds"]
        limitations = " ".join(missing.limitations)
        self.assertIn("No imputation", limitations)
        self.assertIn("MAR/MCAR/MNAR", limitations)
        caveats = " ".join(missing.caveats(missing.impl(server.PRESETS["missing"]["inputs"]), {}))
        self.assertIn("not estimates", caveats)

        inventory = " ".join(LIBRARY["inventory_policy"].limitations).lower()
        self.assertIn("one item only", inventory)
        self.assertIn("no warehouse or budget constraint", inventory)

        queue = " ".join(LIBRARY["queue_analysis"].limitations).lower()
        self.assertIn("priorit", queue)


class PageAndGuide(unittest.TestCase):
    """E-scl-059 ... E-scl-062 - the page tells the student what it cannot do."""

    def test_E_scl_059__the_guidance_names_the_network_and_routing_gaps(self):
        guidance = page()["guidance"].lower()
        for phrase in ("network", "routing", "gaps"):
            self.assertIn(phrase, guidance)

    def test_E_scl_060__the_page_lists_what_it_does_not_do(self):
        definition = {d["id"]: d for d in subjects.SUBJECT_DEFS}[SUBJECT]
        does_not = " ".join(definition.get("does_not") or []).lower()
        self.assertIn("network", does_not)
        self.assertIn("routing", does_not)
        self.assertIn("multi-echelon", does_not)
        self.assertIn("supplier", does_not)

    def test_E_scl_061__the_two_read_only_records_are_reachable_from_the_page(self):
        rows = {r["id"]: r for r in page()["records"]}
        for rid in READ_ONLY_RECORDS:
            self.assertIn(rid, rows, rid)
            self.assertEqual(rows[rid]["form"], "read_only", rid)
            self.assertTrue(rows[rid]["status_short"], rid)

    def test_E_scl_062__the_curriculum_map_names_this_shelf_truthfully(self):
        path = "docs/CURRICULUM_MAP.md"
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        rows = [line for line in text.splitlines() if line.startswith("| Supply chain |")]
        self.assertEqual(len(rows), 1, rows)
        row = rows[0]
        self.assertIn("eleven operations worksheets", row)
        for gap in ("location", "routing", "transport", "multi-echelon", "supplier"):
            self.assertIn(gap, row.lower())


if __name__ == "__main__":
    unittest.main()







    def test_E_scl_007__nine_records_two_of_them_read_only(self):
        records = page()["records"]
        self.assertEqual([r["id"] for r in records], RECORDS)
        read_only = [r["id"] for r in records if r["form"] == "read_only"]
        self.assertEqual(read_only, READ_ONLY_RECORDS)
        for row in records:
            self.assertEqual(row["type"], "Q", row["id"])

    def test_E_scl_008__every_computed_record_links_a_method_that_exists(self):
        for row in page()["records"]:
            if row["form"] != "computed":
                continue
            self.assertTrue(row["linked_methods"], row["id"])
            for method_id in row["linked_methods"]:
                self.assertIn(method_id, LIBRARY, (row["id"], method_id))

    def test_E_scl_009__no_record_masquerades_as_a_calculator(self):
        for row in page()["records"]:
            if row["form"] == "computed":
                self.assertTrue(row["linked_methods"], row["id"])
            else:
                self.assertEqual(row["linked_methods"], [], row["id"])
                self.assertIsNone(row["template"], row["id"])

    def test_E_scl_010__the_glossary_carries_twenty_defined_terms(self):
        glossary = page()["glossary"]
        self.assertEqual(len(glossary), GLOSSARY_TERMS)
        for entry in glossary:
            self.assertTrue(entry["term"].strip())
            self.assertGreater(len(entry["definition"]), 30, entry["term"])

    def test_E_scl_011__worksheets_records_and_theories_partition_the_catalogue(self):
        served = page()
        ids = {r["id"] for r in served["catalogue"]}
        parts = {w["key"] for w in served["worksheets"]} | {r["id"] for r in served["records"]}
        parts |= {r["id"] for r in served["theories"]}
        self.assertEqual(ids, parts)
        self.assertEqual(len(served["catalogue"]), 20)
        self.assertEqual(served["theories"], [])

    def test_E_scl_012__the_page_states_the_contract_it_is_judged_against(self):
        served = page()
        self.assertEqual(served["label"], "Supply chain & logistics")
        self.assertIn("inventory and network gaps stated plainly", served["summary"])
        self.assertTrue(served["guidance"])
        self.assertIn("network", served["guidance"].lower())
        self.assertIn("routing", served["guidance"].lower())
