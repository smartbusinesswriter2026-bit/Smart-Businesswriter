"""The deterministic PESTEL conductor: questions, plan, evidence, draft, export."""

import base64
import io
import os
import re
import shutil
import tempfile
import unittest
import zipfile
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.methods import breakeven as core_breakeven  # noqa: E402  (test-side core import)
from bp.product import api, chat  # noqa: E402

chat.set_compute(core_breakeven)


BRIEF = ("A grocery chain is considering entering the Saudi market and needs to assess the "
         "political, economic, social, technological, environmental and legal context.")


def academic(query, databases=None, limit=20, year_from=None):
    # The corpus is layer 1 and is searched alone.  These fixtures model a
    # corpus miss, so the web/API fallback and its notice are exercised.
    if databases == ["corpus"]:
        return {"results": [], "errors": [], "skipped": []}
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


def answer_all(state, style="harvard"):
    for question_id, value in (("decision", "Should we enter the Saudi grocery market?"),
                               ("geography", "Middle East"), ("period", "5"), ("style", style)):
        state = chat.answer(state, question_id, value)
    return state


class StartTest(unittest.TestCase):
    def test_a_nonsensical_category_error_is_refused_early(self):
        state = chat.start("What is the interest rate of Ansoff matrix at 6% per annum?")
        self.assertEqual(state["stage"], "refused")
        self.assertEqual(state["refusal"]["code"], "CATEGORY_ERROR")
        self.assertIn("framework", state["refusal"]["detail"])
        self.assertEqual(state["questions"], [])

    def test_a_pestel_brief_starts_with_one_question_and_defaults_from_the_text(self):
        state = chat.start(BRIEF, framework="pestel")
        self.assertEqual(state["stage"], "clarify")
        self.assertEqual(state["answers"]["geography"], "Middle East")
        self.assertEqual(state["answers"]["style"], "apa")
        self.assertEqual(chat.current_question(state)["id"], "decision")

    def test_a_computation_brief_is_refused_instead_of_forced_into_pestel(self):
        state = chat.start("Prepare the journal entries and the trial balance for the month.")
        self.assertEqual(state["stage"], "not_supported")
        self.assertIn("Accounting", state["message"])
        self.assertEqual(state["questions"], [])

    def test_a_too_short_brief_is_refused_with_a_reason(self):
        with self.assertRaises(chat.ChatError):
            chat.start("help")


class PlanProposalTest(unittest.TestCase):
    def test_a_valid_instruction_gets_a_proposal_not_a_repeated_brief(self):
        state = chat.start("Assess how a 6-week port disruption affects inventory policy using ABC analysis.",
                           subject="any")
        self.assertEqual(state["stage"], "clarify")
        proposal = state.get("proposal") or {}
        self.assertTrue(proposal.get("reading"))
        self.assertTrue(proposal.get("framework_options"))
        self.assertTrue(proposal.get("claims"))
        self.assertNotIn("Your brief", str(proposal))

    def test_refine_rejects_a_number_not_in_the_brief(self):
        state = chat.start("Assess how a 6-week port disruption affects inventory policy.",
                           subject="any")
        with self.assertRaises(chat.ChatError):
            chat.refine_plan(state, {"text": "Use a 10-week disruption instead"})

    def test_accept_plan_builds_the_plan_without_another_question_round(self):
        state = chat.start("Assess how a 6-week port disruption affects inventory policy.",
                           subject="any")
        updated = chat.accept_plan(state, framework="none")
        self.assertEqual(updated["stage"], "plan")
        self.assertEqual(updated["framework"], "none")
        self.assertTrue(updated["plan"])
        self.assertEqual(updated["questions"], [])

    def test_refine_accepts_a_framework_within_the_proposed_options(self):
        state = chat.start("Assess how a port disruption affects inventory policy.",
                           subject="any")
        updated = chat.refine_plan(state, {"framework": "none"})
        self.assertEqual(updated["framework"], "none")
        self.assertEqual(updated["stage"], "clarify")


