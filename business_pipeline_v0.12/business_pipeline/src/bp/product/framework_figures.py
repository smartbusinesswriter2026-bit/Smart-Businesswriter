"""A framework chart built from the existing chart and diagram modules.

This is an adapter, not a renderer.  A framework record that holds numeric values
(a scorecard, an RPN table, a measure series, a calculation row) becomes a normal
`figure`: the spec is `bp-chart/1` or `bp-diagram/1`, the digest is stamped, and
Word embeds the PNG or falls back to the value table.  The model never draws a
chart and never supplies a number that the record does not hold.
"""

from . import figures, visuals

#: The existing kinds a framework may use.  A framework is not allowed to invent
#: a new kind; the list is the chart/diagram registry, not a preference.
CHART_KINDS = ("bar", "line", "pie", "pareto", "waterfall", "stacked_bar", "tree")


class ChartError(ValueError):
    """The framework chart cannot be drawn honestly."""


def _text(value):
    return str(value or "").strip()


def validate_chart(chart, allowed_values=None):
    """A clean chart record, or `ChartError` naming what is wrong.

    ``allowed_values`` is the set of numbers the record actually holds.  When it
    is supplied, every plotted value must be in it; a chart may reorder the
    record but may not add to it.
    """
    if not isinstance(chart, dict):
        raise ChartError("a chart must be an object")
    kind = _text(chart.get("kind"))
    if kind not in CHART_KINDS:
        raise ChartError("chart kind must be one of: " + ", ".join(CHART_KINDS))
    title = _text(chart.get("title"))
    if not title:
        raise ChartError("a chart needs a title")
    if kind == "tree":
        root = _text(chart.get("root"))
        children = [_text(child) for child in chart.get("children") or [] if _text(child)]
        if not root or not children:
            raise ChartError("a tree chart needs a root and at least one child")
        return {"kind": "tree", "title": title, "root": root, "children": children}
    points = chart.get("points")
    if not isinstance(points, list) or not points:
        raise ChartError("a chart needs at least one point")
    clean = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ChartError("point %d must be an object" % (index + 1))
        label = _text(point.get("label"))
        if not label:
            raise ChartError("point %d needs a label" % (index + 1))
        try:
            value = float(point.get("value"))
        except (TypeError, ValueError):
            raise ChartError("point %r needs a number in 'value'" % label)
        if allowed_values is not None:
            known = {float(item) for item in allowed_values}
            if value not in known:
                raise ChartError("point %r plots a value the record does not hold" % label)
        entry = {"label": label, "value": str(point.get("value")).strip()}
        if kind == "pareto":
            try:
                float(point.get("cumulative"))
            except (TypeError, ValueError):
                raise ChartError("a pareto needs a cumulative for every point; %r has none"
                                 % label)
            entry["cumulative"] = str(point.get("cumulative")).strip()
        clean.append(entry)
    return {"kind": kind, "title": title, "points": clean}


def build(chart, caption="Framework chart"):
    """A rendered figure for a validated chart record.

    The caption is the module's own words and must carry no digit (a figure
    caption is not allowed a number; the numbers live in the spec and the
    table).  The chart title may carry the framework's own figure.
    """
    record = validate_chart(chart)
    caption = _text(caption) or "Framework chart"
    if any(character.isdigit() for character in caption):
        raise ChartError("the figure caption may not contain a digit: %r" % caption)
    title = record["title"]
    try:
        if record["kind"] == "tree":
            spec = {"format": "bp-diagram/1", "kind": "tree", "title": title,
                    "root": record["root"],
                    "children": [{"label": child} for child in record["children"]]}
            figure = figures.make("diagram", spec, caption=caption,
                                  why="the why-chain record", origin="chat")
            figures.render(figure, None)
            figures.stamp(figure, None)
            return figure
        bundle, series, label = visuals.source_bundle(
            {"kind": "declared", "points": record["points"]})
        spec = visuals.spec_for(record["kind"], series, title)
        figure = figures.make("chart", spec, caption=caption, note=label,
                              why="the framework record holds these values", origin="chat")
        figures.render(figure, bundle)
        figures.stamp(figure, bundle)
        return figure
    except ChartError:
        raise
    except Exception as error:                                  # noqa: BLE001
        raise ChartError(str(error)[:300])
