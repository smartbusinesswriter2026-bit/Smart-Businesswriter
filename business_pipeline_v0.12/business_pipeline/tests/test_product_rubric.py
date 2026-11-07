"""Acceptance suite for the rubric reader (B-187, `qa/manual/rubric.md` E-rub-001…018).

The rubric is the student's own statement of what their assignment is marked
against, so the reader is judged on one thing above all: it may only carry what
the document states.  Every test here is offline and uses a float-free, integer
comparison; nothing calls the network, the frozen core or a model.
"""

import json
import os
import pathlib
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, "src")

from bp.product import completion, intake, paper, rubric  # noqa: E402

TABLE = """BA 101 - Group Business Report (30% of the course grade)

| Criterion | Weight | Descriptor |
|---|---|---|
| Situation analysis | 30% | Applies two frameworks to the case and shows the working |
| Financial analysis | 40% | Must include: a break-even calculation; three ratios computed from the case |
| Recommendations | 30% | Recommended actions follow from the analysis |

Required sections: Introduction, Situation analysis, Financial analysis, Recommendations, Conclusion

Word count: 2,500 words (+/- 10%)
Referencing: APA 7th edition
"""

LIST = """Assessment criteria
1. Problem definition - 20% - states the decision to be made
2. Evidence - 40% - should include three sources from 2020 or later
3. Analysis - 30% - applies the value chain
4. Writing - 10% - clear structure
"""

NO_WEIGHTS = """The report is marked on:
- Clarity of the problem statement
- Use of course frameworks
- Quality of the recommendation
"""

NOT_A_RUBRIC = """Please read the attached case and write a short report about the
company's competitive position in its market, with no criteria stated.
"""

BARE_NUMBERS = """| Assessment item | Marks |
| --- | --- |
| Research | 25 |
| Analysis | 45 |
| Presentation | 30 |
"""

PAGES = """Style notes for the assignment.
The report must not exceed 8 pages and should use Harvard referencing.
| Criterion | % |
| --- | --- |
| Structure | 50 |
| Content | 50 |
"""


