"""Draw a completed process framework from the labels it was given (product layer).

A SIPOC and a value stream map are pictures before they are prose, so the page
draws one after the student applies the completion.  The drawing obeys the same
rule as `bp.product.diagrams`: it carries **labels, not numbers**.  A line that
contains a digit is left out of the picture and counted, because a diagram that
prints "90 seconds" would smuggle a figure into a picture that is otherwise a
structure, and the paper's numbers must come from the frozen core.

Nothing here measures, orders or infers.  The boxes are the declared parts in the
declared order; a part with no item is drawn as a gap; lines are shortened only
to fit and the full text stays in the worksheet and the paper.
"""

import html
import re

#: The two frameworks this module can draw, and the parts each one shows.
LAYOUTS = {
    "template_sipoc": ("sipoc", ("suppliers", "inputs", "process", "outputs", "customers")),
    "template_value_stream_map": ("vsm", ("process_steps", "cycle_and_lead_times", "inventory_wip",
                                          "waits_delays", "value_added", "improvements")),
}

_DIGIT = re.compile(r"\d")
_WORD = re.compile(r"\S+")
MAX_LINES = 3
MAX_CHARS = 26


class MapError(ValueError):
    """The completion cannot be drawn."""


def supported(template):
    return str(template or "") in LAYOUTS


def _lines(text, limit=MAX_CHARS, max_lines=MAX_LINES):
    """Break a label into at most `max_lines` lines, without cutting a word."""
    words, lines, current = _WORD.findall(str(text or "")), [], ""
    for word in words:
        candidate = (current + " " + word).strip()
        if len(candidate) <= limit or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and len(" ".join(words)) > len(" ".join(lines)):
        lines[-1] = lines[-1].rstrip(" .,;:") + "..."
    return lines or [""]


def _escape(text):
    return html.escape(str(text or ""), quote=True)


def _text(x, y, lines, size=12, fill="#1b1b1b", anchor="start", weight="normal"):
    out = []
    for index, line in enumerate(lines):
        out.append('<text x="%s" y="%s" font-family="Georgia, serif" font-size="%s" fill="%s" '
                   'text-anchor="%s" font-weight="%s">%s</text>'
                   % (x, y + index * (size + 3), size, fill, anchor, weight, _escape(line)))
    return "".join(out)


