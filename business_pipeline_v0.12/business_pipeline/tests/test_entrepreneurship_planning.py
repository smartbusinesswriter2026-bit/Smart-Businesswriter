"""The venture-planning computations and canvas worksheets (B-106/B-107).

Hand-checked arithmetic for the six planning methods, and structural tests for
the four canvas/plan templates: every item placed once, reproduced verbatim,
gaps named and no score produced.
"""

import re
import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, "src")
from bp import server, templates as T
from bp.methods import LIBRARY
from bp.orchestrator import Pipeline
from bp.product import subjects

YES = lambda spec: True

PROJECTION = {"start_units": "300", "price": "120", "unit_variable_cost": "55",
              "fixed_cost_per_period": "12000", "growth_rate": "0.05", "periods": "12"}
CAPTABLE = {"pre_money_valuation": "4000000", "investment": "1000000",
            "founders_shares": "1000000", "option_pool_pct": "0.10"}
FUNNEL = {"stages": [{"name": "store visits", "count": "10000"},
                     {"name": "inquiries", "count": "2500"},
                     {"name": "purchases", "count": "500"}], "spend": "25000"}
COHORT = {"cohort_sizes": ["200", "180", "150"],
          "retained": [["200", "140", "110", "90"], ["180", "130", "100", "60"], ["150", "120", "95", "70"]]}
DEMAND = {"prices": ["20", "25", "30", "35", "40"], "quantities": ["400", "340", "280", "220", "160"]}
INTENT = {"definitely": "120", "probably": "80", "maybe": "150", "never": "50",
          "target_population": "20000", "price": "250"}

NEW_METHODS = ("sales_projection", "cap_table_round", "sales_funnel", "cohort_retention",
               "demand_curve", "purchase_intent")
NEW_PRESETS = ("salesprojection", "captable", "funnel", "cohort", "demandcurve", "purchaseintent")
NEW_TEMPLATES = ("template_business_model_canvas", "template_lean_canvas",
                 "template_value_proposition_canvas", "template_marketing_plan")


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


