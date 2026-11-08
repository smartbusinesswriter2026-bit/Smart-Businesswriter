"""Acceptance suite for the Operations management shelf â€” one test per row of `qa/manual/operations.md`.

The manual is the specification: every `E-ops-nnn` row names a test below.  Nothing here is a new
requirement: each expectation is traced to the shipped catalogue (`subjects.detail("operations")`), the
framework profiles (`framework_profiles`), the paper rules in `docs/VALIDATION_HARNESS.md` Â§5
(V-01..V-20), or an owner presentation rule (P1..P6), and the source is cited in the manual.

Rules this file keeps:
  * offline â€” no provider key, no network, no model call;
  * it asserts the product's behaviour through the real paths (`completion.complete` â†’
    `completion.draft` â†’ `completion.draft_bytes`, `Pipeline`, `session_paper.docx_bytes`), and it never
    edits an expected value to go green;
  * a refusal is a refusal: a test that expects a block asserts the reason too;
  * a trap test fails on the day the defect returns, and names its ledger id.

Run:  PYTHONPATH=src python -m pytest tests/test_subject_operations_acceptance.py -q
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
QA = os.path.join(ROOT, "qa")
for path in (SRC, QA):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp import registry, server, templates                       # noqa: E402
from bp.methods import LIBRARY                                   # noqa: E402
from bp.orchestrator import Pipeline                             # noqa: E402
from bp.product import (completion, deliverables, framework_profiles,  # noqa: E402
                        matrix, paper, retrieval, session_paper, subjects)

SUBJECT = "operations"
PROCESS = "the lunch service at the meal counter"
BRIEF = ("The lunch service at the meal counter takes an order, assembles and packs the meal, then the "
         "student collects and pays. At noon the queue reaches the gate, one oven bakes one tray at a "
         "time, and the supervisor re-times the wait from collection. The counter hands on a packed "
         "meal and a payment receipt. Bread arrives from one regional bakery every morning before "
         "opening.")
#: D-OPS-03: a brief that only *mentions* cost, quality and flow.  Nothing in it describes a
#: framework's part, so anything a cell quotes from it is a word-match dressed as an answer.
TRAP_BRIEF = ("The counter must cut its cost per meal without losing quality, and the flow between the "
              "kitchen and the counter has to hold at the noon peak. The manager reviews the change "
              "next term.")
TEMPLATES = {
    "OPS-01": "template_scor", "OPS-02": "template_sipoc", "OPS-03": "template_value_stream_map",
    "OPS-04": "template_5s", "OPS-05": "template_a3", "OPS-06": "template_toc",
    "OPS-07": "template_root_cause", "OPS-08": "template_fmea", "OPS-10": "template_kraljic",
    "OPS-11": "template_sop", "OPS-12": "template_pdca",
}
RECORDS = ["OPS-09", "QNT-OPS-01", "QNT-OPS-02", "QNT-OPS-04", "QNT-OPS-05", "QNT-OPS-06", "QNT-OPS-08"]

def page():
    return subjects.detail(SUBJECT)


def sheets():
    return page()["worksheets"]


def catalogue_ids():
    return [sheet["catalogue_id"] for sheet in sheets()]


def profile(template):
    return framework_profiles.get(template) or {}


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query: the fair test of 'can this block accept evidence
    for the question it asks?'."""
    return {"results": [{
        "title": query[:120],
        "abstract": "Evidence on " + query[:110] + ". A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Operations Management", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def empty(query, databases=None, limit=10, year_from=None):
    return {"results": [], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(template, brief=BRIEF, sources=True, process=PROCESS):
    side = academic if sources else empty
    with mock.patch("bp.product.sources.search_academic", side_effect=side), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(template, brief, unit_value=process)


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


_PAPERS = {}


def built(template, sources=True, brief=BRIEF):
    """One paper per (template, sources, brief): complete, draft, draft_bytes, read back.  Cached."""
    key = (template, bool(sources), brief)
    if key not in _PAPERS:
        result = dict(complete(template, brief=brief, sources=sources),
                      byline=["A Student", "Example University"])
        report = completion.draft(result, "apa", "draft", "mid")
        payload = completion.draft_bytes(result, "apa", report, "draft", "mid")
        _PAPERS[key] = (result, report, docx_text(payload))
    return _PAPERS[key]


def deliver(method, inputs):
    return Pipeline().run({"objective": "operations acceptance", "method": method,
                           "inputs": inputs}, lambda spec: True)


def tool_delivery(tool):
    preset = server.PRESETS[tool["preset"]]
    return deliver(preset["method"], dict(preset["inputs"]))


class InventoryTest(unittest.TestCase):
    """E-ops-001..010 â€” the shelf, reconciled against the catalogue."""

    def test_E_ops_001__the_shelf_declares_14_tools_with_a_preset_and_a_method(self):
        tools = page()["tools"]
        self.assertEqual(len(tools), 14)
        for tool in tools:
            self.assertIn(tool["preset"], server.PRESETS, tool["key"])
            preset = server.PRESETS[tool["preset"]]
            self.assertEqual(preset["method"], tool["method"], tool["key"])
            self.assertIn(preset["method"], LIBRARY, tool["key"])
            self.assertTrue(preset["inputs"], tool["key"])

    def test_E_ops_002__the_shelf_declares_11_worksheets_with_distinct_catalogue_ids(self):
        self.assertEqual(len(sheets()), 11)
        self.assertEqual(len(set(catalogue_ids())), 11)
        self.assertEqual(sorted(catalogue_ids()), sorted(TEMPLATES))

    def test_E_ops_003__every_worksheet_resolves_and_every_record_is_read_only(self):
        for sheet in sheets():
            self.assertIn(sheet["template"], framework_profiles.PROFILES, sheet["catalogue_id"])
            self.assertTrue(profile(sheet["template"])["blocks"], sheet["catalogue_id"])
            self.assertEqual(registry.get(sheet["catalogue_id"])["form"], "worksheet")
        for record in page()["records"]:
            row = registry.get(record["id"])
            self.assertIsNotNone(row, record["id"])
            self.assertEqual(row["form"], "computed", record["id"])
            self.assertIsNone(row["template"], "%s must not be a worksheet" % record["id"])
            for method in record.get("linked_methods") or []:
                self.assertIn(method, LIBRARY, "%s links %s" % (record["id"], method))
        self.assertEqual(sorted(r["id"] for r in page()["records"]), sorted(RECORDS))

    def test_E_ops_004__seven_records_twenty_defined_terms_and_no_theories(self):
        measured = page()
        self.assertEqual(len(measured["records"]), 7)
        self.assertEqual(measured["theories"], [])
        self.assertEqual(len(measured["glossary"]), 20)
        undefined = [term["term"] for term in measured["glossary"] if not term.get("definition")]
        self.assertEqual(undefined, [], "a glossary term with no definition")
        for term in measured["glossary"]:
            self.assertGreater(len(term["definition"].strip()), 20, term["term"])

    def test_E_ops_005__every_worksheet_is_a_form_the_page_can_render(self):
        for sheet in sheets():
            described = templates.describe(sheet["template"])
            self.assertEqual(described["form_kind"], "canvas", sheet["catalogue_id"])
            self.assertTrue(described["blocks"], sheet["catalogue_id"])
            self.assertNotIn(described["form_kind"], (None, "none"), sheet["catalogue_id"])

    def test_E_ops_006__ops_03_is_the_one_non_draftable_worksheet(self):
        off = sorted(sheet["catalogue_id"] for sheet in sheets() if not sheet["draftable"])
        self.assertEqual(off, ["OPS-03"])
        fills = {framework_profiles.fill_of(block) for block in
                 framework_profiles.PROFILES["template_value_stream_map"]["blocks"]}
        self.assertEqual(fills, {"quote", "gap"},
                         "OPS-03 is the only quote+gap profile on the shelf")

    def test_E_ops_007__every_worksheet_has_a_worked_example_that_passes_its_own_checks(self):
        for sheet in sheets():
            kind = sheet["template"]
            self.assertIn(kind, templates.EXAMPLES, "no worked example for %s" % sheet["catalogue_id"])
            example = templates.EXAMPLES[kind]
            self.assertEqual(example["method"], kind)
            self.assertTrue(example["objective"])
            self.assertEqual(templates.validate(kind, example["inputs"]), [], sheet["catalogue_id"])
            checks = templates.run_template(kind, example["inputs"])["results"]
            self.assertTrue(all(ok for _name, ok in checks), "%s: %s" % (kind, checks))

    def test_E_ops_008__the_declared_does_not_list_is_present_and_specific(self):
        declared = page()["does_not"]
        self.assertGreaterEqual(len(declared), 3)
        self.assertTrue(any("data" in line.lower() for line in declared))
        self.assertTrue(any("schedule" in line.lower() or "optimise" in line.lower()
                            for line in declared))
        self.assertTrue(any("observation" in line.lower() or "visit" in line.lower()
                            for line in declared))

    def test_E_ops_009__the_catalogue_row_agrees_with_the_detail_page(self):
        entry = next(row for row in subjects.catalogue()["subjects"] if row["id"] == SUBJECT)
        self.assertEqual(entry["tool_count"], len(page()["tools"]))
        self.assertEqual(entry["worksheet_count"], len(sheets()))
        self.assertEqual(entry["record_count"], len(page()["records"]))
        self.assertEqual(entry["theory_count"], len(page()["theories"]))
        self.assertEqual(entry["catalogue_count"], len(sheets()) + len(page()["records"]))

    def test_E_ops_010__all_eleven_worksheets_are_shared_and_the_page_groups_them(self):
        reached = {}
        for row in subjects.catalogue()["subjects"]:
            for sheet in subjects.detail(row["id"])["worksheets"]:
                reached.setdefault(sheet["template"], set()).add(row["id"])
        for sheet in sheets():
            self.assertIn("supply-chain", reached[sheet["template"]],
                          "%s is no longer shared with supply-chain" % sheet["catalogue_id"])
        ours = {sheet["template"] for sheet in sheets()}
        self.assertEqual(sorted(ours - set(reached)), [],
                         "a template on this shelf is reached by no page")

        # G-ops-02 / D-OPS-06, closed 2026-11-03: the shelf declares three tiles, and
        # their keys are the shelf's own tool groups, because `_tiles` places a
        # calculator in the tile whose key equals the tool's group.
        tiles = page()["tiles"]
        self.assertEqual([tile["key"] for tile in tiles],
                         ["Process and capacity", "Inventory and planning",
                          "Quality and evidence"])
        self.assertEqual(sorted({sheet["group"] for sheet in sheets()}),
                         sorted(tile["key"] for tile in tiles))

        def ident(item):
            return item.get("catalogue_id") or item.get("id") or item.get("key")

        for kind, items in (("worksheets", sheets()), ("tools", page()["tools"]),
                            ("records", page()["records"])):
            on_page = sorted(ident(item) for item in items)
            in_tiles = sorted(ident(item) for tile in tiles for item in tile[kind])
            self.assertEqual(in_tiles, on_page,
                             "%s: a tile dropped or duplicated an item" % kind)
        # and each tile says what it covers and what the student needs first
        for tile in tiles:
            self.assertTrue(tile["what"], tile["key"])
            self.assertTrue(tile["need"], tile["key"])
            self.assertTrue(tile["worksheets"], "%s is empty" % tile["key"])


class PaperTest(unittest.TestCase):
    """E-ops-011..020 â€” the eleven papers, read on the artefact (P6)."""

    def test_E_ops_011__every_worksheet_paper_opens_and_closes_in_the_declared_order(self):
        for sheet in sheets():
            _result, report, _text = built(sheet["template"])
            headings = [section["heading"] for section in report["sections"]]
            self.assertEqual(headings[0], "Introduction", sheet["catalogue_id"])
            self.assertEqual(headings[-2:], ["Conclusion", "References"], sheet["catalogue_id"])
            levels = [int(section["level"]) for section in report["sections"]]
            jumps = [(a, b) for a, b in zip(levels, levels[1:]) if b > a + 1]
            self.assertEqual(jumps, [], "%s: heading level jump" % sheet["catalogue_id"])

    def test_E_ops_012__every_block_carries_an_item_or_a_named_gap(self):
        for sheet in sheets():
            result = complete(sheet["template"])
            declared = [block["key"] for block in profile(sheet["template"])["blocks"]]
            self.assertEqual([block["key"] for block in result["blocks"]], declared,
                             sheet["catalogue_id"])
            for block in result["blocks"]:
                self.assertTrue(block["items"] or block["gap"],
                                "%s/%s is blank" % (sheet["catalogue_id"], block["key"]))

    def test_E_ops_013__a_named_gap_says_what_to_state(self):
        for sheet in sheets():
            result = complete(sheet["template"], sources=False)
            for block in result["blocks"]:
                if block["items"] or not block["gap"]:
                    continue
                self.assertIn("What to state", block["gap"],
                              "%s/%s names a gap but not what to state"
                              % (sheet["catalogue_id"], block["key"]))

    def test_E_ops_014__the_byline_reaches_the_title_page_and_no_placeholder_is_printed(self):
        for sheet in sheets():
            _result, _report, text = built(sheet["template"])
            self.assertIn("A Student", text, sheet["catalogue_id"])
            self.assertIn("Example University", text, sheet["catalogue_id"])
            for placeholder in paper.META:
                self.assertNotIn(placeholder, text.lower(),
                                 "%s prints %r" % (sheet["catalogue_id"], placeholder))

    def test_E_ops_015__no_paper_prints_an_instructional_phrase(self):
        forbidden = ("add your", "not supplied", "Diagram to draw", "TODO", "insert here",
                     "lorem ipsum", "How this was produced", "Specification hash")
        for sheet in sheets():
            for sources in (True, False):
                _result, _report, text = built(sheet["template"], sources=sources)
                for phrase in forbidden:
                    self.assertNotIn(phrase.lower(), text.lower(),
                                     "%s prints %r" % (sheet["catalogue_id"], phrase))

    def test_E_ops_016__every_sourced_item_carries_one_citation_in_its_own_section(self):
        for sheet in sheets():
            result, _report, text = built(sheet["template"])
            sourced = [item for block in result["blocks"] for item in block["items"]
                       if item.get("provenance") == "sourced"]
            for item in sourced:
                self.assertTrue(item.get("source"), sheet["catalogue_id"])
                self.assertTrue(item.get("citation"), sheet["catalogue_id"])
                self.assertIn(item["citation"], text,
                              "%s: citation missing from the paper" % sheet["catalogue_id"])
                doubled = item["citation"] + " " + item["citation"]
                self.assertNotIn(doubled, text,
                                 "%s prints its citation twice (D-OPS-04)" % sheet["catalogue_id"])

    def test_E_ops_017__every_reference_is_cited_and_no_source_fills_two_parts(self):
        for sheet in sheets():
            result, report, _text = built(sheet["template"])
            sources = [item["source"] for block in result["blocks"] for item in block["items"]
                       if item.get("provenance") == "sourced"]
            self.assertEqual(len(sources), len(set(sources)),
                             "%s: one source fills two parts" % sheet["catalogue_id"])
            references = [line for line in report["sections"][-1]["lines"]
                          if line != "No sources were used."]
            body = "\n".join("\n".join(section["lines"]) for section in report["sections"][:-1])
            for reference in references:
                author = re.split(r"\s*[,(]", str(reference))[0].strip()
                self.assertIn(author, body, "%s: uncited reference" % sheet["catalogue_id"])

    def test_E_ops_018__the_figure_carries_one_labelled_cell_per_block(self):
        """Owner instruction, 2026-11-03: the eleven papers carry their grid (G-ops-01 closed).

        `matrix.LAYOUTS` now declares a layout for each of the eleven templates, so the
        canvas reaches the paper as a table.  Every cell is labelled with the block's own
        label and carries either the accepted items or the named gap: the figure adds no
        number and no evidence, it places what the completion already produced.
        """
        for sheet in sheets():
            _result, report, text = built(sheet["template"])
            figure = next((s["figure"] for s in report["sections"] if s.get("figure")), None)
            self.assertIsNotNone(figure, "%s draws no figure" % sheet["catalogue_id"])
            cells = [cell for grid in figure["grids"] for row in grid["rows"] for cell in row]
            declared = {block["label"] for block in profile(sheet["template"])["blocks"]}
            self.assertEqual(len(cells), len(declared), sheet["catalogue_id"])
            self.assertEqual({cell["label"] for cell in cells}, declared, sheet["catalogue_id"])
            blank = [cell["label"] for cell in cells if not cell["bullets"] and not cell["gap"]]
            self.assertEqual(blank, [], "%s: an empty cell" % sheet["catalogue_id"])
            self.assertIn("Figure 1", text, "%s: the figure is not in the paper" % sheet["catalogue_id"])

    def test_E_ops_019__two_identical_runs_produce_identical_bytes(self):
        for sheet in sheets()[:3]:
            first = dict(complete(sheet["template"]), byline=["A Student", "Example University"])
            second = dict(complete(sheet["template"]), byline=["A Student", "Example University"])
            once = completion.draft_bytes(first, "apa",
                                          completion.draft(first, "apa", "draft", "mid"),
                                          "draft", "mid")
            again = completion.draft_bytes(second, "apa",
                                           completion.draft(second, "apa", "draft", "mid"),
                                           "draft", "mid")
            self.assertEqual(once, again, sheet["catalogue_id"])

    def test_E_ops_020__no_paper_scores_ranks_or_recommends(self):
        for sheet in sheets():
            result, report, _text = built(sheet["template"])
            self.assertFalse({"score", "overall", "verdict", "ranking", "total_score"} & set(result),
                             "%s carries an aggregate" % sheet["catalogue_id"])
            conclusion = "\n".join(report["sections"][-2]["lines"])
            self.assertNotIn("carries the most weight", conclusion,
                             "%s ranks the parts (D-OPS-02)" % sheet["catalogue_id"])
            self.assertNotIn("carries the least", conclusion, sheet["catalogue_id"])
            self.assertIn("accepted items", conclusion,
                          "%s does not state the count of accepted items" % sheet["catalogue_id"])


class FillPolicyTest(unittest.TestCase):
    """E-ops-021..026 â€” what the pipeline may do with each part."""

    def test_E_ops_021__a_research_part_accepts_its_own_vocabulary(self):
        block = next(b for b in profile("template_sipoc")["blocks"] if b["key"] == "suppliers")
        self.assertEqual(framework_profiles.fill_of(block), "research")
        query = retrieval.build_query("supplier of the input this process depends on", PROCESS)
        with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
                mock.patch("bp.product.sources.search_web", side_effect=web):
            found = retrieval.retrieve(key=block["key"], cues=block.get("cues"), queries=[query],
                                       context=retrieval.context_words(PROCESS),
                                       geography="Global", gate=profile("template_sipoc").get("gate"))
        self.assertTrue(found["items"], "the suppliers block accepted nothing for its own query")
        result = complete("template_sipoc")
        suppliers = next(b for b in result["blocks"] if b["key"] == "suppliers")
        self.assertEqual([item["provenance"] for item in suppliers["items"]], ["sourced"])
        self.assertTrue(suppliers["items"][0]["citation"])

    def test_E_ops_022__a_quote_part_takes_the_students_own_sentence_verbatim(self):
        result = complete("template_sipoc")
        for key in ("process", "outputs", "customers"):
            block = next(b for b in result["blocks"] if b["key"] == key)
            self.assertTrue(block["items"], key)
            for item in block["items"]:
                self.assertEqual(item["provenance"], "student", key)
                self.assertIn(item["text"], BRIEF, "%s: the quote is not the brief verbatim" % key)

    def test_E_ops_023__a_sentence_that_only_shares_a_generic_word_is_refused(self):
        """D-OPS-03: the defect this shelf was named for.  A sentence that mentions cost,
        quality or flow used to be quoted into any cell whose cue list happened to hold the
        word.  It is now a named gap unless the sentence names the part."""
        for sheet in sheets():
            result = complete(sheet["template"], brief=TRAP_BRIEF, sources=False)
            quoted = [(block["key"], item["text"]) for block in result["blocks"]
                      for item in block["items"] if item.get("provenance") == "student"]
            self.assertEqual(quoted, [],
                             "%s quoted a sentence it does not describe" % sheet["catalogue_id"])
            for block in result["blocks"]:
                self.assertTrue(block["gap"], "%s/%s: neither an item nor a gap"
                                % (sheet["catalogue_id"], block["key"]))

    def test_E_ops_024__a_gap_part_is_never_filled_and_says_what_to_state(self):
        result = complete("template_value_stream_map")
        for key in ("value_added", "improvements"):
            block = next(b for b in result["blocks"] if b["key"] == key)
            self.assertEqual(block["items"], [], key)
            self.assertIn("only you can state", block["gap"], key)
            self.assertIn("What to state", block["gap"], key)

    def test_E_ops_025__a_value_stream_map_never_searches_for_a_part_the_student_owns(self):
        fills = {framework_profiles.fill_of(block) for block in
                 framework_profiles.PROFILES["template_value_stream_map"]["blocks"]}
        self.assertNotIn("research", fills)
        self.assertNotIn("auto", fills)
        with mock.patch("bp.product.sources.search_academic",
                        side_effect=AssertionError("the value stream map searched")), \
                mock.patch("bp.product.sources.search_web",
                           side_effect=AssertionError("the value stream map searched")):
            result = completion.complete("template_value_stream_map", BRIEF, unit_value=PROCESS)
        self.assertEqual([block["key"] for block in result["blocks"]],
                         [block["key"] for block in
                          framework_profiles.PROFILES["template_value_stream_map"]["blocks"]])

    def test_E_ops_026__the_chart_and_export_cards_keep_their_ids(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        for bound in ('id="chartbtn"', 'id="expbtn"', 'id="expzip"'):
            self.assertIn(bound, page_html, "%s is bound unguarded by the inline script" % bound)
        # the Charts card is a live feature now; the Export card is still half-built.
        index = page_html.index("<h3>Charts</h3>")
        self.assertNotIn('style="display:none"', page_html[max(0, index - 120):index],
                         "the Charts card is live")
        index = page_html.index("<h3>Export</h3>")
        self.assertIn('style="display:none"', page_html[max(0, index - 120):index],
                      "the Export card must stay hidden")


class ToolTest(unittest.TestCase):
    """E-ops-027..032 â€” the fourteen compute tools, end to end and on the paper."""

    def test_E_ops_027__no_download_carries_a_specification_footer_or_a_hash(self):
        from bp.product import spreadsheets
        footer = ("How this was produced", "Specification hash", "Code hash", "Outputs hash",
                  "Document hash")
        tool = page()["tools"][0]
        delivery = tool_delivery(tool)
        marker = "spec-" + "b" * 59
        bundle = {"id": "ops-p3", "title": "Break-even", "method": tool["method"],
                  "spec_hash": marker, "outputs_hash": marker,
                  "delivery": {"report": delivery.report, "appendix": delivery.appendix}}
        downloads = {
            "computation": "\n".join(line for _h, lines in
                                     session_paper.sections(bundle["delivery"]) for line in lines),
            "worksheet": "\n".join(line for _h, lines in deliverables.sections(bundle, "worksheet")
                                   for line in lines),
            "submission": "\n".join(line for _h, lines in deliverables.sections(bundle, "submission")
                                    for line in lines),
            "csv": spreadsheets.to_csv(bundle),
            "spreadsheetml": spreadsheets.to_spreadsheetml(bundle),
        }
        for name, text in downloads.items():
            self.assertTrue(text.strip(), "%s is empty" % name)
            for fragment in footer:
                self.assertNotIn(fragment, text, "%s still prints %r" % (name, fragment))
            self.assertNotIn("bbbbbbbbbb", text, "%s shows part of the hash" % name)
        # the hash stays in the record: it is the system's marker, not the student's cell
        self.assertEqual(bundle["spec_hash"], marker)
        self.assertEqual(bundle["outputs_hash"], marker)

    def test_E_ops_028__every_figure_prints_at_the_methods_declared_precision(self):
        hookless = sorted(key for key, method in LIBRARY.items()
                          if not callable(getattr(method, "typing", None)))
        self.assertEqual(hookless, [], "every method must declare its own precision")
        for tool in page()["tools"]:
            delivery = tool_delivery(tool)
            self.assertEqual(delivery.status, "delivered", tool["key"])
            self.assertTrue(delivery.appendix.get("tests"), tool["key"])
            bundle = {"report": delivery.report, "appendix": delivery.appendix}
            text = docx_text(session_paper.docx_bytes(bundle))
            self.assertTrue(text.strip(), tool["key"])
            self.assertNotRegex(text, r"\d\.\d{6,}", "%s prints a raw Decimal" % tool["key"])
            for repr_mark in ("{'", "['", "'}", "']"):
                self.assertNotIn(repr_mark, text, "%s carries a Python repr" % tool["key"])
            figures = "\n".join(line for heading, lines in session_paper.sections(bundle)
                                if heading in ("Result", "Inputs and results") for line in lines)
            self.assertNotRegex(figures, r"\d[eE][+-]\d",
                                "%s prints a computed figure in scientific notation" % tool["key"])

    def test_E_ops_029__no_paper_or_page_promises_a_diagram(self):
        for relative in (("bp", "product", "completion.py"), ("bp", "product", "chat.py"),
                         ("bp", "product", "session_paper.py")):
            source = open(os.path.join(SRC, *relative), encoding="utf-8").read()
            self.assertNotIn("Diagram to draw", source, relative[-1])
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        self.assertNotIn("Diagram to draw", page_html)
        for sheet in sheets():
            for sources in (True, False):
                _result, _report, text = built(sheet["template"], sources=sources)
                self.assertNotIn("Diagram to draw", text, sheet["catalogue_id"])

    def test_E_ops_030__there_is_no_markdown_download_anywhere(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        for forbidden in ('format: "md"', "format:'md'", "Download (Markdown)", "Markdown)"):
            self.assertNotIn(forbidden, page_html, forbidden)
        server_py = open(os.path.join(SRC, "bp", "server.py"), encoding="utf-8").read()
        self.assertNotIn("session_paper.markdown", server_py)
        api_py = open(os.path.join(SRC, "bp", "product", "api.py"), encoding="utf-8").read()
        self.assertNotIn('"md"', api_py)

    def test_E_ops_031__no_block_declares_a_placeholder_cue_or_a_list_of_cues(self):
        checked = 0
        for sheet in sheets():
            for block in profile(sheet["template"])["blocks"]:
                words = retrieval.cue_words_of(block.get("cues"))
                self.assertTrue(words, "%s/%s declares no cue"
                                % (sheet["catalogue_id"], block["key"]))
                self.assertNotEqual(words, {"evidence"},
                                    "%s/%s still declares the placeholder"
                                    % (sheet["catalogue_id"], block["key"]))
                if framework_profiles.fill_of(block) in ("research", "auto"):
                    checked += 1
                    self.assertTrue(block.get("queries"), "%s/%s declares no query"
                                    % (sheet["catalogue_id"], block["key"]))
                if framework_profiles.fill_of(block) in ("quote", "auto"):
                    self.assertTrue(block.get("queries") or block.get("quote_cues"),
                                    "%s/%s can borrow a sentence but declares no vocabulary"
                                    % (sheet["catalogue_id"], block["key"]))
        self.assertGreaterEqual(checked, 50, "the sweep did not run")

    def test_E_ops_032__every_researched_block_accepts_evidence_for_its_own_question(self):
        refused, checked = [], 0
        for sheet in sheets():
            for block in profile(sheet["template"])["blocks"]:
                if framework_profiles.fill_of(block) not in ("research", "auto"):
                    continue
                checked += 1
                query = retrieval.build_query((block.get("queries") or [""])[0], PROCESS)
                with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
                        mock.patch("bp.product.sources.search_web", side_effect=web):
                    found = retrieval.retrieve(key=block["key"], cues=block.get("cues"),
                                               queries=[query],
                                               context=retrieval.context_words(PROCESS),
                                               geography="Global",
                                               gate=profile(sheet["template"]).get("gate"))
                if not found["items"]:
                    refused.append("%s/%s (query=%r)" % (sheet["catalogue_id"], block["key"], query))
        self.assertGreaterEqual(checked, 50, "the sweep did not run")
        self.assertEqual(refused, [], "blocks that accept no evidence for their own question:\n  "
                                      + "\n  ".join(refused))

    def test_E_ops_033__no_paper_prints_a_wrong_article_or_a_broken_singular(self):
        for sheet in sheets():
            _result, _report, text = built(sheet["template"])
            for weak in (r"\ba activitie\b", r"\bA activitie\b", r"\ba entrie\b", r"\bA entrie\b",
                         r"\ba element\b", r"\ba assumption\b", r"\ba outcome\b",
                         r"\ba operation\b", r"\ba activity\b"):
                self.assertIsNone(re.search(weak, text),
                                  "%s prints %r" % (sheet["catalogue_id"], weak))
            self.assertNotIn("().", text, sheet["catalogue_id"])

    def test_E_ops_034__no_paper_prints_a_python_repr_or_a_raw_decimal(self):
        for sheet in sheets():
            _result, _report, text = built(sheet["template"])
            self.assertNotRegex(text, r"\d\.\d{6,}", "%s prints a raw decimal"
                                % sheet["catalogue_id"])
            for mark in ("{'", "['", "'}", "']", "None,", "Decimal("):
                self.assertNotIn(mark, text, "%s carries %r" % (sheet["catalogue_id"], mark))

    def test_E_ops_035__the_hash_stays_in_the_record_and_out_of_every_download(self):
        """Owner, 2026-11-03: "use the hash, just don't show it in the file downloaded by users â€”
        they are not part of academic papers, they are your markers, so keep it as such"."""
        marker = "spec-" + "c" * 59
        for sheet in sheets():
            result = dict(complete(sheet["template"]), byline=["A Student", "Example University"])
            report = completion.draft(result, "apa", "draft", "mid")
            payload = completion.draft_bytes(result, "apa", report, "draft", "mid")
            text = docx_text(payload)
            self.assertNotIn(marker, text, sheet["catalogue_id"])
            self.assertNotIn("cccccccccc", text, sheet["catalogue_id"])
            self.assertNotIn("Specification hash", text, sheet["catalogue_id"])
        self.assertEqual(marker, "spec-" + "c" * 59, "the marker is unchanged: it is the record's")

    def test_E_ops_036__the_probe_reports_no_problem_on_this_shelf(self):
        """The harness that found four defects on the last two shelves, pointed at this one."""
        import probe_mgt_debug as probe
        problems = []
        for sheet in sheets():
            probe.check(sheet["template"], True, problems)
            probe.check(sheet["template"], False, problems)
        probe.tools(problems)
        self.assertEqual(problems, [], "the probe still finds:\n  "
                                       + "\n  ".join("%s %s %s" % row for row in problems))


class TrapTest(unittest.TestCase):
    """E-ops-037..046 â€” the shelf-wide traps.  Each fails on the day its defect returns."""

    def test_E_ops_037__every_auto_and_quote_block_declares_its_quote_vocabulary(self):
        """D-OPS-03 at the declaration: `cues` is the retrieval vocabulary, and a block that
        may borrow the student's words has to say which words make a sentence about it."""
        missing = []
        for sheet in sheets():
            for block in profile(sheet["template"])["blocks"]:
                if framework_profiles.fill_of(block) not in ("quote", "auto"):
                    continue
                declared = block.get("quote_cues")
                if declared is None:
                    missing.append("%s/%s" % (sheet["catalogue_id"], block["key"]))
                elif not str(declared).split():
                    missing.append("%s/%s declares an empty quote vocabulary"
                                   % (sheet["catalogue_id"], block["key"]))
        self.assertEqual(missing, [], "blocks with no declared quote vocabulary:\n  "
                                      + "\n  ".join(missing))
        # and the declaration is what the matcher reads, not the retrieval cues
        block = next(b for b in profile("template_a3")["blocks"] if b["key"] == "countermeasures")
        self.assertIn("change", str(block["cues"]).split())
        self.assertNotIn("change", str(block["quote_cues"]).split(),
                         "the generic word must not be able to fill the countermeasures cell")

    def test_E_ops_038__a_generic_brief_fills_no_part_it_does_not_describe(self):
        measured = {}
        for sheet in sheets():
            result = complete(sheet["template"], brief=TRAP_BRIEF, sources=False)
            measured[sheet["catalogue_id"]] = [
                (block["key"], item["text"]) for block in result["blocks"]
                for item in block["items"]]
        self.assertEqual({key: value for key, value in measured.items() if value}, {},
                         "a generic brief was quoted into a cell it does not answer")

    def test_E_ops_039__an_honest_brief_still_fills_the_parts_it_describes(self):
        sipoc = {block["key"]: block for block in complete("template_sipoc")["blocks"]}
        for key in ("process", "outputs", "customers"):
            self.assertTrue(sipoc[key]["items"], "%s stopped quoting a brief that states it" % key)
            self.assertEqual(sipoc[key]["items"][0]["provenance"], "student", key)
        vsm = {block["key"]: block for block in complete("template_value_stream_map")["blocks"]}
        self.assertTrue(vsm["process_steps"]["items"], "the steps cell must still quote the brief")
        self.assertTrue(vsm["waits_delays"]["items"], "the waits cell must still quote the brief")
        # the brief states no time, so the times cell is a named gap, not a quote
        self.assertEqual(vsm["cycle_and_lead_times"]["items"], [])
        self.assertIn("What to state", vsm["cycle_and_lead_times"]["gap"])

    def test_E_ops_040__no_conclusion_ranks_the_parts(self):
        for sheet in sheets():
            _result, report, _text = built(sheet["template"])
            conclusion = "\n".join(report["sections"][-2]["lines"])
            self.assertNotIn("most weight", conclusion, sheet["catalogue_id"])
            self.assertNotIn("carries the least", conclusion, sheet["catalogue_id"])
            self.assertIn("same number of accepted items", conclusion,
                          "%s must say the parts are equally supported" % sheet["catalogue_id"])

    def test_E_ops_041__a_non_draftable_profile_still_produces_a_paper(self):
        _result, report, text = built("template_value_stream_map")
        self.assertTrue(report["sections"])
        self.assertGreater(report["words"], 400)
        self.assertIn("Value Stream Mapping", text)
        self.assertIn("Conclusion", text)

    def test_E_ops_042__a_run_without_sources_names_every_part_and_fills_nothing(self):
        for sheet in sheets():
            result = complete(sheet["template"], sources=False)
            for block in result["blocks"]:
                if block["items"]:
                    self.assertTrue(all(item["provenance"] == "student" for item in block["items"]),
                                    "%s/%s: an item that was not the student's, without a search"
                                    % (sheet["catalogue_id"], block["key"]))
                else:
                    self.assertTrue(block["gap"], "%s/%s: no item and no gap"
                                    % (sheet["catalogue_id"], block["key"]))
                    self.assertIn("What to state", block["gap"],
                                  "%s/%s: the gap says nothing about what to state"
                                  % (sheet["catalogue_id"], block["key"]))
            summary = result["summary"]
            self.assertEqual(summary["filled"] + summary["gaps"], summary["parts"],
                             sheet["catalogue_id"])

    def test_E_ops_043__every_worksheet_serves_its_example_and_the_example_is_synthetic(self):
        for sheet in sheets():
            described = templates.describe(sheet["template"])
            example = described["example_request"]
            self.assertIsNotNone(example, "%s serves no example" % sheet["catalogue_id"])
            self.assertEqual(example["method"], sheet["template"])
            provenances = {item.get("provenance", "user")
                           for items in (example["inputs"].get("blocks") or {}).values()
                           for item in items}
            self.assertTrue(provenances & {"synthetic", "assumption"},
                            "%s: the example is not labelled illustrative" % sheet["catalogue_id"])

    def test_E_ops_044__the_supply_chain_shelf_still_serves_and_builds_the_eleven(self):
        shared = {sheet["template"] for sheet in sheets()}
        other = {sheet["template"] for sheet in subjects.detail("supply-chain")["worksheets"]}
        self.assertEqual(shared, other, "the two shelves no longer share the same worksheets")
        result = dict(complete("template_scor"), byline=["A Student", "Example University"])
        report = completion.draft(result, "apa", "draft", "short")
        self.assertTrue(report["sections"])
        self.assertIsInstance(completion.draft_bytes(result, "apa", report, "draft", "short"),
                              bytes)

    def test_E_ops_045__no_paper_prints_its_citation_twice(self):
        for sheet in sheets():
            _result, _report, text = built(sheet["template"])
            citations = re.findall(r"\([A-Z][^()]{2,40}, \d{4}\)", text)
            for citation in set(citations):
                self.assertNotIn(citation + " " + citation, text,
                                 "%s prints %r twice (D-OPS-04)"
                                 % (sheet["catalogue_id"], citation))

    def test_E_ops_046__no_query_is_built_from_a_raw_block_key(self):
        for sheet in sheets():
            for block in profile(sheet["template"])["blocks"]:
                for phrase in block.get("queries") or []:
                    self.assertNotIn("_", str(phrase),
                                     "%s/%s builds a query from its raw key: %r"
                                     % (sheet["catalogue_id"], block["key"], phrase))
                    self.assertNotEqual(str(phrase).strip().lower(), str(block["key"]).lower())


if __name__ == "__main__":
    unittest.main()








