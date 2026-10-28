"""Report length: a word target with a floor, and the sections a full report adds.

The rule the test protects: a length is a request the system answers honestly.  It
is read from the brief ("write about 2500 words"), refused below the floor instead
of padded, and a full report adds only the sections the record supports - method,
evidence base, the reading of a dimension, the method's assumptions, the
recommendation and the appendix.
"""

import unittest

from bp import methods
from bp.product import chat

BRIEF = ("A retailer is considering opening a device store in Tehran. Analyse the Iranian market "
         "environment with PESTEL, and test whether the store pays for itself at the declared fixed "
         "cost of 2000000, price of 40000 and variable cost of 28000.")

SOURCES = [
    ("Sanctions and the Iranian economy", 2025, "Middle East Critique", "CrossRef"),
    ("Household conditions in Iran", 2026, "World Bank", "World Bank"),
]


def _run(method_id, values):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, values)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(values)


def setUpModule():
    import bp.product.api as product_api
    product_api.attach_compute(lambda values: methods.breakeven(values))
    product_api.attach_methods(_run, methods.describe)


def _seed(state):
    """Two frozen-style sources per dimension, so every dimension has evidence."""
    sources, evidence = [], []
    for dimension in state["plan"]["dimensions"]:
        for title, year, venue, database in SOURCES:
            source_id = "S%d" % (len(sources) + 1)
            sources.append({"id": source_id, "title": title + " (" + dimension["label"] + ")",
                            "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"],
                            "year": year, "venue": venue, "database": database,
                            "abstract": "A sentence about " + dimension["label"].lower() + "."})
            evidence.append({"id": "E%d" % (len(evidence) + 1), "dimension": dimension["key"],
                             "claim": "A sentence about " + dimension["label"].lower() + ".",
                             "quote": "A sentence about " + dimension["label"].lower() + ".",
                             "source_id": source_id, "status": "accepted"})
    state.update({"sources": sources, "evidence": evidence, "gaps": [], "notes": [], "stage": "evidence"})
    return state


def build(target=None):
    """Run a case to a draft; `target` is written into the brief, as a student would."""
    brief = BRIEF if target is None else BRIEF + " Write about " + str(target) + " words."
    state = chat.start(brief, "management", "pestel")
    answers = {"decision": "Should the retailer open a device store in Tehran?",
               "geography": "Middle East", "period": "5", "style": "apa"}
    while chat.current_question(state):
        question = chat.current_question(state)
        state = chat.answer(state, question["id"], answers.get(question["id"], ""))
    state = chat.confirm_plan(state)
    state = chat.run_capability(state, "breakeven",
                                {"fixed": "2000000", "price": "40000", "variable": "28000"})
    state = _seed(state)
    return chat.draft(state, implications="The declared volume is below the break-even quantity, so the price or "
                                          "the variable cost has to change before entry is viable.")


class LengthTest(unittest.TestCase):
    def test_a_brief_without_a_count_is_the_short_version(self):
        state = chat.start(BRIEF, "management", "pestel")
        self.assertEqual(state["answers"].get("length"), None)
        self.assertEqual(chat.target_words(state), 0)

    def test_a_brief_that_names_a_count_asks_for_the_full_report(self):
        state = chat.start(BRIEF + " Write about 2500 words.", "management", "pestel")
        self.assertEqual(state["answers"]["length"], "2500")
        self.assertEqual(chat.target_words(state), 2500)
        # The questions a student answers are unchanged by the length.
        self.assertEqual([question["id"] for question in state["questions"]],
                         ["decision", "geography", "period", "style"])

    def test_a_count_below_the_floor_is_refused_with_the_reason(self):
        with self.assertRaises(chat.ChatError) as raised:
            chat.start(BRIEF + " Write 800 words.", "management", "pestel")
        self.assertIn(str(chat.MIN_WORDS), str(raised.exception))
        self.assertIn("cannot be written properly", str(raised.exception))

    def test_a_count_above_the_ceiling_is_refused(self):
        with self.assertRaises(chat.ChatError):
            chat.start(BRIEF + " Write " + str(chat.MAX_WORDS + 1) + " words.", "management", "pestel")

    def test_the_home_composer_box_sets_the_length(self):
        state = chat.start(BRIEF, "management", "pestel", words="2500")
        self.assertEqual(state["answers"]["length"], "2500")
        # The box is part of start, so the plan carries it before any question.
        self.assertEqual(chat.target_words(state), 2500)

    def test_the_home_box_floor_is_enforced(self):
        with self.assertRaises(chat.ChatError) as raised:
            chat.start(BRIEF, "management", "pestel", words="900")
        self.assertIn(str(chat.MIN_WORDS), str(raised.exception))

    def test_the_count_is_read_with_a_comma(self):
        state = chat.start(BRIEF + " Write 2,500 words.", "management", "pestel")
        self.assertEqual(state["answers"]["length"], "2500")
        self.assertEqual(chat.check_word_target("2,500"), 2500)
        self.assertEqual(chat.check_word_target("2500 words"), 2500)
        self.assertEqual(chat.check_word_target(""), 0)