class PlanTest(unittest.TestCase):
    def test_the_plan_lists_the_six_dimensions_and_what_pestel_misses(self):
        state = answer_all(chat.start(BRIEF, framework="pestel"))
        self.assertEqual(state["stage"], "plan")
        plan = state["plan"]
        self.assertEqual(plan["framework"], "PESTEL")
        self.assertEqual(len(plan["dimensions"]), 6)
        self.assertIn("does not assess internal capabilities", plan["misses"])
        self.assertEqual(plan["style"], "harvard")
        self.assertTrue(plan["checkpoints"])

    def test_an_invalid_choice_is_refused(self):
        state = chat.start(BRIEF, framework="pestel")
        chat.answer(state, "decision", "Should we enter?")
        with self.assertRaises(chat.ChatError):
            chat.answer(state, "geography", "Atlantis")
        with self.assertRaises(chat.ChatError):
            chat.answer(state, "period", "5")


class ResearchTest(unittest.TestCase):
    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_research_fills_six_dimensions_and_records_sources(self, _a, _w):
        state = answer_all(chat.start(BRIEF, framework="pestel"))
        state = chat.confirm_plan(state)
        state = chat.research(state)
        self.assertEqual(state["stage"], "evidence")
        self.assertEqual({item["dimension"] for item in state["evidence"]},
                         {"political", "economic", "social", "technological", "environmental", "legal"})
        self.assertEqual(len(state["sources"]), 6)
        self.assertTrue(all(item["source_id"] in {s["id"] for s in state["sources"]}
                            for item in state["evidence"]))
        self.assertEqual(state["gaps"], [])
        self.assertTrue(any("not configured" in note for note in state["notes"]))
        self.assertIn("total_s", state["timings"])
        self.assertEqual(set(state["timings"]["dimensions"]), {"political", "economic", "social",
                                                               "technological", "environmental", "legal"})

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", return_value={"results": [], "errors": [], "skipped": []})
    def test_a_dimension_with_no_evidence_is_a_gap(self, _a, _w):
        state = answer_all(chat.start(BRIEF, framework="pestel"))
        state = chat.research(chat.confirm_plan(state))
        self.assertEqual(len(state["gaps"]), 6)
        self.assertEqual(state["evidence"], [])

    def test_research_requires_a_confirmed_plan(self):
        state = answer_all(chat.start(BRIEF, framework="pestel"))
        with self.assertRaises(chat.ChatError):
            chat.research(state)

    @mock.patch("bp.product.chat.RESEARCH_DEADLINE", 0.05)
    @mock.patch("bp.product.chat._research_one")
    def test_a_hung_dimension_becomes_a_named_gap_instead_of_blocking(self, research_one):
        import time as _time

        def slow(state, dimension, corpus_doc_counts=None):
            _time.sleep(0.2)
            return {"dimension": dimension, "found": [], "errors": [], "skipped": [],
                    "notice": None, "dropped": 0, "elapsed": 0.2, "academic_cached": False,
                    "web_cached": False, "database_timings": {}}

        research_one.side_effect = slow
        state = chat.research(chat.confirm_plan(answer_all(chat.start(BRIEF, framework="pestel"))))
        self.assertEqual(len(state["gaps"]), 6)
        self.assertTrue(all("timed out" in gap["reason"] for gap in state["gaps"]))
        self.assertTrue(any("stopped after" in note for note in state["notes"]))
        self.assertLess(state["timings"]["total_s"], 1.0)


