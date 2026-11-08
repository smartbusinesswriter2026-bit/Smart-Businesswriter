"""Standalone visuals: a figure without a paper.

A student who wants one chart should not have to write a paper first.  This module
owns a visual's **own store**, its data sources and its exports, so a figure can be
made, kept and downloaded without a case or a draft.

A visual has exactly one job: draw the figures the student asked for, from a source
they named.  Three sources:

* **declared** - figures the student types.  They are the student's own data, so the
  figure says so; they are never merged into a case's artifacts and never called
  evidence.
* **calculation** - a frozen method run on declared inputs.  The values are the
  core's recorded outputs.
* **case** - artifacts already recorded in a case.

The chart is chosen by rule from the data's shape and the student's own words, and
the student confirms the kind.  No model picks a chart and no model writes a number.
"""

import json
import os
import re
import tempfile
import time
import uuid
from hashlib import sha256

from . import charts, deck, docx, figures, renderers
from . import export as case_export

FORMAT = "bp-visual/1"
#: What a visual can be.  The rest of the figure kinds stay available through the
#: paper; these are the ones a student asks for on their own.
KINDS = ("bar", "line", "pie", "stacked_bar", "waterfall", "table", "pareto")

#: Words a student uses, mapped to the chart they usually mean.
KIND_CUES = (
    ("pareto", ("pareto", "vital few", "running total", "cumulative", "concentration",
                "which few", "the few that")),
    ("waterfall", ("bridge", "movement", "moved", "driven by", "walk", "step change")),
    ("pie", ("share", "mix", "composition", "split", "proportion", "breakdown")),
    ("stacked_bar", ("mix", "composition", "breakdown", "split")),
    ("line", ("trend", "over time", "grew", "fell", "growth", "quarter", "year",
              "month", "week", "forecast")),
    ("bar", ("compare", "comparison", "versus", "rank", "by region", "by product",
             "by channel")),
)


#: The frozen-core callable, attached by `bp.server` through `api.attach_methods`.
METHOD_RUN = None


def set_method_compute(run):
    """Attach the frozen-core callable the 'calculation' source uses."""
    global METHOD_RUN
    METHOD_RUN = run


class VisualError(ValueError):
    """The visual cannot be made from what was asked."""


# --- the store -------------------------------------------------------------

def state_dir():
    from . import ops
    root = os.path.join(str(ops.state_dir()), "visuals")
    os.makedirs(root, exist_ok=True)
    return root


def _path(visual_id):
    return os.path.join(state_dir(), str(visual_id) + ".json")


def _clean_id(visual_id):
    text = str(visual_id or "").strip()
    if not re.match(r"^vis_[0-9a-f]{12}$", text):
        raise VisualError("no such visual")
    return text


