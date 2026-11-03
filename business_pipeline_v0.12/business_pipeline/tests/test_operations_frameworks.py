"""The two operations worksheets and their completion profiles.

SIPOC (`OPS-02`) and the value stream map (`OPS-03`) are the first frameworks
whose facts are the student's own process.  They are T4 structure-and-evidence
worksheets, like every other framework, and their completion profiles carry a
`fill` policy per block so the pipeline completes itself without inventing a
process it cannot observe:

  research - external evidence is retrieved for the part, as for Five Forces;
  quote    - the student's own sentences from the instruction are taken verbatim,
             so a part the brief already states is never re-typed;
  gap      - only the student can state the part, and it is named as a gap.

Nothing here times a step, measures capacity, reads a machine or derives a
score, ranking or verdict.
"""

import copy
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, "src")
from bp import registry as R, templates as T  # noqa: E402
from bp.product import completion, framework_profiles, subjects  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _PATH(*parts):
    """A file beside the package, read as text: the served page is part of the product."""
    return os.path.join(ROOT, *parts)


NEW = {
    "template_sipoc": "OPS-02",
    "template_value_stream_map": "OPS-03",
    "template_a3": "OPS-05",
    "template_toc": "OPS-06",
    "template_scor": "OPS-01",
    "template_5s": "OPS-04",
    "template_root_cause": "OPS-07",
    "template_fmea": "OPS-08",
    "template_kraljic": "OPS-10",
    "template_sop": "OPS-11",
    "template_pdca": "OPS-12",
}

#: A brief that already describes the process, so the `quote` parts have
#: something honest to quote and the student need not type it twice.  The second
#: sentence states the times because a times cell has to be given a time: the old
#: brief filled it on the word "takes" in "takes an order", which is D-OPS-03.
#: The third states the output, because "packs the meal" names the meal and not
#: what the process hands on — quoting it into Outputs was the same defect.
BRIEF = ("The lunch service at the meal counter takes an order, assembles and packs the meal, then the "
         "student collects and pays. Taking an order takes about a minute, packing four and the noon "
         "wait twelve minutes. The counter hands on a packed meal and a payment receipt. "
         "Bread arrives from one regional bakery every morning before opening.")
#: The same brief with no time anywhere in it: what the times cell must refuse.
BRIEF_NO_TIMES = ("The lunch service at the meal counter takes an order, assembles and packs the meal, "
                  "then the student collects and pays. The counter hands on a packed meal and a "
                  "payment receipt. Bread arrives from one regional bakery every morning before "
                  "opening.")
PROCESS = "the lunch service at the meal counter"


def example(kind):
    return copy.deepcopy(T.EXAMPLES[kind])


def results(kind, req):
    out = T.run_template(kind, req["inputs"])
    return {name: ok for name, ok in out["results"]}, out


def _source(title="Regional bakery supply", abstract="A single regional mill supplies most of the bread flour "
                                                     "in the study area."):
    return {"title": title, "abstract": abstract, "doi": None, "url": None, "database": "openalex"}


def _fake_retrieve(key, cues, queries, context, **kwargs):
    """One supplier source, nothing anywhere else: a typical quiet search."""
    items = [_source()] if key == "suppliers" else []
    return {"items": items, "queries": queries, "dropped": 0, "errors": [], "skipped": [],
            "notices": [], "timed_out": False}


def complete_sipoc(instruction=BRIEF, unit=PROCESS):
    with mock.patch.object(completion.retrieval, "retrieve", _fake_retrieve), \
         mock.patch.object(completion.retrieval, "first_sentence",
                           lambda source, sentences=2: source["abstract"]), \
         mock.patch.object(completion, "_source_text",
                           lambda source: source["title"] + " (2024)"), \
         mock.patch.object(completion, "_source_cite", lambda source: "(Regional mill, 2024)"):
        return completion.complete("template_sipoc", instruction, unit_value=unit)


def complete_vsm(instruction=BRIEF, unit=PROCESS):
    with mock.patch.object(completion.retrieval, "retrieve", _fake_retrieve):
        return completion.complete("template_value_stream_map", instruction, unit_value=unit)


