"""Deterministic SVG charts from stored artifacts (product layer, standard library only).

A chart is described by a small JSON spec and drawn from the **stored** values of
a case bundle; it never receives a model-drawn shape and never prints a number
that is not already recorded.  Rules, all enforced:

* every series names a stored artifact (by metric or artifact id); a missing
  artifact, or a value that is not a number, is refused with a reason;
* the text fields of a spec (title, series label, axis label, note) may **not
  contain digits** - numbers appear only as the stored value strings, so the
  chart cannot invent one;
* the same bundle + spec produce byte-identical SVG (fixed frame, fixed order,
  numbers formatted to two decimals);
* geometry arithmetic (bar lengths, point positions) is rendering-only: the
  labels a reader sees are the stored strings, verbatim.

Kinds: bar, line, area, scatter, candlestick, stacked_bar, waterfall, pie, sparkline,
table, gantt, pareto.

A Gantt chart is drawn from the stored CPM artifacts: each activity names its
early-start and early-finish artifact, and optionally its float and critical
flag.  The drawing scales those stored values into the frame; it does not
schedule, level resources or infer a dependency.

A Pareto chart is drawn from **two stored series**: the bars (each entry's
`artifact`) and the running total (the same entry's `cumulative`).  The drawing
never adds the bars up - a running total it worked out itself would be a figure
the record does not hold.  The running total is only checked to be
non-decreasing; that is a rule, not arithmetic.
"""

import html
import re
from decimal import Decimal, InvalidOperation

from . import export as case_export
from . import theme

FORMAT = "bp-chart/1"
KINDS = ("bar", "line", "area", "scatter", "candlestick", "stacked_bar", "waterfall",
         "pie", "sparkline", "table", "gantt", "pareto", "network")
WIDTH, HEIGHT = 720, 300
#: The categorical palette is defined once, in `theme`, so the builtin drawing and
#: the Plotly template cannot drift apart.
PALETTE = theme.SERIES
_DIGIT = re.compile(r"\d")


class ChartError(ValueError):
    """The chart spec cannot be drawn honestly from the bundle."""


def _text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise ChartError("%s must be non-empty text" % what)
    if _DIGIT.search(value):
        raise ChartError("%s may not contain digits: numbers come only from the stored artifacts (%r)" % (what, value))
    return value.strip()


def _stored_rows(bundle):
    rows = case_export.artifact_rows(bundle)
    if not rows:
        raise ChartError("the bundle records no artifacts to chart")
    return rows


def _row_for(rows, key):
    for row in rows:
        if row.get("metric") == key or row.get("id") == key:
            return row
    raise ChartError("no stored artifact %r in this bundle; recorded: %s"
                     % (key, ", ".join(sorted(str(row.get("metric") or row.get("id")) for row in rows))))


def _number(row, key):
    value = row.get("value")
    if value is None:
        raise ChartError("artifact %r has no recorded value, so it cannot be charted" % key)
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ChartError("artifact %r has a non-numeric value %r, so it cannot be charted" % (key, value))


