"""Eval runner: measure the pipeline against its own cases, its tiles and its
repair loop.

Three directions, one manifest:

* **Direction 1** - deterministic golden replay over the stored tile cases.
  Zero model calls.  It answers: does the frozen method still return the
  recorded result, do the invariants hold, and does the paper carry the
  sections and the computed values the case names?
* **Direction 2** - live end-to-end over the tiles with a code-only rubric.
  It answers: does the delivered paper hold up when it is built through the
  real paper path and scored by code?  The figures come from the first source
  that has them - what the caller declared, the tile's published defaults, or
  the tile's first stored case - and the manifest records which one was used.
* **Direction 3** - the self-heal loop: which causes were closed, what the
  repair cost, and whether the fix held.

Nothing here decides anything.  This module measures, counts and records.  A
gap the measurement finds is a **finding**, and a finding becomes a capability
only when a human approves it and the growth loop scaffolds it.

**The count is split by scope**, because one number cannot carry the three
meanings the repair loop already distinguishes (``docs/CAUSE_LOOP.md``):

===============  =========================================================
``pass``         the case replayed and every check agreed.
``fail``         a **pipeline** defect: the computation, the invariants, the
                 paper or the workbook disagreed with the case.
``invalid``      the case's **own figures** are inconsistent.  That is an
                 invalid fixture, not a defect the pipeline can fix, and it
                 is never counted against the pipeline.
``error``        the case could not be replayed at all.
``skipped``      (Direction 2) a tile with no declared figures to build it
                 from.  There is no computation to disagree with.
===============  =========================================================

The budget in the spec counts ``fail`` only.  A case that turns from ``pass``
to ``fail`` is a **regression** and is a blocker whatever the budget says.

The state lives under ``state/eval_runs/<run_id>/``.  ``BP_STATE_DIR`` moves
it, so a test never writes into the real state.
"""

import json
import os
import re
import time
import urllib.request
import uuid
from datetime import datetime, timezone

from . import case_runner
from . import case_store
from . import ops_log
from .. import build as build_info

FORMAT = "bp-eval-run/1"

#: The three directions.  A name outside this list is refused, with a reason:
#: the runner fails closed rather than guessing what was meant.
DIRECTIONS = ("direction1", "direction2", "direction3")

#: The four scopes a case outcome can land in.  The order is the order the
#: report prints them in.
SCOPES = ("pass", "fail", "invalid", "error")

#: The pipeline-failure budget from the spec.  It counts ``fail`` only.
FAIL_BUDGET = 2


def _now():
    return datetime.now(timezone.utc).isoformat()


def _state_root():
    from . import ops as ops_mod
    return ops_mod.state_dir() / "eval_runs"


#: The corpus state, probed once per process.  The index does not come and go
#: inside a run, and a manifest is written after every case, so probing per
#: manifest turned a two-second run into a two-minute one.
_CORPUS_STATE = None


def corpus_available(timeout=1.5, refresh=False):
    """Is the proprietary corpus index reachable?

    The corpus adapter **fails open**: when Meilisearch is down it returns an
    empty list and no error, so a run that finds no evidence looks exactly
    like a run that found no match.  The eval asks the index itself, so a
    missing corpus is reported as missing and the RAG score is ``not
    measured`` instead of a green.

    The answer is cached for the process; pass ``refresh=True`` to ask again.
    """
    global _CORPUS_STATE
    if _CORPUS_STATE is not None and not refresh:
        return _CORPUS_STATE
    try:
        from . import sources
        url = str(sources.CORPUS_MEILI_URL).rstrip("/") + "/health"
    except Exception:
        url = str(os.environ.get("CORPUS_MEILI_URL", "http://127.0.0.1:7700")).rstrip("/") + "/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            _CORPUS_STATE = 200 <= int(response.getcode()) < 300
    except Exception:
        _CORPUS_STATE = False
    return _CORPUS_STATE


def environment():
    """What the run was measured against: the build, and the corpus state."""
    return {
        "build": str(getattr(build_info, "VERSION", "") or ""),
        "corpus_available": corpus_available(),
    }


