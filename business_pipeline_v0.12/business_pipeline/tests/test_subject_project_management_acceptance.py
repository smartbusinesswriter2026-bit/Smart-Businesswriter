"""Acceptance tests for the Project management shelf (session 7).

One test per acceptance row in `qa/manual/project-management.md`.  Every
expectation is read from the code or the served data - never from the manual -
and every numeric expectation is recomputed independently: hand arithmetic or a
second formula, never the method's own output compared with itself.

    $env:PYTHONPATH="src"; python -m unittest tests.test_subject_project_management_acceptance
"""

import copy
import io
import json
import os
import re
import sys
import unittest
import zipfile
from decimal import Decimal
from unittest import mock

sys.path.insert(0, "src")

from bp import registry as R, server, templates as T   # noqa: E402
from bp.methods import DataError, LIBRARY                      # noqa: E402
from bp.orchestrator import Pipeline                           # noqa: E402
from bp.product import completion, framework_profiles, matrix, subjects  # noqa: E402

SUBJECT = "project-management"
UNIT = "the shift-roster replacement project at a grocery retailer"
BRIEF = ("A grocery retailer is replacing its paper-based shift roster with a scheduling "
         "system, and the store manager must show the board the plan, the cost and the risk "
         "before the pilot starts in the second quarter.")

TOOLS = ["npv", "irr", "dpayback", "projectmetrics", "scenario", "case_decision", "forecast",
         "cpm", "evm", "leveling", "crashing", "calendar", "multiproject", "schedrisk",
         "decisiontree", "realoption", "mcda", "montecarlo"]
METHODS = {"npv": "npv", "irr": "irr", "dpayback": "discounted_payback",
           "projectmetrics": "project_metrics", "scenario": "scenario_analysis",
           "forecast": "trend_forecast", "cpm": "cpm_schedule", "evm": "earned_value",
           "leveling": "resource_leveling", "crashing": "project_crashing",
           "calendar": "calendar_schedule", "multiproject": "multi_project_schedule",
           "schedrisk": "schedule_risk", "decisiontree": "decision_tree",
           "realoption": "real_option", "mcda": "multi_criteria",
           "montecarlo": "monte_carlo"}

WORKSHEETS = {"PM-01": "template_balanced_scorecard",
              "PM-05": "template_project_charter", "PM-06": "template_risk_register",
              "PM-09": "template_wbs", "PM-10": "template_raci",
              "PM-15": "template_stakeholder_plan", "PM-16": "template_lessons_learned"}
RECORDS = ["PM-02", "PM-03", "PM-04", "PM-07", "PM-08", "PM-11", "PM-12",
           "PM-13", "PM-14"]
FORMS = {"template_balanced_scorecard": "matrix",
         "template_project_charter": "canvas", "template_wbs": "canvas",
         "template_raci": "matrix", "template_risk_register": "matrix",
         "template_stakeholder_plan": "canvas", "template_lessons_learned": "canvas"}


def page():
    return subjects.detail(SUBJECT)


def run(method_id, inputs):
    method = LIBRARY[method_id]
    return method.impl(inputs), method.tests(inputs, method.impl)


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": "grocery retailer " + query[:60],
        "abstract": "The paper reports how the project was run. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "International Journal of Project Management", "doi": "10.1/pm",
        "url": "https://doi.org/10.1/pm", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(template, sources=True, items=None, unit=None):
    side = academic if sources else (lambda *a, **k: {"results": [], "errors": [], "skipped": []})
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, BRIEF, industry="grocery retail",
                                   unit_value=unit if unit is not None else UNIT,
                                   student_items=items)


class InventoryTest(unittest.TestCase):
    """E-pm-001 ... E-pm-009 : what the shelf actually holds."""

    def test_E_pm_001__the_shelf_offers_the_eighteen_declared_calculators(self):
        self.assertEqual([tool["key"] for tool in page()["tools"]], TOOLS)

    def test_E_pm_002__the_six_worksheets_reconcile_one_to_one_with_the_catalogue(self):
        offered = {sheet["catalogue_id"]: sheet["template"] for sheet in page()["worksheets"]}
        self.assertEqual(offered, WORKSHEETS)

    def test_E_pm_003__the_ten_records_are_read_only_and_carry_no_template(self):
        records = page()["records"]
        self.assertEqual([row["id"] for row in records], RECORDS)
        for row in records:
            self.assertEqual(row["form"], "read_only", row["id"])
            self.assertIsNone(row["template"], row["id"])

    def test_E_pm_004__the_shelf_has_no_theories_and_twenty_three_glossary_terms(self):
        self.assertEqual(page()["theories"], [])
        self.assertEqual(len(page()["glossary"]), 23)

    def test_E_pm_005__every_glossary_term_carries_a_definition(self):
        for row in page()["glossary"]:
            self.assertTrue(row["term"].strip())
            self.assertGreater(len(row["definition"].split()), 6, row["term"])

    def test_E_pm_006__the_shelf_declares_no_tiles_and_the_page_falls_back_to_groups(self):
        """A measured zero, not a hidden one: the page groups by fallback."""
        self.assertEqual(page()["tiles"], [])
        self.assertNotIn(SUBJECT, subjects.SUBJECT_TILES)
        html = io.open("web/index.html", encoding="utf-8").read()
        self.assertIn("if ((s.tiles || []).length) {", html)
        self.assertIn("Complete a framework", html)          # worksheets lead the fallback

    def test_E_pm_007__every_worksheet_on_the_shelf_is_draftable(self):
        self.assertEqual([s["catalogue_id"] for s in page()["worksheets"]
                          if not s.get("draftable")], [])

    def test_E_pm_008__every_record_states_what_it_structures_and_needs(self):
        for row in page()["records"]:
            self.assertGreater(len(row["structures"].split()), 4, row["id"])
            self.assertGreater(len(row["evidence_needs"].split()), 3, row["id"])

    def test_E_pm_009__the_raci_record_is_shared_and_filed_under_both_pages(self):
        """K2: one paper serves both shelves; the id is PM-10 on both."""
        on_pm = [s["template"] for s in page()["worksheets"]]
        on_people = [s["template"] for s in subjects.detail("people")["worksheets"]]
        self.assertIn("template_raci", on_pm)
        self.assertIn("template_raci", on_people)
        self.assertEqual(R.get("PM-10")["form"], "worksheet")


