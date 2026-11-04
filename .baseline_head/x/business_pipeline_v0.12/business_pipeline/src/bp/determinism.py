"""Determinism guard (G10)."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict


def hash_inputs(problem_text: str, schema_version: str) -> str:
    return hashlib.sha256(f"{schema_version}|{problem_text}".encode()).hexdigest()


def hash_outputs(statements: dict, tb_balances: dict) -> str:
    canonical = json.dumps({
        "statements": statements,
        "tb": {code: str(tb_balances[code]) for code in sorted(tb_balances)},
    }, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


class DeterminismFailure(Exception):
    pass


def assert_deterministic(run_fn: Callable[[str], Dict[str, Any]], problem_text: str, runs: int = 3) -> None:
    hashes = []
    for _ in range(runs):
        res = run_fn(problem_text)
        hashes.append(res.get("output_hash"))
    if len(set(hashes)) > 1:
        raise DeterminismFailure(f"outputs differ across runs: {hashes}")
