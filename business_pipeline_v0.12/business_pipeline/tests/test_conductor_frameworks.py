"""The conductor frameworks added in this increment: Value Chain, Ansoff, VRIO and Break-even.

These tests prove the contract in CONDUCTOR_MANUAL.md §5/§7: each framework has a
question bank, a plan that says what it does and misses, a draft whose hierarchy is
H1 framework / H2 dimension, a named gap where evidence or input is missing, and no
figure that did not come from the frozen core.
"""

import re
import sys
import unittest
from unittest import mock

sys.path.insert(0, "src")
from bp import methods  # noqa: E402
from bp.methods import LIBRARY, breakeven as core_breakeven  # noqa: E402
from bp.product import api, chat  # noqa: E402

chat.set_compute(core_breakeven)
chat.set_method_compute(lambda name, inputs: LIBRARY[name].impl(inputs), methods.describe)

BRIEF = ("A grocery chain is considering entering the Saudi market and needs to assess the "
         "political, economic, social, technological, environmental and legal context.")


def academic(query, databases=None, limit=20, year_from=None):
    slug = re.sub(r"[^a-z0-9]+", "-", query.lower())[-60:]
    return {"results": [{
        "title": "Evidence on " + query[:60],
        "abstract": "The source reports a relevant change in the external environment. A second sentence.",
        "authors": "Ada Lovelace", "authors_list": ["Ada Lovelace"], "year": 2024,
        "venue": "Journal of External Analysis", "doi": "10.1/" + slug,
        "url": "https://doi.org/10.1/" + slug, "database": "OpenAlex",
    }], "errors": [], "skipped": []}


def web(query, region="Global", limit=10, category=None, fast=False):
    return {"results": [], "notice": "Web search is not configured.", "sites": []}


def answer_all(state, answers):
    while chat.current_question(state):
        question = chat.current_question(state)
        if question["id"] in answers:
            value = answers[question["id"]]
        elif question["type"] == "number":
            value = "1"
        else:
            value = question.get("default") or "x"
        state = chat.answer(state, question["id"], value)
    return state


def research(state):
    with mock.patch("bp.product.sources.search_academic", side_effect=academic), \
         mock.patch("bp.product.sources.search_web", side_effect=web):
        return chat.research(state)


def levels(state):
    return {item["heading"]: item["level"] for item in state["draft"]["outline"]}


def body(state):
    return "\n".join(line for _heading, lines in state["draft"]["sections"] for line in lines)


class Registration(unittest.TestCase):
    def test_every_new_framework_has_a_label_questions_and_a_plan_entry(self):
        for key in ("value_chain", "ansoff", "vrio", "breakeven"):
            self.assertIn(key, chat.FRAMEWORKS, key)
            self.assertTrue(chat.FRAMEWORKS[key]["label"], key)
            self.assertTrue(chat.FRAMEWORK_QUESTIONS[key], key)
            state = chat.start(BRIEF, framework=key)
            self.assertEqual(state["framework"], key)
            self.assertNotEqual(state["stage"], "not_supported", key)

    def test_the_dimension_count_matches_the_named_framework(self):
        self.assertEqual(len(chat.VALUE_DIMENSIONS), 9)
        self.assertEqual(len(chat.ANSOFF_DIMENSIONS), 4)
        self.assertEqual(chat.FRAMEWORKS["vrio"]["dimensions"], [])
        self.assertEqual(chat.FRAMEWORKS["breakeven"]["dimensions"], [])
        self.assertFalse(chat.FRAMEWORKS["vrio"]["evidence"])

    def test_the_unknown_framework_message_names_the_new_options(self):
        with self.assertRaises(chat.ChatError) as caught:
            chat.start(BRIEF, framework="bcg_matrix")
        message = str(caught.exception)
        for word in ("Value Chain", "Ansoff", "VRIO", "Break-even"):
            self.assertIn(word, message)


class Inference(unittest.TestCase):
    def test_a_named_framework_is_inferred_from_the_brief(self):
        cases = {
            "Assess the value chain of the grocery chain in Saudi Arabia.": "value_chain",
            "Use the Ansoff growth matrix for the grocery chain.": "ansoff",
            "Apply VRIO to the chain's cold-chain fleet in Saudi Arabia.": "vrio",
            "Run a break-even analysis for the Jeddah store at the declared price.": "breakeven",
            "Use Porter's Five Forces and a break-even analysis.": "five_forces_breakeven",
            "Use Porter's Five Forces for the Saudi grocery market.": "five_forces",
        }
        for brief, expected in cases.items():
            self.assertEqual(chat.start(brief)["framework"], expected, brief)

    def test_a_computation_brief_is_not_refused_when_break_even_is_named(self):
        state = chat.start("Compute the break-even for the new store at a declared price.", framework="breakeven")
        self.assertNotEqual(state["stage"], "not_supported")