class RegistrationTest(unittest.TestCase):
    def test_every_new_worksheet_is_t4_and_links_its_record(self):
        for kind, rid in NEW.items():
            template = T.TEMPLATES[kind]
            self.assertEqual(template["tier"], "T4", kind)
            self.assertEqual(template["registry_ids"], [rid], kind)
            self.assertEqual(R.get(rid)["template"], kind, rid)
            self.assertEqual(R.get(rid)["form"], "worksheet", rid)

    def test_every_new_worksheet_declares_the_form_the_page_renders(self):
        for kind in NEW:
            self.assertEqual(T.describe(kind)["form_kind"], "canvas", kind)

    def test_every_new_worksheet_describes_its_limits_and_unsupported_use(self):
        for kind in NEW:
            described = T.describe(kind)
            self.assertTrue(described["intended_use"], kind)
            self.assertTrue(described["unsupported_use"], kind)
            self.assertTrue(described["limitations"], kind)
            self.assertTrue(described["defaults"], kind)
            self.assertTrue(described["planned_checks"], kind)
            self.assertIn("blocks", described["input_help"], kind)

    def test_the_operations_shelf_offers_both_and_no_record_is_repeated(self):
        for subject_id in ("operations", "supply-chain"):
            page = subjects.detail(subject_id)
            offered = {worksheet["template"] for worksheet in page["worksheets"]}
            self.assertTrue(set(NEW).issubset(offered), subject_id)
            self.assertFalse({row["id"] for row in page["records"]}
                             & {w["catalogue_id"] for w in page["worksheets"]}, subject_id)

    def test_the_sipoc_worksheet_is_draftable_from_research_and_the_vsm_is_not(self):
        """Only the parts a source can legitimately fill are drafted into."""
        from bp.product import drafting

        sheets = {sheet["catalogue_id"]: sheet for sheet in subjects.detail("operations")["worksheets"]}
        self.assertTrue(sheets["OPS-02"].get("draftable"))
        self.assertFalse(sheets["OPS-03"].get("draftable"))
        self.assertTrue(drafting.supported("template_sipoc"))
        self.assertFalse(drafting.supported("template_value_stream_map"))

    def test_the_registry_accepts_the_new_template_links(self):
        self.assertEqual(R.validate(R.load()), [])


class ExampleTest(unittest.TestCase):
    def test_the_completion_reports_how_the_page_may_count_it(self):
        """The page shows '3 of 5 parts' from the server, never from its own arithmetic."""
        result = complete_sipoc()
        summary = result["summary"]
        self.assertEqual(summary["parts"], 5)
        self.assertEqual(summary["filled"], len([b for b in result["blocks"] if b["items"]]))
        self.assertEqual(summary["filled"] + summary["gaps"], summary["parts"])

    def test_every_block_says_how_it_was_completed(self):
        result = complete_sipoc()
        fills = {block["key"]: block["fill"] for block in result["blocks"]}
        self.assertEqual(fills, {"suppliers": "research", "inputs": "research", "process": "quote",
                                 "outputs": "quote", "customers": "quote"})
        vsm = {block["key"]: block["fill"] for block in complete_vsm()["blocks"]}
        self.assertEqual(vsm["value_added"], "gap")
        self.assertEqual(vsm["improvements"], "gap")

    def test_the_worksheet_page_shows_the_three_steps_and_the_badges(self):
        page = open(_PATH("web", "index.html"), encoding="utf-8").read()
        for needle in ('class="stepbar"', "function fillBadge", "Researched", "From your brief",
                       "You state this", "result.summary", "Completes itself from your brief"):
            self.assertIn(needle, page, needle)

    def test_the_operations_page_leads_with_the_frameworks(self):
        page = open(_PATH("web", "index.html"), encoding="utf-8").read()
        self.assertIn("Complete a framework", page)
        self.assertIn("sheets.length\n      ? '<h3", page)

    def test_every_example_runs_and_passes_its_own_checks(self):
        for kind in NEW:
            checks, _out = results(kind, example(kind))
            self.assertTrue(all(checks.values()), "%s: %s" % (kind, checks))

    def test_an_empty_block_is_named_and_never_filled(self):
        req = example("template_sipoc")
        req["inputs"]["blocks"]["customers"] = []
        kind = "template_sipoc"
        checks, out = results(kind, req)
        self.assertIn("customers", out["analysis"]["audit"]["empty_blocks"], kind)
        self.assertTrue(checks["empty_blocks_reported_not_filled"], kind)

    def test_no_score_ranking_or_verdict_is_derived(self):
        for kind in NEW:
            _checks, out = results(kind, example(kind))
            analysis = out["analysis"]
            for forbidden in ("score", "overall", "verdict", "ranking", "rank"):
                self.assertNotIn(forbidden, analysis, kind)
            self.assertNotIn(forbidden, analysis.get("counts", {}), kind)

    def test_a_synthetic_item_stays_marked_and_is_not_presented_as_evidence(self):
        checks, out = results("template_sipoc", example("template_sipoc"))
        self.assertTrue(out["analysis"]["audit"]["synthetic_items"], "template_sipoc")
        self.assertTrue(checks["assumptions_and_synthetic_flagged"])


