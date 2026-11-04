"""The current/non-current balance sheet split: presentation only, so no total may move.

An account's `section` is **declared**, never inferred - whether a receivable is current is a fact about
the item and the entity. Three properties matter:

1. a classified chart is presented in sections, and the subtotals add to the same total assets;
2. an account with no declared section lands in an explicit `unclassified` group rather than being
   silently forced into current or non-current;
3. a chart with no sections still renders the flat statement, so existing specifications are unaffected.

The trap reclassifies one account between current and non-current and shows the subtotals move while
total assets does not - the whole safety property of a presentation-only change.
"""

import copy
import os
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import accounts as accounts_mod   # noqa: E402
from bp import ledger                     # noqa: E402
from bp.server import PRESETS             # noqa: E402


def chart(sections=True, extra_unclassified=False):
    def s(value):
        return value if sections else ""

    rows = [
        {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash", "section": s("current")},
        {"code": "1100", "name": "Receivables", "type": "asset", "line": "Receivables", "section": s("current")},
        {"code": "1200", "name": "Equipment", "type": "asset", "line": "Equipment", "section": s("non_current")},
        {"code": "2100", "name": "Payables", "type": "liability", "line": "Payables", "section": s("current")},
        {"code": "2200", "name": "Bank loan", "type": "liability", "line": "Loan", "section": s("non_current")},
        {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
        {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings",
         "role": "retained_earnings"},
        {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
        {"code": "5000", "name": "Rent", "type": "expense", "line": "Rent"},
    ]
    if extra_unclassified:
        rows.append({"code": "1300", "name": "Deposit not yet classified", "type": "asset", "line": "Deposit"})
    return rows


def make_spec(sections=True, extra_unclassified=False, reclassify=False):
    s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    s["chart"] = chart(sections=sections, extra_unclassified=extra_unclassified)
    if reclassify:
        for a in s["chart"]:
            if a["code"] == "1100":
                a["section"] = "non_current"
    s["prior_closing"] = {"1000": "5000", "3000": "5000"}
    s["opening"] = [{"lines": [{"account": "1000", "debit": "5000"}, {"account": "3000", "credit": "5000"}]}]
    s["entries"] = [
        {"date": "2026-01-15", "description": "sale",
         "lines": [{"account": "1100", "debit": "2000"}, {"account": "4000", "credit": "2000"}]},
        {"date": "2026-01-20", "description": "buy equipment",
         "lines": [{"account": "1200", "debit": "1500"}, {"account": "2100", "credit": "1500"}]},
        {"date": "2026-02-01", "description": "loan",
         "lines": [{"account": "1000", "debit": "1000"}, {"account": "2200", "credit": "1000"}]},
        {"date": "2026-02-28", "description": "rent",
         "lines": [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}]},
    ]
    if extra_unclassified:
        s["entries"].append({"date": "2026-02-10", "description": "deposit",
                             "lines": [{"account": "1300", "debit": "400"}, {"account": "2100", "credit": "400"}]})
    s.pop("reconciliation", None)
    s["schedules"] = []
    return s


def build(**kw):
    return accounts_mod.build(make_spec(**kw))


def journal_for(s):
    j = ledger.Journal(ledger.Chart([ledger.Account(**a) for a in s["chart"]]),
                       s["period"]["start"], s["period"]["end"], s["currency"])
    for e in s.get("opening", []):
        j.post(ledger.Entry.make(s["period"]["start"], e.get("description", "opening"), e["lines"], 2, opening=True))
    for e in s.get("entries", []):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2))
    pre = ledger.statements(j)
    for e in ledger.closing_entries(j, pre):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2, closing=e["closing"]))
    return j


def groups(**kw):
    return ledger.balance_sheet_groups(journal_for(make_spec(**kw)))


class TheSectionsAddUp(unittest.TestCase):
    def test_sections_and_subtotals_appear(self):
        text = build()["_appendix"]["statements_export"]["balance_sheet"]
        for phrase in ("Current assets", "Total current assets", "Non-current assets",
                       "Total non-current assets", "Current liabilities", "Non-current liabilities",
                       "Total assets", "Total equity"):
            self.assertIn(phrase, text)

    def test_the_subtotals_are_the_figures_they_claim(self):
        g = groups()
        self.assertEqual(D(g["totals"]["current_assets"]), D("7500"))
        self.assertEqual(D(g["totals"]["non_current_assets"]), D("1500"))
        self.assertEqual(D(g["totals"]["current_liabilities"]), D("1500"))
        self.assertEqual(D(g["totals"]["non_current_liabilities"]), D("1000"))
        self.assertTrue(g["classified"])

    def test_total_assets_is_the_same_as_the_unclassified_statement(self):
        classified = build()["_appendix"]["statements"]
        flat = build(sections=False)["_appendix"]["statements"]
        self.assertEqual(D(classified["total_assets"]), D(flat["total_assets"]))
        self.assertEqual(D(classified["total_liabilities"]), D(flat["total_liabilities"]))
        self.assertEqual(D(classified["equity_with_current_earnings"]), D(flat["equity_with_current_earnings"]))

    def test_the_statement_still_balances(self):
        st = build()["_appendix"]["statements"]
        self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))


class UnclassifiedIsExplicit(unittest.TestCase):
    def test_an_account_without_a_section_is_not_forced_into_one(self):
        text = build(extra_unclassified=True)["_appendix"]["statements_export"]["balance_sheet"]
        self.assertIn("Assets (no section declared)", text)
        self.assertIn("Deposit", text)          # the grouped layout labels rows by statement line
        g = groups(extra_unclassified=True)
        self.assertEqual(D(g["totals"]["unclassified_assets"]), D("400"))

    def test_total_assets_includes_the_unclassified_group(self):
        st = build(extra_unclassified=True)["_appendix"]["statements"]
        self.assertEqual(D(st["total_assets"]), D("9400"))     # 9,000 + 400 deposit


class FlatLayoutIsPreserved(unittest.TestCase):
    def test_an_unclassified_chart_renders_the_flat_statement(self):
        text = build(sections=False)["_appendix"]["statements_export"]["balance_sheet"]
        self.assertNotIn("Current assets", text)
        self.assertNotIn("non-current", text.lower())
        self.assertIn("Total assets", text)
        self.assertFalse(groups(sections=False)["classified"])


class TrapTest(unittest.TestCase):
    def test_reclassifying_moves_the_subtotals_but_not_the_totals(self):
        before = groups()
        after = groups(reclassify=True)
        self.assertEqual(D(before["totals"]["current_assets"]), D("7500"))
        self.assertEqual(D(after["totals"]["current_assets"]), D("5500"), "receivables left current assets")
        self.assertEqual(D(after["totals"]["non_current_assets"]), D("3500"), "and joined non-current")

        sum_before = (D(before["totals"]["current_assets"]) + D(before["totals"]["non_current_assets"])
                      + D(before["totals"]["unclassified_assets"]))
        sum_after = (D(after["totals"]["current_assets"]) + D(after["totals"]["non_current_assets"])
                     + D(after["totals"]["unclassified_assets"]))
        self.assertEqual(sum_before, sum_after, "reclassification must not move total assets")


if __name__ == "__main__":
    unittest.main()
