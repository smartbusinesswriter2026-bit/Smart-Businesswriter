"""Revaluation: restate the asset, and send the movement to the right place.

IAS 16 permits two presentations of a revaluation, and the 2013 amendment pins the arithmetic either way:
accumulated depreciation = gross - net. So the tests check that both methods land on the **same** net
carrying amount and the **same** surplus, while differing in the gross and accumulated figures - and that
the surplus goes to other comprehensive income, not to profit.

A decrease goes to profit or loss, except for a declared `reverses_surplus` amount charged to the reserve
first. The engine does not guess that split: a pooled reserve does not say how much belongs to one asset.

The trap checks the property a wrong implementation would break: a revaluation gain must leave retained
earnings alone and appear in the reserve.
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
from bp import schedules                  # noqa: E402
from bp.server import PRESETS             # noqa: E402

SCHED = dict(kind="revaluation", date="2026-03-15", asset_account="1200", accum_account="1210",
             oci_account="4200", loss_account="5400", places=2)


def spec(amount="2600", method="proportionate", reverses=None):
    s = copy.deepcopy(PRESETS["accounts"]["inputs"]["spec"])
    s["chart"] += [
        {"code": "1200", "name": "Equipment", "type": "asset", "line": "Equipment", "section": "non_current"},
        {"code": "1210", "name": "Accumulated depreciation", "type": "asset", "line": "Accum. dep.", "contra": True},
        {"code": "4200", "name": "Revaluation gain", "type": "oci", "line": "Revaluation gain"},
        {"code": "3300", "name": "Revaluation reserve", "type": "equity", "line": "Revaluation reserve",
         "role": "oci_reserve"},
        {"code": "5400", "name": "Revaluation loss", "type": "expense", "line": "Revaluation loss"},
    ]
    s["entries"] += [
        {"date": "2026-02-01", "description": "buy equipment",
         "lines": [{"account": "1200", "debit": "3000"}, {"account": "1000", "credit": "3000"}]},
        {"date": "2026-02-28", "description": "depreciation on equipment",
         "lines": [{"account": "5400", "debit": "800"}, {"account": "1210", "credit": "800"}]},
    ]
    schedule = dict(SCHED, revalued_amount=amount, method=method)
    if reverses is not None:
        schedule["reverses_surplus"] = reverses
    s["schedules"] = [schedule]
    return s


def build(**kw):
    return accounts_mod.build(spec(**kw))


def ledgers(out):
    return {lg["code"]: lg for lg in out["_appendix"]["ledgers"]}


class BothMethodsAgreeOnTheNet(unittest.TestCase):
    def test_proportionate_restates_gross_and_accumulated(self):
        lg = ledgers(build(method="proportionate"))
        gross, accum = D(lg["1200"]["closing_balance"]), D(lg["1210"]["closing_balance"])
        self.assertEqual(gross - accum, D("2600"), "gross less accumulated must be the revalued amount")
        self.assertEqual(accum, gross - D("2600"), "accumulated = gross - net, as the 2013 amendment requires")
        self.assertGreater(accum, D("800"), "proportionate restatement keeps some accumulated depreciation")

    def test_elimination_writes_accumulated_depreciation_off(self):
        lg = ledgers(build(method="elimination"))
        self.assertEqual(D(lg["1200"]["closing_balance"]), D("2600"))
        self.assertEqual(D(lg["1210"]["closing_balance"]), D(0))

    def test_the_surplus_is_the_same_either_way(self):
        for method in ("proportionate", "elimination"):
            ci = build(method=method)["_appendix"]["comprehensive_income"]
            self.assertEqual(D(ci["total_oci"]), D("400"), "%s: surplus must be 2,600 - 2,200" % method)

    def test_the_statement_balances_either_way(self):
        for method in ("proportionate", "elimination"):
            st = build(method=method)["_appendix"]["statements"]
            self.assertEqual(D(st["total_assets"]), D(st["total_liabilities"]) + D(st["equity_with_current_earnings"]))


class TheSurplusGoesToReserve(unittest.TestCase):
    def test_an_increase_is_other_comprehensive_income(self):
        out = build()
        lg = ledgers(out)
        self.assertEqual(D(lg["3300"]["closing_balance"]), D("400"))
        self.assertEqual(D(lg["4200"]["closing_balance"]), D(0), "the OCI account closes to the reserve")
        self.assertEqual(D(out["_appendix"]["comprehensive_income"]["total_oci"]), D("400"))

    def test_profit_is_not_inflated(self):
        out = build()
        lg = ledgers(out)
        self.assertEqual(D(lg["3100"]["closing_balance"]), D("850"),
                         "retained earnings carries the trading result (1,650) less the 800 depreciation booked")


class ADecreaseGoesToProfit(unittest.TestCase):
    def test_a_downward_revaluation_is_an_expense(self):
        out = build(amount="1800")                       # net 2,200 -> 1,800, a decline of 400
        lg = ledgers(out)
        self.assertEqual(D(lg["3300"]["closing_balance"]), D(0), "a loss must not touch the reserve")
        self.assertEqual(D(out["net_income"]), D("450"), "850 of trading profit less the 400 decline")

    def test_a_declared_reversal_is_charged_to_the_reserve_first(self):
        out = build(amount="1800", reverses="150")
        lg = ledgers(out)
        self.assertEqual(D(lg["3300"]["closing_balance"]), D("-150"),
                         "150 of the decline reversed the surplus, leaving the reserve at -150")
        self.assertEqual(D(out["net_income"]), D("600"), "only the remaining 250 reaches profit")


class Refusals(unittest.TestCase):
    def _raises(self, amount="2600", method="proportionate", message=""):
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            build(amount=amount, method=method)
        self.assertIn(message, str(ctx.exception))

    def test_an_unknown_method_is_refused(self):
        self._raises(method="fair_value", message="proportionate or elimination")

    def test_a_negative_amount_is_refused(self):
        with self.assertRaises(schedules.ScheduleError):
            schedules.revaluation({"revalued_amount": "-1", **{k: v for k, v in SCHED.items() if k != "kind"}})

    def test_revaluing_to_the_carrying_amount_is_refused(self):
        self._raises(amount="2200", message="changes nothing")

    def test_a_fully_depreciated_asset_is_refused(self):
        spec_ = spec()
        dep = next(e for e in spec_["entries"] if e["description"] == "depreciation on equipment")
        dep["lines"][0]["debit"] = "3000"       # depreciate the asset to nil
        dep["lines"][1]["credit"] = "3000"
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            accounts_mod.build(spec_)
        self.assertIn("no carrying amount", str(ctx.exception))

    def test_a_gain_into_a_non_oci_account_is_refused(self):
        spec_ = spec()
        for a in spec_["chart"]:
            if a["code"] == "4200":
                a["type"] = "income"
        with self.assertRaises(accounts_mod.EngagementError) as ctx:
            accounts_mod.build(spec_)
        self.assertIn("other-comprehensive-income", str(ctx.exception))


class TrapTest(unittest.TestCase):
    def test_the_gain_never_reaches_retained_earnings(self):
        """The plausible wrong implementation credits the revaluation to profit. Then net income would rise
        by 400 and the reserve would stay empty, while every entry still balances."""
        out = build()
        lg = ledgers(out)
        self.assertEqual(D(lg["3100"]["closing_balance"]), D("850"))
        self.assertEqual(D(lg["3300"]["closing_balance"]), D("400"))
        self.assertNotEqual(D(lg["3100"]["closing_balance"]), D("1250"),
                            "crediting the revaluation to profit would overstate it by 400")


if __name__ == "__main__":
    unittest.main()
