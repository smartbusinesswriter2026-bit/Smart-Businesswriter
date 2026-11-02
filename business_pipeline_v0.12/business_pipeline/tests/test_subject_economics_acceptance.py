"""Acceptance suite for the Economics shelf.

One test per row of `qa/manual/economics.md` §8, named after its E-id so the
traceability matrix is mechanical. Offline: no model, no network, no new dependency.

The expected values in `GUIDE_EXAMPLES` are hand arithmetic taken from
`docs/ECONOMICS_STUDENT_GUIDE.md` — they are the independent second route, never
produced by the method under test.
"""
import json
import re
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, "src")

from bp import server                      # noqa: E402
from bp.methods import LIBRARY             # noqa: E402
from bp.orchestrator import Pipeline       # noqa: E402
from bp.product import subjects            # noqa: E402

YES = lambda _reason: True                 # noqa: E731
DETAIL = subjects.detail("economics")
TOOLS = DETAIL["tools"]
TOOL_KEYS = [tool["key"] for tool in TOOLS]
EQ = {"demand_intercept": "100", "demand_slope": "2",
      "supply_intercept": "20", "supply_slope": "2"}


def request_for(tool):
    preset = server.PRESETS[tool["preset"]]
    request = dict(preset)
    request.setdefault("objective", "economics acceptance %s" % tool["key"])
    request.setdefault("period", "annual")
    return request


def deliver(tool):
    return Pipeline().run(request_for(tool), YES)


def closing(observed, expected, tolerance=1e-4):
    return abs(float(observed) - float(expected)) <= tolerance * max(1.0, abs(float(expected)))


def check_tool(case, tool):
    """Every assertion behind one per-tool E-row (E-eco-001…059)."""
    case.assertIn(tool["method"], LIBRARY, "%s: method not in LIBRARY" % tool["key"])
    case.assertIn(tool["preset"], server.PRESETS, "%s: preset missing" % tool["key"])
    case.assertEqual(server.PRESETS[tool["preset"]]["method"], tool["method"],
                     "%s: preset launches another method" % tool["key"])
    method = LIBRARY[tool["method"]]
    inputs = server.PRESETS[tool["preset"]]["inputs"]
    case.assertEqual(tuple(name for name, _ok in method.tests(inputs, method.impl)),
                     tuple(method.test_names),
                     "%s: checks do not match the declared names" % tool["key"])
    case.assertTrue(all(ok for _name, ok in method.tests(inputs, method.impl)),
                    "%s: a declared check fails" % tool["key"])
    delivery = deliver(tool)
    case.assertEqual(delivery.status, "delivered",
                     "%s: %s" % (tool["key"], delivery.blocked_reason))
    case.assertTrue((delivery.report or "").strip(), "%s: empty report" % tool["key"])
    checked = delivery.appendix.get("tests") or []
    values = checked.values() if isinstance(checked, dict) else checked
    case.assertTrue(all(value is not False for value in values),
                    "%s: a delivered check is false" % tool["key"])
    first = method.impl(inputs)
    second = method.impl(inputs)
    case.assertEqual(first, second, "%s: not deterministic" % tool["key"])
    case.assertEqual(json.loads(json.dumps(first, default=str)),
                     json.loads(json.dumps(second, default=str)),
                     "%s: not JSON-stable" % tool["key"])


class EconomicsTools(unittest.TestCase):
    """The 59 per-tool rows. Each test is generated from the catalogue, above."""


def _tool_test(tool, number):
    def test(self):
        check_tool(self, tool)

    test.__name__ = "test_E_eco_%03d__%s_runs_from_its_preset" % (number, tool["key"])
    test.__doc__ = "E-eco-%03d — %s runs from preset %r." % (number, tool["label"], tool["preset"])
    return test


for _number, _tool in enumerate(TOOLS, start=1):
    setattr(EconomicsTools,
            "test_E_eco_%03d__%s_runs_from_its_preset" % (_number, _tool["key"]),
            _tool_test(_tool, _number))


def _all_reports():
    return {tool["key"]: (deliver(tool).report or "") for tool in TOOLS}


