"""Acceptance suite for the rubric reader (B-187, `qa/manual/rubric.md` E-rub-001…018).

The rubric is the student's own statement of what their assignment is marked
against, so the reader is judged on one thing above all: it may only carry what
the document states.  Every test here is offline and uses a float-free, integer
comparison; nothing calls the network, the frozen core or a model.
"""

import json
import pathlib
import sys
import unittest

sys.path.insert(0, "src")

from bp.product import rubric

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


if __name__ == "__main__":
    unittest.main()
