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
from decimal import Decimal, InvalidOperation
from hashlib import sha256

from . import charts, deck, diagrams, docx, figures, renderers
from . import export as case_export

FORMAT = "bp-visual/1"
#: What a visual can be.  The rest of the figure kinds stay available through the
#: paper; these are the ones a student asks for on their own.
KINDS = ("bar", "line", "area", "scatter", "candlestick", "pie", "stacked_bar",
         "waterfall", "table", "pareto")

#: Words a student uses, mapped to the chart they usually mean.
KIND_CUES = (
    ("pareto", ("pareto", "vital few", "running total", "cumulative", "concentration",
                "which few", "the few that")),
    ("waterfall", ("bridge", "movement", "moved", "driven by", "walk", "step change")),
    ("candlestick", ("candlestick", "ohlc", "open high low close", "stock price",
                     "share price", "price range")),
    ("scatter", ("relationship", "correlation", "correlate", "against", "versus",
                 "risk and return", "ad spend", "x and y")),
    ("pie", ("share", "mix", "composition", "split", "proportion", "breakdown")),
    ("stacked_bar", ("mix", "composition", "breakdown", "split")),
    ("area", ("area chart", "area graph")),
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
                     "kinds": [(figure.get("spec") or {}).get("kind")
                               or figure.get("kind") for figure in record.get("figures") or []]})
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return {"visuals": rows}


def delete(visual_id):
    path = _path(_clean_id(visual_id))
    if not os.path.exists(path):
        raise VisualError("no such visual")
    os.unlink(path)
    return {"deleted": visual_id}


# --- data sources ----------------------------------------------------------

def _source_file(file):
    """The compact file record a visual keeps when its figures came from a file."""
    if not isinstance(file, dict) or not str(file.get("filename") or "").strip():
        return None
    keys = ("id", "filename", "sha256", "sheet", "ext", "edited", "kind")
    compact = {key: file.get(key) for key in keys if file.get(key) is not None}
    if isinstance(file.get("columns"), dict):
        compact["columns"] = {key: file["columns"].get(key)
                              for key in ("label", "value", "cumulative")
                              if file["columns"].get(key)}
    return compact


def _declared(points, source_file=None):
    """A bundle built from figures the student typed or read from their file."""
    if not isinstance(points, list) or not points:
        raise VisualError("a declared visual needs at least one point")
    file = _source_file(source_file)
    note = "declared by the student"
    label = "Figures you declared"
    if file:
        note += " from %s" % file["filename"]
        if file.get("sha256"):
            note += " (sha256 %s)" % str(file["sha256"])[:12]
        if file.get("edited"):
            note += "; edited after reading"
        label = "Figures read from %s" % file["filename"]
    artifacts, outputs, series = [], {}, []
    for index, point in enumerate(points, 1):
        if not isinstance(point, dict):
            raise VisualError("every point must be an object with 'label' and 'value'")
        label_text = str(point.get("label") or "").strip()
        if not label_text:
            raise VisualError("every point needs a label")
        try:
            float(point.get("value"))
        except (TypeError, ValueError):
            raise VisualError("point %r needs a number in 'value'" % label_text)
        label_id = "declared_label_%d" % index
        value_id = "declared_value_%d" % index
        for key, stored in ((label_id, label_text), (value_id, str(point.get("value")).strip())):
            artifacts.append([key, [key, "", "entity", "base"], note])
            outputs[key] = stored
        entry = {"label": label_text, "label_artifact": label_id, "artifact": value_id}
        group = str(point.get("group") or "").strip()
        if group:
            entry["group"] = group
        for key in ("x", "open", "high", "low", "close"):
            raw = point.get(key)
            if raw is None or not str(raw).strip():
                continue
            try:
                float(raw)
            except (TypeError, ValueError):
                raise VisualError("point %r needs a number in %r" % (label_text, key))
            artifact_id = "declared_%s_%d" % (key, index)
            artifacts.append([artifact_id, [artifact_id, "", "entity", "base"], note])
            outputs[artifact_id] = str(raw).strip()
            entry[key] = artifact_id
        running = point.get("cumulative")
        if running is not None and str(running).strip():
            try:
                float(running)
            except (TypeError, ValueError):
                raise VisualError("point %r needs a number in 'cumulative'" % label_text)
            running_id = "declared_cumulative_%d" % index
            artifacts.append([running_id, [running_id, "", "entity", "base"], note])
            outputs[running_id] = str(running).strip()
            entry["cumulative"] = running_id
        series.append(entry)
    bundle = {"delivery": {"appendix": {"artifacts": artifacts}},
              "reperform": {"outputs": outputs}}
    return bundle, series, label


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
        return _declared(source.get("points"), source.get("file"))
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
    if kind == "scatter":
        missing = [entry["label"] for entry in series if not entry.get("x")]
        if missing:
            raise VisualError("a scatter plot needs an x value for every point; missing: %s"
                              % ", ".join(missing[:3]))
        return {"format": "bp-chart/1", "kind": "scatter", "title": title,
                "series": [{"label": entry["label"], "artifact": entry["artifact"],
                            "x_artifact": entry["x"],
                            "label_artifact": entry.get("label_artifact")}
                           for entry in series]}
    if kind == "candlestick":
        missing = [entry["label"] for entry in series
                   if not all(entry.get(key) for key in ("open", "high", "low", "close"))]
        if missing:
            raise VisualError("a candlestick chart needs open, high, low and close for every "
                              "period; missing: %s" % ", ".join(missing[:3]))
        return {"format": "bp-chart/1", "kind": "candlestick", "title": title,
                "series": [{"label": entry["label"], "artifact": entry["close"],
                            "open": entry["open"], "high": entry["high"],
                            "low": entry["low"], "close": entry["close"],
                            "label_artifact": entry.get("label_artifact")}
                           for entry in series]}
    return {"format": "bp-chart/1", "kind": kind, "title": title, "series": series}