def validate_spec(spec):
    """Check a chart spec against its own rules (not yet against a bundle)."""
    if not isinstance(spec, dict):
        raise ChartError("chart spec must be an object")
    found_format = spec.get("format", FORMAT)
    if found_format != FORMAT:
        raise ChartError("unsupported chart format %r, expected %r" % (found_format, FORMAT))
    kind = spec.get("kind")
    if kind not in KINDS:
        raise ChartError("kind must be one of: " + ", ".join(KINDS))
    title = _text(spec.get("title"), "chart title")
    if spec.get("note") is not None:
        _text(spec["note"], "chart note")
    if spec.get("x_label") is not None:
        _text(spec["x_label"], "x axis label")
    if spec.get("y_label") is not None:
        _text(spec["y_label"], "y axis label")
    if spec.get("y2_label") is not None:
        _text(spec["y2_label"], "second y axis label")
    if kind == "pareto":
        entries = spec.get("series")
        if not isinstance(entries, list) or len(entries) < 2:
            raise ChartError("a pareto chart needs at least two 'series' entries")
        clean = []
        for index, entry in enumerate(entries):
            where = "series[%d]" % index
            if not isinstance(entry, dict):
                raise ChartError("%s must be an object" % where)
            source = entry.get("label_artifact")
            if source is not None:
                if not isinstance(source, str) or not source.strip():
                    raise ChartError("%s 'label_artifact' must be a stored artifact id" % where)
                if not isinstance(entry.get("label"), str) or not entry["label"].strip():
                    raise ChartError("%s needs a 'label'" % where)
            else:
                _text(entry.get("label"), "%s label" % where)
            for key in ("artifact", "cumulative"):
                value = entry.get(key)
                if not isinstance(value, str) or not value.strip():
                    raise ChartError("%s needs a stored artifact id in %r" % (where, key))
            clean.append({"label": entry["label"], "artifact": entry["artifact"].strip(),
                          "cumulative": entry["cumulative"].strip(),
                          "label_artifact": source})
        return kind, title, clean
    if kind == "gantt":
        activities = spec.get("activities")
        if not isinstance(activities, list) or not activities:
            raise ChartError("a gantt chart needs a non-empty 'activities' list")
        clean = []
        for index, entry in enumerate(activities, 1):
            where = "activities[%d]" % (index - 1)
            if not isinstance(entry, dict):
                raise ChartError("%s must be an object" % where)
            label = _text(entry.get("label"), "%s label" % where)
            for key in ("start", "end"):
                if not isinstance(entry.get(key), str) or not entry[key].strip():
                    raise ChartError("%s needs a stored artifact id in %r" % (where, key))
            for key in ("float", "critical", "start_label", "end_label"):
                if entry.get(key) is not None and (not isinstance(entry[key], str) or not entry[key].strip()):
                    raise ChartError("%s %r must be a stored artifact id when supplied" % (where, key))
            identifier = entry.get("id") or label
            if not isinstance(identifier, str) or not identifier.strip():
                raise ChartError("%s id must be text when supplied" % where)
            clean.append({"id": identifier.strip(), "label": label, "start": entry["start"].strip(),
                          "end": entry["end"].strip(), "float": (entry.get("float") or "").strip() or None,
                          "critical": (entry.get("critical") or "").strip() or None,
                          "start_label": (entry.get("start_label") or "").strip() or None,
                          "end_label": (entry.get("end_label") or "").strip() or None})
        identifiers = [item["id"] for item in clean]
        if len(set(identifiers)) != len(identifiers):
            raise ChartError("gantt activity ids must be unique")
        raw_dependencies = spec.get("dependencies") or []
        if not isinstance(raw_dependencies, list):
            raise ChartError("gantt dependencies must be a list")
        dependencies = []
        for index, dep in enumerate(raw_dependencies, 1):
            if not isinstance(dep, dict):
                raise ChartError("dependencies[%d] must be an object" % (index - 1))
            source, target = dep.get("from"), dep.get("to")
            if source not in identifiers or target not in identifiers:
                raise ChartError("dependencies[%d] must name two activities in this chart" % (index - 1))
            if source == target:
                raise ChartError("dependencies[%d] cannot link an activity to itself" % (index - 1))
            dependencies.append({"from": source, "to": target})
        return kind, title, {"activities": clean, "dependencies": dependencies}
    if kind == "network":
        nodes = spec.get("nodes")
        if not isinstance(nodes, list) or not nodes:
            raise ChartError("a network chart needs a non-empty 'nodes' list")
        clean = []
        for index, entry in enumerate(nodes):
            where = "nodes[%d]" % index
            if not isinstance(entry, dict):
                raise ChartError("%s must be an object" % where)
            identifier = entry.get("id")
            if not isinstance(identifier, str) or not identifier.strip():
                raise ChartError("%s needs an 'id'" % where)
            label = _text(entry.get("label"), "%s label" % where)
            clean.append({"id": identifier.strip(), "label": label})
        identifiers = [item["id"] for item in clean]
        if len(set(identifiers)) != len(identifiers):
            raise ChartError("network node ids must be unique")
        raw_edges = spec.get("edges") or []
        if not isinstance(raw_edges, list):
            raise ChartError("network edges must be a list")
        edges = []
        for index, edge in enumerate(raw_edges, 1):
            if not isinstance(edge, dict):
                raise ChartError("edges[%d] must be an object" % (index - 1))
            source, target = edge.get("from"), edge.get("to")
            if source not in identifiers or target not in identifiers:
                raise ChartError("edges[%d] must name two nodes in this chart" % (index - 1))
            if source == target:
                raise ChartError("edges[%d] cannot link a node to itself" % (index - 1))
            edges.append({"from": source, "to": target})
        return kind, title, {"nodes": clean, "edges": edges}
    series = spec.get("series")
    if kind != "table":
        if not isinstance(series, list) or not series:
            raise ChartError("a %s chart needs a non-empty 'series' list" % kind)
        for entry in series:
            if not isinstance(entry, dict):
                raise ChartError("each series entry must be an object")
            source = entry.get("label_artifact")
            if source is not None:
                # A label that carries a digit (a sprint number, a year) is allowed
                # only when it is the recorded value of an artifact, and the render
                # then checks the two agree.  A typed number is still refused.
                if not isinstance(source, str) or not source.strip():
                    raise ChartError("'label_artifact' must be a stored artifact id")
                if not isinstance(entry.get("label"), str) or not entry["label"].strip():
                    raise ChartError("each series entry needs a 'label'")
            else:
                _text(entry.get("label"), "series label")
            if entry.get("group") is not None:
                _text(entry["group"], "series group")
            if not isinstance(entry.get("artifact"), str) or not entry["artifact"].strip():
                raise ChartError("each series entry needs an 'artifact' id or metric")
        if kind == "scatter":
            for entry in series:
                if not isinstance(entry.get("x_artifact"), str) or not entry["x_artifact"].strip():
                    raise ChartError("a scatter series entry needs an 'x_artifact' id")
        if kind == "candlestick":
            for entry in series:
                for key in ("open", "high", "low", "close"):
                    if not isinstance(entry.get(key), str) or not entry[key].strip():
                        raise ChartError("a candlestick series entry needs a stored %r id" % key)
    return kind, title, series or []