class DraftTest(unittest.TestCase):
    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def prepared(self, _a, _w):
        state = answer_all(chat.start(BRIEF, framework="pestel"))
        state = chat.research(chat.confirm_plan(state))
        return state

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_paper_uses_h1_for_frameworks_and_h2_for_dimensions(self, _a, _w):
        state = chat.draft(self.prepared(), implications="A cautious entry.", style="apa")
        levels = {section["heading"]: section["level"] for section in state["draft"]["outline"]}
        self.assertEqual(levels["Introduction"], 1)
        self.assertEqual(levels["PESTEL"], 1)
        self.assertEqual(levels["Political"], 2)
        self.assertEqual(levels["Discussion"], 1)
        self.assertEqual(levels["Implications"], 2)
        self.assertEqual(levels["Limitations"], 2)
        self.assertEqual(levels["Conclusion"], 1)
        self.assertEqual(levels["References"], 1)
        text = "\n".join(line for section in state["draft"]["outline"] for line in section["lines"])
        self.assertNotIn("(your analysis)", text)
        self.assertNotIn("Not supplied", text)

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_export_is_blocked_without_implications(self, _a, _w):
        state = chat.draft(self.prepared(), accepted_ids=[], implications="", style="apa")
        self.assertIn("implications", state["draft"]["missing"])
        with self.assertRaises(chat.ExportBlocked) as blocked:
            chat.docx_bytes(state)
        self.assertIn("implications", blocked.exception.missing)

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_section_quotes_the_evidence_and_uses_harvard(self, _a, _w):
        state = self.prepared()
        state = chat.draft(state, implications="The evidence suggests a cautious entry.", style="harvard")
        self.assertEqual(state["stage"], "draft")
        headings = [heading for heading, _lines in state["draft"]["sections"]]
        self.assertIn("Introduction", headings)
        self.assertIn("Political", headings)
        self.assertIn("Implications", headings)
        self.assertIn("Bibliography", headings)
        text = "\n".join(line for _h, lines in state["draft"]["sections"] for line in lines)
        self.assertIn("The source reports a relevant change", text)
        self.assertIn("(Lovelace, 2024)", text)
        self.assertIn("The evidence suggests a cautious entry.", text)
        self.assertNotIn("[E1]", text)
        self.assertNotIn("provenance", text)

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_a_gap_is_named_and_no_implication_is_invented(self, _a, _w):
        state = self.prepared()
        state = chat.draft(state, accepted_ids=[], implications="")
        text = "\n".join(line for _h, lines in state["draft"]["sections"] for line in lines)
        self.assertIn("No retrieved evidence covered this dimension", text)
        self.assertIn("implications", state["draft"]["missing"])

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_same_evidence_produces_the_same_sections(self, _a, _w):
        first = chat.draft(self.prepared(), implications="Same view.", style="apa")
        second = chat.draft(self.prepared(), implications="Same view.", style="apa")
        self.assertEqual(first["draft"]["sections"], second["draft"]["sections"])

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_export_is_a_real_docx(self, _a, _w):
        state = chat.draft(self.prepared(), implications="A view.", style="apa")
        data = chat.docx_bytes(state)
        self.assertTrue(data.startswith(b"PK"))
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            document = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("Times New Roman", document)
        self.assertIn("References", document)


class SwotTest(unittest.TestCase):
    def answer_swot(self, state, style="apa"):
        for question_id, value in (("decision", "Should the Saudi chain expand?"),
                                   ("strengths", "Brand loyalty; supplier relationships"),
                                   ("weaknesses", "Thin margins; limited digital capability"),
                                   ("geography", "Middle East"), ("period", "5"), ("style", style)):
            state = chat.answer(state, question_id, value)
        return state

    def test_the_swot_questions_collect_internal_factors_as_lists(self):
        state = chat.start(BRIEF + " Use a SWOT.", framework="swot")
        self.assertEqual(state["framework"], "swot")
        self.assertEqual(chat.current_question(state)["id"], "decision")
        state = chat.answer(state, "decision", "Should the chain expand?")
        self.assertEqual(chat.current_question(state)["id"], "strengths")
        state = chat.answer(state, "strengths", "Brand loyalty; supplier relationships")
        self.assertEqual(state["answers"]["strengths"], ["Brand loyalty", "supplier relationships"])

    def test_the_swot_plan_has_only_external_dimensions_and_says_what_it_misses(self):
        state = self.answer_swot(chat.start(BRIEF + " Use a SWOT.", framework="swot"))
        self.assertEqual(state["stage"], "plan")
        self.assertEqual(state["plan"]["framework"], "SWOT")
        self.assertEqual([d["key"] for d in state["plan"]["dimensions"]], ["opportunities", "threats"])
        self.assertTrue(state["plan"]["internal"])
        self.assertIn("does not weigh", state["plan"]["misses"])

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_swot_draft_keeps_internal_input_and_cites_external_evidence(self, _a, _w):
        state = self.answer_swot(chat.start(BRIEF + " Use a SWOT.", framework="swot"))
        state = chat.research(chat.confirm_plan(state))
        state = chat.draft(state, implications="A cautious expansion.", style="apa")
        headings = [heading for heading, _lines in state["draft"]["sections"]]
        for heading in ("Strengths", "Weaknesses", "Opportunities", "Threats", "References"):
            self.assertIn(heading, headings)
        text = "\n".join(line for _heading, lines in state["draft"]["sections"] for line in lines)
        self.assertIn("Brand loyalty", text)
        self.assertIn("Thin margins", text)
        self.assertIn("The source reports a relevant change", text)

    def test_swot_is_inferred_from_the_brief(self):
        self.assertEqual(chat.start(BRIEF + " Use a SWOT.")["framework"], "swot")
        self.assertEqual(chat.start(BRIEF + " Use PESTEL and SWOT.")["framework"], "pestel_swot")

    def test_a_country_brief_puts_the_country_into_every_query(self):
        state = chat.start("Apple is considering market entry into Iran and needs analysis.")
        state = chat.answer(state, "framework", "pestel")
        state = chat.answer(state, "decision", "Should Apple enter the Iranian market?")
        state = chat.answer(state, "geography", "Middle East")
        state = chat.answer(state, "period", "5")
        state = chat.answer(state, "style", "apa")
        self.assertEqual(state["plan"]["country"], "Iran")
        queries = [dimension["query"] for dimension in state["plan"]["dimensions"]]
        self.assertTrue(all(query.startswith("Iran ") for query in queries))
        self.assertTrue(all("Apple" not in query for query in queries))


    def test_precision_ranking_prefers_a_title_match_and_recency(self):
        cues = {"water"}
        specific = {"iran"}
        older = {"title": "Iran economy", "abstract": "water", "year": 2015,
                 "credibility": 50, "database": "OpenAlex"}
        better = {"title": "Iran water crisis", "abstract": "water", "year": 2025,
                  "credibility": 50, "database": "OpenAlex"}
        self.assertGreater(chat._rank(better, 4, cues, specific), chat._rank(older, 4, cues, specific))