# --- building one visual ---------------------------------------------------

def _record_source(source, label):
    stored = {"kind": source.get("kind"), "label": label}
    if source.get("case_id"):
        stored["case_id"] = source["case_id"]
    file = _source_file(source.get("file"))
    if file:
        stored["file"] = file
    return stored


def _diagram_record(request):
    """A framework or process diagram, from the student's own words."""
    title = str(request.get("title") or "").strip()
    if not title:
        raise VisualError("a diagram needs a title")
    source = request.get("source")
    spec = source.get("spec") if isinstance(source, dict) else None
    if not isinstance(spec, dict):
        raise VisualError("a diagram needs a spec")
    spec = dict(spec)
    spec.setdefault("format", diagrams.FORMAT)
    try:
        kind, _title, _payload = diagrams.validate_spec(spec)
    except diagrams.DiagramError as error:
        raise VisualError(str(error))
    figure = figures.make("diagram", spec, caption=title, note="Your framework",
                          why="the student asked for this visual", origin="chat")
    figures.render(figure, {})
    figures.stamp(figure, {})
    record = {
        "format": FORMAT,
        "id": "vis_" + sha256((title + kind + str(time.time())).encode("utf-8")).hexdigest()[:12],
        "title": title,
        "source": {"kind": "diagram", "label": "Your framework"},
        "kind": kind,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "figures": [{key: figure[key] for key in
                     ("id", "format", "kind", "spec", "caption", "note", "why",
                      "origin", "place", "sources", "digest", "table") if key in figure}],
        "bundle": {},
    }
    return record, figure


def _gantt_record(request):
    """A project timeline from declared task names and day numbers."""
    title = str(request.get("title") or "").strip()
    if not title:
        raise VisualError("a timeline needs a title")
    source = request.get("source")
    activities = source.get("activities") if isinstance(source, dict) else None
    if not isinstance(activities, list) or not activities:
        raise VisualError("a timeline needs at least one task")
    artifacts, outputs, clean = [], {}, []
    for index, activity in enumerate(activities, 1):
        if not isinstance(activity, dict):
            raise VisualError("every task must be an object with label, start and end")
        label = str(activity.get("label") or "").strip()
        if not label:
            raise VisualError("every task needs a label")
        start = str(activity.get("start") or "").strip()
        end = str(activity.get("end") or "").strip()
        try:
            start_value, end_value = Decimal(start), Decimal(end)
        except (InvalidOperation, ValueError):
            raise VisualError("task %r needs numeric start and end day numbers" % label)
        if end_value < start_value:
            raise VisualError("task %r ends before it starts" % label)
        label_id = "gantt_label_%d" % index
        start_id = "gantt_start_%d" % index
        end_id = "gantt_end_%d" % index
        for key, value in ((label_id, label), (start_id, start), (end_id, end)):
            artifacts.append([key, [key, "", "entity", "base"], "declared by the student"])
            outputs[key] = value
        entry = {"id": "gantt_%d" % index, "label": label,
                 "start": start_id, "end": end_id}
        for key, text_key in (("start_label", "start_label"), ("end_label", "end_label")):
            text = str(activity.get(text_key) or "").strip()
            if text:
                artifact_id = "gantt_%s_%d" % (key, index)
                artifacts.append([artifact_id, [artifact_id, "", "entity", "base"],
                                  "declared by the student"])
                outputs[artifact_id] = text
                entry[key] = artifact_id
        clean.append(entry)
    spec = {"format": "bp-chart/1", "kind": "gantt", "title": title,
            "activities": clean}
    bundle = {"delivery": {"appendix": {"artifacts": artifacts}},
              "reperform": {"outputs": outputs}}
    figure = figures.make("chart", spec, caption=title, note="Your project timeline",
                          why="the student asked for this visual", origin="chat")
    figures.render(figure, bundle)
    figures.stamp(figure, bundle)
    record = {
        "format": FORMAT,
        "id": "vis_" + sha256((title + "gantt" + str(time.time())).encode("utf-8")).hexdigest()[:12],
        "title": title,
        "source": {"kind": "gantt", "label": "Your project timeline"},
        "kind": "gantt",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "figures": [{key: figure[key] for key in
                     ("id", "format", "kind", "spec", "caption", "note", "why",
                      "origin", "place", "sources", "digest", "table") if key in figure}],
        "bundle": bundle,
    }
    return record, figure


def _record(request, run=None):
    """(record, figure) for a request, without storing it."""
    if not isinstance(request, dict):
        raise VisualError("a visual request must be an object")
    source = request.get("source")
    if isinstance(source, dict) and source.get("kind") == "diagram":
        return _diagram_record(request)
    if isinstance(source, dict) and source.get("kind") == "gantt":
        return _gantt_record(request)
    title = str(request.get("title") or "").strip()
    if not title:
        raise VisualError("a visual needs a title")
    bundle, series, label = source_bundle(source, run)
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
        "source": _record_source(request["source"], label),
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
