"""RRA configuration.

Mirrors the autoresearch switch so the owner controls the RRA the same way:
nothing starts by itself, and every budget has a default.

    BP_RELEVANCE_ENABLED          1/0 — forbid every model call (default 1)
    BP_RELEVANCE_PROVIDER         provider id (default: BP_LLM_PROVIDER)
    BP_RELEVANCE_MODEL            model id (default: BP_LLM_MODEL)
    BP_RELEVANCE_EXTRACT_MODEL    model for S2 (the passage that matters)
    BP_RELEVANCE_DESIGN_MODEL     model for S5 (the gap spec)
    BP_RELEVANCE_DISCOVERY_MODEL  model for S1b (the search query)
    BP_RELEVANCE_MAX_PAGES        page budget per sweep (default 50)
    BP_RELEVANCE_BUDGET_TOKENS    token budget per sweep (default 200000)
    BP_RELEVANCE_MAX_TOKENS       per-call output cap (default 2000)
    BP_RELEVANCE_MAX_INPUT        per-call input cap (default 30000)
    BP_RELEVANCE_INTERVAL         seconds between scheduled sweeps (default 2592000 = 30 days)
    BP_RELEVANCE_AUTOSTART        1/0 — start a sweep at server boot (default 0)
    BP_RELEVANCE_DISCOVER         1/0 — let the pipeline search for pages (default 1)
    BP_RELEVANCE_DELAY            seconds between fetches (default 0.5)
    BP_RELEVANCE_STATE_DIR        override the state directory
"""
import os

DEFAULT_MAX_PAGES = 50
DEFAULT_BUDGET_TOKENS = 200000
DEFAULT_MAX_TOKENS = 2000
DEFAULT_MAX_INPUT = 30000
DEFAULT_INTERVAL = 2592000   # 30 days
DEFAULT_DELAY = 0.5


def _int(name, default):
    try:
        return int(os.environ.get(name, str(default)))
    except (TypeError, ValueError):
        return default


def _flag(name, default="1"):
    return os.environ.get(name, default) != "0"


def max_pages():
    return _int("BP_RELEVANCE_MAX_PAGES", DEFAULT_MAX_PAGES)


def budget_tokens():
    return _int("BP_RELEVANCE_BUDGET_TOKENS", DEFAULT_BUDGET_TOKENS)


def max_tokens():
    return _int("BP_RELEVANCE_MAX_TOKENS", DEFAULT_MAX_TOKENS)


def max_input():
    return _int("BP_RELEVANCE_MAX_INPUT", DEFAULT_MAX_INPUT)


def interval():
    return _int("BP_RELEVANCE_INTERVAL", DEFAULT_INTERVAL)


def autostart():
    return _flag("BP_RELEVANCE_AUTOSTART", "0")


def discover():
    return _flag("BP_RELEVANCE_DISCOVER", "1")


def delay():
    try:
        value = float(os.environ.get("BP_RELEVANCE_DELAY", str(DEFAULT_DELAY)))
        return max(0.0, value)
    except (TypeError, ValueError):
        return DEFAULT_DELAY


def max_schools():
    """How many schools one sweep covers.

    The frame has twenty-five schools and the sweep asks every topic of every
    school, so an unbounded sweep spends its whole search budget on the first
    few schools and never reaches the rest.  The bound is reported with the
    run, so a partial sweep never reads as a complete one.
    """
    return _int("BP_RELEVANCE_MAX_SCHOOLS", 0)   # 0 = the whole frame


def model_enabled():
    return _flag("BP_RELEVANCE_ENABLED", "1")


def describe():
    """What the RRA would do, for the admin panel.  Never exposes a key."""
    from . import model as _model
    info = _model.describe()
    info.update({
        "max_pages": max_pages(),
        "budget_tokens": budget_tokens(),
        "interval_seconds": interval(),
        "autostart": autostart(),
        "discover": discover(),
        "delay_seconds": delay(),
    })
    return info