class FiveForcesTest(unittest.TestCase):
    BRIEF = ("A mid-sized grocery chain is considering acquiring a cold-chain logistics provider in Saudi Arabia. "
             "Use Porter's Five Forces and a break-even analysis.")

    def answer_five(self):
        state = chat.start(self.BRIEF, framework="five_forces_breakeven")
        for question_id, value in (("decision", "Should the chain acquire the provider?"),
                                   ("industry", "grocery retail"),
                                   ("geography", "Middle East"), ("period", "5"), ("style", "apa"),
                                   ("fixed", "2000000"), ("price", "40"), ("variable", "28"),
                                   ("expected", "250000")):
            state = chat.answer(state, question_id, value)
        return state

    def test_the_combination_asks_for_the_break_even_inputs(self):
        state = chat.start(self.BRIEF, framework="five_forces_breakeven")
        self.assertEqual([q["id"] for q in state["questions"]],
                         ["decision", "industry", "geography", "period", "style", "fixed", "price", "variable", "expected"])
        self.assertEqual(chat.start(self.BRIEF)["framework"], "five_forces_breakeven")

    def test_the_plan_lists_the_five_forces(self):
        state = self.answer_five()
        self.assertEqual(state["plan"]["framework"], "Five Forces + Break-even")
        self.assertEqual([d["key"] for d in state["plan"]["dimensions"]],
                         ["rivalry", "entrants", "substitutes", "buyers", "suppliers"])

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_draft_has_forces_and_a_core_break_even_result(self, _a, _w):
        state = chat.research(chat.confirm_plan(self.answer_five()))
        state = chat.draft(state, implications="The acquisition is defensible only above break-even.", style="apa")
        levels = {item["heading"]: item["level"] for item in state["draft"]["outline"]}
        self.assertEqual(levels["Five Forces"], 1)
        self.assertEqual(levels["Industry rivalry"], 2)
        self.assertEqual(levels["Financial Feasibility"], 1)
        self.assertEqual(levels["Break-even Analysis"], 2)
        text = "\n".join(line for _heading, lines in state["draft"]["sections"] for line in lines)
        self.assertIn("166,666.67", text)
        self.assertIn("6,666,666.67", text)

    def test_a_price_below_variable_cost_is_refused(self):
        state = chat.start(self.BRIEF, framework="five_forces_breakeven")
        for question_id, value in (("decision", "Should the chain acquire?"), ("industry", "grocery retail"),
                                   ("geography", "Middle East"), ("period", "5"), ("style", "apa"),
                                   ("fixed", "100"), ("price", "20"), ("variable", "30")):
            state = chat.answer(state, question_id, value)
        state = chat.answer(state, "expected", "")
        with self.assertRaises(chat.ChatError):
            chat.draft(chat.confirm_plan(chat.research(state)), implications="A view.", style="apa")


