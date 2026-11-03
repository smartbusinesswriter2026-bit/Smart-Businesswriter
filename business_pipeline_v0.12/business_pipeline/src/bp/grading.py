"""Grading and diff guard (G16)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List


@dataclass
class Mismatch:
    statement: str
    line: str
    expected: Decimal
    actual: Decimal | None
    diff: Decimal | None
    violated_rule: str
    hint: str


@dataclass
class GradeResult:
    is_correct: bool
    matches: List[str]
    mismatches: List[Mismatch]
    overall_score: float


def find_matching_line(stmt_lines, label):
    for l in stmt_lines:
        if l.get("label") == label:
            return l
    return None


def grade(user_statements: dict, expected_statements: dict) -> GradeResult:
    matches = []
    mismatches = []
    total = 0
    for stmt in ["IS", "RE", "BS", "CF"]:
        exp_lines = expected_statements.get(stmt, {}).get("lines", [])
        for line in exp_lines:
            if line.get("kind") in ("heading", "header", "spacer", "note"):
                continue
            total += 1
            user_line = find_matching_line(user_statements.get(stmt, {}).get("lines", []), line["label"])
            if user_line is None:
                mismatches.append(Mismatch(stmt, line["label"], Decimal(str(line["value"])), None, None,
                                          "missing_line", "line not present"))
                continue
            exp_val = Decimal(str(line["value"]))
            act_val = Decimal(str(user_line["value"]))
            if act_val == exp_val:
                matches.append(f"{stmt}.{line['label']}")
            else:
                mismatches.append(Mismatch(stmt, line["label"], exp_val, act_val,
                                          act_val - exp_val, "value_mismatch", "check computation"))
    score = (len(matches) / total) if total else 1.0
    return GradeResult(is_correct=(len(mismatches) == 0), matches=matches,
                       mismatches=mismatches, overall_score=score)