class ContractTest(unittest.TestCase):
    """E-pm-010 ... E-pm-014 : the frozen contract of every calculator."""

    def test_E_pm_010__every_method_declares_its_use_limits_and_ceiling(self):
        for key, method_id in METHODS.items():
            method = LIBRARY[method_id]
            for field in ("intended_use", "unsupported_use", "assumptions", "limitations"):
                self.assertTrue(getattr(method, field), (key, field))
            self.assertIn(method.claim_ceiling, ("descriptive", "predictive", "causal",
                                                 "classification", "structural"), key)
            self.assertGreaterEqual(len(method.test_names), 3, key)

    def test_E_pm_011__every_input_declares_a_type_and_a_description(self):
        for key, method_id in METHODS.items():
            schema = LIBRARY[method_id].input_schema
            self.assertTrue(schema, key)
            for name, spec in schema.items():
                self.assertIn("type", spec, (key, name))
                self.assertTrue(spec.get("desc"), (key, name))

    def test_E_pm_012__every_method_is_a_declared_tier_and_states_a_metric_and_unit(self):
        for key, method_id in METHODS.items():
            method = LIBRARY[method_id]
            self.assertIn(method.tier, ("T1", "T2", "T3", "T4"), key)
            self.assertTrue(method.metric, key)
            self.assertTrue(method.unit, key)


    def test_E_pm_013__every_calculator_has_a_preset_on_the_server(self):
        for tool in page()["tools"]:
            self.assertIn(tool["preset"], server.PRESETS, tool["key"])

    def test_E_pm_014__case_decision_is_a_template_that_computes_not_a_core_method(self):
        """The one card with no bp.methods entry: it is a T2 template, and it delivers."""
        self.assertNotIn("case_decision", LIBRARY)
        self.assertEqual(T.TEMPLATES["case_decision"]["tier"], "T2")
        result = Pipeline().run(server.PRESETS["case_decision"], lambda _s: True)
        self.assertEqual(result.status, "delivered", result.blocked_reason)


def npv_of(flows, rate):
    """A second NPV: Decimal discounting written here, not the method's."""
    total = Decimal("0")
    for period, flow in enumerate(flows):
        total += Decimal(str(flow)) / (Decimal("1") + Decimal(str(rate))) ** period
    return total


def cpm_of(activities, durations=None):
    """A second CPM: forward and backward pass written here from the network."""
    dur = durations or {a["id"]: int(a["duration"]) for a in activities}
    preds = {a["id"]: [p.strip() for p in str(a.get("predecessors") or "").split(",")
                       if p.strip()] for a in activities}
    es, ef, order, pending = {}, {}, [], list(preds)
    while pending:
        for aid in list(pending):
            if all(p in ef for p in preds[aid]):
                es[aid] = max((ef[p] for p in preds[aid]), default=0)
                ef[aid] = es[aid] + dur[aid]
                order.append(aid)
                pending.remove(aid)
                break
        else:
            raise AssertionError("cycle in the test network")
    duration = max(ef.values())
    succ = {aid: [x for x in preds if aid in preds[x]] for aid in preds}
    ls, lf = {}, {}
    for aid in reversed(order):
        lf[aid] = min((ls[s] for s in succ[aid]), default=duration)
        ls[aid] = lf[aid] - dur[aid]
    return {"duration": duration, "es": es, "ef": ef, "ls": ls, "lf": lf,
            "float": {aid: ls[aid] - es[aid] for aid in preds}}


def lattice(value, strike, sigma, rate, steps):
    """A second binomial lattice: Cox-Ross-Rubinstein written here."""
    import math
    step = 1.0 / steps
    up = math.exp(sigma * math.sqrt(step))
    down = 1 / up
    prob = (math.exp(rate * step) - down) / (up - down)
    disc = math.exp(-rate * step)
    nodes = [value * up ** k * down ** (steps - k) for k in range(steps + 1)]
    option = [max(node - strike, 0.0) for node in nodes]
    for level in range(steps - 1, -1, -1):
        nodes = [value * up ** k * down ** (level - k) for k in range(level + 1)]
        hold = [disc * (prob * option[k + 1] + (1 - prob) * option[k])
                for k in range(level + 1)]
        option = [max(hold[k], nodes[k] - strike) for k in range(level + 1)]
    return option[0], up, prob