def verify_labels(spec, rows):
    """A label that carries a digit must equal the recorded value it names."""
    for entry in spec.get("series") or []:
        source = entry.get("label_artifact")
        if not source:
            continue
        row = _row_for(rows, source.strip())
        stored = str(row.get("value"))
        numbers = re.findall(r"\d+(?:\.\d+)?", str(entry.get("label")))
        if stored != str(entry.get("label")) and stored not in numbers:
            raise ChartError("the label %r does not carry the recorded value %r of %r"
                             % (entry.get("label"), stored, source))


def _series_values(spec, rows):
    series = []
    for entry in spec["series"]:
        row = _row_for(rows, entry["artifact"].strip())
        item = {"label": entry["label"].strip(), "value": _number(row, entry["artifact"].strip()),
                "stored": str(row.get("value")), "unit": row.get("unit"),
                "group": str(entry.get("group") or "").strip()}
        if entry.get("x_artifact"):
            x_row = _row_for(rows, entry["x_artifact"].strip())
            item["x"] = _number(x_row, entry["x_artifact"].strip())
            item["x_stored"] = str(x_row.get("value"))
        for key in ("open", "high", "low", "close"):
            if entry.get(key):
                source_row = _row_for(rows, entry[key].strip())
                item[key] = _number(source_row, entry[key].strip())
                item[key + "_stored"] = str(source_row.get("value"))
        source = entry.get("cumulative")
        if isinstance(source, str) and source.strip():
            running = _row_for(rows, source.strip())
            item["cumulative"] = _number(running, source.strip())
            item["cumulative_stored"] = str(running.get("value"))
        series.append(item)
    return series


def series_of(bundle, spec):
    """The resolved series a chart draws, for a writer that needs the values themselves.

    The workbook's native chart and the Plotly trace both read this, so the picture
    and the numbers beside it come from one resolution of the record.
    """
    kind, _title, _payload = validate_spec(spec)
    if kind in ("table", "gantt", "network"):
        return []
    rows = _stored_rows(bundle)
    verify_labels(spec, rows)
    return _series_values(spec, rows)


def _svg_open(title):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s">' % (WIDTH, HEIGHT, WIDTH, HEIGHT, html.escape(title, quote=True)))


def _footer_text():
    return ("Values shown are the stored strings recorded in this case; the drawing only scales them into the frame.")


def _frame(title, body):
    return (_svg_open(title) + '<rect width="100%" height="100%" fill="#fdfdfb"/>' +
            '<text x="24" y="34" font-family="Georgia, \'Times New Roman\', serif" font-size="18" fill="#1b1b1b">'
            + html.escape(title, quote=False) + "</text>" + body +
            '<text x="24" y="%d" font-family="Georgia, serif" font-size="11" fill="#6b6b6b">%s</text>'
            % (HEIGHT - 14, _footer_text()) + "</svg>")


def _fmt(value):
    return "%.2f" % float(value)


def _bar(series, title):
    body, top = [], 64
    slot = (HEIGHT - top - 40) / max(1, len(series))
    longest = max(abs(item["value"]) for item in series) or Decimal(1)
    for index, item in enumerate(series):
        y = top + slot * index + slot * 0.2
        width = abs(item["value"]) / longest * (WIDTH - 300)
        colour = PALETTE[index % len(PALETTE)]
        body.append('<text x="24" y="%s" font-family="Georgia, serif" font-size="13" fill="#1b1b1b">%s</text>'
                    % (_fmt(y + slot * 0.35), html.escape(item["label"], quote=False)))
        body.append('<rect x="220" y="%s" width="%s" height="%s" fill="%s" rx="2"/>'
                    % (_fmt(y), _fmt(width), _fmt(slot * 0.5), colour))
        body.append('<text x="%s" y="%s" font-family="Consolas, monospace" font-size="12" fill="#1b1b1b">%s</text>'
                    % (_fmt(220 + width + 10), _fmt(y + slot * 0.35), html.escape(item["stored"], quote=False)))
    return _frame(title, "".join(body))


