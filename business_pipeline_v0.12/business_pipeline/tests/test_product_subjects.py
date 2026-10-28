"""The subject index is a testable catalogue, not a hand-waved menu.

Every launch id in `bp.product.subjects` must exist in the frozen contract,
every catalogue id must exist in the shipped registry, and the rail
Calculator's union must be exactly the subjects' compute tools.  A catalogue
change that drops an id therefore fails here instead of drifting silently in
the browser (the UI suite cannot see the JavaScript).

The product package still imports nothing from the frozen core; these tests
are allowed to read the frozen fixture and the registry as **data**, and to
import the core only to confirm that a preset launches the method it claims.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import api, subjects  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "frozen_contract.json")
REGISTRY = os.path.join(ROOT, "src", "bp", "data", "registry_v0_2.json")


def frozen():
    with open(FIXTURE, encoding="utf-8") as stream:
        return json.load(stream)


def registry_records():
    """The enriched registry records (the same ones `/api/frameworks` serves).

    Reading the raw JSON is not enough: `registry.load()` adds the template and
    implementation-status fields from the template catalogue, and those are
    the fields the subject pages display.  Importing it is a test-side
    privilege; the product package still reads only its committed slice.
    """
    from bp import registry

    return {record["id"]: record for record in registry.load()["records"]}


class SubjectCatalogueTest(unittest.TestCase):
    def test_the_gallery_declares_ten_subjects_and_a_cross_cutting_shelf(self):
        gallery = subjects.catalogue()
        self.assertEqual(gallery["format"], "bp-subjects/1")
        self.assertEqual(len(gallery["subjects"]), 10)
        self.assertEqual([row["id"] for row in gallery["subjects"]][:2], ["accounting", "finance"])
        cross = [row for row in gallery["subjects"] if row["cross_cutting"]]
        self.assertEqual([row["id"] for row in cross], ["research"])

    def test_the_rail_lists_every_subject_in_order_with_a_distinct_icon(self):
        rows = subjects.catalogue()["subjects"]
        self.assertEqual([row["id"] for row in rows],
                         ["accounting", "finance", "economics", "management", "entrepreneurship",
                          "operations", "supply-chain", "marketing", "people", "research"])
        icons = [row["icon"] for row in rows]
        self.assertTrue(all(icons), "a subject has no icon key")
        self.assertEqual(len(set(icons)), len(icons), "two subjects share an icon key")
        for row in rows:
            self.assertEqual(subjects.detail(row["id"])["icon"], row["icon"])

    def test_entrepreneurship_offers_venture_tools_and_canvas_records(self):
        page = subjects.detail("entrepreneurship")
        self.assertEqual(page["label"], "Entrepreneurship")
        self.assertTrue({"breakeven", "multi_product_breakeven", "unit_economics", "npv", "irr",
                         "discounted_payback"}.issubset({tool["method"] for tool in page["tools"]}))
        self.assertEqual([worksheet["template"] for worksheet in page["worksheets"]],
                         ["template_business_model_canvas", "template_lean_canvas",
                          "template_value_proposition_canvas", "template_swot", "template_marketing_plan"])
        self.assertTrue({"STR-15", "STR-16", "STR-17"}.issubset({row["id"] for row in page["catalogue"]}))

    def test_every_economics_tool_carries_student_notes_and_a_level(self):
        page = subjects.detail("economics")
        self.assertGreaterEqual(len(page["tools"]), 20)
        self.assertTrue(page["glossary"], "the Economics page has no glossary")
        levels = {tool["level"] for tool in page["tools"]}
        self.assertTrue({"intro", "intermediate", "advanced"}.issubset(levels),
                        "the Economics page does not separate intro, intermediate and advanced tools")
        for tool in page["tools"]:
            self.assertIn(tool["level"], ("intro", "intermediate", "advanced"), tool["key"])
            self.assertTrue(tool["formula"], "%s has no formula" % tool["key"])
            self.assertTrue(tool["steps"], "%s has no worked steps" % tool["key"])
            self.assertTrue(tool["common_mistakes"], "%s has no common mistakes" % tool["key"])
            self.assertIn("diagram", tool, tool["key"])
            for related in tool["related"]:
                self.assertIn(related, subjects.TOOL_INFO,
                              "%s points to unknown related tool %r" % (tool["key"], related))

    def test_the_five_new_micro_tools_have_diagrams(self):
        page = subjects.detail("economics")
        by_key = {tool["key"]: tool for tool in page["tools"]}
        for key in ("equilibrium", "elasticity", "taxincidence", "pricecontrol", "concentration"):
            self.assertIn(key, by_key, key)
            self.assertTrue(by_key[key]["diagram"], "%s has no diagram key" % key)


class ServedUiContractTest(unittest.TestCase):
    """The served page must carry the subject rail and the Enter affordance.

    The Python suite cannot run the browser, so this guards the static markup
    the client starts from: if another agent replaces the page, the ten subject
    links, the expandable rail toggle and the up-arrow run button either exist
    in the file or this test fails. It is a presence guard, not a DOM test.
    """

    def setUp(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            self.html = stream.read()

    def test_the_served_page_carries_every_subject_and_the_rail_toggle(self):
        for subject_id in ["accounting", "finance", "economics", "management", "entrepreneurship",
                           "operations", "supply-chain", "marketing", "people", "research"]:
            self.assertIn('href="#/subject/%s"' % subject_id, self.html)
            self.assertIn('data-subject="%s"' % subject_id, self.html)
        self.assertIn('id="railtoggle"', self.html)
        self.assertIn('aria-controls="rail"', self.html)
        self.assertIn('aria-label="Expand navigation"', self.html)
        self.assertIn("--rail-w-open:272px", self.html)
        self.assertIn("body.rail-open .railtoggle{justify-content:flex-end}", self.html)
        self.assertNotIn('class="rt-label"', self.html)
        self.assertNotIn(">Collapse<", self.html)
        self.assertIn('id="buildpill"', self.html)
        self.assertIn("v0.85", self.html)
        self.assertIn("levelhead", self.html)
        self.assertIn("studynote", self.html)
        self.assertIn("capcard .lvl", self.html)
        self.assertIn(".chatbtn{position:fixed;right:24px;bottom:24px;", self.html)
        self.assertIn("font-size:16.8px", self.html)

    def test_the_home_chat_uses_an_up_arrow_and_enter(self):
        self.assertIn('id="run"', self.html)
        self.assertIn('aria-label="Start the analysis"', self.html)
        self.assertIn('title="Start the analysis (Enter)"', self.html)
        self.assertIn('M12 19V5M6 11l6-6 6 6', self.html)
        for gone in ('id="preset"', 'id="method"', 'id="currency"', 'data-example', 'id="hero-sub"',
                     "Your cases", "Or choose a subject", "Enter to start"):
            self.assertNotIn(gone, self.html)

    def test_the_removed_panels_have_not_come_back(self):
        for gone in ('id="panel-frames"', 'id="panel-assistant"', 'data-panel="frames"', 'data-panel="assistant"'):
            self.assertNotIn(gone, self.html)

    def test_every_launch_id_exists_in_the_frozen_contract(self):
        from bp import templates  # test-side only

        contract = frozen()
        presets = set(contract["presets"])
        methods = set(contract["methods"]) | set(templates.TEMPLATES)
        for definition in subjects.SUBJECT_DEFS:
            for key in definition["tools"]:
                tool = subjects.TOOL_INFO[key]
                self.assertIn(tool["method"], methods,
                              "%s launches %s, which is not a frozen method" % (key, tool["method"]))
                if tool["preset"] is not None:
                    self.assertIn(tool["preset"], presets,
                                  "%s launches preset %s, which is not frozen" % (key, tool["preset"]))

    def test_every_preset_launches_the_method_it_claims(self):
        from bp import server  # test-side only; the product package never imports the core

        for definition in subjects.SUBJECT_DEFS:
            for key in definition["tools"]:
                tool = subjects.TOOL_INFO[key]
                if tool["preset"] is None:
                    continue
                self.assertIn(tool["preset"], server.PRESETS)
                self.assertEqual(server.PRESETS[tool["preset"]]["method"], tool["method"],
                                 "%s preset/method mismatch" % key)

    def test_every_worksheet_template_exists_and_matches_the_registry(self):
        from bp import templates  # test-side only

        records = registry_records()
        for subject_id in [definition["id"] for definition in subjects.SUBJECT_DEFS]:
            for worksheet in subjects.detail(subject_id)["worksheets"]:
                self.assertIn(worksheet["template"], templates.TEMPLATES)
                record = records[worksheet["catalogue_id"]]
                self.assertEqual(record.get("template"), worksheet["template"],
                                 "%s worksheet does not match the registry" % worksheet["catalogue_id"])

    def test_every_catalogue_id_exists_and_no_template_is_invented(self):
        records = registry_records()
        for definition in subjects.SUBJECT_DEFS:
            for catalogue_id in definition["catalogue_ids"]:
                self.assertIn(catalogue_id, records,
                              "%s names %s, which is not in the registry" % (definition["id"], catalogue_id))
            for row in subjects.detail(definition["id"])["catalogue"]:
                record = records[row["id"]]
                self.assertEqual(row["implementation_status"], record.get("implementation_status"))
                self.assertEqual(row["template"], record.get("template"))
                self.assertEqual(row["name"], record["name"])

    def test_no_catalogue_row_claims_a_worksheet_the_engine_does_not_have(self):
        for definition in subjects.SUBJECT_DEFS:
            worksheet_ids = set(definition["worksheets"])
            for row in subjects.detail(definition["id"])["catalogue"]:
                if row["template"] is not None:
                    self.assertIn(row["id"], worksheet_ids,
                                  "%s has a template but is not offered as a worksheet" % row["id"])

    def test_a_subject_page_has_tools_or_an_honest_catalogue(self):
        for definition in subjects.SUBJECT_DEFS:
            page = subjects.detail(definition["id"])
            self.assertTrue(page["tools"] or page["worksheets"] or page["catalogue"],
                            "%s has nothing to show" % definition["id"])
            for tool in page["tools"]:
                self.assertEqual(tool["kind"], "compute")
                self.assertTrue(tool["label"] and tool["what"])

    def test_an_unknown_subject_is_a_clear_refusal(self):
        with self.assertRaises(subjects.SubjectNotFound):
            subjects.detail("astrology")
        status, payload = api.handle("GET", "/api/cases/subjects/astrology")
        self.assertEqual(status, 404)
        self.assertIn("astrology", payload["error"])


class CalculatorGuardTest(unittest.TestCase):
    def test_the_calculator_union_is_exactly_the_subject_compute_tools(self):
        union = {tool["key"] for tool in subjects.compute_tools()}
        grouped = {}
        for group in subjects.calculator_groups()["groups"]:
            for tool in group["tools"]:
                grouped[tool["key"]] = tool
        self.assertEqual(set(grouped), union)
        self.assertEqual(len(grouped), len(subjects.compute_tools()))

    def test_the_calculator_has_eight_business_function_groups(self):
        payload = subjects.calculator_groups()
        self.assertEqual(payload["format"], "bp-calculator/1")
        self.assertEqual([group["id"] for group in payload["groups"]],
                         ["finance", "accounting", "statistics", "economics", "entrepreneurship",
                          "operations", "marketing", "people"])
        self.assertIn("computes nothing", payload["note"])
        self.assertIn("free-form arithmetic is not supported", payload["note"])

    def test_the_calculator_covers_every_frozen_method_or_says_why_not(self):
        from bp import methods  # test-side only

        launched = {tool["method"] for tool in subjects.compute_tools()}
        frozen_methods = {method["method_id"] for method in methods.list_methods()}
        self.assertEqual(frozen_methods - launched, set(),
                         "a frozen method is missing from the Calculator and subject pages")


class SubjectRouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-subject-routes-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_gallery_and_detail_are_served_without_computing_anything(self):
        status, gallery = api.handle("GET", "/api/cases/subjects")
        self.assertEqual(status, 200)
        self.assertEqual(len(gallery["subjects"]), 10)
        status, page = api.handle("GET", "/api/cases/subjects/accounting")
        self.assertEqual(status, 200)
        self.assertEqual(page["id"], "accounting")
        self.assertEqual({tool["method"] for tool in page["tools"]},
                         {"management_accounts", "ratio_analysis",
                          "breakeven", "multi_product_breakeven", "trial_balance_check"})

    def test_a_stored_case_is_filtered_by_the_methods_of_a_subject(self):
        status, stored = api.handle("POST", "/api/cases", product_fixtures.make_bundle())
        self.assertEqual(status, 201)
        status, finance = api.handle("GET", "/api/cases?subject=finance")
        self.assertEqual(status, 200)
        self.assertEqual([item["id"] for item in finance["cases"]], [stored["id"]])
        status, accounting = api.handle("GET", "/api/cases?subject=accounting")
        self.assertEqual(status, 200)
        self.assertEqual(accounting["cases"], [])
        status, unknown = api.handle("GET", "/api/cases?subject=astrology")
        self.assertEqual(status, 422)
        self.assertIn("astrology", unknown["error"])

    def test_the_calculator_route_is_get_only(self):
        status, payload = api.handle("GET", "/api/cases/calculator")
        self.assertEqual(status, 200)
        self.assertEqual(payload["format"], "bp-calculator/1")
        self.assertEqual(api.handle("POST", "/api/cases/calculator", {})[0], 405)


if __name__ == "__main__":
    unittest.main()

