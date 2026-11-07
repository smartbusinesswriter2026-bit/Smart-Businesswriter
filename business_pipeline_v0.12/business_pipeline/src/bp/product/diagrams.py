"""Business diagram templates as deterministic SVG (product layer, standard library only).

Diagrams organise **the owner's words** - they are structure-only (T4): no
number, score or ranking is drawn or computed.  Text fields may not contain
digits, so a diagram cannot smuggle a figure into what is otherwise a picture
of labels.

Kinds:

* process - an ordered sequence of steps;
* matrix2x2 - four quadrants (top-left, top-right, bottom-left, bottom-right)
  with optional axis labels;
* pyramid - items from the apex down;
* funnel - items from the widest to the narrowest;
* tree - one root label with child labels.

Every render is deterministic for the same spec (fixed frame, fixed order).
"""

import html
import os
import re
import tempfile
from pathlib import Path

from . import theme

FORMAT = "bp-diagram/1"
KINDS = ("process", "matrix2x2", "pyramid", "funnel", "tree", "board", "journey", "kpi")
WIDTH, HEIGHT = 720, 420
#: The diagram palette is the chart palette, defined once in `theme`.
PALETTE = theme.SERIES[:6]
_DIGIT = re.compile(r"\d")


class DiagramError(ValueError):
    """The diagram spec cannot be drawn as declared."""


def _text(value, what):
    if not isinstance(value, str) or not value.strip():
        raise DiagramError("%s must be non-empty text" % what)
    if _DIGIT.search(value):
        raise DiagramError("%s may not contain digits: diagrams carry labels, not numbers (%r)" % (what, value))
    return value.strip()


def validate_spec(spec):
    """Check a diagram spec against its own rules."""
    if not isinstance(spec, dict):
        raise DiagramError("diagram spec must be an object")
    if spec.get("format", FORMAT) != FORMAT:
        raise DiagramError("unsupported diagram format %r, expected %r" % (spec.get("format"), FORMAT))
    kind = spec.get("kind")
    if kind not in KINDS:
        raise DiagramError("kind must be one of: " + ", ".join(KINDS))
    title = _text(spec.get("title"), "diagram title")
    if kind == "matrix2x2":
        quadrants = spec.get("quadrants")
        if not isinstance(quadrants, dict):
            raise DiagramError("a matrix2x2 diagram needs a 'quadrants' object")
        for key in ("top_left", "top_right", "bottom_left", "bottom_right"):
            _text(quadrants.get(key), "quadrant %r" % key)
        for key in ("x_axis", "y_axis"):
            if spec.get(key) is not None:
                _text(spec[key], "axis label")
        return kind, title, []
    if kind == "tree":
        _text(spec.get("root"), "tree root label")
        children = spec.get("children")
        if not isinstance(children, list) or not children:
            raise DiagramError("a tree diagram needs a non-empty 'children' list")
        labels = [_text(entry.get("label") if isinstance(entry, dict) else None, "child label") for entry in children]
        return kind, title, labels
    if kind == "kpi":
        items = spec.get("items")
        if not isinstance(items, list) or not items:
            raise DiagramError("a KPI board needs at least one item")
        clean = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                raise DiagramError("items[%d] must be an object" % index)
            label = _text(item.get("label"), "KPI label")
            value = item.get("value")
            if not isinstance(value, str) or not value.strip():
                raise DiagramError("KPI %r needs a stored artifact id in 'value'" % label)
            entry = {"label": label, "value": value.strip()}
            for key in ("target", "status"):
                if item.get(key) is not None:
                    if not isinstance(item[key], str) or not item[key].strip():
                        raise DiagramError("KPI %r %r must be a stored artifact id" % (label, key))
                    entry[key] = item[key].strip()
            clean.append(entry)
        return kind, title, clean

    if kind == "journey":
        stages = spec.get("stages")
        if not isinstance(stages, list) or len(stages) < 2:
            raise DiagramError("a journey needs at least two stages")
        clean_stages = [_text(stage.get("label") if isinstance(stage, dict) else None,
                              "stage %d label" % (index + 1))
                        for index, stage in enumerate(stages)]
        lanes = spec.get("lanes")
        if not isinstance(lanes, list) or not lanes:
            raise DiagramError("a journey needs at least one lane")
        clean_lanes = []
        for index, lane in enumerate(lanes):
            if not isinstance(lane, dict):
                raise DiagramError("lanes[%d] must be an object" % index)
            label = _text(lane.get("label"), "lane %d label" % (index + 1))
            cells = lane.get("cells") or []
            if not isinstance(cells, list):
                raise DiagramError("lanes[%d] cells must be a list" % index)
            if len(cells) > len(clean_stages):
                raise DiagramError("lanes[%d] has more cells than stages" % index)
            clean_cells = []
            for cell in cells:
                text = cell.get("label") if isinstance(cell, dict) else cell
                clean_cells.append(_text(text, "lane %d cell" % (index + 1)) if text else "")
            clean_lanes.append({"label": label, "cells": clean_cells})
        return kind, title, {"stages": clean_stages, "lanes": clean_lanes}

    if kind == "board":
        columns = spec.get("columns")
        if not isinstance(columns, list) or len(columns) < 2:
            raise DiagramError("a board needs at least two columns")
        clean_columns = []
        for index, column in enumerate(columns, 1):
            if not isinstance(column, dict):
                raise DiagramError("columns[%d] must be an object" % (index - 1))
            label = _text(column.get("label"), "column %d label" % index)
            cards = column.get("cards")
            if cards is None:
                cards = []
            if not isinstance(cards, list):
                raise DiagramError("columns[%d] cards must be a list" % (index - 1))
            clean_cards = []
            for card_index, card in enumerate(cards, 1):
                if not isinstance(card, dict):
                    raise DiagramError("columns[%d] cards[%d] must be an object"
                                       % (index - 1, card_index - 1))
                clean_cards.append({"label": _text(card.get("label"), "card label")})
            clean_columns.append({"label": label, "cards": clean_cards})
        return kind, title, clean_columns

    items = spec.get("items")
    if not isinstance(items, list) or len(items) < 2:
        raise DiagramError("a %s diagram needs at least two 'items'" % kind)
    labels = [_text(entry.get("label") if isinstance(entry, dict) else None, "item label") for entry in items]
    return kind, title, labels


