import unittest
from decimal import Decimal

from bp import statement_detect as sd


class DetectBasic(unittest.TestCase):
    def test_cash_sale_detected(self):
        ms = sd.detect("Cash sales of $50,000.")
        self.assertTrue(any(m.detector_id == "cash_sale" for m in ms))
        m = next(m for m in ms if m.detector_id == "cash_sale")
        self.assertEqual(m.slots["amount"], Decimal("50000"))

    def test_credit_sale_detected(self):
        ms = sd.detect("Credit sales of $30,000.")
        m = next(m for m in ms if m.detector_id == "credit_sale")
        self.assertEqual(m.slots["amount"], Decimal("30000"))

    def test_specificity_ordering(self):
        ms = sd.detect("Paid $6,000 cash for a 12-month insurance policy.")
        self.assertTrue(any(m.detector_id == "prepaid_expense" for m in ms))
        # prepaid is more specific than any generic
        self.assertTrue(all(m.specificity >= sd.SPECIFICITY_THRESHOLD
                            for m in ms if m.detector_id == "prepaid_expense"))

    def test_freight_in_detected(self):
        ms = sd.detect("Paid freight-in of $2,000.")
        m = next(m for m in ms if m.detector_id == "freight_in")
        self.assertEqual(m.slots["amount"], Decimal("2000"))

    def test_no_match_returns_empty(self):
        self.assertEqual(sd.detect(""), [])
        self.assertEqual(sd.detect("   "), [])

    def test_unmatched_transaction_is_not_journalizable(self):
        # a generic cash payment with no specific detector
        ms = sd.detect("Paid cash $500.")
        # either no matches or all below threshold
        self.assertTrue(all(not sd.journalizable(m) for m in ms) or not ms)


class JournalizeTests(unittest.TestCase):
    def test_cash_sale_balances(self):
        lines = sd.journalize("cash_sale", {"amount": Decimal("50000")})
        self.assertEqual(lines, [("1000", "Dr", Decimal("50000")),
                                 ("4000", "Cr", Decimal("50000"))])

    def test_unknown_detector_raises(self):
        with self.assertRaises(sd.DetectError):
            sd.journalize("nope", {})

    def test_chart_missing_account_raises(self):
        with self.assertRaises(sd.DetectError):
            sd.journalize("cash_sale", {"amount": Decimal("50000")},
                          chart={"4000": {}})

    def test_chart_present_passes(self):
        lines = sd.journalize("cash_sale", {"amount": Decimal("50000")},
                              chart={"1000": {}, "4000": {}})
        self.assertEqual(len(lines), 2)

    def test_required_slot_missing_raises(self):
        with self.assertRaises(sd.DetectError):
            sd._validate_slot(sd.Slot("amount", "money"), None)


class SlotValidation(unittest.TestCase):
    def test_money_with_commas(self):
        self.assertEqual(sd._money("1,234.56"), Decimal("1234.56"))

    def test_percent(self):
        self.assertEqual(sd._percent("25%"), Decimal("0.25"))
        self.assertEqual(sd._percent("0.25"), Decimal("0.25"))

    def test_int(self):
        self.assertEqual(sd._int("12"), 12)


class DetectIntegration(unittest.TestCase):
    def test_northstar_transactions(self):
        text = ("Issued 50,000 common shares for cash, 50,000. "
                "Borrowed 40,000 from the bank. "
                "Purchased equipment for 60,000 cash. "
                "Cash sales of 200,000. "
                "Credit sales of 30,000.")
        ms = sd.detect(text)
        ids = {m.detector_id for m in ms}
        self.assertIn("equity_issuance_cash", ids)
        self.assertIn("loan_proceeds", ids)
        self.assertIn("ppe_purchase", ids)
        self.assertIn("cash_sale", ids)
        self.assertIn("credit_sale", ids)


if __name__ == "__main__":
    unittest.main()
