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

Kinds: bar, line, stacked_bar, waterfall, pie, sparkline, table.
"""

import html
import re
from decimal import Decimal, InvalidOperation

from . import export as case_export

FORMAT = "bp-chart/1"
KINDS = ("bar", "line", "stacked_bar", "waterfall", "pie", "sparkline", "table")
WIDTH, HEIGHT = 720, 300
PALETTE = ("#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948", "#b07aa1", "#9c755f")
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
    series = spec.get("series")
    if kind != "table":
        if not isinstance(series, list) or not series:
            raise ChartError("a %s chart needs a non-empty 'series' list" % kind)
        for entry in series:
            if not isinstance(entry, dict):
                raise ChartError("each series entry must be an object")
            _text(entry.get("label"), "series label")
            if not isinstance(entry.get("artifact"), str) or not entry["artifact"].strip():
                raise ChartError("each series entry needs an 'artifact' id or metric")
    return kind, title, series or []


def _series_values(spec, rows):
    series = []
    for entry in spec["series"]:
        row = _row_for(rows, entry["artifact"].strip())
        series.append({"label": entry["label"].strip(), "value": _number(row, entry["artifact"].strip()),
                       "stored": str(row.get("value")), "unit": row.get("unit")})
    return series


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


def _line(series, title, sparkline=False):
    if len(series) < 2:
        raise ChartError("a line chart needs at least two series points")
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


def render_svg(bundle, spec):
    """Draw one chart as deterministic SVG. Returns the SVG string."""
    kind, title, _ = validate_spec(spec)
    rows = _stored_rows(bundle)
    if kind == "table":
        return _table(rows, title)
    series = _series_values(spec, rows)
    if kind == "bar":
        return _bar(series, title)
    if kind == "line":
        return _line(series, title)
    if kind == "stacked_bar":
        return _stacked(series, title)
    if kind == "waterfall":
        return _waterfall(series, title)
    if kind == "pie":
        return _pie(series, title)
    return _line(series, title, sparkline=True)