def _line_multi(series, groups, title):
    """One line per group, on one scale, with a legend: a burndown or a control chart."""
    top, bottom, left, right = 64, HEIGHT - 60, 40, WIDTH - 40
    values = [item["value"] for item in series]
    low, high = min(values), max(values)
    span = (high - low) or Decimal(1)
    longest = max(len([item for item in series if item["group"] == group]) for group in groups)
    body = []
    for index, group in enumerate(groups):
        members = [item for item in series if item["group"] == group]
        colour = PALETTE[index % len(PALETTE)]
        points = []
        for position, item in enumerate(members):
            x = Decimal(left) + Decimal(right - left) * Decimal(position) / Decimal(max(1, longest - 1))
            y = Decimal(bottom) - Decimal(bottom - top) * (item["value"] - low) / span
            points.append((x, y, item))
        body.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>'
                    % (colour, " ".join("%s,%s" % (_fmt(x), _fmt(y)) for x, y, _ in points)))
        for x, y, item in points:
            body.append('<circle cx="%s" cy="%s" r="3.5" fill="%s"/>' % (_fmt(x), _fmt(y), colour))
        legend_x = WIDTH - 24 - (len(groups) - index) * 118
        body.append('<rect x="%d" y="22" width="10" height="10" fill="%s"/>' % (legend_x, colour))
        body.append('<text x="%d" y="31" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s</text>'
                    % (legend_x + 14, html.escape(group)))
    first = [item for item in series if item["group"] == groups[0]]
    for position, item in enumerate(first):
        x = Decimal(left) + Decimal(right - left) * Decimal(position) / Decimal(max(1, longest - 1))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="11" '
                    'fill="#555550">%s</text>' % (_fmt(x), _fmt(bottom + 22), html.escape(item["label"])))
    return _frame(title, "".join(body))


def _line(series, title, sparkline=False):
    if len(series) < 2:
        raise ChartError("a line chart needs at least two series points")
    groups = []
    for item in series:
        if item["group"] and item["group"] not in groups:
            groups.append(item["group"])
    if len(groups) > 1 and not sparkline:
        return _line_multi(series, groups, title)
    top, bottom, left, right = (20, HEIGHT - 46, 24, WIDTH - 24) if sparkline else (64, HEIGHT - 60, 40, WIDTH - 40)
    values = [item["value"] for item in series]
    low, high = min(values), max(values)
    span = (high - low) or Decimal(1)
    points = []
    for index, item in enumerate(series):
        x = Decimal(left) + Decimal(right - left) * Decimal(index) / Decimal(len(series) - 1)
        y = Decimal(bottom) - Decimal(bottom - top) * (item["value"] - low) / span
        points.append((x, y, item))
    body = ['<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>'
            % (PALETTE[0], " ".join("%s,%s" % (_fmt(x), _fmt(y)) for x, y, _ in points))]
    for x, y, item in points:
        if sparkline:
            body.append('<circle cx="%s" cy="%s" r="3" fill="%s"/>' % (_fmt(x), _fmt(y), PALETTE[0]))
        else:
            body.append('<circle cx="%s" cy="%s" r="4" fill="%s"/>' % (_fmt(x), _fmt(y), PALETTE[0]))
            body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="12" fill="#1b1b1b">%s</text>'
                        % (_fmt(x), _fmt(y - 12), html.escape(item["stored"], quote=False)))
            body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="11" fill="#555550">%s</text>'
                        % (_fmt(x), _fmt(bottom + 22), html.escape(item["label"], quote=False)))
    return _frame(title, "".join(body))


def _stacked(series, title):
    body, top = [], 84
    total = sum(abs(item["value"]) for item in series) or Decimal(1)
    x = Decimal(24)
    for index, item in enumerate(series):
        width = abs(item["value"]) / total * (WIDTH - 60)
        colour = PALETTE[index % len(PALETTE)]
        body.append('<rect x="%s" y="%s" width="%s" height="70" fill="%s"/>' % (_fmt(x), _fmt(top), _fmt(width), colour))
        body.append('<text x="%s" y="%s" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s</text>'
                    % (_fmt(x + 6), _fmt(top + 24), html.escape(item["label"], quote=False)))
        body.append('<text x="%s" y="%s" font-family="Consolas, monospace" font-size="11" fill="#1b1b1b">%s</text>'
                    % (_fmt(x + 6), _fmt(top + 44), html.escape(item["stored"], quote=False)))
        x += width
    return _frame(title, "".join(body))


def _waterfall(series, title):
    body, top = [], 70
    running = 0.0
    levels = [0.0]
    for item in series:
        running += float(item["value"])
        levels.append(running)
    low, high = min(levels), max(levels)
    span = (high - low) or 1.0
    slot = (WIDTH - 80) / max(1, len(series))
    def y_of(value):
        return top + (HEIGHT - top - 60) * (high - value) / span
    for index, item in enumerate(series):
        before = levels[index]
        after = levels[index + 1]
        x = 40.0 + slot * index
        top_y = min(y_of(before), y_of(after))
        height = abs(y_of(before) - y_of(after)) or 4.0
        colour = PALETTE[index % len(PALETTE)]
        body.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" rx="2"/>'
                    % (_fmt(x), _fmt(top_y), _fmt(slot * 0.6), _fmt(height), colour))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s</text>'
                    % (_fmt(x + slot * 0.3), _fmt(top_y - 8), html.escape(item["stored"], quote=False)))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="10" fill="#555550">%s</text>'
                    % (_fmt(x + slot * 0.3), _fmt(HEIGHT - 40), html.escape(item["label"], quote=False)))
    return _frame(title, "".join(body))


