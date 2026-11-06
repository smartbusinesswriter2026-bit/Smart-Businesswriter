import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import instruction_reading as reading


class FrameworkReadingTest(unittest.TestCase):
    def test_no_framework_is_absent(self):
        result = reading.read_frameworks("Analyse the company and recommend an action.")
        self.assertEqual(result.status, "absent")

    def test_one_framework_is_resolved(self):
        result = reading.read_frameworks("Use Five Forces for the industry.")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.primary, "five_forces")

    def test_two_frameworks_are_ambiguous_and_combinable_when_roles_differ(self):
        result = reading.read_frameworks("Compare Ansoff and Five Forces.")
        self.assertEqual(result.status, "ambiguous")
        self.assertTrue(result.combinable)

    def test_two_frameworks_with_the_same_role_conflict(self):
        result = reading.read_frameworks("Use PESTEL and Five Forces.")
        self.assertEqual(result.status, "conflict")

    def test_negated_framework_is_not_selected(self):
        result = reading.read_frameworks("Not Ansoff, use Five Forces.")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.primary, "five_forces")
        self.assertIn("ansoff", result.rejected)

    def test_alias_is_normalised(self):
        result = reading.read_frameworks("Apply Porter 5 forces to the industry.")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.primary, "five_forces")

    def test_pestel_and_swot_are_one_combined_framework(self):
        result = reading.read_frameworks("Use PESTEL and SWOT.")
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.primary, "pestel_swot")


class SlotTest(unittest.TestCase):
    def test_percent_is_typed_as_a_rate(self):
        slots = reading.extract_slots("The rate is 6% per annum.")
        self.assertEqual(len(slots), 1)
        self.assertEqual(slots[0].value, "0.06")
        self.assertEqual(slots[0].kind, "rate")
        self.assertEqual(slots[0].period, "per annum")
        self.assertEqual(slots[0].status, "pending")

    def test_orphan_amount_is_pending(self):
        slots = reading.extract_slots("The project costs 500,000.")
        self.assertTrue(reading.no_silent_drop(slots))

    def test_consumed_and_dismissed_slots_are_not_pending(self):
        slots = reading.extract_slots("The rate is 6% and the cost is 500,000.")
        slots = tuple(reading.Slot(s.name, s.value, s.span, "consumed", s.kind, s.period, s.compounding, s.candidate_roles)
                      for s in slots)
        self.assertEqual(reading.no_silent_drop(slots), ())


class CategoryTest(unittest.TestCase):
    def test_interest_rate_of_a_framework_is_a_category_error(self):
        brief = ("what is the interest rate of ansoff matrix when one wants to do "
                 "porter's five forces at 6% per annum?")
        errors = reading.find_category_errors(brief)
        self.assertTrue(errors)
        self.assertEqual(errors[0].code, "CATEGORY_ERROR")
        self.assertIn("interest rate", errors[0].found.lower())

    def test_interest_rate_of_a_loan_is_not_a_category_error(self):
        errors = reading.find_category_errors("What is the interest rate of the loan at 6% per annum?")
        self.assertEqual(errors, ())

    def test_refusal_carries_code_span_options_and_next_step(self):
        brief = "What is the interest rate of ansoff matrix at 6% per annum?"
        error = reading.find_category_errors(brief)[0]
        payload = reading.refusal(error)
        self.assertEqual(payload["code"], "CATEGORY_ERROR")
        self.assertTrue(payload["span"])
        self.assertTrue(payload["options"])
        self.assertIn("proceed", payload)


class PlannerTest(unittest.TestCase):
    def test_intent_is_asked_first(self):
        result = reading.read_frameworks("Use Five Forces.")
        question = reading.next_question(result, ())
        self.assertEqual(question["id"], "intent")

    def test_category_error_is_asked_before_framework(self):
        brief = "What is the interest rate of ansoff matrix at 6% per annum?"
        result = reading.read_frameworks(brief)
        errors = reading.find_category_errors(brief)
        question = reading.next_question(result, (), intent="paper", errors=errors)
        self.assertEqual(question["id"], "category_error")

    def test_pending_slot_is_asked(self):
        result = reading.read_frameworks("Use Five Forces.")
        slots = reading.extract_slots("The rate is 6% per annum.")
        question = reading.next_question(result, slots, intent="paper")
        self.assertEqual(question["id"], "slot:rate_1")


if __name__ == "__main__":
    unittest.main()
