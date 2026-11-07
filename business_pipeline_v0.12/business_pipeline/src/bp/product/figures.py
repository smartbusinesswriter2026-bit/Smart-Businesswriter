"""One figure record, referenced by id, drawn only from stored values.

A figure is what the paper, the deck and the spreadsheet all point at.  It
carries:

* the spec - `bp-chart/1` (`charts`) or `bp-diagram/1` (`diagrams`);
* the caption and the note, both digit-free: a figure may not carry a claim;
* the artifact ids it draws from, and a **digest** of the values it was drawn
  from, so a figure that no longer matches the record is caught, not shipped;
* the reason it exists (`why`), so a plan can show a figure earned its place;
* where it goes (`place`, a section heading).

A paper section, a slide and a spreadsheet cell all name a figure by `id`; none
of them copies its values, so two artefacts cannot disagree about one number.

Rendering is delegated to `bp.product.renderers`, which always has the builtin
standard-library SVG and uses Plotly, Mermaid or Graphviz only when installed.
"""

import json
from hashlib import sha256

from . import charts, diagrams, tables
from . import export as case_export

FIGURE_FORMAT = "bp-figure/1"
KINDS = ("chart", "diagram", "table")


class FigureError(ValueError):
    """The figure cannot be made, validated or drawn honestly."""


def _text(value, what, allow_digits=False):
    if not isinstance(value, str) or not value.strip():
        raise FigureError("%s must be non-empty text" % what)
    text = value.strip()
    if not allow_digits and any(character.isdigit() for character in text):
        raise FigureError("%s may not contain digits: numbers appear only as stored values (%r)"
                          % (what, text))
    return text


def _validate_spec(kind, spec):
    if kind == "chart":
        charts.validate_spec(spec)
    elif kind == "diagram":
        diagrams.validate_spec(spec)
    else:
        tables.validate_spec(spec)


def _sources(kind, spec):
    """Every artifact id a spec draws from, in the order it names them."""
    if kind == "table":
        return tables.sources(spec) if isinstance(spec, dict) else []
    if kind != "chart" or not isinstance(spec, dict):
        return []
    if spec.get("kind") == "gantt":
        found = []
        for activity in spec.get("activities") or []:
            if not isinstance(activity, dict):
                continue
            for key in ("start", "end", "float", "critical"):
                value = activity.get(key)
                if isinstance(value, str) and value.strip():
                    found.append(value.strip())
        return found
    found = []
    for entry in spec.get("series") or []:
        if not isinstance(entry, dict):
            continue
        for key in ("artifact", "label_artifact"):
            if isinstance(entry.get(key), str) and entry[key].strip():
                found.append(entry[key].strip())
    return found


def make(kind, spec, caption, note="", why="", origin="plan", ident=None, place=""):
    """Build one figure record.  Raises `FigureError` when the spec is not honest."""
    if kind not in KINDS:
        raise FigureError("figure kind must be one of: " + ", ".join(KINDS))
    if not isinstance(spec, dict):
        raise FigureError("figure spec must be an object")
    _validate_spec(kind, spec)
    figure = {
        "format": FIGURE_FORMAT,
        "kind": kind,
        "spec": spec,
        "caption": _text(caption, "figure caption"),
        "note": _text(note, "figure note") if note else "",
        "why": _text(why, "figure reason", allow_digits=True),
        "origin": origin if origin in ("plan", "chat") else "plan",
        "place": _text(place, "figure placement", allow_digits=True) if place else "",
        "sources": _sources(kind, spec),
    }
    figure["id"] = ident or _ident(figure)
    return figure


