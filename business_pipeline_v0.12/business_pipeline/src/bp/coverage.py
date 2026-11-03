"""Template coverage guard (G21)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class Diagnostic:
    stage: str
    gate: str
    input_ref: str
    expected: str
    actual: str
    hint: str


def check_template_coverage(matches, templates) -> List[Diagnostic]:
    issues = []
    for m in matches:
        if m.detector_id not in templates:
            issues.append(Diagnostic(stage="JOURNALIZE", gate="template_exists",
                                    input_ref=m.detector_id,
                                    expected=f"a template for detector {m.detector_id}",
                                    actual="none registered",
                                    hint=f"matched detector {m.detector_id} but no template"))
    return issues


def check_detector_coverage(claims, matches) -> List[Diagnostic]:
    matched = {getattr(m, "claim_id", None) for m in matches}
    issues = []
    for c in claims:
        cid = getattr(c, "id", None)
        kind = getattr(c, "kind", None)
        if kind == "transaction" and cid not in matched:
            issues.append(Diagnostic(stage="DETECT", gate="detector_coverage", input_ref=cid,
                                    expected="at least one detector match", actual="no detector matched",
                                    hint=f"claim: {getattr(c, 'text', c)!r}"))
    return issues
