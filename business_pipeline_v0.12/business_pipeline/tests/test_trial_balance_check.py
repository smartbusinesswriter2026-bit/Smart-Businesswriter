"""The trial-balance check: what it reports, what it refuses, and what it refuses to claim.

The check exists to be useful to a student without ever pretending to know which of two declared figures is
right. So the tests are as much about the wording and the refusals as about the arithmetic:

- an exact agreement is reported as agreement, and the verdict still says it does not prove the entries;
- a difference is located, and every differing or missing line carries a finding;
- a trial balance that does not balance is reported *first*, because nothing else means anything until it does;
- the classic hints (divisible by 9, equal-and-opposite, one side unposted) appear labelled as hints;
- one input alone is allowed, and the verdict says exactly what that costs the reader;
- ambiguous names, negative figures and over-precise figures are refused rather than guessed.

The trap shows the central assertion can fail: a tampered trial balance must not be reported as agreeing.
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

from bp import check                     # noqa: E402
from bp.methods import LIBRARY, validate_inputs   # noqa: E402
from bp.server import PRESETS            # noqa: E402

CHECKS = LIBRARY["trial_balance_check"].test_names


def base():
    return copy.deepcopy(PRESETS["tbcheck"]["inputs"])


def run(inputs):
    return LIBRARY["trial_balance_check"].impl(inputs)


def statuses(report):
    return {r["status"] for r in report["rows"]}


class AgreementAndDisagreement(unittest.TestCase):
    def test_an_exact_match_is_reported_as_agreement(self):
        r = check.compare(base()["journal"], base()["trial_balance"], 2)
        self.assertEqual(r["counts"]["n_differing"], 0)
        self.assertEqual(r["counts"]["n_matched"], 2)
        self.assertEqual(r["findings"], [])
        self.assertIn("agrees with your own journal", r["verdict"])
        self.assertIn("does not prove your entries are right", r["verdict"])

    def test_a_wrong_figure_is_located(self):
        inputs = base()
        # move both sides by 100 so the trial balance still balances - otherwise the imbalance verdict
        # masks the comparison, which is the right behaviour but not what this test is about
        inputs["trial_balance"][0]["debit"] = "1600"
        inputs["trial_balance"][1]["credit"] = "1600"
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertEqual(r["counts"]["n_differing"], 2)
        self.assertEqual(D(r["amounts"]["total_absolute_difference"]), D("200"))
        self.assertTrue(any(f["kind"] == "amount-differs" for f in r["findings"]))
        self.assertIn("cannot tell you which one is wrong", r["verdict"])

    def test_an_account_only_in_the_journal_is_reported(self):
        inputs = base()
        inputs["trial_balance"] = [row for row in inputs["trial_balance"] if row["code"] != "3000"]
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertEqual(r["counts"]["n_missing_submitted"], 1)
        self.assertTrue(any(f["kind"] == "only-in-journal" for f in r["findings"]))
        self.assertIn("only-in-journal", statuses(r))

    def test_an_account_only_in_the_trial_balance_is_reported(self):
        inputs = base()
        inputs["trial_balance"].append({"code": "9999", "name": "Suspense", "debit": "0", "credit": "0"})
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertEqual(r["counts"]["n_missing_rebuilt"], 1)
        self.assertTrue(any(f["kind"] == "only-in-yours" for f in r["findings"]))


class TheHintsAreHints(unittest.TestCase):
    def test_an_unbalanced_trial_balance_is_reported_first(self):
        inputs = base()
        inputs["trial_balance"][0]["debit"] = "1530"       # debits 1530 vs credits 1500
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertEqual(r["findings"][0]["kind"], "submitted-does-not-balance")
        self.assertIn("does not balance", r["verdict"])

    def test_a_difference_divisible_by_nine_is_labelled_a_hint(self):
        inputs = base()
        inputs["trial_balance"][0]["debit"] = "1590"       # 90 out: divisible by 9
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        top = r["findings"][0]
        self.assertEqual(top["kind"], "submitted-does-not-balance")
        self.assertIn("divisible by 9", top["detail"])
        self.assertIn("hint", top["detail"])
        self.assertIn("not a finding", top["detail"])

    def test_an_equal_and_opposite_figure_is_called_a_wrong_side(self):
        inputs = base()
        # Cash appears as a credit of 1,500 instead of a debit: equal and opposite to the journal
        inputs["trial_balance"][0] = {"code": "1000", "name": "Cash", "debit": "0", "credit": "1500"}
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        kinds = {f["kind"] for f in r["findings"]}
        self.assertIn("wrong-side", kinds, r["findings"])


class OneInputIsAllowed(unittest.TestCase):
    def test_only_a_trial_balance_gives_the_honest_weak_verdict(self):
        r = check.compare(None, base()["trial_balance"], 2)
        self.assertIn("and that is all", r["verdict"])
        self.assertIn("all leave a trial balance balanced", r["verdict"])
        self.assertTrue(all(row["status"] == "unchecked" for row in r["rows"]))

    def test_only_a_journal_says_there_is_nothing_to_compare(self):
        r = check.compare(base()["journal"], None, 2)
        self.assertIn("nothing to compare it against", r["verdict"])
        self.assertTrue(all(row["status"] == "unchecked" for row in r["rows"]))

    def test_neither_is_refused(self):
        with self.assertRaises(check.CheckError):
            check.compare(None, None, 2)


class Refusals(unittest.TestCase):
    def test_the_same_account_listed_twice_is_refused(self):
        """A student listing Cash twice would otherwise be double-counted silently."""
        with self.assertRaises(check.CheckError) as ctx:
            check.compare(None, [{"name": "Cash", "debit": "10"}, {"name": "cash", "debit": "20"}], 2)
        self.assertIn("more than once", str(ctx.exception))

    def test_a_negative_figure_is_refused(self):
        with self.assertRaises(check.CheckError):
            check.compare(None, [{"code": "1000", "debit": "-5"}], 2)

    def test_too_many_decimal_places_are_refused(self):
        with self.assertRaises(check.CheckError):
            check.compare(None, [{"code": "1000", "debit": "1.234"}], 2)

    def test_a_row_with_neither_code_nor_name_is_refused(self):
        with self.assertRaises(check.CheckError):
            check.compare(None, [{"debit": "1"}], 2)

    def test_the_input_schema_accepts_a_partial_row(self):
        """A student needs only a name and one side; the schema must not demand all four fields."""
        errs = validate_inputs(LIBRARY["trial_balance_check"],
                               {"trial_balance": [{"name": "Cash", "debit": "10"}]})
        self.assertEqual(errs, [])


class TheMethodContract(unittest.TestCase):
    def test_all_five_checks_run_and_pass(self):
        out = run(base())
        names = [n for n, ok, _ in out["_checks"]]
        self.assertEqual(tuple(names), CHECKS)
        self.assertTrue(all(ok for _, ok, _ in out["_checks"]), out["_checks"])

    def test_the_second_route_agrees_on_a_tampered_case(self):
        inputs = base()
        inputs["trial_balance"][0]["debit"] = "1200"
        out = run(inputs)
        checks = {n: (ok, d) for n, ok, d in out["_checks"]}
        self.assertTrue(checks["second_route_agrees"][0], checks["second_route_agrees"][1])

    def test_the_appendix_carries_the_verdict_and_the_limits(self):
        ex = run(base())["_appendix"]
        self.assertIn("verdict", ex)
        self.assertEqual(len(ex["cannot_prove"]), 4)
        self.assertIn("which of the two figures is right", ex["cannot_prove"][0])

    def test_the_preset_delivers(self):
        from bp.orchestrator import Pipeline
        d = Pipeline().run(dict(PRESETS["tbcheck"]), lambda s: True)
        self.assertEqual(d.status, "delivered")
        self.assertIn("detail", d.appendix, "the check's appendix must not be filed under 'accounts'")


class TrapTest(unittest.TestCase):
    def test_a_tampered_figure_is_never_reported_as_agreeing(self):
        """The central assertion of the whole feature: if this could not fail, the check would be worthless."""
        inputs = base()
        inputs["trial_balance"][0]["debit"] = "1499"
        r = check.compare(inputs["journal"], inputs["trial_balance"], 2)
        self.assertNotEqual(r["counts"]["n_differing"], 0)
        self.assertTrue(r["findings"])
        self.assertNotIn("agrees with your own journal", r["verdict"])


if __name__ == "__main__":
    unittest.main()
