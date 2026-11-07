# Append to ops_log.py: proposals store

def _proposals_path():
    return _log_dir() / "proposals.jsonl"


def log_proposal(finding_key, kind, payload, status="pending"):
    """Append one proposal. Returns proposal_id."""
    import uuid
    pid = uuid.uuid4().hex[:12]
    record = {
        "ts": _now_iso(),
        "proposal_id": pid,
        "finding_key": str(finding_key or ""),
        "kind": str(kind or "code"),
        "status": str(status or "pending"),
        "payload": payload if isinstance(payload, dict) else {"text": str(payload)},
    }
    ok = _append_jsonl(_proposals_path(), record)
    return pid if ok else None


def list_proposals(finding_key=None, status=None, limit=100):
    all_records = _read_jsonl(_proposals_path(), limit=100000)
    latest = {}
    for r in all_records:
        pid = r.get("proposal_id")
        if not pid:
            continue
        latest[pid] = r
    out = []
    for p in latest.values():
        if finding_key and p.get("finding_key") != finding_key:
            continue
        if status and p.get("status") != status:
            continue
        out.append(p)
    out.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return out[:limit]


def update_proposal_status(proposal_id, status):
    """Append a status update for a proposal."""
    all_records = _read_jsonl(_proposals_path(), limit=100000)
    known = {r.get("proposal_id") for r in all_records if r.get("proposal_id")}
    if proposal_id not in known:
        return False
    _append_jsonl(_proposals_path(), {"ts": _now_iso(), "proposal_id": proposal_id,
                                     "status": str(status)})
    # update in-memory latest record's status by re-reading
    return True
PY