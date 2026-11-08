"""The figures a plan's recorded data earns - and nothing more.

A figure is proposed only when a rule fires on stored data, and every proposal
carries the reason it fired.  A single scalar is a sentence, not a chart; fewer
than three points is not a trend; a picture that would repeat a table beside it
is not drawn.

The rules are data.  A new trigger is a new entry in `RULES`, never an edit to a
renderer, and a block that declares no data draws nothing.

Two ways in:

* the plan declares the shape - `block["series"]`, `block["composition"]`,
  `block["alternatives"]` or a full `block["figure"]` spec;
* the bundle records a schedule - early start / early finish artifacts become a
  Gantt, because those values already exist and nothing else uses them.
"""

from . import figures
from . import export as case_export

#: The minimum points a shape needs before it is worth drawing.
MIN_SERIES = 2
MIN_TREND = 3


def _stored_ids(bundle):
    return {str(row.get("id")) for row in case_export.artifact_rows(bundle) if row.get("id")}


def _cpm_activities(bundle):
    """One activity per `es_*` that also has an `ef_*`, labelled from the id."""
    recorded = _stored_ids(bundle)
    activities = []
    for ident in sorted(recorded):
        if not ident.startswith("es_"):
            continue
        suffix = ident[3:]
        if not suffix or "ef_" + suffix not in recorded:
            continue
        activity = {"id": suffix, "label": suffix.replace("_", " ").title(),
                    "start": ident, "end": "ef_" + suffix}
        if "float_" + suffix in recorded:
            activity["float"] = "float_" + suffix
        if "critical_" + suffix in recorded:
            activity["critical"] = "critical_" + suffix
        activities.append(activity)
    return activities


def _pairs(block, key):
    entries = block.get(key)
    if not isinstance(entries, list):
        return []
    pairs = []
    for entry in entries:
        if isinstance(entry, dict) and entry.get("label") and entry.get("artifact"):
            pairs.append({"label": str(entry["label"]), "artifact": str(entry["artifact"])})
    return pairs


def _chart(block, series, kind, why):
    return {
        "format": "bp-chart/1",
        "kind": kind,
        "title": str(block.get("figure_title") or block.get("label") or "Recorded results"),
        "series": series,
    }, why


