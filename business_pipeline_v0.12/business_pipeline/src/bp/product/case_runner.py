"""Run stored tile cases and log a real failure as a replayable error.

A case is checked by code: the tile's paper is regenerated, the recorded
computation must equal the frozen method's output, and the paper must carry the
required phrases.  A failure writes one `tile-case` error carrying the case id,
so the Karpathy loop can re-check the case without a model call.

The runner stores its run manifest under `state/case_runs/<run_id>/` and saves
the failing paper beside it, so a failure can be opened and inspected.
"""

import json
import math
import os
import random
import re
import time
import uuid
import zipfile
from datetime import datetime, timezone

from . import case_store
from . import case_invariants
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


def _xlsx_text(data):
    """Every cell text and shared string in a workbook, tags stripped."""
    try:
        archive = zipfile.ZipFile(__import__("io").BytesIO(data))
        parts = [archive.read(name).decode("utf-8", errors="replace")
                 for name in archive.namelist()
                 if name.startswith("xl/worksheets/") or name == "xl/sharedStrings.xml"]
    except Exception:
        return ""
    return " ".join(re.sub(r"<[^>]+>", " ", part) for part in parts)


def _is_number(value):
    try:
        float(str(value).replace(",", ""))
        return True
    except (TypeError, ValueError):
        return False


def _value_forms(value):
    """The ways a recorded value may appear in the paper text."""
    text = str(value).strip()
    forms = {text}
    if not text:
        return forms
    try:
        number = float(text.replace(",", ""))
    except (TypeError, ValueError):
        return forms
    forms.add(text.replace(",", ""))
    forms.add(("%f" % number).rstrip("0").rstrip("."))
    forms.add("%.1f" % number)
    forms.add("%.2f" % number)
    forms.add("%.3f" % number)
    forms.add("{:,.2f}".format(number))
    if number == int(number):
        forms.add("{:,}".format(int(number)))
    if 0 <= abs(number) <= 1:
        percent = number * 100
        forms.add("%.1f%%" % percent)
        forms.add("%.2f%%" % percent)
        forms.add("%d%%" % round(percent))
    return {form for form in forms if form and form not in ("-", "0", "0.0", "0.00")}


def _paper_has_value(text, value):
    """True when the text shows the value, at any reasonable precision."""
    try:
        target = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return any(form in text for form in _value_forms(value))
    candidates = [target]
    if 0 <= abs(target) <= 1:
        candidates.append(target * 100)
    for match in re.findall(r"-?\d[\d,]*\.?\d*", text):
        try:
            number = float(match.replace(",", ""))
        except (TypeError, ValueError):
            continue
        if any(math.isclose(number, candidate, rel_tol=1e-4, abs_tol=0.005)
               for candidate in candidates):
            return True
    return False


def _close_case_errors(case_id):
    """Close open tile-case errors for a case that now passes."""
    closed = 0
    for row in ops_log.merge_resolved(ops_log.list_errors(limit=1000, status="open")):
        if row.get("case_id") != case_id:
            continue
        if ops_log.mark_error_verified(
                row.get("error_id"), "the case passed in a later run"):
            closed += 1
    return closed


def _check(case, result):
    problems = []
    expected = case.get("expected") or {}
    status = result.get("status")
    if status != expected.get("status", "ok"):
        problems.append("status %s, expected %s%s" % (
            status, expected.get("status", "ok"),
            (": " + str(result.get("error") or "")[:200]) if result.get("error") else ""))
    expected_result = {str(name): value for name, value in (expected.get("result") or {}).items()
                       if not str(name).startswith("_")}
    if expected.get("status", "ok") == "ok" and not expected_result:
        problems.append("the case declares no expected result, so it cannot test the computation")
    computed = result.get("computation") or {}
    for name, value in expected_result.items():
        actual = computed.get(name)
        if actual is None:
            problems.append("the method did not return %s" % name)
        elif not _same_number(actual, value):
            problems.append("%s is %s, expected %s" % (name, actual, value))
    if expected_result:
        extra = sorted(str(name) for name in computed
                       if not str(name).startswith("_") and name not in expected_result)
        if extra:
            problems.append("the method returned key(s) the case does not expect: "
                            + ", ".join(extra[:6]))
    method_id = case.get("method") or ""
    if not method_id:
        try:
            _subject, _group, tile = paper_batch._find_tile(case["subject"], case["tile"])
            method_id = tile.get("method") or ""
        except Exception:
            method_id = ""
    problems.extend(case_invariants.check(method_id, case.get("inputs") or {}, computed))
    text = _docx_text(result.get("bytes") or b"")
    for phrase in expected.get("contains") or []:
        if phrase and phrase not in text:
            problems.append("the paper does not contain %r" % phrase)
    paper_values = expected.get("paper_values")
    if paper_values is None:
        numeric = []
        for value in expected_result.values():
            if not _is_number(value):
                continue
            try:
                if abs(float(str(value).replace(",", ""))) <= 1e-12:
                    continue
            except (TypeError, ValueError):
                pass
            numeric.append(value)
        paper_values = numeric[:3]
    if paper_values and not any(_paper_has_value(text, value) for value in paper_values):
        problems.append("the paper does not show any of the computed values: "
                        + ", ".join(str(value)[:24] for value in paper_values))
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
            if paper_values:
                workbook_text = _xlsx_text(workbook)
                if workbook_text and not any(_paper_has_value(workbook_text, value)
                                             for value in paper_values):
                    problems.append("the workbook does not show any of the computed values")
    return problems