class Plans(unittest.TestCase):
    def plan(self, framework, answers):
        state = answer_all(chat.start(BRIEF, framework=framework), answers)
        return state["plan"]

    def test_the_plan_lists_the_nine_activities_and_the_four_options(self):
        chain = self.plan("value_chain", {"firm": "Grocery chain", "decision": "Should the chain enter?"})
        self.assertEqual([d["key"] for d in chain["dimensions"]],
                         ["inbound", "operations", "outbound", "marketing", "service",
                          "procurement", "technology", "human", "infrastructure"])
        ansoff = self.plan("ansoff", {"firm": "Grocery chain", "decision": "Which option?"})
        self.assertEqual([d["key"] for d in ansoff["dimensions"]],
                         ["penetration", "development", "product", "diversification"])

    def test_every_plan_says_what_it_does_and_misses(self):
        for framework in ("value_chain", "ansoff", "vrio", "breakeven"):
            plan = self.plan(framework, {})
            self.assertTrue(plan["why"], framework)
            self.assertTrue(plan["misses"], framework)
            self.assertTrue(plan["output"], framework)

    def test_vrio_and_break_even_declare_that_no_evidence_is_retrieved(self):
        for framework in ("vrio", "breakeven"):
            plan = self.plan(framework, {})
            self.assertFalse(plan["evidence"], framework)
            self.assertIn("Review your inputs", plan["checkpoints"], framework)


class Drafts(unittest.TestCase):
    def test_a_value_chain_paper_has_one_h1_and_nine_h2s(self):
        state = answer_all(chat.start(BRIEF, framework="value_chain"),
                           {"firm": "Grocery chain", "decision": "Should the chain enter?"})
        state = research(chat.confirm_plan(state))
        state = chat.draft(state, implications="Entry depends on outbound logistics.")
        found = levels(state)
        self.assertEqual(found["Value Chain"], 1)
        for label in ("Inbound logistics", "Operations", "Outbound logistics", "Marketing and sales", "Service",
                      "Procurement", "Technology development", "Human resource management", "Firm infrastructure"):
            self.assertEqual(found[label], 2, label)
        self.assertIn("Evidence on", body(state))

    def test_an_ansoff_paper_has_the_four_options(self):
        state = answer_all(chat.start(BRIEF, framework="ansoff"), {"firm": "Grocery chain"})
        state = research(chat.confirm_plan(state))
        state = chat.draft(state, implications="Market penetration is the least risky option.")
        found = levels(state)
        self.assertEqual(found["Ansoff Growth Matrix"], 1)
        for label in ("Market penetration", "Market development", "Product development", "Diversification"):
            self.assertEqual(found[label], 2, label)

    def test_a_vrio_paper_reproduces_the_students_judgments(self):
        state = answer_all(chat.start(BRIEF, framework="vrio"), {
            "resources": "Cold-chain fleet; Store locations",
            "valuable": "Fleet - yes: it serves chilled goods",
            "rare": "Fleet - no: rivals own one",
            "costly": "", "organized": "",
        })
        state = research(chat.confirm_plan(state))
        self.assertEqual(state["evidence"], [])
        state = chat.draft(state, implications="The fleet alone is not a durable advantage.")
        found = levels(state)
        self.assertEqual(found["VRIO"], 1)
        for label in ("Resources", "Valuable", "Rare", "Costly to imitate", "Organised to capture value"):
            self.assertEqual(found[label], 2, label)
        text = body(state)
        self.assertIn("Cold-chain fleet; Store locations", text)
        self.assertIn("Fleet - yes: it serves chilled goods", text)
        self.assertIn("No imitation-cost judgments were supplied.", text)

    def test_a_break_even_paper_reports_only_the_core_result(self):
        state = answer_all(chat.start(BRIEF, framework="breakeven"), {
            "fixed": "2000000", "price": "40", "variable": "28", "expected": "250000",
            "decision": "Is the declared price viable?"})
        state = research(chat.confirm_plan(state))
        state = chat.draft(state, implications="The price is viable only above the break-even volume.")
        found = levels(state)
        self.assertEqual(found["Financial Feasibility"], 1)
        self.assertEqual(found["Break-even Analysis"], 2)
        text = body(state)
        self.assertIn("166,666.67", text)
        self.assertIn("6,666,666.67", text)
        self.assertIn("Every financial figure is the frozen method's result", text)
        self.assertNotIn("No financial figure is computed", text)

    def test_a_missing_dimension_gets_background_not_a_gap(self):
        with mock.patch("bp.product.sources.search_academic", return_value={"results": [], "errors": [], "skipped": []}), \
             mock.patch("bp.product.sources.search_web", side_effect=web):
            state = chat.start(BRIEF, framework="ansoff")
            state = answer_all(state, {"firm": "Grocery chain"})
            state = chat.confirm_plan(state)
            state = chat.research(state)
        state = chat.draft(state, implications="No option is supported yet.")
        self.assertEqual(state["gaps"], [])
        self.assertTrue(state["background"])
        self.assertIn("Background reading", body(state))
        self.assertNotIn("No evidence was retrieved for", body(state))


