"""The four long documents, and the door to each of them.

`bp.product.chat` has always composed four documents section by section — a
business plan, a feasibility study, a marketing plan and a project proposal — but
only the business plan could be reached: the page carried one hard-coded button and
posted `profile: "business_plan"`, and `paper._missing_base` gated on that same one
string.  The other three therefore drafted and then could never be exported (the
gate fell through to the framework-paper path and demanded an "implications"
sentence no plan profile has a field for), and two of them stored a draft with no
title, no outline and no `missing` list, and printed a placeholder reference list
whether or not a source had been accepted.

These tests pin both halves: the engine shape and export of every profile, and the
doors in the served page.  They are presence guards where the browser cannot be
run, exactly like `tests/test_product_subjects.ServedUiContractTest`.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp.product import api, chat, paper  # noqa: E402


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


api.attach_methods(_run, methods.describe)

BRIEF = "A coffee shop selling specialty coffee to commuters in a mid-sized city."

#: Every documented profile, its shelf and the sections it promises.
PROFILES = {
    "business_plan": ("entrepreneurship",
                      ["executive_summary", "business_description", "market_analysis", "marketing_plan",
                       "operations_plan", "management", "financial_plan", "risk", "conclusion", "references"]),
    "feasibility_study": ("entrepreneurship",
                          ["executive_summary", "project_description", "market_feasibility",
                           "technical_feasibility", "management_feasibility", "legal_feasibility",
                           "financial_feasibility", "risk", "conclusion", "references"]),
    "marketing_plan": ("marketing",
                       ["executive_summary", "business_context", "audience_positioning", "channels_tactics",
                        "budget_measurement", "risk", "conclusion", "references"]),
    "project_proposal": ("project-management",
                         ["executive_summary", "project_description", "work_plan", "budget",
                          "monitoring_evaluation", "risk", "conclusion", "references"]),
    "project_plan": ("project-management",
                     ["executive_summary", "charter", "scope", "wbs", "schedule", "cost",
                      "organisation", "risk", "governance", "monitoring", "limitations",
                      "conclusion", "references"]),
}

#: A complete project record for the plan profile; no number is invented here.
PROJECT_RECORD = {
    "charter": {"title": "Meal counter", "objective": "Open a counter", "sponsor": "Dean",
                "scope_in": ["Counter"], "scope_out": ["Delivery"],
                "deliverables": ["Counter built"], "success_measures": ["Break even"],
                "budget_total": 25000, "currency": "USD"},
    "wbs": [
        {"id": "1", "parent": None, "level": 1, "name": "Design", "acceptance": "", "owner": "", "cost": 0},
        {"id": "1.1", "parent": "1", "level": 2, "name": "Drawings", "acceptance": "Signed",
         "owner": "Architect", "cost": 20000},
        {"id": "2", "parent": None, "level": 1, "name": "Build", "acceptance": "", "owner": "", "cost": 0},
        {"id": "2.1", "parent": "2", "level": 2, "name": "Fit-out", "acceptance": "Handover",
         "owner": "Builder", "cost": 5000},
    ],
    "activities": [
        {"id": "A1", "name": "Draw", "wbs": "1.1", "duration": 5, "predecessors": [], "resource": "Architect"},
        {"id": "A2", "name": "Fit-out", "wbs": "2.1", "duration": 4, "predecessors": ["A1"], "resource": "Builder"},
    ],
    "resources": [{"name": "Architect", "role": "Design", "capacity": 1},
                  {"name": "Builder", "role": "Build", "capacity": 1}],
    "raci": [
        {"activity": "A1", "role": "Design", "letter": "R"},
        {"activity": "A1", "role": "Build", "letter": "A"},
        {"activity": "A2", "role": "Build", "letter": "R"},
        {"activity": "A2", "role": "Design", "letter": "A"},
    ],
    "risks": [{"id": "R1", "description": "Permit delay", "likelihood": "Medium", "impact": "High",
               "response": "Apply early", "owner": "PM"}],
}

BLOCKS = {
    "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
    "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
    "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
    "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                    "base_fixed_cost": "300000", "price_changes": ["-0.1", "0", "0.1"],
                    "volume_changes": ["-0.2", "0", "0.2"]},
    "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "90000", "90000"],
                 "interest": ["40000", "30000", "20000"],
                 "principal_repayment": ["100000", "100000", "100000"],
                 "capex": ["0", "0", "0"], "tax_rate": "0.25", "receivable_days": "30",
                 "inventory_days": "45", "payable_days": "30", "opening_cash": "200000",
                 "opening_fixed_assets": "450000", "opening_receivables": "0",
                 "opening_inventory": "0", "opening_payables": "0", "opening_loan": "400000",
                 "opening_equity": "250000"},
}


def supplied(profile):
    """A confirmed document with every required field supplied and every required block run."""
    subject = PROFILES[profile][0]
    state = chat.start(BRIEF, subject=subject, profile=profile, level="shs")
    state = chat.confirm_plan(state)
    required = [field["key"] for field in state["plan"]["fields"] if field.get("required")]
    state = chat.set_inputs(state, {key: "a detail the student supplies" for key in required})
    if profile == "project_plan":
        state = chat.set_project(state, PROJECT_RECORD)
    wanted = [block["key"] for block in state["plan"]["blocks"] if block.get("required")]
    return chat.compute(state, {key: BLOCKS[key] for key in wanted if key in BLOCKS})


class PlanEngineTest(unittest.TestCase):
    def test_every_profile_declares_the_documented_sections_in_order(self):
        for profile, (subject, sections) in PROFILES.items():
            state = chat.start(BRIEF, subject=subject, profile=profile, level="shs")
            self.assertEqual([row["key"] for row in state["plan"]["sections"]], sections, profile)
            self.assertEqual(state["plan"]["profile"], profile, profile)

    def test_every_profile_carries_student_fields_and_computation_blocks(self):
        for profile, (subject, _) in PROFILES.items():
            state = chat.start(BRIEF, subject=subject, profile=profile, level="shs")
            self.assertTrue(state["plan"]["fields"], profile)
            if profile == "project_plan":
                self.assertEqual(state["plan"]["blocks"], [], profile)
                continue
            self.assertTrue(state["plan"]["blocks"], profile)
            self.assertTrue(any(block.get("required") for block in state["plan"]["blocks"]), profile)

    def test_every_profile_drafts_a_titled_document_with_an_outline(self):
        for profile in PROFILES:
            draft = chat.draft(supplied(profile))["draft"]
            self.assertTrue(draft["title"], profile)
            self.assertTrue(draft["outline"], profile)
            self.assertEqual(draft["profile"], profile)
            self.assertEqual(draft["missing"], [], profile)
            headings = [item["heading"] for item in draft["outline"]]
            self.assertIn("Conclusion", headings, profile)
            self.assertIn("References", headings, profile)

    def test_every_profile_exports_a_word_file(self):
        """The trap: three profiles drafted cleanly and then could not export at all."""
        for profile in PROFILES:
            data = chat.docx_bytes(chat.draft(supplied(profile)))
            self.assertTrue(data.startswith(b"PK"), profile)
            self.assertGreater(len(data), 5000, profile)

    def test_the_export_gate_names_a_missing_field_and_never_asks_for_implications(self):
        """`paper` gated on `business_plan` alone, then asked a plan for `implications`."""
        state = chat.confirm_plan(chat.start(BRIEF, subject="marketing", profile="marketing_plan", level="shs"))
        declared = paper.missing(state)
        labels = {field["label"] for field in state["plan"]["fields"] if field.get("required")}
        self.assertTrue(declared)
        self.assertTrue(labels & set(declared), declared[:3])
        self.assertNotIn("implications", declared)

    def test_the_gate_knows_exactly_the_profiles_chat_declares(self):
        declared = {chat.PROFILE_BUSINESS_PLAN, chat.PROFILE_FEASIBILITY_STUDY,
                    chat.PROFILE_MARKETING_PLAN, chat.PROFILE_PROJECT_PROPOSAL,
                    chat.PROFILE_PROJECT_PLAN}
        self.assertEqual(set(paper.DRAFT_PROFILES), declared)

    def test_a_plan_with_no_accepted_evidence_says_so_and_never_prints_a_placeholder(self):
        text = " ".join(" ".join(item["lines"]) for item in chat.draft(supplied("project_proposal"))["draft"]["outline"])
        self.assertNotIn("No references supplied.", text)
        self.assertIn("No sources were used.", text)


class PlanDoorContractTest(unittest.TestCase):
    """The served page must carry a door for every document, not one for the business plan."""

    def setUp(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            self.html = stream.read()

    def test_the_page_declares_a_door_for_every_profile(self):
        self.assertIn("const PLAN_PROFILES = {", self.html)
        for profile in PROFILES:
            self.assertIn(profile + ": {", self.html, profile)

    def test_each_door_names_its_subject_and_its_start_label(self):
        for profile, (subject, _) in PROFILES.items():
            block = self.html.split(profile + ": {", 1)[1].split("},", 1)[0]
            self.assertIn('subject: "%s"' % subject, block, profile)
            self.assertIn('start: "Start the', block, profile)
            self.assertIn("heading:", block, profile)

    def test_the_subject_pages_offer_the_right_doors(self):
        self.assertIn('entrepreneurship: ["business_plan", "feasibility_study"]', self.html)
        self.assertIn('marketing: ["marketing_plan"]', self.html)
        self.assertIn('"project-management": ["project_proposal", "project_plan"]', self.html)

    def test_the_proposal_run_posts_the_chosen_profile_and_its_subject(self):
        body = self.html.split("async function beginPlan()", 1)[1].split("async function downloadPlan()", 1)[0]
        self.assertIn('profile: state.planProfile || "business_plan"', body)
        self.assertIn("subject: door.subject", body)
        self.assertNotIn('profile: "business_plan", subject: "entrepreneurship"', body)

    def test_the_subject_page_binds_every_door(self):
        self.assertIn('$$("[data-plan-profile]", out).forEach', self.html)
        self.assertIn('startPlan("strict", button.dataset.planProfile)', self.html)
        self.assertNotIn('$("#subjectplan")', self.html)

    def test_the_start_box_carries_the_door_profile_once(self):
        body = self.html.split("async function startChat()", 1)[1].split("async function reviseChat", 1)[0]
        self.assertIn("if (state.planDoor)", body)
        self.assertIn("body.profile = state.planDoor", body)
        self.assertIn("state.planDoor = null", body)

    def test_the_panel_heading_follows_the_document_that_is_open(self):
        self.assertIn("titleNode.textContent = composed || planProfile().label", self.html)
        self.assertIn('const titleNode = $("#plan-title")', self.html)


if __name__ == "__main__":
    unittest.main()