class NumbersTest(unittest.TestCase):
    """E-pm-015 ... E-pm-031 : every calculator recomputed independently."""

    def test_E_pm_015__npv_matches_discounting_written_in_the_test(self):
        flows = ["-1000", "400", "400", "400"]
        out = LIBRARY["npv"].impl({"rate": "0.10", "cashflows": flows})
        mine = npv_of(flows, "0.10")
        self.assertEqual(round(Decimal(str(out)), 6), round(mine, 6))
        self.assertEqual(round(mine, 6), Decimal("-5.259204"))

    def test_E_pm_016__irr_is_a_root_of_the_polynomial_the_test_builds(self):
        flows = ["-1000", "400", "400", "400", "400"]
        out = LIBRARY["irr"].impl({"cashflows": flows})
        rate = Decimal(str(out["irr"]))
        self.assertLess(abs(npv_of(flows, rate)), Decimal("0.01"))
        low, high = Decimal("0.01"), Decimal("1")
        for _ in range(200):
            middle = (low + high) / 2
            if npv_of(flows, middle) > 0:
                low = middle
            else:
                high = middle
        self.assertLess(abs((low + high) / 2 - rate), Decimal("0.000001"))

    def test_E_pm_017__discounted_payback_matches_the_cumulative_test_ledger(self):
        flows = ["-1000", "400", "400", "400", "400"]
        out = LIBRARY["discounted_payback"].impl({"cashflows": flows, "rate": "0.10"})
        cumulative, periods = Decimal("0"), Decimal("0")
        for period, flow in enumerate(flows[1:], 1):
            discounted = Decimal(flow) / Decimal("1.10") ** period
            if cumulative + discounted >= 1000:
                periods = Decimal(period - 1) + (Decimal("1000") - cumulative) / discounted
                break
            cumulative += discounted
        self.assertAlmostEqual(float(out["discounted_payback"]), float(periods), places=9)
        self.assertEqual(int(out["recovered_in_period"]), 4)

    def test_E_pm_018__profitability_index_and_mirr_match_the_test_arithmetic(self):
        flows = ["-1000", "400", "400", "400", "400"]
        out = LIBRARY["project_metrics"].impl({"cashflows": flows, "rate": "0.10",
                                               "finance_rate": "0.08"})
        inflow = sum((Decimal("400") / Decimal("1.10") ** period for period in range(1, 5)),
                     Decimal("0"))
        self.assertAlmostEqual(float(out["profitability_index"]), float(inflow / 1000), places=9)
        future = sum((Decimal("400") * Decimal("1.08") ** (4 - period) for period in range(1, 5)),
                     Decimal("0"))
        mirr = (future / Decimal("1000")) ** (Decimal("1") / Decimal("4")) - 1
        self.assertAlmostEqual(float(out["mirr"]), float(mirr), places=9)

    def test_E_pm_019__the_scenario_range_matches_the_test_discounting(self):
        flows = ["-1000", "400", "400", "400", "400"]
        out = LIBRARY["scenario_analysis"].impl({"cashflows": flows, "discount_rate": "0.10",
                                                 "rate_low": "0.05", "rate_high": "0.20"})
        self.assertAlmostEqual(float(out["npv_base"]), float(npv_of(flows, "0.10")), places=6)
        self.assertAlmostEqual(float(out["npv_at_low_rate"]), float(npv_of(flows, "0.05")), places=6)
        self.assertAlmostEqual(float(out["npv_at_high_rate"]), float(npv_of(flows, "0.20")), places=6)
        self.assertAlmostEqual(float(out["swing"]),
                               float(npv_of(flows, "0.05") - npv_of(flows, "0.20")), places=6)

    def test_E_pm_020__the_trend_matches_least_squares_fitted_in_the_test(self):
        values = [10, 12, 11, 14, 13, 16, 15, 18, 17, 20, 19, 22]
        out = LIBRARY["trend_forecast"].impl({"values": [str(v) for v in values],
                                              "missing_codes": [], "horizon": "3"})
        n = len(values)
        mean_x = (n + 1) / 2
        mean_y = sum(values) / n
        slope = (sum((i + 1 - mean_x) * (y - mean_y) for i, y in enumerate(values))
                 / sum((i + 1 - mean_x) ** 2 for i in range(n)))
        intercept = mean_y - slope * mean_x
        self.assertAlmostEqual(float(out["slope"]), slope, places=9)
        self.assertAlmostEqual(float(out["intercept"]), intercept, places=9)
        self.assertAlmostEqual(float(out["forecast_1"]), intercept + slope * (n + 1), places=6)
        self.assertAlmostEqual(float(out["forecast_3"]) - float(out["forecast_1"]), 2 * slope,
                               places=6)

    def test_E_pm_021__cpm_matches_a_forward_and_backward_pass_written_in_the_test(self):
        activities = [{"id": "A", "duration": "3", "predecessors": ""},
                      {"id": "B", "duration": "4", "predecessors": "A"},
                      {"id": "C", "duration": "2", "predecessors": "A"},
                      {"id": "D", "duration": "5", "predecessors": "B,C"}]
        out = LIBRARY["cpm_schedule"].impl({"estimate": "single", "activities": activities})
        mine = cpm_of(activities)
        self.assertEqual(int(out["project_duration"]), mine["duration"])
        for aid in ("A", "B", "C", "D"):
            self.assertEqual(int(out["es_" + aid]), mine["es"][aid], aid)
            self.assertEqual(int(out["ef_" + aid]), mine["ef"][aid], aid)
            self.assertEqual(int(out["float_" + aid]), mine["float"][aid], aid)
        self.assertEqual(int(out["critical_count"]),
                         sum(1 for aid in mine["float"] if mine["float"][aid] == 0))

    def test_E_pm_022__earned_value_indices_are_recomputed_from_the_declared_figures(self):
        out = LIBRARY["earned_value"].impl({"planned_value": "100000", "earned_value": "90000",
                                            "actual_cost": "95000",
                                            "budget_at_completion": "200000",
                                            "eac_method": "cpi"})
        self.assertAlmostEqual(float(out["spi"]), 90000 / 100000, places=9)
        self.assertAlmostEqual(float(out["cpi"]), 90000 / 95000, places=9)
        self.assertAlmostEqual(float(out["estimate_at_completion"]),
                               200000 / (90000 / 95000), places=6)
        self.assertAlmostEqual(float(out["tcpi"]), 110000 / 105000, places=9)

    def test_E_pm_023__resource_levelling_matches_a_greedy_simulation_in_the_test(self):
        capacity = 2
        activities = [("A", 2, 2, ""), ("B", 2, 2, "A"), ("C", 2, 1, "A"), ("D", 1, 1, "B,C")]
        usage, finishes, starts, pending = {}, {}, {}, list(activities)
        while pending:
            progressed = False
            for row in list(pending):
                aid, duration, demand, preds = row
                ready = [p.strip() for p in preds.split(",") if p.strip()]
                if not all(p in finishes for p in ready):
                    continue
                start = max((finishes[p] for p in ready), default=0)
                while any(usage.get(period, 0) + demand > capacity
                          for period in range(start, start + duration)):
                    start += 1
                for period in range(start, start + duration):
                    usage[period] = usage.get(period, 0) + demand
                starts[aid], finishes[aid] = start, start + duration
                pending.remove(row)
                progressed = True
            if not progressed:
                raise AssertionError("the test simulation stalled")
        out = LIBRARY["resource_leveling"].impl({
            "resources": [{"name": "crew", "capacity": "2"}],
            "activities": [{"id": aid, "duration": str(duration), "resource": "crew",
                            "demand": str(demand), "predecessors": preds}
                           for aid, duration, demand, preds in activities]})
        self.assertEqual(int(out["levelled_duration"]), max(finishes.values()))
        self.assertEqual(int(out["lv_start_C"]), starts["C"])
        self.assertEqual(int(out["overallocated_periods_after"]), 0)

    def test_E_pm_024__crashing_matches_the_hand_optimal_plan_on_both_paths(self):
        """A5/B4/C3: crashing B by two leaves A-C the longest path, so A pays one."""
        activities = [{"id": "A", "normal_duration": "5", "crash_duration": "3",
                       "crash_cost": "100", "predecessors": ""},
                      {"id": "B", "normal_duration": "4", "crash_duration": "2",
                       "crash_cost": "80", "predecessors": "A"},
                      {"id": "C", "normal_duration": "3", "crash_duration": "3",
                       "crash_cost": "0", "predecessors": "A"}]
        out = LIBRARY["project_crashing"].impl({"target_duration": "7", "activities": activities})
        self.assertEqual(int(out["normal_duration"]), 9)
        self.assertEqual(int(out["crash_periods_B"]), 2)
        self.assertEqual(int(out["crash_periods_A"]), 1)
        self.assertEqual(int(out["total_crash_cost"]), 80 + 50)
        mine = cpm_of([{"id": "A", "duration": out["final_duration_A"], "predecessors": ""},
                       {"id": "B", "duration": out["final_duration_B"], "predecessors": "A"},
                       {"id": "C", "duration": out["final_duration_C"], "predecessors": "A"}])
        self.assertEqual(mine["duration"], int(out["crashed_duration"]))
        self.assertEqual(int(out["crashed_duration"]), 7)

    def test_E_pm_025__the_calendar_schedule_skips_the_declared_non_working_periods(self):
        working = [0, 1, 2, 5, 6, 7, 10, 11, 12]
        activities = [("A", 2, ""), ("B", 2, "A"), ("C", 1, "B"), ("D", 1, "A")]
        finish, pending = {}, list(activities)
        while pending:
            for aid, duration, preds in list(pending):
                ready = [p.strip() for p in preds.split(",") if p.strip()]
                if not all(p in finish for p in ready):
                    continue
                start = max((finish[p] for p in ready), default=0)
                taken = [period for period in working if period >= start][:duration]
                finish[aid] = taken[-1] + 1
                pending.remove((aid, duration, preds))
        out = LIBRARY["calendar_schedule"].impl({
            "working_periods": "0,1,2,5,6,7,10,11,12",
            "activities": [{"id": aid, "duration": str(duration), "predecessors": preds}
                           for aid, duration, preds in activities]})
        self.assertEqual(int(out["project_duration"]), max(finish.values()))
        self.assertEqual(int(out["es_B"]), 2)
        self.assertEqual(int(out["ef_B"]), finish["B"])
        self.assertEqual(int(out["float_D"]), max(finish.values()) - finish["D"])

    def test_E_pm_026__the_shared_crew_sequences_the_lower_priority_project(self):
        out = LIBRARY["multi_project_schedule"].impl(server.PRESETS["multiproject"]["inputs"])
        self.assertEqual(int(out["finish_alpha"]), 4)
        self.assertEqual(int(out["start_beta_X"]), 4)
        self.assertEqual(int(out["start_beta_Y"]), 6)
        self.assertEqual(int(out["overall_duration"]), 8)
        self.assertEqual(int(out["delay_beta"]), int(out["start_beta_X"]))


    def test_E_pm_027__schedule_risk_percentiles_are_ordered_and_the_count_is_the_probability(self):
        out = LIBRARY["schedule_risk"].impl(server.PRESETS["schedrisk"]["inputs"])
        p50, p80, p90 = (float(out["p50_duration"]), float(out["p80_duration"]),
                         float(out["p90_duration"]))
        self.assertLessEqual(float(out["min_duration"]), p50)
        self.assertLessEqual(p50, p80)
        self.assertLessEqual(p80, p90)
        self.assertLessEqual(p90, float(out["max_duration"]))
        self.assertAlmostEqual(float(out["probability_within_target"]),
                               int(out["n_within_target"]) / int(out["iterations"]), places=9)

    def test_E_pm_028__schedule_risk_mean_sits_inside_the_analytic_bracket(self):
        """Triangular means: A 10/3, B 13/3, C 7/3; the max of two paths brackets the mean."""
        out = LIBRARY["schedule_risk"].impl(server.PRESETS["schedrisk"]["inputs"])
        mean = float(out["mean_duration"])
        self.assertGreaterEqual(mean, 10 / 3 + 13 / 3)
        self.assertLessEqual(mean, 10 / 3 + 13 / 3 + 7 / 3)
        self.assertGreaterEqual(float(out["sample_min_A"]), 2.0)
        self.assertLessEqual(float(out["sample_max_A"]), 5.0)

    def test_E_pm_029__the_decision_tree_rolls_back_to_the_hand_expected_values(self):
        out = LIBRARY["decision_tree"].impl(server.PRESETS["decisiontree"]["inputs"])
        self.assertAlmostEqual(float(out["ev_1"]), 0.6 * 100000 + 0.4 * -20000, places=6)
        self.assertAlmostEqual(float(out["ev_2"]), 0.7 * 40000 + 0.3 * 5000, places=6)
        self.assertEqual(int(out["best_index"]), 1)
        self.assertAlmostEqual(float(out["expected_value"]), 52000, places=6)
        self.assertAlmostEqual(float(out["loss_probability_1"]), 0.4, places=9)

    def test_E_pm_030__the_real_option_lattice_matches_a_binomial_built_in_the_test(self):
        mine, up, prob = lattice(100.0, 100.0, 0.30, 0.05, 5)
        out = LIBRARY["real_option"].impl(server.PRESETS["realoption"]["inputs"])
        self.assertAlmostEqual(float(out["option_value"]), mine, places=6)
        self.assertAlmostEqual(float(out["up_factor"]), up, places=9)
        self.assertAlmostEqual(float(out["risk_neutral_probability"]), prob, places=9)
        self.assertAlmostEqual(float(out["option_value"]), 14.789285, places=5)

    def test_E_pm_031__the_weighted_matrix_totals_are_the_declared_weights(self):
        out = LIBRARY["multi_criteria"].impl(server.PRESETS["mcda"]["inputs"])
        self.assertAlmostEqual(float(out["total_1"]), 0.6 * 9 + 0.4 * 5, places=9)
        self.assertAlmostEqual(float(out["total_2"]), 0.6 * 6 + 0.4 * 9, places=9)
        self.assertAlmostEqual(float(out["total_3"]), 0.6 * 7 + 0.4 * 7, places=9)
        self.assertEqual(int(out["best_index"]), 1)
        self.assertEqual((int(out["rank_1"]), int(out["rank_2"]), int(out["rank_3"])), (1, 2, 3))

    def test_E_pm_032__monte_carlo_is_exact_when_every_input_is_declared_fixed(self):
        fixed = {"model": "npv", "iterations": "200", "seed": "5", "discount_rate": "0.10",
                 "cashflows": [{"name": "outlay", "period": "0", "distribution": "fixed",
                                "value": "-1000"},
                               {"name": "y1", "period": "1", "distribution": "fixed",
                                "value": "400"},
                               {"name": "y2", "period": "2", "distribution": "fixed",
                                "value": "400"},
                               {"name": "y3", "period": "3", "distribution": "fixed",
                                "value": "400"}]}
        out = LIBRARY["monte_carlo"].impl(fixed)
        expected = float(npv_of(["-1000", "400", "400", "400"], "0.10"))
        for key in ("mean_result", "p10_result", "p50_result", "p90_result"):
            self.assertAlmostEqual(float(out[key]), expected, places=6, msg=key)
        self.assertEqual(float(out["probability_positive"]), 0.0)

    def test_E_pm_033__the_stochastic_mean_stays_within_monte_carlo_error_of_the_expectation(self):
        """E[triangular(200,400,600)] = 400, so the analytic NPV mean is -5.2592."""
        out = LIBRARY["monte_carlo"].impl(server.PRESETS["montecarlo"]["inputs"])
        expected = float(npv_of(["-1000", "400", "400", "400"], "0.10"))
        self.assertLess(abs(float(out["mean_result"]) - expected), 8.0)
        self.assertLessEqual(float(out["p10_result"]), float(out["p90_result"]))
        self.assertGreaterEqual(float(out["probability_positive"]), 0.0)
        self.assertLessEqual(float(out["probability_positive"]), 1.0)