def _open(title):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" '
            'aria-label="%s"><rect width="100%%" height="100%%" fill="#fdfdfb"/>'
            % (WIDTH, HEIGHT, WIDTH, HEIGHT, html.escape(title, quote=True)))


def _title(title):
    return ('<text x="24" y="34" font-family="Georgia, serif" font-size="18" fill="#1b1b1b">%s</text>'
            % html.escape(title, quote=False))


def _footer():
    return ('<text x="24" y="%d" font-family="Georgia, serif" font-size="11" fill="#6b6b6b">'
            'Structure only: these are the labels supplied for this diagram, not computed values.</text>'
            % (HEIGHT - 14))


def _close():
    return _footer() + "</svg>"


def _process(labels, title):
    body, y = [], 90
    step_height = (HEIGHT - 150) / max(1, len(labels))
    for index, label in enumerate(labels):
        top = y + step_height * index
        body.append('<rect x="120" y="%s" width="480" height="%s" fill="%s" rx="4"/>'
                    % ("%.2f" % top, "%.2f" % (step_height * 0.7), PALETTE[index % len(PALETTE)]))
        body.append('<text x="360" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="14" fill="#1b1b1b">%s</text>'
                    % ("%.2f" % (top + step_height * 0.35 + 5), html.escape(label, quote=False)))
        if index < len(labels) - 1:
            body.append('<line x1="360" y1="%s" x2="360" y2="%s" stroke="#6b6b6b" stroke-width="2"/>'
                        % ("%.2f" % (top + step_height * 0.7), "%.2f" % (top + step_height)))
    return _open(title) + _title(title) + "".join(body) + _close()


def _matrix(spec, title):
    body = []
    positions = (("top_left", 60, 70), ("top_right", 380, 70), ("bottom_left", 60, 220), ("bottom_right", 380, 220))
    for key, x, y in positions:
        body.append('<rect x="%d" y="%d" width="280" height="130" fill="none" stroke="#6b6b6b" stroke-width="2"/>' % (x, y))
        body.append('<text x="%d" y="%d" text-anchor="middle" font-family="Georgia, serif" font-size="13" fill="#1b1b1b">%s</text>'
                    % (x + 140, y + 70, html.escape(spec["quadrants"][key].strip(), quote=False)))
    if spec.get("x_axis"):
        body.append('<text x="360" y="%d" text-anchor="middle" font-family="Georgia, serif" font-size="12" fill="#555550">%s</text>'
                    % (HEIGHT - 40, html.escape(spec["x_axis"].strip(), quote=False)))
    if spec.get("y_axis"):
        body.append('<text x="24" y="%d" font-family="Georgia, serif" font-size="12" fill="#555550">%s</text>'
                    % (HEIGHT - 60, html.escape(spec["y_axis"].strip(), quote=False)))
    return _open(title) + _title(title) + "".join(body) + _close()


def _pyramid(labels, title):
    body = []
    count = len(labels)
    for index, label in enumerate(labels):
        width = 100 + (count - index - 1) * (360 / max(1, count - 1))
        height = (HEIGHT - 170) / count
        top = 80 + index * height
        body.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" rx="3"/>'
                    % ("%.2f" % (360 - width / 2), "%.2f" % top, "%.2f" % width, "%.2f" % (height * 0.85),
                       PALETTE[index % len(PALETTE)]))
        body.append('<text x="360" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="13" fill="#1b1b1b">%s</text>'
                    % ("%.2f" % (top + height * 0.45), html.escape(label, quote=False)))
    return _open(title) + _title(title) + "".join(body) + _close()


