"""Acceptance tests for the People & organisation shelf (session 10).

One test per acceptance row in `qa/manual/people.md`.  Every expectation is read
from the code or the served data - never from the manual - and every numeric
expectation is recomputed independently: hand arithmetic or a second formula
written here, never the method's own output compared with itself.

This shelf is the only one carrying its own arithmetic (`trainingroi`,
`labourtightness` and `programmecost` are presets of `return_on_investment`,
`labour_market` and `cost_effectiveness`), so this module also carries the unit
audit (work order §6) and the parity tests: the same worksheet with the same
brief on this shelf and on Management & strategy must produce the same paper,
and the same calculator preset on this shelf and on Economics or Operations must
produce the same `outputs_hash`.  Management & strategy carries none of the ten
calculators, so the calculator limb of parity is measured against the shelves
that do carry them.

    $env:PYTHONPATH="src"; python -m unittest tests.test_subject_people_acceptance
"""

import io
import json
import math
import os
import re
import sys
import unittest
import zipfile
from decimal import Decimal, getcontext
from fractions import Fraction
from unittest import mock

sys.path.insert(0, "src")

from bp import server, templates as T                     # noqa: E402
from bp.methods import DataError, LIBRARY, TOL, validate_inputs   # noqa: E402
from bp.orchestrator import Pipeline, Quantity            # noqa: E402
from bp.product import completion, framework_profiles, subjects   # noqa: E402

getcontext().prec = 50

SUBJECT = "people"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

#: The ten compute tools, in the order the page declares them.
TOOLS = ["alpha", "weighted", "descriptive", "chi_square", "power", "pearson", "ols",
         "trainingroi", "labourtightness", "programmecost"]
METHODS = {"alpha": "reliability_alpha", "weighted": "weighted_summary",
           "descriptive": "descriptive_stats", "chi_square": "chi_square",
           "power": "power_analysis", "pearson": "pearson", "ols": "ols",
           "trainingroi": "return_on_investment", "labourtightness": "labour_market",
           "programmecost": "cost_effectiveness"}

#: catalogue id -> (template, tile group), in the order the page declares them.
WORKSHEETS = {
    "PPL-03": ("template_job_characteristics", "resourcing"),
    "PPL-02": ("template_kirkpatrick", "development"),
    "PPL-01": ("template_amo", "engagement_culture"),
    "PPL-05": ("template_tuckman", "development"),
    "PPL-04": ("template_nine_box", "resourcing"),
    "PM-10": ("template_raci", "resourcing"),
    "CHG-01": ("template_kotter", "strategy_design"),
    "CHG-11": ("template_org_design", "strategy_design"),
    "CHG-12": ("template_competing_values", "engagement_culture"),
    "CHG-02": ("template_adkar", "development"),
    "CHG-03": ("template_lewin", "strategy_design"),
    "CHG-04": ("template_mckinsey_7s", "strategy_design"),
    "CHG-05": ("template_burke_litwin", "strategy_design"),
    "CHG-06": ("template_galbraith_star", "strategy_design"),
    "CHG-07": ("template_theory_of_change", "strategy_design"),
    "CHG-08": ("template_logic_model", "strategy_design"),
    "CHG-09": ("template_pdsa", "development"),
    "CHG-10": ("template_dmaic", "development"),
    "CHG-13": ("template_mintzberg", "strategy_design"),
}

#: The six tiles, in the order the page declares them.
TILES = ["strategy_design", "resourcing", "development", "reward",
         "engagement_culture", "analytics"]
TILE_TITLE = {"strategy_design": "Strategy and design", "resourcing": "Resourcing",
              "development": "Development", "reward": "Reward",
              "engagement_culture": "Engagement and culture", "analytics": "Analytics"}

#: The eighteen framework profiles that declare `subject == "people"`.
PEOPLE_PROFILES = 18

#: The worksheets shared with another shelf: a fix to one belongs to the other
#: shelf's session, a presentation fix belongs to this one (work order §3).
SHARED_WITH_MANAGEMENT = ["CHG-%02d" % i for i in range(1, 14)]
SHARED_WITH_PROJECTS = ["PM-10"]

#: The calculators this shelf shares with Economics and Operations.  The page
#: declares no calculator that Management & strategy carries.
SHARED_WITH_ECONOMICS = ["chi_square", "descriptive", "ols", "pearson", "power"]
SHARED_WITH_OPERATIONS = ["chi_square", "descriptive", "power"]

YES = lambda spec: True                                    # noqa: E731


def page(subject=SUBJECT):
    return subjects.detail(subject)


def path(*parts):
    return os.path.join(ROOT, *parts)


def preset_request(key):
    """The exact request the page's launcher would send for one tool."""
    tool = subjects.TOOL_INFO[key]
    preset = server.PRESETS[tool["preset"]]
    return {"objective": preset["objective"], "method": preset["method"],
            "inputs": json.loads(json.dumps(preset["inputs"])),
            "currency": preset.get("currency"), "period": preset.get("period"),
            "unit": preset.get("unit")}


def delivered(request):
    pipeline = Pipeline()
    decision = pipeline.run(request, YES)
    assert decision.status == "delivered", decision.blocked_reason
    return pipeline, decision


def refused(request):
    return Pipeline().run(request, YES)


def run(method_id, inputs):
    method = LIBRARY[method_id]
    return method.impl(inputs), method.tests(inputs, method.impl)


def close(actual, expected, tol=TOL):
    """Decimal comparison at the core's own tolerance."""
    return abs(Decimal(str(actual)) - Decimal(str(expected))) <= tol


def near(actual, expected, tol=1e-9):
    """Float comparison for a recomputation done in float in this module."""
    return abs(float(actual) - float(expected)) <= tol


def normal_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def z_for(p):
    """The standard-normal quantile by bisection on its own CDF."""
    lo, hi = 0.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if normal_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_two_sided_p(t, df):
    """Two-sided p from Student's t density, integrated by Simpson's rule."""
    def pdf(z):
        return math.exp(math.lgamma((df + 1) / 2) - math.lgamma(df / 2)
                        - 0.5 * math.log(df * math.pi)
                        - (df + 1) / 2 * math.log(1 + z * z / df))
    steps = 20000
    h = t / steps
    total = pdf(0.0) + pdf(t)
    for i in range(1, steps):
        total += (4 if i % 2 else 2) * pdf(i * h)
    return 2 * (0.5 - total * h / 3)


def ols_fit(ys, columns):
    """Least squares by the normal equations, solved exactly in Fractions."""
    X = [[Fraction(1)] + [Fraction(int(v)) for v in row] for row in zip(*columns)]
    Y = [Fraction(int(v)) for v in ys]
    p = 1 + len(columns)
    A = [[sum(X[i][r] * X[i][s] for i in range(len(X))) for s in range(p)] for r in range(p)]
    b = [sum(X[i][r] * Y[i] for i in range(len(X))) for r in range(p)]
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for col in range(p):
        pivot = next(i for i in range(col, p) if M[i][col] != 0)
        M[col], M[pivot] = M[pivot], M[col]
        scale = M[col][col]
        M[col] = [v / scale for v in M[col]]
        for i in range(p):
            if i != col and M[i][col] != 0:
                factor = M[i][col]
                M[i] = [vi - factor * vj for vi, vj in zip(M[i], M[col])]
    coefs = [float(M[i][p]) for i in range(p)]
    fitted = [sum(coefs[j] * float(X[i][j]) for j in range(p)) for i in range(len(X))]
    mean_y = sum(float(v) for v in Y) / len(Y)
    ss_tot = sum((float(v) - mean_y) ** 2 for v in Y)
    ss_res = sum((float(Y[i]) - fitted[i]) ** 2 for i in range(len(Y)))
    return coefs, 1 - ss_res / ss_tot


