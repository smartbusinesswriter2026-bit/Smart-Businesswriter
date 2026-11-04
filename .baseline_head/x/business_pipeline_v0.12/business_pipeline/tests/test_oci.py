"""Other comprehensive income: a separate route, closing to a reserve, never through profit.

The point of OCI is that some gains are real but are not profit. So the tests are about keeping the two
apart:

- an `oci` account is credit-normal and is presented **after** net income, with total comprehensive
  income being the sum of the two;
- closing moves the OCI balance to an equity account with role `oci_reserve`, and the OCI account itself
  ends at zero;
- the reserve is equity, so the balance sheet still balances;
- **profit is not inflated** by the revaluation - retained earnings carries only the trading result and
  the reserve carries the revaluation. The trap asserts exactly that, because closing OCI to retained
  earnings is the plausible wrong implementation and it would overstate profit.

A chart with an OCI account and no reserve is refused: there would be nowhere for the balance to go.
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


def spec(amount="1000", reserve=True, oci_account_type="oci"):
    s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    s["chart"] += [
        {"code": "1200", "name": "Equipment", "type": "asset", "line": "Equipment", "section": "non_current"},
        {"code": "4200", "name": "Revaluation gain", "type": oci_account_type, "line": "Revaluation gain"},
    ]
    if reserve:
        s["chart"].append({"code": "3300", "name": "Revaluation reserve", "type": "equity",
                           "line": "Revaluation reserve", "role": "oci_reserve"})
    s["entries"].append({"date": "2026-03-01", "description": "revaluation",
                         "lines": [{"account": "1200", "debit": amount}, {"account": "4200", "credit": amount}]})
    return s


def build(**kw):
    return accounts_mod.build(spec(**kw))


def ledgers(out):
    return {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}


class ItIsPresentedSeparately(unittest.TestCase):
    def test_the_comprehensive_income_block_carries_the_figures(self):
        out = build()
        ci = out["_appendix"]["comprehensive_income"]
        self.assertEqual(D(ci["profit_for_period"]), D(out["net_income"]))
        self.assertEqual(D(ci["total_oci"]), D("1000"))
        self.assertEqual(D(ci["total_comprehensive_income"]), D(ci["profit_for_period"]) + D(ci["total_oci"]))

    def test_oci_is_zero_in_the_post_closing_statements(self):
        """The appendix statement set is post-closing, so OCI has already moved to the reserve there."""
        st = build()["_appendix"]["statements"]
        self.assertEqual(D(st["total_oci"]), D(0))
        self.assertEqual(D(st["equity_with_current_earnings"]), D("7650"))

    def test_the_income_statement_shows_oci_after_net_income(self):
        text = build()["_appendix"]["statements_export"]["income_statement"]
        self.assertIn("Other comprehensive income", text)
        self.assertIn("Total comprehensive income", text)
        self.assertLess(text.index("Net income"), text.index("Other comprehensive income"),
                        "OCI must be presented after profit, not inside it")
        self.assertIn("2,650.00", text, "total comprehensive income is profit plus OCI")

    def test_a_chart_without_oci_does_not_render_the_section(self):
        out = accounts_mod.build(copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"]))
        text = out["_appendix"]["statements_export"]["income_statement"]
        self.assertNotIn("Other comprehensive income", text)


class ItClosesToTheReserve(unittest.TestCase):
    def test_the_oci_account_ends_at_zero(self):
        lg = ledgers(build())
        self.assertEqual(D(lg["4200"]["closing_balance"]), D(0))

    def test_the_reserve_carries_the_amount(self):
        lg = ledgers(build())
        self.assertEqual(D(lg["3300"]["closing_balance"]), D("1000"))

    def test_the_balance_sheet_still_balances(self):
        st = build()["_appendix"]["statements"]
        self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))

    def test_the_equity_statement_classifies_it(self):
        eq = build()["_appendix"]["equity_statement"]
        self.assertEqual(D(eq["by_kind"].get("other comprehensive income", "0")), D("1000"))


class Refusals(unittest.TestCase):
    def test_an_oci_account_without_a_reserve_is_refused_before_building(self):
        errors = accounts_mod.validate_spec(spec(reserve=False))
        self.assertTrue(any("oci_reserve" in e for e in errors), errors)

    def test_an_oci_account_without_a_reserve_never_reaches_the_ledger(self):
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            build(reserve=False)
        self.assertIn("oci_reserve", str(ctx.exception))

    def test_an_unknown_account_type_is_still_refused(self):
        with self.assertRaises(accounts_mod.EngagementError):
            build(oci_account_type="comprehensive")


class TrapTest(unittest.TestCase):
    def test_oci_does_not_leak_into_retained_earnings(self):
        """The plausible wrong implementation closes OCI to retained earnings. Then profit would read
        2,650 instead of 1,650 and the reserve would be empty - every entry would still balance."""
        out = build()
        lg = ledgers(out)
        self.assertEqual(D(lg["3100"]["closing_balance"]), D("1650"),
                         "retained earnings must carry the trading result only")
        self.assertEqual(D(lg["3300"]["closing_balance"]), D("1000"),
                         "the revaluation belongs in the reserve, not in retained earnings")
        self.assertNotEqual(D(lg["3100"]["closing_balance"]), D("2650"),
                            "adding OCI to retained earnings would overstate profit")


if __name__ == "__main__":
    unittest.main()
