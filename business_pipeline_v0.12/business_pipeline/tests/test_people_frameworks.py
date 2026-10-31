"""People & organisation: the eight frameworks the shelf now completes.

The tests are the behaviour the Five Forces and PESTEL pilots proved, applied to
the People shelf.  Every framework here is a T4 structure-and-evidence worksheet
on its own canvas, and every part of it is a `research` block: the pipeline
retrieves what a source can support, and where nothing is found it writes the
framework's own general background paragraph as an uncited item, so a part is
never a notice, never a blank and never a gate.

Nothing here designs a role, runs a training, chooses an intervention, scores a
person or predicts who will succeed.  The frameworks record and evidence a
decision; they state what they cannot settle.
"""

import copy
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, "src")
from bp import registry as R, templates as T  # noqa: E402
from bp.product import completion, drafting, framework_profiles, subjects  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _PATH(*parts):
    """A file beside the package, read as text: the served page is part of the product."""
    return os.path.join(ROOT, *parts)


#: template -> (catalogue id, number of blocks, the unit the student names, the brief).
NEW = {
    "template_job_characteristics": (
        "PPL-03", 5, "the kitchen supervisor",
        "The role of the kitchen supervisor needs reviewing before the pay round."),
    "template_kirkpatrick": (
        "PPL-02", 4, "the food-safety induction for kitchen staff",
        "The food-safety induction for kitchen staff has to be judged before it runs again this year."),
    "template_amo": (
        "PPL-01", 3, "slow service on the meal counter",
        "Service on the meal counter is slow at lunchtime and the manager has to say why."),
    "template_tuckman": (
        "PPL-05", 5, "the tray assembly team",
        "The tray assembly team is not working as it should and the manager has to review it."),
    "template_nine_box": (
        "PPL-04", 4, "the counter team",
        "The counter team needs a talent review before the two vacancies are filled."),
    "template_kotter": (
        "CHG-01", 8, "moving the campus meal card to a contactless system",
        "The campus meal card is moving to a contactless system and the manager has to plan the change."),
    "template_competing_values": (
        "CHG-12", 4, "the campus catering team",
        "The campus catering team has to be understood before the service is changed."),
    "template_org_design": (
        "CHG-11", 6, "the catering unit of the university",
        "The catering unit of the university is being reorganised and the design has to be checked."),
}

#: Words a section heading may keep in lower case.
STOP_WORDS = {"a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "of", "on",
              "or", "the", "to", "with", "its", "their"}

#: Every cue word of every People framework, so one source can be made to match
#: every part: the gate then has to refuse to let it fill more than one.
CUE_BLOB = " ".join(sorted({word for kind in NEW
                            for block in framework_profiles.get(kind)["blocks"]
                            for word in block["cues"].split()}))

#: Every unit the student may name, so one fixed title can carry the unit words
#: each framework's gate looks for.
UNIT_BLOB = " ".join(sorted({word for _cid, _count, unit, _brief in NEW.values()
                             for word in unit.split()}))