class DeliveryTest(unittest.TestCase):
    """E-pm-034 ... E-pm-037 : the happy path, twice."""

    def test_E_pm_034__every_preset_delivers_and_every_check_passes(self):
        for key in TOOLS:
            result = Pipeline().run(server.PRESETS[key], lambda _s: True)
            self.assertEqual(result.status, "delivered", (key, result.blocked_reason))
            checks = result.appendix.get("tests") or []
            self.assertTrue(checks, key)
            for item in checks:
                passed = item[1] if isinstance(item, (list, tuple)) else bool(item)
                self.assertTrue(passed, (key, item))
            for row in result.appendix.get("ambiguities") or []:
                for field in ("question", "default_chosen", "impact"):
                    self.assertTrue(row.get(field), (key, field))

    def test_E_pm_035__the_same_inputs_twice_give_a_byte_identical_result(self):
        for key, method_id in METHODS.items():
            first, _ = run(method_id, server.PRESETS[key]["inputs"])
            second, _ = run(method_id, server.PRESETS[key]["inputs"])
            self.assertEqual(first, second, key)


    def test_E_pm_036__a_delivered_appendix_round_trips_through_json(self):
        result = Pipeline().run(server.PRESETS["cpm"], lambda _s: True)
        once = json.dumps(result.appendix, sort_keys=True, default=str)
        twice = json.dumps(json.loads(once), sort_keys=True)
        self.assertEqual(once, twice)

    def test_E_pm_037__the_delivered_report_carries_no_unresolved_token(self):
        document = completion.draft_bytes(complete("template_project_charter"))
        with zipfile.ZipFile(io.BytesIO(document)) as archive:
            text = archive.read("word/document.xml").decode("utf-8")
        for token in ("{{", "}}", "[insert", "<insert", "TODO", "TBD"):
            self.assertNotIn(token, text, token)


