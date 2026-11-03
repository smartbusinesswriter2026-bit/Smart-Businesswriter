"""The statement council and the verifier: a model reading, a dissent, and a code veto.

No socket: a fake provider stands in for the model, so the council's contract is tested as behaviour
— one reading, a dissent only on contested items, a verifier that refuses an untraceable figure, a
non-balancing journal or a mis-articulating statement, and a same-model disclosure.
"""

import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import statements, statements_council, statements_verify  # noqa: E402

TRANSACTIONS = ("Amara started the business with cash 50,000 and bought equipment for 20,000 cash. "
                "She sold goods for 8,000 cash and paid rent of 1,500.")

READING = {
    "problem_type": "transactions",
    "why": "cue 'started with': the instruction lists transactions",
    "currency": "USD", "framework": "US_GAAP", "places": 2,
    "period": {"start": "2026-01-01", "end": "2026-12-31"}, "period_source": "assumed",
    "chart": [
        {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "section": "current",
         "role": "cash", "activity": "operating", "quote": "cash 50,000"},
        {"code": "1500", "name": "Equipment", "type": "asset", "line": "Property, plant and equipment",
         "section": "non_current", "activity": "investing", "quote": "equipment for 20,000"},
        {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "role": "capital",
         "activity": "financing", "quote": "cash 50,000"},
        {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings",
         "role": "retained_earnings", "quote": "rent of 1,500"},
        {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue",
         "activity": "operating", "quote": "sold goods for 8,000"},
        {"code": "5100", "name": "Rent", "type": "expense", "line": "Operating expenses",
         "activity": "operating", "quote": "rent of 1,500"}],
    "opening": [],
    "journal": [
        {"date": "2026-01-02", "description": "capital introduced",
         "quote": "started the business with cash 50,000",
         "lines": [{"account": "1000", "debit": "50000"}, {"account": "3000", "credit": "50000"}]},
        {"date": "2026-01-03", "description": "equipment bought",
         "quote": "bought equipment for 20,000 cash",
         "lines": [{"account": "1500", "debit": "20000"}, {"account": "1000", "credit": "20000"}]},
        {"date": "2026-02-01", "description": "cash sale", "quote": "sold goods for 8,000 cash",
         "lines": [{"account": "1000", "debit": "8000"}, {"account": "4000", "credit": "8000"}]},
        {"date": "2026-02-02", "description": "rent paid", "quote": "paid rent of 1,500",
         "lines": [{"account": "5100", "debit": "1500"}, {"account": "1000", "credit": "1500"}]}],
    "schedules": [],
    "figures": [{"written": "50,000", "value": "50000", "kind": "amount", "quote": "cash 50,000"},
                {"written": "20,000", "value": "20000", "kind": "amount", "quote": "equipment for 20,000"},
                {"written": "8,000", "value": "8000", "kind": "amount", "quote": "sold goods for 8,000"},
                {"written": "1,500", "value": "1500", "kind": "amount", "quote": "rent of 1,500"}],
    "derivations": [], "ratio_map": {}, "diagnosis": None, "missing": [], "assumptions": [],
}