def new_manifest(direction, run_id=None, env=None):
    """A fresh manifest for one run."""
    if direction not in DIRECTIONS:
        raise ValueError("unknown eval direction: %r (known: %s)"
                         % (direction, ", ".join(DIRECTIONS)))
    now = _now()
    return {
        "format": FORMAT,
        "run_id": run_id or uuid.uuid4().hex[:12],
        "direction": direction,
        "created_at": now,
        "started_at": now,
        "finished_at": "",
        "status": "running",
        "counts": {scope: 0 for scope in SCOPES} | {"total": 0},
        "cases": [],
        "cost": {"model_calls": 0, "tokens_in": 0, "tokens_out": 0,
                 "usd": None, "seconds": 0},
        "environment": dict(env or environment()),
        "notes": "",
    }


def _safe_run_id(run_id):
    """A run id that cannot walk out of the state directory.

    The run id names a folder under `state/eval_runs/`.  It is generated here,
    but a caller may pass one, so the name is checked: no separator, no
    parent reference, nothing that could leave the directory.
    """
    value = str(run_id or "").strip()
    if not value or len(value) > 64:
        raise ValueError("a run id must be between 1 and 64 characters")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise ValueError("a run id may hold only letters, digits, '-' and '_'")
    return value


def save_manifest(run_id, manifest):
    """Write the manifest atomically.  Returns its path."""
    run_dir = os.path.join(str(_state_root()), _safe_run_id(run_id))
    os.makedirs(run_dir, exist_ok=True)
    path = os.path.join(run_dir, "manifest.json")
    temp = path + ".tmp"
    with open(temp, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=1)
    os.replace(temp, path)
    return path