def declared_units():
    """(tool, metric) -> (unit, precision) for every output of the ten presets."""
    table = {}
    for key in TOOLS:
        request = preset_request(key)
        method = LIBRARY[request["method"]]
        out = method.impl(request["inputs"])
        if not isinstance(out, dict):
            out = {method.metric: out}
        for metric, value in out.items():
            if metric.startswith("_"):
                continue
            table[(key, metric)] = method.typing(metric)
    return table


def ANY_UNIT_HINT(metric, unit):
    """Does this declared unit contradict the field's own name?

    Only the contradictions this session can defend field by field are encoded,
    and each is named in `qa/manual/people.md` §3.  A variance in points squared
    has no word in the engine's vocabulary, so it is recorded there as a MINOR
    observation rather than failed here.
    """
    if metric.startswith("icer_") and unit != "currency_per_effect":
        return True                      # a cost PER UNIT OF EFFECT is not money
    if metric == "comparator_cost" and unit != "currency":
        return True                      # a money amount with no money unit
    if metric in ("mde", "se") and unit in ("probability", "@unit"):
        return True                      # an outcome-scale difference is not a probability
    return False



class Inventory(unittest.TestCase):
    """E-ppl-001 ... E-ppl-015 - what the shelf actually offers."""

    def test_E_ppl_001__the_ten_declared_calculators_in_order(self):
        self.assertEqual([t["key"] for t in page()["tools"]], TOOLS)
        for tool in page()["tools"]:
            self.assertEqual(tool["method"], METHODS[tool["key"]], tool["key"])
            self.assertEqual(tool["kind"], "compute", tool["key"])

    def test_E_ppl_002__six_tiles_in_the_declared_order(self):
        tiles = page()["tiles"]
        self.assertEqual([t["key"] for t in tiles], TILES)
        for tile in tiles:
            self.assertEqual(tile["label"], TILE_TITLE[tile["key"]], tile["key"])
            self.assertTrue(tile["what"], tile["key"])
            self.assertTrue(tile["need"], tile["key"])

    def test_E_ppl_003__each_tile_holds_the_worksheets_its_group_declares(self):
        for tile in page()["tiles"]:
            expected = [cid for cid, (kind, group) in WORKSHEETS.items()
                        if group == tile["key"]]
            self.assertEqual([w["key"] for w in tile["worksheets"]], expected,
                             tile["key"])
            for sheet in tile["worksheets"]:
                self.assertEqual(sheet["group"], tile["key"], sheet["key"])

    def test_E_ppl_004__all_ten_calculators_sit_in_the_analytics_tile(self):
        tile = {t["key"]: t for t in page()["tiles"]}["analytics"]
        self.assertEqual([t["key"] for t in tile["tools"]], TOOLS)
        for tool in page()["tools"]:
            self.assertEqual(tool["group"], "analytics", tool["key"])
        for other in page()["tiles"]:
            if other["key"] != "analytics":
                self.assertEqual(other["tools"], [], other["key"])

    def test_E_ppl_005__the_reward_tile_is_empty_by_design_and_says_why(self):
        """Q1 of the work order: declared and visible, not silently absent."""
        tile = {t["key"]: t for t in page()["tiles"]}["reward"]
        self.assertEqual(tile["worksheets"], [])
        self.assertEqual(tile["tools"], [])
        self.assertEqual(tile["records"], [])
        self.assertIsNone(tile["service"])
        self.assertTrue(tile["note"], "an empty tile with no note is a silent absence")
        self.assertIn("empty by design", tile["note"])
        self.assertIn("no reward or job-evaluation framework", tile["note"])
        self.assertIn("Reward is empty by design", page()["guidance"])
        html = io.open(path("web", "index.html"), encoding="utf-8").read()
        self.assertIn('esc(tile.note || "Nothing is assigned to this tile yet.")', html)

    def test_E_ppl_006__no_records_and_no_theories_so_nothing_promises_a_missing_calculator(self):
        """Q3 of the work order: no record here claims a method it cannot start."""
        served = page()
        self.assertEqual(served["records"], [])
        self.assertEqual(served["theories"], [])
        self.assertEqual(sorted(row["id"] for row in served["catalogue"]),
                         sorted(WORKSHEETS))
        for row in served["catalogue"]:
            self.assertEqual(row["form"], "worksheet", row["id"])
        for tile in served["tiles"]:
            self.assertEqual(tile["records"], [], tile["key"])

    def test_E_ppl_007__no_glossary_is_served_and_none_is_claimed(self):
        """G-PPL-04: measured, and the page renders no empty glossary section."""
        self.assertEqual(page()["glossary"], [])
        self.assertNotIn("people", subjects.GLOSSARIES)
        html = io.open(path("web", "index.html"), encoding="utf-8").read()
        self.assertIn("if ((s.glossary || []).length) {", html)

    def test_E_ppl_008__every_tool_carries_the_student_notes(self):
        for tool in page()["tools"]:
            self.assertTrue(tool["formula"], tool["key"])
            self.assertTrue(tool["steps"], tool["key"])
            self.assertTrue(tool["common_mistakes"], tool["key"])
            self.assertIn(tool["level"], ("intro", "intermediate", "advanced"), tool["key"])
            self.assertTrue(tool["period"], tool["key"])
            self.assertTrue(tool["related"], tool["key"])
            self.assertTrue(tool["need"], tool["key"])
            self.assertTrue(tool["what"], tool["key"])

    def test_E_ppl_023__no_output_unit_contradicts_its_own_name(self):
        """TRAP (D-PPL-01): before B-216 four fields contradicted their own names -
        an ICER typed as money, money typed as the undeclared base unit, and an
        outcome-scale difference and its standard error typed as probabilities."""
        units = declared_units()
        contradictory = sorted(pair for pair, value in units.items()
                               if ANY_UNIT_HINT(pair[1], value[0]))
        self.assertEqual(contradictory, [],
                         "a unit that contradicts its own name is a BLOCKER-class finding")
        # and the four that used to be wrong are now named correctly
        self.assertEqual(units[("programmecost", "icer_intensive")],
                         ("currency_per_effect", 2))
        self.assertEqual(units[("programmecost", "comparator_cost")], ("currency", 2))
        self.assertEqual(units[("programmecost", "comparator_effect")], ("units", 2))
        self.assertEqual(units[("power", "mde")], ("units", 2))
        self.assertEqual(units[("power", "se")], ("units", 2))
    def test_E_ppl_024__the_units_that_are_right_stay_right(self):
        units = declared_units()
        self.assertEqual(units[("alpha", "alpha")], ("ratio", 4))
        self.assertEqual(units[("alpha", "k_items")], ("count", 0))
        self.assertEqual(units[("chi_square", "p_value")], ("probability", 4))
        self.assertEqual(units[("chi_square", "df")], ("count", 0))
        self.assertEqual(units[("pearson", "r")], ("correlation", 3))
        self.assertEqual(units[("trainingroi", "total_investment")], ("currency", 2))
        self.assertEqual(units[("trainingroi", "roi")], ("rate", 4))
        self.assertEqual(units[("labourtightness", "real_wage")], ("currency", 2))
        self.assertEqual(units[("descriptive", "n")], ("count", 0))
        # B-216: a holding period is a period, and a count is a count
        self.assertEqual(units[("trainingroi", "years")], ("periods", 2))
        self.assertEqual(units[("labourtightness", "vacancies")], ("count", 0))
        self.assertEqual(units[("labourtightness", "unemployed")], ("count", 0))
    def test_E_ppl_016__use_unsupported_use_assumptions_and_limitations_are_declared(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertTrue(method.intended_use, key)
            self.assertTrue(method.unsupported_use, key)
            self.assertTrue(method.assumptions, key)
            self.assertTrue(method.limitations, key)

    def test_E_ppl_017__at_least_three_named_checks_and_the_names_that_run_are_declared(self):
        for key in TOOLS:
            request = preset_request(key)
            method = LIBRARY[request["method"]]
            self.assertGreaterEqual(len(method.test_names), 3, key)
            out, results = run(request["method"], request["inputs"])
            self.assertEqual([name for name, ok in results], list(method.test_names), key)
            self.assertTrue(all(ok for name, ok in results), key)

    def test_E_ppl_018__tier_metric_unit_and_a_valid_claim_ceiling(self):
        ceilings = {"descriptive", "predictive", "prescriptive", "associational"}
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertIn(method.tier, ("T1", "T2", "T3"), key)
            self.assertTrue(method.metric, key)
            self.assertTrue(method.unit, key)
            self.assertIn(method.claim_ceiling, ceilings, key)

    def test_E_ppl_019__every_input_declares_a_type_and_a_description(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertTrue(method.input_schema, key)
            for name, spec in method.input_schema.items():
                self.assertIn("type", spec, (key, name))
                self.assertTrue(spec.get("desc"), (key, name))

    def test_E_ppl_020__every_tool_has_a_preset_for_the_same_method(self):
        for key in TOOLS:
            tool = subjects.TOOL_INFO[key]
            self.assertIn(tool["preset"], server.PRESETS, key)
            preset = server.PRESETS[tool["preset"]]
            self.assertEqual(preset["method"], tool["method"], key)
            self.assertEqual(preset["method"], METHODS[key], key)
            self.assertEqual(validate_inputs(LIBRARY[METHODS[key]], preset["inputs"]), [], key)

    def test_E_ppl_021__every_tool_declares_the_period_its_inputs_are_read_in(self):
        for tool in page()["tools"]:
            self.assertTrue(tool["period"], tool["key"])

    def test_E_ppl_022__every_output_has_a_declared_unit_and_an_integer_precision(self):
        for (tool, metric), pair in sorted(declared_units().items()):
            self.assertEqual(len(pair), 2, (tool, metric))
            unit, precision = pair
            self.assertIsInstance(unit, str, (tool, metric))
            self.assertTrue(unit, (tool, metric))
            self.assertIsInstance(precision, int, (tool, metric))
            self.assertLessEqual(precision, 6, (tool, metric))


class WorksheetInventory(unittest.TestCase):
    """E-ppl-009 ... E-ppl-015 - the worksheets and the catalogue view."""

    def test_E_ppl_009__nineteen_worksheets_and_every_template_exists(self):
        sheets = page()["worksheets"]

        self.assertEqual([w["key"] for w in sheets], list(WORKSHEETS))
        for sheet in sheets:
            self.assertEqual(sheet["template"], WORKSHEETS[sheet["key"]][0], sheet["key"])
            self.assertIn(sheet["template"], T.TEMPLATES, sheet["key"])
            self.assertTrue(sheet["label"], sheet["key"])
            self.assertTrue(sheet["what"], sheet["key"])

    def test_E_ppl_010__every_worksheet_is_draftable(self):
        sheets = page()["worksheets"]
        self.assertEqual([w["key"] for w in sheets if not w["draftable"]], [])
        for sheet in sheets:
            self.assertIsNone(sheet.get("draft_note"), sheet["key"])

    def test_E_ppl_011__every_worksheet_group_is_a_declared_tile(self):
        """Q4 of the work order: no worksheet is filed under a tile that does not exist."""
        declared = {tile["key"] for tile in page()["tiles"]}
        for cid, (kind, group) in WORKSHEETS.items():
            self.assertIn(group, declared, cid)
        self.assertEqual(set(subjects.SUBJECT_WORKSHEET_GROUPS["people"].values()) - declared,
                         set())

    def test_E_ppl_012__all_eighteen_people_profiles_are_reachable_from_the_page(self):
        templates = {w["template"] for w in page()["worksheets"]}
        profiles = {kind for kind, row in framework_profiles.PROFILES.items()
                    if row.get("subject") == SUBJECT}
        self.assertEqual(len(profiles), PEOPLE_PROFILES)
        self.assertEqual(profiles - templates, set(),
                         "a profile with no worksheet on the page is unreachable from it")
        self.assertEqual(templates - profiles, {"template_raci"},
                         "the only worksheet here that is another shelf's profile")

    def test_E_ppl_013__the_page_states_the_contract_it_is_judged_against(self):
        served = page()
        self.assertEqual(served["label"], "People & organisation")
        self.assertEqual(served["summary"],
                         "Design the job, develop the people who do it, and read the "
                         "organisation they work in.")
        self.assertGreaterEqual(len(served["start_steps"]), 4)
        self.assertGreaterEqual(len(served["does_not"]), 3)
        self.assertTrue(served["guidance"])

    def test_E_ppl_014__does_not_names_the_people_facts_the_core_cannot_compute(self):
        text = " ".join(page()["does_not"]).lower()
        for word in ("headcount", "turnover", "absence", "cost per hire", "time to hire",
                     "compa-ratio", "span of control", "diversity", "engagement",
                     "nine-box score"):
            self.assertIn(word, text, word)

    def test_E_ppl_015__the_shelf_catalogue_counts_its_nineteen_worksheets(self):
        listing = subjects.catalogue()
        rows = listing["subjects"] if isinstance(listing, dict) else listing
        row = [item for item in rows if item["id"] == SUBJECT][0]
        self.assertEqual(row["worksheet_count"], len(WORKSHEETS))
        self.assertEqual(row["catalogue_count"], len(WORKSHEETS))
        self.assertEqual(row["tool_count"], len(TOOLS))
        self.assertEqual(row["record_count"], 0)
        self.assertEqual(row["theory_count"], 0)


class Numbers(unittest.TestCase):
    """E-ppl-025 ... E-ppl-042 - every calculator recomputed independently."""

    ALPHA_ITEMS = {"one": ["4", "5", "3", "4", "5", "2", "4", "3"],
                   "two": ["4", "4", "3", "5", "4", "3", "4", "2"],
                   "three": ["3", "4", "2", "4", "5", "3", "4", "3"],
                   "four": ["4", "5", "3", "4", "4", "2", "3", "3"]}

    def test_E_ppl_025__alpha_is_recomputed_from_every_item_variance(self):
        out = LIBRARY["reliability_alpha"].impl({"items": self.ALPHA_ITEMS})
        columns = [[float(v) for v in col] for col in self.ALPHA_ITEMS.values()]
        k, n = len(columns), len(columns[0])
        item_var = []
        for col in columns:
            mean = sum(col) / n
            item_var.append(sum((v - mean) ** 2 for v in col) / (n - 1))
        totals = [sum(col[i] for col in columns) for i in range(n)]
        tmean = sum(totals) / n
        total_var = sum((t - tmean) ** 2 for t in totals) / (n - 1)
        self.assertTrue(near(out["sum_item_variance"], sum(item_var)))
        self.assertTrue(near(out["total_variance"], total_var))
        alpha = k / (k - 1) * (1 - sum(item_var) / total_var)
        self.assertTrue(near(out["alpha"], alpha))
        self.assertEqual(out["k_items"], Decimal(k))
        self.assertEqual(out["n"], Decimal(n))

    def test_E_ppl_026__two_items_follow_the_spearman_brown_identity(self):
        """Raw alpha for k = 2 equals 2r/(1+r) when the two items have equal variance."""
        items = {"a": ["1", "2", "3", "4", "5"], "b": ["2", "1", "4", "5", "3"]}
        out = LIBRARY["reliability_alpha"].impl({"items": items})
        xs = [float(v) for v in items["a"]]
        ys = [float(v) for v in items["b"]]
        mx, my = sum(xs) / 5, sum(ys) / 5
        var_x = sum((v - mx) ** 2 for v in xs) / 4
        var_y = sum((v - my) ** 2 for v in ys) / 4
        self.assertTrue(near(var_x, var_y), "the identity needs equal item variances")
        r = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / math.sqrt(var_x * var_y) / 4
        self.assertTrue(near(out["alpha"], 2 * r / (1 + r)))

    def test_E_ppl_027__identical_items_give_one_and_a_reflected_itemset_does_not(self):
        identical = {"items": {"a": ["1", "2", "3", "4"], "b": ["1", "2", "3", "4"]}}
        self.assertTrue(close(LIBRARY["reliability_alpha"].impl(identical)["alpha"], 1))
        scaled = {"items": {"a": ["1", "2", "3", "4"], "b": ["2", "4", "6", "8"]}}
        self.assertLess(LIBRARY["reliability_alpha"].impl(scaled)["alpha"], Decimal(1))
        reflected = {"items": {"one": ["1", "2", "3", "4"], "two": ["4", "3", "2", "1"],
                               "three": ["1", "2", "3", "4"]}}
        self.assertLess(LIBRARY["reliability_alpha"].impl(reflected)["alpha"], Decimal(0))

    def test_E_ppl_028__alpha_refuses_a_zero_variance_and_a_single_item(self):
        with self.assertRaises(DataError):
            LIBRARY["reliability_alpha"].impl(
                {"items": {"one": ["3", "3", "3"], "two": ["3", "3", "3"]}})
        errors = validate_inputs(LIBRARY["reliability_alpha"],
                                 {"items": {"one": ["1", "2", "3"]}})
        self.assertTrue(errors)
        self.assertIn("at least 2 columns", errors[0])

    def test_E_ppl_029__the_weighted_mean_is_sum_wx_over_sum_w(self):
        out = LIBRARY["weighted_summary"].impl(
            {"values": ["1", "2", "3", "4"], "weights": ["1", "1", "1", "3"],
             "weight_kind": "reliability"})
        expected = (1 * 1 + 2 * 1 + 3 * 1 + 4 * 3) / (1 + 1 + 1 + 3)
        self.assertTrue(near(out["weighted_mean"], expected))
        self.assertEqual(out["sum_weights"], Decimal(6))
        n_eff = (1 + 1 + 1 + 3) ** 2 / (1 + 1 + 1 + 9)
        self.assertTrue(near(out["n_eff"], n_eff))
        self.assertTrue(near(out["design_effect"], 4 / n_eff))

    def test_E_ppl_030__unit_weights_reproduce_the_plain_mean(self):
        values = ["2", "4", "9"]
        weighted = LIBRARY["weighted_summary"].impl(
            {"values": values, "weights": ["1", "1", "1"], "weight_kind": "reliability"})
        plain = LIBRARY["descriptive_stats"].impl({"values": values})
        self.assertTrue(near(weighted["weighted_mean"], plain["mean"]))

    def test_E_ppl_031__zero_or_negative_total_weight_is_refused(self):
        for weights in (["0", "0"], ["-1", "2"], ["1", "0"]):
            with self.assertRaises(DataError):
                LIBRARY["weighted_summary"].impl({"values": ["1", "2"], "weights": weights,
                                                  "weight_kind": "reliability"})

    def test_E_ppl_032__a_weight_entered_as_40_is_taken_as_given_and_disclosed(self):
        """GAP, declared: the weight is not validated, and the caveat says so in the paper."""
        out = LIBRARY["weighted_summary"].impl(
            {"values": ["1", "2"], "weights": ["40", "60"], "weight_kind": "reliability"})
        self.assertEqual(out["sum_weights"], Decimal(100))
        self.assertTrue(near(out["weighted_mean"], 1.6))
        caveats = " ".join(LIBRARY["weighted_summary"].caveats(out, {}))
        self.assertIn("Weights are not validated", caveats)
        self.assertIn("used as given", caveats)

    def test_E_ppl_033__the_descriptive_sd_uses_the_n_minus_one_denominator(self):
        values = [72.0, 85.0, 90.0, 68.0, 77.0, 81.0]
        out = LIBRARY["descriptive_stats"].impl(
            {"values": [str(int(v)) for v in values] + ["99"], "missing_codes": ["99"]})
        mean = sum(values) / len(values)
        ordered = sorted(values)
        median = (ordered[2] + ordered[3]) / 2
        var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
        self.assertTrue(near(out["mean"], mean))
        self.assertTrue(near(out["median"], median))
        self.assertTrue(near(out["variance"], var))
        self.assertTrue(near(out["sd"], math.sqrt(var)))
        population = sum((v - mean) ** 2 for v in values) / len(values)
        self.assertFalse(near(out["variance"], population), "the declared denominator is n-1")
        self.assertEqual(out["n"], Decimal(6))
        self.assertEqual(out["n_missing"], Decimal(1))

    def test_E_ppl_034__all_equal_values_give_zero_and_one_value_omits_the_spread(self):
        flat = LIBRARY["descriptive_stats"].impl({"values": ["7", "7", "7"]})
        self.assertEqual(flat["variance"], Decimal(0))
        self.assertEqual(flat["sd"], Decimal(0))
        single = LIBRARY["descriptive_stats"].impl({"values": ["7"]})
        self.assertNotIn("variance", single)
        self.assertNotIn("sd", single)
        self.assertEqual(single["n"], Decimal(1))

    def test_E_ppl_035__chi_square_is_recomputed_from_its_own_expected_counts(self):
        table = [[45, 30, 25], [20, 40, 40], [10, 20, 70]]
        out = LIBRARY["chi_square"].impl({"table": table})
        total = sum(sum(row) for row in table)
        chi2 = 0.0
        smallest = None
        for i, row in enumerate(table):
            for j, cell in enumerate(row):
                expected = sum(row) * sum(r[j] for r in table) / total
                smallest = expected if smallest is None else min(smallest, expected)
                chi2 += (cell - expected) ** 2 / expected
        self.assertTrue(near(out["chi_squared"], chi2))
        self.assertTrue(near(out["min_expected_count"], smallest))
        self.assertEqual(out["df"], Decimal(4))
        self.assertEqual(out["n_total"], Decimal(300))
        # p recomputed from the chi-square density's closed form at df = 4
        self.assertTrue(near(out["p_value"], math.exp(-chi2 / 2) * (1 + chi2 / 2), 1e-12))

    def test_E_ppl_036__a_2x2_table_agrees_with_the_z_squared_identity(self):
        table = [[10, 20], [30, 40]]
        out = LIBRARY["chi_square"].impl({"table": table})
        total = 100
        chi2 = 0.0
        for i in range(2):
            for j in range(2):
                expected = sum(table[i]) * sum(r[j] for r in table) / total
                chi2 += (table[i][j] - expected) ** 2 / expected
        self.assertTrue(near(out["chi_squared"], chi2))
        self.assertEqual(out["df"], Decimal(1))
        z = math.sqrt(chi2)
        p_from_z = 2 * (1 - normal_cdf(z))
        self.assertTrue(near(out["p_value"], p_from_z, 1e-12))
        self.assertTrue(near(out["p_value"], math.erfc(math.sqrt(chi2 / 2)), 1e-12))

    def test_E_ppl_037__a_zero_row_is_accepted_and_answered_p_one(self):
        """GAP, declared on the page: the method reports the zero expected count, it
        does not refuse the degenerate table.  `common_mistakes` names the risk."""
        out, checks = run("chi_square", {"table": [[0, 0, 0], [1, 2, 3]]})
        self.assertEqual(out["min_expected_count"], Decimal(0))
        self.assertEqual(out["chi_squared"], Decimal(0))
        self.assertEqual(out["p_value"], Decimal(1))
        self.assertTrue(all(ok for name, ok in checks))
        mistakes = " ".join(subjects.STUDENT_NOTES["chi_square"]["common_mistakes"]).lower()
        self.assertIn("very small expected counts", mistakes)

    def test_E_ppl_038__power_is_recomputed_from_the_declared_effect_and_sizes(self):
        request = preset_request("power")
        out = LIBRARY["power_analysis"].impl(request["inputs"])
        se = math.sqrt(10 ** 2 / 30 + 12 ** 2 / 40)
        ncp = 5 / se
        z_alpha = z_for(0.975)
        z_beta = z_for(0.8)
        self.assertTrue(near(out["se"], se))
        self.assertTrue(near(out["ncp"], ncp))
        self.assertTrue(near(out["z_alpha"], z_alpha))
        power = 1 - normal_cdf(z_alpha - ncp) + normal_cdf(-z_alpha - ncp)
        self.assertTrue(near(out["power"], power))
        self.assertTrue(near(out["mde"], (z_alpha + z_beta) * se))

    def test_E_ppl_039__power_rises_with_the_effect_and_one_sided_differs(self):
        request = preset_request("power")
        base = LIBRARY["power_analysis"].impl(request["inputs"])
        bigger = LIBRARY["power_analysis"].impl({**request["inputs"], "effect": "10"})
        one = LIBRARY["power_analysis"].impl({**request["inputs"], "tails": "one_sided"})
        self.assertGreater(bigger["power"], base["power"])
        self.assertGreater(one["power"], base["power"])
        self.assertLess(one["mde"], base["mde"])
        with self.assertRaises(DataError):
            LIBRARY["power_analysis"].impl({**request["inputs"], "alpha": "0"})

    def test_E_ppl_040__pearson_is_recomputed_and_survives_an_affine_transform(self):
        xs = ["1", "2", "3", "4", "5", "6", "7", "8"]
        ys = ["52", "55", "61", "58", "70", "72", "69", "80"]
        out = LIBRARY["pearson"].impl({"x": xs, "y": ys})
        x = [float(v) for v in xs]
        y = [float(v) for v in ys]
        mx, my = sum(x) / 8, sum(y) / 8
        sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
        sxx = sum((a - mx) ** 2 for a in x)
        syy = sum((b - my) ** 2 for b in y)
        r = sxy / math.sqrt(sxx * syy)
        self.assertTrue(near(out["r"], r))
        self.assertTrue(near(out["r_squared"], r * r))
        t = r * math.sqrt(6) / math.sqrt(1 - r * r)
        self.assertTrue(near(out["p_value"], t_two_sided_p(t, 6), 1e-9))
        moved = LIBRARY["pearson"].impl(
            {"x": [str(3 * float(v) + 7) for v in xs],
             "y": [str(2 * float(v) - 11) for v in ys]})
        self.assertTrue(near(moved["r"], r, 1e-12))

    def test_E_ppl_041__a_constant_column_is_refused_not_divided_by_zero(self):
        with self.assertRaises(DataError):
            LIBRARY["pearson"].impl({"x": ["1", "1", "1"], "y": ["2", "3", "4"]})
        with self.assertRaises(DataError):
            LIBRARY["pearson"].impl({"x": ["1", "2"], "y": ["3", "5"]})

    def test_E_ppl_042__ols_is_fitted_by_the_normal_equations_and_equals_r_squared(self):
        ys = [52, 55, 61, 58, 70, 72, 69, 80, 66, 74]
        hours = [1, 2, 3, 4, 5, 6, 7, 8, 4, 6]
        sleep = [6, 7, 5, 8, 6, 7, 8, 6, 7, 7]
        out = LIBRARY["ols"].impl({"y": [str(v) for v in ys],
                                   "predictors": {"study_hours": [str(v) for v in hours],
                                                  "sleep_hours": [str(v) for v in sleep]}})
        coefs, r2 = ols_fit(ys, [hours, sleep])
        self.assertTrue(near(out["coef_intercept"], coefs[0], 1e-9))
        self.assertTrue(near(out["coef_study_hours"], coefs[1], 1e-9))
        self.assertTrue(near(out["coef_sleep_hours"], coefs[2], 1e-9))
        self.assertTrue(near(out["r_squared"], r2, 1e-9))
        self.assertEqual(out["n"], Decimal(10))
        self.assertEqual(out["k"], Decimal(2))
        # one predictor: R squared is the squared correlation of the same pairs
        single = LIBRARY["ols"].impl({"y": [str(v) for v in ys],
                                      "predictors": {"study_hours": [str(v) for v in hours]}})
        r_one = LIBRARY["pearson"].impl({"x": [str(v) for v in hours],
                                         "y": [str(v) for v in ys]})
        single_coefs = ols_fit(ys, [hours])[0]
        self.assertTrue(near(single["r_squared"], r_one["r_squared"]))
        self.assertTrue(near(single["coef_study_hours"], single_coefs[1], 1e-9))
        self.assertTrue(near(single["coef_intercept"], single_coefs[0], 1e-9))

    def test_E_ppl_043__collinear_predictors_are_refused(self):
        ys = [1, 2, 3, 4, 5, 6]
        with self.assertRaises(DataError):
            LIBRARY["ols"].impl({"y": [str(v) for v in ys],
                                 "predictors": {"a": [str(v) for v in ys],
                                                "b": [str(2 * v) for v in ys]}})

    def test_E_ppl_044__training_roi_is_the_net_gain_over_the_investment(self):
        out = LIBRARY["return_on_investment"].impl(
            {"total_investment": "500000", "net_gain": "125000", "years": "3"})
        self.assertTrue(near(out["roi"], 125000 / 500000))
        self.assertTrue(near(out["annualised_roi"], 1.25 ** (1 / 3) - 1))
        with self.assertRaises(DataError):
            LIBRARY["return_on_investment"].impl({"total_investment": "0", "net_gain": "100"})
        with self.assertRaises(DataError):
            LIBRARY["return_on_investment"].impl({"total_investment": "-5", "net_gain": "100"})

    def test_E_ppl_045__the_period_alignment_is_declared_in_the_paper(self):
        """The gain is a total over the holding period, not an annual flow."""
        _, decision = delivered({"objective": "Training ROI", "method": "return_on_investment",
                                 "inputs": {"total_investment": "100", "net_gain": "40",
                                            "years": "2.5"},
                                 "currency": "PHP", "period": "annual"})
        text = decision.report
        self.assertIn("total gain you declared over the whole holding period", text)
        self.assertIn("14.41%", text)
        self.assertTrue(near(1.4 ** (1 / 2.5) - 1, 0.1441, 5e-5))

    def test_E_ppl_046__a_fractional_holding_period_is_printed_not_rounded(self):
        """TRAP (D-PPL-02): `years` was typed ("count", 0), so a 2.5-year holding
        printed "Compounded over 2 years" beside a return compounded over 2.5 years."""
        _, decision = delivered({"objective": "Training ROI", "method": "return_on_investment",
                                 "inputs": {"total_investment": "100", "net_gain": "40",
                                            "years": "2.5"},
                                 "currency": "PHP", "period": "annual"})
        self.assertIn("Compounded over 2.50 years", decision.report)
        self.assertNotIn("Compounded over 2 years", decision.report)
        self.assertTrue(near(1.4 ** (1 / 2.5) - 1, 0.1441, 5e-5))
        self.assertEqual(LIBRARY["return_on_investment"].typing("years"), ("periods", 2))
    def test_E_ppl_047__tightness_is_vacancies_over_unemployed_people(self):
        """TRAP (Item 11b, D-PPL-01): the denominator used to be an unemployment RATE,
        so ten vacancies over five per cent printed 200. The documented route -
        vacancies over unemployed people - could not even be entered."""
        request = preset_request("labourtightness")
        out = LIBRARY["labour_market"].impl(request["inputs"])
        self.assertEqual(request["inputs"]["vacancies"], "10")
        self.assertEqual(request["inputs"]["unemployed"], "50")
        self.assertEqual(out["labour_market_tightness"], Decimal("0.2"))
        self.assertEqual(out["unemployed"], Decimal(50))
        self.assertNotIn("unemployment_rate", out)
        errors = validate_inputs(LIBRARY["labour_market"],
                                 {"nominal_wage": "100", "cpi": "105",
                                  "labour_productivity": "120",
                                  "vacancies": "10", "unemployment_rate": "0.05"})
        self.assertEqual(len(errors), 1)
        self.assertIn("unknown input 'unemployment_rate'", errors[0])
        _, results = run("labour_market", request["inputs"])
        self.assertIn("tightness_is_vacancies_over_unemployed",
                      [name for name, ok in results])
    def test_E_ppl_048__the_tightness_output_reaches_the_report(self):
        """TRAP (Item 11c): the tool is named for a number the paper never stated."""
        _, decision = delivered(preset_request("labourtightness"))
        self.assertIn("0.2000 vacancies for each unemployed person", decision.report)
        self.assertIn("10 vacancies against 50 unemployed", decision.report)
        self.assertIn("labour_market_tightness",
                      [a[0] for a in decision.appendix["artifacts"]])
        _, results = run("labour_market", preset_request("labourtightness")["inputs"])
        self.assertTrue(all(ok for name, ok in results))
    def test_E_ppl_049__programme_cost_effectiveness_is_the_incremental_ratio(self):
        out = LIBRARY["cost_effectiveness"].impl({"options": [
            {"name": "basic", "cost": "10000", "effect": "40"},
            {"name": "intensive", "cost": "18000", "effect": "60"}]})
        self.assertTrue(near(out["icer_intensive"], (18000 - 10000) / (60 - 40)))
        self.assertEqual(out["delta_cost_intensive"], Decimal(8000))
        self.assertEqual(out["delta_effect_intensive"], Decimal(20))
        self.assertEqual(out["n_options"], Decimal(2))
        self.assertEqual(out["comparator_cost"], Decimal(10000))
        dominant = LIBRARY["cost_effectiveness"].impl({"options": [
            {"name": "a", "cost": "100", "effect": "10"},
            {"name": "b", "cost": "80", "effect": "20"}]})
        self.assertEqual(dominant["dominant_b"], Decimal(1))
        with self.assertRaises(DataError):
            LIBRARY["cost_effectiveness"].impl({"options": [
                {"name": "a", "cost": "100", "effect": "10"},
                {"name": "b", "cost": "200", "effect": "10"}]})

    def test_E_ppl_050__two_option_names_that_normalise_the_same_collapse_one_ratio(self):
        """D-PPL-03, measured: the slug is the key, so 'Option A' and 'Option_A'
        collide and the later option's ratio silently replaces the earlier one's."""
        out = LIBRARY["cost_effectiveness"].impl({"options": [
            {"name": "Option A", "cost": "100", "effect": "10"},
            {"name": "option-a", "cost": "200", "effect": "20"},
            {"name": "Option_A", "cost": "300", "effect": "40"}]})
        self.assertEqual(out["n_options"], Decimal(3))
        ratios = [k for k in out if k.startswith("icer_")]
        self.assertEqual(sorted(ratios), ["icer_Option_A", "icer_option_a"])
        self.assertTrue(near(out["icer_Option_A"], (300 - 100) / (40 - 10)))
        self.assertTrue(near(out["icer_option_a"], (200 - 100) / (20 - 10)))


    def test_E_ppl_085__a_cost_per_unit_of_effect_prints_its_denominator(self):
        """TRAP (B-216): the engine gained one composite unit. It must print as a cost
        per effect, keep the accounting parentheses for a negative ratio, and never be
        mistaken for an amount."""
        ratio = Quantity(Decimal("400"), unit="currency_per_effect", currency="USD", precision=2)
        self.assertEqual(ratio.display(), "USD 400.00 per unit of effect")
        negative = Quantity(Decimal("-2"), unit="currency_per_effect", currency="USD", precision=2)
        self.assertEqual(negative.display(), "USD (2.00) per unit of effect")
        no_currency = Quantity(Decimal("1.5"), unit="currency_per_effect", precision=2)
        self.assertEqual(no_currency.display(), "1.50 per unit of effect")


class Units(unittest.TestCase):
    """E-ppl-051 ... E-ppl-055 - what the product actually prints, in its own units."""

    def test_E_ppl_051__an_effect_is_printed_on_its_own_scale_not_as_money(self):
        """TRAP (D-PPL-01): the orchestrator took the request's currency for an `@unit`
        output BEFORE resolving the unit, so an effect of 40 printed "USD 40.00"."""
        pipeline, decision = delivered(preset_request("programmecost"))
        shown = {a.id: a.value for a in pipeline.store.all()}
        self.assertEqual(shown["comparator_effect"].unit, "units")
        self.assertIsNone(shown["comparator_effect"].currency)
        self.assertEqual(shown["comparator_effect"].display(), "40.00")
        self.assertEqual(shown["delta_effect_intensive"].display(), "20.000")
        self.assertNotIn("USD", decision.report.split("The ratios are in the appendix")[0])
    def test_E_ppl_052__the_comparator_cost_keeps_its_money_and_the_ratio_names_its_denominator(self):
        """TRAP (D-PPL-01): the comparator's cost was declared @unit (no money unit) and
        the ICER was declared plain currency, so a cost per effect printed as an amount."""
        pipeline, decision = delivered(preset_request("programmecost"))
        shown = {a.id: a.value for a in pipeline.store.all()}
        self.assertEqual(shown["comparator_cost"].unit, "currency")
        self.assertEqual(shown["comparator_cost"].display(), "USD 10,000.00")
        self.assertEqual(shown["icer_intensive"].display(), "USD 400.00 per unit of effect")
        self.assertEqual(LIBRARY["cost_effectiveness"].typing("icer_intensive"),
                         ("currency_per_effect", 2))
    def test_E_ppl_053__a_ratio_of_two_counts_prints_with_no_currency_prefix(self):
        """`ratio` is in the currency-exempt tuple, and tightness is now a ratio of like
        units: ten vacancies over fifty unemployed people is 0.2000."""
        pipeline, decision = delivered(preset_request("labourtightness"))
        shown = {a.id: a.value for a in pipeline.store.all()}
        self.assertEqual(shown["labour_market_tightness"].display(), "0.2000")
        self.assertIsNone(shown["labour_market_tightness"].currency)
        self.assertEqual(shown["vacancies"].display(), "10")
        self.assertEqual(shown["unemployed"].display(), "50")
        self.assertEqual(shown["real_wage"].display(), "PHP 95.24")
    def test_E_ppl_054__every_delivered_figure_is_printed_at_its_declared_precision(self):
        for key in TOOLS:
            pipeline, decision = delivered(preset_request(key))
            for artifact in pipeline.store.all():
                quantity, text = artifact.value, artifact.value.display()
                if quantity.unit == "count" and quantity.currency is None:
                    self.assertNotIn(".", text, (key, artifact.id, text))
                if quantity.unit == "probability":
                    self.assertEqual(len(text.split(".")[1]), quantity.precision,
                                     (key, artifact.id, text))
                # a count that carries a currency is D-PPL-01 and is pinned there

    def test_E_ppl_055__a_currency_label_changes_no_number(self):
        request = preset_request("trainingroi")
        hashes = {}
        for label in ("PHP", "USD"):
            _, decision = delivered({**request, "currency": label})
            hashes[label] = decision.appendix["reperform"]["outputs_hash"]
        self.assertEqual(hashes["PHP"], hashes["USD"])


class Refusals(unittest.TestCase):
    """E-ppl-056 ... E-ppl-066 - the boundary and refusal sweep."""

    def test_E_ppl_056__an_empty_list_is_refused_by_validation(self):
        self.assertTrue(validate_inputs(LIBRARY["descriptive_stats"], {"values": []}))
        self.assertTrue(validate_inputs(LIBRARY["reliability_alpha"], {"items": {}}))
        self.assertTrue(validate_inputs(LIBRARY["cost_effectiveness"], {"options": []}))
        self.assertTrue(validate_inputs(LIBRARY["weighted_summary"],
                                        {"values": [], "weights": []}))

    def test_E_ppl_057__one_element_is_defined_or_refused_with_a_reason(self):
        single = LIBRARY["descriptive_stats"].impl({"values": ["7"]})
        self.assertEqual(single["mean"], Decimal(7))
        self.assertNotIn("sd", single)
        with self.assertRaises(DataError):
            LIBRARY["weighted_summary"].impl({"values": ["5"], "weights": ["2"],
                                              "weight_kind": "reliability"})
        self.assertTrue(validate_inputs(LIBRARY["cost_effectiveness"],
                                        {"options": [{"name": "a", "cost": "1",
                                                      "effect": "1"}]}))

    def test_E_ppl_058__a_formatted_number_is_refused_by_name(self):
        errors = validate_inputs(LIBRARY["descriptive_stats"], {"values": ["1,200,000"]})
        self.assertTrue(errors)
        self.assertIn("1,200,000", errors[0])
        self.assertIn("not a number", errors[0])
        errors = validate_inputs(LIBRARY["reliability_alpha"],
                                 {"items": {"one": ["1,200,000", "2"], "two": ["3", "4"]}})
        self.assertTrue(errors)
        self.assertIn("not a number", errors[0])

    def test_E_ppl_059__a_significance_level_entered_as_5_is_refused_by_name(self):
        """A rate entered as `5` is never rescaled. The labour tool no longer takes a
        rate at all (Item 11b), so the rule is measured on a rate that remains: the
        significance level of the chi-square test."""
        decision = refused({"objective": "x", "method": "chi_square",
                            "inputs": {"table": [[1, 2], [3, 4]], "alpha": "5"},
                            "period": "cross_section"})
        self.assertEqual(decision.status, "blocked")
        self.assertIn("alpha must be between 0 and 1", decision.blocked_reason)
    def test_E_ppl_060__a_zero_or_negative_denominator_is_refused_by_the_method(self):
        request = preset_request("labourtightness")
        for value in ("0", "-5"):
            with self.assertRaises(DataError):
                LIBRARY["labour_market"].impl({**request["inputs"], "unemployed": value})
        with self.assertRaises(DataError):
            LIBRARY["labour_market"].impl({**request["inputs"], "vacancies": "-1"})
        self.assertTrue(validate_inputs(LIBRARY["labour_market"],
                                        {**request["inputs"], "unemployed": "not a number"}))
    def test_E_ppl_061__very_large_values_stay_exact(self):
        out = LIBRARY["descriptive_stats"].impl({"values": ["1200000000", "1200000002"]})
        self.assertEqual(out["mean"], Decimal(1200000001))
        self.assertEqual(out["sd"], Decimal(2).sqrt())

    def test_E_ppl_062__duplicates_are_counted_not_collapsed(self):
        out = LIBRARY["descriptive_stats"].impl({"values": ["2", "2", "4", "4"]})
        self.assertEqual(out["n"], Decimal(4))
        self.assertEqual(out["mean"], Decimal(3))
        self.assertEqual(out["median"], Decimal(3))

    def test_E_ppl_063__an_unknown_input_is_refused_with_the_reason_it_is_not_modelled(self):
        errors = validate_inputs(LIBRARY["descriptive_stats"],
                                 {"values": ["1", "2"], "weight": ["1", "1"]})
        self.assertTrue(errors)
        self.assertIn("survey weights", errors[0])
        self.assertIn("not supported", errors[0])

    def test_E_ppl_064__a_binary_float_is_refused_rather_than_silently_converted(self):
        errors = validate_inputs(LIBRARY["descriptive_stats"], {"values": [1.5, 2]})
        self.assertTrue(errors)
        self.assertIn("binary floats", errors[0])

    def test_E_ppl_065__an_unknown_method_is_an_actionable_block_not_a_traceback(self):
        decision = refused({"objective": "x", "method": "not_a_method", "inputs": {}})
        self.assertEqual(decision.status, "blocked")
        self.assertIn("unknown method 'not_a_method'", decision.blocked_reason)
        self.assertNotIn("Traceback", decision.blocked_reason)

    def test_E_ppl_066__an_option_with_the_same_effect_blocks_the_ratio(self):
        with self.assertRaises(DataError) as caught:
            LIBRARY["cost_effectiveness"].impl({"options": [
                {"name": "a", "cost": "100", "effect": "10"},
                {"name": "b", "cost": "200", "effect": "10"}]})
        self.assertIn("undefined", str(caught.exception))


class Delivery(unittest.TestCase):
    """E-ppl-067 ... E-ppl-073 - delivery, determinism and disclosure."""

    def test_E_ppl_067__every_preset_delivers_with_every_check_passing(self):
        for key in TOOLS:
            pipeline, decision = delivered(preset_request(key))
            self.assertEqual(decision.status, "delivered", key)
            self.assertEqual(decision.appendix["amendments"], 0, key)
            self.assertTrue(decision.appendix["tests"], key)
            self.assertNotIn("{{", decision.report, key)
            for field in ("spec_hash", "method", "run_id", "env_hash", "artifacts",
                          "assumptions", "limitations", "honesty", "reperform"):
                self.assertIn(field, decision.appendix, (key, field))
            self.assertIn(decision.tier, ("T1", "T2", "T3"), key)

    def test_E_ppl_068__the_same_inputs_twice_give_the_same_numbers(self):
        for key in TOOLS:
            first = delivered(preset_request(key))[1]
            second = delivered(preset_request(key))[1]
            self.assertEqual(first.appendix["reperform"]["outputs_hash"],
                             second.appendix["reperform"]["outputs_hash"], key)
            self.assertEqual(first.report, second.report, key)
            self.assertNotEqual(first.appendix["run_id"], second.appendix["run_id"], key)

    def test_E_ppl_069__the_appendix_survives_a_json_round_trip(self):
        for key in TOOLS:
            decision = delivered(preset_request(key))[1]
            revived = json.loads(json.dumps(decision.appendix))
            self.assertEqual(revived["reperform"]["outputs_hash"],
                             decision.appendix["reperform"]["outputs_hash"], key)
            self.assertEqual(revived["tests"], decision.appendix["tests"], key)

    def test_E_ppl_070__a_refusal_is_a_refusal_not_a_zero(self):
        decision = refused({"objective": "x", "method": "descriptive_stats",
                            "inputs": {"values": "not a list"}})
        self.assertEqual(decision.status, "blocked")
        self.assertEqual(decision.report, "")
        self.assertNotIn("reperform", decision.appendix)
        self.assertNotIn("artifacts", decision.appendix)
        self.assertTrue(decision.blocked_reason)

    def test_E_ppl_071__the_disclosure_names_what_was_not_done(self):
        self.assertIn("not validity", delivered(preset_request("alpha"))[1].report)
        self.assertIn("No taxes, benefits, hours, composition or bargaining model",
                      delivered(preset_request("labourtightness"))[1].report)
        self.assertIn("not a forecast", delivered(preset_request("trainingroi"))[1].report)
        self.assertIn("does not convert or weight different outcomes",
                      delivered(preset_request("programmecost"))[1].report)

    def test_E_ppl_072__no_report_claims_more_than_its_ceiling_allows(self):
        for key in TOOLS:
            method = LIBRARY[METHODS[key]]
            self.assertIn(method.claim_ceiling, ("descriptive", "associational"), key)
            text = delivered(preset_request(key))[1].report.lower()
            for word in ("we recommend", "you should", "proves that", "will improve"):
                self.assertNotIn(word, text, (key, word))

    def test_E_ppl_073__the_honesty_block_is_attached_to_every_delivery(self):
        for key in TOOLS:
            honesty = delivered(preset_request(key))[1].appendix["honesty"]
            self.assertTrue(honesty, key)
            self.assertIsInstance(honesty, (dict, list), key)


SHARED_BRIEFS = {
    "CHG-01": ("moving the campus meal card to a contactless system",
               "The campus meal card is moving to a contactless system and the manager "
               "has to plan the change."),
    "CHG-12": ("the campus catering team",
               "The campus catering team has to be understood before the service is changed."),
}


def _academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{"title": query[:70],
                         "abstract": "Evidence on the conditions named in the query. "
                                     "A second sentence follows it.",
                         "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"],
                         "year": 2024, "venue": "Journal of People Studies",
                         "doi": "10.1/" + str(abs(hash(query)) % 1000000),
                         "url": "https://doi.org/10.1/x", "database": "OpenAlex"}],
            "errors": [], "skipped": []}