def _funnel(labels, title):
    body = []
    count = len(labels)
    for index, label in enumerate(labels):
        width = 420 - index * (280 / max(1, count - 1))
        height = (HEIGHT - 170) / count
        top = 80 + index * height
        body.append('<rect x="%s" y="%s" width="%s" height="%s" fill="%s" rx="3"/>'
                    % ("%.2f" % (360 - width / 2), "%.2f" % top, "%.2f" % width, "%.2f" % (height * 0.75),
                       PALETTE[index % len(PALETTE)]))
        body.append('<text x="360" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="13" fill="#1b1b1b">%s</text>'
                    % ("%.2f" % (top + height * 0.45), html.escape(label, quote=False)))
    return _open(title) + _title(title) + "".join(body) + _close()


def _tree(spec, labels, title):
    body = []
    root = spec["root"].strip()
    body.append('<rect x="240" y="70" width="240" height="54" fill="%s" rx="4"/>' % PALETTE[0])
    body.append('<text x="360" y="%s" text-anchor="middle" font-family="Georgia, serif" font-size="14" fill="#1b1b1b">%s</text>'
                % ("%.2f" % 101, html.escape(root, quote=False)))
    columns = len(labels)
    step = (WIDTH - 120) / max(1, columns)
    for index, label in enumerate(labels):
        x = 60 + step * index + step / 2 - 100
        body.append('<line x1="360" y1="124" x2="%s" y2="190" stroke="#6b6b6b" stroke-width="2"/>'
                    % ("%.2f" % (x + 100)))
        body.append('<rect x="%s" y="190" width="200" height="90" fill="%s" rx="4"/>'
                    % ("%.2f" % x, PALETTE[(index + 1) % len(PALETTE)]))
        body.append('<text x="%s" y="240" text-anchor="middle" font-family="Georgia, serif" font-size="13" fill="#1b1b1b">%s</text>'
                    % ("%.2f" % (x + 100), html.escape(label, quote=False)))
    return _open(title) + _title(title) + "".join(body) + _close()


def _wrap(text, width):
    """Split a label at word boundaries, so a card shows the words it was given."""
    words, lines, current = str(text).split(), [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines or [""]


def _board(columns, title):
    """Columns of cards: a sprint board, a Kanban board or a retrospective."""
    top, bottom, margin, gap = 74, HEIGHT - 40, 20, 12
    count = max(1, len(columns))
    width = (WIDTH - 2 * margin - gap * (count - 1)) / count
    body = []
    for index, column in enumerate(columns):
        x = margin + index * (width + gap)
        body.append('<rect x="%.2f" y="%d" width="%.2f" height="34" rx="6" fill="%s"/>'
                    % (x, top, width, PALETTE[0]))
        body.append('<text x="%.2f" y="%d" text-anchor="middle" font-family="Georgia, serif" '
                    'font-size="13" fill="#ffffff">%s</text>'
                    % (x + width / 2, top + 22, html.escape(column["label"])))
        y = top + 44
        for card in column.get("cards") or []:
            lines = _wrap(card["label"], max(8, int(width / 7.2)))
            height = 18 + 15 * len(lines)
            if y + height > bottom:
                break
            body.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%d" rx="4" '
                        'fill="#ffffff" stroke="#c9c9c4"/>' % (x, y, width, height))
            for line_index, line in enumerate(lines):
                body.append('<text x="%.2f" y="%.2f" text-anchor="middle" font-family="Georgia, serif" '
                            'font-size="11" fill="#1b1b1b">%s</text>'
                            % (x + width / 2, y + 18 + 14 * line_index, html.escape(line)))
            y += height + 8
    return _open(title) + _title(title) + "".join(body) + _close()