def load_manifest(run_id):
    """The stored manifest of one run.  Raises KeyError when there is none."""
    path = os.path.join(str(_state_root()), _safe_run_id(run_id), "manifest.json")
    if not os.path.isfile(path):
        raise KeyError("no such eval run")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def runs(limit=20, direction=None):
    """Stored runs, newest first, without their case rows."""
    root = _state_root()
    if not os.path.isdir(root):
        return []
    out = []
    for name in os.listdir(root):
        path = os.path.join(root, name, "manifest.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                manifest = json.load(handle)
        except Exception:
            continue
        if manifest.get("format") != FORMAT:
            continue
        if direction and manifest.get("direction") != direction:
            continue
        manifest.pop("cases", None)
        out.append(manifest)
    out.sort(key=lambda row: row.get("created_at") or "", reverse=True)
    return out[:limit]


def scope_of(status):
    """Which scope an outcome lands in.

    ``fail`` is the pipeline's; ``invalid`` is the case's own figures; a run
    that could not be measured is an ``error``.  The case runner already
    draws that line, so this reads its verdict rather than re-deciding it.
    """
    value = str(status or "").strip().lower()
    if value == "pass":
        return "pass"
    if value == "invalid":
        return "invalid"
    if value == "fail":
        return "fail"
    return "error"


def count(results):
    """The counts for a list of case outcomes."""
    counts = {scope: 0 for scope in SCOPES}
    counts["total"] = len(list(results or []))
    for row in results or []:
        scope = scope_of((row or {}).get("status"))
        counts[scope] = counts.get(scope, 0) + 1
    return counts


def trend(limit=20, direction=None):
    """The counts of recent runs, newest first."""
    out = []
    for manifest in runs(limit=limit, direction=direction):
        out.append({
            "run_id": manifest.get("run_id"),
            "direction": manifest.get("direction"),
            "created_at": manifest.get("created_at"),
            "counts": manifest.get("counts") or {},
        })
    return out


def _previous_run(manifest):
    """The run that came before this one in the same direction."""
    candidates = [row for row in runs(limit=200)
                  if row.get("direction") == manifest.get("direction")]
    candidates.sort(key=lambda row: row.get("created_at") or "")
    mine = manifest.get("created_at") or ""
    earlier = [row for row in candidates if (row.get("created_at") or "") < mine]
    return earlier[-1] if earlier else None


def regressions(run_id):
    """Cases that passed in the previous run and fail in this one.

    A regression is a blocker whatever the failure budget says: the budget is
    for failures that were always there, not for something that worked and
    stopped working.
    """
    manifest = load_manifest(run_id)
    previous = _previous_run(manifest)
    if previous is None:
        return []
    before = {}
    try:
        with open(os.path.join(str(_state_root()), _safe_run_id(previous.get("run_id")),
                               "manifest.json"), "r", encoding="utf-8") as handle:
            earlier = json.load(handle)
    except Exception:
        return []
    for row in earlier.get("cases") or []:
        before[row.get("case_id")] = (row or {}).get("scope") or scope_of(row.get("status"))
    out = []
    for row in manifest.get("cases") or []:
        case_id = row.get("case_id")
        was = before.get(case_id)
        now = (row or {}).get("scope") or scope_of(row.get("status"))
        if was == "pass" and now == "fail":
            out.append({"case_id": case_id, "from": was, "to": now,
                        "blocker": True,
                        "error": str(row.get("error") or "")[:200]})
    return out


def _case_row(outcome, subject="", tile="", tile_label=""):
    """One row of the manifest: what happened, and where."""
    return {
        "case_id": outcome.get("case_id"),
        "status": outcome.get("status"),
        "scope": scope_of(outcome.get("status")),
        "error": str(outcome.get("error") or "")[:300],
        "duration_ms": outcome.get("duration_ms"),
        "subject": subject,
        "tile": tile,
        "tile_label": tile_label,
    }


def run_direction1(case_ids=None, subject=None, tile=None, style="apa",
                   length=1200, limit=None, log=True):
    """Direction 1: replay stored cases and count them by scope.

    Returns the manifest.  Every case is replayed through the paper path and
    checked by the same code the case runner uses, so a case that passes here
    passes there.  No model call is made, and the manifest says so.
    """
    cases = case_store.load_cases(subject=subject, tile=tile)
    missing = []
    if case_ids:
        wanted = [str(c) for c in case_ids]
        found = {str(case.get("id")): case for case in cases}
        cases = [found[c] for c in wanted if c in found]
        missing = [c for c in wanted if c not in found]
    if limit:
        cases = cases[:int(limit)]

    manifest = new_manifest("direction1")
    started = time.perf_counter()
    rows = []
    for case_id in missing:
        # A case that was asked for and is not there could not be measured.
        rows.append(_case_row({"case_id": case_id, "status": "error",
                                "error": "no such case"}))
    for case in cases:
        try:
            outcome = case_runner.run_case_object(case, style=style, length=length, log=log)
        except Exception as error:                      # a crash is an error, not a failure
            outcome = {"case_id": case.get("id"), "status": "error",
                       "error": str(error)[:300]}
        rows.append(_case_row(outcome, case.get("subject") or "", case.get("tile") or "",
                              case.get("tile_label") or ""))
        manifest["cases"] = rows
        manifest["counts"] = count(rows)
        save_manifest(manifest["run_id"], manifest)

    manifest["counts"] = count(rows)
    manifest["cost"]["seconds"] = round(time.perf_counter() - started, 2)
    manifest["cost"]["model_calls"] = 0
    manifest["status"] = "done"
    manifest["finished_at"] = _now()
    save_manifest(manifest["run_id"], manifest)
    # The regression line reads the previous run from disk, so the manifest
    # has to be there first.
    manifest["regressions"] = regressions(manifest["run_id"])
    save_manifest(manifest["run_id"], manifest)
    _log(manifest)
    return manifest


def _tile_rows():
    """Every tile the product offers, in the order the shelf lists them."""
    from . import paper_batch
    rows = []
    data = paper_batch.sections()
    for section in data.get("subjects") or []:
        for group in section.get("groups") or []:
            for tile in group.get("tiles") or []:
                rows.append({
                    "subject": section.get("id"),
                    "subject_label": section.get("label") or section.get("id"),
                    "group": group.get("label") or "",
                    "tile": tile.get("key"),
                    "tile_label": tile.get("label") or tile.get("key"),
                    "service": tile.get("service") or "",
                    "has_defaults": bool(tile.get("has_defaults")),
                })
    return rows


def select_tiles(budget=None):
    """The tiles a Direction 2 run covers.

    ``budget=None`` takes one tile per subject: a representative sample that
    costs nothing, because the tile path makes no model call.  ``budget="all"``
    takes every tile.  A number takes that many tiles in shelf order.  Zero
    is refused: a run that covers nothing is not a measurement.
    """
    rows = _tile_rows()
    if budget == "all":
        return rows
    if budget is None:
        chosen, seen = [], set()
        for row in rows:
            if row["subject"] in seen:
                continue
            seen.add(row["subject"])
            chosen.append(row)
        return chosen
    try:
        count = int(budget)
    except (TypeError, ValueError):
        raise ValueError("the budget must be a number, 'all', or nothing (got %r)" % (budget,))
    if count <= 0:
        raise ValueError("the budget must be greater than zero")
    return rows[:count]


def _tile_inputs(subject, tile_key, declared=None):
    """The figures a Direction 2 run declares for one tile, and where they came from.

    Three sources, in order of authority:

    1. what the caller declared for this run;
    2. the tile's **published defaults** - available only when the process has
       the presets configured (the workbench does; a bare process does not);
    3. the tile's **first stored case** - the representative figures the case
       store already holds for that tile.

    The source is returned with the figures and recorded in the manifest, so a
    reader knows which set was used.  A tile with none of the three is
    **skipped**, not failed: there are no figures to disagree with.
    """
    from . import case_store as _store
    from . import paper_batch as _batch
    if isinstance(declared, dict) and declared:
        return declared, "declared"
    try:
        _subject_row, _group, tile = _batch._find_tile(subject, tile_key)
    except Exception:
        tile = {}
    preset = _batch._preset_for({"preset": tile.get("preset")})
    inputs = (preset or {}).get("inputs") or {}
    if inputs:
        return inputs, "preset"
    for case in _store.load_cases(subject=subject, tile=tile_key):
        case_inputs = case.get("inputs") or {}
        if case_inputs:
            return case_inputs, "case"
    return {}, "none"


def _checkpoint(manifest, rows):
    """Write the rows so far, so a killed run still shows what it reached."""
    manifest["cases"] = list(rows)
    manifest["counts"] = _count_direction2(rows)
    save_manifest(manifest["run_id"], manifest)
    return manifest


def run_direction2(tiles=None, budget=None, style="apa", length=1200, use_rag=True,
                   inputs=None):
    """Direction 2: build each tile's paper from declared figures and score it
    with the code-only rubric.

    The tile path is **model-free**, so this direction costs no tokens and
    says so in the manifest.  A tile with no declared figures is **skipped**,
    not failed: there is no computation to disagree with.
    """
    from . import eval_rubric
    from . import paper_batch

    if tiles is None:
        rows = select_tiles(budget)
    else:
        wanted = set(str(t) for t in tiles)
        rows = [row for row in _tile_rows() if str(row["tile"]) in wanted]

    manifest = new_manifest("direction2")
    manifest["budget"] = "all" if budget == "all" else budget
    started = time.perf_counter()
    rows_out = []
    for row in rows:
        started_tile = time.perf_counter()
        rubric = None
        rag = None
        declared, source = _tile_inputs(row["subject"], row["tile"],
                                         (inputs or {}).get(row["tile"]))
        if not declared:
            rows_out.append({"tile": row["tile"], "subject": row["subject"],
                             "tile_label": row["tile_label"],
                             "status": "skipped", "scope": "skipped",
                             "inputs_source": source,
                             "reason": "the tile has no declared figures to build it from",
                             "duration_ms": 0})
            _checkpoint(manifest, rows_out)
            continue
        try:
            result = paper_batch.generate_one(row["subject"], row["tile"], style=style,
                                              length=length, format="both",
                                              inputs=declared)
        except Exception as error:
            rows_out.append({"tile": row["tile"], "subject": row["subject"],
                             "status": "error", "scope": "error",
                             "inputs_source": source,
                             "error": str(error)[:300],
                             "duration_ms": int((time.perf_counter() - started_tile) * 1000)})
            _checkpoint(manifest, rows_out)
            continue

        status = result.get("status")
        duration = int((time.perf_counter() - started_tile) * 1000)
        if status != "ok":
            # `needs_input` is a tile with no published defaults, and the
            # statements tile is a different product.  Neither is a failure.
            rows_out.append({"tile": row["tile"], "subject": row["subject"],
                             "tile_label": row["tile_label"],
                             "status": status, "scope": "skipped",
                             "inputs_source": source,
                             "reason": str(result.get("error") or "")[:200],
                             "duration_ms": duration})
            _checkpoint(manifest, rows_out)
            continue

        if use_rag:
            try:
                rag = eval_rubric.score_rag(row["subject"], row["tile"],
                                             objective=result.get("objective"))
            except Exception as error:
                rag = {"measured": False, "reason": str(error)[:160]}
        rubric = eval_rubric.score_paper(
            case_runner._docx_text(result.get("bytes") or b""),
            computed=result.get("computation") or {},
            workbook_text=case_runner._xlsx_text(result.get("xlsx") or b"")
            if result.get("xlsx") else "",
            contract={"sections": list(eval_rubric.TILE_CONTRACT_SECTIONS)},
            length_target=length, rag=rag)
        rows_out.append({
            "tile": row["tile"], "subject": row["subject"],
            "tile_label": row["tile_label"], "status": "pass" if rubric["passed"] else "fail",
            "scope": "pass" if rubric["passed"] else "fail",
            "duration_ms": duration,
            "inputs_source": source,
            "problems": rubric["problems"][:5],
            "sources": result.get("sources"), "background": result.get("background"),
            "gaps": result.get("gaps"),
            "rag_measured": bool((rag or {}).get("measured")),
            "model_calls": 0,
        })
        _checkpoint(manifest, rows_out)

    manifest["cases"] = rows_out
    manifest["counts"] = _count_direction2(rows_out)
    manifest["cost"]["seconds"] = round(time.perf_counter() - started, 2)
    manifest["cost"]["model_calls"] = 0
    manifest["status"] = "done"
    manifest["finished_at"] = _now()
    save_manifest(manifest["run_id"], manifest)
    manifest["regressions"] = regressions(manifest["run_id"])
    save_manifest(manifest["run_id"], manifest)
    _log(manifest)
    return manifest


def _count_direction2(rows):
    """The counts of a Direction 2 run.

    A tile that was skipped is not a failure, so it has its own number.
    """
    counts = {scope: 0 for scope in SCOPES}
    counts["skipped"] = 0
    counts["total"] = len(list(rows or []))
    for row in rows or []:
        scope = (row or {}).get("scope") or scope_of((row or {}).get("status"))
        if scope == "skipped":
            counts["skipped"] = counts.get("skipped", 0) + 1
        elif scope in counts:
            counts[scope] += 1
        else:
            counts["error"] += 1
    return counts


def durability(green_runs=3, limit=100000):
    """For each pipeline cause: how many consecutive green replays it has.

    **One passing replay closes an instance; it does not prove the class.**
    A cause counts as durable only when it has a durable artifact *and* this
    many green replays in a row.  A failure in between resets the run.

    The count comes from the ops log: a verified record is a green replay and
    carries its cause; an open record of the same cause is a failure.
    """
    from . import cause_ledger
    from . import causes as _causes
    from . import ops_log as _log

    ledger = cause_ledger.summary(limit=limit)
    rows = ledger.get("causes") or []
    fixed_at = {row.get("cause"): row.get("fixed_at") or "" for row in rows}

    runs = {}
    for record in _log.list_errors(limit=limit, status="all"):
        cause = _causes.classify_cause(record.get("error") or "",
                                       record.get("problem"))["cause"]
        meta = _causes.REMEDIES.get(cause) or _causes.REMEDIES["pipeline.unknown"]
        if meta.get("scope") != _causes.PIPELINE:
            continue
        entry = runs.setdefault(cause, {"cause": cause, "green": 0, "run": 0, "longest": 0,
                                        "fixed_at": fixed_at.get(cause) or "",
                                        "artifacts": list(meta.get("artifact") or [])})
        if record.get("verified"):
            entry["green"] += 1
            entry["run"] += 1
            if entry["run"] > entry["longest"]:
                entry["longest"] = entry["run"]
        elif record.get("resolved") or record.get("invalid") or record.get("dismissed"):
            # An instance closed without a verified replay: not green, but the
            # class did not fail either.  It does not break the run.
            continue
        else:
            entry["run"] = 0
    for entry in runs.values():
        entry["durable"] = bool(entry["fixed_at"]) and entry["run"] >= int(green_runs)
        entry["green_runs_required"] = int(green_runs)
    return list(runs.values())


def run_direction3(limit=200, green_runs=3):
    """Direction 3: what the repair loop closed, what it cost, and whether it held.

    The causes that count are the **pipeline** ones.  An input or transient
    class is refused at intake and never reaches the ledger, so it is not
    counted as a repair the loop made.
    """
    from . import autoresearch
    from . import cause_ledger
    from . import usage as _usage

    manifest = new_manifest("direction3")
    started = time.perf_counter()

    ledger = cause_ledger.summary()
    totals = ledger.get("summary") or {}
    experiments = autoresearch.experiments(limit=limit) or []

    spent = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "seconds": 0.0, "models": {}}
    by_model = {}
    for experiment in experiments:
        usage = experiment.get("usage") or {}
        if not usage:
            continue
        spent = _usage.add(spent, usage)
        for model, row in (usage.get("models") or {}).items():
            merged = by_model.setdefault(model, {"calls": 0, "input_tokens": 0,
                                                 "output_tokens": 0})
            for key in ("calls", "input_tokens", "output_tokens"):
                merged[key] += int(row.get(key) or 0)

    durability_rows = durability(green_runs=green_runs)
    durable = [row for row in durability_rows if row.get("durable")]

    manifest["counts"] = {
        "pass": 0, "fail": 0, "invalid": 0, "error": 0,
        "total": len(experiments),
        "causes": totals.get("causes", 0),
        "fixed": totals.get("fixed", 0),
        "recurring": totals.get("recurring", 0),
        "unfixed": totals.get("unfixed", 0),
        "closed_instance_only": totals.get("closed_instance_only", 0),
        "durable": len(durable),
    }
    manifest["cost"] = {
        "model_calls": spent["calls"],
        "tokens_in": spent["input_tokens"],
        "tokens_out": spent["output_tokens"],
        "usd": _usage.cost_of(spent),
        "seconds": round(time.perf_counter() - started, 2),
        "by_model": by_model,
    }
    manifest["causes"] = ledger.get("causes") or []
    manifest["durability"] = durability_rows
    manifest["experiments"] = [
        {"ts": row.get("ts"), "error": str(row.get("error") or "")[:200],
         "outcome": row.get("outcome"), "model": row.get("model"),
         "usage": row.get("usage")} for row in experiments[:limit]
    ]
    manifest["status"] = "done"
    manifest["finished_at"] = _now()
    save_manifest(manifest["run_id"], manifest)
    manifest["regressions"] = regressions(manifest["run_id"])
    save_manifest(manifest["run_id"], manifest)
    _log(manifest)
    return manifest


