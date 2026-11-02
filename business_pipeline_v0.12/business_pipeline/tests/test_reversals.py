"""Reversing entries: `ref` names an entry, `reverses` posts its exact mirror.

A reversal must be visible. The engine expands it into an ordinary balanced entry rather than
adjusting a stored balance, so both the original and its reversal appear in the journal and in
every T-account they touch - which is the only way a reader can check the correction.

These tests hold the contract:

- the expansion is an exact mirror (same accounts, debits and credits swapped);
- it lands on the account balances by exactly the negated amount;
- the declared date is used and a missing description is generated, not invented silently;
- every invalid link is refused *before* anything is posted: lines plus reverses, a duplicate
  ref, an unknown target, a forward reference and a self-reference.

The trap at the end shows the reversal actually moves the numbers, so "the mirror is exact" is
not a test of an empty change.
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
from bp.server import PRESETS             # noqa: E402


def spec_with_reversal():
    spec = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    spec["entries"][0]["ref"] = "sale-1"                 # the sale: Dr Cash 2000 / Cr Sales 2000
    spec["entries"].append({"date": "2026-03-05", "reverses": "sale-1"})
    return spec


def cash_closing(spec):
    out = accounts_mod.build(spec)
    ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
    return D(ledgers["1000"]["closing_balance"])


class TheMirrorIsExact(unittest.TestCase):
    def test_reversal_swaps_debits_and_credits_on_the_same_accounts(self):
        spec = spec_with_reversal()
        rows = accounts_mod.build(spec)["_appendix"]["journal"]
        original = next(r for r in rows if r["description"] == "sale")
        reversal = next(r for r in rows if r["description"].startswith("reversal of"))
        self.assertEqual([l["account"] for l in reversal["lines"]],
                         [l["account"] for l in original["lines"]])
        for a, b in zip(original["lines"], reversal["lines"]):
            self.assertEqual(a["debit"], b["credit"])
            self.assertEqual(a["credit"], b["debit"])
        self.assertEqual(reversal["debits"], reversal["credits"])

    def test_reversal_lands_on_the_balance_by_the_negated_amount(self):
        plain = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
        self.assertEqual(cash_closing(plain) - cash_closing(spec_with_reversal()), D("2000"))

    def test_reversal_uses_the_declared_date_and_generates_a_description(self):
        rows = accounts_mod.build(spec_with_reversal())["_appendix"]["journal"]
        reversal = next(r for r in rows if r["description"].startswith("reversal of"))
        self.assertEqual(reversal["date"], "2026-03-05")
        self.assertEqual(reversal["description"], "reversal of sale-1")
        self.assertFalse(reversal["opening"] or reversal["closing"])

    def test_reversal_is_visible_in_the_affected_account(self):
        out = accounts_mod.build(spec_with_reversal())
        ledgers = {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}
        cash = ledgers["1000"]
        self.assertTrue(any("reversal of" in r["entry"] for r in cash["movements"]),
                        "the reversal must appear in the cash T-account")


class InvalidLinksAreRefused(unittest.TestCase):
    def _errors(self, mutate):
        spec = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
        spec["entries"][0]["ref"] = "sale-1"
        mutate(spec)
        return accounts_mod.validate_spec(spec)

    def test_lines_and_reverses_together_are_refused(self):
        errs = self._errors(lambda s: s["entries"].append(
            {"date": "2026-03-05", "reverses": "sale-1",
             "lines": [{"account": "1000", "debit": "1"}, {"account": "4000", "credit": "1"}]}))
        self.assertTrue(any("must not also declare lines" in e for e in errs), errs)

    def test_duplicate_ref_is_refused(self):
        errs = self._errors(lambda s: s["entries"].append(
            {"date": "2026-03-05", "ref": "sale-1",
             "lines": [{"account": "1000", "debit": "1"}, {"account": "4000", "credit": "1"}]}))
        self.assertTrue(any("duplicate ref" in e for e in errs), errs)

    def test_unknown_target_is_refused(self):
        errs = self._errors(lambda s: s["entries"].append({"date": "2026-03-05", "reverses": "nope"}))
        self.assertTrue(any("reverses must name a declared ref" in e for e in errs), errs)

    def test_self_reference_is_refused(self):
        errs = self._errors(lambda s: s["entries"].append(
            {"date": "2026-03-05", "ref": "loop", "reverses": "loop"}))
        self.assertTrue(any("cannot reverse itself" in e for e in errs), errs)

    def test_forward_reference_is_refused(self):
        def mutate(s):
            s["entries"].insert(0, {"date": "2026-01-05", "reverses": "sale-1"})
        errs = self._errors(mutate)
        self.assertTrue(any("declared before it" in e for e in errs), errs)

    def test_a_refused_link_never_reaches_the_ledger(self):
        spec = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
        spec["entries"][0]["ref"] = "sale-1"
        spec["entries"].append({"date": "2026-03-05", "reverses": "missing"})
        with self.assertRaises(accounts_mod.EngagementError):
            accounts_mod.build(spec)


class TrapTest(unittest.TestCase):
    def test_the_reversal_actually_changes_the_balances(self):
        plain = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
        self.assertNotEqual(cash_closing(plain), cash_closing(spec_with_reversal()),
                            "a reversal that changed nothing would make the mirror test vacuous")


if __name__ == "__main__":
    unittest.main()