def _pie(series, title):
    body = []
    total = sum(abs(item["value"]) for item in series) or Decimal(1)
    start = -90.0
    centre = (WIDTH / 2.0, HEIGHT / 2.0 + 8)
    radius = 96.0
    for index, item in enumerate(series):
        fraction = float(abs(item["value"]) / total)
        angle = fraction * 360.0
        end = start + angle
        large = 1 if angle > 180 else 0
        def point(degrees, r=radius):
            import math
            radians = math.radians(degrees)
            return centre[0] + r * math.cos(radians), centre[1] + r * math.sin(radians)
        x1, y1 = point(start)
        x2, y2 = point(end)
        body.append('<path d="M%s,%s L%s,%s A%s,%s 0 %d 1 %s,%s Z" fill="%s" stroke="#fdfdfb" stroke-width="2"/>'
                    % (_fmt(centre[0]), _fmt(centre[1]), _fmt(x1), _fmt(y1), _fmt(radius), _fmt(radius), large,
                       _fmt(x2), _fmt(y2), PALETTE[index % len(PALETTE)]))
        mid_x, mid_y = point(start + angle / 2.0, radius + 18)
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s: %s</text>'
                    % (_fmt(mid_x), _fmt(mid_y), html.escape(item["label"], quote=False), html.escape(item["stored"], quote=False)))
        start = end
    return _frame(title, "".join(body))


def _gantt(payload, rows, title):
    """Bars from stored early dates, with the critical path, float and declared dependencies."""
    activities = payload["activities"]
    resolved = []
    for entry in activities:
        start_row = _row_for(rows, entry["start"])
        end_row = _row_for(rows, entry["end"])
        start = _number(start_row, entry["start"])
        end = _number(end_row, entry["end"])
        if start < 0 or end < start:
            raise ChartError("activity %r has an early finish before its early start" % entry["label"])
        float_value = _number(_row_for(rows, entry["float"]), entry["float"]) if entry["float"] else Decimal(0)
        critical = _number(_row_for(rows, entry["critical"]), entry["critical"]) if entry["critical"] else Decimal(0)
        start_text = str(start_row.get("value"))
        end_text = str(end_row.get("value"))
        if entry.get("start_label"):
            start_text = str(_row_for(rows, entry["start_label"]).get("value"))
        if entry.get("end_label"):
            end_text = str(_row_for(rows, entry["end_label"]).get("value"))
        resolved.append({"id": entry["id"], "label": entry["label"], "start": start, "end": end,
                         "float": float_value, "critical": critical != 0,
                         "start_stored": start_text, "end_stored": end_text})
    horizon = max(item["end"] + item["float"] for item in resolved) or Decimal(1)
    left, right, top, bottom = 250, WIDTH - 40, 76, HEIGHT - 58
    row_height = (bottom - top) / max(1, len(resolved))
    scale = float((right - left) / horizon) if horizon else 1.0
    body = []
    step = max(1, int(float(horizon) / 8) + 1)
    body.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#c9c9c4"/>' % (left, top, left, bottom))
    for tick in range(0, int(horizon) + 1, step):
        x = left + tick * scale
        body.append('<line x1="%s" y1="%d" x2="%s" y2="%d" stroke="#e6e6e1"/>'
                    % (_fmt(x), top, _fmt(x), bottom))
        body.append('<text x="%s" y="%d" text-anchor="middle" font-family="Consolas, monospace" font-size="11" '
                    'fill="#555550">%d</text>' % (_fmt(x), bottom + 18, tick))
    for index, item in enumerate(resolved):
        y = top + row_height * index + row_height * 0.18
        height = row_height * 0.52
        body.append('<text x="24" y="%s" font-family="Georgia, serif" font-size="13" fill="#1b1b1b">%s</text>'
                    % (_fmt(y + height * 0.7), html.escape(item["label"], quote=False)))
        body.append('<text x="24" y="%s" font-family="Consolas, monospace" font-size="11" fill="#555550">%s</text>'
                    % (_fmt(y + height * 0.7 + 13),
                       html.escape("%s to %s" % (item["start_stored"], item["end_stored"]), quote=False)))
        x = left + float(item["start"]) * scale
        width = max(2.0, float(item["end"] - item["start"]) * scale)
        colour = "#e15759" if item["critical"] else PALETTE[index % len(PALETTE)]
        body.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" rx="2"/>'
                    % (_fmt(x), _fmt(y), _fmt(width), _fmt(height), colour))
        if item["float"]:
            end_x = x + width
            float_x = end_x + float(item["float"]) * scale
            mid = y + height / 2.0
            body.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#7a7a75" stroke-width="2"/>'
                        % (_fmt(end_x), _fmt(mid), _fmt(float_x), _fmt(mid)))
            body.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#7a7a75" stroke-width="2"/>'
                        % (_fmt(float_x), _fmt(mid - 5), _fmt(float_x), _fmt(mid + 5)))
    positions = {}
    for index, item in enumerate(resolved):
        y = top + row_height * index + row_height * 0.18
        height = row_height * 0.52
        x = left + float(item["start"]) * scale
        width = max(2.0, float(item["end"] - item["start"]) * scale)
        positions[item["id"]] = {"start": x, "end": x + width, "mid": y + height / 2.0}
    for dependency in payload["dependencies"]:
        source, target = positions[dependency["from"]], positions[dependency["to"]]
        bend = max(source["end"] + 8, target["start"] - 10)
        body.append('<polyline points="%s,%s %s,%s %s,%s %s,%s" fill="none" stroke="#7a7a75" '
                    'stroke-width="1.5"/>'
                    % (_fmt(source["end"]), _fmt(source["mid"]), _fmt(bend), _fmt(source["mid"]),
                       _fmt(bend), _fmt(target["mid"]), _fmt(target["start"] - 6), _fmt(target["mid"])))
        body.append('<path d="M%s,%s L%s,%s L%s,%s Z" fill="#7a7a75"/>'
                    % (_fmt(target["start"]), _fmt(target["mid"]),
                       _fmt(target["start"] - 6), _fmt(target["mid"] - 4),
                       _fmt(target["start"] - 6), _fmt(target["mid"] + 4)))
    body.append('<text x="24" y="%d" font-family="Georgia, serif" font-size="11" fill="#555550">'
                'Bars are the stored early dates; red marks the critical path, the thin line is float and '
                'arrows are the declared dependencies.</text>'
                % (HEIGHT - 34))
    return _frame(title, "".join(body))


