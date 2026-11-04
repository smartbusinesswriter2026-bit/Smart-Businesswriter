"""COGS composition guard (G3)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .money import q


@dataclass
class PurchasesLedger:
    purchases: Decimal
    freight_in: Decimal = Decimal("0")
    purchase_returns: Decimal = Decimal("0")
    purchase_discounts: Decimal = Decimal("0")

    def net_purchases(self) -> Decimal:
        return self.purchases + self.freight_in - self.purchase_returns - self.purchase_discounts


def cogs_periodic(beginning_inv: Decimal, p: PurchasesLedger, ending_inv: Decimal) -> Decimal:
    if beginning_inv is None or ending_inv is None:
        raise ValueError("beginning and ending inventory are required")
    return q(beginning_inv + p.net_purchases() - ending_inv)
