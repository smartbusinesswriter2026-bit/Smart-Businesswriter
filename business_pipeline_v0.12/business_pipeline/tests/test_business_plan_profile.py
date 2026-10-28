"""The business-plan paper profile (B-121).

The profile composes student input, retrieved evidence, plan-level computations
from the frozen core and integration prose.  These tests pin the plan shape, the
hard refusals (an unbalanced opening balance, a missing required block), the
brief readers and the routes that carry the plan through to a Word file.
"""

import base64
import io
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from bp import methods  # noqa: E402
from bp.product import api, chat, documents, paper  # noqa: E402


def _run(method_id, inputs):
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


api.attach_methods(_run, methods.describe)

BRIEF = "A coffee shop selling specialty coffee to university students in Cebu City."

INPUTS = {
    "business_name": "Bean There", "product": "specialty coffee and pastries",
    "customers": "university students", "location": "Cebu City",
    "positioning": "affordable specialty coffee", "channels": "a campus kiosk and social media",
    "pricing_note": "mid-market pricing", "operations": "a single kiosk with two staff",
    "suppliers": "a local roaster", "capacity_note": "120 cups a day",
    "team": "the owner and one barista", "roles": "the owner buys and manages; the barista serves",
    "risks": ["a rent increase", "low student footfall"],
}

BLOCKS = {
    "frommarket": {"market_size": "60000000", "target_share": "0.03", "price": "120"},
    "breakeven": {"fixed": "300000", "price": "120", "variable": "55"},
    "depreciation": {"cost": "500000", "salvage": "50000", "life": "5", "method": "straight_line"},
    "proforma": {"revenue": ["1200000", "1500000", "1800000"], "gross_margin_rate": "0.40",
                 "operating_costs": ["300000", "320000", "340000"],
                 "depreciation": ["90000", "90000", "90000"],
                 "interest": ["40000", "30000", "20000"],
                 "principal_repayment": ["100000", "100000", "100000"],
                 "capex": ["0", "0", "0"], "tax_rate": "0.25",
                 "receivable_days": "30", "inventory_days": "45", "payable_days": "30",
                 "opening_cash": "200000", "opening_fixed_assets": "450000",
                 "opening_receivables": "0", "opening_inventory": "0", "opening_payables": "0",
                 "opening_loan": "400000", "opening_equity": "250000"},
    "sensitivity": {"base_price": "120", "base_units": "10000", "base_variable_cost": "55",
                    "base_fixed_cost": "300000",
                    "price_changes": ["-0.1", "0", "0.1"], "volume_changes": ["-0.2", "0", "0.2"]},
    "tax": {"taxable_income": "1000000", "income_tax_rate": "0.25"},
    "captable": {"pre_money_valuation": "4000000", "investment": "1000000",
                 "founders_shares": "1000000", "option_pool_pct": "0.10"},
    "impact": {"options": [{"name": "basic", "cost": "10000", "effect": "40"},
                           {"name": "intensive", "cost": "18000", "effect": "60"}]},
}
COLLEGE_INPUTS = {**INPUTS, "impact_summary": "Local sourcing keeps more spending in the city."}


def complete(level="shs"):
    state = chat.start(BRIEF, "entrepreneurship", profile="business_plan", level=level)
    state = chat.confirm_plan(state)
    state = chat.set_inputs(state, COLLEGE_INPUTS if level == "college" else INPUTS)
    wanted = {block["key"] for block in state["plan"]["blocks"]}
    state = chat.compute(state, {key: value for key, value in BLOCKS.items() if key in wanted})
    return chat.draft(state)


def headings(state, level=1):
    return [item["heading"] for item in state["draft"]["outline"] if item["level"] == level]


