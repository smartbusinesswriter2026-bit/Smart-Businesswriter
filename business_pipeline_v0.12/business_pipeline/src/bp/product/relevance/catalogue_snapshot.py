"""Catalogue snapshot adapter for the RRA Mapper.

Exports the pipeline's own catalogue (capabilities, framework profiles, method
registry, paper families) into a versioned JSON file that the Mapper reads.
This is a read-only snapshot — it does not modify any source.  A drift test
compares the snapshot to the live code.
"""
import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from . import storage


def _repo_root():
    return Path(__file__).resolve().parents[4]


def build_catalogue_snapshot():
    """Build a catalogue snapshot dict from the live code.  Returns (snapshot, error)."""
    snapshot = {
        "format": "bp-catalogue-snapshot/1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capabilities": [],
        "frameworks": [],
        "methods": [],
        "paper_families": [],
    }

    # Capabilities
    try:
        from .. import capabilities as _caps
        entries = getattr(_caps, "ENTRIES", {}) or {}
        if isinstance(entries, dict):
            for key, val in entries.items():
                if isinstance(val, dict):
                    snapshot["capabilities"].append({
                        "key": val.get("key", key),
                        "label": val.get("label", key),
                        "method": val.get("method", ""),
                        "subject": val.get("subject", ""),
                        "intent": val.get("intent", ""),
                        "aliases": [],
                    })
    except Exception as e:
        return None, "capabilities: %s" % str(e)[:200]

    # Framework profiles
    try:
        from .. import framework_profiles as _fp
        profiles = getattr(_fp, "PROFILES", {}) or {}
        if isinstance(profiles, dict):
            for key, val in profiles.items():
                if isinstance(val, dict):
                    snapshot["frameworks"].append({
                        "key": val.get("key", key),
                        "label": val.get("label", key),
                        "unit": val.get("unit", ""),
                        "aliases": [],
                    })
    except Exception as e:
        return None, "framework_profiles: %s" % str(e)[:200]

    # Methods (from bp.methods)
    try:
        import bp.methods as _methods
        method_list = _methods.list_methods() if hasattr(_methods, "list_methods") else []
        for m in (method_list or []):
            if isinstance(m, dict):
                snapshot["methods"].append({
                    "method_id": m.get("method_id", ""),
                    "category": m.get("category", ""),
                    "tier": m.get("tier", ""),
                    "status": m.get("status", ""),
                    "intended_use": m.get("intended_use", ""),
                })
    except Exception as e:
        return None, "methods: %s" % str(e)[:200]

    # Paper families
    try:
        from .. import paper_families as _pf
        families = getattr(_pf, "FAMILIES", None) or getattr(_pf, "PAPER_FAMILIES", None)
        if isinstance(families, dict):
            for key, val in families.items():
                snapshot["paper_families"].append({"key": key, "label": str(val)[:80]})
        elif isinstance(families, (list, tuple)):
            for f in families:
                snapshot["paper_families"].append({"key": str(f), "label": str(f)})
    except Exception:
        # paper_families module may not expose families directly — skip gracefully
        pass

    # Compute a hash of the snapshot content (excluding generated_at)
    content = {k: v for k, v in snapshot.items() if k != "generated_at"}
    snapshot["hash"] = hashlib.sha256(
        json.dumps(content, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()

    return snapshot, ""


def write_catalogue_snapshot():
    """Write the catalogue snapshot to qa/relevance/catalogue_snapshot.json."""
    snapshot, err = build_catalogue_snapshot()
    if err:
        return None, err
    path = _repo_root() / "qa" / "relevance" / "catalogue_snapshot.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False, default=str)
        return path, ""
    except OSError as e:
        return None, "write error: %s" % str(e)


def load_catalogue_snapshot():
    """Load the catalogue snapshot if it exists."""
    path = _repo_root() / "qa" / "relevance" / "catalogue_snapshot.json"
    if not path.is_file():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def check_drift():
    """Compare the stored snapshot to a fresh build.  Returns (drifted: bool, details)."""
    stored = load_catalogue_snapshot()
    if stored is None:
        return True, "no stored snapshot found"
    fresh, err = build_catalogue_snapshot()
    if err:
        return True, "build error: %s" % err
    if stored.get("hash") != fresh.get("hash"):
        return True, "snapshot hash mismatch (catalogue changed since snapshot was written)"
    return False, "in sync"
