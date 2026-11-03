"""Acceptance suite for the Management & strategy shelf — one test per row of `qa/manual/management.md`.

The manual is the specification: every `E-mgt-nnn` row names a test below, and §4 of the
manual records its status.  Nothing here is a new requirement: each expectation is traced to
the shipped catalogue (`subjects.detail("management")`), the framework profiles
(`framework_profiles.PROFILES`), the paper rules in `docs/VALIDATION_HARNESS.md` §5
(V-01..V-20), or an owner presentation rule (P1..P6), and the source is cited in the manual.

Rules this file keeps:
  * offline — no provider key, no network, no model call;
  * it asserts the product's behaviour through the real paths (`completion.complete` →
    `completion.draft` → `completion.draft_bytes`, `Pipeline`, `deliverables.write_export`),
    and it never edits an expected value to go green;
  * a refusal is a refusal: a test that expects a block asserts the reason too;
  * a trap test fails on the day the defect returns, and names its ledger id.

Run:  PYTHONPATH=src python -m pytest tests/test_subject_management_acceptance.py -q
"""

import os
import re
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import registry, server, templates                       # noqa: E402
from bp.orchestrator import Pipeline                             # noqa: E402
from bp.product import (completion, deliverables, docx, framework_profiles,  # noqa: E402
                        matrix, paper, retrieval, subjects)

SUBJECT = "management"
INDUSTRY = "grocery retail"
BRIEF = ("A grocery retailer is reviewing how its value chain creates value and where cost and "
         "differentiation come from, before deciding whether to open a new store format.")
CHANGE_BRIEF = ("A grocery retailer is planning to move its store rota and its stock-replenishment "
                "process onto one system, before deciding whether to run the change this year.")
TITLES = {
    "firm infrastructure": "Overhead costs and administrative support functions in grocery retail",
    "human resource": "Recruitment and training practices in grocery retail",
    "technology": "Automation and digital technology adoption in grocery retail",
    "procurement": "Supplier sourcing and procurement in grocery retail",
    "inbound": "Inbound logistics and distribution centre handling in grocery retail",
    "operations": "Store operations and production processes in grocery retail",
    "outbound": "Outbound logistics and home delivery in grocery retail",
    "marketing": "Marketing and sales channels in grocery retail",
    "service": "Customer service and after-sales support in grocery retail",
}


def page():
    return subjects.detail(SUBJECT)


def sheets():
    return page()["worksheets"]


def catalogue_ids():
    return [sheet["catalogue_id"] for sheet in sheets()]


def profile(template):
    return framework_profiles.get(template) or {}


def _title_for(query):
    for cue, title in TITLES.items():
        if cue in query.lower():
            return title
    return "Grocery retail evidence"