class PlanShape(unittest.TestCase):
    def test_shs_plan_has_the_standard_sections_and_core_blocks(self):
        state = chat.start(BRIEF, "entrepreneurship", profile="business_plan", level="shs")
        self.assertEqual(state["stage"], "plan")
        self.assertEqual([block["key"] for block in state["plan"]["blocks"]],
                         ["frommarket", "breakeven", "depreciation", "proforma", "sensitivity"])
        self.assertTrue(all(block["required"] for block in state["plan"]["blocks"]))
        self.assertNotIn("funding", [section["key"] for section in state["plan"]["sections"]])
        self.assertNotIn("impact", [section["key"] for section in state["plan"]["sections"]])

    def test_college_plan_adds_tax_cap_table_and_impact(self):
        state = chat.start(BRIEF, "entrepreneurship", profile="business_plan", level="college")
        keys = [block["key"] for block in state["plan"]["blocks"]]
        for key in ("tax", "captable", "impact"):
            self.assertIn(key, keys)
        sections = [section["key"] for section in state["plan"]["sections"]]
        self.assertIn("funding", sections)
        self.assertIn("impact", sections)
        fields = [field["key"] for field in state["plan"]["fields"]]
        self.assertIn("impact_summary", fields)

    def test_the_financial_plan_is_one_h1_with_computation_h2s(self):
        state = complete("shs")
        self.assertIn("Financial Plan", headings(state))
        outline = state["draft"]["outline"]
        start = next(index for index, item in enumerate(outline) if item["heading"] == "Financial Plan")
        h2s = []
        for item in outline[start + 1:]:
            if item["level"] == 1:
                break
            h2s.append(item["heading"])
        self.assertEqual(h2s, ["Market Size and Target Sales", "Break-even", "Depreciation",
                               "Projected Financial Statements", "Sensitivity"])

    def test_every_plan_block_is_a_declared_core_method(self):
        for block in chat.COMPUTATION_BLOCKS:
            self.assertIn(block["method"], methods.LIBRARY)

    def test_an_unknown_level_or_mode_is_refused(self):
        with self.assertRaises(chat.ChatError):
            chat.start(BRIEF, profile="business_plan", level="graduate")
        with self.assertRaises(chat.ChatError):
            chat.start(BRIEF, profile="business_plan", mode="anything")

    def test_a_short_brief_is_refused(self):
        with self.assertRaises(chat.ChatError):
            chat.start("coffee", profile="business_plan")


