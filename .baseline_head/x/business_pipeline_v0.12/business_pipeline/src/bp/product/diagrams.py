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

FORMAT = "bp-diagram/1"
KINDS = ("process", "matrix2x2", "pyramid", "funnel", "tree")
WIDTH, HEIGHT = 720, 420
PALETTE = ("#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948")
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


def render_svg(spec):
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