class FillPolicyTest(unittest.TestCase):
    """The profile says how each part may be completed; the engine obeys it."""

    def test_the_two_profiles_validate_and_carry_every_block(self):
        for kind in NEW:
            profile = framework_profiles.profile_for(kind)
            self.assertEqual(profile["template"], kind, kind)
            self.assertEqual(len(profile["blocks"]), len(T.CANVAS_BLOCKS[kind]), kind)
            self.assertEqual([b["key"] for b in profile["blocks"]], list(T.CANVAS_BLOCKS[kind]), kind)

    def test_the_profiles_are_declared_as_operations_frameworks(self):
        for kind in NEW:
            self.assertEqual(framework_profiles.get(kind)["subject"], "operations", kind)
            self.assertEqual(framework_profiles.get(kind)["unit"]["field"], "process", kind)

    def test_only_a_research_block_carries_queries(self):
        for kind in NEW:
            for block in framework_profiles.get(kind)["blocks"]:
                if framework_profiles.fill_of(block) in ("research", "auto"):
                    self.assertTrue(block["queries"], "%s: %s" % (kind, block["key"]))
                else:
                    self.assertFalse(block.get("queries"), "%s: %s carries research for a part that is the student's"
                                      % (kind, block["key"]))

    def test_a_profile_with_an_unknown_fill_is_refused(self):
        broken = copy.deepcopy(framework_profiles.get("template_sipoc"))
        broken["blocks"][0]["fill"] = "guess"
        with mock.patch.dict(framework_profiles.PROFILES, {"template_broken": broken}):
            with self.assertRaises(ValueError):
                framework_profiles.profile_for("template_broken")

    def test_the_page_is_told_which_parts_it_may_complete(self):
        described = framework_profiles.describe_extra("template_sipoc")
        fills = {block["key"]: block["fill"] for block in described["blocks"]}
        self.assertEqual(fills, {"suppliers": "research", "inputs": "research", "process": "quote",
                                 "outputs": "quote", "customers": "quote"})
        self.assertTrue(described["fills"])


