"""The journal view: the audit trail behind the statements and the T-accounts.

`ledger.journal_view` is what lets a reader see *why* a balance is what it is. It must
therefore be a faithful projection of the journal and nothing else:

- every entry carries its own debit and credit totals, and they must balance;
- recomputing every account's debits and credits from the view must agree exactly with
  `j.balances()`, which is what the statements are built from;
- opening and closing entries must be marked, because a reader who sees income accounts
  close deserves to see the closing entry;
- each entry carries the hash link that `verify_chain` checks.

The trap at the end drops one entry and shows the recomputation stops agreeing, so
"the view agrees with the journal" is a real assertion rather than a tautology.
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

from bp import ledger      # noqa: E402
from bp import report      # noqa: E402
from bp.server import PRESETS  # noqa: E402


def base_spec():
    return copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])


def journal_for(spec):
    chart = ledger.Chart([ledger.Account(**a) for a in spec["chart"]])
    p = spec["period"]
    j = ledger.Journal(chart, p["start"], p["end"], spec["currency"])
    for e in spec.get("opening", []):
        j.post(ledger.Entry.make(p["start"], e.get("description", "opening"), e["lines"], 2, opening=True))
    for e in spec.get("entries", []):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2))
    pre = ledger.statements(j)
    for e in ledger.closing_entries(j, pre):
        j.post(ledger.Entry.make(e["date"], e["description"], e["lines"], 2, closing=e["closing"]))
    return j


def recompute(entries, chart):
    d = {code: [D(0), D(0)] for code in chart.accounts}
    for row in entries:
        for l in row["lines"]:
            d[l["account"]][0 if l["side"] == "D" else 1] += D(l["debit"]) if l["side"] == "D" else D(l["credit"])
    return d


class FaithfulProjection(unittest.TestCase):
    def test_view_matches_the_journal_entry_for_entry(self):
        j = journal_for(base_spec())
        view = ledger.journal_view(j)
        self.assertEqual(len(view), len(j.entries))
        self.assertEqual([r["hash"] for r in view], list(j.hashes))
        self.assertEqual([r["date"] for r in view], [e.date for e in j.entries])
        self.assertEqual([r["description"] for r in view], [e.description for e in j.entries])
        self.assertTrue(j.verify_chain(), "the hash chain must verify")

    def test_every_entry_balances_in_the_view(self):
        for row in ledger.journal_view(journal_for(base_spec())):
            self.assertEqual(row["debits"], row["credits"],
                             "entry '%s' does not balance in the view" % row["description"])
            self.assertGreaterEqual(len(row["lines"]), 2)

    def test_recomputing_balances_from_the_view_agrees_with_the_journal(self):
        j = journal_for(base_spec())
        view = ledger.journal_view(j)
        rebuilt = recompute(view, j.chart)
        actual = j.balances()
        for code in j.chart.accounts:
            self.assertEqual(rebuilt[code][0], actual[code][0], "%s debits disagree" % code)
            self.assertEqual(rebuilt[code][1], actual[code][1], "%s credits disagree" % code)

    def test_every_line_names_an_account_in_the_chart(self):
        j = journal_for(base_spec())
        for row in ledger.journal_view(j):
            for l in row["lines"]:
                self.assertIn(l["account"], j.chart.accounts)
                self.assertEqual(l["name"], j.chart.get(l["account"]).name)


class Marking(unittest.TestCase):
    def test_opening_and_closing_entries_are_marked(self):
        view = ledger.journal_view(journal_for(base_spec()))
        openings = [r for r in view if r["opening"]]
        closings = [r for r in view if r["closing"]]
        self.assertEqual(len(openings), 1, "the preset has one opening entry")
        self.assertTrue(closings, "a closed engagement must show its closing entries")
        self.assertFalse(any(r["opening"] and r["closing"] for r in view))

    def test_rendered_journal_marks_the_close(self):
        text = report.journal(journal_for(base_spec()))
        self.assertIn("(opening)", text)
        self.assertIn("(closing)", text)
        self.assertIn("entry totals", text)


class TrapTest(unittest.TestCase):
    def test_dropping_an_entry_breaks_the_recomputation(self):
        """Proof the agreement test can fail: remove one entry and the balances
        recomputed from the view no longer match the journal."""
        j = journal_for(base_spec())
        view = ledger.journal_view(j)
        self.assertEqual(recompute(view, j.chart)["1000"][0], j.balances()["1000"][0])

        forged = [r for r in view if r["description"] != "sale"]
        self.assertNotEqual(recompute(forged, j.chart)["1000"][0], j.balances()["1000"][0],
                            "dropping an entry must break the recomputation")


if __name__ == "__main__":
    unittest.main()