class FullReportTest(unittest.TestCase):
    def test_the_short_version_carries_no_full_report_sections(self):
        state = build(None)
        headings = [item["heading"] for item in state["draft"]["outline"]]
        self.assertNotIn("Scope and Method", headings)
        self.assertNotIn("Evidence Base", headings)
        self.assertNotIn("Recommendation", headings)
        self.assertNotIn("Appendix: How the Computations Were Checked", headings)
        self.assertEqual(state["draft"]["target_words"], chat.SHORT_WORDS)
        self.assertTrue(state["draft"]["met_target"])

    def test_a_full_report_adds_its_sections_in_order(self):
        state = build(2000)
        headings = [item["heading"] for item in state["draft"]["outline"]]
        for heading in ("Scope and Method", "Evidence Base", "Recommendation",
                        "Appendix: How the Computations Were Checked"):
            self.assertIn(heading, headings)
        self.assertLess(headings.index("Scope and Method"), headings.index("PESTEL"))
        self.assertLess(headings.index("Evidence Base"), headings.index("Discussion"))
        self.assertLess(headings.index("Recommendation"), headings.index("Conclusion"))
        self.assertEqual(state["draft"]["target_words"], 2000)

    def test_the_full_report_meets_its_target_and_passes_the_gate(self):
        state = build(chat.MIN_WORDS)
        self.assertTrue(state["draft"]["met_target"], state["draft"]["words"])
        self.assertGreaterEqual(state["draft"]["words"], chat.MIN_WORDS)
        self.assertEqual(state["draft"]["missing"], [])
        data = chat.docx_bytes(state)
        self.assertTrue(data.startswith(b"PK"))

    def test_a_full_report_states_its_own_length_and_its_limits(self):
        state = build(chat.MIN_WORDS)
        text = " ".join(line for _heading, lines in state["draft"]["sections"] for line in lines)
        self.assertIn("planned at 1500 words", text)
        self.assertIn("condition of entry", text)
        self.assertIn("What Would Change the Answer", [item["heading"] for item in state["draft"]["outline"]])

    def test_the_full_report_passes_the_claim_gate(self):
        state = build(2000)
        self.assertEqual(state.get("claim_problems"), [])
        self.assertEqual(state.get("recompute_problems"), [])


