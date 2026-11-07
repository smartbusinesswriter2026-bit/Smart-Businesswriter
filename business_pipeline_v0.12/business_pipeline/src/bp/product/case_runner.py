"""Run stored tile cases and log a real failure as a replayable error.

A case is checked by code: the tile's paper is regenerated, the recorded
computation must equal the frozen method's output, and the paper must carry the
required phrases.  A failure writes one `tile-case` error carrying the case id,
so the Karpathy loop can re-check the case without a model call.

The runner stores its run manifest under `state/case_runs/<run_id>/` and saves
the failing paper beside it, so a failure can be opened and inspected.
"""

import json
import os
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone

from . import case_store
from . import ops_log
from . import paper_batch

FORMAT = "bp-case-run/1"


def _state_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "..", "..", "..", "state", "case_runs"))


def _now():
    return datetime.now(timezone.utc).isoformat()


def _docx_text(data):
    try:
        xml = zipfile.ZipFile(__import__("io").BytesIO(data)).read("word/document.xml").decode("utf-8")
    except Exception:
        return ""
    out = []
    for para in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        text = "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", para, re.S))
        if text.strip():
            out.append(text)
    return "\n".join(out)


def _open_case_error(case_id, error_text):
    rows = ops_log.merge_resolved(ops_log.list_errors(limit=500))
    for row in rows:
        if row.get("case_id") != case_id:
            continue
        if (row.get("error") or "").strip() != error_text.strip():
            continue
        if row.get("resolved") or row.get("attended") or row.get("invalid") or row.get("dismissed"):
            continue
        return True
    return False


def _same_number(actual, expected):
    """Numeric equality with a tolerance for Decimal trailing-digit noise."""
    left, right = str(actual), str(expected)
    if left == right:
        return True
    try:
        a, b = float(left), float(right)
    except (TypeError, ValueError):
        return False
    if a == b:
        return True
    return abs(a - b) <= max(1e-9, abs(b) * 1e-9)


def _xlsx_sheets(data):
    """The sheet names in a workbook, read from `xl/workbook.xml`."""
    try:
        xml = zipfile.ZipFile(__import__("io").BytesIO(data)).read("xl/workbook.xml").decode("utf-8")
    except Exception:
        return []
    return re.findall(r'<sheet[^>]+name="([^"]+)"', xml)


def _check(case, result):
    problems = []
    expected = case.get("expected") or {}
    status = result.get("status")
    if status != expected.get("status", "ok"):
        problems.append("status %s, expected %s%s" % (
            status, expected.get("status", "ok"),
            (": " + str(result.get("error") or "")[:200]) if result.get("error") else ""))
    computed = result.get("computation") or {}
    for name, value in (expected.get("result") or {}).items():
        if str(name).startswith("_"):
            continue
        actual = computed.get(name)
        if actual is None:
            problems.append("the method did not return %s" % name)
        elif not _same_number(actual, value):
            problems.append("%s is %s, expected %s" % (name, actual, value))
    text = _docx_text(result.get("bytes") or b"")
    for phrase in expected.get("contains") or []:
        if phrase and phrase not in text:
            problems.append("the paper does not contain %r" % phrase)
    wanted_sheets = expected.get("xlsx_sheets") or []
    if wanted_sheets:
        workbook = result.get("xlsx") or b""
        if not workbook:
            problems.append("the workbook was not produced")
        else:
            names = _xlsx_sheets(workbook)
            missing = [name for name in wanted_sheets if name not in names]
            if missing:
                problems.append("the workbook is missing the %s sheet(s)" % ", ".join(missing))
    return problems


def run_case(case_id, style="apa", length=1200, log=True):
    """Replay one stored case.  Returns {case_id, status, problems, error, bytes}."""
    case = case_store.get_case(case_id)
    if case is None:
        return {"case_id": case_id, "status": "missing", "problems": ["no such case"],
                "error": "no such case", "bytes": b""}
    started = time.perf_counter()
    try:
        result = paper_batch.generate_one(case["subject"], case["tile"],
                                          style=style, length=length, format="both",
                                          inputs=case.get("inputs"),
                                          instruction=case.get("instruction"))
    except Exception as error:
        result = {"status": "error", "error": str(error)[:500]}
    problems = _check(case, result)
    elapsed = int((time.perf_counter() - started) * 1000)
    if problems:
        error_text = "; ".join(problems)[:500]
        if log and not _open_case_error(case_id, error_text):
            ops_log.log_error("tile-case", error_text,
                              problem_text=case.get("instruction") or "",
                              gap_label=case.get("tile_label") or case.get("tile"),
                              case_id=case_id)
        return {"case_id": case_id, "status": "fail", "problems": problems,
                "error": error_text, "duration_ms": elapsed,
                "bytes": result.get("bytes") or b"", "xlsx": result.get("xlsx") or b"",
                "tile": case.get("tile"), "tile_label": case.get("tile_label")}
    return {"case_id": case_id, "status": "pass", "problems": [],
            "error": "", "duration_ms": elapsed,
            "bytes": result.get("bytes") or b"", "xlsx": result.get("xlsx") or b"",
            "tile": case.get("tile"), "tile_label": case.get("tile_label")}