class EconomicsCrossCutting(unittest.TestCase):
    """E-eco-060 … E-eco-073, 080, 084 — the shelf-wide claims."""

    @classmethod
    def setUpClass(cls):
        cls.reports = _all_reports()

    def test_E_eco_060__no_report_prints_a_raw_decimal_or_scientific_notation(self):
        long_decimal = re.compile(r"\d+\.\d{5,}")
        scientific = re.compile(r"\d(?:\.\d+)?[eE][+-]?\d")
        for key, text in self.reports.items():
            self.assertEqual(long_decimal.findall(text), [],
                             "%s: a figure prints with more than four decimals" % key)
            self.assertEqual(scientific.findall(text), [],
                             "%s: a figure prints in scientific notation" % key)

    def test_E_eco_061__no_report_carries_an_unresolved_template_token(self):
        for key, text in self.reports.items():
            self.assertNotIn("{{ref:", text, "%s: unresolved reference token" % key)
            self.assertNotIn("@unit", text, "%s: unresolved unit token" % key)

    def test_E_eco_062__computations_are_deterministic_and_json_stable(self):
        for tool in TOOLS:
            method = LIBRARY[tool["method"]]
            inputs = server.PRESETS[tool["preset"]]["inputs"]
            first, second = method.impl(inputs), method.impl(inputs)
            self.assertEqual(first, second, "%s: two runs differ" % tool["key"])
            self.assertEqual(json.dumps(first, default=str, sort_keys=True),
                             json.dumps(second, default=str, sort_keys=True),
                             "%s: JSON round trip is unstable" % tool["key"])

    def test_E_eco_063__every_method_reports_its_declared_checks_and_they_pass(self):
        for tool in TOOLS:
            method = LIBRARY[tool["method"]]
            inputs = server.PRESETS[tool["preset"]]["inputs"]
            pairs = list(method.tests(inputs, method.impl))
            self.assertEqual(tuple(name for name, _ in pairs), tuple(method.test_names),
                             "%s: check names drifted" % tool["key"])
            self.assertTrue(all(ok for _, ok in pairs), "%s: a check fails" % tool["key"])

    def test_E_eco_064__every_method_contract_is_complete(self):
        for tool in TOOLS:
            method = LIBRARY[tool["method"]]
            label = tool["method"]
            for field in ("intended_use", "unsupported_use", "assumptions", "limitations",
                          "test_names", "metric", "unit", "tier", "claim_ceiling"):
                self.assertTrue(getattr(method, field, None), "%s: %s is empty" % (label, field))
            self.assertIn(method.tier, ("T1", "T2", "T3", "T4"), "%s: bad tier" % label)
            self.assertIn(method.claim_ceiling,
                          ("descriptive", "associational", "predictive"),
                          "%s: bad claim ceiling" % label)
            self.assertGreaterEqual(len(method.test_names), 3, "%s: under 3 checks" % label)
            schema = method.input_schema or {}
            self.assertTrue(schema, "%s: no input schema" % label)
            for name, spec in schema.items():
                self.assertIn("type", spec, "%s.%s has no type" % (label, name))
                self.assertTrue(spec.get("desc"), "%s.%s has no description" % (label, name))

    def test_E_eco_065__every_preset_launches_the_method_it_claims(self):
        seen = set()
        for tool in TOOLS:
            self.assertIn(tool["preset"], server.PRESETS, "%s: preset missing" % tool["key"])
            self.assertEqual(server.PRESETS[tool["preset"]]["method"], tool["method"],
                             "%s: preset launches another method" % tool["key"])
            self.assertNotIn(tool["preset"], seen, "%s: two tools share a preset" % tool["key"])
            seen.add(tool["preset"])

    def test_E_eco_066__the_catalogue_has_no_duplicate_or_empty_tool_row(self):
        methods = [tool["method"] for tool in TOOLS]
        self.assertEqual(len(methods), len(set(methods)), "a method is claimed twice")
        self.assertEqual(len(TOOL_KEYS), len(set(TOOL_KEYS)), "a tool key repeats")
        for tool in TOOLS:
            for field in ("key", "label", "method", "preset", "group", "level", "formula"):
                self.assertTrue(tool.get(field), "%s: %s is empty" % (tool.get("key"), field))

    def test_E_eco_067__levels_are_declared_and_split_23_23_13(self):
        counts = {}
        for tool in TOOLS:
            self.assertIn(tool["level"], ("intro", "intermediate", "advanced"),
                          "%s: unknown level" % tool["key"])
            counts[tool["level"]] = counts.get(tool["level"], 0) + 1
        self.assertEqual(counts, {"intro": 23, "intermediate": 23, "advanced": 13})

    def test_E_eco_068__every_tool_carries_formula_steps_and_mistakes(self):
        for tool in TOOLS:
            self.assertTrue(tool.get("formula"), "%s: no formula" % tool["key"])
            self.assertGreaterEqual(len(tool.get("steps") or []), 3,
                                    "%s: fewer than three steps" % tool["key"])
            self.assertGreaterEqual(len(tool.get("common_mistakes") or []), 3,
                                    "%s: fewer than three common mistakes" % tool["key"])




    def test_E_eco_069__every_related_id_resolves_to_a_built_tool(self):
        catalogues = getattr(subjects, "SUBJECT_DEFS", None) or []
        built = set()
        for row in catalogues:
            for tool in subjects.detail(row["id"])["tools"] or []:
                if tool.get("key"):
                    built.add(tool["key"])
        self.assertTrue(built, "no subject catalogue was readable")
        for tool in TOOLS:
            for related in tool.get("related") or []:
                self.assertIn(related, built,
                              "%s: related id %r is not a built tool" % (tool["key"], related))
        page = open("web/index.html", encoding="utf-8").read()
        self.assertIn("Related: ", page, "the page no longer renders the related line")

    def test_E_eco_070__records_link_only_built_methods(self):
        records = DETAIL["records"]
        self.assertEqual(len(records), 5)
        for record in records:
            for method_id in record.get("linked_methods") or []:
                self.assertIn(method_id, LIBRARY,
                              "%s links unknown method %r" % (record.get("id"), method_id))
            self.assertIsNone(record.get("template"),
                              "%s names a worksheet template" % record.get("id"))

    def test_E_eco_071__the_glossary_is_complete_and_has_no_duplicates(self):
        glossary = DETAIL["glossary"]
        self.assertEqual(len(glossary), 25)
        terms = [entry["term"] for entry in glossary]
        self.assertEqual(len(terms), len(set(terms)), "a glossary term repeats")
        for entry in glossary:
            self.assertTrue(entry["term"].strip(), "an empty term")
            self.assertTrue(entry["definition"].strip(),
                            "%r has no definition" % entry["term"])

    def test_E_eco_072__the_tiles_partition_the_tool_set(self):
        tiles = DETAIL["tiles"]
        self.assertEqual(len(tiles), 8)
        grouped = []
        for tile in tiles:
            self.assertTrue(tile["key"] and tile["label"] and tile.get("what"),
                            "tile %r is incomplete" % tile.get("key"))
            for tool in tile.get("tools") or []:
                grouped.append(tool["key"])
                self.assertEqual(tool.get("group"), tile["key"],
                                 "%s sits in tile %s but declares group %r"
                                 % (tool["key"], tile["key"], tool.get("group")))
        self.assertEqual(sorted(grouped), sorted(TOOL_KEYS),
                         "the tiles do not cover each tool exactly once")

    def test_E_eco_073__start_steps_and_does_not_are_declared(self):
        steps = DETAIL.get("start_steps") or []
        does_not = DETAIL.get("does_not") or []
        self.assertGreaterEqual(len(steps), 3, "fewer than three start steps")
        self.assertGreaterEqual(len(does_not), 2, "fewer than two does-not statements")
        self.assertEqual(len(steps), 5)
        self.assertEqual(len(does_not), 3)
        for item in steps + does_not:
            self.assertTrue(item.strip(), "an empty guidance line")

    def test_E_eco_080__a_missing_need_line_falls_back_and_is_ledgered(self):
        with_need = sorted(tool["key"] for tool in TOOLS if tool.get("need"))
        self.assertEqual(with_need,
                         ["chi_square", "descriptive", "forecast", "npv", "ols",
                          "pearson", "power"],
                         "TOOL_NEEDS coverage for economics changed; update G-eco-01")
        for tile in DETAIL["tiles"]:
            self.assertTrue(tile.get("need"),
                            "tile %s has no 'what to gather' fallback" % tile["key"])

    def test_E_eco_081__a_share_and_a_count_are_not_typed_as_money(self):
        method = LIBRARY["labour_market"]
        inputs = {"nominal_wage": "100", "cpi": "110", "labour_productivity": "50",
                  "unemployment_rate": "0.06", "vacancies": "300"}
        method.impl(inputs)
        self.assertEqual(method.typing("wage_share_of_productivity")[0], "ratio",
                         "the wage share is a ratio, not money")
        self.assertEqual(method.typing("labour_market_tightness")[0], "ratio",
                         "tightness is a ratio, not money")
        self.assertEqual(method.typing("vacancies")[0], "count",
                         "vacancies are a count, not money")
        self.assertEqual(method.typing("real_wage")[0], "currency",
                         "the real wage is money and must stay money")
        self.assertEqual(method.typing("nominal_wage")[0], "currency")
        tool = [row for row in TOOLS if row["key"] == "labour"][0]
        report = deliver(tool).report or ""
        self.assertIn("0.7937", report, "the wage share should print at four places")
        self.assertIsNone(re.search(r"[A-Z]{3} 0\.7937", report),
                          "the wage share must not be printed with a currency")

    def test_E_eco_083__the_conversion_never_mislabels_the_source_amount(self):
        tool = [row for row in TOOLS if row["key"] == "currency"][0]
        report = deliver(tool).report or ""
        self.assertIn("920.00", report, "the converted amount is reported")
        self.assertIsNone(re.search(r"[A-Z]{3} 1,000\.00", report),
                          "the source amount must not carry the target currency")
        self.assertNotIn("1,000.00", report,
                         "the source amount must not be re-labelled as a money figure")
        self.assertIn("converted amount", report)
        self.assertIn("appendix", report,
                      "the source amount and both codes must be pointed at the appendix")

    def test_E_eco_084__the_curriculum_map_states_the_true_tool_count(self):
        import os
        path = "docs/CURRICULUM_MAP.md" if os.path.exists("docs/CURRICULUM_MAP.md") \
            else os.path.join("..", "docs", "CURRICULUM_MAP.md")
        text = open(path, encoding="utf-8").read()
        row = [line for line in text.splitlines() if line.startswith("| Economics |")]
        self.assertEqual(len(row), 1, "the Economics row is missing from the curriculum map")
        self.assertIn("%d tools" % len(TOOLS), row[0],
                      "the curriculum map's tool count no longer matches the catalogue")