class CombinedTest(unittest.TestCase):
    def answer_combined(self, style="apa"):
        state = chat.start(BRIEF + " Use PESTEL and SWOT.", framework="pestel_swot")
        for question_id, value in (("decision", "Should the Saudi chain enter?"),
                                   ("strengths", "Brand loyalty"), ("weaknesses", "Thin margins"),
                                   ("geography", "Middle East"), ("period", "5"), ("style", style)):
            state = chat.answer(state, question_id, value)
        return state

    def test_the_combined_plan_keeps_the_six_pestel_dimensions(self):
        state = self.answer_combined()
        self.assertEqual(state["plan"]["framework"], "PESTEL + SWOT")
        self.assertEqual(len(state["plan"]["dimensions"]), 6)
        self.assertTrue(state["plan"]["swot"])

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic", side_effect=academic)
    def test_the_combined_draft_has_pestel_and_swot_sections(self, _a, _w):
        state = chat.research(chat.confirm_plan(self.answer_combined()))
        state = chat.draft(state, implications="Proceed only with a partner.", style="harvard")
        headings = [heading for heading, _lines in state["draft"]["sections"]]
        for heading in ("Political", "Economic", "Social", "Technological", "Environmental", "Legal",
                        "Strengths", "Weaknesses", "Opportunities", "Threats", "Bibliography"):
            self.assertIn(heading, headings)
        text = "\n".join(line for _heading, lines in state["draft"]["sections"] for line in lines)
        self.assertIn("Brand loyalty", text)
        self.assertIn("from the", text)
        self.assertIn("by keyword", text)

    @mock.patch("bp.product.sources.search_web", side_effect=web)
    @mock.patch("bp.product.sources.search_academic",
                return_value={"results": [{"title": "Saudi chain growth and demand",
                                           "abstract": "Growth in demand and digital investment creates an opportunity in the Saudi market.",
                                           "authors": "Ada", "authors_list": ["Ada"], "year": 2024,
                                           "venue": "J", "doi": "10.1/growth", "url": "https://doi.org/10.1/growth",
                                           "database": "OpenAlex"}], "errors": [], "skipped": []})
    def test_the_combined_draft_maps_positive_evidence_to_opportunities(self, _a, _w):
        state = chat.research(chat.confirm_plan(self.answer_combined()))
        state = chat.draft(state, style="apa")
        opportunities = dict(state["draft"]["sections"])["Opportunities"]
        self.assertTrue(any("from the" in line for line in opportunities))
        self.assertIn("Growth in demand", "\n".join(opportunities))


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-chat-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_chat_route_creates_answers_and_exports(self):
        status, state = api.handle("POST", "/api/cases/chat", {"brief": BRIEF, "framework": "pestel"})
        self.assertEqual(status, 201)
        case_id = state["id"]
        status, state = api.handle("GET", "/api/cases/chat/" + case_id)
        self.assertEqual(status, 200)
        status, state = api.handle("POST", "/api/cases/chat/" + case_id + "/answer",
                                   {"question_id": "decision", "value": "Should we enter?"})
        self.assertEqual(status, 200)
        self.assertEqual(state["question_index"], 1)
        self.assertEqual(api.handle("GET", "/api/cases/chat/" + case_id + "/answer")[0], 405)
        self.assertEqual(api.handle("POST", "/api/cases/chat/ffffffffffff/answer", {})[0], 404)
        self.assertEqual(api.handle("DELETE", "/api/cases/chat/" + case_id)[0], 200)

    def test_the_chat_route_accepts_a_swot_framework(self):
        status, state = api.handle("POST", "/api/cases/chat",
                                   {"brief": BRIEF + " Use a SWOT.", "framework": "swot"})
        self.assertEqual(status, 201)
        self.assertEqual(state["framework"], "swot")
        self.assertEqual(state["questions"][1]["id"], "strengths")
        api.handle("DELETE", "/api/cases/chat/" + state["id"])


if __name__ == "__main__":
    unittest.main()
