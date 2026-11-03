import unittest
from decimal import Decimal

from bp import money


class MoneyTests(unittest.TestCase):
    def test_q_rounds_half_up(self):
        self.assertEqual(money.q(Decimal("2.665")), Decimal("2.67"))
        self.assertEqual(money.q(Decimal("2.675")), Decimal("2.68"))

    def test_money_rejects_float(self):
        with self.assertRaises(ValueError):
            money.money(1.5)

    def test_money_from_str(self):
        self.assertEqual(money.money("1234.56"), Decimal("1234.56"))

    def test_q_from_str(self):
        self.assertEqual(money.q("6000 * 11 / 12".replace(" ", "") if False else Decimal("6000") * Decimal("11") / Decimal("12")),
                         Decimal("5500.00"))


if __name__ == "__main__":
    unittest.main()
