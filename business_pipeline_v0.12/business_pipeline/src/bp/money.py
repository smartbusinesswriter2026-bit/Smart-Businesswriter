"""Decimal arithmetic guard (G2).

All money values are Decimal. q() is the ONLY rounding function, called only at render
time. No float, no mid-computation rounding.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

MONEY = Decimal("0.01")


def q(x) -> Decimal:
    """The only rounding function. Called only by renderers."""
    return Decimal(str(x)).quantize(MONEY, rounding=ROUND_HALF_UP)


def money(x) -> Decimal:
    """Coerce any input to Decimal without float contamination."""
    if isinstance(x, bool):
        raise ValueError("bool is not a money value")
    if isinstance(x, float):
        raise ValueError("float is not allowed for money; pass str or Decimal")
    return Decimal(str(x))