class RubricReaderTest(unittest.TestCase):
    """E-rub-001…018: what the reader may and may not conclude."""

    # -- what a rubric states is read ---------------------------------------

    def test_e_rub_001__a_table_rubric_carries_its_stated_weights(self):
        parsed = rubric.parse(TABLE)
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["layout"], "table")
        self.assertEqual([row["name"] for row in parsed["criteria"]],
                         ["Situation analysis", "Financial analysis", "Recommendations"])
        self.assertEqual([row["weight"] for row in parsed["criteria"]], [30.0, 40.0, 30.0])
        self.assertEqual(parsed["total_weight"], 100.0)
        self.assertFalse(parsed["confirm_required"],
                         "a rubric whose weights total 100 needs no correction from the student")

    def test_e_rub_002__a_numbered_list_rubric_carries_its_stated_weights(self):
        parsed = rubric.parse(LIST)
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["layout"], "list")
        self.assertEqual([row["weight"] for row in parsed["criteria"]], [20.0, 40.0, 30.0, 10.0])
        self.assertEqual(parsed["total_weight"], 100.0)
        self.assertEqual(parsed["criteria"][0]["descriptor"], "states the decision to be made")

    def test_e_rub_016__a_lead_in_line_is_not_a_criterion(self):
        parsed = rubric.parse(NO_WEIGHTS)
        names = [row["name"] for row in parsed["criteria"]]
        self.assertEqual(names, ["Clarity of the problem statement", "Use of course frameworks",
                                 "Quality of the recommendation"])
        for name in names:
            self.assertNotIn("marked on", name)

    def test_e_rub_017__a_bare_number_in_a_marks_column_is_the_weight(self):
        parsed = rubric.parse(BARE_NUMBERS)
        self.assertEqual([row["weight"] for row in parsed["criteria"]], [25.0, 45.0, 30.0])
        self.assertEqual(parsed["total_weight"], 100.0)
        self.assertFalse(parsed["problems"])

    def test_e_rub_007__a_stated_word_budget_is_read_with_its_tolerance(self):
        parsed = rubric.parse(TABLE)
        self.assertEqual(parsed["word_budget"]["words"], 2500)
        self.assertEqual(parsed["word_budget"]["tolerance"], 0.1)
        self.assertIn("2,500 words", parsed["word_budget"]["text"])

    def test_e_rub_011__sections_are_read_from_an_explicit_structure_label(self):
        parsed = rubric.parse(TABLE)
        self.assertEqual(parsed["sections"], ["Introduction", "Situation analysis",
                                              "Financial analysis", "Recommendations",
                                              "Conclusion"])

    def test_e_rub_009__required_elements_are_carried_verbatim(self):
        parsed = rubric.parse(TABLE)
        financial = parsed["criteria"][1]
        self.assertEqual(financial["required_elements"],
                         ["a break-even calculation", "three ratios computed from the case"])
        self.assertEqual(parsed["criteria"][0]["required_elements"], [],
                         "a criterion with no requirement clause gets no invented element")

    def test_e_rub_010__a_descriptor_is_never_rewritten(self):
        parsed = rubric.parse(TABLE)
        self.assertEqual(parsed["criteria"][0]["descriptor"],
                         "Applies two frameworks to the case and shows the working")
        self.assertEqual(parsed["criteria"][1]["descriptor"],
                         "Must include: a break-even calculation; three ratios computed from the case")

    def test_e_rub_012__one_named_citation_style_is_taken(self):
        self.assertEqual(rubric.parse(TABLE)["citation_style"], "apa")
        self.assertEqual(rubric.parse(PAGES)["citation_style"], "harvard")


    # -- what a rubric does not state is never invented -----------------------

    def test_e_rub_003__a_weight_is_never_invented(self):
        parsed = rubric.parse(NO_WEIGHTS)
        self.assertTrue(parsed["ok"], "three criteria were read, so the rubric is usable")
        for row in parsed["criteria"]:
            self.assertIsNone(row["weight"], "no weight may be assumed")
            self.assertIsNone(row["weight_text"])
        self.assertIsNone(parsed["total_weight"])
        self.assertTrue(parsed["problems"], "the missing weights are named, never silent")
        self.assertIn("No weight has been assumed", parsed["problems"][0])
        self.assertTrue(parsed["confirm_required"])

    def test_e_rub_004__weights_that_miss_a_hundred_are_reported_not_rescaled(self):
        parsed = rubric.parse("""| Criterion | Weight |
| --- | --- |
| Research | 30% |
| Analysis | 30% |
| Writing | 30% |
""")
        self.assertEqual([row["weight"] for row in parsed["criteria"]], [30.0, 30.0, 30.0],
                         "the student's own weights are carried as written")
        self.assertEqual(parsed["total_weight"], 90.0)
        self.assertTrue(any("total 90" in problem for problem in parsed["problems"]))
        self.assertTrue(parsed["confirm_required"])

    def test_e_rub_012b__two_named_citation_styles_are_refused_not_chosen(self):
        parsed = rubric.parse("""| Criterion | Weight |
| --- | --- |
| Structure | 50% |
| Content | 50% |

Cite every source in APA or Harvard style.
""")
        self.assertIsNone(parsed["citation_style"], "a style is never chosen for the student")
        self.assertTrue(any("more than one citation style" in problem
                            for problem in parsed["problems"]))
        self.assertTrue(parsed["confirm_required"])

    def test_e_rub_008__a_page_limit_is_never_converted_into_a_word_budget(self):
        parsed = rubric.parse(PAGES)
        self.assertIsNone(parsed["word_budget"],
                          "8 pages is not a number of words; converting it would invent a budget")

    def test_e_rub_005__an_unreadable_rubric_asks_the_student_instead_of_guessing(self):
        parsed = rubric.parse(NOT_A_RUBRIC)
        self.assertFalse(parsed["ok"])
        self.assertEqual(parsed["criteria"], [])
        self.assertEqual(parsed["layout"], "none")
        self.assertTrue(parsed["confirm_required"])
        self.assertEqual(parsed["text"], NOT_A_RUBRIC,
                         "the raw text is preserved so the student can correct it")
        self.assertIn("No assessment criterion could be read", parsed["problems"][0])

    def test_e_rub_006__an_empty_rubric_is_refused_by_name(self):
        for empty in ("", "   ", "too short"):
            parsed = rubric.parse(empty)
            self.assertFalse(parsed["ok"])
            self.assertIn("empty or too short", parsed["problems"][0])
            self.assertTrue(parsed["confirm_required"])

    def test_e_rub_018__an_oversized_rubric_is_refused_by_name_not_truncated(self):
        original = rubric.MAX_CHARS
        rubric.MAX_CHARS = 400
        try:
            payload = "| Criterion | Weight |\n| --- | --- |\n| Research | 100% |\n" * 20
            parsed = rubric.parse(payload)
        finally:
            rubric.MAX_CHARS = original
        self.assertFalse(parsed["ok"])
        self.assertIn("character limit", parsed["problems"][0])
        self.assertEqual(parsed["text"], payload, "the text is refused, never cut")

    # -- honesty: the reader concludes nothing a human must judge -------------

    def test_e_rub_013__the_reader_scores_nothing(self):
        parsed = rubric.parse(TABLE)
        self.assertTrue(parsed["scores_nothing"])
        banned = ("score", "mark", "grade", "awarded", "percent_met", "attained")
        for key in parsed:
            if key == "scores_nothing":
                continue  # the declared flag itself: it says the reader awards nothing
            for word in banned:
                self.assertNotIn(word, key.lower(),
                                 "a rubric reader must not report a mark or a grade")
        for key in rubric.summary(parsed):
            for word in banned:
                self.assertNotIn(word, key.lower())

    def test_e_rub_014__the_parse_is_deterministic_and_json_safe(self):
        first, second = rubric.parse(TABLE), rubric.parse(TABLE)
        self.assertEqual(first, second)
        self.assertEqual(rubric.as_json(first), rubric.as_json(second))
        revived = json.loads(rubric.as_json(first))
        self.assertEqual(revived["criteria"], first["criteria"],
                         "a stored rubric survives a JSON round trip unchanged")

    def test_e_rub_015__the_reader_reaches_neither_the_core_nor_the_network(self):
        source = pathlib.Path(rubric.__file__).read_text(encoding="utf-8")
        for banned in ("import methods", "from bp.methods", "from . import methods",
                       "urllib", "socket", "requests", "http.client", "openai", "anthropic"):
            self.assertNotIn(banned, source,
                             "the rubric reader must stay offline and outside the frozen core")


