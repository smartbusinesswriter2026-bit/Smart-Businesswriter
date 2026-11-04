"""Root-cause diagnostic guard (G11)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class Diagnostic:
    stage: str
    gate: str
    input_ref: Any = None
    expected: Any = None
    actual: Any = None
    hint: str = ""
    severity: Literal["fail", "warn"] = "fail"

    def __str__(self) -> str:
        return (f"[{self.severity}] {self.stage}.{self.gate} on {self.input_ref}\n"
                f"  expected: {self.expected}\n"
                f"  actual:   {self.actual}\n"
                f"  hint:     {self.hint}")
