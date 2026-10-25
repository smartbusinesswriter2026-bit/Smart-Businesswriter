"""Typed quantities and provenance (manual section 6). Decimal only; mismatches raise."""
from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_EVEN

PROVENANCE = {"user", "sourced", "assumption", "computed", "synthetic"}

class TypeMismatch(Exception): pass
class UntaggedNumber(Exception): pass

@dataclass(frozen=True)
class Quantity:
    value: Decimal
    unit: str = "currency"
    currency: str | None = None
    period: str | None = None
    scale: str = "units"
    precision: int = 2

    def __post_init__(self):
        if isinstance(self.value, float):
            raise TypeMismatch("binary floats are not allowed; pass str, int or Decimal")
        object.__setattr__(self, "value", Decimal(str(self.value)))

    def _key(self): return (self.unit, self.currency, self.period, self.scale)
    def _check(self, o):
        if not isinstance(o, Quantity) or self._key() != o._key():
            raise TypeMismatch(f"cannot combine {self._key()} with {getattr(o, '_key', lambda: o)()}")
    def __add__(self, o): self._check(o); return replace(self, value=self.value + o.value)
    def __sub__(self, o): self._check(o); return replace(self, value=self.value - o.value)
    def scaled(self, k): return replace(self, value=self.value * Decimal(str(k)))
    def display(self) -> str:
        q = Decimal(1).scaleb(-self.precision)
        v = self.value.quantize(q, rounding=ROUND_HALF_EVEN)
        if self.unit == "rate":
            return f"{(self.value * 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)}%"
        s = f"{abs(v):,.{self.precision}f}"
        if self.currency: return f"{self.currency} ({s})" if v < 0 else f"{self.currency} {s}"   # accounting convention (manual 9.5)
        return f"-{s}" if v < 0 else s

@dataclass(frozen=True)
class Tagged:
    id: str
    quantity: Quantity
    provenance: str
    rationale: str = ""
    def __post_init__(self):
        if self.provenance not in PROVENANCE:
            raise UntaggedNumber(f"{self.id}: provenance must be one of {sorted(PROVENANCE)}")
