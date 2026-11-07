"""The computation explainer is a formatter of recorded data, not an engine.

These tests hold it to the three promises the feature makes:

* every figure in the document is a recorded input or output (or a declared
  catalogue value), and no arithmetic is performed to produce one;
* a paper that carries a computation downloads as one ZIP with the paper and
  the explainer as separate files; a paper without one keeps the plain Word
  download;
* a new method without teaching notes is a named gap, never an invented
  derivation, and the gap set cannot grow silently.
"""

import base64
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
import zipfile
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import api, cases, chat_store, explain, subjects  # noqa: E402

SLICE = os.path.join(ROOT, "src", "bp", "product", "data", "explain_contracts_v0_1.json")


def breakeven_bundle():
    return {
        "id": "83c75b9cf7ad",
        "title": "How many units must we sell to break even?",
        "method": "breakeven",
        "tier": "T1",
        "spec_hash": "spec-hash",
        "outputs_hash": "output-hash",
        "created_at": "2026-10-28T10:00:00+00:00",
        "session": {
            "work_plan": {"objective": "How many units must we sell to break even?",
                          "method": "breakeven",
                          "inputs": {"fixed": {"value": "1000", "provenance": "user"},
                                     "price": {"value": "20", "provenance": "user"},
                                     "variable": {"value": "10", "provenance": "user"}}},
            "spec": {"inputs": {"fixed": {"value": "1000", "provenance": "user"},
                                "price": {"value": "20", "provenance": "user"},
                                "variable": {"value": "10", "provenance": "user"}}},
        },
        "delivery": {
            "report": "At a contribution margin of 10.00 per unit, the business breaks even at 100.00 units.",
            "appendix": {
                "tier": "T1",
                "method": {"id": "breakeven", "version": "1.0.0"},
                "tests": ["profit_at_breakeven_is_zero", "contribution_margin_is_price_minus_variable"],
                "assumptions": ["Linear cost and revenue."],
                "limitations": ["Single product; a mix needs multi_product_breakeven."],
                "artifacts": [
                    ["breakeven_units", ["breakeven_units", "annual", "entity", "base"],
                     "breakeven(inputs).breakeven_units"],
                    ["contribution_margin", ["contribution_margin", "annual", "entity", "base"],
                     "breakeven(inputs).contribution_margin"],
                ],
                "spec_hash": "spec-hash",
                "code_hash": "code-hash",
                "env_hash": "env-hash",
                "run_id": "run-1",
                "sandbox": {"isolation": "separate process"},
            },
        },
        "reperform": {
            "method": {"id": "breakeven", "version": "1.0.0"},
            "inputs": {"fixed": "1000", "price": "20", "variable": "10"},
            "outputs": {"breakeven_units": "100", "contribution_margin": "10"},
            "outputs_hash": "output-hash",
            "env_hash": "env-hash",
        },
    }


def accounting_bundle():
    return {
        "id": "a69b56457bdc",
        "title": "Prepare the management accounts for the period",
        "method": "management_accounts",
        "tier": "T2",
        "spec_hash": "spec-hash",
        "outputs_hash": "output-hash",
        "session": {"work_plan": {"objective": "Prepare the management accounts for the period",
                                  "method": "management_accounts"}},
        "delivery": {
            "report": "The engagement posts 6 entries. Net income is 1,650.00.",
            "appendix": {
                "tier": "T2",
                "method": {"id": "management_accounts", "version": "1.0.0"},
                "tests": ["trial_balance_debits_equal_credits"],
                "assumptions": ["Every entry is balanced."],
                "limitations": ["Management accounts only."],
                "accounts": {
                    "statements_export": {"trial_balance": "TRIAL BALANCE\nCash 6,650.00",
                                          "income_statement": "INCOME STATEMENT\nNet income 1,650.00"},
                    "journal_export": "JOURNAL 2026-01-01 to 2026-03-31\nCash Dr 5,000.00",
                    "t_accounts_export": {"1000": "ACCOUNT Cash\nClosing balance 6,650.00"},
                    "checks": [["trial_balance_debits_equal_credits", True, "ok"]],
                },
                "spec_hash": "spec-hash",
                "code_hash": "code-hash",
                "env_hash": "env-hash",
                "run_id": "run-2",
            },
        },
        "reperform": {
            "method": {"id": "management_accounts", "version": "1.0.0"},
            "inputs": {"spec": {"period": {"start": "2026-01-01", "end": "2026-03-31"},
                                "currency": "USD",
                                "chart": [{"code": "1000"}],
                                "entries": [{"date": "2026-01-01"}]}},
            "outputs": {"net_income": "1650"},
            "outputs_hash": "output-hash",
        },
    }