def save(record):
    if not isinstance(record, dict) or record.get("format") != FORMAT:
        raise VisualError("a visual record must carry format %r" % FORMAT)
    target = _path(_clean_id(record.get("id")))
    payload = json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True)
    handle, temp_name = tempfile.mkstemp(dir=state_dir(), prefix=".tmp-visual-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return record


def load(visual_id):
    path = _path(_clean_id(visual_id))
    if not os.path.exists(path):
        raise VisualError("no such visual")
    with open(path, encoding="utf-8") as stream:
        return json.load(stream)


def listing():
    rows = []
    for name in sorted(os.listdir(state_dir())):
        if not name.endswith(".json") or name.startswith("."):
            continue
        try:
            with open(os.path.join(state_dir(), name), encoding="utf-8") as stream:
                record = json.load(stream)
        except (OSError, ValueError):
            continue
        rows.append({"id": record.get("id"), "title": record.get("title"),
                     "source": record.get("source"), "created_at": record.get("created_at"),
                     "kinds": [figure.get("kind") for figure in record.get("figures") or []]})
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {"visuals": rows}


def delete(visual_id):
    path = _path(_clean_id(visual_id))
    if not os.path.exists(path):
        raise VisualError("no such visual")
    os.unlink(path)
    return {"deleted": visual_id}


# --- data sources ----------------------------------------------------------

def _declared(points):
    """A bundle built from figures the student typed, labelled as their own."""
    if not isinstance(points, list) or not points:
        raise VisualError("a declared visual needs at least one point")
    artifacts, outputs, series = [], {}, []
    for index, point in enumerate(points, 1):
        if not isinstance(point, dict):
            raise VisualError("every point must be an object with 'label' and 'value'")
        label = str(point.get("label") or "").strip()
        if not label:
            raise VisualError("every point needs a label")
        try:
            value = float(point.get("value"))
        except (TypeError, ValueError):
            raise VisualError("point %r needs a number in 'value'" % label)
        label_id = "declared_label_%d" % index
        value_id = "declared_value_%d" % index
        for key, stored in ((label_id, label), (value_id, str(point.get("value")).strip())):
            artifacts.append([key, [key, "", "entity", "base"], "declared by the student"])
            outputs[key] = stored
        entry = {"label": label, "label_artifact": label_id, "artifact": value_id}
        running = point.get("cumulative")
        if running is not None and str(running).strip():
            try:
                float(running)
            except (TypeError, ValueError):
                raise VisualError("point %r needs a number in 'cumulative'" % label)
            running_id = "declared_cumulative_%d" % index
            artifacts.append([running_id, [running_id, "", "entity", "base"],
                              "declared by the student"])
            outputs[running_id] = str(running).strip()
            entry["cumulative"] = running_id
        series.append(entry)
    bundle = {"delivery": {"appendix": {"artifacts": artifacts}},
              "reperform": {"outputs": outputs}}
    return bundle, series, "Figures you declared"


def _calculation(method, inputs, run):
    """A bundle from one frozen method run on declared inputs."""
    if run is None:
        raise VisualError("the frozen core is not attached, so nothing can be computed")
    method_id = str(method or "").strip()
    if not method_id:
        raise VisualError("a calculation needs a method id")
    try:
        output = run(method_id, inputs or {})
    except Exception as error:
        raise VisualError(str(error)[:300])
    if not isinstance(output, dict):
        output = {"value": output}
    artifacts, outputs, series = [], {}, []
    for name, value in output.items():
        if str(name).startswith("_"):
            continue
        key = "%s.%s" % (method_id, name)
        artifacts.append([key, [key, "", "entity", "base"], method_id])
        outputs[key] = str(value)
        series.append({"label": str(name).replace("_", " ").title(), "artifact": key})
    if len(series) < 2:
        raise VisualError("that method records a single figure, which is a sentence, not a chart")
    bundle = {"delivery": {"appendix": {"artifacts": artifacts}},
              "reperform": {"outputs": outputs}}
    return bundle, series, "Computed by %s on your inputs" % method_id.replace("_", " ")


def _case(case_id, ids):
    """A bundle from artifacts already recorded in a case."""
    from . import cases as case_store

    bundle = case_store.load(str(case_id))
    rows = {str(row.get("id")): row for row in case_export.artifact_rows(bundle)}
    wanted = [str(item).strip() for item in (ids or []) if str(item).strip()]
    if not wanted:
        wanted = [key for key, row in rows.items()
                  if isinstance(row.get("value"), (int, float, str))
                  and str(row.get("value") or "").strip()]
    series = []
    for key in wanted:
        row = rows.get(key)
        if not row:
            raise VisualError("the case does not record %r" % key)
        label = str(row.get("metric") or key).replace("_", " ").title()
        series.append({"label": label, "artifact": key})
    if len(series) < 2:
        raise VisualError("a chart needs at least two recorded values")
    return bundle, series, "Recorded in this case"


def source_bundle(source, run=None):
    """(bundle, series, label) for the source the student named."""
    if not isinstance(source, dict):
        raise VisualError("a visual needs a 'source' object")
    kind = str(source.get("kind") or "").strip()
    if kind == "declared":
        return _declared(source.get("points"))
    if kind == "calculation":
        return _calculation(source.get("method"), source.get("inputs"), run or METHOD_RUN)
    if kind == "case":
        return _case(source.get("case_id"), source.get("artifacts"))
    raise VisualError("source kind must be 'declared', 'calculation' or 'case'")


# --- choosing the chart ----------------------------------------------------

def propose(source, words="", run=None):
    """The charts this data can carry, best first, each with the reason it fits."""
    bundle, series, label = source_bundle(source, run)
    values = []
    for entry in series:
        row = next((row for row in case_export.artifact_rows(bundle)
                    if row.get("id") == entry["artifact"]), None)
        try:
            values.append(float((row or {}).get("value")))
        except (TypeError, ValueError):
            values.append(0.0)
    text = (" " + str(words or "").lower() + " ")
    can_pareto = bool(series) and all(entry.get("cumulative") for entry in series)
    ranked = []
    if any(value < 0 for value in values):
        ranked.append(("waterfall", "the figures include a fall, so the steps read as a bridge"))
    for kind, cues in KIND_CUES:
        if kind == "pareto" and not can_pareto:
            continue
        if any(cue in text for cue in cues) and kind not in [row[0] for row in ranked]:
            ranked.append((kind, "your words point at %s" % kind.replace("_", " ")))
    if len(series) >= 3:
        ranked.append(("line", "three or more points read as a trend"))
    ranked.append(("bar", "a bar compares the values directly"))
    if len(series) <= 6:
        ranked.append(("pie", "few parts can be read as a whole"))
    seen, proposals = set(), []
    for kind, why in ranked:
        if kind in seen or kind not in KINDS:
            continue
        seen.add(kind)
        proposals.append({"kind": kind, "why": why})
        if len(proposals) == 3:
            break
    return {"source": label, "points": len(series), "proposals": proposals}


def spec_for(kind, series, title):
    if kind not in KINDS:
        raise VisualError("kind must be one of: " + ", ".join(KINDS))
    if kind == "table":
        columns = ["Item", "Value"]
        rows = [{"cells": [entry["label"], {"artifact": entry["artifact"]}]} for entry in series]
        return {"format": "bp-table/1", "title": title, "columns": columns, "rows": rows}
    if kind == "pareto":
        missing = [entry["label"] for entry in series if not entry.get("cumulative")]
        if missing:
            raise VisualError("a pareto chart needs a running total for every point; add a "
                              "third column for %s" % ", ".join(missing[:3]))
        return {"format": "bp-chart/1", "kind": "pareto", "title": title,
                "series": [{"label": entry["label"], "artifact": entry["artifact"],
                            "cumulative": entry["cumulative"],
                            "label_artifact": entry.get("label_artifact")}
                           for entry in series]}
    return {"format": "bp-chart/1", "kind": kind, "title": title, "series": series}


# --- building one visual ---------------------------------------------------

def _record(request, run=None):
    """(record, figure) for a request, without storing it."""
    if not isinstance(request, dict):
        raise VisualError("a visual request must be an object")
    title = str(request.get("title") or "").strip()
    if not title:
        raise VisualError("a visual needs a title")
    bundle, series, label = source_bundle(request.get("source"), run)
    kind = str(request.get("kind") or "").strip()
    if not kind:
        proposals = propose(request.get("source"), request.get("words") or title, run)
        kind = proposals["proposals"][0]["kind"]
    spec = spec_for(kind, series, title)
    figure_kind = "table" if kind == "table" else "chart"
    record_figure = figures.make(figure_kind, spec, caption=title,
                                 note=label, why="the student asked for this visual",
                                 origin="chat")
    figures.render(record_figure, bundle)
    figures.stamp(record_figure, bundle)
    record = {
        "format": FORMAT,
        "id": "vis_" + sha256((title + kind + str(time.time())).encode("utf-8")).hexdigest()[:12],
        "title": title,
        "source": {"kind": request["source"].get("kind"), "label": label,
                   "case_id": request["source"].get("case_id")},
        "kind": kind,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "figures": [{key: record_figure[key] for key in
                     ("id", "format", "kind", "spec", "caption", "note", "why",
                      "origin", "place", "sources", "digest", "table") if key in record_figure}],
        "bundle": bundle,
    }
    return record, record_figure


def build(request, run=None):
    """Create and store a visual from a request.  Returns the record."""
    record, _figure = _record(request, run)
    return save(record)


def preview(request, run=None):
    """The visual a request would make, drawn but not stored."""
    record, figure = _record(request, run)
    return {"title": record["title"], "kind": record["kind"],
            "source": record["source"], "figure": record["figures"][0],
            "svg": (figure.get("asset") or {}).get("svg"),
            "png": bool((figure.get("asset") or {}).get("png"))}


# --- exporting one visual --------------------------------------------------

def _figure_of(record):
    stored = (record.get("figures") or [{}])[0]
    copy = dict(stored)
    figures.render(copy, record.get("bundle") or {})
    figures.stamp(copy, record.get("bundle") or {})
    return copy


def export(record, fmt):
    """(bytes, filename, mime) for one visual in the format asked for."""
    fmt = str(fmt or "png").lower()
    figure = _figure_of(record)
    stem = re.sub(r"[^A-Za-z0-9 _-]+", " ", str(record.get("title") or "visual")).strip() or "visual"
    stem = " ".join(stem.split())[:80]
    if fmt == "png":
        data = (figure.get("asset") or {}).get("png")
        if not data:
            raise VisualError("a PNG needs a rasterizer; none is installed")
        return data, stem + ".png", "image/png"
    if fmt == "svg":
        data = (figure.get("asset") or {}).get("svg")
        if not data:
            raise VisualError("a table has no SVG; export it as Word, Excel or PowerPoint")
        return data.encode("utf-8"), stem + ".svg", "image/svg+xml"
    if fmt == "docx":
        data = docx.render_bytes(record.get("title"), [], figures=[figure])
        return data, stem + ".docx", ("application/vnd.openxmlformats-officedocument"
                                      ".wordprocessingml.document")
    if fmt == "pptx":
        built = {"format": deck.DECK_FORMAT, "slides": [
            deck.slide("title", claim=record.get("title")),
            deck.slide("table" if figure.get("kind") == "table" else "figure",
                       claim=record.get("title"),
                       **({"table": figure["id"]} if figure.get("kind") == "table"
                          else {"figure": figure["id"]})),
        ]}
        data = deck.render(built, {figure["id"]: figure})
        return data, stem + ".pptx", ("application/vnd.openxmlformats-officedocument"
                                      ".presentationml.presentation")
    if fmt == "pdf":
        built = {"format": deck.DECK_FORMAT, "slides": [
            deck.slide("title", claim=record.get("title")),
            deck.slide("table" if figure.get("kind") == "table" else "figure",
                       claim=record.get("title"),
                       **({"table": figure["id"]} if figure.get("kind") == "table"
                          else {"figure": figure["id"]})),
        ]}
        data = deck.pdf_bytes(built, {figure["id"]: figure})
        if data is None:
            raise VisualError("a PDF needs Chrome; none was found on this machine")
        return data, stem + ".pdf", "application/pdf"
    raise VisualError("format must be png, svg, docx, pptx or pdf")

def export_sheet(ids, fmt="docx", title=None):
    """Several visuals on one page, in the order given."""
    records = [load(ident) for ident in ids or []]
    if not records:
        raise VisualError("a figure sheet needs at least one visual")
    fmt = str(fmt or "docx").lower()
    if fmt != "docx":
        raise VisualError("a figure sheet exports as docx")
    drawn = [_figure_of(record) for record in records]
    name = str(title or "Figure sheet").strip() or "Figure sheet"
    stem = re.sub(r"[^A-Za-z0-9 _-]+", " ", name).strip() or "figure sheet"
    stem = " ".join(stem.split())[:80]
    data = docx.render_bytes(name, [], figures=drawn)
    return data, stem + ".docx", ("application/vnd.openxmlformats-officedocument"
                                  ".wordprocessingml.document")