class BoundaryTest(unittest.TestCase):
    """E-pm-038 ... E-pm-041 : the edges, refused rather than defaulted."""

    def test_E_pm_038__an_empty_ledger_is_refused_and_a_milestone_is_legal(self):
        empty = dict(server.PRESETS["npv"], inputs={"rate": "0.10", "cashflows": []})
        result = Pipeline().run(empty, lambda _s: True)
        self.assertEqual(result.status, "blocked")
        self.assertIn("at least 2", result.blocked_reason or "")
        milestone = dict(server.PRESETS["cpm"], inputs={"estimate": "single", "activities": [
            {"id": "A", "duration": "0", "predecessors": ""}]})
        self.assertEqual(Pipeline().run(milestone, lambda _s: True).status, "delivered")

    def test_E_pm_039__identical_three_point_estimates_collapse_to_a_point_mass(self):
        inputs = {"iterations": "200", "seed": "3", "target_duration": "7", "activities": [
            {"id": "A", "optimistic": "3", "most_likely": "3", "pessimistic": "3",
             "predecessors": ""},
            {"id": "B", "optimistic": "4", "most_likely": "4", "pessimistic": "4",
             "predecessors": "A"}]}
        out = LIBRARY["schedule_risk"].impl(inputs)
        self.assertAlmostEqual(float(out["min_duration"]), 7.0, places=9)
        self.assertAlmostEqual(float(out["max_duration"]), 7.0, places=9)
        self.assertEqual(float(out["probability_within_target"]), 1.0)

    def test_E_pm_040__a_thousands_separator_is_refused_and_the_rate_is_taken_as_given(self):
        """C4: '1,200,000' is refused by name; a rate of 6 is not rescaled - it is disclosed."""
        thousands = dict(server.PRESETS["npv"],
                         inputs={"rate": "0.10", "cashflows": ["-1,200,000", "500,000",
                                                               "500,000"]})
        blocked = Pipeline().run(thousands, lambda _s: True)
        self.assertEqual(blocked.status, "blocked")
        self.assertIn("not a number", blocked.blocked_reason or "")
        as_given = Pipeline().run(dict(server.PRESETS["npv"],
                                       inputs={"rate": "6", "cashflows": ["-1000", "400",
                                                                          "400"]}),
                                  lambda _s: True)
        self.assertEqual(as_given.status, "delivered")
        said = " ".join(row["default_chosen"] for row in as_given.appendix["ambiguities"])
        self.assertIn("rate", said.lower())

    def test_E_pm_041__duplicate_activity_ids_are_refused(self):
        with self.assertRaises(DataError):
            LIBRARY["cpm_schedule"].impl({"estimate": "single", "activities": [
                {"id": "A", "duration": "2", "predecessors": ""},
                {"id": "A", "duration": "3", "predecessors": ""}]})