def _journey(spec, title):
    """Stages across the top, lanes down the side: a journey, a story map or a roadmap."""
    stages = spec["stages"]
    lanes = spec["lanes"]
    top, bottom, margin, lane_width = 78, HEIGHT - 40, 16, 108
    stage_width = (WIDTH - 2 * margin - lane_width) / max(1, len(stages))
    body = []
    for index, stage in enumerate(stages):
        x = margin + lane_width + index * stage_width
        body.append('<rect x="%.2f" y="%d" width="%.2f" height="30" rx="4" fill="%s"/>'
                    % (x, top, stage_width, PALETTE[0]))
        body.append('<text x="%.2f" y="%d" text-anchor="middle" font-family="Georgia, serif" '
                    'font-size="12" fill="#ffffff">%s</text>'
                    % (x + stage_width / 2, top + 20, html.escape(stage)))
    rows_top = top + 36
    row_height = (bottom - rows_top) / max(1, len(lanes))
    for row, lane in enumerate(lanes):
        y = rows_top + row * row_height
        body.append('<text x="%d" y="%.2f" font-family="Georgia, serif" font-size="12" fill="#1b1b1b">%s</text>'
                    % (margin, y + 18, html.escape(lane["label"])))
        for column, cell in enumerate(lane["cells"]):
            if column >= len(stages):
                break
            x = margin + lane_width + column * stage_width
            body.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="#ffffff" '
                        'stroke="#c9c9c4"/>' % (x, y, stage_width, row_height))
            if not cell:
                continue
            lines = _wrap(cell, max(8, int(stage_width / 6.4)))
            for line_index, line in enumerate(lines[:4]):
                body.append('<text x="%.2f" y="%.2f" text-anchor="middle" font-family="Georgia, serif" '
                            'font-size="10" fill="#1b1b1b">%s</text>'
                            % (x + stage_width / 2, y + 16 + 13 * line_index, html.escape(line)))
    return _open(title) + _title(title) + "".join(body) + _close()


STATUS_COLOURS = {
    "on track": "#59a14f", "green": "#59a14f", "met": "#59a14f",
    "at risk": "#f28e2b", "amber": "#f28e2b", "watch": "#f28e2b",
    "off track": "#e15759", "red": "#e15759", "missed": "#e15759",
}


def _kpi(items, title, bundle):
    """A KPI card per item: the recorded value, its target, and its recorded status."""
    from . import export as case_export

    if bundle is None:
        raise DiagramError("a KPI board reads stored values, so it needs the case record")
    stored = case_export.artifact_rows(bundle)

    def value_of(key):
        for row in stored:
            if row.get("metric") == key or row.get("id") == key:
                return row.get("value")
        return None

    body = []
    columns = 2
    margin, gap = 24, 16
    width = (WIDTH - 2 * margin - gap * (columns - 1)) / columns
    height = 86
    for index, item in enumerate(items):
        column, row = index % columns, index // columns
        x = margin + column * (width + gap)
        y = 78 + row * (height + gap)
        if y + height > HEIGHT - 40:
            break
        status = str(value_of(item.get("status")) or "").strip().lower() if item.get("status") else ""
        colour = STATUS_COLOURS.get(status, "#c9c9c4")
        body.append('<rect x="%.2f" y="%.2f" width="%.2f" height="%d" rx="6" fill="#ffffff" '
                    'stroke="#c9c9c4"/>' % (x, y, width, height))
        body.append('<rect x="%.2f" y="%.2f" width="6" height="%d" rx="3" fill="%s"/>'
                    % (x, y, height, colour))
        body.append('<text x="%.2f" y="%.2f" font-family="Georgia, serif" font-size="11" fill="#555550">%s</text>'
                    % (x + 16, y + 20, html.escape(item["label"])))
        value = value_of(item["value"])
        body.append('<text x="%.2f" y="%.2f" font-family="Georgia, serif" font-size="22" fill="#1b1b1b">%s</text>'
                    % (x + 16, y + 50, html.escape("not recorded" if value is None else str(value))))
        if item.get("target"):
            target = value_of(item["target"])
            body.append('<text x="%.2f" y="%.2f" font-family="Georgia, serif" font-size="10" fill="#6b6b6b">%s</text>'
                        % (x + 16, y + 68, html.escape("Target " + ("not recorded" if target is None else str(target)))))
        if status:
            body.append('<text x="%.2f" y="%.2f" text-anchor="end" font-family="Georgia, serif" font-size="10" '
                        'fill="%s">%s</text>'
                        % (x + width - 12, y + 20, colour, html.escape(status)))
    return _open(title) + _title(title) + "".join(body) + _close()


def render_svg(spec, bundle=None):
    """Draw one diagram as deterministic SVG. Returns the SVG string."""
    kind, title, labels = validate_spec(spec)
    if kind == "process":
        return _process(labels, title)
    if kind == "matrix2x2":
        return _matrix(spec, title)
    if kind == "pyramid":
        return _pyramid(labels, title)
    if kind == "funnel":
        return _funnel(labels, title)
    if kind == "board":
        return _board(labels, title)
    if kind == "journey":
        return _journey(labels, title)
    if kind == "kpi":
        return _kpi(labels, title, bundle)
    return _tree(spec, labels, title)


def export_svg(spec, path):
    """Write one diagram SVG to `path` (atomic). Returns the path."""
    svg = render_svg(spec)
    target = Path(path)
    if str(target.parent) not in ("", "."):
        target.parent.mkdir(parents=True, exist_ok=True)
    handle, temp_name = tempfile.mkstemp(dir=str(target.parent or "."), prefix=".tmp-diagram-", suffix=".svg")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(svg)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, target)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return str(target)