class CompletionTest(unittest.TestCase):
    """The brief completes the framework: the student types nothing twice."""

    def test_the_brief_supplies_the_parts_the_brief_already_states(self):
        result = complete_sipoc()
        blocks = {block["key"]: block for block in result["blocks"]}
        for key in ("process", "outputs", "customers"):
            self.assertTrue(blocks[key]["items"], key)
            self.assertEqual(blocks[key]["items"][0]["provenance"], "student", key)
            # the quote is the student's own sentence, not a paraphrase and not a
            # different part's sentence: "packs the meal" names the meal, and the
            # output cell now needs the sentence that actually states the output
            self.assertIn(blocks[key]["items"][0]["text"], BRIEF, key)

    def test_a_quoted_item_is_the_students_own_words_not_a_paraphrase(self):
        result = complete_sipoc()
        blocks = {block["key"]: block for block in result["blocks"]}
        for item in blocks["process"]["items"]:
            self.assertIn(item["text"], BRIEF, "the quote is not the brief verbatim")

    def test_a_research_block_carries_the_sourced_evidence_with_its_citation(self):
        result = complete_sipoc()
        suppliers = next(b for b in result["blocks"] if b["key"] == "suppliers")
        self.assertEqual([item["provenance"] for item in suppliers["items"]], ["sourced"])
        self.assertEqual(suppliers["items"][0]["source"], "Regional bakery supply (2024)")

    def test_a_part_the_search_misses_is_a_named_gap_not_a_fill(self):
        result = complete_sipoc()
        inputs = next(b for b in result["blocks"] if b["key"] == "inputs")
        self.assertEqual(inputs["items"], [])
        self.assertIn("No evidence was found", inputs["gap"])
        self.assertIn("name each input", inputs["gap"])

    def test_the_value_stream_map_never_searches_for_a_part_the_student_owns(self):
        result = complete_vsm()
        keys = [block["key"] for block in result["blocks"]]
        self.assertEqual(keys, ["process_steps", "cycle_and_lead_times", "inventory_wip",
                                "waits_delays", "value_added", "improvements"])
        blocks = {block["key"]: block for block in result["blocks"]}
        for key in ("process_steps", "cycle_and_lead_times"):
            self.assertTrue(blocks[key]["items"], key)
            self.assertEqual(blocks[key]["items"][0]["provenance"], "student", key)
        # The judgement and the proposal are the student's; the pipeline states
        # what is wanted and fills nothing.
        for key in ("value_added", "improvements"):
            self.assertEqual(blocks[key]["items"], [], key)
            self.assertIn("only you can state", blocks[key]["gap"].lower(), key)

    def test_a_times_cell_is_not_filled_by_the_word_takes(self):
        """D-OPS-03: `takes an order` is not a duration, and the cell must not say it is."""
        result = complete_vsm(BRIEF_NO_TIMES)
        blocks = {block["key"]: block for block in result["blocks"]}
        self.assertEqual(blocks["cycle_and_lead_times"]["items"], [])
        self.assertIn("No evidence was found", blocks["cycle_and_lead_times"]["gap"])
        self.assertIn("What to state", blocks["cycle_and_lead_times"]["gap"])
        # the step cell still holds the student's own sentence: the fix narrows the
        # match, it does not switch the fallback off
        self.assertTrue(blocks["process_steps"]["items"])
        self.assertEqual(blocks["process_steps"]["items"][0]["provenance"], "student")

    def test_the_process_is_never_detected_only_declared(self):
        with self.assertRaises(ValueError) as error:
            completion.complete("template_sipoc", BRIEF, unit_value="")
        self.assertIn("Name the process you are mapping", str(error.exception))

    def test_a_short_instruction_is_refused_before_any_research(self):
        with self.assertRaises(ValueError):
            complete_sipoc(instruction="Map the line")

    def test_the_worksheet_takes_the_completed_blocks_verbatim(self):
        """The review result runs the worksheet the student is handed."""
        result = complete_sipoc()
        inputs = {"inputs": {"blocks": {block["key"]: [{"text": item["text"],
                                                        "provenance": "user",
                                                        "source": item.get("source")}
                                                       for item in block["items"]]
                                        for block in result["blocks"]}}}
        checks, _out = results("template_sipoc", inputs)
        self.assertTrue(all(checks.values()), checks)


class MissingGateTest(unittest.TestCase):
    def test_a_part_with_neither_evidence_nor_an_acknowledged_gap_blocks_the_paper(self):
        result = complete_sipoc()
        self.assertTrue(completion.missing(result))
        self.assertIn("Inputs", completion.missing(result))

    def test_the_gate_clears_only_when_the_student_acknowledges_the_gap(self):
        result = complete_sipoc()
        result["acknowledged_gaps"] = ["inputs"]
        self.assertEqual(completion.missing(result), [])

    def test_a_gap_is_named_by_the_frameworks_own_word_for_the_part(self):
        result = complete_vsm()
        labels = completion.missing(result)
        self.assertTrue(any("value-added" in label.lower() for label in labels), labels)


class GuardTest(unittest.TestCase):
    def test_an_operations_framework_is_not_refused_as_a_computation(self):
        """A process brief legitimately names capacity and variance."""
        result = complete_sipoc(instruction=BRIEF + " The kitchen varies its output between runs.")
        self.assertTrue(result["blocks"])

    def test_an_accounting_brief_is_still_refused_on_an_operations_framework(self):
        with self.assertRaises(ValueError) as error:
            complete_sipoc(instruction=BRIEF + " The journal entry and the trial balance are attached.")
        self.assertIn("Accounting", str(error.exception))


