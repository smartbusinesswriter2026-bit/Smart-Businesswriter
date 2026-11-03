"""G-pm-04: a percentage typed as a number is refused, not silently taken as given.

The defect: `validate_inputs` checked that a rate was a number and nothing else, so a
student who typed `6` where the method wanted `0.06` was handed an answer wrong by a
hundredfold that looked entirely right.  The core cannot know the student's intent, but
it can know that these inputs are *proportions*, and it can refuse the blatant window.

The rule is deliberately narrow, because a bound that is too eager destroys a capability
to catch a typo:

* only inputs whose documented nature is a share or a rate (`PROPORTION_INPUTS`);
* only at or above 2, so a 1.2 volatility or a 1.5 markup still runs;
* refused rather than converted - the product never invents the number the student meant.

Every caller goes through `validate_inputs` (orchestrator, three server routes, replay
and CSV ingest), so one rule covers every path into a method.
"""

import sys
import unittest

sys.path.insert(0, "src")

from bp import methods as M                                          # noqa: E402

TIME_VALUE = {"periods": "3", "present_value": "1000"}


def errors(method, **inputs):
    return M.validate_inputs(M.LIBRARY[method], inputs)


class ProportionRuleTest(unittest.TestCase):
    def test_a_percentage_typed_as_a_number_is_refused_with_the_decimal_form(self):
        found = errors("time_value", rate="6", **TIME_VALUE)
        self.assertTrue(found, "a rate of 6 was accepted")
        self.assertIn("proportion, not a percentage", found[0])
        self.assertIn("0.06", found[0], "the refusal must say what to type instead")

    def test_the_negative_case_names_the_negative_decimal(self):
        found = errors("time_value", rate="-6", **TIME_VALUE)
        self.assertTrue(found)
        self.assertIn("-0.06", found[0])

    def test_a_fraction_passes_unchanged(self):
        for rate in ("0.06", "0", "0.5", "-0.02"):
            self.assertEqual(errors("time_value", rate=rate, **TIME_VALUE), [], rate)

    def test_a_value_above_one_hundred_gets_no_suggestion_but_is_still_refused(self):
        found = errors("time_value", rate="250", **TIME_VALUE)
        self.assertTrue(found)
        self.assertIn("never a percentage", found[0])

    def test_a_rate_that_is_a_count_per_period_is_untouched(self):
        """arrival_rate is events per hour, not a share: 6 is a normal value."""
        self.assertEqual(errors("queue_analysis", arrival_rate="6", service_rate="8",
                                servers="1"), [])

    def test_the_documented_exclusions_keep_their_range(self):
        """The inputs left out of the table on purpose, each at a legitimate value.

        A bound that refused these would be destroying a capability to catch a typo.
        """
        cases = [
            ("pricing_decision", {"markup_rate": "1.5"}),
            ("sales_projection", {"growth_rate": "1.2"}),
            ("ab_test_two_proportion", {"minimum_effect": "1.1"}),
            ("output_gap_okun", {"okun_coefficient": "1.2"}),
            ("trial_balance_check", {"places": "4"}),
            ("sales_projection", {"start_units": "6"}),
        ]
        for method, inputs in cases:
            found = errors(method, **inputs)
            offending = [line for line in found if "proportion, not a percentage" in line]
            self.assertEqual(offending, [], (method, inputs))

    def test_the_table_cannot_rot(self):
        """Every listed input must still exist and still be a decimal.

        A renamed or retyped input would otherwise make the rule silently stop guarding
        anything, which is the failure mode the table exists to prevent.
        """
        self.assertGreaterEqual(len(M.PROPORTION_INPUTS), 30)
        for method, key in sorted(M.PROPORTION_INPUTS):
            self.assertIn(method, M.LIBRARY, method)
            schema = M.LIBRARY[method].input_schema
            self.assertIn(key, schema, (method, key))
            self.assertEqual(schema[key]["type"], "decimal", (method, key))

    def test_no_shipped_preset_is_refused_by_the_rule(self):
        """The rule may not break a preset the product already ships."""
        from bp.server import PRESETS
        refused = []
        for name, preset in PRESETS.items():
            method = preset.get("method")
            if method not in M.LIBRARY:
                continue
            found = M.validate_inputs(M.LIBRARY[method], preset.get("inputs") or {})
            refused += [(name, line) for line in found
                        if "proportion, not a percentage" in line]
        self.assertEqual(refused, [], refused)


if __name__ == "__main__":
    unittest.main()
