"""Golden regression cases harvested from verified fixes (product layer).

Every fix that a replay verified is written here, together with the exact
normalised text that made it pass. `tests/test_problem_norm_regression.py`
replays the whole file on every test run, so a behaviour that once worked
cannot silently regress: if a normalizer changes, the suite fails.

The file lives in the repository (not the state directory) on purpose: it is
part of the product's contract, reviewed with the code.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

_MAX_CASES = 500


def cases_path():
    """qa/regression/problem_norm_cases.jsonl at the repository root.

    `BP_REGRESSION_CASES` redirects it; the test suite points it at its own file so a
    mocked fix cannot write a golden case into the owner's real regression suite.
    """
    import os
    override = os.environ.get("BP_REGRESSION_CASES")
    if override:
        return Path(override)
    return (Path(__file__).resolve().parents[3] / "qa" / "regression"
            / "problem_norm_cases.jsonl")


def _key(original):
    return re.sub(r"\s+", " ", str(original or "").strip().lower())[:2000]


def list_cases():
    path = cases_path()
    if not path.is_file():
        return []
    rows = []
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except OSError:
        return []
    return rows


def record_case(error_id, category, original, normalized, notes, verified_by,
                deterministic_ok=False):
    """Append one golden case (idempotent per original text)."""
    if not original or not normalized or normalized == original and not notes:
        return False
    key = _key(original)
    for row in list_cases():
        if _key(row.get("original")) == key:
            return False
    path = cases_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "error_id": str(error_id or "")[:40],
        "category": str(category or "unknown")[:40],
        "notes": list(notes or []),
        "verified_by": str(verified_by or "")[:60],
        "deterministic_ok": bool(deterministic_ok),
        "original": str(original)[:2000],
        "normalized": str(normalized)[:2000],
    }
    with open(path, "a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    return True


def case_count():
    return len(list_cases())
