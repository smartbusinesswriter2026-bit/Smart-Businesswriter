"""Extraction guards (G19, G20)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List


EXTRACTION_CONFIDENCE_THRESHOLD = 0.85


@dataclass
class Match:
    detector_id: str
    claim_id: str
    slots: dict
    confidence: float
    slot_confidences: dict
    source_span: tuple


def route_low_confidence(matches: List[Match]) -> List[Match]:
    return [m for m in matches if m.confidence < EXTRACTION_CONFIDENCE_THRESHOLD]


def route_low_confidence_slots(matches: List[Match]):
    low = []
    for m in matches:
        for slot, conf in (m.slot_confidences or {}).items():
            if conf < EXTRACTION_CONFIDENCE_THRESHOLD:
                low.append((m, slot))
    return low


def is_grounded(value, source_text: str) -> bool:
    if isinstance(value, str):
        return value.lower() in source_text.lower()
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, Decimal)):
        candidates = [str(value), f"{value:,}", f"${value:,}", f"${value}"]
        return any(c in source_text for c in candidates)
    return True


def verify_grounded(match: Match, source_text: str) -> List[str]:
    issues = []
    for slot, value in (match.slots or {}).items():
        if not is_grounded(value, source_text):
            issues.append(slot)
    return issues