def _network(payload, title):
    """An activity-on-node network: boxes in dependency layers, arrows for edges."""
    nodes, edges = payload["nodes"], payload["edges"]
    layer = {node["id"]: 0 for node in nodes}
    for _ in range(len(nodes)):
        changed = False
        for edge in edges:
            if layer[edge["to"]] < layer[edge["from"]] + 1:
                layer[edge["to"]] = layer[edge["from"]] + 1
                changed = True
        if not changed:
            break
    columns = {}
    for node in nodes:
        columns.setdefault(layer[node["id"]], []).append(node)
    deepest = max(columns) if columns else 0
    positions = {}
    for place, members in columns.items():
        x = 40 + Decimal(WIDTH - 200) * Decimal(place) / Decimal(max(1, deepest))
        for index, node in enumerate(members):
            y = Decimal(70) + Decimal(HEIGHT - 150) * Decimal(index + 0.5) / Decimal(len(members))
            positions[node["id"]] = (x, y)
    body = ['<defs><marker id="network-arrow" markerWidth="8" markerHeight="8" '
            'refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 z" fill="#7c828b"/></marker></defs>']
    for edge in edges:
        x1, y1 = positions[edge["from"]]
        x2, y2 = positions[edge["to"]]
        body.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="#7c828b" stroke-width="1.5" '
                    'marker-end="url(#network-arrow)"/>'
                    % (_fmt(x1 + 62), _fmt(y1), _fmt(x2 - 62), _fmt(y2)))
    for node in nodes:
        x, y = positions[node["id"]]
        body.append('<rect x="%s" y="%s" width="124" height="34" rx="4" fill="#f1f4f8" '
                    'stroke="#4a5568"/>' % (_fmt(x - 62), _fmt(y - 17)))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" '
                    'font-size="11" fill="#1b1b1b">%s</text>'
                    % (_fmt(x), _fmt(y + 4), html.escape(node["label"], quote=False)))
    return _frame(title, "".join(body))