def _explainer_text(case, result, problems, outcome):
    """A readable account of what the case asked, what it computed and how it was checked."""
    tile = case.get("tile_label") or case.get("tile") or "Tile"
    inputs = case.get("inputs") or {}
    computed = result.get("computation") or {}
    lines = [
        "# %s" % tile,
        "",
        "Subject: %s" % (case.get("subject_label") or case.get("subject") or ""),
        "Tile: %s" % (case.get("tile") or ""),
        "Objective: %s" % (case.get("objective") or ""),
        "",
        "## Instruction",
        "",
        str(case.get("instruction") or "").strip(),
        "",
        "## Declared inputs",
        "",
    ]
    for name, value in inputs.items():
        lines.append("- %s: %s" % (str(name).replace("_", " "), value))
    lines.extend(["", "## Computed result", ""])
    for name, value in computed.items():
        lines.append("- %s: %s" % (str(name).replace("_", " "), value))
    lines.extend(["", "## Check", "", "Status: %s" % outcome.get("status", "unknown")])
    if problems:
        lines.extend(["", "Problems:"])
        for problem in problems:
            lines.append("- %s" % problem)
    else:
        lines.append("No problem was found: the computation, the invariants, the paper and the workbook all agree.")
    lines.extend([
        "",
        "## Evidence",
        "",
        "Sources cited: %s" % (result.get("sources") or 0),
        "Background pages: %s" % (result.get("background") or 0),
        "Named gaps: %s" % (result.get("gaps") or 0),
        "",
    ])
    return "\n".join(lines)


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
                "explainer": _explainer_text(case, result, problems, {"status": "fail"}),
                "tile": case.get("tile"), "tile_label": case.get("tile_label")}
    closed = _close_case_errors(case_id)
    return {"case_id": case_id, "status": "pass", "problems": [],
            "error": "", "duration_ms": elapsed, "closed_errors": closed,
            "bytes": result.get("bytes") or b"", "xlsx": result.get("xlsx") or b"",
            "explainer": _explainer_text(case, result, problems, {"status": "pass"}),
            "tile": case.get("tile"), "tile_label": case.get("tile_label")}


def run_random(subject=None, tile=None, style="apa", length=1200):
    """Pick one stored case at random and replay it.

    A pile of cases is only useful if the loop can draw from it without the caller
    naming every id.  This is the one-at-a-time draw the owner asked for; it returns
    the same shape as ``run_case`` so the page and the loop treat it identically.
    """
    cases = case_store.load_cases(subject=subject, tile=tile)
    if not cases:
        return {"case_id": None, "status": "missing", "problems": ["no stored cases"],
                "error": "no stored cases", "bytes": b"", "xlsx": b""}
    case = random.choice(cases)
    return run_case(case.get("id"), style=style, length=length)


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
    explainers = []
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
        explainer = outcome.pop("explainer", "")
        if explainer:
            name = re.sub(r"[^A-Za-z0-9._-]+", "-", case_id.replace("/", "_")) + "_explainer.md"
            with open(os.path.join(run_dir, name), "w", encoding="utf-8", newline="\n") as handle:
                handle.write(explainer + "\n")
            outcome["explainer_file"] = name
            explainers.append((case_id, explainer))
        manifest["results"].append(outcome)
        manifest["completed"] += 1
        if outcome["status"] == "pass":
            manifest["passed"] += 1
        else:
            manifest["failed"] += 1
        _write_manifest(run_dir, manifest)
    if int(generate_count or 0) > 0:
        import os as _os
        if _os.environ.get("BP_ENABLE_DEEPSEEK") != "1":
            manifest["results"].append({"case_id": "generated", "label": "Generated problems",
                                       "status": "error", "error": "problem generation disabled "
                                       "(BP_ENABLE_DEEPSEEK != 1)", "duration_ms": 0, "kind": "generated"})
            manifest["failed"] += 1
            manifest["completed"] += 1
            _write_manifest(run_dir, manifest)
        else:
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
    if explainers:
        path = os.path.join(run_dir, "explainer.md")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("# Case run %s\n\n" % run_id)
            handle.write("Every case below was replayed through the paper path. "
                         "A pass means the computation, the invariants, the paper and the workbook agree.\n")
            for case_id, text in explainers:
                handle.write("\n\n---\n\n" + text)
        manifest["explainer"] = "explainer.md"
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