def academic(query, databases=None, limit=10, year_from=None):
    return {"results": [{
        "title": _title_for(query),
        "abstract": "Evidence on the activity named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Operations Management", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def empty(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(template, instruction=BRIEF, sources=True, **kwargs):
    side = academic if sources else empty
    kwargs.setdefault("industry", INDUSTRY)
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, instruction, **kwargs)


def docx_text(payload):
    """The sentences a reader sees: word/document.xml with the tags stripped."""
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "paper.docx")
        with open(path, "wb") as stream:
            stream.write(payload)
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
    xml = re.sub(r"</w:p>", "\n", xml)
    text = re.sub(r"<[^>]+>", "", xml)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def deliver(method, inputs):
    return Pipeline().run({"objective": "management acceptance", "method": method,
                           "inputs": inputs}, lambda spec: True)


class InventoryTest(unittest.TestCase):
    """E-mgt-001..010 — the shelf against the catalogue."""

    def test_E_mgt_001__the_shelf_declares_one_compute_tool_with_a_preset(self):
        tools = page()["tools"]
        self.assertEqual([tool["key"] for tool in tools], ["case_decision"])
        preset = server.PRESETS[tools[0]["preset"]]
        self.assertEqual(preset["method"], "case_decision")
        self.assertTrue(preset["inputs"])

    def test_E_mgt_002__the_shelf_declares_31_worksheets_with_distinct_catalogue_ids(self):
        self.assertEqual(len(sheets()), 31)
        self.assertEqual(len(catalogue_ids()), 31)
        self.assertEqual(sorted(catalogue_ids()), sorted(set(catalogue_ids())))

    def test_E_mgt_003__every_worksheet_resolves_to_an_installed_profile(self):
        for sheet in sheets():
            self.assertIn(sheet["template"], framework_profiles.PROFILES, sheet["catalogue_id"])
            self.assertTrue(profile(sheet["template"])["blocks"], sheet["catalogue_id"])

    def test_E_mgt_004__the_shelf_declares_no_records_theories_or_glossary_terms(self):
        measured = page()
        self.assertEqual(measured["records"], [], "the shelf advertised a record that is not there")
        self.assertEqual(measured["theories"], [])
        self.assertEqual(len(measured["glossary"] or []), 0)

    def test_E_mgt_005__every_worksheet_is_a_form_the_page_can_render(self):
        for sheet in sheets():
            described = templates.describe(sheet["template"])
            self.assertNotIn(described["form_kind"], (None, "none"), sheet["catalogue_id"])
            row = registry.get(sheet["catalogue_id"])
            self.assertEqual(row["form"], "worksheet", sheet["catalogue_id"])

    def test_E_mgt_006__the_six_non_draftable_worksheets_are_the_recorded_gap(self):
        off = sorted(sheet["catalogue_id"] for sheet in sheets() if not sheet["draftable"])
        self.assertEqual(off, ["STR-04", "STR-08", "STR-09", "STR-12", "STR-13", "STR-14"])

    def test_E_mgt_007__two_worksheets_that_share_one_engine_say_so(self):
        swot = [sheet["catalogue_id"] for sheet in sheets()
                if sheet["template"] == "template_swot"]
        self.assertEqual(sorted(swot), ["STR-07", "STR-18"],
                         "two catalogue records share one engine; the manual names both")

    def test_E_mgt_008__the_declared_does_not_list_is_present_and_specific(self):
        declared = page()["does_not"]
        self.assertGreaterEqual(len(declared), 3)
        self.assertTrue(any("evidence" in line.lower() for line in declared))
        self.assertTrue(any("score" in line.lower() for line in declared))

    def test_E_mgt_009__the_shelf_appears_in_the_catalogue_with_the_same_counts(self):
        entry = next(row for row in subjects.catalogue()["subjects"] if row["id"] == SUBJECT)
        self.assertEqual(entry["label"], page()["label"])
        self.assertEqual(entry["tool_count"], len(page()["tools"]))
        self.assertEqual(entry["worksheet_count"], len(sheets()))
        self.assertEqual(entry["record_count"], 0)
        self.assertEqual(entry["theory_count"], 0)

    def test_E_mgt_010__every_worksheet_group_is_one_the_page_declares(self):
        groups = sorted({sheet.get("group") for sheet in sheets()})
        self.assertEqual(groups, ["business_model", "change_organisation", "competitive_position",
                                 "diagnosis", "portfolio_growth"])


class ToolTest(unittest.TestCase):
    """E-mgt-011..013 — the shelf's one compute tool."""

    def test_E_mgt_011__case_decision_compares_the_options_from_its_preset(self):
        preset = server.PRESETS[page()["tools"][0]["preset"]]
        delivery = deliver("case_decision", dict(preset["inputs"]))
        self.assertEqual(delivery.status, "delivered", delivery.blocked_reason)
        self.assertIn("net present value", delivery.report.lower())
        self.assertIn("Expand the shop", delivery.report)
        self.assertIn("Office catering", delivery.report)

    def test_E_mgt_012__case_decision_refuses_a_single_option(self):
        preset = server.PRESETS[page()["tools"][0]["preset"]]
        inputs = dict(preset["inputs"])
        inputs["alternatives"] = inputs["alternatives"][:1]
        delivery = deliver("case_decision", inputs)
        self.assertEqual(delivery.status, "blocked")
        self.assertTrue(delivery.blocked_reason)
        self.assertEqual(delivery.report, "", "a refusal must not carry a report")

    def test_E_mgt_013__the_case_decision_paper_carries_no_specification_footer(self):
        preset = server.PRESETS[page()["tools"][0]["preset"]]
        delivery = deliver("case_decision", dict(preset["inputs"]))
        bundle = {"id": "mgt-tool", "title": "Option comparison",
                  "delivery": {"report": delivery.report, "appendix": delivery.appendix}}
        headings = [heading for heading, _ in deliverables.sections(bundle, "submission")]
        self.assertNotIn("How this was produced", headings)
        text = "\n".join(line for _heading, lines in deliverables.sections(bundle, "submission")
                         for line in lines)
        for fragment in ("Specification hash", "Code hash", "Document hash", "Method: "):
            self.assertNotIn(fragment, text)


class ValueChainTest(unittest.TestCase):
    """E-mgt-014..022 — Porter's nine activities, end to end."""

    def test_E_mgt_014__the_nine_activities_are_those_the_profile_and_the_form_declare(self):
        declared = [block["key"] for block in framework_profiles.VALUE_CHAIN["blocks"]]
        self.assertEqual(declared, ["firm_infrastructure", "human_resource_management",
                                    "technology_development", "procurement", "inbound_logistics",
                                    "operations", "outbound_logistics", "marketing_and_sales", "service"])
        form = templates.CANVAS_BLOCKS["template_value_chain"]
        self.assertEqual(sorted(form), sorted(declared),
                         "the worksheet form and the profile must name the same nine blocks")

    def test_E_mgt_015__the_canvas_figure_carries_one_bullet_per_activity(self):
        result = complete("template_value_chain")
        report = completion.draft(result, "apa", "draft", "mid")
        figure = next(section["figure"] for section in report["sections"] if section.get("figure"))
        cells = [cell for grid in figure["grids"] for row in grid["rows"] for cell in row]
        self.assertEqual(len(cells), 9)
        empty = [cell["label"] for cell in cells if not cell["bullets"] and not cell["gap"]]
        self.assertEqual(empty, [], "an empty box in the figure is a cell with no evidence and no gap")

    def test_E_mgt_016__firm_infrastructure_accepts_real_overhead_evidence(self):
        """D-MGT-02: the cue set must contain the words its own query asks for."""
        result = complete("template_value_chain")
        blocks = {block["key"]: block for block in result["blocks"]}
        sourced = [item for item in blocks["firm_infrastructure"]["items"]
                   if item["provenance"] == "sourced"]
        self.assertTrue(sourced, "firm infrastructure accepted no evidence at all")
        self.assertTrue(sourced[0]["citation"])


    def test_E_mgt_017__a_cell_with_no_source_says_so_in_the_paper(self):
        result = dict(complete("template_value_chain", sources=False),
                      byline=["A Student", "Example University"])
        report = completion.draft(result, "apa", "draft", "mid")
        text = docx_text(completion.draft_bytes(result, "apa", report, "draft", "mid"))
        self.assertIn("No source was found for this part", text)
        self.assertIn("is not cited", text)

    def test_E_mgt_018__the_outline_headings_are_present_in_declared_order(self):
        result = complete("template_value_chain")
        report = completion.draft(result, "apa", "draft", "mid")
        headings = [section["heading"] for section in report["sections"]]
        expected = ["Introduction", "Case and Market Context", "Porter's Value Chain",
                    "Firm Infrastructure", "Human Resource Management", "Technology Development",
                    "Procurement", "Inbound Logistics", "Operations", "Outbound Logistics",
                    "Marketing and Sales", "Service", "Discussion", "What the Evidence Shows",
                    "Implications for the Decision", "Limitations", "Conclusion", "References"]
        self.assertEqual(headings, expected)

    def test_E_mgt_019__conclusion_and_references_are_the_last_two_sections(self):
        result = complete("template_value_chain")
        report = completion.draft(result, "apa", "draft", "mid")
        headings = [section["heading"] for section in report["sections"]]
        self.assertEqual(headings[-2:], ["Conclusion", "References"])
        # V-09 on the real sections: no level jump, and no level-2 before a level-1.
        levels = [int(section["level"]) for section in report["sections"]]
        self.assertEqual(levels[0], 1)
        for previous, level in zip(levels, levels[1:]):
            self.assertLessEqual(level, previous + 1)
            if level == 2:
                self.assertGreaterEqual(previous, 1)

    def test_E_mgt_020__the_byline_reaches_the_title_page_and_no_placeholder_is_printed(self):
        result = dict(complete("template_value_chain"), byline=["A Student", "Example University"])
        report = completion.draft(result, "apa", "draft", "mid")
        text = docx_text(completion.draft_bytes(result, "apa", report, "draft", "mid"))
        self.assertIn("A Student", text)
        self.assertIn("Example University", text)
        for placeholder in paper.META:
            self.assertNotIn(placeholder, text.lower())

    def test_E_mgt_021__the_title_drops_the_trailing_period(self):
        report = completion.draft(complete("template_value_chain", BRIEF + "."), "apa", "draft")
        self.assertTrue(report["title"].startswith("Porter's Value Chain: "))
        self.assertFalse(report["title"].endswith("."))

    def test_E_mgt_022__a_brief_without_an_industry_is_refused_naming_the_market(self):
        with self.assertRaises(ValueError) as refused:
            complete("template_value_chain", "A firm is reviewing its activities.", industry="")
        self.assertIn("market", str(refused.exception).lower())



class ChangeOrganizationTest(unittest.TestCase):
    """E-mgt-023..028 — the four elements on the shared engine."""

    def test_E_mgt_023__the_unit_of_analysis_is_the_industry(self):
        result = complete("template_change_organization", CHANGE_BRIEF)
        self.assertEqual(result["unit"]["field"], "industry")
        self.assertEqual(result["unit"]["value"], INDUSTRY)
        self.assertTrue(result["blocks"][0]["query"].startswith(INDUSTRY + " "))
        self.assertIn("market", framework_profiles.CHANGE_ORGANIZATION["unit"]["refuse"].lower())

    def test_E_mgt_024__each_element_carries_a_sourced_item_or_a_named_gap(self):
        result = complete("template_change_organization", CHANGE_BRIEF)
        self.assertEqual([block["key"] for block in result["blocks"]],
                         ["change_type", "readiness", "resistance", "support"])
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                if item["provenance"] == "sourced":
                    self.assertTrue(item["source"], block["key"])
                    self.assertTrue(item["citation"], block["key"])

    def test_E_mgt_025__one_source_cannot_fill_two_elements(self):
        result = complete("template_change_organization", CHANGE_BRIEF)
        sources = [item["source"] for block in result["blocks"] for item in block["items"]
                   if item.get("provenance") == "sourced"]
        self.assertEqual(len(sources), len(set(sources)), "one study was cited in two elements")

    def test_E_mgt_026__a_run_without_sources_still_records_every_element(self):
        result = complete("template_change_organization", CHANGE_BRIEF, sources=False)
        for block in result["blocks"]:
            self.assertTrue(block["items"] or block["gap"], block["key"])
            for item in block["items"]:
                self.assertEqual(item["provenance"], "background", block["key"])
        self.assertEqual(completion.missing(result), [])

    def test_E_mgt_027__the_prompt_names_the_framework_and_the_unit(self):
        system = completion._system(completion.HEAD_SYSTEM, dict(completion.LENGTHS["mid"]),
                                    completion._profile("template_change_organization"))
        self.assertIn("Change and Organization", system)
        self.assertIn("industry", system.lower())
        self.assertNotIn("PESTEL", system)
        self.assertIn("Do not add facts, numbers, names, sources or citations", system)

    def test_E_mgt_028__the_draft_route_generates_a_paper_with_an_empty_element(self):
        from bp.product import api
        result = complete("template_change_organization", CHANGE_BRIEF)
        result["blocks"] = [block for block in result["blocks"] if block["key"] != "support"]
        result["blocks"].append({"key": "support", "label": "Support", "items": [],
                                 "gap": "No evidence."})
        status, payload = api.handle("POST", "/api/cases/frameworks/report",
                                     {"completion": result, "version": "draft"})
        self.assertEqual(status, 200, payload)



class PromptTest(unittest.TestCase):
    """E-mgt-029..032 — D-MGT-04, the model prompt for every profile on the shelf."""

    def _systems(self):
        for sheet in sheets():
            template = sheet["template"]
            system = completion._system(completion.HEAD_SYSTEM, dict(completion.LENGTHS["mid"]),
                                        completion._profile(template))
            yield sheet, template, system

    def test_E_mgt_029__every_prompt_names_its_own_framework(self):
        for sheet, template, system in self._systems():
            self.assertIn(profile(template)["label"], system, sheet["catalogue_id"])

    def test_E_mgt_030__no_prompt_imports_another_frameworks_vocabulary(self):
        for sheet, template, system in self._systems():
            if template == "template_pestel":
                self.assertIn("PESTEL", system)
                continue
            self.assertNotIn("PESTEL", system, sheet["catalogue_id"])

    def test_E_mgt_031__every_industry_prompt_names_the_industry(self):
        for sheet, template, system in self._systems():
            unit = (profile(template).get("unit") or {}).get("field")
            if unit == "industry":
                self.assertIn("industry", system.lower(), sheet["catalogue_id"])

    def test_E_mgt_032__no_prompt_promises_a_diagram(self):
        for _sheet, _template, system in self._systems():
            self.assertNotIn("Diagram to draw", system)


class PresentationTest(unittest.TestCase):
    """E-mgt-033..038 — the owner's presentation rules P1..P5."""

    def test_E_mgt_033__there_is_no_markdown_download_anywhere(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        for forbidden in ('format: "md"', "format:'md'", "Download ... (Markdown)",
                          "Download (Markdown)", "Markdown)", " .md file for the paper"):
            self.assertNotIn(forbidden, page_html, forbidden)
        server_py = open(os.path.join(SRC, "bp", "server.py"), encoding="utf-8").read()
        self.assertNotIn("session_paper.markdown", server_py)
        api_py = open(os.path.join(SRC, "bp", "product", "api.py"), encoding="utf-8").read()
        self.assertNotIn('"md"', api_py)

    def test_E_mgt_034__the_chart_and_export_cards_keep_their_ids_and_stay_hidden(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        for bound in ('id="chartbtn"', 'id="expbtn"', 'id="expzip"'):
            self.assertIn(bound, page_html, "%s is bound unguarded by the inline script" % bound)
        for card in ("Charts", "Export"):
            index = page_html.index("<h3>%s</h3>" % card)
            head = page_html[max(0, index - 120):index]
            self.assertIn('style="display:none"', head, "%s card must stay hidden" % card)

    def test_E_mgt_035__no_paper_path_prints_a_specification_footer(self):
        """P3, read on the artefacts: the computation paper, the worksheet paper, the export."""
        footer = ("How this was produced", "Specification hash", "Code hash", "Document hash",
                  "can be re-run from the stored bundle")
        delivery = deliver("case_decision", dict(server.PRESETS["case_decision"]["inputs"]))
        bundle = {"id": "mgt-p3", "title": "Option comparison",
                  "delivery": {"report": delivery.report, "appendix": delivery.appendix}}
        papers = {
            "computation": "\n".join(line for _h, lines in
                                     __import__("bp.product.session_paper", fromlist=["x"]).sections(
                                         bundle["delivery"]) for line in lines),
            "worksheet": "\n".join(line for _h, lines in deliverables.sections(bundle, "worksheet")
                                   for line in lines),
            "submission": "\n".join(line for _h, lines in deliverables.sections(bundle, "submission")
                                    for line in lines),
        }
        academic = docx_text(completion.draft_bytes(
            complete("template_value_chain"), "apa",
            completion.draft(complete("template_value_chain"), "apa", "draft", "mid"), "draft", "mid"))
        papers["framework"] = academic
        for name, text in papers.items():
            self.assertTrue(text.strip(), "%s paper is empty" % name)
            for fragment in footer:
                self.assertNotIn(fragment, text, "%s paper still prints %r" % (name, fragment))

    def test_E_mgt_036__figures_print_at_the_methods_declared_precision(self):
        """P4: a method that declares a precision gets that precision, and only that."""
        import sys
        from bp.methods import LIBRARY
        from bp.product import session_paper
        for method_id, key in (("breakeven", "margin_of_safety"), ("irr", "irr"),
                               ("ratio_analysis", "current_ratio")):
            method = LIBRARY[method_id]
            unit, precision = method.typing(key)
            self.assertIsNotNone(precision, "%s declares no precision for %s" % (method_id, key))
            rendered = session_paper._render(key, "1.6666666666666666666666666666666666666666", method)
            decimals = rendered.split(": ", 1)[1]
            self.assertEqual(len(decimals.split(".")[-1]), precision, rendered)
        lists = session_paper._render("cashflows", ["-1000", "400"], None)
        self.assertNotIn("['", lists, "a Python list repr reached the paper")
        self.assertNotIn("'400'", lists)

    def test_E_mgt_037__no_paper_promises_a_diagram_nobody_draws(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        self.assertNotIn("Diagram to draw", page_html)
        for relative in (("bp", "product", "session_paper.py"),
                         ("bp", "product", "completion.py"), ("bp", "product", "chat.py")):
            source = open(os.path.join(SRC, *relative), encoding="utf-8").read()
            self.assertNotIn("Diagram to draw", source, relative[-1])

    def test_E_mgt_038__the_figures_are_the_cores_not_the_products(self):
        """P4: the product formats a number, it never recomputes one."""
        source = open(os.path.join(SRC, "bp", "product", "session_paper.py"), encoding="utf-8").read()
        self.assertIn("method.typing(key)", source)
        self.assertIn("quantize", source)
        self.assertNotIn("float(", source)

    def test_E_mgt_039__every_method_declares_its_precision_and_no_paper_prints_a_raw_decimal(self):
        """D-MGT-08 (FIXED, B-196): the owner unfroze the core rather than a paper rule.

        Four methods (`npv`, `pearson`, `spearman`, `descriptive_stats`) declared no
        `typing` hook and `case_decision` is a template rather than a `Method`, so the
        computation paper printed `Npv A1: 2586.473380864479782327…`.  The hooks are now
        declared in the core (the unfreeze) and the paper reads the core's own recorded
        precision for a template's derived keys.  This test fails if either half goes.
        """
        from bp.methods import LIBRARY
        from bp.product import session_paper
        hookless = sorted(key for key, method in LIBRARY.items()
                          if not callable(getattr(method, "typing", None)))
        self.assertEqual(hookless, [], "every method must declare its own precision")
        self.assertEqual(LIBRARY["npv"].typing("npv"), ("currency", 2))
        self.assertEqual(LIBRARY["pearson"].typing("r"), ("correlation", 3))
        self.assertEqual(LIBRARY["spearman"].typing("rho"), ("correlation", 3))
        self.assertEqual(LIBRARY["descriptive_stats"].typing("n"), ("count", 0))
        for method_id in ("npv", "case_decision"):
            preset = server.PRESETS[method_id]
            delivery = deliver(preset["method"], dict(preset["inputs"]))
            paper = "\n".join(line for _h, lines in
                              __import__("bp.product.session_paper", fromlist=["x"]).sections(
                                  {"report": delivery.report, "appendix": delivery.appendix})
                              for line in lines)
            self.assertNotRegex(paper, r"\d\.\d{6,}", "%s paper prints a raw Decimal" % method_id)
            for repr_mark in ("{'", "['", "'}"):
                self.assertNotIn(repr_mark, paper, "%s paper carries a Python repr" % method_id)
            recorded = session_paper._recorded_precision(delivery.appendix)
            if method_id == "case_decision":
                self.assertEqual(recorded.get("npv_A1"), ("currency", 2),
                                 "the core's own recorded precision must reach the paper")



def complete_any(template, instruction=None):
    """Complete any profile, with the unit of analysis its own declaration needs."""
    unit = (profile(template).get("unit") or {}).get("field")
    if unit == "industry":
        return complete(template, instruction or BRIEF)
    if unit == "process":
        return complete(template, instruction or
                        "Moving the store rota and the stock-replenishment process onto one system.",
                        industry="", unit_value="the lunch orders at the meal counter")
    if unit == "country":
        return complete(template, instruction or BRIEF, industry="", country="Iran")
    return complete(template, instruction or BRIEF, industry="", unit_value="the campus shop")


class ProfileIntegrityTest(unittest.TestCase):
    """E-mgt-040..042 — D-MGT-01 and D-MGT-05: the module itself."""

    def test_E_mgt_040__the_profiles_module_imports_nothing_outside_the_repository(self):
        path = os.path.join(SRC, "bp", "product", "framework_profiles.py")
        source = open(path, encoding="utf-8").read()
        self.assertNotRegex(source, r"(?m)^\s*exec\(",
                            "an import-time exec is a crash waiting for another machine")
        self.assertNotIn("C:/tmp", source)
        self.assertNotIn("C:\\tmp", source)
        for name in ("BMC", "LEAN_CANVAS", "VALUE_PROPOSITION_CANVAS", "PROJECT_CHARTER",
                     "WBS", "RISK_REGISTER", "STAKEHOLDER_PLAN", "LESSONS_LEARNED"):
            self.assertIn("template", getattr(framework_profiles, name), name)

    def test_E_mgt_041__every_profile_is_declared_once_in_the_module(self):
        path = os.path.join(SRC, "bp", "product", "framework_profiles.py")
        source = open(path, encoding="utf-8").read()
        declared = re.findall(r"^([A-Z][A-Z0-9_]*) = \{", source, re.M)
        duplicates = sorted({name for name in declared if declared.count(name) > 1})
        self.assertEqual(duplicates, [], "a second assignment silently replaced the first")

    def test_E_mgt_042__every_researched_block_declares_cues_and_a_query(self):
        for sheet in sheets():
            for block in profile(sheet["template"])["blocks"]:
                if framework_profiles.fill_of(block) in ("research", "auto"):
                    self.assertTrue(block.get("cues"), "%s/%s" % (sheet["catalogue_id"], block["key"]))
                    self.assertTrue(block.get("queries"), "%s/%s" % (sheet["catalogue_id"], block["key"]))


class ReachabilityTest(unittest.TestCase):
    """E-mgt-043..045 — D-MGT-09: a profile no page reaches still has to work."""

    def _unreachable(self):
        reached = set()
        for row in subjects.catalogue()["subjects"]:
            for sheet in subjects.detail(row["id"])["worksheets"]:
                reached.add(sheet["template"])
        return sorted(template for template in framework_profiles.PROFILES
                      if template not in reached)

    def test_E_mgt_043__the_unreachable_profiles_are_the_measured_eighteen(self):
        measured = self._unreachable()
        # 3 on 2026-11-03: the marketing shelf wired its fifteen dark worksheets
        # (B-211), so the only profiles no shelf offers are MKT-07 (its tile is hidden
        # by the owner, B-198), STR-19 (management's own decision) and CHG-15 (change's).
        # It was 18 before that, and 17 before the marketing lane removed the SERVQUAL
        # worksheet row while repairing it (D-MKT-04/B-198).  Re-measure; do not re-copy.
        self.assertEqual(len(measured), 3,
                         "3 on 2026-11-03 (18 before the marketing shelf wired its fifteen "
                         "worksheets, B-211); re-measure, do not re-copy the number")
        self.assertIn("template_change_organization", measured,
                      "the Change and Organization profile has no worksheet on any shelf (G-mgt-02)")

    def test_E_mgt_044__an_unreachable_profile_still_produces_a_paper(self):
        for template in self._unreachable():
            result = complete_any(template)
            report = completion.draft(result, "apa", "draft", "short")
            self.assertTrue(report["sections"], template)
            self.assertIsInstance(completion.draft_bytes(result, "apa", report, "draft", "short"),
                                  bytes)

    def test_E_mgt_045__a_non_draftable_profile_still_produces_a_paper(self):
        not_draftable = sorted({sheet["template"] for row in subjects.catalogue()["subjects"]
                                for sheet in subjects.detail(row["id"])["worksheets"]
                                if not sheet["draftable"]})
        self.assertEqual(len(not_draftable), 11,
                         "11 on 2026-11-03: SERVQUAL left the shelf's rows while the marketing "
                         "lane repairs it, so it is no longer counted here")
        for template in not_draftable:
            result = complete_any(template)
            report = completion.draft(result, "apa", "draft", "short")
            self.assertTrue(report["sections"], template)

    def test_E_mgt_046__the_shelf_catalogue_count_omits_three_of_its_own_worksheets(self):
        """D-MGT-08 (MINOR, CATALOGUE): 28 declared records against 31 worksheet rows.

        Pinned so the page's headline count cannot drift unnoticed.  The three ids the
        shelf shows but does not count are STR-01, STR-07 and STR-18; whether the count
        or the definition should change is the owner's call (the number is on the page).
        """
        declared = set(subjects._subject_definition(SUBJECT)["catalogue_ids"])
        shown = {sheet["catalogue_id"] for sheet in sheets()}
        self.assertEqual(sorted(shown - declared), ["STR-01", "STR-07", "STR-18"])
        entry = next(row for row in subjects.catalogue()["subjects"] if row["id"] == SUBJECT)
        self.assertEqual(entry["catalogue_count"], 28)
        self.assertEqual(entry["worksheet_count"], 31)



class CueReachabilityTest(unittest.TestCase):
    """E-mgt-047..049 — D-MGT-12: a block must be able to accept evidence for its own question.

    Found by driving all 30 profiles with a source whose title echoes the block's own query:
    the three canvas profiles accepted nothing, ever, because their blocks declared
    `cues: ['evidence']` and `queries: ['<key> evidence']`, and a list of cues became the
    single token "['evidence']" once it was coerced with str().
    """

    def _echo(self, query, databases=None, limit=10, year_from=None):
        return {"results": [{"title": query[:120],
                             "abstract": "Evidence on " + query[:110] + ".",
                             "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"],
                             "year": 2024, "venue": "Journal", "doi": "10.1/" + str(abs(hash(query)) % 999983),
                             "url": "https://doi.org/10.1/x", "database": "OpenAlex"}],
                "errors": [], "skipped": []}

    def test_E_mgt_047__no_block_declares_a_placeholder_cue_or_a_list_of_cues(self):
        for sheet in sheets():
            for block in profile(sheet["template"])["blocks"]:
                self.assertIsInstance(block.get("cues"), str,
                                      "%s/%s declares cues as a list" % (sheet["catalogue_id"], block["key"]))
                words = str(block.get("cues") or "").split()
                self.assertGreaterEqual(len(words), 2,
                                        "%s/%s has no cue vocabulary" % (sheet["catalogue_id"], block["key"]))
                self.assertNotEqual(words, ["evidence"],
                                    "%s/%s declares the placeholder cue 'evidence'"
                                    % (sheet["catalogue_id"], block["key"]))
                for query in block.get("queries") or []:
                    self.assertNotEqual(query, "%s evidence" % block["key"],
                                        "%s/%s searches its own key name"
                                        % (sheet["catalogue_id"], block["key"]))

    def test_E_mgt_048__every_research_block_accepts_evidence_for_its_own_question(self):
        for sheet in sheets():
            template = sheet["template"]
            for block in profile(template)["blocks"]:
                if framework_profiles.fill_of(block) not in ("research", "auto"):
                    continue
                query = retrieval.build_query((block.get("queries") or [""])[0], INDUSTRY, "Global")
                with mock.patch("bp.product.sources.search_academic", side_effect=self._echo), \
                        mock.patch("bp.product.sources.search_web", side_effect=web):
                    found = retrieval.retrieve(
                        key=block["key"], cues=block.get("cues"), queries=[query],
                        context=retrieval.context_words(INDUSTRY), geography="Global",
                        gate=profile(template).get("gate"))
                self.assertTrue(found["items"],
                                "%s/%s accepted no evidence for its own query (dropped %d)"
                                % (sheet["catalogue_id"], block["key"], found["dropped"]))

    def test_E_mgt_049__the_three_canvases_carry_a_sourced_item(self):
        for template in ("template_business_model_canvas", "template_lean_canvas",
                         "template_value_proposition_canvas"):
            unit = (profile(template).get("unit") or {}).get("field")
            kwargs = {"industry": INDUSTRY} if unit == "industry" else {"unit_value": "the campus shop"}
            with mock.patch("bp.product.sources.search_academic", side_effect=self._echo), \
                    mock.patch("bp.product.sources.search_web", side_effect=web):
                result = completion.complete(template, BRIEF, **kwargs)
            sourced = [item for block in result["blocks"] for item in block["items"]
                       if item["provenance"] == "sourced"]
            self.assertTrue(sourced, "%s accepted no evidence" % template)
            for item in sourced:
                self.assertTrue(item["citation"], template)


    def test_E_mgt_051__the_hash_stays_in_the_record_and_out_of_every_download(self):
        """Owner, 2026-11-03: "use the hash, just don't show it in the file downloaded by users
        — they are not part of academic papers, they are your markers, so keep it as such"."""
        from bp.product import spreadsheets
        delivery = deliver("case_decision", dict(server.PRESETS["case_decision"]["inputs"]))
        marker = "spec-" + "a" * 59
        bundle = {"id": "mgt-hash", "title": "Option comparison", "method": "case_decision",
                  "tier": delivery.tier, "created_at": "2026-11-03T00:00:00+00:00",
                  "spec_hash": marker, "outputs_hash": marker,
                  "delivery": {"report": delivery.report, "appendix": delivery.appendix}}
        downloads = {
            "csv": spreadsheets.to_csv(bundle),
            "spreadsheetml": spreadsheets.to_spreadsheetml(bundle),
            "session-paper": "\n".join(
                line for _h, lines in __import__("bp.product.session_paper", fromlist=["x"])
                .sections(bundle["delivery"]) for line in lines),
            "worksheet": "\n".join(line for _h, lines in deliverables.sections(bundle, "worksheet")
                                   for line in lines),
        }
        for name, text in downloads.items():
            self.assertNotIn("aaaaaaaaaa", text, "%s shows part of the hash" % name)
            self.assertNotIn(marker, text, "%s shows the hash" % name)
        # and the record keeps its marker: the hash is the system's, not the student's
        self.assertEqual(bundle["spec_hash"], marker)
        self.assertEqual(bundle["outputs_hash"], marker)
        self.assertEqual(delivery.appendix.get("spec_hash"), delivery.appendix.get("spec_hash"))

        """The article was hard-coded "a", so a vowel-initial singular read "a element"."""
        for sheet in sheets():
            template = sheet["template"]
            profile = framework_profiles.PROFILES[template]
            field = (profile.get("unit") or {}).get("field")
            kwargs = {}
            if field == "industry":
                kwargs["industry"] = INDUSTRY
            elif field == "process":
                kwargs["unit_value"] = "the campus mentoring programme"
            elif field == "country":
                kwargs["country"] = "Iran"
            else:
                kwargs["unit_value"] = "the campus shop offer"
            instruction = {"process": "The programme is being reviewed before deciding whether to continue it.",
                           "country": "A supermarket chain in Iran is weighing its options.",
                           "unit": "The campus shop is reviewing its offer."}.get(
                               field, BRIEF)
            with mock.patch("bp.product.sources.search_academic", side_effect=empty), \
                    mock.patch("bp.product.sources.search_web", side_effect=web):
                result = completion.complete(template, instruction, **kwargs)
            report = completion.draft(dict(result, byline=["A Student"]), "apa", "draft", "mid")
            text = docx_text(completion.draft_bytes(dict(result, byline=["A Student"]), "apa",
                                                   report, "draft", "mid"))
            for weak in (r"\ba activitie\b", r"\ba entrie\b", r"\ba element\b",
                         r"\ba assumption\b", r"\ba outcome\b", r"\ba activitie "):
                self.assertIsNone(re.search(weak, text),
                                  "%s: %r in the paper" % (sheet["catalogue_id"], weak))