class SalesProjection(unittest.TestCase):
    def m(self):
        return LIBRARY["sales_projection"]

    def test_arithmetic(self):
        out = self.m().impl(PROJECTION)
        self.assertEqual(out["units_1"], D(300))
        self.assertEqual(out["revenue_1"], D(36000))
        self.assertEqual(out["profit_1"], D(7500))
        self.assertEqual(out["units_2"], D("315.00"))
        self.assertEqual(out["total_fixed_cost"], D(144000))
        self.assertAlmostEqual(float(out["total_profit"]), 166383.967, places=3)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("sales_projection", PROJECTION))
        self.assertTrue(checks_pass("sales_projection", {**PROJECTION, "growth_rate": "0", "periods": "1"}))
        for inputs in ({**PROJECTION, "price": "0"}, {**PROJECTION, "start_units": "-1"},
                       {**PROJECTION, "periods": "0"}, {**PROJECTION, "periods": "25"},
                       {**PROJECTION, "growth_rate": "-1"}, {**PROJECTION, "fixed_cost_per_period": "-1"}):
            self.assertTrue(blocked("sales_projection", inputs), inputs)

    def test_pipeline_delivers_and_reports_the_horizon(self):
        d = delivered({"objective": "Projection", "method": "sales_projection", "currency": "PHP",
                       "period": "monthly", "inputs": PROJECTION})
        self.assertIn("total revenue", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class CapTableRound(unittest.TestCase):
    def m(self):
        return LIBRARY["cap_table_round"]

    def test_arithmetic(self):
        out = self.m().impl(CAPTABLE)
        self.assertEqual((out["post_money_valuation"], out["price_per_share"], out["new_shares"]),
                         (D(5000000), D(4), D(250000)))
        self.assertEqual(out["investor_pct"], D("0.18"))
        self.assertAlmostEqual(float(out["founder_pct"]), 0.72, places=12)
        self.assertEqual(out["pool_pct_actual"], D("0.1"))
        self.assertAlmostEqual(float(out["founder_dilution"]), 0.28, places=12)

    def test_no_pool_means_no_pool_dilution(self):
        out = self.m().impl({**CAPTABLE, "option_pool_pct": "0"})
        self.assertEqual(out["option_pool_shares"], D(0))
        self.assertEqual(out["investor_pct"], D("0.2"))
        self.assertEqual(out["founder_pct"], D("0.8"))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("cap_table_round", CAPTABLE))
        self.assertTrue(checks_pass("cap_table_round", {**CAPTABLE, "option_pool_pct": "0"}))
        for inputs in ({**CAPTABLE, "pre_money_valuation": "0"}, {**CAPTABLE, "investment": "0"},
                       {**CAPTABLE, "founders_shares": "0"}, {**CAPTABLE, "option_pool_pct": "1"}):
            self.assertTrue(blocked("cap_table_round", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Round", "method": "cap_table_round", "currency": "PHP",
                       "period": "point in time", "inputs": CAPTABLE})
        self.assertIn("post-money", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class SalesFunnel(unittest.TestCase):
    def m(self):
        return LIBRARY["sales_funnel"]

    def test_arithmetic(self):
        out = self.m().impl(FUNNEL)
        self.assertEqual((out["count_1"], out["customers"], out["drop_off"]), (D(10000), D(500), D(9500)))
        self.assertEqual((out["conversion_1"], out["conversion_2"], out["overall_conversion"]),
                         (D("0.25"), D("0.2"), D("0.05")))
        self.assertEqual(out["cac"], D(50))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("sales_funnel", FUNNEL))
        self.assertTrue(checks_pass("sales_funnel", {"stages": FUNNEL["stages"]}))
        for inputs in ({"stages": [{"name": "one", "count": "10"}]},
                       {"stages": [{"name": "a", "count": "10"}, {"name": "b", "count": "11"}]},
                       {"stages": [{"name": "a", "count": "0"}, {"name": "b", "count": "0"}]},
                       {"stages": [{"name": "", "count": "10"}, {"name": "b", "count": "5"}]},
                       {"stages": FUNNEL["stages"], "spend": "-1"}):
            self.assertTrue(blocked("sales_funnel", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Funnel", "method": "sales_funnel", "currency": "PHP",
                       "period": "monthly", "inputs": FUNNEL})
        self.assertIn("overall conversion", d.report.lower())
        self.assertIn("acquisition cost", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class CohortRetention(unittest.TestCase):
    def m(self):
        return LIBRARY["cohort_retention"]

    def test_arithmetic(self):
        out = self.m().impl(COHORT)
        self.assertEqual(out["retention_1"], D(1))
        self.assertAlmostEqual(float(out["retention_2"]), 390 / 530, places=12)
        self.assertAlmostEqual(float(out["retention_4"]), 220 / 530, places=12)
        self.assertAlmostEqual(float(out["average_retention"]), (1 + 390 / 530 + 305 / 530 + 220 / 530) / 4, places=12)
        self.assertAlmostEqual(float(out["average_lifetime"]), 1 + 390 / 530 + 305 / 530 + 220 / 530, places=12)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("cohort_retention", COHORT))
        for inputs in ({"cohort_sizes": ["100"], "retained": [["100", "80"], ["50", "40"]]},
                       {"cohort_sizes": ["100"], "retained": [["100", "101"]]},
                       {"cohort_sizes": ["0"], "retained": [["0"]]},
                       {"cohort_sizes": ["100"], "retained": [["100", "-1"]]}):
            self.assertTrue(blocked("cohort_retention", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Retention", "method": "cohort_retention", "currency": "PHP",
                       "period": "monthly", "inputs": COHORT})
        self.assertIn("retention", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class DemandCurve(unittest.TestCase):
    def m(self):
        return LIBRARY["demand_curve"]

    def test_arithmetic(self):
        out = self.m().impl(DEMAND)
        self.assertEqual(out["slope"], D(-12))
        self.assertEqual(out["intercept"], D(640))
        self.assertEqual(out["r_squared"], D(1))
        self.assertAlmostEqual(float(out["revenue_max_price"]), 26.6666667, places=6)
        self.assertEqual(out["revenue_max_quantity"], D(320))
        self.assertAlmostEqual(float(out["elasticity_at_mean"]), -12 * 30 / 280, places=12)

    def test_a_positive_slope_omits_the_revenue_maximum_rather_than_inventing_one(self):
        out = self.m().impl({"prices": ["1", "2", "3"], "quantities": ["10", "20", "30"]})
        self.assertGreater(out["slope"], 0)
        self.assertNotIn("revenue_max_price", out)

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("demand_curve", DEMAND))
        self.assertTrue(checks_pass("demand_curve", {"prices": ["1", "2", "3"], "quantities": ["10", "20", "30"]}))
        for inputs in ({"prices": ["1", "2"], "quantities": ["10", "20"]},
                       {"prices": ["1", "2", "3"], "quantities": ["10", "20"]},
                       {"prices": ["2", "2", "2"], "quantities": ["10", "20", "30"]},
                       {"prices": ["1", "2", "3"], "quantities": ["10", "10", "10"]}):
            self.assertTrue(blocked("demand_curve", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Demand", "method": "demand_curve", "currency": "PHP",
                       "period": "per observation", "inputs": DEMAND})
        self.assertIn("slope", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class PurchaseIntent(unittest.TestCase):
    def m(self):
        return LIBRARY["purchase_intent"]

    def test_arithmetic(self):
        out = self.m().impl(INTENT)
        self.assertEqual(out["respondents"], D(400))
        self.assertEqual(out["weighted_intenders"], D(135))
        self.assertEqual(out["intent_rate"], D("0.3375"))
        self.assertEqual(out["projected_buyers"], D(6750))
        self.assertEqual(out["projected_revenue"], D(1687500))

    def test_checks_and_refusals(self):
        self.assertTrue(checks_pass("purchase_intent", INTENT))
        self.assertTrue(checks_pass("purchase_intent", {"definitely": "10", "probably": "0", "maybe": "0", "never": "0"}))
        for inputs in ({"definitely": "0", "probably": "0", "maybe": "0", "never": "0"},
                       {"definitely": "-1", "probably": "0", "maybe": "0", "never": "0"},
                       {**INTENT, "definitely_weight": "1.5"},
                       {**INTENT, "target_population": "0"}):
            self.assertTrue(blocked("purchase_intent", inputs), inputs)

    def test_pipeline_delivers(self):
        d = delivered({"objective": "Intent", "method": "purchase_intent", "currency": "PHP",
                       "period": "cross_section", "inputs": INTENT})
        self.assertIn("intent rate", d.report.lower())
        self.assertNotIn("{{ref:", d.report)


class PresetDelivery(unittest.TestCase):
    def test_every_new_preset_delivers(self):
        for preset in NEW_PRESETS:
            p = server.PRESETS[preset]
            d = delivered({"objective": p["objective"], "method": p["method"], "inputs": p["inputs"],
                           "currency": p.get("currency"), "period": p.get("period")})
            self.assertNotIn("{{ref:", d.report, preset)
            self.assertTrue(all(ok for _, ok, *_ in d.appendix["tests"]), preset)


class CanvasTemplates(unittest.TestCase):
    def test_every_canvas_example_passes_its_checks_and_reports_gaps(self):
        for kind in NEW_TEMPLATES:
            result = T.run_template(kind, T.EXAMPLES[kind]["inputs"])
            self.assertTrue(all(ok for _, ok in result["results"]), (kind, result["results"]))
            audit = result["analysis"]["audit"]
            if kind != "template_value_proposition_canvas":
                self.assertTrue(audit["empty_blocks"], kind)
            self.assertNotIn("score", result["analysis"])
            self.assertNotIn("score", result["counts"])

    def test_the_listing_reproduces_every_item_verbatim(self):
        for kind in NEW_TEMPLATES:
            example = T.EXAMPLES[kind]
            result = T.run_template(kind, example["inputs"])
            for items in example["inputs"]["blocks"].values():
                for item in items:
                    self.assertIn(item["text"], result["listing"], kind)

    def test_links_are_kept_and_unlinked_items_are_reported(self):
        result = T.run_template("template_value_proposition_canvas",
                                T.EXAMPLES["template_value_proposition_canvas"]["inputs"])
        self.assertEqual(len(result["analysis"]["links"]), 2)
        self.assertEqual(result["analysis"]["counts"]["n_unlinked"], 2)

    def test_validation_errors_are_actionable(self):
        cases = [
            ({"blocks": {}}, "'blocks' must be an object"),
            ({"blocks": {"no_such_block": [{"text": "x"}]}}, "unknown block"),
            ({"blocks": {"customer_segments": [{"text": ""}]}}, "'text' is required"),
            ({"blocks": {"customer_segments": [{"text": "x", "provenance": "sourced"}]}}, "needs a 'source'"),
            ({"blocks": {"customer_segments": [{"text": "x", "id": "A"}, {"text": "y", "id": "A"}]}}, "duplicate id"),
            ({"blocks": {"customer_segments": [{"text": "x"}]}, "links": [{"from": "E1", "to": "E9"}]}, "unknown item ids"),
            ({"blocks": {"customer_segments": [{"text": "x"}] * 21}}, "at most 20"),
        ]
        for inputs, fragment in cases:
            errs = T.validate("template_business_model_canvas", inputs)
            self.assertTrue(errs, inputs)
            self.assertTrue(any(fragment in e for e in errs), (fragment, errs))

    def test_no_raw_digits_leak_into_the_narrative(self):
        for kind in NEW_TEMPLATES:
            result = T.run_template(kind, T.EXAMPLES[kind]["inputs"])
            stripped = re.sub(r"\{\{ref:[^}]*\}\}", "", result["narrative"])
            self.assertIsNone(re.search(r"\d", stripped), kind)

    def test_rendering_is_deterministic(self):
        for kind in NEW_TEMPLATES:
            a = T.run_template(kind, T.EXAMPLES[kind]["inputs"])
            b = T.run_template(kind, T.EXAMPLES[kind]["inputs"])
            self.assertEqual(a["narrative"], b["narrative"], kind)
            self.assertEqual(a["listing"], b["listing"], kind)

    def test_describe_exposes_the_t4_contract(self):
        for kind in NEW_TEMPLATES:
            desc = T.describe(kind)
            self.assertEqual(desc["tier"], "T4")
            self.assertTrue(desc["input_help"]["blocks"])
            self.assertTrue(desc["defaults"])
            self.assertTrue(desc["limitations"])
            self.assertTrue(desc["planned_checks"])
            self.assertTrue(desc["example_request"]["inputs"]["blocks"])

    def test_describe_exposes_the_block_editor_metadata(self):
        for kind in NEW_TEMPLATES:
            desc = T.describe(kind)
            self.assertTrue(desc["blocks"], kind)
            for block in desc["blocks"]:
                self.assertTrue(block["label"], kind)
                self.assertTrue(block["prompt"], kind)
                self.assertRegex(block["prefix"], r"^[A-Z]{2}$", kind)
            prefixes = [b["prefix"] for b in desc["blocks"]]
            self.assertEqual(len(prefixes), len(set(prefixes)), kind)


class ShelfWiring(unittest.TestCase):
    def test_the_entrepreneurship_page_carries_the_planning_tools_and_worksheets(self):
        page = subjects.detail("entrepreneurship")
        methods = {tool["method"] for tool in page["tools"]}
        for method in NEW_METHODS:
            self.assertIn(method, methods, method)
        templates = {w["template"] for w in page["worksheets"]}
        for kind in NEW_TEMPLATES:
            self.assertIn(kind, templates, kind)

    def test_management_and_marketing_offer_the_canvases_they_list(self):
        self.assertIn("STR-15", [w["catalogue_id"] for w in subjects.detail("management")["worksheets"]])
        self.assertIn("MKT-02", [w["catalogue_id"] for w in subjects.detail("marketing")["worksheets"]])

    def test_the_new_terms_are_in_the_glossary(self):
        terms = {row["term"] for row in subjects.detail("entrepreneurship")["glossary"]}
        for term in ("Cap table", "Dilution", "Funnel", "Cohort", "Purchase intent", "Positioning"):
            self.assertIn(term, terms)

    def test_every_new_tool_has_notes_group_and_period(self):
        page = subjects.detail("entrepreneurship")
        by_key = {t["key"]: t for t in page["tools"]}
        for key in ("salesprojection", "captable", "funnel", "cohort", "demandcurve", "purchaseintent"):
            tool = by_key[key]
            self.assertTrue(tool["group"], key)
            self.assertTrue(tool["period"], key)
            self.assertTrue(tool["formula"], key)
            self.assertTrue(tool["steps"], key)
            self.assertTrue(tool["common_mistakes"], key)


if __name__ == "__main__":
    unittest.main()