def _panel(kind, blocks, process):
    """The five SIPOC columns, or the value-stream strip, from the declared parts."""
    width, height = 960, 300
    title = ("SIPOC: " if kind == "sipoc" else "Value stream: ") + (process or "the declared process")
    parts = []
    omitted = 0
    seen = {}
    for block in blocks:
        kept = []
        for item in block.get("items") or []:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            if _DIGIT.search(text):
                omitted += 1
                continue
            # One sentence of a brief can honestly describe two parts of a map.
            # Repeating it in every column looks like three findings, so the
            # second and later columns point at the first instead.
            key = " ".join(text.lower().split())
            if key in seen:
                kept.append(("see " + seen[key], True))
                continue
            seen[key] = block.get("label") or block.get("key") or "the earlier part"
            kept.append((text, False))
        parts.append({"key": block.get("key"), "label": block.get("label") or block.get("key"),
                      "items": kept})
    if not any(part["items"] for part in parts):
        return None, omitted
    body = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" '
            'role="img" aria-label="%s">' % (width, height, width, height, _escape(title)),
            '<rect width="100%" height="100%" fill="#fdfdfb"/>',
            _text(24, 30, [title], size=16, weight="bold")]
    if kind == "sipoc":
        left, gap = 24, 12
        column = (width - 2 * left - gap * (len(parts) - 1)) / max(1, len(parts))
        top, box = 56, 190
        for index, part in enumerate(parts):
            x = left + index * (column + gap)
            body.append('<rect x="%.2f" y="%d" width="%.2f" height="%d" rx="8" fill="#ffffff" '
                        'stroke="#c9d3dd" stroke-width="1"/>' % (x, top, column, box))
            body.append('<rect x="%.2f" y="%d" width="%.2f" height="26" rx="8" fill="#eef3f8"/>'
                        % (x, top, column))
            body.append(_text(x + 10, top + 18, _lines(part["label"], limit=22, max_lines=1), size=11))
            if part["items"]:
                text, repeat = part["items"][0]
                body.append(_text(x + 10, top + 48, _lines(text), size=11,
                                  fill="#5c6b7a" if repeat else "#1b1b1b"))
                if len(part["items"]) > 1:
                    body.append(_text(x + 10, top + 48 + 3 * 14,
                                      ["+%d more" % (len(part["items"]) - 1)], size=10, fill="#5c6b7a"))
            else:
                body.append(_text(x + 10, top + 48, ["gap"], size=11, fill="#8a5a08"))
            if index < len(parts) - 1:
                body.append('<path d="M%.2f %d l8 0 m-4 -4 l4 4 l-4 4" stroke="#8fa2b5" stroke-width="1.6" '
                            'fill="none"/>' % (x + column + 1, top + box // 2))
    else:
        steps = next((part["items"] for part in parts if part["key"] == "process_steps"), [])
        others = [part for part in parts if part["key"] != "process_steps" and part["items"]]
        shown = steps[:6]
        left, gap, top, box = 24, 10, 56, 96
        width_each = (width - 2 * left - gap * max(0, len(shown) - 1)) / max(1, len(shown))
        for index, step in enumerate(shown):
            x = left + index * (width_each + gap)
            body.append('<rect x="%.2f" y="%d" width="%.2f" height="%d" rx="8" fill="#eef3f8" '
                        'stroke="#c9d3dd" stroke-width="1"/>' % (x, top, width_each, box))
            body.append(_text(x + 8, top + 20, _lines(step[0], limit=18), size=10,
                              fill="#5c6b7a" if step[1] else "#1b1b1b"))
            if index < len(shown) - 1:
                body.append('<path d="M%.2f %d l7 0 m-3 -3 l3 3 l-3 3" stroke="#8fa2b5" stroke-width="1.6" '
                            'fill="none"/>' % (x + width_each + 1, top + box // 2))
        if not shown:
            body.append(_text(left, top + 20, ["No step was declared, so nothing is drawn here."],
                              size=11, fill="#8a5a08"))
        y = top + box + 34
        for part in others:
            body.append(_text(left, y, _lines(part["label"], limit=40, max_lines=1), size=10, fill="#5c6b7a"))
            text, repeat = part["items"][0]
            body.append(_text(left + 210, y, _lines(text, limit=54, max_lines=1), size=11,
                              fill="#5c6b7a" if repeat else "#1b1b1b"))
            y += 22
    body.append(_text(24, height - 16,
                      ["Structure only: the parts and lines you supplied, in the order you supplied them. "
                       "No step was timed, placed or computed."], size=10, fill="#6b6b6b"))
    body.append("</svg>")
    return "".join(body), omitted


def build(completion):
    """Return the drawing for a completion, or a named reason it has none.

    `omitted` counts the lines left out because they carry a number: the page
    says so, so a shorter picture is never mistaken for a complete one.
    """
    if not isinstance(completion, dict):
        raise MapError("a completion object is required")
    template = completion.get("template")
    if not supported(template):
        raise MapError("this framework is not drawn; the map covers the SIPOC and the value stream map")
    kind, order = LAYOUTS[template]
    blocks = completion.get("blocks")
    if not isinstance(blocks, list) or not blocks:
        raise MapError("the completion has no parts to draw")
    known = {block.get("key"): block for block in blocks if isinstance(block, dict)}
    ordered = [known[key] for key in order if key in known]
    if not ordered:
        raise MapError("the completion does not carry the parts this map draws")
    process = (completion.get("unit") or {}).get("value") or ""
    svg, omitted = _panel(kind, ordered, process)
    return {"format": "bp-worksheet-map/1", "template": template, "kind": kind,
            "svg": svg, "drawn": svg is not None, "omitted": omitted,
            "process": process}
