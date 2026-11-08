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
    """Percentage of logged errors that are closed (resolved, invalid or dismissed).

    The old metric ran four pytest suites every cycle.  That measured the test
    suite, not the loop's own work, and it could not tell a fixed error from an
    unrelated green test.  This one reads the error log the loop actually acts
    on, so a verified fix moves it and a nothing-done cycle does not.

    The denominator is every logged error, not the open list: counting only open
    rows made a closed error vanish from both the numerator and the denominator,
    so the panel read "0 % closed" however much the loop repaired.
    """
    errors = _ops_log.merge_resolved(_ops_log.list_errors(limit=1000, status="all"))
    if not errors:
        return 100.0
    closed = sum(1 for row in errors
                 if row.get("resolved") or row.get("invalid") or row.get("dismissed"))
    return round(100.0 * closed / len(errors), 2)


# ── Problem generation ─────────────────────────────────────────────────────

def _pick_highest_impact_error(exclude=None):
    """Pick the most frequent/severe open error that is left unattended.

    The owner's rule: the Karpathy loop only works on errors nobody is
    handling. Errors opened in the Self-Healing panel are marked attended and
    are skipped until resolved.  `exclude` is the set of error ids this session
    has already attempted, so one permanent failure cannot be retried forever.
    """
    exclude = exclude or set()
    errors = _ops_log.list_errors(limit=100)
    errors = _ops_log.merge_resolved(errors)
    open_all = [e for e in errors
                if not e.get("resolved") and not e.get("attended")
                and not e.get("invalid") and not e.get("dismissed")
                and (e.get("error_id") not in exclude)]
    open_errors = [e for e in open_all
                   if e.get("problem") or e.get("case_id")]
    if not open_errors:
        # Count how many open errors we refused to touch, so the status line
        # explains why the loop is doing nothing instead of looping silently.
        if open_all:
            with _lock:
                _state["status_message"] = ("%d open error(s), none replayable - waiting for owner"
                                           % len(open_all))
            return None
        return None
    # Sort by severity (severe first) then by count
    severity_rank = {"severe": 0, "moderate": 1, "light": 2}
    open_errors.sort(key=lambda e: (severity_rank.get(e.get("severity", "moderate"), 1), -e.get("count", 1)))
    return open_errors[0]


def _run_experiment(error):
    """Attempt one fix, in the cheapest honest order.

    1. A stored tile case is replayed by code (no model, no tokens).
    2. An error with a stored problem is resolved by the fix ladder
       (deepseek-v4.1-flash, then deepseek-v4-pro); replay must pass.
    3. An error with neither is left to the owner: generating a problem from
       an unreplayable error spends tokens and cannot verify a fix.
    """
    from . import auto_resolve

    exp = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "error": error.get("error", "")[:200],
        "error_id": error.get("error_id", ""),
        "severity": error.get("severity", "moderate"),
        "case_id": error.get("case_id") or "",
    }
    exp["baseline_metric"] = _measure_metric()

    if not error.get("case_id") and not error.get("problem"):
        exp["outcome"] = "no_replayable_problem"
        exp["reason"] = ("no stored problem or case id; skipped without a model call")
        exp["after_metric"] = exp["baseline_metric"]
        _log_experiment(exp)
        return exp

    result = auto_resolve.resolve(error.get("error_id", ""))
    exp["category"] = result.get("category") or ""
    exp["model"] = result.get("model") or ""
    exp["steps"] = result.get("steps") or []
    exp["verified"] = bool(result.get("verified"))
    exp["problems_solved"] = 1 if result.get("verified") else 0
    exp["problems_failed"] = 0 if result.get("verified") else 1
    exp["outcome"] = "kept" if result.get("verified") else "still_failing"
    exp["reason"] = result.get("reason") or ""
    exp["after_metric"] = _measure_metric()
    _log_experiment(exp)
    return exp


def _run_case_suite():
    """Replay every stored tile case; failures become open tile-case errors."""
    try:
        from . import case_runner, case_store
        ids = [case["id"] for case in case_store.load_cases()]
        if not ids:
            return {"total": 0, "passed": 0, "failed": 0}
        return case_runner.run_cases(ids)
    except Exception as error:
        return {"total": 0, "passed": 0, "failed": 0, "error": str(error)[:200]}


# ── Main loop ──────────────────────────────────────────────────────────────

def _loop():
    """Main autoresearch loop. Runs in background thread."""
    global _state
    # Work through the queue: 30 s between cycles, not an hour.  The owner's queue of
    # open errors should drain in minutes, not days.
    interval = int(os.environ.get("BP_AUTORESEARCH_INTERVAL", "30"))
    max_exp = int(os.environ.get("BP_AUTORESEARCH_MAX_EXP", "3"))

    with _lock:
        _state["running"] = True
        _state["stopped"] = False
        _state["status_message"] = "running"

    attempted = set()  # error ids this session has tried, so a permanent failure is not retried forever

    while not _state["stopped"]:
        try:
            # Check if all tests pass → stop
            metric = _measure_metric()
            with _lock:
                _state["current_metric"] = metric
                if _state["best_metric"] is None or metric > _state["best_metric"]:
                    _state["best_metric"] = metric
                _state["last_run"] = datetime.now(timezone.utc).isoformat()

            # Check for open errors, skipping the ones already tried this session
            error = _pick_highest_impact_error(exclude=attempted)
            if error is None:
                if attempted:
                    # Every open error has been tried once this session.  Clear the set
                    # so a new arrival is picked up, and sleep before a retry pass.
                    attempted.clear()
                    with _lock:
                        _state["status_message"] = "all open errors attempted — waiting"
                    time.sleep(interval)
                    continue
                # No unattended error: re-run the stored case suite, which is
                # the loop's own regression pass.  A failure becomes an open
                # tile-case error for the next cycle; a clean pass stops the
                # loop because there is nothing left to repair.
                if os.environ.get("BP_AUTORESEARCH_CASES", "1") != "0":
                    with _lock:
                        _state["status_message"] = "replaying the stored case suite"
                    suite = _run_case_suite()
                    with _lock:
                        _state["status_message"] = "case suite: %d passed / %d failed" % (
                            suite.get("passed", 0), suite.get("failed", 0))
                    if suite.get("failed"):
                        continue
                with _lock:
                    _state["status_message"] = ("all logged errors closed and the stored case suite "
                                                "passed — stopped")
                    _state["stopped"] = True
                    _state["running"] = False
                break

            # Run experiments
            with _lock:
                _state["status_message"] = "running experiments"

            exp = None
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
                # One attempt per error per cycle: a resolved error is done, and
                # an error with nothing to replay will say the same thing again.
                # Repeating it would only fill the experiment log.
                if exp.get("outcome") in ("kept", "applied", "no_replayable_problem",
                                          "still_failing", "reverted", "rejected"):
                    break

            attempted.add(error.get("error_id"))
            if exp is not None and exp.get("outcome") == "still_failing":
                # The loop tried and could not fix it: mark it attended so it stops
                # blocking the queue and waits for the owner rather than being retried
                # on the next cycle.
                _ops_log.mark_error_attended(error.get("error_id"))

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