"""Golden regression tests for deterministic problem normalizers.

Every fix verified by the pipeline is pinned in
`qa/regression/problem_norm_cases.jsonl`. This suite replays the whole file on
every test run, so a normalizer change that would reintroduce a fixed failure
fails here instead of showing up as a new error in production.

The suite is deliberately model-free: it proves the normalisation contract and
that the frozen deterministic reader accepts the normalised text where the
capture recorded that it did.
"""
import json
from pathlib import Path

import pytest

from bp.product.problem_norm import normalize_problem

CASES_PATH = (Path(__file__).resolve().parents[1] / "qa" / "regression"
              / "problem_norm_cases.jsonl")


def _cases():
    if not CASES_PATH.is_file():
        return []
    rows = []
    with open(CASES_PATH, encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return rows


CASES = _cases()


def test_case_file_parses():
    assert isinstance(CASES, list)


@pytest.mark.parametrize("case", CASES or [None], ids=lambda c: (c or {}).get("error_id", "empty"))
def test_golden_normalization_is_stable(case):
    if case is None:
        pytest.skip("no harvested regression cases yet")
    normalized, notes = normalize_problem(case["original"])
    assert normalized == case["normalized"], "normalizer output drifted from the recorded case"
    assert notes == case.get("notes", notes)


@pytest.mark.parametrize("case", CASES or [None], ids=lambda c: (c or {}).get("error_id", "empty"))
def test_normalization_is_idempotent(case):
    if case is None:
        pytest.skip("no harvested regression cases yet")
    again, second_notes = normalize_problem(case["normalized"])
    assert again == case["normalized"]
    assert second_notes == []


@pytest.mark.parametrize("case", CASES or [None], ids=lambda c: (c or {}).get("error_id", "empty"))
def test_deterministic_reader_still_accepts(case):
    if case is None:
        pytest.skip("no harvested regression cases yet")
    if not case.get("deterministic_ok"):
        pytest.skip("capture recorded that a model read is required")
    from bp.product import statements
    rows = statements.read_deterministic(case["normalized"])
    assert rows, "the frozen reader no longer accepts a case it once accepted"
