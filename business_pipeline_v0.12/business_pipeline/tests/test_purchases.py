import unittest
from decimal import Decimal

from bp import purchases as pc


class PurchasesTests(unittest.TestCase):
    def test_harbor_light(self):
        p = pc.PurchasesLedger(purchases=Decimal("52000"), freight_in=Decimal("1500"),
                               purchase_returns=Decimal("2000"))
        cogs = pc.cogs_periodic(Decimal("0"), p, Decimal("8000"))
        self.assertEqual(cogs, Decimal("43500.00"))

    def test_missing_freight_understates(self):
        p = pc.PurchasesLedger(purchases=Decimal("52000"), purchase_returns=Decimal("2000"))
        cogs = pc.cogs_periodic(Decimal("0"), p, Decimal("8000"))
        self.assertEqual(cogs, Decimal("42000.00"))


if __name__ == "__main__":
    unittest.main()