def paper_state():
    return {
        "id": "70c987992aa4",
        "format": "bp-chat/1",
        "profile": "business_plan",
        "level": "shs",
        "level_label": "Senior high school",
        "mode": "strict",
        "mode_label": "Business-plan convention",
        "brief": "A coffee shop selling specialty coffee to university students in a mid-sized city.",
        "answers": {"decision": "A coffee shop in a mid-sized city.", "style": "apa"},
        "sources": [],
        "gaps": ["Market size and growth"],
        "plan": {
            "profile": "business_plan",
            "label": "Business plan",
            "level": "shs",
            "level_label": "Senior high school",
            "mode": "strict",
            "mode_label": "Business-plan convention",
            "sections": [{"heading": "Executive Summary"}, {"heading": "Financial Plan"},
                         {"heading": "Conclusion"}],
            "blocks": [{"key": "breakeven", "label": "Break-even", "method": "breakeven",
                        "section": "financial_plan"}],
        },
        "draft": {
            "title": "Business plan: Bean There",
            "sections": [["Executive Summary", ["This plan sets out Bean There."]],
                         ["Break-even", ["At a declared fixed cost of 300,000, the break-even "
                                         "quantity is 4,615.38 units."]]],
            "outline": [{"heading": "Executive Summary", "level": 1,
                         "lines": ["This plan sets out Bean There."]},
                        {"heading": "Break-even", "level": 2,
                         "lines": ["At a declared fixed cost of 300,000, the break-even "
                                   "quantity is 4,615.38 units."]}],
        },
        "computations": {
            "breakeven": {"ok": True, "method": "breakeven",
                          "inputs": {"fixed": "300000", "price": "120", "variable": "55"},
                          "result": {"breakeven_units": "4615.384615384615384615384615",
                                     "contribution_margin": "65"}},
        },
    }


class ContractSliceTest(unittest.TestCase):
    def test_the_committed_contract_slice_matches_the_frozen_methods(self):
        from bp import methods  # test-side only

        with open(SLICE, encoding="utf-8") as stream:
            payload = json.load(stream)
        self.assertEqual(payload["format"], "bp-explain-contracts/1")
        expected = {}
        for method in methods.list_methods():
            expected[method["method_id"]] = {
                "method_id": method["method_id"],
                "version": method.get("version"),
                "tier": method.get("tier"),
                "category": method.get("category"),
                "status": method.get("status"),
                "review_status": method.get("review_status"),
                "intended_use": method.get("intended_use") or "",
                "unsupported_use": method.get("unsupported_use") or "",
                "claim_ceiling": method.get("claim_ceiling") or "",
                "assumptions": list(method.get("assumptions") or []),
                "limitations": list(method.get("limitations") or []),
                "defaults": list(method.get("defaults") or []),
                "planned_checks": list(method.get("planned_checks") or []),
                "inputs": {name: {"type": (spec or {}).get("type"),
                                  "desc": (spec or {}).get("desc") or "",
                                  "required": (spec or {}).get("required", True) is not False}
                           for name, spec in sorted((method.get("input_schema") or {}).items())},
            }
        self.assertEqual(payload["methods"], expected,
                         "run scripts/generate_explain_contracts.py: the contract slice drifted")

    def test_every_calculator_method_has_a_contract_or_a_declared_template(self):
        for info in subjects.TOOL_INFO.values():
            if info["method"] in explain.TEMPLATE_METHODS:
                continue
            self.assertIn(info["method"], explain.CONTRACTS, info["method"])

    def test_no_method_without_notes_can_appear_without_being_a_declared_gap(self):
        for key, info in subjects.TOOL_INFO.items():
            notes = subjects.STUDENT_NOTES.get(key) or {}
            if not (notes.get("formula") and notes.get("steps")):
                self.assertIn(key, explain.NOTES_GAPS,
                              "%s has no explanation notes and is not a declared gap" % key)
        self.assertEqual(len(explain.NOTES_GAPS), 10)

    def test_the_explainer_does_not_import_the_frozen_core(self):
        with open(os.path.join(ROOT, "src", "bp", "product", "explain.py"),
                  encoding="utf-8") as stream:
            source = stream.read()
        for forbidden in ("from ..methods", "from bp.methods", "import methods",
                          "from ..orchestrator", "from ..spec", "from ..sandbox"):
            self.assertNotIn(forbidden, source, "the product layer must not import the core")


