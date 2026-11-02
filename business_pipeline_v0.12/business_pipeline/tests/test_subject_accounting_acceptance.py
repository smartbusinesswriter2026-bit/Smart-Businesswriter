"""Acceptance suite for the Accounting shelf — one test per row of `qa/manual/accounting.md`.

The manual is the specification: every `E-acc-nnn` row names a test below, and the
traceability matrix in §9 of the manual records its status.  Nothing here is a new
requirement: each expectation is traced to `bp.methods.LIBRARY`, the shipped catalogue,
the student guide or the paper rules, and the source is cited in the manual.

Rules this file keeps:
  * offline — no provider key, no network, no model call;
  * it asserts the frozen core's behaviour and the product's formatting of it, and it
    never edits an expected value to go green;
  * a refusal is a refusal: a test that expects a block asserts the *reason* too.

Run:  PYTHONPATH=src python -m pytest tests/test_subject_accounting_acceptance.py -q
"""

import copy
import json
import os
import re
import sys
import tempfile
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import methods, server                      # noqa: E402
from bp.orchestrator import Pipeline                # noqa: E402
from bp.product import api, chat, deliverables, subjects  # noqa: E402
from bp.session import SessionManager               # noqa: E402

TOOLS = ["accounts", "tbcheck", "ratios", "scv", "abc", "salesvar", "breakeven",
         "multibreakeven", "workingcapital", "loan", "trendanalysis", "tax"]
METHODS = ["management_accounts", "trial_balance_check", "ratio_analysis",
           "standard_cost_variances", "abc_costing", "sales_variances", "breakeven",
           "multi_product_breakeven", "working_capital", "loan_amortization",
           "trend_analysis", "tax_declared"]
GROUPS = {"Bookkeeping and statements", "Cost and variance analysis",
          "Working capital and financing", "Tax and reporting"}
GUIDE = os.path.join(ROOT, "docs", "ACCOUNTING_STUDENT_GUIDE.md")


def page():
    return subjects.detail("accounting")


def tool(key):
    return next(item for item in page()["tools"] if item["key"] == key)


def preset(key):
    return copy.deepcopy(server.PRESETS[tool(key)["preset"]])


def deliver(key, inputs=None):
    """Run one accounting preset through the real pipeline; return the delivery."""
    request = preset(key)
    if inputs is not None:
        request["inputs"] = inputs
    return Pipeline().run(request, lambda stage: True)


def number(value):
    return Decimal(str(value))