def explainer_sections(manifest):
    """The owner-readable account of one run, as document sections."""
    counts = manifest.get("counts") or {}
    cost = manifest.get("cost") or {}
    env = manifest.get("environment") or {}
    summary = summarise(manifest)
    sections = []
    sections.append(("What this run measured", [
        "Direction: %s" % manifest.get("direction"),
        "Run: %s (%s)" % (manifest.get("run_id"), manifest.get("created_at")),
        "Build: %s" % (env.get("build") or "unknown"),
        "Corpus index reachable: %s" % ("yes" if env.get("corpus_available") else "no"),
    ]))
    sections.append(("The count", [
        "Pass: %d" % counts.get("pass", 0),
        "Pipeline failures: %d (the budget is %d)" % (counts.get("fail", 0), FAIL_BUDGET),
        "Invalid inputs (the case's own figures): %d" % counts.get("invalid", 0),
        "Errors (could not be measured): %d" % counts.get("error", 0),
        "Skipped (nothing to measure): %d" % counts.get("skipped", 0),
        "Total: %d" % counts.get("total", 0),
    ]))
    sections.append(("Regressions", [
        "A case that passed before and fails now is a blocker: %d"
        % len(manifest.get("regressions") or []),
    ] + ["- %s: %s" % (row.get("case_id"), (row.get("error") or "")[:120])
         for row in (manifest.get("regressions") or [])[:10]]))
    sections.append(("What it cost", [
        "Model calls: %d" % cost.get("model_calls", 0),
        "Input tokens: %d" % cost.get("tokens_in", 0),
        "Output tokens: %d" % cost.get("tokens_out", 0),
        "Dollar cost: %s" % ("not priced" if cost.get("usd") is None
                              else "%.4f USD" % float(cost.get("usd"))),
        "Seconds: %s" % cost.get("seconds", 0),
    ]))
    if manifest.get("direction") == "direction3":
        sections.append(("The causes", [
            "Causes: %s" % (manifest.get("counts") or {}).get("causes", 0),
            "Fixed with a durable artifact: %s" % (manifest.get("counts") or {}).get("fixed", 0),
            "Recurring (the fix did not hold): %s" % (manifest.get("counts") or {}).get("recurring", 0),
            "Durable (three green replays in a row): %s"
            % (manifest.get("counts") or {}).get("durable", 0),
        ]))
    failures = [row for row in (manifest.get("cases") or [])
                if (row.get("scope") or "") == "fail"][:10]
    sections.append(("What failed", [
        "Pipeline failures are named below.  Each one carries the case, the tile and "
        "the message the checker gave.",
    ] + ["- %s: %s" % (row.get("case_id") or row.get("tile"),
                      (row.get("error") or "; ".join(row.get("problems") or []))[:160])
         for row in failures]))
    return sections


