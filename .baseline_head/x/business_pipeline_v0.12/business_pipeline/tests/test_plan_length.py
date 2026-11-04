"""Report length: three options with ranges, and the sections each one adds.

The rule the test protects: a length is a request the system answers honestly.
Short is enough for many cases; mid adds the evidence base and discussion; long
adds the reading of each dimension and the appendix. The draft never pads to hit
a target, and the bands are the same in the brief, the Home box, the plan card
and the draft.
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


def build(length=None):
    """Run a case to a draft; `length` is a band name or a count, as a student gives it."""
    brief = BRIEF if length is None else BRIEF + " Write a " + str(length) + " report."
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


class LengthOptionTest(unittest.TestCase):
    def test_the_three_options_and_their_ranges(self):
        bands = {band[0]: (band[2], band[3]) for band in chat.LENGTH_BANDS}
        self.assertEqual(bands["short"], (600, 1200))
        self.assertEqual(bands["mid"], (1200, 2500))
        self.assertEqual(bands["long"], (2500, 5000))
        self.assertEqual([band[0] for band in chat.LENGTH_BANDS], ["short", "mid", "long"])

    def test_a_count_falls_into_the_right_band(self):
        for words, band in ((600, "short"), (900, "short"), (1199, "short"),
                            (1200, "mid"), (2000, "mid"), (2499, "mid"),
                            (2500, "long"), (4000, "long")):
            self.assertEqual(chat.length_band(words), band, words)

    def test_a_band_name_resolves_to_its_target(self):
        self.assertEqual(chat.check_word_target("short"), chat.SHORT_WORDS)
        self.assertEqual(chat.check_word_target("mid"), chat.MID_WORDS)
        self.assertEqual(chat.check_word_target("long"), chat.LONG_WORDS)

    def test_a_brief_without_a_length_is_short(self):
        state = chat.start(BRIEF, "management", "pestel")
        self.assertEqual(state["answers"].get("length"), None)
        self.assertEqual(chat.target_words(state), 0)

    def test_a_brief_that_names_an_option_sets_that_length(self):
        state = chat.start(BRIEF + " Write a mid-length report.", "management", "pestel")
        self.assertEqual(state["answers"]["length"], str(chat.MID_WORDS))

    def test_a_brief_that_gives_a_count_sets_that_count(self):
        state = chat.start(BRIEF + " Write about 2500 words.", "management", "pestel")
        self.assertEqual(state["answers"]["length"], "2500")
        self.assertEqual(chat.target_words(state), 2500)

    def test_a_count_below_the_short_floor_is_refused(self):
        with self.assertRaises(chat.ChatError) as raised:
            chat.start(BRIEF + " Write 300 words.", "management", "pestel")
        self.assertIn(str(chat.MIN_WORDS), str(raised.exception))

    def test_a_count_above_the_ceiling_is_refused(self):
        with self.assertRaises(chat.ChatError):
            chat.start(BRIEF + " Write " + str(chat.MAX_WORDS + 1) + " words.", "management", "pestel")

    def test_the_home_box_choice_sets_the_length(self):
        state = chat.start(BRIEF, "management", "pestel", words="long")
        self.assertEqual(state["answers"]["length"], str(chat.LONG_WORDS))
        self.assertEqual(chat.length_band(chat.target_words(state)), "long")


class FullReportTest(unittest.TestCase):
    def test_short_carries_none_of_the_long_sections(self):
        state = build(None)
        headings = [item["heading"] for item in state["draft"]["outline"]]
        for heading in ("Scope and Method", "Evidence Base", "Recommendation",
                        "Appendix: How the Computations Were Checked"):
            self.assertNotIn(heading, headings)
        self.assertEqual(state["draft"]["length_band"], "short")
        self.assertTrue(state["draft"]["met_target"])

    def test_mid_adds_the_evidence_base_and_the_discussion(self):
        state = build("mid")
        headings = [item["heading"] for item in state["draft"]["outline"]]
        self.assertIn("Scope and Method", headings)
        self.assertIn("Evidence Base", headings)
        self.assertIn("What the Evidence Shows Together", headings)
        self.assertNotIn("Recommendation", headings)
        self.assertNotIn("Appendix: How the Computations Were Checked", headings)
        self.assertEqual(state["draft"]["length_band"], "mid")
        self.assertGreaterEqual(state["draft"]["words"], chat.LENGTH_BANDS[1][2])

    def test_long_adds_the_reading_the_recommendation_and_the_appendix(self):
        state = build("long")
        headings = [item["heading"] for item in state["draft"]["outline"]]
        for heading in ("Recommendation", "Appendix: How the Computations Were Checked",
                        "What the Figures Assume", "Reading the Result"):
            self.assertIn(heading, headings)
        self.assertEqual(state["draft"]["length_band"], "long")
        # This fixture's evidence is thin, so the target may not be reached; the
        # draft says so rather than padding, which is the contract.
        self.assertEqual(state["draft"]["met_target"],
                         state["draft"]["words"] >= chat.LENGTH_BANDS[2][2])

    def test_the_bands_are_in_order_by_size(self):
        short = build(None)["draft"]["words"]
        mid = build("mid")["draft"]["words"]
        long = build("long")["draft"]["words"]
        self.assertLess(short, mid)
        self.assertLess(mid, long)

    def test_every_band_passes_the_gate_and_the_claim_ceiling(self):
        for length in (None, "mid", "long"):
            state = build(length)
            self.assertEqual(state["draft"]["missing"], [], length)
            self.assertEqual(state.get("claim_problems"), [], length)
            self.assertTrue(chat.docx_bytes(state).startswith(b"PK"), length)


class PlanLengthControlTest(unittest.TestCase):
    """The plan card's selector sets the same length the draft reads."""

    def _planned(self):
        state = chat.start(BRIEF, "management", "pestel")
        answers = {"decision": "Should the retailer open a device store in Tehran?",
                   "geography": "Middle East", "period": "5", "style": "apa"}
        while chat.current_question(state):
            question = chat.current_question(state)
            state = chat.answer(state, question["id"], answers.get(question["id"], ""))
        return state

    def test_the_plan_carries_the_options_and_the_current_band(self):
        state = self._planned()
        self.assertEqual(state["plan"]["length_band"], "short")
        self.assertEqual([option["key"] for option in state["plan"]["length_options"]],
                         ["short", "mid", "long"])

    def test_setting_a_band_updates_the_plan_and_the_draft(self):
        state = chat.set_length(self._planned(), "long")
        self.assertEqual(state["answers"]["length"], str(chat.LONG_WORDS))
        self.assertEqual(state["plan"]["length_band"], "long")
        state = chat.confirm_plan(state)
        state = chat.run_capability(state, "breakeven",
                                    {"fixed": "2000000", "price": "40000", "variable": "28000"})
        state = _seed(state)
        state = chat.draft(state, implications="The declared volume is below break-even.")
        self.assertIn("Recommendation", [item["heading"] for item in state["draft"]["outline"]])
        self.assertEqual(state["draft"]["length_band"], "long")

    def test_a_count_outside_the_bands_is_refused_at_the_plan(self):
        state = self._planned()
        with self.assertRaises(chat.ChatError):
            chat.set_length(state, "300")
        self.assertIsNone(state["answers"].get("length"))

    def test_the_length_is_only_set_while_the_plan_is_open(self):
        with self.assertRaises(chat.ChatError):
            chat.set_length(chat.start(BRIEF, "management", "pestel"), "mid")


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

    def test_the_start_route_takes_the_band_from_the_home_box(self):
        status, state = self.api.handle("POST", "/api/cases/chat",
                                        {"brief": BRIEF, "framework": "pestel", "words": "long"})
        self.assertEqual(status, 201)
        self.assertEqual(state["answers"]["length"], str(chat.LONG_WORDS))
        self.assertEqual(state["plan"]["length_band"] if state.get("plan") else "long", "long")

    def test_the_route_sets_a_band_and_refuses_a_count_below_the_floor(self):
        status, state = self.api.handle("POST", "/api/cases/chat", {"brief": BRIEF, "framework": "pestel"})
        self.assertEqual(status, 201)
        answers = {"decision": "Should the retailer open a device store in Tehran?",
                   "geography": "Middle East", "period": "5", "style": "apa"}
        while chat.current_question(state):
            question = chat.current_question(state)
            status, state = self.api.handle("POST", "/api/cases/chat/" + state["id"] + "/answer",
                                            {"question_id": question["id"],
                                             "value": answers.get(question["id"], "")})
        status, state = self.api.handle("POST", "/api/cases/chat/" + state["id"] + "/length",
                                        {"words": "mid"})
        self.assertEqual(status, 200)
        self.assertEqual(state["plan"]["length_band"], "mid")
        status, payload = self.api.handle("POST", "/api/cases/chat/" + state["id"] + "/length",
                                          {"words": "300"})
        self.assertEqual(status, 422)
        self.assertIn(str(chat.MIN_WORDS), payload["error"])


if __name__ == "__main__":
    unittest.main()
