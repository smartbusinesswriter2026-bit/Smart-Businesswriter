"""Capabilities the owner can switch on and off — the loops and the search chain.

Everything here is **off by default**.  A switch that is turned on works
immediately: the loop starts on the next pass, the search provider joins the
chain for the next search.  A switch that is turned off stops the thing.

Two kinds of capability:

- **loop** — a background job the owner may run: the **repair loop**
  (`autoresearch`, which replays and fixes), the **growth loop**
  (`growth_loop`, which scaffolds a capability gap for a human to finish) and
  the **relevance loop** (the RRA sweep, which looks outward at what the
  curriculum and the standards now require).
- **search** — one provider in the RRA's search chain.  The chain is
  `brave -> firecrawl -> opengo`: Brave and Firecrawl are cheap, and
  `opengo` is the owner's backup — the OpenCode Go gateway running DeepSeek
  V4.1 Flash with its websearch tool — which answers when the other two
  rate-limit.

The state is a small JSON file under `state/`, so a switch survives a
restart.  A switch never changes a rule, a gate or a computation: it decides
whether a loop runs and which search providers answer.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

#: The capability registry.  `default` is what the system does with no owner
#: instruction: every loop is off.
CAPABILITIES = {
    "loop.repair": {
        "kind": "loop",
        "label": "Repair loop",
        "default": False,
        "description": "Replays open errors, fixes what it can by replay, and pins the fix "
                       "as a regression case. It creates nothing and applies no code.",
        "module": "bp.product.autoresearch",
    },
    "loop.growth": {
        "kind": "loop",
        "label": "Growth loop",
        "default": False,
        "description": "Turns an approved capability gap into a PROVISIONAL scaffold: a "
                       "method stub, a capability entry, a preset, a test sketch and a "
                       "README. Nothing is wired in and nothing is committed; a human "
                       "writes the method and runs the suite.",
        "module": "bp.product.growth_loop",
    },
    "loop.relevance": {
        "kind": "loop",
        "label": "Relevance loop",
        "default": False,
        "description": "Sweeps the sampling frame for what business schools teach, assess "
                       "and expect, and what has changed in the standards. Writes gap "
                       "specs and an obsolescence watchlist; it applies nothing.",
        "module": "bp.product.relevance.job",
    },
    "search.brave": {
        "kind": "search",
        "label": "Brave Search",
        "default": True,
        "description": "The cheap, fast web search the RRA uses first.",
        "order": 0,
    },
    "search.firecrawl": {
        "kind": "search",
        "label": "Firecrawl",
        "default": True,
        "description": "The second search provider: a scrape-and-search service that "
                       "answers when Brave rate-limits.",
        "order": 1,
    },
    "search.opengo": {
        "kind": "search",
        "label": "DeepSeek through OpenCode Go",
        "default": True,
        "description": "The owner's backup: a headless OpenCode session running DeepSeek "
                       "V4.1 Flash with its websearch tool. It is slower than the other "
                       "two and answers when they refuse.",
        "order": 2,
    },
}

#: The order the search providers are tried in.
DEFAULT_SEARCH_ORDER = ["brave", "firecrawl", "opengo"]

#: The env var that seeds a loop's switch the first time the system looks.
#: The default is **off**: a loop runs only when the owner says so.
LOOP_SEED_VARS = {
    "loop.repair": "BP_AUTORESEARCH_AUTOSTART",
    "loop.growth": "BP_GROWTH_AUTOSTART",
    "loop.relevance": "BP_RELEVANCE_AUTOSTART",
}


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _repo_root():
    return Path(__file__).resolve().parents[3]


def _state_path():
    state = os.environ.get("BP_STATE_DIR")
    base = Path(state) if state else (_repo_root() / "state")
    return base / "ops_switches.json"


def _read_state():
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return {}
    switches = data.get("switches")
    return switches if isinstance(switches, dict) else {}


def _write_state(switches):
    path = _state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"format": "bp-ops-switches/1", "updated_at": _now_iso(),
                   "switches": switches}
        with open(path, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(payload, stream, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


def get(key):
    """Is a capability switched on?

    The order of truth: the saved state, then the env seed (so an operator
    can set the initial state without a state file), then the capability's
    own default — which is **off** for every loop.
    """
    if key not in CAPABILITIES:
        return None
    switches = _read_state()
    if key in switches:
        return bool(switches[key])
    seed = _env_seed(key)
    if seed is not None:
        return seed
    return bool(CAPABILITIES[key]["default"])


def _env_seed(key):
    """The env var that seeds a loop's switch, or None when there is none."""
    variable = LOOP_SEED_VARS.get(key)
    if not variable:
        return None
    raw = os.environ.get(variable)
    if raw is None:
        return None
    return raw != "0"


