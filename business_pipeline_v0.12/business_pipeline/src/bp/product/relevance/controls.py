"""RRA control set — the measurement's own check on itself.

The controls are the frameworks and capabilities the system **already has**.
Every coverage measurement carries them.  If too few controls were found,
the measurement failed — the method cannot see — and no gap is promoted from
it.  A control that scores zero is evidence about the method, not about the
catalogue.

Phase 1 found this the hard way: reading the sampling frame's core-course
lists produced zero hits for every framework, including the seven the system
already has.  The control failed and the measurement was discarded rather
than reported.
"""
import json
from pathlib import Path

#: The share of controls that must be held for a measurement to count.
DEFAULT_MIN_HELD = 0.75


def _repo_root():
    return Path(__file__).resolve().parents[4]


def registry_path():
    return _repo_root() / "qa" / "relevance" / "controls.json"


def load_controls():
    """Load the control registry.  Returns (controls, rules) or ([], {})."""
    path = registry_path()
    if not path.is_file():
        return [], {}
    try:
        with open(path, encoding="utf-8") as stream:
            data = json.load(stream)
    except (OSError, json.JSONDecodeError):
        return [], {}
    controls = data.get("controls", []) or []
    rules = data.get("rules", {}) or {}
    return controls, rules


def check(coverage_rows, controls=None, rules=None, evidence_records=None):
    """Check the controls against a set of coverage rows.

    `coverage_rows` is a list of dicts with `taxonomy_item` and `status`.
    `evidence_records` is the evidence the sweep gathered (list of dicts with
    `excerpt`).

    A control is held when the sweep **could see it**:

    - a **framework** control needs the framework's name in an evidence
      excerpt.  The catalogue already knows the framework exists, so checking
      the catalogue would pass whether or not the method could see it — and
      the method's failure in Phase 1 was exactly that: it read the core-course
      lists and found no framework name at all, including the controls.
    - a **capability** or **retrieval** control needs the artefact in the
      catalogue; these are not evidenced from the outside.

    Returns a dict: {held, total, ratio, passed, missing, min_held}.
    """
    if controls is None:
        controls, rules = load_controls()
    if rules is None:
        rules = {}
    min_held = float(rules.get("min_controls_held", DEFAULT_MIN_HELD))

    # The evidence the sweep saw.
    excerpts = []
    mentions = []
    for record in (evidence_records or []):
        if hasattr(record, "to_dict"):
            record = record.to_dict()
        excerpt = str(record.get("excerpt", "") or "")
        if excerpt:
            excerpts.append(excerpt.lower())
        for name in (record.get("mentions") or []):
            mentions.append(str(name).strip().lower())
    evidence_text = "\n".join(excerpts + mentions)

    # The match is on the taxonomy id (exact), with the label as a fallback —
    # the taxonomy's `taxonomy_item` and the control's `label` are written
    # differently ("PESTEL analysis" against "PESTEL"), so the id is the
    # reliable key.
    by_id = {}
    by_item = {}
    for row in (coverage_rows or []):
        if hasattr(row, "to_dict"):
            row = row.to_dict()
        tid = str(row.get("taxonomy_id", "")).strip().lower()
        if tid:
            by_id[tid] = row
        label = str(row.get("taxonomy_item", "")).strip().lower()
        if label:
            by_item[label] = row

    held = []
    missing = []
    for control in (controls or []):
        tid = str(control.get("taxonomy_id", "")).strip().lower()
        label = str(control.get("label", "")).strip().lower()
        kind = str(control.get("kind", "framework")).lower()
        row = by_id.get(tid) or by_item.get(label)

        if row is None:
            missing.append({"id": control.get("id", ""), "label": control.get("label", ""),
                            "reason": "not measured"})
            continue

        status = str(row.get("status", ""))
        if status == "missing":
            missing.append({"id": control.get("id", ""), "label": control.get("label", ""),
                            "reason": "reported missing"})
            continue

        if kind == "framework":
            # The name must appear in something the sweep actually read.  With
            # no evidence at all the sweep saw nothing, so the control did
            # not hold.
            name = label.split("(")[0].strip()
            if not name or name.lower() not in evidence_text:
                missing.append({"id": control.get("id", ""),
                                "label": control.get("label", ""),
                                "reason": ("no evidence was read" if not evidence_text
                                           else "not found in any evidence excerpt")})
                continue

        held.append({"id": control.get("id", ""), "label": control.get("label", ""),
                     "status": status, "kind": kind})

    total = len(controls or [])
    ratio = (len(held) / total) if total else 1.0
    return {
        "held": len(held),
        "total": total,
        "ratio": round(ratio, 4),
        "min_held": min_held,
        "passed": ratio >= min_held,
        "held_items": held,
        "missing_items": missing,
        "verdict": "the measurement held" if ratio >= min_held
                   else "the measurement FAILED — no gap is promoted from it",
    }