class CaseExplanationTest(unittest.TestCase):
    def test_break_even_document_quotes_the_recorded_inputs_and_outputs(self):
        document = explain.case_document(breakeven_bundle())
        self.assertEqual(document["format"], "bp-explanation/1")
        self.assertEqual(document["kind"], "computation")
        text = json.dumps(document)
        for value in ("1000", "20", "10", "100"):
            self.assertIn(value, text)
        self.assertIn("Declared formula", text)
        self.assertIn("How you know it is right", text)
        self.assertIn("What was the question?", text)
        self.assertIn("What does it not prove?", text)
        # every figure is tagged with its source; no figure is untraceable
        for figure in document["figures"]:
            self.assertIn(figure["source"], ("input", "output"))
            self.assertTrue(str(figure["value"]).strip())

    def test_the_document_is_a_valid_and_deterministic_docx(self):
        document = explain.case_document(breakeven_bundle())
        first = explain.docx_bytes(document)
        second = explain.docx_bytes(document)
        self.assertEqual(first, second)
        with zipfile.ZipFile(io.BytesIO(first)) as archive:
            self.assertIn("word/document.xml", archive.namelist())
            xml = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("<w:tbl>", xml)
        self.assertIn("Break-even point", xml)

    def test_the_html_version_is_print_ready_and_escaped(self):
        document = explain.case_document(breakeven_bundle())
        page = explain.html_bytes(document).decode("utf-8")
        self.assertIn("@page", page)
        self.assertIn("<table>", page)
        self.assertIn("does not recalculate", page)

    def test_an_accounting_case_gets_the_cycle_journal_and_statements(self):
        document = explain.case_document(accounting_bundle())
        headings = [section["heading"] for section in document["sections"]]
        self.assertIn("The accounting cycle", headings)
        self.assertIn("The journal, as recorded", headings)
        self.assertIn("T-account 1000", headings)
        self.assertIn("Trial balance, as recorded", headings)
        text = json.dumps(document)
        self.assertIn("PASS: trial_balance_debits_equal_credits", text)
        self.assertIn("Cash Dr 5,000.00", text)

    def test_a_case_without_a_computation_is_refused(self):
        bundle = breakeven_bundle()
        bundle["reperform"]["outputs"] = {}
        bundle["delivery"]["appendix"]["artifacts"] = []
        self.assertFalse(explain.has_computation(bundle))
        with self.assertRaises(explain.ExplainError):
            explain.case_document(bundle)


class PaperExplanationTest(unittest.TestCase):
    def test_a_paper_with_a_computation_gets_one_companion(self):
        document = explain.paper_document(paper_state())
        self.assertEqual(document["kind"], "paper")
        self.assertIn("How this paper was solved", document["title"])
        text = json.dumps(document)
        self.assertIn("Business plan", text)
        self.assertIn("Break-even", text)
        self.assertIn("Declared formula", text)
        self.assertIn("4,615.38", text)
        self.assertIn("how the paper reports it", text)
        self.assertIn("If your professor asks", text)
        self.assertEqual(len([section for section in document["sections"]
                              if section["heading"] == "The computations at a glance"]), 1)

    def test_a_paper_without_a_delivered_computation_is_refused(self):
        state = paper_state()
        state["computations"] = {"breakeven": {"ok": False, "method": "breakeven",
                                               "inputs": {}, "error": "refused"}}
        self.assertFalse(explain.has_chat_computation(state))
        with self.assertRaises(explain.ExplainError):
            explain.paper_document(state)

    def test_the_paper_explainer_names_its_gaps(self):
        state = paper_state()
        state["gaps"] = ["Market size and growth", "Competition"]
        document = explain.paper_document(state)
        self.assertIn("Market size and growth", document["gaps"])
        self.assertIn("Competition", document["gaps"])

    def test_a_paper_without_notes_still_ships_with_a_named_gap(self):
        state = paper_state()
        state["computations"]["spearman"] = {
            "ok": True, "method": "spearman",
            "inputs": {"x": ["1", "2", "3"], "y": ["2", "4", "6"]},
            "result": {"rho": "1.0"},
        }
        state["plan"]["blocks"].append({"key": "spearman", "label": "Spearman rank correlation",
                                        "method": "spearman", "section": "financial_plan"})
        document = explain.paper_document(state)
        self.assertTrue(any("no written formula" in gap for gap in document["gaps"]))
        self.assertIn("Spearman", json.dumps(document))


