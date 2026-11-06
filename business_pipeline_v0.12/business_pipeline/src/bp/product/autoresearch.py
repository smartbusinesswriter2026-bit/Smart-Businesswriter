"""Autonomous self-healing research loop (product layer, stdlib only).

Inspired by Karpathy's autoresearch: iteratively proposes fixes, tests them
against a single scalar metric (test pass rate), keeps improvements and
reverts regressions. Runs in the background until all tests pass or manually
stopped.

Trigger: runs when there are open errors or on a schedule (twice daily).
Non-intrusive: logs to state/, no popups, no notifications. Check status
via admin UI or GET /api/ops/autoresearch/status.

Uses cheap/free models by default (beam-free, nemotron). Configurable via:
  BP_AUTORESEARCH_MODEL   model id (default: deepseek-chat)
  BP_AUTORESEARCH_INTERVAL  seconds between cycles (default: 3600 = 1 hour)
  BP_AUTORESEARCH_MAX_EXP  max experiments per cycle (default: 3)
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from . import ops as ops_mod
from . import ops_log as _ops_log

# ── State ──────────────────────────────────────────────────────────────────

_state = {
    "running": False,
    "stopped": False,
    "thread": None,
    "current_metric": None,
    "best_metric": None,
    "experiments_run": 0,
    "experiments_kept": 0,
    "experiments_reverted": 0,
    "last_run": None,
    "status_message": "idle",
}
_lock = threading.Lock()


def _state_dir():
    return ops_mod.state_dir() / "autoresearch"


def _experiments_path():
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / "experiments.jsonl"


def _log_experiment(exp):
    try:
        path = _experiments_path()
        with open(path, "a", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(exp, ensure_ascii=False, default=str) + "\n")
    except OSError:
        pass


def _read_experiments(limit=50):
    path = _experiments_path()
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
    rows.reverse()
    return rows[:limit]


# ── Git helpers ────────────────────────────────────────────────────────────

def _git(args, cwd=None):
    """Run a git command, return (success, output)."""
    root = ops_mod.repo_root()
    try:
        proc = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, timeout=60,
            cwd=str(cwd or root))
        return proc.returncode == 0, (proc.stdout or proc.stderr or "").strip()
    except Exception as e:
        return False, str(e)[:200]


def _ensure_branch():
    """Create or checkout the autoresearch branch."""
    ok, branch = _git(["branch", "--show-current"])
    if ok and branch == "autoresearch/experiments":
        return True
    # Create branch if it doesn't exist
    ok, _ = _git(["rev-parse", "--verify", "autoresearch/experiments"])
    if not ok:
        ok, _ = _git(["branch", "autoresearch/experiments"])
        if not ok:
            return False
    ok, _ = _git(["checkout", "autoresearch/experiments"])
    return ok


def _commit_experiment(message):
    """Commit current changes, return (success, commit_hash)."""
    _git(["add", "-A"])
    ok, out = _git(["commit", "-m", message])
    if ok:
        # Get commit hash
        ok2, hash_out = _git(["rev-parse", "HEAD"])
        return ok2, (hash_out[:12] if ok2 else None)
    return False, None


def _revert_last():
    """Revert the last commit."""
    ok, _ = _git(["revert", "--no-edit", "HEAD"])
    return ok


# ── Metric ─────────────────────────────────────────────────────────────────

def _measure_metric():
    """Run the test suite and return pass rate (0-100)."""
    from . import test_runner
    # Run core suites
    total_passed = 0
    total_tests = 0
    for suite in ["computations", "frameworks", "prose", "paper"]:
        result = test_runner.run_suite(suite)
        total_passed += result.get("passed", 0)
        total_tests += result.get("total", 0)
    if total_tests == 0:
        return 0.0
    return round(total_passed / total_tests * 100, 2)


# ── Problem generation ─────────────────────────────────────────────────────

def _pick_highest_impact_error():
    """Pick the most frequent/severe open error."""
    errors = _ops_log.list_errors(limit=100)
    errors = _ops_log.merge_resolved(errors)
    open_errors = [e for e in errors if not e.get("resolved")]
    if not open_errors:
        return None
    # Sort by severity (severe first) then by count
    severity_rank = {"severe": 0, "moderate": 1, "light": 2}
    open_errors.sort(key=lambda e: (severity_rank.get(e.get("severity", "moderate"), 1), -e.get("count", 1)))
    return open_errors[0]


def _run_experiment(error):
    """Run one experiment: generate problems, solve, propose fix, apply, test."""
    from . import chat_heal
    from . import hallucination_check

    exp = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "error": error.get("error", "")[:200],
        "error_id": error.get("error_id", ""),
        "severity": error.get("severity", "moderate"),
    }

    # Step 1: Generate problems
    count = _ops_log.severity_count(error.get("severity", "moderate"))
    problems, instruction, err = chat_heal.generate_problems_from_error(
        error.get("error", ""), count)
    exp["problems_generated"] = len(problems)
    if err or not problems:
        exp["outcome"] = "no_problems"
        exp["reason"] = err or "no problems generated"
        _log_experiment(exp)
        return exp

    # Step 2: Solve
    results, _ = chat_heal.solve_problems(problems)
    failures = [r for r in results if r.get("status") in ("error", "logged")]
    exp["problems_solved"] = len(results) - len(failures)
    exp["problems_failed"] = len(failures)

    # Step 3: Propose fix (if failures)
    improvements = []
    if failures:
        improvements, _ = chat_heal.write_improvements(
            [{"problem": f.get("problem", ""), "error": f.get("error", "")} for f in failures])
    exp["improvements_proposed"] = len(improvements)

    # Step 4: Measure baseline metric
    baseline_metric = _measure_metric()
    exp["baseline_metric"] = baseline_metric

    # Step 5: Apply fix (if proposals exist)
    from . import statements as _stmt
    proposals = []
    try:
        import urllib.request, json as _json
        # Get pending proposals from statements
        pass
    except Exception:
        pass

    # For now, log the experiment without applying (computation owner needs to expose heal API)
    # The fix application is documented as a request for the computation owner
    exp["outcome"] = "proposed"
    exp["reason"] = "Fix proposed but not auto-applied (needs computation owner heal API)"
    exp["after_metric"] = baseline_metric

    # Step 6: Log
    _log_experiment(exp)
    return exp


# ── Main loop ──────────────────────────────────────────────────────────────

def _loop():
    """Main autoresearch loop. Runs in background thread."""
    global _state
    interval = int(os.environ.get("BP_AUTORESEARCH_INTERVAL", "3600"))
    max_exp = int(os.environ.get("BP_AUTORESEARCH_MAX_EXP", "3"))

    with _lock:
        _state["running"] = True
        _state["stopped"] = False
        _state["status_message"] = "running"

    while not _state["stopped"]:
        try:
            # Check if all tests pass → stop
            metric = _measure_metric()
            with _lock:
                _state["current_metric"] = metric
                if _state["best_metric"] is None or metric > _state["best_metric"]:
                    _state["best_metric"] = metric
                _state["last_run"] = datetime.now(timezone.utc).isoformat()

            if metric >= 100.0:
                with _lock:
                    _state["status_message"] = "all tests pass — stopped"
                    _state["stopped"] = True
                    _state["running"] = False
                break

            # Check for open errors
            error = _pick_highest_impact_error()
            if error is None:
                with _lock:
                    _state["status_message"] = "no open errors — sleeping"
                time.sleep(interval)
                continue

            # Run experiments
            with _lock:
                _state["status_message"] = "running experiments"

            for i in range(max_exp):
                if _state["stopped"]:
                    break
                exp = _run_experiment(error)
                with _lock:
                    _state["experiments_run"] += 1
                    if exp.get("outcome") in ("kept", "applied"):
                        _state["experiments_kept"] += 1
                    elif exp.get("outcome") in ("reverted", "rejected"):
                        _state["experiments_reverted"] += 1

            # Sleep between cycles
            with _lock:
                _state["status_message"] = "sleeping"
            time.sleep(interval)

        except Exception as e:
            with _lock:
                _state["status_message"] = "error: %s" % str(e)[:200]
            time.sleep(60)

    with _lock:
        _state["running"] = False
        if not _state["stopped"]:
            _state["stopped"] = True


# ── Public API ─────────────────────────────────────────────────────────────

def start():
    """Start the autoresearch loop in a background thread."""
    with _lock:
        if _state["running"]:
            return False, "already running"
        _state["stopped"] = False
        _state["thread"] = threading.Thread(target=_loop, daemon=True)
        _state["thread"].start()
    return True, "started"


def stop():
    """Stop the autoresearch loop."""
    with _lock:
        _state["stopped"] = True
    if _state["thread"] and _state["thread"].is_alive():
        _state["thread"].join(timeout=10)
    with _lock:
        _state["running"] = False
        _state["status_message"] = "stopped"
    return True, "stopped"


def status():
    """Return current status."""
    with _lock:
        return {
            "running": _state["running"],
            "stopped": _state["stopped"],
            "current_metric": _state["current_metric"],
            "best_metric": _state["best_metric"],
            "experiments_run": _state["experiments_run"],
            "experiments_kept": _state["experiments_kept"],
            "experiments_reverted": _state["experiments_reverted"],
            "last_run": _state["last_run"],
            "status_message": _state["status_message"],
        }


def experiments(limit=50):
    """Return experiment history."""
    return _read_experiments(limit=limit)