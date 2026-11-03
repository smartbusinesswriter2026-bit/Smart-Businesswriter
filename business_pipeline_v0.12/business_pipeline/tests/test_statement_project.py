import unittest
from decimal import Decimal

from bp import statement_project as sp


class _TB:
    def __init__(self, b):
        self.b = b
    def balance(self, code):
        return self.b.get(code, Decimal(0))


class ProjectionTests(unittest.TestCase):
    def test_is(self):
        tb = _TB({"4000": Decimal("-100"), "5000": Decimal("30")})
        accounts = {
            "4000": {"statement": "IS", "type": "income", "normal": "credit", "name": "Revenue"},
            "5000": {"statement": "IS", "type": "expense", "normal": "debit", "name": "Expense"},
        }
        lines = sp.project_is(tb, accounts)
        self.assertEqual(lines[-1]["label"], "Net income")
        self.assertEqual(lines[-1]["amount"], Decimal("70.00"))

    def test_re(self):
        lines = sp.project_re(Decimal("0"), Decimal("70"), Decimal("0"))
        self.assertEqual(lines[-1]["amount"], Decimal("70.00"))

    def test_bs_balances(self):
        tb = _TB({"1000": Decimal("100"), "2000": Decimal("-30"), "3000": Decimal("-70")})
        accounts = {
            "1000": {"statement": "BS", "type": "asset", "normal": "debit", "name": "Cash", "contra": False},
            "2000": {"statement": "BS", "type": "liability", "normal": "credit", "name": "AP", "contra": False},
            "3000": {"statement": "BS", "type": "equity", "normal": "credit", "name": "RE", "contra": False},
        }
        lines = sp.project_bs(tb, accounts)
        totals = {l["label"]: l["amount"] for l in lines if l["kind"] == "total"}
        self.assertEqual(totals["Total assets"], Decimal("100.00"))
        self.assertEqual(totals["Total liabilities and equity"], Decimal("100.00"))


if __name__ == "__main__":
    unittest.main()