class RefusalTest(unittest.TestCase):
    """E-pm-042 ... E-pm-045 : a refusal names the input, and never returns a zero."""

    def test_E_pm_042__a_missing_probability_weight_or_volatility_blocks_the_run(self):
        tree = copy.deepcopy(server.PRESETS["decisiontree"]["inputs"])
        tree["tree"]["alternatives"][0]["node"]["branches"][0]["probability"] = ""
        cases = (
            ("realoption", dict(server.PRESETS["realoption"]["inputs"], volatility=""),
             "malformed"),
            ("mcda", dict(server.PRESETS["mcda"]["inputs"],
                          criteria=[{"name": "cost", "weight": ""},
                                    {"name": "speed", "weight": "0.4"}]),
             "malformed"),
            ("decisiontree", tree, "malformed"),
        )
        for key, inputs, expected in cases:
            preset = dict(server.PRESETS[key], inputs=inputs)
            result = Pipeline().run(preset, lambda _s: True)
            self.assertEqual(result.status, "blocked", key)
            self.assertIn(expected, (result.blocked_reason or "").lower(), key)

    def test_E_pm_043__a_blocked_run_carries_no_output_and_no_zero(self):
        preset = dict(server.PRESETS["mcda"],
                      inputs=dict(server.PRESETS["mcda"]["inputs"],
                                  criteria=[{"name": "cost", "weight": ""},
                                            {"name": "speed", "weight": "0.4"}]))
        result = Pipeline().run(preset, lambda _s: True)
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.appendix.get("outputs"))

    def test_E_pm_044__a_wrong_type_is_refused_not_coerced(self):
        preset = dict(server.PRESETS["npv"],
                      inputs={"rate": "0.10", "cashflows": "not a list"})
        result = Pipeline().run(preset, lambda _s: True)
        self.assertEqual(result.status, "blocked")
        self.assertIn("cashflows", result.blocked_reason or "")

    def test_E_pm_045__an_unknown_method_is_refused_by_name(self):
        result = Pipeline().run({"objective": "x", "method": "not_a_method", "inputs": {}},
                                lambda _s: True)
        self.assertEqual(result.status, "blocked")
        self.assertIn("not_a_method", result.blocked_reason or "")


class WorksheetTest(unittest.TestCase):
    """E-pm-046 ... E-pm-056 : the form, the vocabulary and the drafting path."""

    def test_E_pm_046__each_project_template_declares_exactly_one_form(self):
        for template in WORKSHEETS.values():
            forms = [name for name, registry in (("canvas", T.CANVAS_BLOCKS),
                                                 ("matrix", T.MATRIX_META))
                     if template in registry]
            self.assertEqual(len(forms), 1, (template, forms))

    def test_E_pm_047__the_declared_form_is_the_form_the_registry_renders(self):
        for template, form in FORMS.items():
            described = T.describe(template)
            self.assertEqual(described["form_kind"], form, template)
            if form == "canvas":
                self.assertTrue(described["blocks"], template)
                self.assertIn("blocks", described["input_help"], template)
            else:
                self.assertIn("rows", described["input_help"], template)
        self.assertTrue(matrix.layout_for("template_raci"))

    def test_E_pm_048__the_blocks_keep_the_declared_order_and_their_own_labels(self):
        for template in WORKSHEETS.values():
            profile = framework_profiles.get(template)
            described = T.describe(template)
            if not described["blocks"]:
                continue
            self.assertEqual([block["key"] for block in described["blocks"]],
                             [block["key"] for block in profile["blocks"]], template)
            for block, row in zip(described["blocks"], profile["blocks"]):
                self.assertEqual(block["label"], row["label"], template)
                self.assertNotIn("_", block["label"], template)

    def test_E_pm_049__no_block_borrows_another_blocks_cues(self):
        """Trap test for D-PM-01: one shared cue word tagged every block alike."""
        for template in WORKSHEETS.values():
            seen = {}
            for block in framework_profiles.get(template)["blocks"]:
                cues = tuple(sorted(block.get("cues") or []))
                self.assertGreaterEqual(len(cues), 2, (template, block["key"], cues))
                self.assertNotEqual(cues, ("evidence",), (template, block["key"]))
                seen.setdefault(cues, []).append(block["key"])
            for cues, keys in seen.items():
                self.assertEqual(len(keys), 1, (template, cues, keys))

    def test_E_pm_050__no_query_is_the_raw_block_key(self):
        """Trap test for D-PM-01: 'scope_in evidence' reached the providers."""
        for template in WORKSHEETS.values():
            for block in framework_profiles.get(template)["blocks"]:
                self.assertTrue(block.get("queries"), (template, block["key"]))
                for query in block["queries"]:
                    self.assertNotIn("_", query, (template, block["key"], query))
                    self.assertNotEqual(query, block["key"] + " evidence",
                                        (template, block["key"]))


    def test_E_pm_051__a_student_item_lands_in_the_block_it_names(self):
        result = complete("template_wbs", items=[
            {"block": "deliverables", "text": "The roster file migrated for every store"},
            {"block": "acceptance", "text": "The pilot passes a two-week parallel run"}])
        placed = {block["key"]: [item["text"] for item in block["items"]]
                  for block in result["blocks"]}
        self.assertIn("The roster file migrated for every store", placed["deliverables"])
        self.assertIn("The pilot passes a two-week parallel run", placed["acceptance"])
        self.assertEqual(len([text for texts in placed.values() for text in texts
                              if text.startswith("The roster file")]), 1)

    def test_E_pm_052__an_item_naming_an_unknown_block_is_not_forced_into_one(self):
        result = complete("template_wbs", items=[
            {"block": "no_such_block", "text": "An item with nowhere to go"}])
        placed = [item["text"] for block in result["blocks"] for item in block["items"]]
        self.assertNotIn("An item with nowhere to go", placed)

    def test_E_pm_053__a_unit_typed_worksheet_refuses_without_the_unit(self):
        for template, profile in framework_profiles.PROFILES.items():
            if profile.get("subject") != SUBJECT:
                continue
            if (profile.get("unit") or {}).get("field") != "unit":
                continue
            with self.assertRaises(ValueError) as caught:
                complete(template, unit="")
            self.assertIn("unit", str(caught.exception).lower(), template)

    def test_E_pm_054__a_block_with_no_source_is_a_named_gap_or_a_disclosed_background(self):
        result = complete("template_project_charter", sources=False)
        for block in result["blocks"]:
            kinds = [item["provenance"] for item in block["items"]]
            self.assertTrue(kinds or block.get("gap"), block["key"])
            if kinds == ["background"]:
                self.assertTrue(any("background" in note.lower()
                                    for note in result.get("notes") or [])
                                or block.get("gap") is None, block["key"])

    def test_E_pm_055__the_raci_matrix_still_holds_one_accountable_role_per_activity(self):
        request = copy.deepcopy(T.EXAMPLES["template_raci"])
        checks, _ = results_of("template_raci", request["inputs"])
        self.assertTrue(checks["every_activity_has_exactly_one_accountable"], checks)
        self.assertTrue(checks["every_activity_has_at_least_one_responsible"], checks)

    def test_E_pm_056__no_worksheet_output_carries_a_score_ranking_or_probability(self):
        for template in WORKSHEETS.values():
            _, out = results_of(template, copy.deepcopy(T.EXAMPLES[template])["inputs"])
            for forbidden in ("score", "overall", "ranking", "probability", "verdict"):
                self.assertNotIn(forbidden, out["analysis"], (template, forbidden))
                self.assertNotIn(forbidden, out["counts"], (template, forbidden))