def _pareto(series, title, spec):
    """Bars in the order given, and the stored running total on its own scale.

    The bars are scaled to the tallest stored value and the line to the largest
    stored running total; neither is computed from the other.  Every figure a
    reader sees - above a bar or beside a point - is the stored string.
    """
    values = [item["value"] for item in series]
    if any(value < 0 for value in values):
        raise ChartError("a pareto chart draws positive bars; a fall belongs in a waterfall")
    previous = None
    running = []
    for item in series:
        value = item.get("cumulative")
        if value is None:
            raise ChartError("series entry %r needs a stored 'cumulative' artifact" % item["label"])
        if previous is not None and value < previous:
            raise ChartError("the running total falls at %r, so it is not a running total" % item["label"])
        previous = value
        running.append(value)
    tallest = max(values) or Decimal(1)
    highest = max(running) or Decimal(1)
    top, bottom, left, right = 92, HEIGHT - 66, 44, WIDTH - 44
    slot = (right - left) / float(max(1, len(series)))
    width = slot * 0.56
    body = []
    points = []
    for index, item in enumerate(series):
        x = left + slot * index + (slot - width) / 2.0
        height = float(item["value"] / tallest) * (bottom - top)
        y = bottom - height
        body.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" rx="2"/>'
                    % (_fmt(x), _fmt(y), _fmt(width), _fmt(max(height, 1.0)), PALETTE[0]))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Consolas, monospace" '
                    'font-size="11" fill="#1b1b1b">%s</text>'
                    % (_fmt(x + width / 2.0), _fmt(max(y - 8, top - 4)),
                       html.escape(item["stored"], quote=False)))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" '
                    'font-size="10" fill="#555550">%s</text>'
                    % (_fmt(x + width / 2.0), _fmt(bottom + 18),
                       html.escape(item["label"], quote=False)))
        point_y = bottom - float(item["cumulative"] / highest) * (bottom - top)
        points.append((x + width / 2.0, point_y, item))
    body.append('<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>'
                % (PALETTE[1], " ".join("%s,%s" % (_fmt(px), _fmt(py)) for px, py, _ in points)))
    for px, py, item in points:
        body.append('<circle cx="%s" cy="%s" r="3.5" fill="%s"/>' % (_fmt(px), _fmt(py), PALETTE[1]))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Consolas, monospace" '
                    'font-size="10" fill="%s">%s</text>'
                    % (_fmt(px), _fmt(max(py - 10, top - 4)), PALETTE[1],
                       html.escape(item.get("cumulative_stored") or "", quote=False)))
    body.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#c9c9c4"/>'
                % (left, bottom, right, bottom))
    body.append('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#c9c9c4"/>'
                % (left, top, left, bottom))
    bars_label = str(spec.get("y_label") or "Recorded value")
    line_label = str(spec.get("y2_label") or "Running total")
    body.append('<rect x="%d" y="22" width="10" height="10" fill="%s"/>' % (WIDTH - 268, PALETTE[0]))
    body.append('<text x="%d" y="31" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s</text>'
                % (WIDTH - 254, html.escape(bars_label, quote=False)))
    body.append('<line x1="%d" y1="27" x2="%d" y2="27" stroke="%s" stroke-width="3"/>'
                % (WIDTH - 150, WIDTH - 138, PALETTE[1]))
    body.append('<text x="%d" y="31" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s</text>'
                % (WIDTH - 132, html.escape(line_label, quote=False)))
    body.append('<text x="24" y="%d" font-family="Georgia, serif" font-size="11" fill="#555550">'
                'Bars are the stored values; the line is the stored running total on its own '
                'scale.</text>' % (HEIGHT - 34))
    return _frame(title, "".join(body))


def _table(rows, title):
    body, y = [], 62
    header = ("Artifact", "Metric", "Unit", "Value", "Derivation")
    column_x = (24, 160, 300, 380, 500)
    for text, x in zip(header, column_x):
        body.append('<text x="%s" y="%s" font-family="Georgia, serif" font-size="12" font-weight="bold" fill="#1b1b1b">%s</text>'
                    % (x, y, text))
    for row in rows[:12]:
        y += 20
        cells = (row.get("id"), row.get("metric"), row.get("unit"), row.get("value"), row.get("derivation"))
        for text, x in zip(cells, column_x):
            shown = "not recorded" if text is None else str(text)
            body.append('<text x="%s" y="%s" font-family="Georgia, serif" font-size="11" fill="#1b1b1b">%s</text>'
                        % (x, y, html.escape(shown, quote=False)))
    return _frame(title, "".join(body))


def _area(series, title):
    """A filled line: the same stored values as a line, drawn as a trend area."""
    if len(series) < 2:
        raise ChartError("an area chart needs at least two series points")
    top, bottom, left, right = 64, HEIGHT - 60, 40, WIDTH - 40
    values = [item["value"] for item in series]
    low, high = min(values), max(values)
    span = (high - low) or Decimal(1)
    points = []
    for index, item in enumerate(series):
        x = Decimal(left) + Decimal(right - left) * Decimal(index) / Decimal(len(series) - 1)
        y = Decimal(bottom) - Decimal(bottom - top) * (item["value"] - low) / span
        points.append((x, y, item))
    polygon = " ".join("%s,%s" % (_fmt(x), _fmt(y)) for x, y, _ in points)
    body = ['<polygon fill="%s" fill-opacity="0.18" stroke="none" points="%s %s,%s %s,%s"/>'
            % (PALETTE[0], polygon, _fmt(right), _fmt(bottom), _fmt(left), _fmt(bottom)),
            '<polyline fill="none" stroke="%s" stroke-width="2" points="%s"/>' % (PALETTE[0], polygon)]
    for x, y, item in points:
        body.append('<circle cx="%s" cy="%s" r="4" fill="%s"/>' % (_fmt(x), _fmt(y), PALETTE[0]))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="12" fill="#1b1b1b">%s</text>'
                    % (_fmt(x), _fmt(y - 12), html.escape(item["stored"], quote=False)))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="11" fill="#555550">%s</text>'
                    % (_fmt(x), _fmt(bottom + 22), html.escape(item["label"], quote=False)))
    return _frame(title, "".join(body))