BRIEF = ("A grocery retailer is reviewing growth options before deciding whether to open a new "
         "store format or launch a private-label range.")
INDUSTRY = "grocery retail"

TWO_CRITERIA = """| Criterion | Weight | Descriptor |
| --- | --- | --- |
| Market penetration | 50% | existing markets with existing products |
| Recommendations | 50% | actions follow from the findings |
"""

ELEMENT_MISSING = """| Criterion | Weight | Required |
| --- | --- | --- |
| Market penetration | 100% | a five-year forecast |
"""

WITH_TOLERANCE = """| Criterion | Weight |
| --- | --- |
| Market penetration | 50% |
| Discussion | 50% |

Word count: 2,500 words (+/- 10%)
"""

NO_TOLERANCE = """| Criterion | Weight |
| --- | --- |
| Market penetration | 50% |
| Discussion | 50% |

Word count: 2,500 words
"""


def _academic(query, databases=None, limit=10, year_from=None):
    """A source whose title follows the query, so the cell gate can judge it."""
    return {"results": [{
        "title": "Grocery retail " + query[:70],
        "abstract": "Evidence on the growth option named in the query. A second sentence.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of Marketing", "doi": "10.1/" + str(abs(hash(query)) % 1000000),
        "url": "https://doi.org/10.1/x", "database": "OpenAlex"}], "errors": [], "skipped": []}


def _web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def _complete(rubric_text):
    with mock.patch("bp.product.sources.search_academic", side_effect=_academic), \
            mock.patch("bp.product.sources.search_web", side_effect=_web):
        return completion.complete("template_ansoff", BRIEF, industry=INDUSTRY,
                                   rubric=rubric_text)


def _draft(rubric_text):
    return completion.draft(_complete(rubric_text))