def results_of(template, inputs):
    out = T.run_template(template, inputs)
    return {name: ok for name, ok in out["results"]}, out


class GateTest(unittest.TestCase):
    """E-pm-057 ... E-pm-062 : the page, the paper and the registry."""

    def test_E_pm_057__two_registry_kinds_are_still_declared_in_two_forms(self):
        """The K1 audit, ledgered as D-PM-03: marketing owns the fix, not this shelf.

        Half of it was closed on 2026-11-03: the customer journey map is a grid and is
        now declared only as one (D-MKT-04).  The SERVQUAL grid is still in both maps, and
        its tile is hidden from the marketing page until that is repaired (B-198), so the
        remaining declaration is recorded here rather than silently tolerated.
        """
        both = sorted(set(T.CANVAS_BLOCKS) & set(T.MATRIX_META))
        self.assertEqual(both, ["template_servqual"])
        for template in WORKSHEETS.values():
            self.assertNotIn(template, both)

    def test_E_pm_058__the_raci_profile_subject_agrees_with_its_catalogue_id(self):
        """Trap test for D-PM-02: the profile said 'management', the id said PM-10."""
        self.assertEqual(framework_profiles.get("template_raci")["subject"], SUBJECT)
        self.assertEqual(R.get("PM-10")["template"], "template_raci")

    def test_E_pm_059__no_tool_promises_a_diagram_the_product_cannot_draw(self):
        """A declared diagram is a geometry the renderer knows, never free text."""
        kinds = {"process", "tree", "matrix", "chain", "quadrant", "columns", "map"}
        for tool in page()["tools"]:
            declared = tool.get("diagram")
            if declared is None:
                continue
            self.assertIn(str(declared).lower(), kinds, tool["key"])

    def test_E_pm_060__the_paper_prints_no_specification_footer(self):
        document = completion.draft_bytes(complete("template_raci", unit=None))
        with zipfile.ZipFile(io.BytesIO(document)) as archive:
            text = archive.read("word/document.xml").decode("utf-8").lower()
        for furniture in ("specification hash", "can be re-run", "diagram to draw",
                          "method:", "version 1.0.0"):
            self.assertNotIn(furniture, text, furniture)

    def test_E_pm_061__the_served_page_offers_no_markdown_download(self):
        import re
        html = io.open("web/index.html", encoding="utf-8").read()
        self.assertEqual(re.findall(r'href="[^"]*\.md"', html), [])
        self.assertNotIn("downloadmarkdown", html.lower())

    def test_E_pm_062__the_shelf_guidance_names_the_read_only_records_honestly(self):
        guidance = page()["guidance"].lower()
        self.assertIn("read-only", guidance)
        for promise in ("fills in a wbs", "assigns responsibilities for you"):
            self.assertNotIn(promise, guidance, promise)

    def test_E_pm_064__every_block_tells_the_student_what_a_usable_answer_contains(self):
        """The authoring help: teaching text per block, and it can never read as data."""
        for template in WORKSHEETS.values():
            for block in framework_profiles.get(template)["blocks"]:
                advice = framework_profiles.advice_for(template, block["key"])
                self.assertGreaterEqual(len(advice["contains"]), 2, (template, block["key"]))
                self.assertGreaterEqual(len(advice["ask"]), 1, (template, block["key"]))
                self.assertTrue(advice["ask"][0].endswith("?"), (template, block["key"]))
                for line in advice["contains"] + advice["ask"]:
                    self.assertFalse(re.search(r"\d", line), (template, block["key"], line))

    def test_E_pm_065__the_served_form_carries_the_advice_and_never_writes_it_into_the_answer(self):
        described = framework_profiles.describe_extra("template_project_charter")
        self.assertTrue(all(block["advice"]["ask"] for block in described["blocks"]))
        html = io.open("web/index.html", encoding="utf-8").read()
        self.assertIn("function adviceHtml", html)
        self.assertIn("How to write this block", html)
        start = html.index("function adviceHtml")
        body = html[start:html.index("function evidenceBlocks", start)]
        # It may only render text: no assignment into an input, and no item construction.
        self.assertNotIn(".value =", body)
        self.assertNotIn("provenance", body)

    def test_E_pm_066__a_suggestion_never_becomes_an_item_or_changes_provenance(self):
        result = complete("template_wbs")
        for block in result["blocks"]:
            self.assertIn("advice", block)
            self.assertTrue(block["advice"]["ask"], block["key"])
            for item in block["items"]:
                self.assertNotIn(item["provenance"], ("suggested", "question", "advice"), block["key"])
        kinds = {item["provenance"] for block in result["blocks"] for item in block["items"]}
        self.assertTrue(kinds <= {"sourced", "student", "assumption", "background"}, kinds)
        # with no model lane configured there is no tailored text at all
        with mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": ""}, clear=False):
            self.assertEqual(complete("template_wbs")["blocks"][0]["advice"]["tailored"], "")

    def test_E_pm_067__a_model_question_is_validated_and_a_fabricated_one_is_dropped(self):
        from bp.product import prose
        self.assertEqual(prose.valid_suggestion("What evidence shows the roster handover?"),
                         "What evidence shows the roster handover?")
        for bad in ("The roster cuts overtime by 12 percent?",     # a number
                    "See https://example.org for the roster?",     # a link
                    "What does the shift roster migration cover",  # not a question
                    "What about " + " ".join(["very"] * 30) + "?",  # too long
                    "What does {{block}} need?"):                  # template braces
            self.assertIsNone(prose.valid_suggestion(bad), bad)
        answer = json.dumps({"questions": [
            {"block": "deliverables", "question": "What does the roster handover deliver?"},
            {"block": "acceptance", "question": "Which test proves it works by week 12?"}]})
        with mock.patch.dict(os.environ, {"BP_OPENGO_API_KEY": "test"}, clear=False), \
                mock.patch("bp.product.prose._call", return_value=answer):
            result = complete("template_wbs")
        tailored = {block["key"]: block["advice"]["tailored"] for block in result["blocks"]}
        self.assertEqual(tailored["deliverables"], "What does the roster handover deliver?")
        self.assertEqual(tailored["acceptance"], "")          # the fabricated one was dropped
        self.assertFalse(any(block["advice"]["model_used"] for block in result["blocks"]
                             if block["key"] == "acceptance"))
        # and it never reaches the paper
        document = completion.draft_bytes(result)
        with zipfile.ZipFile(io.BytesIO(document)) as archive:
            text = archive.read("word/document.xml").decode("utf-8")
        self.assertNotIn("What does the roster handover deliver?", text)

    def test_E_pm_068__the_balanced_scorecard_is_a_declared_t4_matrix_worksheet(self):
        """PM-01 stops being a read-only entry: it is a completing worksheet now."""
        template = T.TEMPLATES["template_balanced_scorecard"]
        self.assertEqual(template["tier"], "T4")
        self.assertEqual(template["registry_ids"], ["PM-01"])
        self.assertEqual(T.describe("template_balanced_scorecard")["form_kind"], "matrix")
        self.assertEqual(R.get("PM-01")["template"], "template_balanced_scorecard")
        offered = {sheet["catalogue_id"]: sheet for sheet in page()["worksheets"]}
        self.assertIn("PM-01", offered)
        self.assertTrue(offered["PM-01"]["draftable"])
        self.assertEqual(R.get("PM-01")["form"], "worksheet")

    def test_E_pm_069__the_scorecard_grid_passes_its_checks_and_computes_nothing(self):
        checks, out = results_of("template_balanced_scorecard",
                                 copy.deepcopy(T.EXAMPLES["template_balanced_scorecard"])["inputs"])
        self.assertTrue(all(checks.values()), checks)
        self.assertGreaterEqual(len(checks), 8)
        self.assertEqual(out["counts"]["n_rows"], 4)
        self.assertEqual(out["counts"]["n_columns"], 4)
        for forbidden in ("score", "weight", "index", "ranking", "verdict"):
            self.assertNotIn(forbidden, out["analysis"], forbidden)
            self.assertNotIn(forbidden, out["counts"], forbidden)
        # an empty cell is named, never filled
        request = copy.deepcopy(T.EXAMPLES["template_balanced_scorecard"])["inputs"]
        request["cells"].pop()
        checks, out = results_of("template_balanced_scorecard", request)
        self.assertTrue(checks["empty_cells_reported_not_filled"])
        self.assertEqual(out["counts"]["n_empty_cells"], 1)

    def test_E_pm_070__the_scorecard_paper_opens_with_its_four_perspectives(self):
        result = complete("template_balanced_scorecard")
        self.assertEqual(len(result["blocks"]), 4)
        lead = completion._lead_of(framework_profiles.get("template_balanced_scorecard")["outline"])
        self.assertGreaterEqual(len(lead.split()), 25)
        document = completion.draft_bytes(result)
        with zipfile.ZipFile(io.BytesIO(document)) as archive:
            text = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("A balanced scorecard steers one unit", text)
        for label in ("Financial perspective", "Customer perspective",
                      "Internal process perspective", "Organisational capacity perspective"):
            self.assertIn(label, text, label)

    def test_E_pm_063__every_framework_lead_is_authored_and_never_a_placeholder(self):
        """Trap test for D-PM-05. Three layers, because the defect had three.

        The data shipped `'lead': 'lead'` for eight profiles; the code printed it;
        and the paper carried the token. So this asserts the data is authored, the
        guard still fails closed on a stub, and the finished paper prints the
        paragraph instead of the token.
        """
        placeholders = ["template_project_charter", "template_wbs", "template_risk_register",
                        "template_stakeholder_plan", "template_lessons_learned"]
        canvases = ["template_business_model_canvas", "template_lean_canvas",
                    "template_value_proposition_canvas"]
        for template in placeholders + canvases:
            outline = framework_profiles.get(template)["outline"]
            self.assertNotEqual(str(outline.get("lead") or "").strip().lower(), "lead", template)
            lead = completion._lead_of(outline)
            self.assertGreaterEqual(len(lead.split()), 25, template)
            self.assertNotIn("'", lead.replace("'s ", "s "), template)   # no shell-out quoting
        # the guard itself still refuses a stub, for any profile added later
        self.assertEqual(completion._lead_of({"lead": "lead"}), "")
        self.assertEqual(completion._lead_of({}), "")
        # the finished paper prints the authored paragraph and no bare token
        for template in placeholders:
            lead = completion._lead_of(framework_profiles.get(template)["outline"])
            document = completion.draft_bytes(complete(template))
            with zipfile.ZipFile(io.BytesIO(document)) as archive:
                text = archive.read("word/document.xml").decode("utf-8")
            paragraphs = [re.sub(r"<[^>]+>", "", chunk).strip()
                          for chunk in text.split("</w:p>")]
            self.assertIn(lead.split(":")[0], text, template)          # the paragraph is present
            for paragraph in paragraphs:
                if paragraph:
                    self.assertNotEqual(paragraph.lower(), "lead", (template, paragraph))


if __name__ == "__main__":
    unittest.main()

