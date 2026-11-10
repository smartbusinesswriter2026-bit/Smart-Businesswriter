"""RRA background job — the scheduled sweep.

Mirrors the autoresearch loop: a background thread, a start/stop switch, a
status the admin panel can read, and nothing that starts by itself
(BP_RELEVANCE_AUTOSTART defaults to 0).  The job only runs sweeps; it never
approves a gap and never writes outside the RRA's own folders.
"""
import os
import threading
import time
from datetime import datetime, timezone

from . import storage
from . import config as _config
from .runner import run_sweep

_lock = threading.Lock()

_state = {
    "running": False,
    "stopped": False,
    "thread": None,
    "current_run": None,
    "sweeps_run": 0,
    "last_run": None,
    "last_error": "",
    "status_message": "idle",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def status():
    """The RRA's status for the admin panel.  Never raises."""
    with _lock:
        state = dict(_state)
    state["config"] = _config.describe()
    state["pending_decisions"] = len(_pending())
    return state


def _pending():
    try:
        from .s7_gate import pending_decisions
        return pending_decisions()
    except Exception:
        return []


def start(url_list=None, use_model=True, discover=True):
    """Start the background sweep.  Returns (ok, message)."""
    with _lock:
        if _state["running"]:
            return False, "the relevance sweep is already running"
        _state["running"] = True
        _state["stopped"] = False
        _state["last_error"] = ""
        _state["status_message"] = "starting"
        thread = threading.Thread(target=_loop, args=(url_list, use_model, discover),
                                  daemon=True)
        _state["thread"] = thread
    thread.start()
    return True, "the relevance sweep has started"


def stop():
    """Ask the background sweep to stop after the current step."""
    with _lock:
        if not _state["running"]:
            return False, "the relevance sweep is not running"
        _state["stopped"] = True
        _state["status_message"] = "stopping"
    return True, "the relevance sweep will stop after the current step"


def run_once(url_list=None, use_model=True, discover=True):
    """Run one sweep in the foreground.  Returns the sweep result."""
    result = run_sweep(url_list=url_list, use_model=use_model, discover=discover,
                       delay=_config.delay())
    with _lock:
        _state["sweeps_run"] += 1
        _state["last_run"] = _now_iso()
        _state["current_run"] = result.get("run_id")
        _state["last_error"] = result.get("error", "") if isinstance(result, dict) else ""
        _state["status_message"] = "idle"
    return result


def _loop(url_list, use_model, discover):
    """The background thread's body: one sweep, then sleep until the interval."""
    interval = _config.interval()
    try:
        with _lock:
            if _state["stopped"]:
                _state["running"] = False
                return
            _state["status_message"] = "sweeping"
        run_once(url_list=url_list, use_model=use_model, discover=discover)
    except Exception as error:
        with _lock:
            _state["last_error"] = str(error)[:200]
            _state["status_message"] = "idle"
    with _lock:
        _state["running"] = False
        _state["status_message"] = "idle"

    # Sleep in short steps so a stop is honoured quickly.
    waited = 0
    while waited < interval:
        with _lock:
            if _state["stopped"]:
                _state["stopped"] = False
                return
        time.sleep(min(5, max(0, interval - waited)))
        waited += 5


def autostart():
    """Start the job at boot when the owner asked for it.  Off by default."""
    if not _config.autostart():
        return False, "autostart is off (BP_RELEVANCE_AUTOSTART=0)"
    return start()