class PlanLengthControlTest(unittest.TestCase):
    """The word-count box on the plan card sets the same length the draft reads."""

    def _planned(self):
        state = chat.start(BRIEF, "management", "pestel")
        answers = {"decision": "Should the retailer open a device store in Tehran?",
                   "geography": "Middle East", "period": "5", "style": "apa"}
        while chat.current_question(state):
            question = chat.current_question(state)
            state = chat.answer(state, question["id"], answers.get(question["id"], ""))
        return state

    def test_the_plan_carries_the_length_it_will_write_to(self):
        state = self._planned()
        self.assertEqual(state["plan"]["target_words"], chat.SHORT_WORDS)
        self.assertFalse(state["plan"]["full_report"])
        self.assertEqual(state["plan"]["min_words"], chat.MIN_WORDS)

    def test_setting_a_length_updates_the_plan_and_the_draft(self):
        state = chat.set_length(self._planned(), "2500")
        self.assertEqual(state["answers"]["length"], "2500")
        self.assertEqual(state["plan"]["target_words"], 2500)
        self.assertTrue(state["plan"]["full_report"])
        state = chat.confirm_plan(state)
        state = chat.run_capability(state, "breakeven",
                                    {"fixed": "2000000", "price": "40000", "variable": "28000"})
        state = _seed(state)
        state = chat.draft(state, implications="The declared volume is below break-even.")
        self.assertIn("Scope and Method", [item["heading"] for item in state["draft"]["outline"]])
        # This fixture's evidence is thin, so the draft reports the shortfall rather
        # than padding to the number, and the shortfall does not block the export.
        self.assertFalse(state["draft"]["met_target"])
        self.assertLess(state["draft"]["words"], 2500)
        self.assertEqual(state["draft"]["missing"], [])

    def test_a_length_below_the_floor_is_refused_at_the_plan(self):
        state = self._planned()
        with self.assertRaises(chat.ChatError) as raised:
            chat.set_length(state, "900")
        self.assertIn(str(chat.MIN_WORDS), str(raised.exception))
        self.assertEqual(state["answers"].get("length"), None)

    def test_clearing_the_box_returns_to_the_short_version(self):
        state = chat.set_length(self._planned(), "2500")
        state = chat.set_length(state, "")
        self.assertEqual(state["answers"]["length"], "")
        self.assertEqual(state["plan"]["target_words"], chat.SHORT_WORDS)
        self.assertFalse(state["plan"]["full_report"])

    def test_the_length_is_only_set_while_the_plan_is_open(self):
        with self.assertRaises(chat.ChatError):
            chat.set_length(chat.start(BRIEF, "management", "pestel"), "2500")


class LengthRouteTest(unittest.TestCase):
    def setUp(self):
        import os
        import tempfile
        from bp.product import api
        self.api = api
        self.root = tempfile.mkdtemp(prefix="bp-length-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        import os
        import shutil
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _case(self):
        status, state = self.api.handle("POST", "/api/cases/chat", {"brief": BRIEF, "framework": "pestel"})
        self.assertEqual(status, 201)
        answers = {"decision": "Should the retailer open a device store in Tehran?",
                   "geography": "Middle East", "period": "5", "style": "apa"}
        while chat.current_question(state):
            question = chat.current_question(state)
            status, state = self.api.handle("POST", "/api/cases/chat/" + state["id"] + "/answer",
                                            {"question_id": question["id"],
                                             "value": answers.get(question["id"], "")})
            self.assertEqual(status, 200)
        return state

    def test_the_start_route_takes_the_length_from_the_home_box(self):
        status, state = self.api.handle("POST", "/api/cases/chat",
                                        {"brief": BRIEF, "framework": "pestel", "words": "2500"})
        self.assertEqual(status, 201)
        self.assertEqual(state["answers"]["length"], "2500")
        status, payload = self.api.handle("POST", "/api/cases/chat",
                                          {"brief": BRIEF, "framework": "pestel", "words": "900"})
        self.assertEqual(status, 422)
        self.assertIn(str(chat.MIN_WORDS), payload["error"])

    def test_the_route_sets_a_length_and_refuses_below_the_floor(self):
        state = self._case()
        status, state = self.api.handle("POST", "/api/cases/chat/" + state["id"] + "/length",
                                        {"words": "2500"})
        self.assertEqual(status, 200)
        self.assertEqual(state["plan"]["target_words"], 2500)
        status, payload = self.api.handle("POST", "/api/cases/chat/" + state["id"] + "/length",
                                          {"words": "900"})
        self.assertEqual(status, 422)
        self.assertIn(str(chat.MIN_WORDS), payload["error"])


if __name__ == "__main__":
    unittest.main()
