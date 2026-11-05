"""Automated test runner for the admin monitor (product layer, stdlib only).

Runs pytest suites and returns structured results. Uses subprocess to invoke
pytest so it works with the existing test infrastructure without importing
test modules into the server process.

Suites:
    computations  -> tests/test_methods.py + test_schedule_routes.py
    frameworks    -> tests/test_completion.py + test_conductor_frameworks.py
    prose         -> tests/test_prose.py + test_plan_verifier.py
    paper         -> tests/test_chat.py + test_business_plan_profile.py

Results are stored under state/test_results/ as JSONL.
"""
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

from . import ops as ops_mod

# Suite -> list of test file globs (relative to repo root)
SUITES = {
    "computations": [
        "tests/test_methods.py",
        "tests/test_schedule_routes.py",
        "tests/test_statement_plan.py",
    ],
    "frameworks": [
        "tests/test_completion.py",
        "tests/test_conductor_frameworks.py",
        "tests/test_pestel_completion.py",
    ],
    "prose": [
        "tests/test_prose.py",
        "tests/test_plan_verifier.py",
        "tests/test_plan_corpus.py",
    ],
    "paper": [
        "tests/test_chat.py",
        "tests/test_business_plan_profile.py",
        "tests/test_capability_papers.py",
    ],
}


def _repo_root():
    return ops_mod.repo_root()


def _results_dir():
    d = ops_mod.state_dir() / "test_results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _results_path():
    return _results_dir() / "results.jsonl"


def _run_pytest(files):
    """Run pytest on a list of files, return (passed, failed, total, failures, duration)."""
    root = _repo_root()
    cmd = [sys.executable, "-m", "pytest"] + files + ["-q", "--tb=short", "-p", "no:cacheprovider"]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(root / "src")
    env["BP_STATEMENT_LIBRARY_DIR"] = str(root / "state" / "test_lib")
    start = datetime.datetime.now(datetime.timezone.utc)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            cwd=str(root), env=env)
    except subprocess.TimeoutExpired:
        return 0, 0, 0, ["TIMEOUT after 300s"], 300000
    duration = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds() * 1000

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    # Parse pytest summary line: "X passed, Y failed" or "X passed"
    passed = 0
    failed = 0
    total = 0
    for line in stdout.splitlines() + stderr.splitlines():
        line = line.strip()
        if "passed" in line or "failed" in line or "error" in line:
            # Try to extract numbers
            import re
            m_passed = re.search(r"(\d+)\s+passed", line)
            m_failed = re.search(r"(\d+)\s+failed", line)
            m_error = re.search(r"(\d+)\s+error", line)
            if m_passed:
                passed = int(m_passed.group(1))
            if m_failed:
                failed = int(m_failed.group(1))
            if m_error:
                failed += int(m_error.group(1))

    total = passed + failed

    # Extract failure names
    failures = []
    for line in stdout.splitlines():
        if line.startswith("FAILED") or "FAILED" in line:
            # Extract test name
            parts = line.split("::")
            if len(parts) >= 2:
                failures.append(parts[-1].strip()[:120])
            elif line.strip():
                failures.append(line.strip()[:120])
    if not failures and failed > 0:
        # Fall back to last few lines
        for line in (stdout + stderr).splitlines()[-10:]:
            if line.strip():
                failures.append(line.strip()[:120])

    return passed, failed, total, failures[:20], round(duration, 1)


def run_suite(suite_name):
    """Run one suite, store result, return dict."""
    files = SUITES.get(suite_name)
    if not files:
        return {"suite": suite_name, "error": "unknown suite", "passed": 0, "failed": 0, "total": 0, "failures": []}

    # Filter to existing files
    root = _repo_root()
    existing = [f for f in files if (root / f).is_file()]
    if not existing:
        return {"suite": suite_name, "error": "no test files found", "passed": 0, "failed": 0, "total": 0, "failures": []}

    passed, failed, total, failures, duration = _run_pytest(existing)
    result = {
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "suite": suite_name,
        "passed": passed,
        "failed": failed,
        "total": total,
        "failures": failures,
        "duration_ms": duration,
        "files": existing,
    }
    # Store
    try:
        path = _results_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(result, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass
    return result


def list_results(limit=20):
    """Return recent test results, newest first."""
    path = _results_path()
    if not path.is_file():
        return []
    rows = []
    try:
        with open(path, encoding="utf-8") as stream:
            for line in stream:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    rows.reverse()
    return rows[:limit]


def suites():
    """Return the list of available suites."""
    return list(SUITES.keys())