class RubricCoverageTest(unittest.TestCase):
    """E-rub-019…026: a rubric is measured against the paper, never scored."""

    def test_e_rub_019__a_heading_that_names_the_criterion_addresses_it(self):
        report = _draft(TWO_CRITERIA)
        rows = {row["name"]: row for row in report["rubric"]["criteria"]}
        self.assertEqual(rows["Market penetration"]["status"], "addressed")
        self.assertIn("market penetration",
                      [heading.lower() for heading in rows["Market penetration"]["where"]],
                      "the heading that covers the criterion is named")

    def test_e_rub_020__a_criterion_the_paper_never_mentions_is_a_named_gap(self):
        report = _draft(TWO_CRITERIA)
        rows = {row["name"]: row for row in report["rubric"]["criteria"]}
        self.assertEqual(rows["Recommendations"]["status"], "gap")
        self.assertEqual(report["rubric"]["gaps"], ["Recommendations"])
        self.assertEqual(report["rubric"]["blocking"], ["Recommendations"])
        self.assertEqual(report["rubric_gate"], "blocked")

    def test_e_rub_021__a_stated_element_that_is_absent_downgrades_to_partial(self):
        report = _draft(ELEMENT_MISSING)
        row = report["rubric"]["criteria"][0]
        self.assertEqual(row["status"], "partially")
        self.assertEqual([item["text"] for item in row["elements"]], ["a five-year forecast"])
        self.assertFalse(row["elements"][0]["found"])
        self.assertIn("a five-year forecast", row["note"])

    def test_e_rub_022__the_appendix_reports_coverage_and_cannot_satisfy_it(self):
        report = _draft(TWO_CRITERIA)
        headings = [section["heading"] for section in report["sections"]]
        self.assertIn("Rubric coverage", headings)
        self.assertLess(headings.index("Rubric coverage"), headings.index("References"),
                        "the appendix sits before the reference list")
        self.assertIn("Recommendations", " ".join(report["sections"][headings.index("Rubric coverage")]["lines"]))
        self.assertEqual(report["rubric"]["criteria"][1]["status"], "gap",
                         "the appendix naming a criterion must not make it addressed")


    def _paper(self):
        return [paper.section("Introduction", 1, ["A sentence about the case."]),
                paper.section("Conclusion", 1, ["A sentence that concludes the paper."]),
                paper.section("References", 1, ["No sources were used."])]

    def test_e_rub_023__the_word_budget_is_reported_and_never_guessed(self):
        report = _draft(WITH_TOLERANCE)
        target = report["word_target"]
        self.assertEqual(target["words"], 2500)
        self.assertEqual(target["range"], [2250, 2750])
        self.assertEqual(target["actual"], report["words"],
                         "the count reported is the paper's own count")
        self.assertFalse(target["met"], "a short draft is reported as short, never as met")
        without = _draft(NO_TOLERANCE)["word_target"]
        self.assertFalse(without["met"], "a bare count is read as a target with the product's allowance")
        self.assertEqual(without["range"], [2250, 2750])
        self.assertIn("product's 10% allowance", without["note"])

    def test_e_rub_024__a_weighted_criterion_gap_blocks_export(self):
        coverage = _draft(TWO_CRITERIA)["rubric"]
        state = {"rubric": coverage}
        required = paper.missing(state, "A position.")
        self.assertTrue(any("Recommendations" in item for item in required), required)
        report = paper.check(self._paper(), "ansoff", "A position.", {}, state=state)
        self.assertFalse(report["pass"], "an unaddressed weighted criterion blocks export")

    def test_e_rub_025__turning_the_gate_off_demotes_the_rows_to_warnings(self):
        coverage = _draft(TWO_CRITERIA)["rubric"]
        state = {"rubric": coverage, "rubric_gate": False}
        self.assertFalse(paper.rubric_gate_on(state))
        self.assertEqual(paper.missing(state, "A position."), [],
                         "with the gate off nothing is required before export")
        report = paper.check(self._paper(), "ansoff", "A position.", {}, state=state)
        self.assertTrue(report["pass"])
        self.assertTrue(any(issue["type"] == "rubric_criterion_gap" and issue["severity"] == "medium"
                            for issue in report["issues"]),
                        "the gap is still reported, as a warning")

    def test_e_rub_026__an_unreadable_rubric_is_refused_before_any_research(self):
        with self.assertRaises(ValueError) as refused:
            _complete("Please read the attached case and write a short report about the company.")
        self.assertIn("No assessment criterion", str(refused.exception))

    def test_e_rub_027__coverage_is_deterministic_and_scores_nothing(self):
        first, second = _draft(TWO_CRITERIA)["rubric"], _draft(TWO_CRITERIA)["rubric"]
        self.assertEqual(first, second)
        self.assertFalse(first["scored"])
        for key in first:
            if key == "scored":
                continue
            for word in ("mark", "grade", "score", "percentage"):
                self.assertNotIn(word, key.lower())

    def test_e_rub_028__a_paper_without_a_rubric_is_unchanged(self):
        with mock.patch("bp.product.sources.search_academic", side_effect=_academic), \
                mock.patch("bp.product.sources.search_web", side_effect=_web):
            plain = completion.complete("template_ansoff", BRIEF, industry=INDUSTRY)
        self.assertNotIn("rubric", plain)
        report = completion.draft(plain)
        self.assertNotIn("Rubric coverage", [section["heading"] for section in report["sections"]])
        self.assertNotIn("rubric", report)


