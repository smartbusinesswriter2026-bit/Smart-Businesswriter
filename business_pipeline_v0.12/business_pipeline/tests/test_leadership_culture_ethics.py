"""Leadership, culture and ethics worksheets: shelf, profiles and conductor.

The contract this file pins:

* the three tiles exist on Management & strategy and every new worksheet and
  theory lens is placed in one of them (no leftover section);
* every new worksheet names a template that exists and a profile that passes
  ``framework_profiles.profile_for``;
* the conductor infers each framework from a realistic brief, and a draft from
  the student's own answers passes the export gate without retrieving external
  evidence;
* no paper invents a framework claim: a part with no answer is a named gap.

Standard library only.
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import templates  # noqa: E402
from bp.product import chat, framework_profiles, subjects  # noqa: E402

WORKSHEETS = {
    "LDR-01": "template_leadership_theory_comparison",
    "LDR-02": "template_situational_leadership",
    "LDR-03": "template_leader_effectiveness",
    "LDR-04": "template_leadership_development",
    "CUL-01": "template_culture_framework_comparison",
    "CUL-02": "template_cross_cultural_leadership",
    "CUL-03": "template_organisational_culture",
    "ETH-01": "template_ethical_dilemma",
    "ETH-02": "template_stakeholder_csr",
    "ETH-03": "template_ethical_decision_process",
}
TILES = {"leadership", "culture_organisation", "ethics_dilemmas"}


def draft_text(draft):
    """The body text of a draft, whose sections are [heading, lines, figure?]."""
    parts = []
    for section in (draft or {}).get("sections") or []:
        if isinstance(section, dict):
            parts.extend(section.get("lines") or [])
        elif isinstance(section, (list, tuple)) and len(section) > 1:
            lines = section[1]
            parts.extend(lines if isinstance(lines, (list, tuple)) else [lines])
    return " ".join(str(part) for part in parts)


class ShelfTest(unittest.TestCase):
    def setUp(self):
        self.page = subjects.detail("management")

    def test_three_tiles_exist(self):
        keys = {tile["key"] for tile in self.page["tiles"]}
        self.assertTrue(TILES.issubset(keys), "missing tile: %s" % (TILES - keys))

    def test_every_worksheet_is_placed_in_a_tile(self):
        placed = {row["catalogue_id"] for tile in self.page["tiles"]
                  for row in tile["worksheets"]}
        self.assertEqual(set(WORKSHEETS), placed & set(WORKSHEETS))

    def test_no_leftover_records(self):
        placed = {row["id"] for tile in self.page["tiles"] for row in tile["records"]}
        left = [row["id"] for row in self.page["records"] if row["id"] not in placed]
        self.assertEqual(left, [], "records not in a tile: %s" % left)

    def test_theory_lenses_are_present(self):
        names = {row["name"] for row in self.page["theories"]}
        for expected in ("Hofstede's cultural dimensions", "Transformational leadership (Burns, Bass)",
                         "Utilitarianism and consequentialism", "Deontology (Kant)"):
            self.assertIn(expected, names)


class ProfileTest(unittest.TestCase):
    def test_every_worksheet_profile_is_complete(self):
        for catalogue_id, template in WORKSHEETS.items():
            with self.subTest(catalogue_id=catalogue_id):
                profile = framework_profiles.profile_for(template)
                self.assertEqual(profile["template"], template)

    def test_every_template_builds_and_passes_its_checks(self):
        for template in WORKSHEETS.values():
            with self.subTest(template=template):
                row = templates.TEMPLATES[template]
                blocks = {key: [] for key in templates.CANVAS_BLOCKS[template]}
                first = list(blocks)[0]
                blocks[first] = [{"text": "A student-supplied claim.", "provenance": "user"}]
                art = row["build"]({"blocks": blocks})
                narrative, listing = row["render"](art)
                checks = row["tests"]({"blocks": blocks}, art, narrative, listing)
                self.assertTrue(all(ok for _name, ok in checks), template)


class ConductorTest(unittest.TestCase):
    BRIEFS = {
        "leadership_theory_comparison": (
            "Analyse transformational leadership in a hospital merger and compare it with "
            "transactional leadership."),
        "culture_framework_comparison": (
            "Compare Hofstede and GLOBE to explain leadership expectations in the merger."),
        "ethical_dilemma": (
            "Was the plant closure ethical? Apply utilitarian and Kantian reasoning to the "
            "workers and the community."),
    }

    def test_each_framework_is_inferred_from_its_brief(self):
        for framework, brief in self.BRIEFS.items():
            with self.subTest(framework=framework):
                state = chat.start(brief, "any")
                self.assertEqual(state.get("framework"), framework)
                self.assertNotEqual(state.get("stage"), "not_supported")

    def test_a_draft_from_the_student_answers_passes_the_gate(self):
        brief = self.BRIEFS["leadership_theory_comparison"]
        state = chat.start(brief, "any")
        answers = {
            "decision": "Whether the merged hospital should keep the chief executive.",
            "starting_theory": "Transformational leadership: idealized influence, inspirational "
                               "motivation, intellectual stimulation and individualized consideration.",
            "evidence": "Staff reported that the chief executive set a clear vision and coached "
                        "unit leads through the merger.",
            "comparison": "Transactional leadership relies on contingent reward and management by "
                          "exception; it does not explain voluntary effort.",
            "best_fit": "Transformational leadership fits because the change required discretionary "
                        "effort beyond contract.",
            "limits": "The evidence is staff perception, not outcome data.",
            "style": "apa",
        }
        guard = 0
        while state.get("stage") == "clarify" and guard < 30:
            question = state["questions"][state["question_index"]]
            state = chat.answer(state, question["id"], answers.get(question["id"], ""))
            guard += 1
        state = chat.confirm_plan(state)
        state = chat.research(state)
        state = chat.draft(
            state,
            implications="The board should keep the chief executive through the integration "
                         "year and review against outcome measures.")
        self.assertEqual(state.get("stage"), "draft")
        self.assertEqual((state.get("draft") or {}).get("missing"), [])
        self.assertIn("Transformational leadership", draft_text(state["draft"]))

    def test_no_answer_becomes_a_named_gap_not_invented_text(self):
        brief = self.BRIEFS["ethical_dilemma"]
        state = chat.start(brief, "any")
        # Answer only the decision, leaving every ethical-theory part empty.
        guard = 0
        while state.get("stage") == "clarify" and guard < 30:
            question = state["questions"][state["question_index"]]
            value = {"decision": "Whether the plant should close.", "style": "apa"}.get(
                question["id"], "")
            state = chat.answer(state, question["id"], value)
            guard += 1
        state = chat.confirm_plan(state)
        state = chat.research(state)
        state = chat.draft(state, implications="The board should state its reasoning and mitigate harm.")
        self.assertIn("No evidence or student input was recorded for", draft_text(state["draft"]))


if __name__ == "__main__":
    unittest.main()