class EconomicsGuideExamples(unittest.TestCase):
    """E-eco-074 … 079 — the guide's own conventions, recomputed by hand."""

    def test_E_eco_074__the_student_guide_examples_reproduce(self):
        for example_id, method_id, inputs, expected in GUIDE_EXAMPLES:
            out = LIBRARY[method_id].impl(inputs)
            for key, want in expected.items():
                self.assertIn(key, out, "%s: %s missing from %s"
                              % (example_id, key, method_id))
                self.assertTrue(closing(out[key], want),
                                "%s: %s expected %s, got %s"
                                % (example_id, key, want, out[key]))

    def test_E_eco_075__labour_ratios_use_the_declared_denominators(self):
        out = LIBRARY["unemployment_rate"].impl(
            {"labour_force": "500", "employed": "450", "working_age_population": "800"})
        self.assertTrue(closing(out["unemployed"], 50))
        self.assertTrue(closing(out["unemployment_rate"], 50 / 500))
        self.assertTrue(closing(out["labour_force_participation_rate"], 500 / 800))
        self.assertTrue(closing(out["employment_population_ratio"], 450 / 800))

    def test_E_eco_076__the_real_rate_is_the_fisher_relation(self):
        out = LIBRARY["inflation_cpi"].impl(
            {"cpi_start": "120", "cpi_end": "126", "nominal_interest_rate": "0.07",
             "wage_start": "200", "wage_end": "210"})
        self.assertTrue(closing(out["inflation_rate"], 0.05))
        self.assertTrue(closing(out["real_interest_rate"], 1.07 / 1.05 - 1))
        self.assertTrue(closing(out["real_interest_approximation"], 0.07 - 0.05))
        self.assertTrue(closing(out["real_wage_growth"], 0))

    def test_E_eco_077__arc_elasticity_is_symmetric(self):
        forward = LIBRARY["elasticity"].impl(
            {"price_1": "10", "quantity_1": "100", "price_2": "8", "quantity_2": "140"})
        backward = LIBRARY["elasticity"].impl(
            {"price_1": "8", "quantity_1": "140", "price_2": "10", "quantity_2": "100"})
        self.assertTrue(closing(forward["price_elasticity"], -1.5))
        self.assertTrue(closing(forward["price_elasticity"], backward["price_elasticity"]))

    def test_E_eco_078__a_non_binding_control_changes_nothing(self):
        free = LIBRARY["price_control"].impl(
            {**EQ, "control_type": "ceiling", "control_price": "60"})
        self.assertFalse(float(free["binding"]), "a ceiling above equilibrium must not bind")
        self.assertTrue(closing(free["quantity_traded"], 60))
        self.assertTrue(closing(free["deadweight_loss"], 0))
        short_side = LIBRARY["price_control"].impl(
            {**EQ, "control_type": "ceiling", "control_price": "15"})
        self.assertTrue(closing(short_side["quantity_traded"], 50))
        self.assertTrue(closing(short_side["quantity_demanded_at_control"], 70))
        self.assertTrue(closing(short_side["quantity_supplied_at_control"], 50))

    def test_E_eco_079__hhi_uses_percentage_shares(self):
        percentages = LIBRARY["market_concentration"].impl(
            {"firm_revenues": ["40", "25", "15", "10", "10"]})
        self.assertTrue(closing(percentages["hhi"], 2650))
        self.assertTrue(closing(percentages["cr4"], 90))
        self.assertTrue(closing(percentages["effective_n"], 10000 / 2650))
        # Percentage shares are computed from the revenue total, so the HHI is
        # scale-invariant: the same market written in fractions is the same HHI.
        fractions = LIBRARY["market_concentration"].impl(
            {"firm_revenues": ["0.40", "0.25", "0.15", "0.10", "0.10"]})
        self.assertTrue(closing(fractions["hhi"], 2650),
                        "scaling every revenue by the same factor must not move the HHI")
        # Two equal firms are 50% each: 50² + 50² = 5,000, i.e. a percentage scale.
        duopoly = LIBRARY["market_concentration"].impl({"firm_revenues": ["50", "50"]})
        self.assertTrue(closing(duopoly["hhi"], 5000))