class HonestyTest(unittest.TestCase):
    def test_the_completion_carries_no_number_the_pipeline_did_not_receive(self):
        """Nothing measured: a number in a quoted item is the student's own."""
        result = complete_sipoc(instruction=BRIEF + " About 90 seconds are taken to serve each student.")
        quoted = [item["text"] for block in result["blocks"] for item in block["items"]
                  if item["provenance"] == "student"]
        self.assertTrue(any("90 seconds" in text for text in quoted), quoted)

    def test_the_worksheet_states_that_it_does_not_observe_the_process(self):
        for kind in NEW:
            self.assertIn("observ", T.describe(kind)["unsupported_use"].lower(), kind)


class MapTest(unittest.TestCase):
    """The drawing is labels, not numbers, and it draws what was declared."""

    def setUp(self):
        from bp.product import mapsheet
        self.mapsheet = mapsheet

    def completion(self, template="template_sipoc", blocks=None):
        return {"template": template, "unit": {"field": "process", "value": "the lunch service"},
                "blocks": blocks if blocks is not None else [
                    {"key": "suppliers", "label": "Suppliers",
                     "items": [{"text": "The regional bakery"}]},
                    {"key": "inputs", "label": "Inputs", "items": []},
                    {"key": "process", "label": "Process steps",
                     "items": [{"text": "Take the order"}, {"text": "Pack the meal"}]},
                    {"key": "outputs", "label": "Outputs", "items": [{"text": "A packed meal"}]},
                    {"key": "customers", "label": "Customers", "items": [{"text": "The student"}]},
                ]}

    def test_every_declared_part_is_drawn_in_its_own_column(self):
        out = self.mapsheet.build(self.completion())
        self.assertTrue(out["drawn"])
        for label in ("Suppliers", "Inputs", "Process steps", "Outputs", "Customers"):
            self.assertIn(label, out["svg"])
        self.assertIn("The regional bakery", out["svg"])
        self.assertIn("gap", out["svg"])

    def test_a_line_with_a_number_is_left_out_and_counted(self):
        blocks = self.completion()["blocks"]
        blocks[2]["items"].append({"text": "About 90 seconds per order"})
        out = self.mapsheet.build(self.completion(blocks=blocks))
        self.assertNotIn("90 seconds", out["svg"])
        self.assertEqual(out["omitted"], 1)

    def test_a_map_with_no_items_is_not_drawn(self):
        blocks = [{k: [] for k in ("suppliers", "inputs", "process", "outputs", "customers")}]
        blocks = [{"key": key, "label": key.title(), "items": []} for key in
                  ("suppliers", "inputs", "process", "outputs", "customers")]
        out = self.mapsheet.build(self.completion(blocks=blocks))
        self.assertFalse(out["drawn"])
        self.assertIsNone(out["svg"])

    def test_the_value_stream_draws_steps_and_never_places_a_wait_between_them(self):
        blocks = [
            {"key": "process_steps", "label": "Process steps",
             "items": [{"text": "Take the order"}, {"text": "Pack the meal"}]},
            {"key": "cycle_and_lead_times", "label": "Cycle and lead times", "items": []},
            {"key": "inventory_wip", "label": "Inventory and work in progress", "items": []},
            {"key": "waits_delays", "label": "Waits and delays", "items": [{"text": "Queue at the counter"}]},
            {"key": "value_added", "label": "Value-added assessment", "items": []},
            {"key": "improvements", "label": "Improvement opportunities", "items": []},
        ]
        out = self.mapsheet.build(self.completion("template_value_stream_map", blocks))
        self.assertTrue(out["drawn"])
        self.assertIn("Take the order", out["svg"])
        self.assertIn("Queue at the counter", out["svg"])

    def test_a_sentence_shared_by_two_parts_is_not_drawn_twice(self):
        """Repeating one brief sentence in three columns would read as three findings."""
        blocks = self.completion()["blocks"]
        blocks[3]["items"] = [{"text": blocks[2]["items"][0]["text"]}]
        out = self.mapsheet.build(self.completion(blocks=blocks))
        self.assertEqual(out["svg"].count("Take the order"), 1)
        self.assertIn("see Process steps", out["svg"])

    def test_a_label_cannot_inject_markup(self):
        blocks = self.completion()["blocks"]
        blocks[0]["items"] = [{"text": '<script>alert("x")</script>'}]
        out = self.mapsheet.build(self.completion(blocks=blocks))
        self.assertNotIn("<script>", out["svg"])
        self.assertIn("&lt;script&gt;", out["svg"])

    def test_an_unsupported_framework_is_refused(self):
        with self.assertRaises(ValueError):
            self.mapsheet.build({"template": "template_swot", "blocks": []})

    def test_the_route_returns_the_drawing(self):
        from bp.product import api
        code, out = api.handle("POST", "/api/cases/worksheets/map", {"completion": self.completion()})
        self.assertEqual(code, 200)
        self.assertTrue(out["drawn"])
        self.assertIn("<svg", out["svg"])

    def test_the_route_refuses_a_bad_object(self):
        from bp.product import api
        code, out = api.handle("POST", "/api/cases/worksheets/map", {"completion": "nope"})
        self.assertEqual(code, 422)