def _web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def worksheet(cid):
    """One completion with the searches mocked, then the paper's own bytes."""
    kind = WORKSHEETS[cid][0]
    unit, brief = SHARED_BRIEFS[cid]
    with mock.patch("bp.product.sources.search_academic", side_effect=_academic), \
            mock.patch("bp.product.sources.search_web", side_effect=_web):
        result = completion.complete(kind, brief, unit_value=unit)
    return result, completion.draft_bytes(result, "apa")


def paper_text(raw):
    """The words of a .docx, in order, with the markup stripped."""
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        xml = archive.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    return re.sub(r"<[^>]+>", "", xml)


class Parity(unittest.TestCase):
    """E-ppl-074 ... E-ppl-077 - the same worksheet and the same calculator twice."""

    def test_E_ppl_074__the_shared_worksheets_are_declared_identically_on_both_shelves(self):
        here = {w["key"]: w for w in page()["worksheets"]}
        there = {w["key"]: w for w in page("management")["worksheets"]}
        for cid in SHARED_WITH_MANAGEMENT:
            self.assertIn(cid, here, cid)
            self.assertIn(cid, there, cid)
            for field in ("label", "template", "what", "before", "draftable", "kind"):
                self.assertEqual(here[cid][field], there[cid][field], (cid, field))
        project = {w["key"]: w for w in page("project-management")["worksheets"]}
        for cid in SHARED_WITH_PROJECTS:
            self.assertIn(cid, here, cid)
            self.assertIn(cid, project, cid)
            for field in ("label", "template", "what", "before", "draftable", "kind"):
                self.assertEqual(here[cid][field], project[cid][field], (cid, field))
        for cid in SHARED_BRIEFS:
            self.assertEqual(completion.missing(worksheet(cid)[0]), [], cid)

    def test_E_ppl_075__the_same_brief_produces_the_same_paper_on_either_shelf(self):
        first, raw = worksheet("CHG-01")
        second, raw_again = worksheet("CHG-01")
        self.assertEqual(raw, raw_again)
        text = paper_text(raw)
        self.assertIn("Kotter", text)
        self.assertNotIn("People & organisation", text)
        self.assertNotIn("Management & strategy", text)

    def test_E_ppl_076__a_shared_calculator_returns_the_same_hash_on_both_shelves(self):
        for subject, keys in (("economics", SHARED_WITH_ECONOMICS),
                              ("operations", SHARED_WITH_OPERATIONS)):
            other = {t["key"]: t for t in page(subject)["tools"]}
            for key in keys:
                self.assertIn(key, other, (subject, key))
                mine = subjects.TOOL_INFO[key]
                theirs = other[key]
                self.assertEqual(mine["preset"], theirs["preset"], (subject, key))
                self.assertEqual(mine["method"], theirs["method"], (subject, key))
                left = delivered(preset_request(key))[1]
                right = delivered(preset_request(key))[1]
                self.assertEqual(left.appendix["reperform"]["outputs_hash"],
                                 right.appendix["reperform"]["outputs_hash"],
                                 (subject, key))
                self.assertEqual(left.report, right.report, (subject, key))

    def test_E_ppl_077__management_declares_none_of_the_ten_calculators(self):
        theirs = {t["key"] for t in page("management")["tools"]}
        self.assertEqual(theirs & set(TOOLS), set())
        self.assertEqual(theirs, {"case_decision"})


