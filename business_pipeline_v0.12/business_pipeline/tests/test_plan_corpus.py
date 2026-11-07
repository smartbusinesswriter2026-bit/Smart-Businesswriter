"""The brief corpus: the resolver's contract, measured on real briefs.

Every row is a brief from this project's own working sessions, the reading a
person expects, and whether one question is owed.  A cue or priority change that
moves a case fails here by name, which is the point: resolver quality stops being
a story and becomes a diff.
"""

import json
import pathlib
import unittest

from bp.product import capabilities, chat

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "brief_corpus.json"


class BriefCorpusTest(unittest.TestCase):
    def setUp(self):
        self.rows = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_the_corpus_is_not_empty_and_names_its_cases(self):
        self.assertGreaterEqual(len(self.rows), 40)
        for row in self.rows:
            self.assertTrue(row["note"], "every corpus row needs a note")

    def test_every_brief_reads_the_way_a_person_expects(self):
        for row in self.rows:
            with self.subTest(note=row["note"]):
                state = chat.start(row["brief"], "management", row["requested_framework"])
                self.assertNotEqual(state["stage"], "not_supported", "the guard refused the brief")
                self.assertEqual(state.get("framework"), row["expected_framework"])
                if row["expected_framework"] is None:
                    # a brief that names no framework is left to the student; the system
                    # never fills the gap with a default, and a question is still owed.
                    self.assertIsNotNone(chat.current_question(state),
                                         "a brief that names no framework must leave a question owed")
                selected = sorted(item["key"] for item in state["selection"]["selected"])
                self.assertEqual(selected, sorted(row["expected_capabilities"]))
                question = (state["selection"].get("question") or {}).get("id")
                self.assertEqual(question, row["expected_question"])

    def test_the_corpus_covers_the_whole_catalogue_families(self):
        covered = set()
        for row in self.rows:
            covered.update(row["expected_capabilities"])
        # A corpus that only exercises one family would let the others drift.
        for family in ("breakeven", "npv", "dcf_valuation", "gini_coefficient", "pearson",
                       "cpm_schedule", "multi_criteria", "monte_carlo", "sroi",
                       "working_capital", "cohort_retention", "decision_tree"):
            self.assertIn(family, covered)

    def test_no_brief_selects_a_capability_that_does_not_apply_to_its_framework(self):
        for row in self.rows:
            state = chat.start(row["brief"], "management", row["requested_framework"])
            framework = state.get("framework")
            if framework is None:
                # nothing is committed to a framework yet, so there is no applies_to to
                # check against; the capability is provisional until the student answers.
                continue
            for item in state["selection"]["selected"]:
                applies = capabilities.ENTRIES[item["key"]]["applies_to"]
                self.assertIn(framework, applies, item["key"] + " on " + str(framework))


if __name__ == "__main__":
    unittest.main()