def all_switches():
    """Every capability with its current state."""
    switches = _read_state()
    out = []
    for key, entry in CAPABILITIES.items():
        on = get(key)
        row = {"key": key, "kind": entry["kind"], "label": entry["label"],
               "description": entry["description"], "enabled": bool(on),
               "default": bool(entry["default"])}
        if entry["kind"] == "loop":
            row["running"] = _loop_running(key)
        out.append(row)
    return out


def _loop_running(key):
    """Is the loop behind a switch actually running right now?"""
    try:
        if key == "loop.repair":
            from . import autoresearch as _autoresearch
            return bool(_autoresearch.status().get("running"))
        if key == "loop.growth":
            from . import growth_loop as _growth
            return bool(_growth.status().get("running"))
        if key == "loop.relevance":
            from .relevance import job as _job
            return bool(_job.status().get("running"))
    except Exception:
        return False
    return False


def set_switch(key, on, persist=True):
    """Turn a capability on or off.  Returns (ok, message).

    The change takes effect **immediately**: a loop that is turned on starts
    on its next pass, and a loop that is turned off stops.  A search provider
    that is turned off leaves the chain for the next search.
    """
    if key not in CAPABILITIES:
        return False, "unknown capability: %s" % key
    on = bool(on)
    entry = CAPABILITIES[key]

    if persist:
        switches = dict(_read_state())
        switches[key] = on
        _write_state(switches)

    if entry["kind"] == "loop":
        ok, message = _apply_loop(key, on)
        return ok, message
    _apply_search_order()
    return True, ("%s is %s" % (entry["label"], "on" if on else "off"))


def _apply_loop(key, on):
    """Start or stop the loop behind a switch.  Returns (ok, message)."""
    try:
        if key == "loop.repair":
            from . import autoresearch as _autoresearch
            if on:
                ok, message = _autoresearch.start()
            else:
                ok, message = _autoresearch.stop()
            return ok, message
        if key == "loop.growth":
            from . import growth_loop as _growth
            if on:
                ok, message = _growth.start()
            else:
                ok, message = _growth.stop()
            return ok, message
        if key == "loop.relevance":
            from .relevance import job as _job
            if on:
                ok, message = _job.start()
            else:
                ok, message = _job.stop()
            return ok, message
    except Exception as error:
        return False, str(error)[:200]
    return False, "no loop for %s" % key


def search_order():
    """The search providers that are switched on, in order.

    The **switches are the source of truth**.  `BP_RELEVANCE_SEARCH_ORDER` is
    only a seed for a system with no switch state yet, so the owner's env and
    the owner's switches cannot fight each other.
    """
    switches = _read_state()
    seeded = any(key.startswith("search.") for key in switches)
    if not seeded:
        raw = os.environ.get("BP_RELEVANCE_SEARCH_ORDER")
        if raw:
            order = []
            for name in str(raw).split(","):
                name = name.strip().lower()
                if name and name not in order:
                    order.append(name)
            if order:
                return order
    on = []
    for name in DEFAULT_SEARCH_ORDER:
        key = "search.%s" % name
        if key in switches:
            if not switches[key]:
                continue
        elif not CAPABILITIES[key]["default"]:
            continue
        on.append(name)
    # Anything the owner added that is not in the default order still counts.
    for key, value in switches.items():
        if not key.startswith("search.") or not value:
            continue
        name = key.split(".", 1)[1]
        if name not in on:
            on.append(name)
    return on


def _apply_search_order():
    """Publish the enabled search order.  The registry is the source of truth,
    so this only reports the order; the discovery reads it directly."""
    return ",".join(search_order())


def apply_all():
    """Apply every switch to the running system.

    Called at boot: a loop whose switch is on is started, and the search
    order is published.  A loop whose switch is off is left alone.
    """
    applied = []
    for key, entry in CAPABILITIES.items():
        if entry["kind"] != "loop":
            continue
        if not get(key):
            continue
        ok, message = _apply_loop(key, True)
        applied.append({"key": key, "ok": ok, "message": message})
    order = _apply_search_order()
    return {"loops": applied, "search_order": order}
