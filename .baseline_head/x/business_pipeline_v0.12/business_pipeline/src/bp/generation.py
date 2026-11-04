"""Verified problem generation guard (G17)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Tuple


@dataclass
class ProblemSpec:
    scenario: str
    transactions: list
    adjustments: list
    policies: dict
    given_facts: dict


def render_problem_text(spec: ProblemSpec) -> str:
    lines = [spec.scenario]
    for t in spec.transactions:
        lines.append(str(t))
    for a in spec.adjustments:
        lines.append(str(a))
    for k, v in spec.policies.items():
        lines.append(f"{k}: {v}")
    for k, v in spec.given_facts.items():
        lines.append(f"{k}: {v}")
    return "\n".join(lines)


def generate_problem(spec: ProblemSpec, run_pipeline: Callable[[str], dict]) -> Tuple[str, Any]:
    text = render_problem_text(spec)
    result = run_pipeline(text)
    if result.get("status") != "ok":
        raise ValueError(f"generated problem is not solvable: {result.get('diagnostics')}")
    return text, result.get("statements")
