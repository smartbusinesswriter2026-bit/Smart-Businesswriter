"""Stored tile cases: one folder per subject tile, one JSON file per case.

A case is the tile's prefilled instruction, its declared figures, and the result
the frozen method returns for them.  It is a **test**, not a narrative: the case
runner replays it through the same paper path and checks the recorded result and
the paper's required phrases.  A case that fails writes a `tile-case` error that
carries its `case_id`, so the Karpathy loop can re-check it by code with no model
call.

Cases live in `qa/cases/<subject>/<tile-slug>/case_NNN.json` so they can be read,
diffed and committed like any other fixture.  Seeding is additive: an existing
case is never overwritten unless the caller asks for it.
"""

import csv
import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone

from .. import methods
from . import capabilities
from . import documents
from . import paper_batch

FORMAT = "bp-tile-case/1"


def _root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "..", "qa", "cases"))


def _slug(text):
    text = re.sub(r"[^a-z0-9]+", "-", str(text or "").lower()).strip("-")
    return text or "tile"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _case_path(subject, tile_key, number=1):
    return os.path.join(_root(), _slug(subject), _slug(tile_key), "case_%03d.json" % number)


def _write(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)


def _recorded(output, output_key=None):
    if isinstance(output, dict):
        return {str(name): str(value) for name, value in output.items()
                if not str(name).startswith("_")}
    return {str(output_key or "value"): str(output)}


def seed(subject=None, tile=None, overwrite=False, limit=None):
    """Create a case for every tile with published defaults (or the named one)."""
    written, skipped, errors = 0, 0, []
    data = paper_batch.sections()
    for section in data.get("subjects") or []:
        if subject and section.get("id") != subject:
            continue
        for group in section.get("groups") or []:
            for row in group.get("tiles") or []:
                if not row.get("has_defaults"):
                    continue
                if row.get("service") == "statements" or not row.get("method"):
                    continue
                if tile and row.get("key") != tile:
                    continue
                path = _case_path(section["id"], row["key"])
                if os.path.exists(path) and not overwrite:
                    skipped += 1
                    continue
                try:
                    info = paper_batch.brief_for(section["id"], row["key"])
                    output = paper_batch._run_method(info["tile"], info["inputs"])
                    entry = next((candidate for candidate in capabilities.ENTRIES.values()
                                  if candidate.get("method") == row.get("method")), {})
                    expected = _recorded(output, entry.get("output"))
                except Exception as error:
                    errors.append({"subject": section["id"], "tile": row.get("key"),
                                   "error": str(error)[:300]})
                    continue
                payload = {
                    "format": FORMAT,
                    "id": "%s/%s/%03d" % (_slug(section["id"]), _slug(row["key"]), 1),
                    "subject": section["id"],
                    "subject_label": section.get("label") or section["id"],
                    "tile": row["key"],
                    "method": row.get("method") or "",
                    "tile_label": row.get("label") or row["key"],
                    "group": group.get("label") or "",
                    "objective": info["objective"],
                    "instruction": info["brief"],
                    "inputs": info["inputs"],
                    "expected": {
                        "status": "ok",
                        "result": expected,
                        "contains": [row.get("label") or row["key"], "What you declared", "How the figures were checked"],
                        "contract": {"sections": ["Result", "Inputs and results",
                                                  "How the figures were checked"]},
                        "xlsx_sheets": ["Summary", "Inputs", "Results", "Record"],
                    },
                    "created_at": _now(),
                    "origin": "preset",
                }
                _write(path, payload)
                written += 1
                if limit and written >= int(limit):
                    return {"written": written, "skipped": skipped, "errors": errors}
    return {"written": written, "skipped": skipped, "errors": errors}


def load_cases(subject=None, tile=None):
    """Every stored case, oldest path first; optionally filtered."""
    root = _root()
    if not os.path.isdir(root):
        return []
    out = []
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            if not name.endswith(".json"):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    case = json.load(handle)
            except Exception:
                continue
            if not isinstance(case, dict) or case.get("format") != FORMAT:
                continue
            if subject and case.get("subject") != subject:
                continue
            if tile and case.get("tile") != tile:
                continue
            case["_path"] = path
            out.append(case)
    return out


def get_case(case_id):
    for case in load_cases():
        if case.get("id") == case_id:
            return case
    return None


def summary():
    """Counts by subject, for the admin page."""
    cases = load_cases()
    by_subject = {}
    for case in cases:
        key = case.get("subject") or "unknown"
        by_subject.setdefault(key, {"subject": key, "label": case.get("subject_label") or key,
                                    "cases": 0, "tiles": set()})
        by_subject[key]["cases"] += 1
        by_subject[key]["tiles"].add(case.get("tile"))
    rows = []
    for row in by_subject.values():
        row["tiles"] = len(row["tiles"])
        rows.append(row)
    rows.sort(key=lambda row: row["subject"])
    return {"format": FORMAT, "total": len(cases), "by_subject": rows,
            "root": _root()}