def explain(bundle, plan=None):
    """Propose figures and name every block that drew nothing.

    Returns `(proposed, skipped)` where each skip carries the block and the
    reason, so a plan can show why a section has no figure rather than leaving
    the reader to guess.
    """
    plan = plan or {}
    proposed, skipped = [], []

    for index, block in enumerate(plan.get("blocks") or []):
        if not isinstance(block, dict):
            continue
        label = str(block.get("label") or block.get("key") or "block %d" % index)
        section = str(block.get("section") or block.get("label") or "")
        try:
            if isinstance(block.get("figure"), dict):
                record = figures.make(
                    "chart", block["figure"],
                    caption=str(block.get("figure_caption") or label),
                    why=str(block.get("why") or "the block declares this figure"),
                    origin="plan", place=section)
                proposed.append(record)
                continue

            series = _pairs(block, "series")
            if series:
                if len(series) < MIN_SERIES:
                    skipped.append({"block": label,
                                    "reason": "a chart needs at least %d points, this block records %d"
                                              % (MIN_SERIES, len(series))})
                    continue
                kind = "line" if len(series) >= MIN_TREND else "bar"
                spec, why = _chart(block, series, kind,
                                   "the block records %d points" % len(series))
                proposed.append(figures.make(
                    "chart", spec, caption=str(block.get("figure_caption") or label),
                    why=why, origin="plan", place=section))
                continue

            entries = [entry for entry in (block.get("pareto") or [])
                       if isinstance(entry, dict) and entry.get("label")
                       and entry.get("artifact") and entry.get("cumulative")]
            if entries:
                if len(entries) < MIN_SERIES:
                    skipped.append({"block": label,
                                    "reason": "a pareto needs at least %d points, this block "
                                              "records %d" % (MIN_SERIES, len(entries))})
                    continue
                spec = {"format": "bp-chart/1", "kind": "pareto",
                        "title": str(block.get("figure_title") or block.get("label")
                                     or "Recorded results"),
                        "series": [{"label": str(entry["label"]),
                                    "artifact": str(entry["artifact"]),
                                    "cumulative": str(entry["cumulative"])}
                                   for entry in entries]}
                proposed.append(figures.make(
                    "chart", spec, caption=str(block.get("figure_caption") or label),
                    why="the block records a running total for %d points" % len(entries),
                    origin="plan", place=section))
                continue

            for key, kind, minimum in (("composition", "stacked_bar", MIN_SERIES),
                                       ("alternatives", "bar", MIN_SERIES)):
                series = _pairs(block, key)
                if not series:
                    continue
                if len(series) < minimum:
                    skipped.append({"block": label,
                                    "reason": "a %s needs at least %d points, this block records %d"
                                              % (key, minimum, len(series))})
                    continue
                spec, why = _chart(block, series, kind,
                                   "the block records %d %s points" % (len(series), key))
                proposed.append(figures.make(
                    "chart", spec, caption=str(block.get("figure_caption") or label),
                    why=why, origin="plan", place=section))
                break
        except figures.FigureError as error:
            skipped.append({"block": label, "reason": str(error)})

    activities = _cpm_activities(bundle)
    if len(activities) >= MIN_SERIES and not any(
            record["spec"].get("kind") == "gantt" for record in proposed):
        spec = {"format": "bp-chart/1", "kind": "gantt",
                "title": "Project schedule", "activities": activities}
        try:
            proposed.append(figures.make(
                "chart", spec, caption="Project schedule",
                why="the record holds an early start and an early finish for %d activities"
                    % len(activities),
                origin="plan", place="Schedule"))
        except figures.FigureError as error:
            skipped.append({"block": "schedule", "reason": str(error)})

    seen, unique = set(), []
    for record in proposed:
        if record["id"] in seen:
            continue
        seen.add(record["id"])
        unique.append(record)
    return unique, skipped


def propose(bundle, plan=None):
    """The figures this bundle earns, deduplicated by id."""
    return explain(bundle, plan)[0]


def build(bundle, sections, plan=None, scale=3):
    """Propose, draw and place the figures of a paper in one call.

    Returns the sections (each carrying its `figure`) and a report of what was
    placed, what could not be placed, and which blocks drew nothing and why.
    """
    proposed, skipped = explain(bundle, plan)
    drawn = []
    for figure in proposed:
        try:
            figures.render(figure, bundle, scale=scale)
            figures.stamp(figure, bundle)
        except Exception as error:
            skipped.append({"block": figure.get("place") or figure.get("id"),
                            "reason": "the figure could not be drawn: %s" % error})
            continue
        drawn.append(figure)
    sections, placed, unplaced = attach(sections, drawn)
    return sections, {"placed": placed, "unplaced": unplaced, "skipped": skipped}


def attach(sections, proposed):
    """Place each figure under the section it names.

    A figure that names no section, or names one the paper does not carry, is
    returned as unplaced: it is never dropped into an arbitrary heading, and
    never silently discarded.
    """
    placed, unplaced = [], []
    for figure in proposed:
        target = figure.get("place")
        match = None
        if target:
            for item in sections or []:
                if isinstance(item, dict) and str(item.get("heading") or "").strip() == target:
                    match = item
                    break
        if match is None:
            unplaced.append(figure)
            continue
        existing = match.get("figure")
        if existing and existing.get("id") == figure["id"]:
            placed.append(figure)  # already placed by an earlier pass
            continue
        if existing:
            unplaced.append(figure)
            continue
        match["figure"] = figure
        placed.append(figure)
    return sections, placed, unplaced