class PackagingTest(unittest.TestCase):
    def test_the_zip_contains_two_named_files_and_hashes(self):
        payload, contents, name = explain.zip_pair(
            "Apple in Iran", b"paper-bytes", "docx", b"explainer-bytes", "docx")
        self.assertEqual(name, "apple-in-iran-submission.zip")
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertEqual(archive.namelist(), ["apple-in-iran.docx",
                                                  "apple-in-iran-explainer.docx"])
            self.assertEqual(archive.read("apple-in-iran.docx"), b"paper-bytes")
            self.assertEqual(archive.read("apple-in-iran-explainer.docx"), b"explainer-bytes")
        self.assertEqual([row["filename"] for row in contents],
                         ["apple-in-iran.docx", "apple-in-iran-explainer.docx"])
        self.assertTrue(all(row["sha256"] for row in contents))

    def test_a_title_with_punctuation_gets_a_safe_stem(self):
        self.assertEqual(explain.slug("Apple's Entry: Iran!"), "apple-s-entry-iran")
        self.assertEqual(explain.slug(""), "paper")


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-explain-")
        self.old_cases, self.old_state = os.environ.get("BP_CASES_DIR"), os.environ.get("BP_STATE_DIR")
        os.environ["BP_CASES_DIR"] = os.path.join(self.root, "cases")
        os.environ["BP_STATE_DIR"] = os.path.join(self.root, "state")

    def tearDown(self):
        for name, value in (("BP_CASES_DIR", self.old_cases), ("BP_STATE_DIR", self.old_state)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_case_explanation_route_returns_word_bytes(self):
        case_id = cases.save(breakeven_bundle())
        status, payload = api.handle("POST", "/api/cases/%s/explanation" % case_id, {})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["format"], "bp-explanation/1")
        self.assertTrue(zipfile.is_zipfile(io.BytesIO(base64.b64decode(payload["document"]["data"]))))
        self.assertEqual(api.handle("GET", "/api/cases/%s/explanation" % case_id)[0], 405)

    def test_a_case_without_a_computation_has_no_explanation(self):
        bundle = breakeven_bundle()
        bundle["reperform"]["outputs"] = {}
        bundle["delivery"]["appendix"]["artifacts"] = []
        case_id = cases.save(bundle)
        status, payload = api.handle("POST", "/api/cases/%s/explanation" % case_id, {})
        self.assertEqual(status, 422)
        self.assertIn("no computation", payload["error"])

    def test_a_case_download_with_a_computation_is_a_zip(self):
        case_id = cases.save(breakeven_bundle())
        status, payload = api.handle("POST", "/api/cases/%s/export" % case_id,
                                     {"kind": "docx", "deliverable": "submission", "download": True})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["mime"], "application/zip")
        self.assertEqual([row["filename"] for row in payload["contents"]],
                         ["how-many-units-must-we-sell-to-break-even.docx",
                          "how-many-units-must-we-sell-to-break-even-explainer.docx"])
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(payload["data"]))) as archive:
            self.assertEqual(len(archive.namelist()), 2)

    def test_a_chat_paper_with_a_computation_is_a_zip(self):
        state = chat_store.save(paper_state())
        with mock.patch("bp.product.chat.docx_bytes", return_value=b"paper-bytes"):
            status, payload = api.handle("POST", "/api/cases/chat/%s/export" % state["id"], {})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["mime"], "application/zip")
        self.assertEqual(payload["contents"][1]["filename"], "business-plan-bean-there-explainer.docx")

    def test_a_chat_paper_without_a_computation_keeps_the_word_download(self):
        state = paper_state()
        state["computations"] = {}
        state = chat_store.save(state)
        with mock.patch("bp.product.chat.docx_bytes", return_value=b"paper-bytes"):
            status, payload = api.handle("POST", "/api/cases/chat/%s/export" % state["id"], {})
        self.assertEqual(status, 200, payload)
        self.assertEqual(payload["mime"],
                         "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.assertNotIn("contents", payload)

    def test_a_blocked_paper_produces_no_partial_zip(self):
        state = chat_store.save(paper_state())
        from bp.product import chat
        with mock.patch("bp.product.chat.docx_bytes",
                        side_effect=chat.ExportBlocked(["implications"])):
            status, payload = api.handle("POST", "/api/cases/chat/%s/export" % state["id"], {})
        self.assertEqual(status, 409)
        self.assertEqual(payload["missing"], ["implications"])


class ServedUiTest(unittest.TestCase):
    def test_the_page_offers_the_explainer_and_explains_the_zip(self):
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            page = stream.read()
        for present in ("Download the explanation", "Download the explainer",
                        "hasComputation", "Paper and explainer downloaded",
                        "Plan and explainer downloaded", "Word + explainer",
                        "A paper with a computation downloads as a ZIP with its explainer.",
                        "/explanation"):
            self.assertIn(present, page)


if __name__ == "__main__":
    unittest.main()