def write_explainer(manifest):
    """Write the run's explainer .docx beside its manifest.

    The styled report and the admin panel are the design lane's; this is the
    plain document the computation lane can stand behind, rendered the same
    way the case runner renders its explainer.
    """
    try:
        from . import docx as _docx
        run_dir = os.path.join(str(_state_root()), _safe_run_id(manifest.get("run_id")))
        os.makedirs(run_dir, exist_ok=True)
        path = os.path.join(run_dir, "explainer.docx")
        with open(path, "wb") as handle:
            handle.write(_docx.render_bytes(
                "Eval run %s - %s" % (manifest.get("run_id"), manifest.get("direction")),
                explainer_sections(manifest)))
        return path
    except Exception:
        return ""


def _log(manifest):
    """Record the run in the ops log, when the owner has the log switched on."""
    try:
        ops_log.log_run(
            "eval", "eval:%s" % manifest.get("direction"), manifest.get("status"),
            error=None,
            duration_ms=(manifest.get("cost") or {}).get("seconds", 0) * 1000,
            gaps=[])
    except Exception:
        pass
    return manifest


def summarise(manifest):
    """The short, owner-readable account of one run."""
    counts = manifest.get("counts") or {}
    return {
        "run_id": manifest.get("run_id"),
        "direction": manifest.get("direction"),
        "created_at": manifest.get("created_at"),
        "pass": counts.get("pass", 0),
        "fail": counts.get("fail", 0),
        "invalid": counts.get("invalid", 0),
        "error": counts.get("error", 0),
        "total": counts.get("total", 0),
        "budget": FAIL_BUDGET,
        "within_budget": counts.get("fail", 0) <= FAIL_BUDGET,
        "regressions": len(manifest.get("regressions") or []),
        "corpus_available": (manifest.get("environment") or {}).get("corpus_available"),
        "model_calls": (manifest.get("cost") or {}).get("model_calls", 0),
        "seconds": (manifest.get("cost") or {}).get("seconds", 0),
    }