class FakeProvider:
    """Answers with prepared texts in order, and records how often it was asked."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, messages):
        self.calls.append(messages)
        if not self.answers:
            raise AssertionError("the council called the provider more often than expected")
        return self.answers.pop(0)


def reading(**overrides):
    base = json.loads(json.dumps(READING))
    base.update(overrides)
    return json.dumps(base)


class CouncilTest(unittest.TestCase):
    def test_a_single_reading_is_enough_when_nothing_is_contested(self):
        provider = FakeProvider([reading()])
        answer = statements_council.read(TRANSACTIONS, provider=provider)
        self.assertEqual(answer["source"], "council")
        self.assertEqual(len(provider.calls), 1, "no dissent should be asked for an uncontested reading")
        self.assertEqual(statements_verify.verify_reading(answer["reading"], TRANSACTIONS), [])

    def test_a_contested_item_gets_one_dissent_call_and_the_record_keeps_it(self):
        contested = json.loads(json.dumps(READING))
        contested["chart"].append({"code": "2200", "name": "Loan from owner", "type": "liability",
                                   "line": "Borrowings", "section": "non_current",
                                   "activity": "financing", "quote": "cash 50,000"})
        provider = FakeProvider([
            json.dumps(contested),
            json.dumps({"items": [{"label": "Loan from owner", "used": "Borrowings",
                                   "alternative": "Capital", "quote": "cash 50,000",
                                   "why": "an owner's advance can be permanent capital"}]})])
        answer = statements_council.read(TRANSACTIONS, provider=provider)
        self.assertEqual(answer["source"], "council+dissent")
        self.assertEqual(len(provider.calls), 2)
        self.assertEqual(answer["rejected"][0]["alternative"], "Capital")

    def test_a_fenced_answer_with_trailing_prose_still_parses(self):
        provider = FakeProvider(["```json\n" + reading() + "\n```\nThat is my reading."])
        answer = statements_council.read(TRANSACTIONS, provider=provider)
        self.assertEqual(answer["reading"]["problem_type"], "transactions")

    def test_an_unreadable_answer_is_refused(self):
        provider = FakeProvider(["I think this is a trial balance, but I cannot be sure."])
        with self.assertRaises(statements_council.CouncilError):
            statements_council.read(TRANSACTIONS, provider=provider)

    def test_a_truncated_answer_is_a_rejection_not_a_partial_reading(self):
        provider = FakeProvider([reading()[:240]])
        with self.assertRaises(statements_council.CouncilError):
            statements_council.read(TRANSACTIONS, provider=provider)

    def test_the_same_model_is_disclosed(self):
        import bp.product.prose as prose
        original = prose.model_id
        try:
            prose.model_id = lambda: "same-model"
            statements_council.model_id = lambda: "same-model"
            answer = statements_council.read(TRANSACTIONS, provider=FakeProvider([reading()]))
            self.assertTrue(answer["same_model"], "one model is not a second opinion")
        finally:
            prose.model_id = original


class VerifierTest(unittest.TestCase):
    def problems(self, **overrides):
        candidate = json.loads(json.dumps(READING))
        candidate.update(overrides)
        return statements_verify.verify_reading(candidate, TRANSACTIONS)

    def test_the_fixture_reading_is_approved(self):
        self.assertEqual(self.problems(), [])

    def test_a_figure_whose_quote_is_not_in_the_instruction_is_refused(self):
        figures = list(READING["figures"])
        figures.append({"written": "99,000", "value": "99000", "kind": "amount",
                        "quote": "a figure nobody wrote"})
        problems = self.problems(figures=figures)
        self.assertEqual([p["check"] for p in problems], ["provenance"])

    def test_a_figure_with_no_quote_is_refused(self):
        figures = list(READING["figures"]) + [{"written": "5", "value": "5", "kind": "amount", "quote": ""}]
        self.assertIn("provenance", [p["check"] for p in self.problems(figures=figures)])

    def test_a_non_balancing_journal_is_refused(self):
        journal = json.loads(json.dumps(READING["journal"]))
        journal[0]["lines"][1]["credit"] = "49000"
        problems = self.problems(journal=journal)
        self.assertIn("balance", [p["check"] for p in problems])

    def test_an_account_without_a_section_is_refused(self):
        chart = json.loads(json.dumps(READING["chart"]))
        chart[0].pop("section")
        problems = self.problems(chart=chart)
        self.assertIn("chart", [p["check"] for p in problems])

    def test_a_second_retained_earnings_account_is_refused(self):
        chart = json.loads(json.dumps(READING["chart"]))
        chart.append({"code": "3101", "name": "Second retained", "type": "equity",
                      "line": "Retained earnings", "role": "retained_earnings", "quote": "rent of 1,500"})
        self.assertIn("chart", [p["check"] for p in self.problems(chart=chart)])

    def test_a_currency_the_product_does_not_use_is_refused(self):
        self.assertIn("currency", [p["check"] for p in self.problems(currency="PHP")])

    def test_a_mis_articulating_statement_is_refused(self):
        result = {"_checks": [("assets_equal_liabilities_plus_equity", False, "assets 10 vs 9")],
                  "_appendix": {"equity_statement": {"total_closing": "9"},
                                "statements": {"equity_with_current_earnings": "10"}}}
        problems = statements_verify.verify_reading(READING, TRANSACTIONS, result=result)
        self.assertEqual([p["check"] for p in problems], ["articulation", "articulation"])

    def test_a_refusal_without_a_named_gap_is_refused(self):
        problems = statements_verify.verify_reading(READING, TRANSACTIONS, refusal="does not build")
        self.assertIn("completeness", [p["check"] for p in problems])


if __name__ == "__main__":
    unittest.main()