def _ident(figure):
    """A stable id: the same spec and caption name the same figure, every run."""
    payload = json.dumps({"kind": figure["kind"], "spec": figure["spec"],
                          "caption": figure["caption"]},
                         sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "fig_" + sha256(payload.encode("utf-8")).hexdigest()[:12]


def validate(figure):
    """Check a whole record, including the reason it exists."""
    if not isinstance(figure, dict):
        raise FigureError("figure must be an object")
    if figure.get("format", FIGURE_FORMAT) != FIGURE_FORMAT:
        raise FigureError("unsupported figure format %r, expected %r"
                          % (figure.get("format"), FIGURE_FORMAT))
    kind = figure.get("kind")
    if kind not in KINDS:
        raise FigureError("figure kind must be one of: " + ", ".join(KINDS))
    spec = figure.get("spec")
    if not isinstance(spec, dict):
        raise FigureError("figure spec must be an object")
    _validate_spec(kind, spec)
    _text(figure.get("caption"), "figure caption")
    if figure.get("note"):
        _text(figure["note"], "figure note")
    _text(figure.get("why"), "figure reason", allow_digits=True)
    if figure.get("place"):
        _text(figure["place"], "figure placement", allow_digits=True)
    return figure


def _spec_texts(value):
    """Every string a spec carries, for the template-text scan."""
    found = []
    if isinstance(value, dict):
        for item in value.values():
            found.extend(_spec_texts(item))
    elif isinstance(value, (list, tuple)):
        for item in value:
            found.extend(_spec_texts(item))
    elif isinstance(value, str):
        found.append(value)
    return found


def text(figure):
    """Every string a figure carries, joined, for the template-text scan."""
    if not figure:
        return ""
    parts = [str(figure.get("caption") or ""), str(figure.get("note") or "")]
    for grid in figure.get("grids") or []:
        parts.append(str(grid.get("title") or ""))
        for row in grid.get("rows") or []:
            for cell in row or []:
                parts.append(str(cell.get("label") or ""))
                parts.extend(str(bullet) for bullet in cell.get("bullets") or [])
                parts.append(str(cell.get("gap") or ""))
    if figure.get("spec"):
        parts.extend(_spec_texts(figure["spec"]))
    return " ".join(part for part in parts if part)


def _stored(rows, key):
    for row in rows:
        if row.get("metric") == key or row.get("id") == key:
            return row.get("value")
    return None


def digest(figure, bundle):
    """A hash of the stored values the figure draws from.

    Two runs over the same record agree.  When an input changes and an artifact
    moves, the digest moves with it, so a figure drawn from the old value is
    reported as stale instead of being shipped beside the new one.
    """
    if figure.get("sources"):
        rows = case_export.artifact_rows(bundle)
        lines = ["%s=%s" % (key, _stored(rows, key)) for key in figure["sources"]]
    else:
        lines = [json.dumps(figure.get("spec"), sort_keys=True, separators=(",", ":"))]
    return sha256("\n".join(lines).encode("utf-8")).hexdigest()


def stamp(figure, bundle):
    """Record the digest of the values this figure was drawn from."""
    figure["digest"] = digest(figure, bundle)
    return figure


def stale(figure, bundle):
    """True when the record has moved since this figure was drawn."""
    if not figure.get("digest"):
        return False
    return digest(figure, bundle) != figure["digest"]


def rows_for(figure, bundle):
    """The stored values a chart draws, as (label, stored string) pairs.

    The pairs let a Word reader still see the numbers when no rasterizer is
    installed: the chart falls back to a small table of the stored strings,
    never to a picture that cannot be checked.
    """
    if figure.get("kind") != "chart":
        return []
    spec = figure.get("spec") or {}
    stored = case_export.artifact_rows(bundle)
    if spec.get("kind") == "gantt":
        pairs = []
        for activity in spec.get("activities") or []:
            label = activity.get("label")
            start = _stored(stored, activity.get("start"))
            end = _stored(stored, activity.get("end"))
            pairs.append((label, "%s to %s" % (start, end)))
        return pairs
    pairs = []
    for entry in spec.get("series") or []:
        pairs.append((entry.get("label"), _stored(stored, entry.get("artifact"))))
    return pairs


def render(figure, bundle, scale=3):
    """Draw the figure and attach what the exporters need.

    The record carries the SVG, the PNG (when a rasterizer is installed) and
    the stored values, so an exporter never needs the bundle to place it.
    """
    from . import renderers

    if figure.get("kind") == "table":
        figure["table"] = tables.resolve(figure.get("spec") or {}, bundle)
        figure["asset"] = {"svg": None, "png": None}
        figure["rows"] = []
        return figure
    figure["asset"] = {"svg": renderers.svg(figure, bundle),
                       "png": renderers.png(figure, bundle, scale=scale)}
    figure["rows"] = rows_for(figure, bundle)
    return figure


def prepare(records, bundle, scale=3):
    """Render stored records for one export, leaving each stored record untouched.

    A case keeps a figure's record, not its bytes; the exporter draws it again from
    the stored values, so a figure can never ship a picture older than its data.
    """
    drawn = []
    for record in records or []:
        if not isinstance(record, dict):
            continue
        copy = dict(record)
        try:
            render(copy, bundle, scale=scale)
            stamp(copy, bundle)
        except Exception:
            continue
        drawn.append(copy)
    return drawn


def specs(records):
    """The chart and diagram specs of a list of figure records, for the HTML export."""
    charts_out = [record["spec"] for record in records if record.get("kind") == "chart"]
    diagrams_out = [record["spec"] for record in records if record.get("kind") == "diagram"]
    return charts_out, diagrams_out


class Registry:
    """The single place the figures of one case live."""

    def __init__(self, figures=None):
        self._figures = {}
        for figure in figures or []:
            self.add(figure)

    def add(self, figure):
        validate(figure)
        self._figures[figure["id"]] = figure
        return figure

    def get(self, ident):
        return self._figures.get(ident)

    def all(self):
        return [self._figures[key] for key in sorted(self._figures)]

    def to_list(self):
        return self.all()

    @classmethod
    def from_list(cls, figures):
        return cls(figures or [])

    def __len__(self):
        return len(self._figures)
