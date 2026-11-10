"""Call the frozen core for portfolio arithmetic; classify, never compute.

BCG needs relative share and market growth; GE-McKinsey needs weighted scores.
The arithmetic already exists in the frozen core: `market_share` returns
`relative_market_share`, `growth_rate` returns CAGR, and `weighted_summary`
returns `weighted_mean`.  This module calls those methods, formats their output
and applies the declared threshold rule.  It never divides, averages or scores
anything itself.

The core is attached by the server (`api.attach_methods`), so the product
package never imports it.
"""

from . import portfolio_reader, quality_reader

RUN = None
DESCRIBE = None


def set_method_compute(run, describe=None):
    """Attach the frozen core's run and describe callables."""
    global RUN, DESCRIBE
    RUN = run
    DESCRIBE = describe


def _core(name, inputs):
    if RUN is None:
        raise RuntimeError("the computation core is not attached; start the workbench")
    return RUN(name, inputs)


def _pct(value):
    try:
        return "%.1f%%" % (float(value) * 100)
    except (TypeError, ValueError):
        return ""


def _ratio(value):
    try:
        return "%.2f" % float(value)
    except (TypeError, ValueError):
        return ""


#: The BCG quadrant from market growth and relative share.  The cutoff is the
#: declared line between high and low growth; relative share is high at 1.0.
def bcg_quadrant(growth, relative_share, growth_cutoff):
    high_growth = float(growth) >= float(growth_cutoff)
    high_share = float(relative_share) >= 1.0
    if high_growth and high_share:
        return "Star"
    if high_growth and not high_share:
        return "Question mark"
    if not high_growth and high_share:
        return "Cash cow"
    return "Dog"


def _borderline(growth, relative_share, growth_cutoff):
    near_growth = False
    if growth_cutoff:
        near_growth = abs(float(growth) - float(growth_cutoff)) <= 0.15 * abs(float(growth_cutoff))
    near_share = abs(float(relative_share) - 1.0) <= 0.15
    return near_growth or near_share


def bcg(units, growth_cutoff=None):
    """One row per unit: the core's relative share and growth, then the quadrant.

    When the brief declares no cutoff, the portfolio average growth is used (the
    guideline's own example).  That average is a weighted mean from the core, not
    arithmetic in this module.
    """
    columns = ["Unit", "Market", "Growth", "Relative share", "Quadrant", "Borderline"]
    rows, problems = [], []
    cutoff_is_average = growth_cutoff is None
    if cutoff_is_average:
        growths = [unit.get("growth") for unit in units or []
                   if unit.get("growth") is not None]
        if growths:
            try:
                out = _core("weighted_summary", {
                    "values": [str(value) for value in growths],
                    "weights": ["1"] * len(growths),
                })
                growth_cutoff = out.get("weighted_mean")
            except Exception as error:                          # noqa: BLE001
                problems.append("portfolio average growth: " + str(error)[:160])
        if growth_cutoff is None:
            growth_cutoff = 0.0
    for unit in units or []:
        name = str(unit.get("unit") or "").strip()
        market = str(unit.get("market") or "").strip()
        growth = unit.get("growth")
        relative = None
        try:
            if (unit.get("revenue") is not None and unit.get("market_size") is not None
                    and unit.get("competitor_revenue") is not None):
                share = _core("market_share", {
                    "firm_sales": str(unit["revenue"]),
                    "market_sales": str(unit["market_size"]),
                    "largest_competitor_sales": str(unit["competitor_revenue"]),
                })
                relative = share.get("relative_market_share")
            elif unit.get("own_share") is not None and unit.get("competitor_share") is not None:
                # A share-only table: the method only needs the ratio, so a
                # declared share can stand in for sales on a market of 1.
                share = _core("market_share", {
                    "firm_sales": str(unit["own_share"]),
                    "market_sales": "1",
                    "largest_competitor_sales": str(unit["competitor_share"]),
                })
                relative = share.get("relative_market_share")
        except Exception as error:                              # noqa: BLE001
            problems.append("%s: %s" % (name or "unit", str(error)[:160]))
        if relative is None or growth is None:
            missing = []
            if relative is None:
                missing.append("relative share")
            if growth is None:
                missing.append("market growth")
            rows.append([name, market, _pct(growth) if growth is not None else "not declared",
                         _ratio(relative) if relative is not None else "not computed",
                         "Not placed", "no " + " and ".join(missing)])
            problems.append("%s: no %s" % (name or "unit", " and ".join(missing)))
            continue
        quadrant = bcg_quadrant(growth, relative, growth_cutoff)
        rows.append([name, market, _pct(growth), _ratio(relative), quadrant,
                     "within 15% of a threshold" if _borderline(growth, relative, growth_cutoff)
                     else ""])
    return {"ok": bool(rows) and not problems,
            "method": "bcg", "columns": columns, "rows": rows,
            "problems": problems,
            "lines": ["Relative share is the unit's share divided by the largest competitor's "
                      "share, from the frozen market_share method; a value above 1.00 means the "
                      "unit leads its market. Growth is the market's growth, as declared.",
                      "The growth cutoff is %s%s. A unit within 15%% of the cutoff or of a "
                      "relative share of 1.00 is flagged as borderline."
                      % (_pct(growth_cutoff),
                         " (the portfolio average, because the brief declares none)"
                         if cutoff_is_average else "")]}