class AttachedComputation(unittest.TestCase):
    def pestel(self):
        state = answer_all(chat.start(BRIEF, framework="pestel"), {"decision": "Should the chain enter?"})
        return chat.confirm_plan(state)

    def test_break_even_can_be_attached_to_any_framework(self):
        brief = (BRIEF.rstrip(".") + ", and a break-even analysis at the declared price.")
        state = answer_all(chat.start(brief, framework="pestel"), {"decision": "Should the chain enter?"})
        state = chat.confirm_plan(state)
        self.assertTrue(chat.capabilities.carries(state.get("selection"), "breakeven"))
        state = chat.attach_computation(state, "breakeven",
                                        {"fixed": "2000000", "price": "40", "variable": "28", "expected": "250000"})
        self.assertEqual(state["computation"]["key"], "breakeven")
        self.assertIn("breakeven", state["computations"])
        state = research(state)
        state = chat.draft(state, implications="Entry is viable only above break-even.")
        found = levels(state)
        self.assertEqual(found["Financial Feasibility"], 1)
        self.assertEqual(found["Break-even Analysis"], 2)
        self.assertEqual(found["Framework and Financial Feasibility"], 2)
        self.assertIn("166,666.67", body(state))
        self.assertIn("and break-even analysis", state["draft"]["title"])

    def test_it_is_refused_on_the_combo_that_already_carries_it(self):
        state = answer_all(chat.start(BRIEF, framework="five_forces_breakeven"),
                           {"industry": "grocery", "fixed": "2000000", "price": "40", "variable": "28"})
        with self.assertRaises(chat.ChatError):
            chat.attach_computation(state, "breakeven", {"fixed": "1", "price": "2", "variable": "1"})

    def test_bad_or_impossible_figures_are_refused(self):
        state = self.pestel()
        with self.assertRaises(chat.ChatError):
            chat.attach_computation(state, "breakeven", {"fixed": "1", "price": "", "variable": "1"})
        with self.assertRaises(chat.ChatError):
            chat.attach_computation(state, "breakeven", {"fixed": "1", "price": "abc", "variable": "1"})
        with self.assertRaises(chat.ChatError):
            chat.attach_computation(state, "breakeven", {"fixed": "1", "price": "10", "variable": "20"})
        self.assertIsNone(state.get("computation"))

    def test_only_break_even_is_attach_today(self):
        with self.assertRaises(chat.ChatError):
            chat.attach_computation(self.pestel(), "npv", {"fixed": "1", "price": "2", "variable": "1"})


class ExportGate(unittest.TestCase):
    def test_a_vrio_paper_needs_resources_and_a_value_judgment(self):
        state = answer_all(chat.start(BRIEF, framework="vrio"), {"resources": "Fleet", "valuable": ""})
        state["answers"]["resources"] = []
        state = research(chat.confirm_plan(state))
        state = chat.draft(state, implications="No advantage is established.")
        self.assertIn("at least one resource", state["draft"]["missing"])
        self.assertIn("at least one value judgment", state["draft"]["missing"])

    def test_an_attached_computation_is_listed_when_its_figures_are_missing(self):
        from bp.product import paper
        brief = (BRIEF.rstrip(".") + ", and a break-even analysis at the declared price.")
        state = answer_all(chat.start(brief, framework="pestel"), {"decision": "Should the chain enter?"})
        state = chat.confirm_plan(state)
        self.assertIn("the break-even figures", paper.missing(state, "A position."))
        state = chat.attach_computation(state, "breakeven", {"fixed": "1", "price": "2", "variable": "1"})
        self.assertNotIn("the break-even figures", paper.missing(state, "A position."))


class ApiRoute(unittest.TestCase):
    def test_the_computation_action_is_served(self):
        brief = (BRIEF.rstrip(".") + ", and a break-even analysis at the declared price.")
        status, state = api.handle("POST", "/api/cases/chat", {"brief": brief, "framework": "pestel"})
        self.assertEqual(status, 201)
        while chat.current_question(state):
            question = chat.current_question(state)
            value = "Should the chain enter?" if question["id"] == "decision" else (question.get("default") or "1")
            status, state = api.handle("POST", "/api/cases/chat/" + state["id"] + "/answer",
                                       {"question_id": question["id"], "value": value})
            self.assertEqual(status, 200)
        status, state = api.handle("POST", "/api/cases/chat/" + state["id"] + "/plan", {})
        self.assertEqual(status, 200)
        status, state = api.handle("POST", "/api/cases/chat/" + state["id"] + "/computation",
                                   {"key": "breakeven", "fixed": "2000000", "price": "40", "variable": "28"})
        self.assertEqual(status, 200)
        self.assertEqual(state["computation"]["inputs"]["fixed"], "2000000")


if __name__ == "__main__":
    unittest.main()