class AutoFillTest(unittest.TestCase):
    """`auto` researches first, then takes the student's own words, then a gap."""

    def complete(self, retrieve):
        with mock.patch.object(completion.retrieval, "retrieve", retrieve), \
             mock.patch.object(completion.retrieval, "first_sentence",
                               lambda source, sentences=2: source.get("abstract", "")), \
             mock.patch.object(completion, "_source_text", lambda source: source["title"]), \
             mock.patch.object(completion, "_source_cite", lambda source: "(Study, 2024)"):
            return completion.complete(
                "template_a3",
                "The problem is a queue at noon. The lunch service at the meal counter is delayed by the single "
                "oven, which limits how many meals can be served, so students wait.",
                unit_value="the lunch service at the meal counter")

    @staticmethod
    def nothing(key, cues, queries, context, **kwargs):
        return {"items": [], "queries": queries, "dropped": 0, "errors": [], "skipped": [],
                "notices": [], "timed_out": False}

    def test_a_part_without_a_source_falls_back_to_the_brief(self):
        result = self.complete(self.nothing)
        problem = next(b for b in result["blocks"] if b["key"] == "problem")
        self.assertEqual(problem["fill"], "auto")
        self.assertTrue(problem["items"])
        self.assertEqual(problem["items"][0]["provenance"], "student")

    def test_a_part_with_neither_source_nor_brief_is_a_named_gap(self):
        result = self.complete(self.nothing)
        follow = next(b for b in result["blocks"] if b["key"] == "follow_up")
        self.assertEqual(follow["items"], [])
        self.assertIn("No evidence was found", follow["gap"])
        self.assertIn("What to state", follow["gap"])

    def test_a_source_wins_over_the_brief_on_an_auto_part(self):
        def one(key, cues, queries, context, **kwargs):
            items = [{"title": "Queue study", "abstract": "Waiting time rises sharply when one server serves "
                                                          "a peak.", "doi": None, "url": None,
                      "database": "openalex"}] if key == "problem" else []
            return {"items": items, "queries": queries, "dropped": 0, "errors": [], "skipped": [],
                    "notices": [], "timed_out": False}

        result = self.complete(one)
        problem = next(b for b in result["blocks"] if b["key"] == "problem")
        self.assertEqual(problem["items"][0]["provenance"], "sourced")
        self.assertNotIn("lunch service", problem["items"][0]["text"])


class TruthTest(unittest.TestCase):
    """The shelf must not say a method is missing when it ships."""

    def test_spc_is_not_reported_as_unbuilt(self):
        row = next(r for r in subjects.detail("operations")["records"] if r["id"] == "OPS-09")
        self.assertNotEqual(row["status_short"], "Method not built")
        self.assertEqual(row["form"], "computed")

    def test_the_queue_record_names_the_multi_server_model(self):
        row = next(r for r in subjects.detail("operations")["records"] if r["id"] == "QNT-OPS-04")
        self.assertIn("M/M/c", row["status_note"])

    def test_the_cpm_record_does_not_deny_the_scheduling_methods_that_ship(self):
        row = next(r for r in subjects.detail("operations")["records"] if r["id"] == "QNT-OPS-05")
        self.assertIn("resource_leveling", row["status_note"])
        self.assertIn("calendar_schedule", row["status_note"])


if __name__ == "__main__":
    unittest.main()
