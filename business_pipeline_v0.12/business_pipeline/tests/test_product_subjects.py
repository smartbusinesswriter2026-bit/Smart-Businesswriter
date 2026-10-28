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
    def test_the_gallery_declares_eleven_subjects_and_a_cross_cutting_shelf(self):
        gallery = subjects.catalogue()
        self.assertEqual(gallery["format"], "bp-subjects/1")
        self.assertEqual(len(gallery["subjects"]), 11)
        self.assertEqual([row["id"] for row in gallery["subjects"]][:2], ["accounting", "finance"])
        cross = [row for row in gallery["subjects"] if row["cross_cutting"]]
        self.assertEqual([row["id"] for row in cross], ["research"])

    def test_the_rail_lists_every_subject_in_order_with_a_distinct_icon(self):
        rows = subjects.catalogue()["subjects"]
        self.assertEqual([row["id"] for row in rows],
                         ["accounting", "finance", "economics", "management", "project-management",
                          "entrepreneurship", "operations", "supply-chain", "marketing", "people", "research"])
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
                          "template_value_proposition_canvas", "template_swot",
                          "template_blue_ocean_errc", "template_marketing_plan"])
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


class FrameworkMatchTest(unittest.TestCase):
    """The instruction-first entry is a reading aid, not an analysis."""

    def test_a_competitive_case_suggests_swot_or_five_forces(self):
        result = subjects.match_frameworks(
            "We need to weigh our strengths and weaknesses against competitors and new opportunities")
        self.assertTrue(result["matches"])
        self.assertIn(result["matches"][0]["template"], ("template_swot", "template_five_forces"))
        self.assertTrue(result["matches"][0]["why"])
        self.assertTrue(result["matches"][0]["matched_terms"])

    def test_a_case_about_people_and_change_suggests_a_change_worksheet_or_none_but_never_invents_one(self):
        result = subjects.match_frameworks("Our staff resist the new process and we need a change plan")
        for match in result["matches"]:
            self.assertIn(match["template"], {worksheet["template"] for worksheet in subjects.WORKSHEETS.values()})

    def test_the_matcher_says_so_when_nothing_fits(self):
        result = subjects.match_frameworks("zzzz qqqq")
        self.assertEqual(result["matches"], [])
        self.assertTrue(result["none_reason"])
        self.assertEqual(subjects.match_frameworks("")["matches"], [])

    def test_the_matcher_route_is_post_only_and_needs_text(self):
        status, payload = api.handle("POST", "/api/cases/match", {"text": "pricing and customers"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["matches"])
        self.assertEqual(api.handle("POST", "/api/cases/match", {})[0], 422)
        self.assertEqual(api.handle("GET", "/api/cases/match")[0], 405)


class CatalogueHonestyTest(unittest.TestCase):
    """A record must say what the product can do with it, and say it once."""

    def test_project_management_owns_the_pm_records_and_the_appraisal_tools(self):
        page = subjects.detail("project-management")
        pm_ids = {"PM-%02d" % n for n in range(1, 17)}
        worksheet_ids = {"PM-05", "PM-06", "PM-09", "PM-10", "PM-15", "PM-16"}
        self.assertEqual({row["id"] for row in page["records"]}, pm_ids - worksheet_ids,
                         "the Project management page drops or repeats a PM record")
        self.assertEqual([row["catalogue_id"] for row in page["worksheets"]],
                         ["PM-05", "PM-09", "PM-10", "PM-06", "PM-15", "PM-16"],
                         "the six PM worksheets are missing or out of order")
        self.assertEqual([tool["key"] for tool in page["tools"]],
                         ["npv", "irr", "dpayback", "projectmetrics", "scenario", "case_decision",
                          "forecast", "cpm", "evm", "leveling", "crashing", "calendar",
                          "multiproject", "schedrisk", "decisiontree", "realoption", "mcda", "montecarlo"])
        for tool in page["tools"]:
            self.assertTrue(tool["group"], "%s has no project group" % tool["key"])
            self.assertTrue(tool["period"], "%s has no period badge" % tool["key"])
            self.assertTrue(tool["formula"] and tool["steps"] and tool["common_mistakes"], tool["key"])
        self.assertTrue(page["guidance"], "the page has no student guidance")
        self.assertGreaterEqual(len(page["glossary"]), 15, "the page has no usable glossary")
        self.assertEqual(page["discipline_labels"], ["Project delivery and governance"])
        self.assertGreaterEqual(len(page["start_steps"]), 4, "the PM page has no start-here steps")
        self.assertTrue(page["does_not"], "the PM page does not say what it cannot do")
        self.assertTrue(all(tool["need"] for tool in page["tools"]), "a PM tool has no 'you will need' line")
        self.assertTrue(all(sheet["before"] for sheet in page["worksheets"]), "a PM worksheet has no 'before you start' line")
        management = {row["id"] for row in subjects.detail("management")["catalogue"]}
        self.assertFalse((pm_ids - worksheet_ids) & management, "Management still claims the project records")

    def test_economics_declares_the_impact_evaluation_records(self):
        page = subjects.detail("economics")
        ids = {row["id"] for row in page["catalogue"]}
        self.assertTrue({"IMP-03", "IMP-04", "IMP-05", "IMP-06", "IMP-07"} <= ids)

    def test_a_worksheet_is_not_repeated_as_a_catalogue_row(self):
        for definition in subjects.SUBJECT_DEFS:
            page = subjects.detail(definition["id"])
            worksheets = {worksheet["catalogue_id"] for worksheet in page["worksheets"]}
            records = {row["id"] for row in page["records"]}
            theories = {row["id"] for row in page["theories"]}
            self.assertFalse(worksheets & records, definition["id"])
            self.assertFalse(worksheets & theories, definition["id"])
            self.assertTrue(set(definition["catalogue_ids"]) <= (worksheets | records | theories),
                            "%s does not show every assigned record" % definition["id"])
            self.assertEqual(records | theories, set(definition["catalogue_ids"]) - worksheets,
                             "%s repeats or drops a catalogue record" % definition["id"])

    def test_theories_are_reading_lenses_not_a_build_backlog(self):
        for definition in subjects.SUBJECT_DEFS:
            for row in subjects.detail(definition["id"])["theories"]:
                self.assertEqual(row["form"], "theory", row["id"])
                self.assertEqual(row["status_short"], "Reading lens", row["id"])
                self.assertIn("not a worksheet by design", row["status_note"], row["id"])
                self.assertNotIn("not implemented", row["status_note"].lower(), row["id"])

    def test_a_read_only_framework_does_not_say_not_implemented(self):
        for definition in subjects.SUBJECT_DEFS:
            for row in subjects.detail(definition["id"])["records"]:
                if row["form"] == "read_only" and row["type"] in ("F", "M"):
                    self.assertNotIn("not implemented", row["status_note"].lower(), row["id"])
                    self.assertIn("read-only record", row["status_note"], row["id"])

    def test_an_unbuilt_quantitative_method_is_not_called_a_missing_worksheet(self):
        seen = 0
        for definition in subjects.SUBJECT_DEFS:
            for row in subjects.detail(definition["id"])["records"]:
                if row["form"] == "read_only" and row["type"] == "Q":
                    self.assertEqual(row["status_short"], "Method not built", row["id"])
                    seen += 1
        self.assertGreater(seen, 0, "no unbuilt quantitative record was exercised")

    def test_every_record_row_carries_the_text_the_page_shows(self):
        for definition in subjects.SUBJECT_DEFS:
            page = subjects.detail(definition["id"])
            for row in page["records"] + page["theories"]:
                self.assertTrue(row["id"] and row["name"], definition["id"])
                self.assertTrue(row["status_short"] and row["status_note"], row["id"])
                self.assertTrue(row["structures"], row["id"])
                self.assertTrue(row["disciplines"], row["id"])

    def test_registry_form_and_status_are_derived_consistently(self):
        from bp import registry

        for record in registry.load()["records"]:
            if record["type"] == "T":
                self.assertEqual(record["form"], "theory", record["id"])
                self.assertNotIn("not implemented", record["implementation_status"].lower(), record["id"])
            elif record["template"]:
                self.assertEqual(record["form"], "worksheet", record["id"])
                self.assertIn("worksheet available", record["implementation_status"], record["id"])
            elif record["linked_methods"]:
                self.assertEqual(record["form"], "computed", record["id"])
            elif record["type"] == "Q":
                self.assertEqual(record["implementation_status"], "not implemented", record["id"])
            else:
                self.assertEqual(record["form"], "read_only", record["id"])
                self.assertIn("read-only record", record["implementation_status"], record["id"])

    def test_every_subject_carries_a_student_guide(self):
        for row in subjects.catalogue()["subjects"]:
            page = subjects.detail(row["id"])
            self.assertTrue(page.get("guidance"), row["id"])
            self.assertGreaterEqual(len(page.get("start_steps") or []), 3, row["id"])
            self.assertGreaterEqual(len(page.get("does_not") or []), 2, row["id"])


class ServedUiContractTest(unittest.TestCase):
    """The served page must carry the subject rail and the Enter affordance.

    The Python suite cannot run the browser, so this guards the static markup
    the client starts from: if another agent replaces the page, the eleven subject
    links, the expandable rail toggle and the up-arrow run button either exist
    in the file or this test fails. It is a presence guard, not a DOM test.
    """

    def setUp(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            self.html = stream.read()

    def test_the_served_page_carries_every_subject_and_the_rail_toggle(self):
        for subject_id in ["accounting", "finance", "economics", "management", "project-management",
                           "entrepreneurship", "operations", "supply-chain", "marketing", "people", "research"]:
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
        self.assertRegex(self.html, r'id="buildpill"[^>]*>v\d+\.\d+<',
                         "the build pill must carry the served version")
        self.assertIn("levelhead", self.html)
        self.assertIn("studynote", self.html)
        self.assertIn("capcard .lvl", self.html)
        self.assertIn("function worksheetForm", self.html)
        self.assertIn("function collectWorksheetInputs", self.html)
        self.assertIn('const id = "wb-" + b.key', self.html)
        self.assertIn('id="wlinks"', self.html)

    def test_the_rail_carries_the_portfolio_lab_above_the_calculator(self):
        """The Portfolio Lab is the fourteenth rail item and sits above the Calculator.

        The rail order is contract: Portfolio is a workspace of its own, not a
        subject, so it lives in the rail foot with the Calculator and the other
        cross-cutting tools.
        """
        self.assertIn('data-panel="portfolio"', self.html)
        self.assertIn('href="#/portfolio"', self.html)
        self.assertIn('<span class="railtext">Portfolio</span>', self.html)
        self.assertIn('id="panel-portfolio"', self.html)
        self.assertIn("RENDERERS.portfolio", self.html)
        self.assertIn('"portfolio"', self.html.split("const PANELS = ")[1].split("];")[0])
        self.assertLess(self.html.index('data-panel="portfolio"'), self.html.index('data-panel="calculator"'))
        self.assertIn('/api/portfolios', self.html)
        self.assertIn("<strong>Portfolio</strong> for a dated valuation", self.html)

    def test_no_reviewer_surface_remains_in_the_served_page(self):
        for gone in ('data-tab="signoff"', "Reviewer name", "Sign-off", "Review status", "pending_named_reviewer"):
            self.assertNotIn(gone, self.html, "reviewer surface still present: " + gone)
        self.assertIn("not teacher-approved", self.html)

    def test_worksheet_drafts_and_the_worksheet_export_are_present(self):
        self.assertIn("bp-ws-draft-", self.html)
        self.assertIn("discardWorksheetDraft", self.html)
        self.assertIn("Download the worksheet (Word)", self.html)
        self.assertIn("saveWorksheetDraft", self.html)
        self.assertIn("restoreWorksheetDraft", self.html)
        self.assertIn(".chatbtn{position:fixed;right:24px;bottom:24px;", self.html)
        self.assertIn("font-size:16.8px", self.html)
        # Student orientation: a first-run explainer and structured table editors.
        self.assertIn("How it works", self.html)
        self.assertIn("Start here", self.html)
        self.assertIn("Which one do I need?", self.html)
        self.assertIn("Student guide", self.html)
        self.assertIn("Guided paper", self.html)
        self.assertIn("Before you start", self.html)
        self.assertIn('data-rows="', self.html)
        self.assertIn("function rowsEditor", self.html)
        self.assertIn("View the Gantt", self.html)
        self.assertIn("Download spreadsheet", self.html)
        self.assertIn("Key numbers", self.html)
        self.assertIn("What this means", self.html)
        self.assertIn("function treeEditor", self.html)
        self.assertIn("function projectsEditor", self.html)
        self.assertIn("function mcdaEditor", self.html)
        self.assertIn("data-tree", self.html)
        self.assertIn("data-projects", self.html)
        self.assertIn("data-mcda", self.html)
        # Solid text: secondary and tertiary copy use the primary ink, not grey.
        self.assertIn("--text:#0C243E; --text-2:#0C243E; --text-3:#0C243E;", self.html)

    def test_the_business_case_tile_has_a_template_editor_and_the_calculator_delegates_to_it(self):
        """`case_decision` is a template, not a frozen method, so the generic
        schema form used to say "no inputs" and drop the student's alternatives.
        The page must carry the dedicated facts/alternatives editor instead."""
        for marker in ("function caseDecisionForm", "function readCaseDecision",
                       "data-casedecision", "data-addcasefact", "data-addcasealt",
                       "data-casecashflows", "data-caserule"):
            self.assertIn(marker, self.html)
        self.assertIn('if (tool.method === "case_decision") { openTool(tool); return; }', self.html)

    def test_the_schema_form_uses_choices_and_comma_lists_where_the_method_declares_them(self):
        self.assertIn('data-type="enum"', self.html)
        self.assertIn('type === "value_list"', self.html)
        self.assertIn('type === "value_matrix"', self.html)

    def test_frameworks_come_before_computation_and_too_many_get_a_picker(self):
        """The page puts no-computation worksheets first, then computed tools, and
        offers one picker across every framework when the shelf is long."""
        self.assertIn("Frameworks without computation", self.html)
        self.assertIn(">With computation<", self.html)
        self.assertIn('id="frameworkpick"', self.html)
        self.assertIn('id="casebrief"', self.html)
        self.assertIn("/api/cases/match", self.html)
        self.assertNotIn('"Catalogue " + esc(item.catalogue_id)', self.html)
        self.assertLess(self.html.index("Frameworks without computation"), self.html.index(">With computation<"))

    def test_the_home_chat_uses_an_up_arrow_and_enter(self):
        self.assertIn('id="run"', self.html)
        self.assertIn('aria-label="Start the analysis"', self.html)
        self.assertIn('title="Start the analysis (Enter)"', self.html)
        self.assertIn('M12 19V5M6 11l6-6 6 6', self.html)
        for gone in ('id="preset"', 'id="method"', 'id="currency"', 'data-example', 'id="hero-sub"',
                     "Your cases", "Or choose a subject", "Enter to start"):
            self.assertNotIn(gone, self.html)

    def test_every_subject_page_offers_the_shared_source_finder(self):
        self.assertIn("function sourceFinderBox", self.html)
        self.assertIn('id="sourceq"', self.html)
        self.assertIn("/api/cases/sources/search", self.html)
        self.assertIn("/api/cases/sources/web", self.html)
        self.assertIn("Find sources", self.html)
        self.assertIn("Vetted sites for", self.html)
        self.assertIn('id="drafttemplate"', self.html)
        self.assertIn("/api/cases/worksheets/draft", self.html)
        self.assertIn("Draft review", self.html)
        self.assertIn("Run the drafted worksheet", self.html)
        self.assertIn("Download the report (Word)", self.html)
        self.assertIn("/api/cases/worksheets/report", self.html)
        self.assertIn("Browse vetted sources", self.html)
        self.assertIn('id="sitecategory"', self.html)
        self.assertIn("browseVettedSources", self.html)
        self.assertIn('id="reportstyle"', self.html)
        self.assertIn("APA 7", self.html)
        self.assertIn("Harvard", self.html)
        self.assertIn("Recent (last 10 years)", self.html)
        self.assertIn('id="sourcerecent"', self.html)
        self.assertIn('href="#/chat"', self.html)
        self.assertIn('id="panel-chat"', self.html)
        self.assertIn('id="chatout"', self.html)
        self.assertIn('id="chatstart"', self.html)
        self.assertIn("/api/cases/chat", self.html)
        self.assertIn("function renderChat", self.html)
        self.assertIn('id="chatframework"', self.html)
        self.assertIn("PESTEL + SWOT", self.html)

    def test_worksheets_never_show_raw_json_to_the_user(self):
        """A student fills a guided form; the page never exposes the input object."""
        self.assertNotIn("Worksheet inputs (JSON)", self.html)
        self.assertNotIn('id="ws-json"', self.html)
        for function in ("fiveForcesForm", "swotForm", "matrixForm", "vrioForm", "bindWorksheetForm"):
            self.assertIn("function " + function, self.html)
        self.assertIn("Build the grid", self.html)
        self.assertIn("Add another resource", self.html)

    def test_the_removed_panels_have_not_come_back(self):
        for gone in ('id="panel-frames"', 'id="panel-assistant"', 'data-panel="frames"', 'data-panel="assistant"'):
            self.assertNotIn(gone, self.html)

    def test_the_rail_launcher_is_named_the_business_calculator(self):
        """The owner renamed the feature: the served page must say it everywhere.

        The route, the panel id and the JS identifiers stay `calculator` (they
        are contract, not copy); every label a reader sees says "Business
        Calculator", and the bare name may not come back.
        """
        self.assertIn('<span class="railtext">Business Calculator</span>', self.html)
        self.assertIn('<h2 id="calculator-title">Business Calculator</h2>', self.html)
        self.assertIn("Business Calculator: launch any financial or business calculation", self.html)
        self.assertIn("Search the Business Calculator", self.html)
        self.assertIn("Open the Business Calculator", self.html)
        self.assertIn("The Business Calculator arranges the inputs", self.html)
        self.assertIn("What this Business Calculator is", self.html)
        self.assertNotIn('<span class="railtext">Calculator</span>', self.html)
        self.assertNotIn('<h2 id="calculator-title">Calculator</h2>', self.html)
        self.assertNotIn("Open the Calculator", self.html)
        # the contract surface is unchanged by the rename
        self.assertIn('href="#/calculator"', self.html)
        self.assertIn('id="panel-calculator"', self.html)

    def test_the_business_calculator_shell_has_a_display_and_a_keypad(self):
        """P1 of docs/proposals/BUSINESS_CALCULATOR_DESIGN.md: the calculator shell.

        The panel has to look like a calculator (display, keypad, "=") while the
        engine still does every sum. These are presence guards: the Python suite
        cannot run the page, so it asserts the parts exist and are wired to the
        session route rather than to any local arithmetic.
        """
        for present in ('id="calcgrid"', 'id="calcline"', 'aria-live="polite"',
                        'id="calcpad"', 'id="calceq"', 'id="calcinputs"',
                        'id="calcreset"', 'id="calcback"', 'id="calclimits"'):
            self.assertIn(present, self.html)
        self.assertIn("Bare arithmetic", self.html)
        self.assertIn("Tax law", self.html)
        self.assertIn("Market data", self.html)
        for builder in ("function buildCalcPad()", "function calcKey(", "function calcRun(",
                        "function renderCalcLine()", "function selectCalcTool(",
                        "function calcFitOf("):
            self.assertIn(builder, self.html)

    def test_the_calculator_never_computes_in_the_browser(self):
        for forbidden in ("eval(", "new Function", "parseFloat(", "parseInt("):
            self.assertNotIn(forbidden, self.html, "the page must not evaluate expressions")
        # "=" runs the normal two-call sequence; nothing is rendered before a delivery
        self.assertIn('post("/api/sessions", body)', self.html)
        self.assertIn('post("/api/sessions/" + current.id + "/confirm", {})', self.html)
        # the keypad only ever writes text into a field
        self.assertIn('state.calcValues[el.id.replace(/^in-/, "")] = el.value;', self.html)

    def test_every_calculator_run_is_recorded_as_a_case(self):
        self.assertIn("function recordCalcCase(session)", self.html)
        self.assertIn('post("/api/cases", caseBundle(session))', self.html)
        self.assertIn("await recordCalcCase(current)", self.html)
        self.assertIn("Open the recorded case", self.html)

    def test_the_keypad_is_off_for_list_and_worksheet_tools(self):
        self.assertIn('if (tool.kind === "worksheet" || tool.method === "management_accounts") return "C";', self.html)
        self.assertIn('b.disabled = fit !== "A";', self.html)
        self.assertIn('$("#calceq").disabled = fit === "C";', self.html)
        self.assertIn('class="fitbadge ', self.html)

    def test_the_calculator_can_be_asked_in_words_only_through_the_router(self):
        """P3: the chat posts the sentence to the product layer and renders its answer."""
        for present in ('id="calcchat"', 'id="calcask"', 'id="calcaskgo"', 'id="calcmode-ask"'):
            self.assertIn(present, self.html)
        self.assertIn('post("/api/cases/calculator/plan", { text: text })', self.html)
        self.assertIn("function calcAsk()", self.html)
        self.assertIn("function planHtml(payload)", self.html)
        # the router's declared outcomes are rendered explicitly
        for outcome in ("out_of_scope", "unsupported", "choose", "run"):
            self.assertIn('payload.outcome === "' + outcome + '"', self.html)
        self.assertIn("payload.outcome === \"run\" ? \"honesty\" : \"limit\"", self.html)
        # every payload string is escaped before it reaches the page
        self.assertIn("esc(payload.reason || \"\")", self.html)
        self.assertIn("esc(payload.missing.join", self.html)
        self.assertIn("esc(text)", self.html)

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
        self.assertIn("The Business Calculator arranges inputs", payload["note"])

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
        self.assertEqual(len(gallery["subjects"]), 11)
        status, page = api.handle("GET", "/api/cases/subjects/accounting")
        self.assertEqual(status, 200)
        self.assertEqual(page["id"], "accounting")
        self.assertEqual({tool["method"] for tool in page["tools"]},
                         {"management_accounts", "ratio_analysis",
                          "breakeven", "multi_product_breakeven", "trial_balance_check",
                          "standard_cost_variances", "abc_costing", "sales_variances",
                          "working_capital", "loan_amortization", "tax_declared",
                          "trend_analysis"})

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

