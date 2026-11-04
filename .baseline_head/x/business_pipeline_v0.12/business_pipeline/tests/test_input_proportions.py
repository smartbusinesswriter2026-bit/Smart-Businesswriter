"""G-pm-04 is closed by the product already - this pins it so it stays closed.

The ledger row read *"Pipeline delivers; the appendix says the rate is taken as given"*.
That was written before the orchestrator's rate hint existed, and it is now out of date.
Measured on 2026-11-03, for every shipped preset that carries a proportion input, a value
multiplied by 100 is **either refused by the method or delivered with a hint that spells
out the decimal form** - not one is delivered in silence.

Two mechanisms do the work, and neither is new:

* the orchestrator's hint: a run whose **output** is typed `rate` and lands above 1 says
  *"Rates are entered as decimals: 6% is 0.06, not 6."* - which is why a loan at 9 (for
  9%) and CAPM at 4 (for 4%) both come back flagged;
* the methods' own domain checks: `market_sizing` refuses a share of 50 and `tax_declared`
  refuses a tax rate of 25 before any output is produced.

So this file is a **regression test, not a fix**. It exists because a hard refusal was
tried first and broke three acceptance rows on the finance and people shelves
(`test_a_percent_typed_as_a_whole_number_is_flagged`,
`test_011__a_rate_typed_as_a_whole_number_is_explained`,
`test_E_ppl_059__a_rate_entered_as_6_is_refused_or_disclosed`). The product's recorded
policy is *deliver and disclose*, and two other shelves depend on it; overriding it would
have destroyed a capability to catch a typo. A hundredfold input error must never reach a
student without a word, and today it does not.
"""

import re
import sys
import unittest
from decimal import Decimal

sys.path.insert(0, "src")

from bp import methods as M                                          # noqa: E402
from bp.orchestrator import Pipeline                                 # noqa: E402
from bp.server import PRESETS                                        # noqa: E402


def accept(spec):
    return True


#: Documentation that says the input is a share of one, in words.
PROPORTION_WORDS = re.compile(r"fraction|as a decimal|percent|\bproportion\b|%", re.I)

#: Inputs whose documentation mentions decimals but which are NOT shares of one: a count of
#: places, a count of units, a growth or lift that may exceed 1, a coefficient whose scale is
#: percentage points per percent, and a markup where 1.5 is ordinary practice.
NOT_A_SHARE = {"places", "start_units", "growth_rate", "minimum_effect", "okun_coefficient",
               "markup_rate"}

HINT = "Rates are entered as decimals"


def proportion_inputs(method):
    """The inputs of one method that read as a share, found the way a reader would."""
    return [key for key, spec in (M.LIBRARY[method].input_schema or {}).items()
            if spec.get("type") == "decimal"
            and key not in NOT_A_SHARE
            and PROPORTION_WORDS.search(str(spec.get("desc") or ""))]


def request(preset, inputs):
    return {"objective": preset.get("objective") or "x", "method": preset["method"],
            "currency": preset.get("currency"), "period": preset.get("period"),
            "unit": preset.get("unit"), "inputs": inputs}


class HundredfoldErrorIsNeverSilentTest(unittest.TestCase):
    def test_no_shipped_preset_delivers_a_hundredfold_proportion_in_silence(self):
        """The sweep: every preset carrying a share, with that share multiplied by 100.

        A run may refuse it (the method's own domain check) or deliver it with the hint.
        What it may not do is hand back a figure wrong by a hundredfold without a word.
        """
        silent, exercised = [], 0
        for name, preset in sorted(PRESETS.items()):
            method = preset.get("method")
            if method not in M.LIBRARY:
                continue
            inputs = dict(preset.get("inputs") or {})
            keys = [key for key in proportion_inputs(method) if key in inputs]
            if not keys:
                continue
            for key in keys:
                try:
                    inputs[key] = str(Decimal(str(inputs[key])) * 100)
                except Exception:                                    # noqa: BLE001
                    continue
            decision = Pipeline().run(request(preset, inputs), accept)
            exercised += 1
            if decision.status == "delivered" and HINT not in (decision.report or ""):
                silent.append((name, method, keys))
        self.assertGreaterEqual(exercised, 10, "the sweep found almost nothing to exercise")
        self.assertEqual(silent, [],
                         "these presets deliver a hundredfold share error without a word")

    def test_a_rate_typed_as_six_is_delivered_and_flagged(self):
        """The finance shelf's contract, unchanged: deliver, and say what it looks like."""
        preset = {"method": "time_value", "objective": "x", "currency": "USD"}
        bad = Pipeline().run(request(preset, {"present_value": "1000", "rate": "6",
                                              "periods": "1", "compounding": "annual"}), accept)
        self.assertEqual(bad.status, "delivered")
        self.assertIn(HINT, bad.report)
        self.assertIn("6% is 0.06", bad.report)
        good = Pipeline().run(request(preset, {"present_value": "1000", "rate": "0.06",
                                               "periods": "1", "compounding": "annual"}), accept)
        self.assertNotIn(HINT, good.report)

    def test_a_tax_rate_of_25_is_refused_before_any_output(self):
        """The other mechanism: a method whose own domain check catches the bad value."""
        decision = Pipeline().run(request({"method": "tax_declared", "currency": "USD"},
                                          {"taxable_income": "100000",
                                           "income_tax_rate": "25"}), accept)
        self.assertEqual(decision.status, "blocked")

    def test_the_hint_names_the_decimal_form_not_only_the_error(self):
        """A disclosure a student cannot act on is not a disclosure."""
        preset = {"method": "loan_amortization", "objective": "x", "currency": "USD"}
        decision = Pipeline().run(request(preset, {"principal": "10000", "annual_rate": "9",
                                                   "years": "5"}), accept)
        self.assertEqual(decision.status, "delivered")
        self.assertIn(HINT, decision.report)
        self.assertIn("0.06", decision.report, "the hint must show a decimal, not just complain")


if __name__ == "__main__":
    unittest.main()