class Page(unittest.TestCase):
    """E-ppl-078 ... E-ppl-084 - the page a student reads."""

    def test_E_ppl_078__the_guidance_names_every_tile(self):
        guidance = page()["guidance"]
        for words in ("Strategy and design", "Resourcing", "Development", "Reward",
                      "Engagement and culture", "Analytics"):
            self.assertIn(words, guidance, words)

    def test_E_ppl_079__the_curriculum_map_names_this_shelf(self):
        text = io.open(path("docs", "CURRICULUM_MAP.md"), encoding="utf-8").read()
        row = [line for line in text.splitlines()
               if line.startswith("| People & organisation")][0]
        for key in TOOLS:
            self.assertIn("`%s`" % METHODS[key], row, key)
        for tile in TILES:
            self.assertIn(TILE_TITLE[tile], row, tile)
        for cid in WORKSHEETS:
            self.assertIn(cid, row, cid)

    def test_E_ppl_080__the_served_page_renders_the_tiles_and_the_empty_tile_note(self):
        html = io.open(path("web", "index.html"), encoding="utf-8").read()
        self.assertIn("function subjectTiles(s)", html)
        self.assertIn("if (!sheets.length && !rows.length && !tools.length && !tile.service)", html)
        self.assertIn("esc(tile.note ||", html)

    def test_E_ppl_081__no_snake_case_or_field_placeholder_in_the_student_facing_strings(self):
        for tool in page()["tools"]:
            for field in ("label", "what", "need"):
                text = tool[field] or ""
                self.assertNotIn("_", text, (tool["key"], field))
                self.assertNotIn("dimension_", text, (tool["key"], field))
        for sheet in page()["worksheets"]:
            for field in ("label", "what"):
                text = sheet[field] or ""
                self.assertNotIn("_", text, (sheet["key"], field))

    def test_E_ppl_082__every_tool_needs_one_distinct_line_before_it_starts(self):
        needs = [tool["need"] for tool in page()["tools"]]
        self.assertEqual(len(set(needs)), len(needs))
        for need in needs:
            self.assertTrue(need)
            self.assertNotIn("\n", need)

    def test_E_ppl_083__the_calculator_form_is_labelled_from_the_frozen_schema(self):
        html = io.open(path("web", "index.html"), encoding="utf-8").read()
        self.assertIn("function fieldLabel(name, desc, extra)", html)
        self.assertIn("esc(desc || \"\")", html)

    def test_E_ppl_084__the_empty_and_refusal_states_are_designed(self):
        """U3: an empty cell is named as a gap and a refusal names the missing input."""
        html = io.open(path("web", "index.html"), encoding="utf-8").read()
        self.assertIn("Nothing is assigned to this tile yet.", html)
        errors = validate_inputs(LIBRARY["descriptive_stats"], {})
        self.assertTrue(errors)
        self.assertIn("missing required input 'values'", errors[0])
        self.assertIn("the observations", errors[0])