def _scatter(series, title):
    """Points from two stored values per entry: x against y."""
    if len(series) < 2:
        raise ChartError("a scatter plot needs at least two points")
    if any("x" not in item for item in series):
        raise ChartError("a scatter plot needs an x value for every point")
    top, bottom, left, right = 64, HEIGHT - 60, 56, WIDTH - 40
    xs = [item["x"] for item in series]
    ys = [item["value"] for item in series]
    x_low, x_high = min(xs), max(xs)
    y_low, y_high = min(ys), max(ys)
    x_span = (x_high - x_low) or Decimal(1)
    y_span = (y_high - y_low) or Decimal(1)
    body = ['<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#c9c9c4"/>' % (left, top, left, bottom),
            '<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="#c9c9c4"/>' % (left, bottom, right, bottom)]
    for item in series:
        x = Decimal(left) + Decimal(right - left) * (item["x"] - x_low) / x_span
        y = Decimal(bottom) - Decimal(bottom - top) * (item["value"] - y_low) / y_span
        body.append('<circle cx="%s" cy="%s" r="4.5" fill="%s"/>' % (_fmt(x), _fmt(y), PALETTE[0]))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="10" fill="#555550">%s</text>'
                    % (_fmt(x), _fmt(y - 10), html.escape(item["label"], quote=False)))
    body.append('<text x="%d" y="%d" font-family="Georgia, serif" font-size="11" fill="#555550">x: %s to %s</text>'
                % (left, HEIGHT - 28, html.escape(str(x_low)), html.escape(str(x_high))))
    return _frame(title, "".join(body))


def _candlestick(series, title):
    """One candle per period from stored open, high, low and close values."""
    if len(series) < 1:
        raise ChartError("a candlestick chart needs at least one period")
    for item in series:
        for key in ("open", "high", "low", "close"):
            if key not in item:
                raise ChartError("a candlestick chart needs %r for every period" % key)
        if item["high"] < item["low"]:
            raise ChartError("period %r has a high below its low" % item["label"])
        if item["high"] < max(item["open"], item["close"]) or item["low"] > min(item["open"], item["close"]):
            raise ChartError("period %r has an open or close outside its high-low range" % item["label"])
    top, bottom, left, right = 64, HEIGHT - 60, 48, WIDTH - 40
    highs = [item["high"] for item in series]
    lows = [item["low"] for item in series]
    high, low = max(highs), min(lows)
    span = (high - low) or Decimal(1)
    slot = Decimal(right - left) / Decimal(max(1, len(series)))
    width = slot * Decimal("0.45")
    body = []
    for index, item in enumerate(series):
        centre = Decimal(left) + slot * (index + Decimal("0.5"))
        y_high = Decimal(bottom) - Decimal(bottom - top) * (item["high"] - low) / span
        y_low = Decimal(bottom) - Decimal(bottom - top) * (item["low"] - low) / span
        y_open = Decimal(bottom) - Decimal(bottom - top) * (item["open"] - low) / span
        y_close = Decimal(bottom) - Decimal(bottom - top) * (item["close"] - low) / span
        colour = "#2e7d32" if item["close"] >= item["open"] else "#c62828"
        body.append('<line x1="%s" y1="%s" x2="%s" y2="%s" stroke="%s" stroke-width="1.5"/>'
                    % (_fmt(centre), _fmt(y_high), _fmt(centre), _fmt(y_low), colour))
        body.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s"/>'
                    % (_fmt(centre - width / 2), _fmt(min(y_open, y_close)), _fmt(width),
                       _fmt(abs(y_close - y_open) or 2), colour))
        body.append('<text x="%s" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="10" fill="#555550">%s</text>'
                    % (_fmt(centre), _fmt(bottom + 22), html.escape(item["label"], quote=False)))
    return _frame(title, "".join(body))


def render_svg(bundle, spec):
    """Draw one chart as deterministic SVG. Returns the SVG string."""
    kind, title, payload = validate_spec(spec)
    rows = _stored_rows(bundle)
    verify_labels(spec, rows)
    if kind == "table":
        return _table(rows, title)
    if kind == "gantt":
        return _gantt(payload, rows, title)
    if kind == "network":
        return _network(payload, title)
    series = _series_values(spec, rows)
    if kind == "bar":
        return _bar(series, title)
    if kind == "line":
        return _line(series, title)
    if kind == "area":
        return _area(series, title)
    if kind == "scatter":
        return _scatter(series, title)
    if kind == "candlestick":
        return _candlestick(series, title)
    if kind == "stacked_bar":
        return _stacked(series, title)
    if kind == "waterfall":
        return _waterfall(series, title)
    if kind == "pie":
        return _pie(series, title)
    if kind == "pareto":
        return _pareto(series, title, spec)
    return _line(series, title, sparkline=True)