# Hand arithmetic from docs/ECONOMICS_STUDENT_GUIDE.md. Each expected figure is
# recomputed by hand in the manual (§8) — never taken from the method's own output.
GUIDE_EXAMPLES = [
    ("guide-1-equilibrium", "demand_supply_equilibrium", EQ,
     {"equilibrium_price": "20", "equilibrium_quantity": "60",
      "consumer_surplus": "900", "producer_surplus": "900", "total_surplus": "1800"}),
    ("guide-2-elasticity", "elasticity",
     {"price_1": "10", "quantity_1": "100", "price_2": "8", "quantity_2": "140"},
     {"price_elasticity": "-1.5", "revenue_change": "120"}),
    ("guide-3-tax", "tax_incidence", {**EQ, "tax_per_unit": "6"},
     {"consumer_price": "23", "producer_price": "17", "quantity_traded": "54",
      "tax_revenue": "324", "deadweight_loss": "18"}),
    ("guide-4-ceiling", "price_control",
     {**EQ, "control_type": "ceiling", "control_price": "15"},
     {"quantity_demanded_at_control": "70", "quantity_supplied_at_control": "50",
      "shortage": "20", "quantity_traded": "50", "deadweight_loss": "50"}),
    ("guide-4-floor", "price_control",
     {**EQ, "control_type": "floor", "control_price": "25"},
     {"surplus": "20", "quantity_traded": "50", "deadweight_loss": "50"}),
    ("guide-5-concentration", "market_concentration",
     {"firm_revenues": ["40", "25", "15", "10", "10"]},
     {"hhi": "2650", "cr4": "90"}),
    ("guide-6-costs", "cost_curves",
     {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5",
      "quantity": "20", "price": "40"},
     {"total_cost": "1400", "average_cost": "70", "average_variable_cost": "20",
      "average_fixed_cost": "50", "marginal_cost": "30",
      "total_revenue": "800", "profit": "-600"}),
    ("guide-7-profitmax", "profit_maximization",
     {"demand_intercept": "100", "demand_slope": "2", "fixed_cost": "100",
      "linear_cost": "10", "quadratic_cost": "0.5"},
     {"profit_maximizing_quantity": "18", "profit_maximizing_price": "64",
      "profit": "710", "lerner_index": "0.5625"}),
    ("guide-8-national-income", "national_income",
     {"consumption": "600", "investment": "150", "government_spending": "200",
      "exports": "120", "imports": "170", "net_factor_income": "20",
      "depreciation": "50", "gdp_deflator": "120", "population": "100"},
     {"gdp": "900", "gnp": "920", "nnp": "870", "gdp_per_capita": "9"}),
    ("guide-9-growth", "growth_rate",
     {"start_value": "100", "end_value": "200", "periods": "10"},
     {"total_growth": "1"}),
    ("guide-9-growth-practice", "growth_rate",
     {"start_value": "50", "end_value": "80", "periods": "6"},
     {"total_growth": "0.6"}),
    ("guide-10-inflation", "inflation_cpi",
     {"cpi_start": "120", "cpi_end": "126", "nominal_interest_rate": "0.07",
      "wage_start": "200", "wage_end": "210"},
     {"inflation_rate": "0.05"}),
    ("guide-11-unemployment", "unemployment_rate",
     {"labour_force": "500", "employed": "450", "working_age_population": "800"},
     {"unemployment_rate": "0.1", "labour_force_participation_rate": "0.625",
      "employment_population_ratio": "0.5625"}),
    ("guide-12-money", "money_multiplier",
     {"monetary_base": "200", "reserve_ratio": "0.2", "currency_drain_ratio": "0"},
     {"simple_money_multiplier": "5", "money_supply_simple": "1000"}),
    ("guide-13-fiscal", "fiscal_multiplier",
     {"mpc": "0.75", "tax_rate": "0.2", "government_spending_change": "80"},
     {"government_spending_multiplier": "2.5", "output_change": "200"}),
    ("guide-14-budget", "budget_debt",
     {"government_revenue": "300", "government_spending": "330",
      "interest_payments": "20", "debt_stock": "800", "nominal_gdp": "1600",
      "nominal_growth_rate": "0.04"},
     {"overall_balance": "-50", "primary_balance": "-30", "debt_to_gdp": "0.5"}),
    ("guide-15-gini", "gini_coefficient",
     {"incomes": ["10", "20", "30", "40"]},
     {"gini": "0.25", "mean_income": "25"}),
    ("guide-16-poverty", "poverty_measures",
     {"incomes": ["10", "20", "30", "40"], "poverty_line": "25"},
     {"headcount_ratio": "0.5", "poverty_gap": "0.2"}),
    ("guide-17-externality", "externality_pigouvian",
     {**EQ, "marginal_external_cost": "4"},
     {"social_quantity": "56", "pigouvian_tax": "4", "deadweight_loss": "8"}),
    ("guide-19-tariff", "tariff_welfare",
     {**EQ, "world_price": "10", "tariff_per_unit": "5"},
     {"domestic_price": "15", "tariff_revenue": "100", "total_dwloss": "50"}),
    ("guide-20-ppp", "exchange_rate_ppp",
     {"price_domestic": "5000", "price_foreign": "100", "nominal_rate": "55",
      "domestic_inflation": "0", "foreign_inflation": "0"},
     {"ppp_rate": "50", "real_exchange_rate": "1.1"}),
    ("guide-21-irp", "interest_rate_parity",
     {"spot_rate": "50", "domestic_rate": "0.06", "foreign_rate": "0.04",
      "time_to_maturity": "1", "domestic_inflation": "0", "foreign_inflation": "0"},
     {"implied_forward": "50.961538"}),
    ("guide-24-cournot", "cournot_duopoly",
     {"demand_intercept": "100", "demand_slope": "2",
      "marginal_cost_1": "10", "marginal_cost_2": "20"},
     {"quantity_1": "16.6667", "quantity_2": "11.6667", "price": "43.3333",
      "profit_1": "555.5556", "profit_2": "272.2222"}),
]


if __name__ == "__main__":
    unittest.main()

