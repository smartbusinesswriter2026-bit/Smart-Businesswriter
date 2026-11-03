import unittest
from decimal import Decimal

from bp import signs


class SignConventionTests(unittest.TestCase):
    def test_is_revenue_flips(self):
        meta = {"statement": "IS", "normal": "credit", "type": "income"}
        self.assertEqual(signs.SignConvention.for_statement(meta, Decimal("100")), Decimal("-100"))

    def test_is_expense_no_flip(self):
        meta = {"statement": "IS", "normal": "debit", "type": "expense"}
        self.assertEqual(signs.SignConvention.for_statement(meta, Decimal("100")), Decimal("100"))

    def test_bs_asset_no_contra(self):
        meta = {"statement": "BS", "type": "asset", "contra": False}
        self.assertEqual(signs.SignConvention.for_statement(meta, Decimal("100")), Decimal("100"))

    def test_bs_asset_contra(self):
        meta = {"statement": "BS", "type": "asset", "contra": True}
        self.assertEqual(signs.SignConvention.for_statement(meta, Decimal("100")), Decimal("-100"))

    def test_cf_raises(self):
        meta = {"statement": "CF"}
        with self.assertRaises(RuntimeError):
            signs.SignConvention.for_statement(meta, Decimal("100"))

    def test_delta_wc(self):
        class TB:
            def __init__(self, b):
                self.b = b
            def balance(self, code):
                return self.b[code]
        begin = TB({"1100": Decimal("0")})
        end = TB({"1100": Decimal("15000")})
        accounts = {"1100": {"cf_bucket": "operating_working_capital"}}
        res = signs.delta_wc(begin, end, accounts)
        self.assertEqual(res["1100"], Decimal("-15000"))


if __name__ == "__main__":
    unittest.main()
