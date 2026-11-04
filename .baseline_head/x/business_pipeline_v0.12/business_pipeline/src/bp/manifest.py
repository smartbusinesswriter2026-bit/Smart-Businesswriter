"""Convention lock guard (G7): Manifest with require() that raises on None."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal


class ReviewRequired(Exception):
    pass


@dataclass
class Manifest:
    inventory_system: str | None = None
    purchase_discount_method: str | None = None
    accounting_standard: str | None = None
    depreciation_convention: str | None = None
    interest_timing: str | None = None
    tax_rate: Decimal | None = None
    freight_terms: str | None = None

    def require(self, field_name: str) -> Any:
        val = getattr(self, field_name)
        if val is None:
            raise ReviewRequired(f"policy required: {field_name}")
        return val

    def to_dict(self):
        return {
            "inventory_system": self.inventory_system,
            "purchase_discount_method": self.purchase_discount_method,
            "accounting_standard": self.accounting_standard,
            "depreciation_convention": self.depreciation_convention,
            "interest_timing": self.interest_timing,
            "tax_rate": self.tax_rate,
            "freight_terms": self.freight_terms,
        }