def academic(query, databases=None, limit=10, year_from=None):
    """A source whose title carries the query, so the block gate can judge it."""
    return {"results": [{
        "title": query[:70],
        "abstract": "Evidence on the conditions named in the query. A second sentence follows it.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of People Studies", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def complete(kind, unit=None, instruction=None, **kwargs):
    """One completion with the searches mocked, so the tests read the engine's behaviour."""
    _cid, _count, default_unit, brief = NEW[kind]
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
            mock.patch("bp.product.sources.search_web", side_effect=web):
        return completion.complete(kind, instruction or brief,
                                    unit_value=default_unit if unit is None else unit, **kwargs)


def quiet_complete(kind, unit=None, instruction=None):
    """A completion with no source at all: every part must fall back to the background."""
    _cid, _count, default_unit, brief = NEW[kind]
    with mock.patch("bp.product.sources.search_academic",
                    return_value={"results": [], "errors": [], "skipped": []}), \
            mock.patch("bp.product.sources.search_web", side_effect=web), \
            mock.patch("bp.product.prose._call", side_effect=AssertionError("the model must not run")):
        return completion.complete(kind, instruction or brief,
                                    unit_value=default_unit if unit is None else unit)


class RegistrationTest(unittest.TestCase):
    """Each framework is a T4 worksheet on its own canvas, linked to its record."""

    def test_every_new_worksheet_is_t4_and_links_its_record(self):
        for kind, (cid, count, _unit, _brief) in NEW.items():
            template = T.TEMPLATES[kind]
            self.assertEqual(template["tier"], "T4", kind)
            self.assertEqual(template["registry_ids"], [cid], kind)
            self.assertEqual(R.get(cid)["template"], kind, cid)
            self.assertEqual(R.get(cid)["form"], "worksheet", cid)
            self.assertEqual(len(T.CANVAS_BLOCKS[kind]), count, kind)

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

    def test_the_registry_accepts_the_new_template_links(self):
        self.assertEqual(R.validate(R.load()), [])

    def test_every_worksheet_can_be_drafted_from_the_sources_it_retrieves(self):
        """A draftable worksheet must have a drafting schema: no button that can only 422."""
        for kind in NEW:
            self.assertTrue(drafting.supported(kind), kind)


class ProfileTest(unittest.TestCase):
    """The profile says how each part may be completed; the engine obeys it."""

    def test_the_profiles_carry_every_block_of_their_canvas(self):
        for kind, (_cid, count, _unit, _brief) in NEW.items():
            profile = framework_profiles.profile_for(kind)
            self.assertEqual(profile["template"], kind, kind)
            self.assertEqual(len(profile["blocks"]), count, kind)
            self.assertEqual([b["key"] for b in profile["blocks"]], list(T.CANVAS_BLOCKS[kind]), kind)
            for block in profile["blocks"]:
                self.assertEqual(T.CANVAS_BLOCKS[kind][block["key"]][0], block["label"],
                                 "%s: %s" % (kind, block["key"]))

    def test_the_profiles_are_declared_as_people_frameworks(self):
        for kind in NEW:
            self.assertEqual(framework_profiles.get(kind)["subject"], "people", kind)
            self.assertEqual(framework_profiles.get(kind)["unit"]["field"], "process", kind)

    def test_every_part_is_a_research_block_and_carries_a_query(self):
        """A People framework researches each part: none of them is the student's to fill."""
        for kind in NEW:
            for block in framework_profiles.get(kind)["blocks"]:
                self.assertEqual(framework_profiles.fill_of(block), "research",
                                 "%s: %s" % (kind, block["key"]))
                self.assertTrue(block["queries"], "%s: %s" % (kind, block["key"]))
                self.assertTrue(block["cues"], "%s: %s" % (kind, block["key"]))

    def test_every_part_carries_a_probe_and_a_background_paragraph_without_a_figure(self):
        for kind in NEW:
            for block in framework_profiles.get(kind)["blocks"]:
                notes = framework_profiles.get(kind)["notes"][block["key"]]
                self.assertTrue(notes["probe"], "%s: %s" % (kind, block["key"]))
                self.assertFalse(any(char.isdigit() for char in notes["analysis"]),
                                 "%s: %s states a figure" % (kind, block["key"]))

    def test_the_page_is_told_which_parts_it_may_complete(self):
        for kind in NEW:
            described = framework_profiles.describe_extra(kind)
            fills = {block["key"]: block["fill"] for block in described["blocks"]}
            self.assertEqual(set(fills.values()), {"research"}, kind)
            self.assertTrue(described["fills"], kind)


class PeoplePageTest(unittest.TestCase):
    """The shelf a student meets: six tiles, nothing dropped, nothing pretended."""

    def setUp(self):
        self.page = subjects.detail("people")

    def test_the_page_offers_every_framework_as_a_draftable_worksheet(self):
        offered = {sheet["catalogue_id"]: sheet for sheet in self.page["worksheets"]}
        for kind, (cid, _count, _unit, _brief) in NEW.items():
            self.assertIn(cid, offered, cid)
            self.assertEqual(offered[cid]["template"], kind, cid)
            self.assertTrue(offered[cid]["draftable"], cid)

    def test_no_record_is_repeated_as_a_worksheet_and_a_catalogue_row(self):
        self.assertFalse({row["id"] for row in self.page["records"]}
                         & {sheet["catalogue_id"] for sheet in self.page["worksheets"]})

    def test_the_page_has_the_six_tiles_in_the_order_a_student_meets_them(self):
        self.assertEqual([tile["key"] for tile in self.page["tiles"]],
                         ["strategy_design", "resourcing", "development", "reward",
                          "engagement_culture", "analytics"])

    def test_every_tile_says_what_it_covers_and_what_the_student_needs(self):
        for tile in self.page["tiles"]:
            self.assertTrue(tile["what"], tile["key"])
            self.assertTrue(tile["need"], tile["key"])

    def test_every_worksheet_and_every_record_is_in_a_tile(self):
        placed = set()
        for tile in self.page["tiles"]:
            for sheet in tile["worksheets"]:
                placed.add(sheet["catalogue_id"])
            for row in tile["records"]:
                placed.add(row["id"])
        self.assertEqual(placed, {sheet["catalogue_id"] for sheet in self.page["worksheets"]}
                         | {row["id"] for row in self.page["records"]})

    def test_the_reward_tile_is_empty_and_says_why(self):
        """A gap in the shelf is named, not hidden and not faked."""
        reward = next(tile for tile in self.page["tiles"] if tile["key"] == "reward")
        self.assertEqual(reward["worksheets"], [])
        self.assertEqual(reward["records"], [])
        self.assertTrue(reward["note"])
        self.assertIn("no reward or job-evaluation framework", reward["note"].lower())

    def test_the_analytics_tile_holds_every_calculator_and_each_carries_a_period(self):
        analytics = next(tile for tile in self.page["tiles"] if tile["key"] == "analytics")
        self.assertEqual(len(analytics["tools"]), len(self.page["tools"]))
        for tool in analytics["tools"]:
            self.assertTrue(tool["period"], tool["key"])
            self.assertIn(tool["period"], ("annual", "per period", "per observation", "point in time"),
                          tool["key"])
            self.assertTrue(tool["formula"], tool["key"])
            self.assertTrue(tool["steps"], tool["key"])
            self.assertTrue(tool["common_mistakes"], tool["key"])
            self.assertTrue(tool["need"], tool["key"])

    def test_the_shelf_says_it_computes_no_headcount_or_turnover(self):
        """The page must not imply a metric the frozen core cannot compute."""
        does_not = " ".join(self.page["does_not"]).lower()
        for needle in ("turnover", "headcount", "compa-ratio"):
            self.assertIn(needle, does_not)


class CompletionTest(unittest.TestCase):
    """The brief completes the framework, and the paper says what it can and cannot settle."""

    def test_every_block_carries_an_item(self):
        for kind, (_cid, count, _unit, _brief) in NEW.items():
            result = complete(kind)
            self.assertEqual(len(result["blocks"]), count, kind)
            for block in result["blocks"]:
                self.assertTrue(block["items"], "%s: %s" % (kind, block["key"]))
                for item in block["items"]:
                    if item["provenance"] == "sourced":
                        self.assertTrue(item["source"], "%s: %s" % (kind, block["key"]))
                        self.assertTrue(item["citation"], "%s: %s" % (kind, block["key"]))

    def test_the_unit_is_named_by_the_student_and_never_guessed(self):
        for kind, (_cid, _count, _unit, brief) in NEW.items():
            with self.assertRaises(ValueError) as refused:
                completion.complete(kind, brief, unit_value="")
            self.assertIn("Name", str(refused.exception))
            self.assertEqual(complete(kind)["unit"]["value"], NEW[kind][2], kind)

    def test_a_no_source_run_gives_one_background_item_per_block(self):
        for kind in NEW:
            result = quiet_complete(kind)
            for block in result["blocks"]:
                self.assertEqual(len(block["items"]), 1, "%s: %s" % (kind, block["key"]))
                self.assertEqual(block["items"][0]["provenance"], "background",
                                 "%s: %s" % (kind, block["key"]))
                self.assertFalse(block["items"][0]["source"], "%s: %s" % (kind, block["key"]))
                self.assertFalse(block["gap"], "%s: %s" % (kind, block["key"]))
                self.assertFalse(any(char.isdigit() for char in block["items"][0]["text"]),
                                 "%s: %s states a figure" % (kind, block["key"]))

    def test_a_no_source_run_never_gates_the_paper(self):
        for kind in NEW:
            self.assertEqual(completion.missing(quiet_complete(kind)), [], kind)

    def test_one_source_cannot_fill_two_blocks(self):
        def everything(query, databases=None, limit=10, year_from=None):
            return {"results": [{
                "title": UNIT_BLOB + " " + CUE_BLOB,
                "abstract": "One source covers every part the framework names.",
                "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
                "venue": "Journal", "doi": "10.1/same", "url": "https://doi.org/10.1/same",
                "database": "OpenAlex"}], "errors": [], "skipped": []}

        for kind in NEW:
            with mock.patch("bp.product.sources.search_academic", side_effect=everything), \
                    mock.patch("bp.product.sources.search_web", side_effect=web):
                result = completion.complete(kind, NEW[kind][3], unit_value=NEW[kind][2])
            sourced = [block for block in result["blocks"]
                       if any(item["provenance"] == "sourced" for item in block["items"])]
            self.assertEqual(len(sourced), 1, kind)

    def test_the_outline_headings_are_title_cased(self):
        for kind, (_cid, _count, _unit, _brief) in NEW.items():
            report = completion.draft(complete(kind), "apa", "draft")
            headings = [section["heading"] for section in report["sections"]]
            for required in ("Introduction", "Discussion", "What the Evidence Shows",
                             "Implications for the Decision", "Limitations", "Conclusion", "References"):
                self.assertIn(required, headings, kind)
            for heading in headings:
                for word in heading.split():
                    if word.lower() in STOP_WORDS:
                        continue
                    self.assertTrue(word[0].isupper() or word[0].isdigit(),
                                    "%s: %s is not title cased" % (kind, heading))

    def test_the_title_carries_the_framework_prefix_and_drops_the_trailing_period(self):
        for kind in NEW:
            profile = framework_profiles.get(kind)
            result = complete(kind, instruction=NEW[kind][3] + ".")
            report = completion.draft(result, "apa", "draft")
            self.assertTrue(report["title"].startswith(profile["title_prefix"] + ": "), kind)
            self.assertFalse(report["title"].endswith("."), kind)
            self.assertEqual(report["framework"], profile["label"], kind)

    def test_the_byline_reaches_the_title_page_and_the_length_is_reported(self):
        for kind in NEW:
            result = dict(complete(kind), byline=["A Student", "Example University"])
            report = completion.draft(result, "apa", "draft", "long")
            self.assertEqual(report["byline"], ["A Student", "Example University"], kind)
            self.assertEqual(report["length"], "long", kind)
            self.assertEqual(report["length_label"], "Long", kind)

    def test_the_paper_generates_with_an_empty_block(self):
        for kind in NEW:
            result = complete(kind)
            key = result["blocks"][0]["key"]
            result["blocks"] = [block for block in result["blocks"] if block["key"] != key]
            result["blocks"].append({"key": key, "label": "Empty", "items": [], "gap": "No evidence."})
            self.assertEqual(completion.missing(result), [], kind)

    def test_the_route_returns_a_completion(self):
        from bp.product import api
        for kind in NEW:
            with mock.patch("bp.product.completion.complete") as fake:
                fake.return_value = {"format": "bp-framework-completion/1", "template": kind, "blocks": []}
                status, payload = api.handle("POST", "/api/cases/frameworks/complete",
                                             {"template": kind, "instruction": NEW[kind][3],
                                              "unit": NEW[kind][2]})
            self.assertEqual(status, 200, kind)
            self.assertEqual(payload["template"], kind, kind)

    def test_the_prompt_names_the_framework_and_keeps_the_safety_rules(self):
        for kind in NEW:
            profile = dict(completion.LENGTHS["mid"])
            system = completion._system(completion.HEAD_SYSTEM, profile,
                                        completion._profile(kind))
            self.assertIn(framework_profiles.get(kind)["label"], system, kind)
            self.assertIn("Do not add facts, numbers, names, sources or citations", system, kind)

    def test_a_short_instruction_is_refused_before_any_research(self):
        for kind in NEW:
            with self.assertRaises(ValueError):
                complete(kind, instruction="Review it")

    def test_an_accounting_brief_is_refused_on_a_people_framework(self):
        for kind in NEW:
            with self.assertRaises(ValueError) as refused:
                complete(kind, instruction=NEW[kind][3] + " The trial balance and the journal entries are attached.")
            self.assertIn("Accounting", str(refused.exception), kind)


class ExampleTest(unittest.TestCase):
    """Every example runs, passes its own checks and never scores anybody."""

    def test_every_example_runs_and_passes_its_own_checks(self):
        for kind in NEW:
            request = copy.deepcopy(T.EXAMPLES[kind])
            out = T.run_template(kind, request["inputs"])
            checks = {name: ok for name, ok in out["results"]}
            self.assertTrue(all(checks.values()), "%s: %s" % (kind, checks))

    def test_an_empty_block_is_named_and_never_filled(self):
        for kind in NEW:
            request = copy.deepcopy(T.EXAMPLES[kind])
            key = list(request["inputs"]["blocks"])[0]
            request["inputs"]["blocks"][key] = []
            out = T.run_template(kind, request["inputs"])
            checks = {name: ok for name, ok in out["results"]}
            self.assertIn(key, out["analysis"]["audit"]["empty_blocks"], kind)
            self.assertTrue(checks["empty_blocks_reported_not_filled"], kind)

    def test_no_score_ranking_or_verdict_is_derived(self):
        for kind in NEW:
            out = T.run_template(kind, copy.deepcopy(T.EXAMPLES[kind])["inputs"])
            analysis = out["analysis"]
            for forbidden in ("score", "overall", "verdict", "ranking", "rank"):
                self.assertNotIn(forbidden, analysis, "%s: %s" % (kind, forbidden))
                self.assertNotIn(forbidden, analysis.get("counts", {}), kind)


class PageTest(unittest.TestCase):
    """The served page is part of the product, so it is checked as text."""

    def test_the_page_renders_the_tiles_and_the_catalogue_only_action(self):
        page = open(_PATH("web", "index.html"), encoding="utf-8").read()
        for needle in ("function subjectTiles", "Read and cite - no worksheet yet",
                       "Before you start", "The tiles"):
            self.assertIn(needle, page, needle)

    def test_the_page_shows_the_period_badge_on_a_calculator(self):
        page = open(_PATH("web", "index.html"), encoding="utf-8").read()
        self.assertIn('item.period', page)