def run_cases(case_ids, style="apa", length=1200, subject=None, generate_count=0):
    """Run the selected cases in one stored run; return the manifest.

    `generate_count` (0–10) also asks the model for that many problems on the
    subject shelf and solves them, so a run can mix stored cases and fresh
    system-generated problems.  It is the only part of a run that spends tokens,
    and it happens only when the caller asks for it.
    """
    run_id = uuid.uuid4().hex[:12]
    run_dir = os.path.join(_state_root(), run_id)
    os.makedirs(run_dir, exist_ok=True)
    manifest = {
        "format": FORMAT,
        "run_id": run_id,
        "created_at": _now(),
        "status": "running",
        "total": len(case_ids) + max(0, int(generate_count or 0)),
        "completed": 0,
        "passed": 0,
        "failed": 0,
        "results": [],
    }
    for case_id in case_ids:
        outcome = run_case(case_id, style=style, length=length)
        data = outcome.pop("bytes", b"")
        xlsx = outcome.pop("xlsx", b"")
        if data:
            name = re.sub(r"[^A-Za-z0-9._-]+", "-", case_id.replace("/", "_")) + ".docx"
            with open(os.path.join(run_dir, name), "wb") as handle:
                handle.write(data)
            outcome["paper"] = name
        if xlsx:
            name = re.sub(r"[^A-Za-z0-9._-]+", "-", case_id.replace("/", "_")) + ".xlsx"
            with open(os.path.join(run_dir, name), "wb") as handle:
                handle.write(xlsx)
            outcome["workbook"] = name
        manifest["results"].append(outcome)
        manifest["completed"] += 1
        if outcome["status"] == "pass":
            manifest["passed"] += 1
        else:
            manifest["failed"] += 1
        _write_manifest(run_dir, manifest)
    if int(generate_count or 0) > 0:
        from . import chat_heal
        count = min(10, max(1, int(generate_count)))
        instruction = ("Generate %d realistic test problems for the %s shelf. "
                       "Each problem must state its declared figures." % (count, subject or "selected"))
        problems, error = chat_heal.generate_problems(instruction, count, difficulty="medium")
        if error or not problems:
            manifest["results"].append({"case_id": "generated", "label": "Generated problems",
                                        "status": "error", "error": error or "no problems generated",
                                        "duration_ms": 0, "kind": "generated"})
            manifest["failed"] += 1
            manifest["completed"] += 1
        else:
            results, solve_error = chat_heal.solve_problems(problems)
            for index, row in enumerate(results):
                ok = str(row.get("status") or "") not in ("error", "logged")
                manifest["results"].append({
                    "case_id": "generated/%d" % (index + 1),
                    "label": "Generated problem %d" % (index + 1),
                    "status": "pass" if ok else "fail",
                    "error": "" if ok else str(row.get("error") or "")[:300],
                    "duration_ms": 0, "kind": "generated",
                })
                manifest["completed"] += 1
                if ok:
                    manifest["passed"] += 1
                else:
                    manifest["failed"] += 1
            if solve_error and not results:
                manifest["results"].append({"case_id": "generated", "label": "Generated problems",
                                            "status": "error", "error": solve_error[:300],
                                            "duration_ms": 0, "kind": "generated"})
                manifest["failed"] += 1
                manifest["completed"] += 1
        _write_manifest(run_dir, manifest)
    manifest["status"] = "done"
    manifest["finished_at"] = _now()
    _write_manifest(run_dir, manifest)
    return manifest


def _write_manifest(run_dir, manifest):
    path = os.path.join(run_dir, "manifest.json")
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)


def status(run_id):
    path = os.path.join(_state_root(), run_id, "manifest.json")
    if not os.path.exists(path):
        raise KeyError("no such case run")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def file_path(run_id, name):
    """The stored paper or workbook of one case run, if it exists."""
    safe = os.path.basename(str(name))
    if not safe or safe != str(name):
        raise KeyError("no such file")
    path = os.path.join(_state_root(), str(run_id), safe)
    if not os.path.isfile(path):
        raise KeyError("no such file")
    return path


def runs(limit=20):
    root = _state_root()
    if not os.path.isdir(root):
        return []
    out = []
    for name in os.listdir(root):
        path = os.path.join(root, name, "manifest.json")
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except Exception:
            continue
        manifest.pop("results", None)
        out.append(manifest)
    out.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return out[:limit]