#: The student guide's miniature engagement (§1), as the student would declare it.
MINIATURE = {
    "period": {"start": "2026-01-01", "end": "2026-01-31"},
    "currency": "USD",
    "framework": "local",
    "places": 2,
    "chart": [
        {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"},
        {"code": "1100", "name": "Inventory", "type": "asset", "line": "Inventory"},
        {"code": "2000", "name": "Trade payables", "type": "liability", "line": "Payables"},
        {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital",
         "role": "capital"},
        {"code": "3100", "name": "Retained earnings", "type": "equity",
         "line": "Retained earnings", "role": "retained_earnings"},
        {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
        {"code": "5000", "name": "Cost of sales", "type": "expense", "line": "Cost of sales"},
    ],
    "prior_closing": {},
    "opening": [],
    "entries": [
        {"date": "2026-01-02", "description": "owner investment",
         "lines": [{"account": "1000", "debit": "50000"},
                   {"account": "3000", "credit": "50000"}]},
        {"date": "2026-01-03", "description": "stock on credit",
         "lines": [{"account": "1100", "debit": "20000"},
                   {"account": "2000", "credit": "20000"}]},
        {"date": "2026-01-04", "description": "cash sale",
         "lines": [{"account": "1000", "debit": "15000"},
                   {"account": "4000", "credit": "15000"}]},
        {"date": "2026-01-04", "description": "cost of the goods sold",
         "lines": [{"account": "5000", "debit": "9000"},
                   {"account": "1100", "credit": "9000"}]},
    ],
    "schedules": [],
    "policy_changes": [],
}

def trial_balance_totals(spec):
    """The pre-closing trial balance, recomputed from the journal alone.

    This is the independent route to the guide's "debits and credits both 85,000":
    each account's balance is debits minus credits, and a non-zero balance is placed
    on the side its sign puts it.  No engine value is read.
    """
    debits, credits = {}, {}
    for entry in spec["entries"]:
        for line in entry["lines"]:
            code = line["account"]
            debits[code] = debits.get(code, Decimal(0)) + number(line.get("debit") or "0")
            credits[code] = credits.get(code, Decimal(0)) + number(line.get("credit") or "0")
    debit_total, credit_total = Decimal(0), Decimal(0)
    for code in set(debits) | set(credits):
        balance = debits.get(code, Decimal(0)) - credits.get(code, Decimal(0))
        if balance > 0:
            debit_total += balance
        elif balance < 0:
            credit_total += -balance
    return debit_total, credit_total


def _run_method(method_id, inputs):
    """Attach the frozen core the way the server does, for the draft's computations."""
    method = methods.LIBRARY[method_id]
    errors = methods.validate_inputs(method, inputs)
    if errors:
        raise ValueError("; ".join(errors))
    return method.impl(inputs)


def setUpModule():
    api.attach_compute(lambda values: methods.breakeven(values))
    api.attach_methods(_run_method, methods.describe)


def answer_all(state):
    """Answer the question bank the way a student would: first option each time."""
    for _ in range(60):
        question = chat.current_question(state)
        if not question:
            break
        if question["type"] == "choice":
            first = question["choices"][0]
            value = first[0] if isinstance(first, (list, tuple)) else first
        elif question["type"] == "number":
            value = "5"
        elif question["type"] == "items":
            value = "one; two"
        else:
            value = "the board decision"
        state = chat.answer(state, question["id"], value)
    return state


def draftable(state):
    """Skip the network: the paper is drafted from no accepted evidence."""
    state["stage"] = "evidence"
    state["evidence"] = []
    state["gaps"] = []
    state = chat.confirm_plan(state) if state.get("stage") == "plan" else state
    return state


WORKING_CAPITAL_BRIEF = (
    "The grocery chain is entering the Saudi market and the working capital cycle is the question, "
    "with inventory and receivables declared.")
TREND_BRIEF = (
    "The grocery chain is entering the Saudi market and the four declared years of figures need "
    "reading as common-size and trend.")
WORKING_CAPITAL_INPUTS = {
    "revenue": "1200000", "cost_of_sales": "800000", "inventory": "100000",
    "receivables": "150000", "payables": "90000", "annual_demand": "24000",
    "order_cost": "50", "holding_cost_per_unit": "2", "discount_percent": "0.02",
    "credit_terms_days": "40", "discount_days": "10"}
TREND_INPUTS = {
    "years": ["2022", "2023", "2024"],
    "revenue": ["1000000", "1200000", "1500000"],
    "cost_of_sales": ["600000", "700000", "850000"],
    "operating_expenses": ["200000", "250000", "300000"],
    "net_income": ["100000", "160000", "230000"]}
LONG_DECIMAL = re.compile(r"\d+\.\d{6,}")


def paper_section(brief, key, inputs, heading):
    state = draftable(answer_all(chat.start(brief, "management", "pestel")))
    chat.attach_computation(state, key, inputs)
    state = chat.draft(state, accepted_ids=[],
                       implications="The declared figures set the position.")
    rows = [row for row in state["draft"]["outline"] if row.get("heading") == heading]
    assert rows, "the paper has no %r section: %s" % (
        heading, [row.get("heading") for row in state["draft"]["outline"]])
    return " ".join(rows[0].get("lines") or []), state



class ShelfShapeTest(unittest.TestCase):
    """E-acc-001, 002, 011..014, 017..019 — the catalogue promise."""

    def test_E_acc_001__shelf_declares_twelve_tools(self):
        detail = page()
        self.assertEqual([item["key"] for item in detail["tools"]], TOOLS)
        self.assertEqual({item["method"] for item in detail["tools"]}, set(METHODS))
        self.assertTrue(all(item["kind"] == "compute" for item in detail["tools"]),
                        "every accounting tile must be a compute tool")
        self.assertEqual(len({item["method"] for item in detail["tools"]}), 12,
                         "two tools must not launch the same method")

    def test_E_acc_002__no_worksheets_theories_or_tiles(self):
        detail = page()
        definition = subjects._subject_definition("accounting")
        self.assertEqual(definition["worksheets"], [])
        self.assertEqual(detail["worksheets"], [])
        self.assertEqual(detail["theories"], [])
        self.assertEqual(detail["tiles"], [],
                         "the shelf declares no tiles; the page groups the tools instead")
        self.assertEqual({item["group"] for item in detail["tools"]}, GROUPS)

    def test_E_acc_011__tool_notes_and_related_ids_resolve(self):
        known = {item["key"] for item in subjects.compute_tools()}
        for item in page()["tools"]:
            with self.subTest(tool=item["key"]):
                self.assertTrue(item["level"], "a tool with no level")
                self.assertTrue(item["formula"], "a tool with no formula")
                self.assertTrue(item["steps"], "a tool with no steps")
                self.assertTrue(item["common_mistakes"], "a tool with no common mistakes")
                self.assertTrue(item["related"], "a tool with no related tools")
                for related in item["related"]:
                    self.assertIn(related, known,
                                  "%s points at %r, which is not a calculator tool"
                                  % (item["key"], related))
                self.assertNotIn(item["key"], item["related"],
                                 "a tool must not list itself as related")

    def test_E_acc_012__every_tool_has_one_group_and_one_period(self):
        for item in page()["tools"]:
            with self.subTest(tool=item["key"]):
                self.assertIn(item["group"], GROUPS)
                self.assertTrue(item["period"], "a tool with no period badge")
        for group in GROUPS:
            members = [item["key"] for item in page()["tools"] if item["group"] == group]
            self.assertTrue(members, "group %r is declared but empty" % group)

    def test_E_acc_013__calculator_reaches_the_same_twelve_methods(self):
        groups = subjects.calculator_groups()
        accounting = next(row for row in groups["groups"] if row["id"] == "accounting")
        self.assertEqual({item["method"] for item in accounting["tools"]}, set(METHODS))
        union = {item["method"] for item in subjects.compute_tools()}
        self.assertEqual(union, {item["method"] for row in groups["groups"]
                                 for item in row["tools"]},
                         "the calculator union must equal the subjects' compute tools")

    def test_E_acc_014__subject_route_serves_the_shelf_and_computes_nothing(self):
        status, detail = api.handle("GET", "/api/cases/subjects/accounting")
        self.assertEqual(status, 200)
        self.assertEqual(detail["id"], "accounting")
        self.assertEqual(len(detail["tools"]), 12)
        self.assertEqual(detail["worksheets"], [])
        self.assertEqual(len(detail["records"]), 3)
        self.assertEqual(len(detail["glossary"]), 19)
        self.assertIsNone(detail.get("delivery"),
                          "the subject page must never carry a computed delivery")
        self.assertEqual(api.handle("POST", "/api/cases/subjects/accounting", {})[0], 405)

    def test_E_acc_017__guidance_start_steps_and_does_not_are_present(self):
        detail = page()
        self.assertTrue(detail["summary"])
        self.assertTrue(detail["guidance"])
        self.assertGreaterEqual(len(detail["start_steps"]), 3)
        self.assertGreaterEqual(len(detail["does_not"]), 2)
        for step in detail["start_steps"]:
            self.assertGreater(len(step), 20,
                               "a start step must be a sentence a student can act on")
        self.assertTrue(any("tax" in line.lower() for line in detail["does_not"]),
                        "the declared non-goal about tax must survive")

    def test_E_acc_018__missing_need_text_falls_back_and_is_ledgered(self):
        """GAP G-acc-01: the shelf declares no `need` text, so the card must not print null."""
        for item in page()["tools"]:
            self.assertIsNone(item["need"],
                              "if accounting gains `need` text, update GAP G-acc-01 and this row")
        with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
            html = stream.read()
        self.assertIn("Gather the figures this calculation needs", html,
                      "the figures panel needs a generic fallback for a tool with no `need`")
        self.assertIn("(tile.need)", html)

    def test_E_acc_019__opening_a_tool_loads_its_own_preset(self):
        for key in TOOLS:
            with self.subTest(tool=key):
                item = tool(key)
                self.assertIn(item["preset"], server.PRESETS)
                loaded = server.PRESETS[item["preset"]]
                self.assertEqual(loaded["method"], item["method"])
                self.assertTrue(loaded["objective"], "a preset with no objective")


class ContractTest(unittest.TestCase):
    """E-acc-003, 004, 005, 015, 016, 050 — the contract and the catalogue's claims."""

    def test_E_acc_003__every_method_declares_its_full_contract(self):
        for method_id in METHODS:
            with self.subTest(method=method_id):
                method = methods.LIBRARY[method_id]
                self.assertTrue(method.intended_use, "no intended_use")
                self.assertTrue(method.unsupported_use, "no unsupported_use")
                self.assertTrue(method.assumptions, "no assumptions")
                self.assertTrue(method.limitations, "no limitations")
                self.assertTrue(method.test_names, "no test names")
                self.assertEqual(len(method.test_names), len(set(method.test_names)),
                                 "duplicate test names")
                self.assertTrue(method.metric)
                self.assertTrue(method.unit)
                self.assertIn(method.tier, ("T1", "T2", "T3", "T4"))
                self.assertIn(method.claim_ceiling,
                              ("descriptive", "associational", "predictive"))
                self.assertEqual(method.claim_ceiling, "descriptive",
                                 "no accounting method may claim more than description")
                self.assertTrue(method.input_schema)
                for name, spec in method.input_schema.items():
                    self.assertIn("type", spec, "%s.%s has no type" % (method_id, name))
                    self.assertTrue(spec.get("desc"), "%s.%s has no description"
                                    % (method_id, name))

    def test_E_acc_004__preset_launches_the_claimed_method_with_valid_inputs(self):
        for key in TOOLS:
            with self.subTest(tool=key):
                request = preset(key)
                item = tool(key)
                self.assertEqual(request["method"], item["method"])
                errors = methods.validate_inputs(methods.LIBRARY[item["method"]],
                                                 request["inputs"])
                self.assertEqual(errors, [], "the shipped preset must pass the schema")
                profile = methods.LIBRARY[item["method"]].profile
                if profile is not None:
                    self.assertEqual(profile(request["inputs"]), [],
                                     "the shipped preset must not be blocked by its profile")

    def test_E_acc_005__every_guide_assignment_maps_to_a_tool(self):
        with open(GUIDE, encoding="utf-8") as stream:
            text = stream.read()
        section = text.split("## Your assignment requirement", 1)[1]
        section = section.split("## Worked examples", 1)[0]
        named = set(re.findall(r"`([a-z_]+)`", section))
        self.assertGreaterEqual(len(named), 10,
                                "the guide's requirement table must name the tools")
        self.assertEqual(named - set(METHODS), set(),
                         "the guide names something this shelf does not launch")

    def test_E_acc_015__records_claim_only_what_is_built(self):
        rows = page()["records"]
        self.assertEqual([row["id"] for row in rows],
                         ["QNT-FIN-02", "QNT-FIN-03", "QNT-FIN-05"])
        for row in rows:
            with self.subTest(record=row["id"]):
                self.assertEqual(row["form"], "computed",
                                 "a computed record must not be shown as a worksheet")
                self.assertTrue(row["linked_methods"], "a computed record with no method")
                for method_id in row["linked_methods"]:
                    self.assertIn(method_id, methods.LIBRARY,
                                  "%s links an unbuilt method %r" % (row["id"], method_id))
                self.assertIn("not implemented", row["implementation_status"],
                              "the partial claim must name what is missing")

    def test_E_acc_016__glossary_is_complete_and_definition_only(self):
        glossary = page()["glossary"]
        self.assertEqual(len(glossary), 19)
        terms = [row["term"] for row in glossary]
        self.assertEqual(len(terms), len(set(terms)), "a glossary term is listed twice")
        for row in glossary:
            with self.subTest(term=row["term"]):
                self.assertTrue(row["term"].strip())
                self.assertGreater(len(row["definition"]), 20)
                self.assertIsNone(re.search(r"\d", row["definition"]),
                                  "a definition must not carry a computed number")

    def test_E_acc_050__guide_catalogue_and_limitations_agree(self):
        with open(GUIDE, encoding="utf-8") as stream:
            guide = stream.read()
        self.assertIn("No jurisdiction tax rules", guide)
        self.assertIn("no group consolidation", guide)
        self.assertIn("no budget, planning or idle-capacity variances", guide)
        status = " ".join(row["implementation_status"] for row in page()["records"])
        self.assertIn("target", status)
        self.assertIn("are not implemented", status)
        with open(os.path.join(ROOT, "docs", "PRODUCT_GAP_MAP.md"), encoding="utf-8") as stream:
            gap_map = stream.read()
        self.assertIn("Accounting: books, statements, ratios, costing, variances and declared tax",
                      gap_map)
        self.assertIn("**Built**", gap_map.split("Accounting: books", 1)[1][:400],
                      "the gap map must not describe built accounting tools as absent")


class RunPathTest(unittest.TestCase):
    """E-acc-006..010, 045 — the product path every accounting tool runs on."""

    def test_E_acc_006__same_inputs_same_report_and_hash(self):
        for key in ("accounts", "ratios", "scv", "abc", "salesvar", "workingcapital",
                    "loan", "trendanalysis", "tax", "breakeven"):
            with self.subTest(tool=key):
                first, second = deliver(key), deliver(key)
                self.assertEqual(first.status, "delivered", first.blocked_reason)
                self.assertEqual(second.status, "delivered", second.blocked_reason)
                self.assertEqual(first.report, second.report,
                                 "the same declared inputs must produce the same report")
                self.assertEqual(first.appendix["spec_hash"], second.appendix["spec_hash"])
                json.dumps(first.appendix, sort_keys=True, default=str)

    def test_E_acc_007__session_plans_then_delivers_and_serialises(self):
        session = SessionManager().create(preset("ratios"))
        planned = session.to_dict()
        self.assertEqual(planned["status"], "awaiting_confirmation")
        self.assertIsNone(planned["delivery"], "nothing may be computed before confirmation")
        self.assertEqual(planned["work_plan"]["planned_checks"],
                         list(methods.LIBRARY["ratio_analysis"].test_names))
        self.assertIsNone(planned["spec"]["hash"], "the spec hash is frozen only after confirm")
        session.confirm(True)
        delivered = session.to_dict()
        self.assertEqual(delivered["status"], "delivered")
        self.assertTrue(delivered["spec"]["hash"])
        json.dumps(delivered)                       # fully serialisable, no Decimal left

        # The engagement has a second mandatory checkpoint: nothing is posted until
        # the account mapping is confirmed.
        engagement = SessionManager().create(preset("accounts"))
        engagement.confirm(True)
        self.assertEqual(engagement.to_dict()["status"], "awaiting_mapping_confirmation")
        self.assertIsNone(engagement.to_dict()["delivery"],
                          "nothing may be posted before the mapping is confirmed")
        engagement.confirm(True)
        self.assertEqual(engagement.to_dict()["status"], "delivered")

    def test_E_acc_008__rejecting_the_plan_blocks_and_marks_the_rest_not_run(self):
        session = SessionManager().create(preset("tax"))
        session.confirm(False)
        state = session.to_dict()
        self.assertEqual(state["stage_states"]["formalization"], "blocked")
        self.assertEqual(state["stage_states"]["execution"], "not_run")
        with self.assertRaises(ValueError):
            session.confirm(True)

    def test_E_acc_009__bad_input_is_refused_never_coerced(self):
        request = preset("breakeven")
        request["inputs"] = {"fixed": "1000", "price": "20", "variable": "10", "nonsense": "1"}
        refused = Pipeline().run(request, lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertIn("unknown input 'nonsense'", refused.blocked_reason)

        floats = preset("breakeven")
        floats["inputs"] = {"fixed": 1000.0, "price": "20", "variable": "10"}
        refused = Pipeline().run(floats, lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertIn("binary float", refused.blocked_reason)

        missing = preset("breakeven")
        missing["inputs"] = {"fixed": "1000", "price": "20"}
        refused = Pipeline().run(missing, lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertIn("variable", refused.blocked_reason)

        # The product's own planning route must only ever name a method that exists.
        status, plan = api.handle("POST", "/api/cases/calculator/plan",
                                  {"text": "how many units must we sell to break even"})
        self.assertEqual(status, 200)
        self.assertEqual(plan["method"], "breakeven")
        for row in [plan] + list(plan.get("alternatives") or []):
            method_id = row.get("method") if isinstance(row, dict) else None
            if method_id:
                self.assertIn(method_id, methods.LIBRARY,
                              "the plan proposed an unbuilt method %r" % method_id)

    def test_E_acc_010__delivered_report_is_honest_and_licensed(self):
        for key in TOOLS:
            with self.subTest(tool=key):
                result = deliver(key)
                self.assertEqual(result.status, "delivered", result.blocked_reason)
                self.assertEqual(result.appendix["method"]["id"], tool(key)["method"])
                self.assertTrue(result.appendix["tests"], "no declared check was recorded")
                self.assertTrue(result.appendix["limitations"])
                for field in ("missing_data", "multiple_comparisons", "power",
                              "weights_and_clusters"):
                    self.assertIn(field, result.appendix["honesty"],
                                  "the honesty block must name every disclosure")
                    self.assertNotEqual(result.appendix["honesty"][field], "",
                                        "a non-applicable disclosure says so, never blank")
                self.assertNotIn("{{", result.report,
                                 "an unresolved template token reached the report")
                lowered = result.report.lower()
                for overclaim in ("will increase", "proves that", "causes"):
                    self.assertNotIn(overclaim, lowered,
                                     "a descriptive method must not license causation")

    def test_E_acc_045__deliverables_carry_the_numbers_and_refuse_presentation(self):
        delivery = deliver("accounts")
        self.assertEqual(delivery.status, "delivered", delivery.blocked_reason)
        bundle = {"id": "acc-acceptance", "title": "Accounting acceptance case",
                  "delivery": {"status": delivery.status, "report": delivery.report,
                               "appendix": delivery.appendix}}
        root = tempfile.mkdtemp(prefix="bp-acc-export-")
        for profile, fmt, suffix in (("submission", "docx", "docx"),
                                     ("submission", "html", "html"),
                                     ("workpapers", "xlsx", "xlsx"),
                                     ("workpapers", "csv", "csv")):
            with self.subTest(profile=profile, fmt=fmt):
                destination = os.path.join(root, "%s-%s.%s" % (profile, fmt, suffix))
                result = deliverables.write_export(bundle, profile, fmt, destination)
                self.assertTrue(os.path.isfile(destination))
                self.assertGreater(os.path.getsize(destination), 0)
                self.assertEqual(result["deliverable"], profile)
        with self.assertRaises(deliverables.DeliverableError) as refused:
            deliverables.check_pair("presentation", "docx")
        self.assertIn("PowerPoint renderer is not built", str(refused.exception))


class ToolBehaviourTest(unittest.TestCase):
    """E-acc-020..042 — what each accounting tool refuses and what it recomputes to."""

    def test_E_acc_020__unbalanced_trial_balance_reports_the_difference_never_plugs(self):
        from bp import check
        inputs = copy.deepcopy(server.PRESETS["tbcheck"]["inputs"])
        inputs["trial_balance"][0]["debit"] = "1600"
        before = copy.deepcopy(inputs["trial_balance"])
        report = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertIn("does not balance", report["verdict"])
        self.assertEqual(number(report["amounts"]["submitted_balance_difference"]), number("100"))
        self.assertTrue(report["findings"])
        self.assertEqual(inputs["trial_balance"], before,
                         "the check must never write a plug into the student's trial balance")
        self.assertNotIn("plug", json.dumps(report, default=str).lower())

    def test_E_acc_021__balanced_but_wrong_trial_balance_is_located(self):
        from bp import check
        inputs = copy.deepcopy(server.PRESETS["tbcheck"]["inputs"])
        inputs["trial_balance"][0]["debit"] = "1600"
        inputs["trial_balance"][1]["credit"] = "1600"
        report = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertEqual(report["counts"]["n_differing"], 2)
        self.assertIn("cannot tell you which one is wrong", report["verdict"])
        self.assertTrue(any(item["kind"] == "amount-differs" for item in report["findings"]))

    def test_E_acc_022__trial_balance_refuses_duplicates_negatives_and_precision(self):
        from bp import check
        with self.assertRaises(check.CheckError) as refused:
            check.compare(None, [{"name": "Cash", "debit": "10"},
                                 {"name": "cash", "debit": "20"}], 2)
        self.assertIn("more than once", str(refused.exception))
        with self.assertRaises(check.CheckError):
            check.compare(None, [{"code": "1000", "debit": "-5"}], 2)
        with self.assertRaises(check.CheckError):
            check.compare(None, [{"code": "1000", "debit": "1.234"}], 2)
        with self.assertRaises(check.CheckError):
            check.compare(None, None, 2)

    def test_E_acc_023__unbalanced_entry_is_refused(self):
        request = preset("accounts")
        request["inputs"]["spec"]["entries"].append(
            {"date": "2026-01-05", "description": "one-sided entry",
             "lines": [{"account": "1000", "debit": "10"}]})
        refused = Pipeline().run(request, lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertIn("an entry needs at least two lines", refused.blocked_reason)

    def test_E_acc_024__statements_balance_and_both_cash_routes_agree(self):
        result = deliver("accounts")
        self.assertEqual(result.status, "delivered", result.blocked_reason)
        accounts = result.appendix["accounts"]
        statements = accounts["statements"]
        self.assertEqual(number(statements["total_assets"]),
                         number(statements["total_liabilities"])
                         + number(statements["equity_with_current_earnings"]))
        cash_flow = accounts["cash_flow"]
        self.assertEqual(number(cash_flow["net_direct"]), number(cash_flow["net_indirect"]))
        names = [row[0] for row in accounts["checks"]]
        self.assertIn("retained_earnings_rollforward", names)
        self.assertTrue(all(row[1] for row in accounts["checks"]), accounts["checks"])

    def test_E_acc_025__opening_balance_must_equal_prior_closing(self):
        request = preset("accounts")
        request["inputs"]["spec"]["prior_closing"] = {"1000": "2000", "3000": "2000"}
        refused = Pipeline().run(request, lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertIn("opening_balances_equal_prior_closing", refused.blocked_reason)

    def test_E_acc_026__net_margin_matches_an_independent_recomputation(self):
        figures = copy.deepcopy(server.PRESETS["ratios"]["inputs"])
        expected = number(figures["net_income"]) / number(figures["revenue"])
        out = methods.LIBRARY["ratio_analysis"].impl(figures)
        self.assertLessEqual(abs(number(out["net_margin"]) - expected), Decimal("1e-9"),
                             "net margin %s vs independent %s" % (out["net_margin"], expected))
        self.assertEqual(out["current_ratio"],
                         number(figures["current_assets"]) / number(figures["current_liabilities"]))
        self.assertEqual(out["quick_ratio"],
                         (number(figures["current_assets"]) - number(figures["inventory"]))
                         / number(figures["current_liabilities"]))
        delivered = deliver("ratios")
        self.assertEqual(delivered.status, "delivered", delivered.blocked_reason)

    def test_E_acc_027__zero_denominator_is_removed_with_a_reason(self):
        figures = copy.deepcopy(server.PRESETS["ratios"]["inputs"])
        figures["revenue"] = "0"
        out = methods.LIBRARY["ratio_analysis"].impl(figures)
        for name in ("gross_margin", "operating_margin", "net_margin", "receivables_days"):
            self.assertNotIn(name, out, "%s must not be computed off a zero denominator" % name)
        reasons = {row["ratio"]: row["reason"] for row in out["_appendix"]["not_computed"]}
        self.assertIn("zero denominator: revenue", reasons["net_margin"])
        dumped = json.dumps(out, default=str)
        self.assertNotIn("Infinity", dumped)
        self.assertNotIn("NaN", dumped)

    def test_E_acc_028__ratios_make_no_benchmark_claim(self):
        result = deliver("ratios")
        self.assertEqual(result.status, "delivered", result.blocked_reason)
        self.assertIn("no benchmark", result.report)
        out = methods.LIBRARY["ratio_analysis"].impl(
            copy.deepcopy(server.PRESETS["ratios"]["inputs"]))
        for row in out["_appendix"]["ratios"]:
            dumped = json.dumps(row, default=str).lower()
            self.assertNotIn("benchmark", dumped)
            self.assertNotIn("industry average", dumped)

    def test_E_acc_029__variances_match_the_guide_example(self):
        out = methods.LIBRARY["standard_cost_variances"].impl(
            copy.deepcopy(server.PRESETS["scv"]["inputs"]))
        expected = {"material_price_variance": "4900", "material_usage_variance": "3000",
                    "labour_rate_variance": "7300", "labour_efficiency_variance": "4000",
                    "variable_overhead_spending_variance": "-3000",
                    "variable_overhead_efficiency_variance": "1000",
                    "fixed_overhead_spending_variance": "5000",
                    "fixed_overhead_volume_variance": "24000",
                    "total_variance": "46200"}
        for name, value in expected.items():
            with self.subTest(variance=name):
                self.assertEqual(number(out[name]), number(value),
                                 "the student guide's worked example must reproduce")
        self.assertGreater(out["total_variance"], Decimal(0),
                           "a positive total here is unfavourable")

    def test_E_acc_030__overhead_variances_only_when_declared_and_total_foots(self):
        base = {key: value for key, value in server.PRESETS["scv"]["inputs"].items()
                if not key.startswith(("standard_variable_overhead", "actual_variable_overhead",
                                       "budgeted_fixed_overhead", "actual_fixed_overhead",
                                       "denominator_hours"))}
        core_only = methods.LIBRARY["standard_cost_variances"].impl(copy.deepcopy(base))
        self.assertNotIn("variable_overhead_spending_variance", core_only)
        self.assertNotIn("fixed_overhead_volume_variance", core_only)
        self.assertEqual(core_only["total_variance"],
                         core_only["material_price_variance"] + core_only["material_usage_variance"]
                         + core_only["labour_rate_variance"] + core_only["labour_efficiency_variance"])
        full = methods.LIBRARY["standard_cost_variances"].impl(
            copy.deepcopy(server.PRESETS["scv"]["inputs"]))
        reported = [full[key] for key in
                    ("material_price_variance", "material_usage_variance",
                     "labour_rate_variance", "labour_efficiency_variance",
                     "variable_overhead_spending_variance",
                     "variable_overhead_efficiency_variance",
                     "fixed_overhead_spending_variance", "fixed_overhead_volume_variance")]
        self.assertEqual(full["total_variance"], sum(reported, Decimal(0)))

    def test_E_acc_031__abc_allocates_exactly_the_pools(self):
        out = methods.LIBRARY["abc_costing"].impl({
            "activities": [{"name": "setup", "pool_cost": "50000"},
                           {"name": "inspection", "pool_cost": "30000"}],
            "products": [{"name": "X", "units": "1000"}, {"name": "Y", "units": "500"}],
            "allocations": [
                {"activity": "setup", "product": "X", "driver_quantity": "40"},
                {"activity": "setup", "product": "Y", "driver_quantity": "60"},
                {"activity": "inspection", "product": "X", "driver_quantity": "20"},
                {"activity": "inspection", "product": "Y", "driver_quantity": "10"}]})
        self.assertEqual(number(out["rate_setup"]), number("500"))
        self.assertEqual(number(out["rate_inspection"]), number("1000"))
        self.assertEqual(number(out["allocated_X"]), number("40000"))
        self.assertEqual(number(out["unit_cost_X"]), number("40"))
        self.assertEqual(number(out["allocated_Y"]), number("40000"))
        self.assertEqual(number(out["unit_cost_Y"]), number("80"))
        self.assertEqual(number(out["total_allocated"]), number(out["total_pool_cost"]))

    def test_E_acc_032__abc_refuses_a_pool_with_no_driver(self):
        inputs = {"activities": [{"name": "setup", "pool_cost": "50000"},
                                 {"name": "inspection", "pool_cost": "30000"}],
                  "products": [{"name": "X", "units": "1000"}],
                  "allocations": [{"activity": "setup", "product": "X",
                                   "driver_quantity": "40"}]}
        self.assertIn("activity inspection has no driver quantity to allocate against",
                      methods.LIBRARY["abc_costing"].profile(inputs))
        refused = Pipeline().run({"objective": "x", "method": "abc_costing", "inputs": inputs},
                                 lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertIn("no driver quantity", refused.blocked_reason)

    def test_E_acc_033__price_mix_yield_reconcile_to_the_total(self):
        out = methods.LIBRARY["sales_variances"].impl({
            "products": [{"name": "X", "budget_units": "100", "budget_price": "10",
                          "actual_units": "120", "actual_price": "11"},
                         {"name": "Y", "budget_units": "100", "budget_price": "20",
                          "actual_units": "80", "actual_price": "18"}]})
        self.assertEqual(number(out["total_sales_variance"]), number("-240"))
        self.assertEqual(number(out["price_variance"]), number("-40"))
        self.assertEqual(number(out["mix_variance"]), number("-200"))
        self.assertEqual(number(out["yield_variance"]), number("0"))
        self.assertEqual(out["price_variance"] + out["mix_variance"] + out["yield_variance"],
                         out["total_sales_variance"])
        self.assertEqual(out["variance_check"], out["total_sales_variance"])

    def test_E_acc_034__breakeven_refuses_price_at_or_below_variable_cost(self):
        for price in ("10", "5"):
            with self.subTest(price=price):
                self.assertTrue(methods.LIBRARY["breakeven"].profile(
                    {"fixed": "1000", "price": price, "variable": "10"}))
                with self.assertRaises(methods.DataError) as refused:
                    methods.LIBRARY["breakeven"].impl(
                        {"fixed": "1000", "price": price, "variable": "10"})
                self.assertIn("price must exceed variable cost", str(refused.exception))
        refused = Pipeline().run({"objective": "x", "method": "breakeven",
                                  "inputs": {"fixed": "1000", "price": "10", "variable": "10"}},
                                 lambda stage: True)
        self.assertEqual(refused.status, "blocked")
        self.assertNotIn("breakeven_units", json.dumps(refused.appendix, default=str))

    def test_E_acc_035__breakeven_units_and_margin_of_safety(self):
        out = methods.LIBRARY["breakeven"].impl(
            {"fixed": "1000", "price": "20", "variable": "10", "expected_units": "150"})
        self.assertEqual(number(out["breakeven_units"]), number("100"))
        self.assertEqual(number(out["contribution_margin"]), number("10"))
        self.assertEqual(number(out["breakeven_revenue"]), number("2000"))
        self.assertEqual(number(out["margin_of_safety_units"]), number("50"))
        self.assertEqual(number(out["margin_of_safety_ratio"]), number("50") / number("150"))
        target = methods.LIBRARY["breakeven"].impl(
            {"fixed": "1000", "price": "20", "variable": "10", "target_profit": "500"})
        self.assertEqual(number(target["target_profit_units"]), number("150"))

    def test_E_acc_036__multi_product_units_sum_to_the_total(self):
        inputs = copy.deepcopy(server.PRESETS["multibreakeven"]["inputs"])
        out = methods.LIBRARY["multi_product_breakeven"].impl(inputs)
        weighted = Decimal(0)
        total_mix = Decimal(0)
        for product in inputs["products"]:
            units = number(product["mix_units"])
            total_mix += units
            weighted += units * (number(product["price"]) - number(product["variable_cost"]))
        self.assertEqual(number(out["weighted_contribution"]), weighted / total_mix)
        self.assertEqual(number(out["total_mix_units"]), total_mix)
        per_product = [number(value) for key, value in out.items()
                       if key.startswith("units_") and key != "units"]
        self.assertTrue(per_product, "no per-product break-even units were reported")
        self.assertEqual(sum(per_product), number(out["breakeven_total_units"]),
                         "the per-product break-even units must sum to the total")

    def test_E_acc_037__ccc_and_eoq_match_an_independent_recomputation(self):
        inputs = copy.deepcopy(server.PRESETS["workingcapital"]["inputs"])
        out = methods.LIBRARY["working_capital"].impl(inputs)
        self.assertEqual(out["cash_conversion_cycle"], out["dso"] + out["dio"] - out["dpo"])
        expected = (Decimal(2) * number(inputs["annual_demand"]) * number(inputs["order_cost"])
                    / number(inputs["holding_cost_per_unit"])).sqrt()
        self.assertLessEqual(abs(number(out["eoq"]) - expected),
                             Decimal("1e-9") * expected, "EOQ must be sqrt(2DS/H)")
        self.assertLessEqual(abs(number(out["n_orders_per_year"])
                                 - number(inputs["annual_demand"]) / expected),
                             Decimal("1e-9") * number(out["n_orders_per_year"]))

    def test_E_acc_038__loan_payment_matches_the_closed_form(self):
        inputs = {"principal": "200000", "annual_rate": "0.09", "years": "5",
                  "payments_per_year": "12"}
        out = methods.LIBRARY["loan_amortization"].impl(dict(inputs))
        rate = number(inputs["annual_rate"]) / number(inputs["payments_per_year"])
        periods = int(number(inputs["years"]) * number(inputs["payments_per_year"]))
        expected = number(inputs["principal"]) * rate / (1 - (1 + rate) ** -periods)
        self.assertLessEqual(abs(number(out["payment"]) - expected),
                             Decimal("1e-9") * expected, "PMT must match the closed form")
        self.assertEqual(number(out["n_payments"]), number(periods))
        self.assertEqual(out["first_interest"] + out["first_principal"], out["payment"])
        zero = methods.LIBRARY["loan_amortization"].impl(
            {"principal": "1200", "annual_rate": "0", "years": "1", "payments_per_year": "12"})
        self.assertEqual(number(zero["payment"]), number("100"))
        self.assertEqual(number(zero["total_interest"]), number("0"))

    def test_E_acc_039__cagr_matches_an_independent_recomputation(self):
        inputs = copy.deepcopy(server.PRESETS["trendanalysis"]["inputs"])
        out = methods.LIBRARY["trend_analysis"].impl(inputs)
        periods = len(inputs["revenue"]) - 1
        expected = (number(inputs["revenue"][-1]) / number(inputs["revenue"][0])) ** (Decimal(1) / periods)
        self.assertLessEqual(abs(number(out["revenue_cagr"]) - (expected - 1)),
                             Decimal("1e-9"), "CAGR must be (end/start)^(1/n) - 1")
        losing = methods.LIBRARY["trend_analysis"].impl({
            "years": ["2022", "2023", "2024"], "revenue": ["100", "120", "150"],
            "cost_of_sales": ["60", "70", "85"], "operating_expenses": ["20", "25", "30"],
            "net_income": ["-10", "5", "20"]})
        self.assertNotIn("net_income_cagr", losing,
                         "a negative base has no real CAGR; it must be omitted, not invented")
        with self.assertRaises(methods.DataError) as refused:
            methods.LIBRARY["trend_analysis"].impl({
                "years": ["2022", "2023"], "revenue": ["0", "10"],
                "cost_of_sales": ["0", "5"], "operating_expenses": ["0", "2"],
                "net_income": ["0", "3"]})
        self.assertIn("revenue must be positive", str(refused.exception))

    def test_E_acc_040__tax_uses_the_declared_rate_and_no_jurisdiction(self):
        out = methods.LIBRARY["tax_declared"].impl(
            copy.deepcopy(server.PRESETS["tax"]["inputs"]))
        self.assertEqual(number(out["income_tax"]), number("250000"))
        self.assertEqual(number(out["net_income_after_tax"]), number("750000"))
        loss = methods.LIBRARY["tax_declared"].impl(
            {"taxable_income": "-5000", "income_tax_rate": "0.25"})
        self.assertEqual(number(loss["income_tax"]), number("0"))
        self.assertEqual(number(loss["net_income_after_tax"]), number("-5000"))
        result = deliver("tax")
        self.assertIn("no jurisdiction's tax law", result.report)
        self.assertIn("NOLCO", result.report)

    def test_E_acc_041__vat_and_deferred_tax_foot_and_pairs_are_enforced(self):
        out = methods.LIBRARY["tax_declared"].impl(
            copy.deepcopy(server.PRESETS["tax"]["inputs"]))
        self.assertEqual(number(out["vat_payable"]),
                         number(out["vat_output_tax"]) - number(out["vat_input_tax"]))
        self.assertEqual(number(out["vat_payable"]), number("60000"))
        self.assertEqual(number(out["deferred_tax"]), number("25000"))
        self.assertEqual(number(out["total_tax_charge"]),
                         number(out["income_tax"]) + number(out["deferred_tax"]))
        self.assertEqual(number(out["total_tax_charge"]), number("275000"))
        with self.assertRaises(methods.DataError) as refused:
            methods.LIBRARY["tax_declared"].impl(
                {"taxable_income": "1000", "income_tax_rate": "0.25", "vat_output_tax": "10"})
        self.assertIn("declare both vat_output_tax and vat_input_tax",
                      str(refused.exception))
        with self.assertRaises(methods.DataError):
            methods.LIBRARY["tax_declared"].impl(
                {"taxable_income": "1000", "income_tax_rate": "1.5"})

    def test_E_acc_042__guide_worked_examples_reproduce(self):
        from bp import accounts
        spec = MINIATURE
        out = accounts.build(copy.deepcopy(spec))
        self.assertTrue(all(ok for _, ok, _ in out["_checks"]), out["_checks"])
        statements = out["_appendix"]["statements"]
        self.assertEqual(number(statements["total_assets"]), number("76000"))
        self.assertEqual(number(statements["total_liabilities"]), number("20000"))
        self.assertEqual(number(statements["equity_with_current_earnings"]), number("56000"))
        self.assertEqual(number(out["net_income"]), number("6000"))
        debit, credit = trial_balance_totals(spec)
        self.assertEqual(debit, number("85000"), "the guide's trial balance is 85,000 a side")
        self.assertEqual(credit, number("85000"))
        ratios = methods.LIBRARY["ratio_analysis"].impl({
            "current_assets": "500000", "current_liabilities": "200000", "inventory": "200000"})
        self.assertEqual(number(ratios["current_ratio"]), number("2.5"))
        self.assertEqual(number(ratios["quick_ratio"]), number("1.5"))


class PaperTest(unittest.TestCase):
    """E-acc-043, 044, 046, 047, 048 — what the delivered paper says."""

    def test_E_acc_043__papers_read_as_prose_not_raw_decimals(self):
        text, _ = paper_section(WORKING_CAPITAL_BRIEF, "working_capital",
                                WORKING_CAPITAL_INPUTS, "Working Capital Cycle")
        self.assertIsNone(LONG_DECIMAL.search(text),
                          "a 50-digit Decimal reached the paper: %s" % text[:200])
        self.assertNotIn("{", text, "a dict was printed into the paper")
        self.assertNotIn("_appendix", text)
        for key in ("cash_conversion_cycle", "n_orders_per_year", "net_working_capital"):
            self.assertNotIn(key, text, "a raw result key was printed instead of prose")
        self.assertIn("50.19", text, "the cash conversion cycle must appear as prose")
        self.assertIn("1,095.45", text, "the order quantity must appear as rounded money")

    def test_E_acc_044__each_capability_uses_its_own_formatter(self):
        accounting = chat.CAPABILITY_LINES["trend_analysis"]
        forecast = chat.CAPABILITY_LINES["trend_forecast"]
        self.assertIsNot(accounting, forecast,
                         "the two capabilities must not share one formatter")
        self.assertEqual(accounting.__name__, "_trend_lines")
        self.assertEqual(forecast.__name__, "_forecast_lines")
        text, _ = paper_section(TREND_BRIEF, "trend_analysis", TREND_INPUTS, "Trend Analysis")
        self.assertIn("revenue grew at", text,
                      "the trend paper must be written by the common-size/trend formatter")
        self.assertIn("gross margin", text.lower())
        self.assertNotIn("forecast_1", text, "the trend paper must not print forecast fields")
        self.assertIsNone(LONG_DECIMAL.search(text))

    def test_E_acc_046__a_chained_input_names_its_source(self):
        line = chat._declared_inputs_line({"inputs": {"rate": "0.10"},
                                           "from": {"rate": "wacc"}})
        self.assertIn("from the", line)
        self.assertIn("result", line)
        plain = chat._declared_inputs_line({"inputs": {"rate": "0.10"}, "from": {}})
        self.assertIn("Declared inputs:", plain)
        self.assertNotIn("from the", plain)

    def test_E_acc_047__a_section_opens_with_its_declared_inputs(self):
        text, _ = paper_section(WORKING_CAPITAL_BRIEF, "working_capital",
                                WORKING_CAPITAL_INPUTS, "Working Capital Cycle")
        self.assertIn("Declared inputs:", text)
        self.assertIn("revenue 1,200,000", text)
        state = draftable(answer_all(chat.start(WORKING_CAPITAL_BRIEF, "management", "pestel")))
        with self.assertRaises(chat.ChatError) as refused:
            chat.attach_computation(state, "working_capital",
                                    {"revenue": "0", "cost_of_sales": "1"})
        self.assertIn("inventory", str(refused.exception).lower())
        state = chat.draft(state, accepted_ids=[],
                           implications="The declared figures set the position.")
        rows = [row for row in state["draft"]["outline"]
                if row.get("heading") == "Working Capital Cycle"]
        refused_text = " ".join(rows[0].get("lines") or []) if rows else ""
        self.assertIn("refused", refused_text.lower())
        self.assertIn("no figure is reported", refused_text.lower())

    def test_E_acc_048__paper_prose_carries_no_recommendation_or_forecast(self):
        text, _ = paper_section(WORKING_CAPITAL_BRIEF, "working_capital",
                                WORKING_CAPITAL_INPUTS, "Working Capital Cycle")
        lowered = text.lower()
        for forbidden in ("recommend", "we advise", "should invest", "will improve"):
            self.assertNotIn(forbidden, lowered)
        self.assertIn("does not judge the", lowered,
                      "the paper must state what the method does not do")
        recorded = methods.LIBRARY["working_capital"].impl(dict(WORKING_CAPITAL_INPUTS))
        for figure in ("dso", "dio", "dpo", "cash_conversion_cycle"):
            short = str(recorded[figure].quantize(Decimal("0.01")))
            self.assertIn(short.split(".")[0].replace(",", ""), text.replace(",", ""),
                          "%s is missing from the prose" % figure)


class RoutingTest(unittest.TestCase):
    """E-acc-049 — a pure accounting computation is refused by the framework chat."""

    def test_E_acc_049__a_pure_accounting_brief_is_refused_and_named(self):
        state = chat.start("Prepare the journal entries and the trial balance for the month "
                           "from the declared transactions.", "any")
        self.assertEqual(state["stage"], "not_supported",
                         "a journal-entry brief must not be wrapped in a PESTEL paper")
        self.assertIn("Accounting", state["message"])
        self.assertEqual(state["questions"], [])
        self.assertEqual(state["question_index"], 0)
        again = chat.start("Compute the depreciation and reconcile the ledger for the period.",
                           "management")
        self.assertEqual(again["stage"], "not_supported")
        self.assertTrue(again["message"])
        keeps = chat.start("Assess the grocery retail industry in Saudi Arabia and the working "
                           "capital cycle the entry needs.", "any")
        self.assertNotEqual(keeps["stage"], "not_supported",
                            "an industry brief with an external question is still a paper")


if __name__ == "__main__":
    unittest.main()