class Customisation(unittest.TestCase):
    def test_open_composition_can_leave_out_an_optional_section(self):
        state = chat.start(BRIEF, profile="business_plan", mode="open")
        state = chat.customise(state, {"sections": ["marketing_plan"]})
        self.assertNotIn("marketing_plan", [section["key"] for section in state["plan"]["sections"]])

    def test_leaving_out_an_impact_section_also_drops_its_block_and_field(self):
        state = chat.start(BRIEF, profile="business_plan", mode="open", level="college")
        state = chat.customise(state, {"sections": ["impact"]})
        self.assertNotIn("impact", [block["key"] for block in state["plan"]["blocks"]])
        self.assertNotIn("impact_summary", [field["key"] for field in state["plan"]["fields"]])
        self.assertNotIn("impact", [section["key"] for section in state["plan"]["sections"]])

    def test_strict_composition_keeps_the_standard_sections(self):
        state = chat.start(BRIEF, profile="business_plan", mode="strict")
        with self.assertRaises(chat.ChatError):
            chat.customise(state, {"sections": ["marketing_plan"]})

    def test_a_level_change_rebuilds_the_blocks_and_fields(self):
        state = chat.start(BRIEF, profile="business_plan", level="shs")
        state = chat.customise(state, {"level": "college"})
        self.assertIn("captable", [block["key"] for block in state["plan"]["blocks"]])
        self.assertIn("impact_summary", [field["key"] for field in state["plan"]["fields"]])
        state = chat.customise(state, {"level": "shs"})
        self.assertNotIn("captable", [block["key"] for block in state["plan"]["blocks"]])

    def test_a_plan_cannot_be_customised_after_confirmation(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        with self.assertRaises(chat.ChatError):
            chat.customise(state, {"level": "college"})


class InputsAndComputation(unittest.TestCase):
    def test_unknown_input_fields_are_refused(self):
        state = chat.start(BRIEF, profile="business_plan")
        with self.assertRaises(chat.ChatError):
            chat.set_inputs(state, {"invented": "value"})

    def test_inputs_keep_the_students_words_and_split_items(self):
        state = chat.start(BRIEF, profile="business_plan")
        state = chat.set_inputs(state, {"business_name": " Bean There ", "risks": "rent; footfall"})
        self.assertEqual(state["answers"]["inputs"]["business_name"], "Bean There")
        self.assertEqual(state["answers"]["inputs"]["risks"], ["rent", "footfall"])

    def test_saving_inputs_does_not_close_the_research_step(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        state = chat.set_inputs(state, INPUTS)
        self.assertEqual(state["stage"], "research_ready")

    def test_computation_needs_a_confirmed_plan(self):
        state = chat.start(BRIEF, profile="business_plan")
        with self.assertRaises(chat.ChatError):
            chat.compute(state, BLOCKS)

    def test_an_unknown_block_is_refused(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        with self.assertRaises(chat.ChatError):
            chat.compute(state, {"invented": {}})

    def test_the_core_result_is_stored_and_no_formula_is_recomputed(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        state = chat.compute(state, {"frommarket": BLOCKS["frommarket"], "breakeven": BLOCKS["breakeven"]})
        self.assertTrue(state["computations"]["frommarket"]["ok"])
        self.assertEqual(state["computations"]["frommarket"]["result"]["target_revenue"], "1800000.00")
        self.assertEqual(state["computations"]["breakeven"]["result"]["breakeven_units"],
                         "4615.3846153846153846153846153846153846153846153846")

    def test_the_financial_plan_states_the_core_results(self):
        state = complete("shs")
        text = " ".join(" ".join(item["lines"]) for item in state["draft"]["outline"])
        self.assertIn("1,800,000", text)
        self.assertIn("360,000", text)
        self.assertIn("450,000", text)
        self.assertIn("350,000", text)
        self.assertIn("against target revenue of 1,800,000", text)

    def test_an_unbalanced_opening_balance_is_a_hard_refusal_that_blocks_export(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        state = chat.set_inputs(state, INPUTS)
        inputs = dict(BLOCKS["proforma"], opening_equity="200000")
        state = chat.compute(state, {"proforma": inputs})
        self.assertFalse(state["computations"]["proforma"]["ok"])
        self.assertIn("set opening_equity to 250000", state["computations"]["proforma"]["error"])
        state = chat.draft(state)
        self.assertTrue(any("does not balance" in item for item in state["draft"]["missing"]))
        with self.assertRaises(paper.ExportBlocked):
            chat.docx_bytes(state)


class DraftAndGate(unittest.TestCase):
    def test_a_complete_plan_drafts_without_gaps(self):
        state = complete("shs")
        self.assertEqual(state["stage"], "draft")
        self.assertEqual(state["draft"]["missing"], [])
        for heading in ("Executive Summary", "Business Description", "Market Analysis", "Marketing Plan",
                        "Operations Plan", "Management and Organisation", "Financial Plan", "Risk Analysis",
                        "Conclusion", "References"):
            self.assertIn(heading, headings(state))

    def test_no_template_text_reaches_the_plan(self):
        state = complete("shs")
        text = " ".join(" ".join(item["lines"]) for item in state["draft"]["outline"])
        for phrase in paper.META + ("{{ref:", "Not supplied yet", "add your implications"):
            self.assertNotIn(phrase, text)

    def test_the_plan_keeps_the_students_words(self):
        state = complete("shs")
        text = " ".join(" ".join(item["lines"]) for item in state["draft"]["outline"])
        self.assertIn("specialty coffee and pastries", text)
        self.assertIn("a rent increase", text)

    def test_missing_student_fields_are_named_by_the_gate(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        state = chat.set_inputs(state, {"business_name": "Bean There"})
        state = chat.compute(state, {key: value for key, value in BLOCKS.items()
                                     if key in {block["key"] for block in state["plan"]["blocks"]}})
        state = chat.draft(state)
        missing = state["draft"]["missing"]
        self.assertIn("what the business sells", missing)
        self.assertIn("at least one named risk", missing)
        with self.assertRaises(paper.ExportBlocked) as caught:
            chat.docx_bytes(state)
        self.assertIn("what the business sells", caught.exception.missing)

    def test_a_missing_core_block_blocks_export(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        state = chat.set_inputs(state, INPUTS)
        state = chat.compute(state, {"frommarket": BLOCKS["frommarket"]})
        state = chat.draft(state)
        self.assertIn("the break-even computation", state["draft"]["missing"])

    def test_a_complete_college_plan_exports_word_bytes(self):
        state = complete("college")
        self.assertEqual(state["draft"]["missing"], [])
        for heading in ("Funding and Ownership", "Social and Environmental Impact"):
            self.assertIn(heading, headings(state))
        raw = chat.docx_bytes(state)
        self.assertTrue(raw.startswith(b"PK"))
        self.assertGreater(len(raw), 5000)

    def test_the_export_gate_reports_the_missing_list_to_the_route(self):
        state = chat.confirm_plan(chat.start(BRIEF, profile="business_plan"))
        state = chat.compute(state, {})
        state = chat.draft(state)
        with self.assertRaises(paper.ExportBlocked) as caught:
            chat.docx_bytes(state)
        self.assertTrue(caught.exception.missing)

    def test_the_plan_check_passes_core_structure_and_rejects_a_heading_jump(self):
        state = complete("shs")
        self.assertTrue(paper.check(state["draft"]["outline"], state=state)["pass"])
        broken = state["draft"]["outline"][:]
        broken.insert(1, paper.section("Early H3", paper.H3, ["x"]))
        self.assertFalse(paper.check(broken, state=state)["pass"])


def _docx_bytes(*paragraphs):
    body = "".join("<w:p><w:r><w:t>%s</w:t></w:r></w:p>" % text for text in paragraphs)
    document = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
                '<w:body>%s</w:body></w:document>' % body)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


class BriefReaders(unittest.TestCase):
    def test_txt_reads_utf8_and_windows_1252(self):
        self.assertEqual(documents.extract_txt("A plan brief.".encode("utf-8"))["text"], "A plan brief.")
        self.assertEqual(documents.extract_txt("A caf\u00e9 plan.".encode("cp1252"))["text"], "A caf\u00e9 plan.")

    def test_txt_refuses_binary_and_empty_files(self):
        with self.assertRaises(documents.DocumentError):
            documents.extract_txt(b"name\x00value")
        with self.assertRaises(documents.DocumentError):
            documents.extract_txt(b"")

    def test_docx_reads_paragraphs_in_order(self):
        result = documents.extract_docx(_docx_bytes("First paragraph.", "Second paragraph."))
        self.assertEqual(result["method"], "docx_text")
        self.assertEqual(result["text"], "First paragraph.\nSecond paragraph.")

    def test_a_docx_without_a_document_part_is_refused(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("other.xml", "<x/>")
        with self.assertRaises(documents.DocumentError):
            documents.extract_docx(buffer.getvalue())

    def test_a_non_docx_is_refused(self):
        with self.assertRaises(documents.DocumentError):
            documents.extract_docx(b"not a zip")

    def test_extract_document_dispatches_by_extension(self):
        self.assertEqual(documents.extract_document(b"A plan brief.", "brief.txt")["method"], "text_file")
        self.assertEqual(documents.extract_document(_docx_bytes("A brief."), "brief.docx")["method"],
                         "docx_text")
        with self.assertRaises(documents.DocumentError):
            documents.extract_document(b"data", "brief.pptx")


class PlanRoutes(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-plan-api-test-")
        self.previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_CASES_DIR", None)
        else:
            os.environ["BP_CASES_DIR"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def _post(self, path, body=None):
        return api.handle("POST", path, body or {})

    def _start(self, level="shs"):
        status, state = self._post("/api/cases/chat", {"brief": BRIEF, "profile": "business_plan",
                                                       "subject": "entrepreneurship", "level": level})
        self.assertEqual(status, 201, state)
        return state["id"]

    def test_the_whole_plan_flows_over_the_routes(self):
        chat_id = self._start()
        status, state = self._post("/api/cases/chat/%s/plan" % chat_id)
        self.assertEqual(status, 200)
        status, state = self._post("/api/cases/chat/%s/inputs" % chat_id, {"values": INPUTS})
        self.assertEqual(status, 200, state)
        wanted = {block["key"] for block in state["plan"]["blocks"]}
        status, state = self._post("/api/cases/chat/%s/compute" % chat_id,
                                   {"blocks": {key: value for key, value in BLOCKS.items() if key in wanted}})
        self.assertEqual(status, 200, state)
        status, state = self._post("/api/cases/chat/%s/draft" % chat_id)
        self.assertEqual(status, 200, state)
        self.assertEqual(state["draft"]["missing"], [])
        status, payload = self._post("/api/cases/chat/%s/export" % chat_id)
        self.assertEqual(status, 200, payload)
        self.assertTrue(base64.b64decode(payload["data"]).startswith(b"PK"))

    def test_an_export_before_the_plan_is_complete_returns_409_with_missing(self):
        chat_id = self._start()
        self._post("/api/cases/chat/%s/plan" % chat_id)
        self._post("/api/cases/chat/%s/compute" % chat_id, {"blocks": {}})
        self._post("/api/cases/chat/%s/draft" % chat_id)
        status, payload = self._post("/api/cases/chat/%s/export" % chat_id)
        self.assertEqual(status, 409, payload)
        self.assertTrue(payload["missing"])
        self.assertIn("what the business sells", payload["missing"])

    def test_an_unbalanced_opening_balance_blocks_the_route(self):
        chat_id = self._start()
        self._post("/api/cases/chat/%s/plan" % chat_id)
        self._post("/api/cases/chat/%s/inputs" % chat_id, {"values": INPUTS})
        inputs = dict(BLOCKS["proforma"], opening_equity="200000")
        self._post("/api/cases/chat/%s/compute" % chat_id, {"blocks": {"proforma": inputs}})
        self._post("/api/cases/chat/%s/draft" % chat_id)
        status, payload = self._post("/api/cases/chat/%s/export" % chat_id)
        self.assertEqual(status, 409)
        self.assertTrue(any("does not balance" in item for item in payload["missing"]))

    def test_customise_changes_the_level_through_the_route(self):
        chat_id = self._start()
        status, state = self._post("/api/cases/chat/%s/customise" % chat_id, {"level": "college"})
        self.assertEqual(status, 200, state)
        self.assertIn("captable", [block["key"] for block in state["plan"]["blocks"]])

    def test_the_brief_route_reads_pasted_text(self):
        status, payload = self._post("/api/cases/brief", {"text": "  A coffee shop in Cebu.  "})
        self.assertEqual(status, 200)
        self.assertEqual(payload["text"], "A coffee shop in Cebu.")

    def test_the_brief_route_reads_a_txt_attachment(self):
        encoded = base64.b64encode(b"A coffee shop in Cebu City.").decode("ascii")
        status, payload = self._post("/api/cases/brief", {"filename": "brief.txt", "data": encoded})
        self.assertEqual(status, 200)
        self.assertEqual(payload["method"], "text_file")
        self.assertIn("Cebu", payload["text"])

    def test_the_brief_route_reads_a_docx_attachment(self):
        encoded = base64.b64encode(_docx_bytes("A coffee shop in Cebu City.")).decode("ascii")
        status, payload = self._post("/api/cases/brief", {"filename": "brief.docx", "data": encoded})
        self.assertEqual(status, 200)
        self.assertEqual(payload["method"], "docx_text")
        self.assertIn("Cebu", payload["text"])

    def test_the_brief_route_refuses_bad_base64_and_unknown_types(self):
        status, _ = self._post("/api/cases/brief", {"filename": "brief.txt", "data": "not base64!"})
        self.assertEqual(status, 422)
        encoded = base64.b64encode(b"data").decode("ascii")
        status, _ = self._post("/api/cases/brief", {"filename": "brief.pptx", "data": encoded})
        self.assertEqual(status, 422)


if __name__ == "__main__":
    unittest.main()
