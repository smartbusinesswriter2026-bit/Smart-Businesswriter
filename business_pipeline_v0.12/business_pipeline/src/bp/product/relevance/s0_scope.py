"""RRA Stage S0 — Scope.

Reads the owner-edited school list and topic list, produces a run plan with
a page and token budget.  Deterministic gate: budget and list must be present.
"""
import json
import os
from pathlib import Path

from . import storage
from .schemas import make_run_id, RunRecord


def _repo_root():
    return Path(__file__).resolve().parents[4]


def load_school_list():
    """Load the owner-edited school list from qa/relevance/schools.json."""
    path = _repo_root() / "qa" / "relevance" / "schools.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_allowlist():
    """Load the source allowlist from qa/relevance/allowlist.json."""
    path = _repo_root() / "qa" / "relevance" / "allowlist.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_taxonomy():
    """Load the taxonomy from qa/relevance/taxonomy.json."""
    path = _repo_root() / "qa" / "relevance" / "taxonomy.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def load_backtest():
    """Load the back-test set from qa/relevance/backtest.json."""
    path = _repo_root() / "qa" / "relevance" / "backtest.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def build_run_plan(school_list=None, topic_list=None, page_budget=None, token_budget=None):
    """Build a run plan.  Returns (plan_dict, error_string).

    Deterministic gate: school list and page/token budget must be present.
    """
    if school_list is None:
        school_list = load_school_list()
    if school_list is None:
        return None, "school list is required (qa/relevance/schools.json)"

    if page_budget is None:
        page_budget = int(os.environ.get("BP_RELEVANCE_MAX_PAGES", "50"))
    if token_budget is None:
        token_budget = int(os.environ.get("BP_RELEVANCE_BUDGET_TOKENS", "100000"))

    if page_budget <= 0:
        return None, "page_budget must be > 0"
    if token_budget <= 0:
        return None, "token_budget must be > 0"

    if topic_list is None:
        taxonomy = load_taxonomy()
        if taxonomy and isinstance(taxonomy.get("topics"), list):
            topic_list = [t.get("id") for t in taxonomy["topics"] if t.get("id")]
        else:
            topic_list = []

    schools = []
    regions = school_list.get("regions", {}) if isinstance(school_list, dict) else {}
    for region, items in regions.items():
        for item in (items or []):
            schools.append({"name": item.get("name", ""), "region": region,
                            "level": item.get("level", ""), "notes": item.get("notes", "")})

    bodies = school_list.get("bodies_to_watch", []) if isinstance(school_list, dict) else []

    plan = {
        "run_id": make_run_id(),
        "school_count": len(schools),
        "schools": schools,
        "bodies": bodies,
        "topic_count": len(topic_list),
        "topics": topic_list,
        "page_budget": page_budget,
        "token_budget": token_budget,
        "pages_used": 0,
        "tokens_used": 0,
    }
    return plan, ""


def create_run_record(plan):
    """Create a RunRecord from a plan."""
    return RunRecord(
        run_id=plan["run_id"],
        started_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        status="running",
        school_count=plan["school_count"],
        evidence_count=0,
        gap_count=0,
        watchitem_count=0,
        cost_tokens=0,
    )