TEXT_RUBRIC = b"""| Criterion | Weight |
| --- | --- |
| Market penetration | 50% |
| Recommendations | 50% |
"""


class RubricUploadTest(unittest.TestCase):
    """E-rub-029…034: the student hands the rubric over, and nothing is started for them."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-rubric-test-")
        self.previous = os.environ.get("BP_INTAKE_DIR")
        os.environ["BP_INTAKE_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_INTAKE_DIR", None)
        else:
            os.environ["BP_INTAKE_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_e_rub_029__a_rubric_file_is_read_and_recorded_as_the_marking_guide(self):
        record = intake.save("rubric.txt", TEXT_RUBRIC)
        used = intake.use_as_rubric(record["id"])
        self.assertEqual(used["role"], "rubric")
        self.assertTrue(used["unverified"], "extracted text is never presented as verified")
        self.assertEqual(len(used["rubric"]["criteria"]), 2)
        self.assertEqual(used["rubric_summary"]["criteria"], 2)
        self.assertEqual(intake.load(record["id"])["role"], "rubric",
                         "the role is recorded on the file itself")
        self.assertIn("marking guide", intake.load(record["id"])["note"])

    def test_e_rub_030__a_file_with_no_reader_is_refused_and_keeps_its_role(self):
        record = intake.save("sales.csv", b"region,sales\nnorth,10\n")
        with self.assertRaises(intake.IntakeError) as refused:
            intake.use_as_rubric(record["id"])
        self.assertIn("attach a PDF", str(refused.exception))
        self.assertIsNone(intake.load(record["id"])["role"],
                          "a refused file is not labelled as the marking guide")

    def test_e_rub_031__text_that_is_not_a_rubric_is_refused_with_the_readers_reason(self):
        record = intake.save("notes.txt", b"Please read the case and write a short report about it.")
        with self.assertRaises(intake.IntakeError) as refused:
            intake.use_as_rubric(record["id"])
        self.assertIn("No assessment criterion", str(refused.exception))
        self.assertIsNone(intake.load(record["id"])["role"])

    def test_e_rub_034__an_unknown_role_is_still_refused(self):
        with self.assertRaises(ValueError):
            intake.save("memo.txt", b"hello", role="memo")
        self.assertIn("rubric", intake.ROLES)

    def test_e_rub_032__the_paper_blocks_while_a_weighted_criterion_is_unaddressed(self):
        result = _complete(TWO_CRITERIA)
        report = completion.draft(result)
        blockers = completion.rubric_blockers(report)
        self.assertTrue(any("Recommendations" in item for item in blockers), blockers)
        result["rubric_gate"] = False
        relaxed = completion.draft(result)
        self.assertEqual(relaxed["rubric_gate"], "clear")
        self.assertEqual(completion.rubric_blockers(relaxed), [],
                         "the student's switch is honoured")

    def test_e_rub_033__the_page_offers_the_action_and_sends_the_rubric_with_the_run(self):
        page = (pathlib.Path(__file__).resolve().parent.parent / "web" / "index.html").read_text(
            encoding="utf-8")
        self.assertIn('data-rubric="', page)
        self.assertIn("Use as the rubric", page)
        self.assertIn('useAsRubric', page)
        self.assertIn('/rubric"', page)
        self.assertIn("body.rubric = state.rubric", page)
        self.assertIn("Read as the marking guide", page)


if __name__ == "__main__":
    unittest.main()