def _levels(score, cutoffs):
    low, high = float(cutoffs[0]), float(cutoffs[1])
    if float(score) <= low:
        return "Low"
    if float(score) >= high:
        return "High"
    return "Medium"


def ge(units, cutoffs=(2.33, 3.67)):
    """Weighted axis scores from the core and the 3x3 zone, one row per unit."""
    columns = ["Unit", "Attractiveness", "Strength", "Zone"]
    rows, problems = [], []
    for unit in units or []:
        name = str(unit.get("unit") or "").strip()
        totals = {}
        for axis in ("attractiveness", "strength"):
            block = unit.get(axis) or {}
            values = block.get("values") or []
            weights = block.get("weights") or []
            if len(values) != len(weights) or not values:
                problems.append("%s: %s needs one weight per score" % (name or "unit", axis))
                totals[axis] = None
                continue
            try:
                total_weight = sum(float(weight) for weight in weights)
                if abs(total_weight - 100) > 0.01:
                    raise ValueError("weights must sum to 100, not %g" % total_weight)
                out = _core("weighted_summary", {
                    "values": [str(value) for value in values],
                    "weights": [str(weight) for weight in weights],
                })
                totals[axis] = out.get("weighted_mean")
            except Exception as error:                          # noqa: BLE001
                problems.append("%s: %s: %s" % (name or "unit", axis, str(error)[:160]))
                totals[axis] = None
        if totals.get("attractiveness") is None or totals.get("strength") is None:
            rows.append([name, "not computed", "not computed", "Not placed"])
            continue
        attractiveness = _levels(totals["attractiveness"], cutoffs)
        strength = _levels(totals["strength"], cutoffs)
        if attractiveness == "High" and strength in ("Strong", "High", "Average", "Medium"):
            zone = "Invest / grow"
        elif attractiveness == "Low" and strength in ("Weak", "Low", "Average", "Medium"):
            zone = "Harvest / divest"
        else:
            zone = "Selective hold"
        rows.append([name, _ratio(totals["attractiveness"]), _ratio(totals["strength"]), zone])
    return {"ok": bool(rows) and not problems, "method": "ge_mckinsey",
            "columns": columns, "rows": rows, "problems": problems,
            "lines": ["Each axis is the weighted mean of its declared factor scores, from the "
                      "frozen weighted_summary method; the weights must sum to 100.",
                      "The zone is read from the declared cutoffs (low up to %.2f, high from "
                      "%.2f)." % (cutoffs[0], cutoffs[1])]}


def fmea(rows):
    """RPN per failure mode from the core, ranked into a Pareto."""
    columns = ["ID", "Failure mode", "S", "O", "D", "RPN", "Priority"]
    out, points, problems = [], [], []
    for row in rows or []:
        name = str(row.get("failure") or "").strip()
        try:
            result = _core("fmea_rpn", {
                "severity": str(row.get("severity")),
                "occurrence": str(row.get("occurrence")),
                "detection": str(row.get("detection")),
            })
        except Exception as error:                              # noqa: BLE001
            problems.append("%s: %s" % (name or "row", str(error)[:160]))
            out.append([str(row.get("id") or ""), name, "", "", "", "not computed", ""])
            continue
        severity = float(row.get("severity"))
        rpn = result.get("rpn")
        out.append([str(row.get("id") or ""), name, str(round(severity)),
                    str(round(float(row.get("occurrence")))),
                    str(round(float(row.get("detection")))),
                    _ratio(rpn), "Severity 9-10" if severity >= 9 else ""])
        points.append((name or str(row.get("id") or "row"), float(rpn)))
    points.sort(key=lambda pair: pair[1], reverse=True)
    cumulative, running = [], 0.0
    for label, value in points:
        running += value
        cumulative.append({"label": label, "value": "%.2f" % value,
                           "cumulative": "%.2f" % running})
    chart = ({"kind": "pareto", "title": "RPN by failure mode", "points": cumulative}
             if len(cumulative) >= 2 else None)
    return {"ok": bool(out) and not problems, "method": "fmea", "columns": columns,
            "rows": out, "chart": chart, "problems": problems,
            "lines": ["RPN = Severity x Occurrence x Detection, from the frozen fmea_rpn "
                      "method. A severity of 9 or 10 is a priority regardless of the RPN."]}


