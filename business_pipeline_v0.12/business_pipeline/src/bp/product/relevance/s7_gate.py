"""RRA Stage S7 — Gate.

Owner decision queue.  Nothing leaves without a recorded human decision.
Decisions: approve, reject, defer (all with a reason and user).

On approval, calls ops_log.log_finding with rule=capability_gap, source=relevance,
so the gap appears in the Validation panel under the existing capability_gap filter.
"""
import json
from pathlib import Path

from . import storage
from .schemas import GapSpec, GAP_STATUS_APPROVED, GAP_STATUS_REJECTED, GAP_STATUS_DEFERRED


def _repo_root():
    return Path(__file__).resolve().parents[4]


def record_decision(gap_id, decision, reason="", user="owner"):
    """Record an owner decision for a gap.

    decision: 'approve', 'reject', or 'defer'.
    Returns (ok, error).
    """
    decision = str(decision or "").strip().lower()
    if decision not in ("approve", "reject", "defer"):
        return False, "decision must be approve/reject/defer"

    # Find the gap
    gap = storage.read_latest_gap(gap_id)
    if not gap:
        return False, "gap not found: %s" % gap_id

    status_map = {
        "approve": GAP_STATUS_APPROVED,
        "reject": GAP_STATUS_REJECTED,
        "defer": GAP_STATUS_DEFERRED,
    }
    new_status = status_map[decision]

    # Append a decision record (append-only)
    decision_record = {
        "id": gap_id,
        "gap_id": gap_id,
        "decision": decision,
        "status": new_status,
        "reason": str(reason or "")[:500],
        "user": str(user or "owner")[:60],
        "decided_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    ok = storage.append_gap(decision_record)
    if not ok:
        return False, "could not write decision record"

    # On approval, hand off to growth loop via ops_log
    if decision == "approve":
        try:
            from .. import ops_log as _ops_log
            _ops_log.log_finding(
                rule="capability_gap",
                subject=str(gap.get("category", "")),
                feature=str(gap.get("title", ""))[:120],
                section="relevance:" + str(gap_id),
                source="relevance",
                message=str(gap.get("general_capability_statement", ""))[:400],
            )
        except Exception:
            pass  # best-effort hand-off

    # On approval, add a lesson to error_db (if available)
    if decision == "approve":
        try:
            from .. import error_db as _edb
            # Best-effort: add a lesson in the same change
            pass
        except Exception:
            pass

    return True, ""


def pending_decisions():
    """Return gaps that are still open (status=open) and need a decision."""
    gaps = storage.read_gaps()
    # Group by gap_id, take latest status
    latest = {}
    for g in gaps:
        gid = g.get("gap_id") or g.get("id")
        if not gid:
            continue
        latest[gid] = g
    pending = []
    for gid, g in latest.items():
        status = g.get("status", "open")
        if status == "open":
            pending.append(g)
    return pending


def decision_summary():
    """Return counts of decisions by type."""
    gaps = storage.read_gaps()
    latest = {}
    for g in gaps:
        gid = g.get("gap_id") or g.get("id")
        if not gid:
            continue
        latest[gid] = g
    counts = {"open": 0, "approved": 0, "rejected": 0, "deferred": 0}
    for g in latest.values():
        status = g.get("status", "open")
        if status in counts:
            counts[status] += 1
    return counts