def five_s(rows):
    """The Five-S score per S from the core, as a bar of percentages."""
    columns = ["S", "Criteria", "Total", "Maximum", "Score %"]
    groups = {}
    for row in rows or []:
        key = str(row.get("category") or "").strip()
        if not key:
            continue
        groups.setdefault(key, []).append(row)
    out, points, problems = [], [], []
    for key in ("Sort", "Set in order", "Shine", "Standardize", "Sustain"):
        sample = next((name for name in groups if name.lower().startswith(key.lower())), None)
        if sample is None:
            continue
        group = groups.pop(sample)
        scores = [row.get("score") for row in group]
        maxima = [row.get("maximum") for row in group]
        if any(value is None for value in scores + maxima):
            problems.append("%s: a score or maximum is missing" % sample)
            continue
        if len(set(maxima)) != 1:
            problems.append("%s: the criteria use different maxima" % sample)
            continue
        try:
            result = _core("five_s_score", {
                "scores": [str(value) for value in scores],
                "maximum": str(maxima[0]),
            })
        except Exception as error:                              # noqa: BLE001
            problems.append("%s: %s" % (sample, str(error)[:160]))
            continue
        percent = float(result["score_rate"]) * 100
        out.append([sample, str(len(scores)), _ratio(result["total"]),
                    _ratio(result["max_total"]), "%.1f" % percent])
        points.append({"label": sample, "value": "%.1f" % percent})
    for key, group in groups.items():
        out.append([key, str(len(group)), "not computed", "not computed", "not computed"])
        problems.append("%s: not one of the five S categories" % key)
    chart = ({"kind": "bar", "title": "Score by S", "points": points}
             if len(points) >= 2 else None)
    return {"ok": bool(out) and not problems, "method": "five_s", "columns": columns,
            "rows": out, "chart": chart, "problems": problems,
            "lines": ["The score is the sum of the criterion scores over the declared maximum, "
                      "from the frozen five_s_score method. An unassessed criterion is excluded."]}


def for_quality(module, text):
    """The calculation record for an FMEA or Five-S brief, or a named gap."""
    if module == "fmea":
        parsed = quality_reader.read_fmea(text)
        if not parsed.get("ok"):
            return {"ok": False, "method": "fmea", "rows": [], "columns": [],
                    "error": " ".join(parsed.get("problems") or
                                      ["No FMEA table was found in the brief."])}
        result = fmea(parsed["rows"])
        result["problems"] = list(result.get("problems") or []) + list(parsed.get("problems") or [])
        return result
    if module == "five_s":
        parsed = quality_reader.read_five_s(text)
        if not parsed.get("ok"):
            return {"ok": False, "method": "five_s", "rows": [], "columns": [],
                    "error": " ".join(parsed.get("problems") or
                                      ["No Five-S scorecard was found in the brief."])}
        result = five_s(parsed["rows"])
        result["problems"] = list(result.get("problems") or []) + list(parsed.get("problems") or [])
        return result
    return None


def for_template(template, text):
    """The calculation record for a framework, or a named gap when it cannot run."""
    if template == "template_bcg":
        parsed = portfolio_reader.read(text)
        if not parsed.get("ok"):
            return {"ok": False, "method": "bcg", "rows": [], "columns": [],
                    "error": " ".join(parsed.get("problems") or
                                      ["No portfolio table was found in the brief."])}
        result = bcg(parsed["units"])
        result["problems"] = list(result.get("problems") or []) + list(parsed.get("problems") or [])
        return result
    if template == "template_ge_mckinsey":
        return {"ok": False, "method": "ge_mckinsey", "rows": [], "columns": [],
                "error": ("GE-McKinsey needs a factor table with a weight and a score per unit. "
                          "Declare the factors, their weights (summing to 100) and the scores.")}
    return None
