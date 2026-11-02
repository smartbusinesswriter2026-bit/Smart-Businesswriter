"""Matrix and canvas figures for the paper (product layer).

A framework that *is* a grid - SWOT, Ansoff, BCG, GE/McKinsey, Blue Ocean's
four actions, VRIO, McKinsey's seven S, Porter's value chain - should reach the
paper as a grid, not as four paragraphs in a row.  This module holds the geometry
of those grids as data and turns a framework's blocks into a figure.

Two rules govern everything here:

- the geometry is data, not code, so adding a framework never means editing the
  renderer (the conductor manual's rule for the writer and the renderer);
- the builder writes no content.  It places what the caller gives it and never
  a character of its own, so a cell can carry only the student's words, a
  retrieved item's own identity, the framework's recorded background, or a model
  proposal the student has already been shown.
"""

#: Geometry per template.  ``rows`` lists block keys in reading order; a cell
#: may span columns with ``span`` and may be a shared core with ``role``.
#: ``labels`` gives a cell its canonical name even when the caller supplies no
#: content for it, so an empty grid still reads as the framework.
LAYOUTS = {
    "template_swot": {
        "kind": "quadrant",
        "caption": "SWOT matrix",
        "note": "Strengths and weaknesses are the firm's own; opportunities and "
                "threats are drawn from the cited sources.",
        "labels": {"S": "Strengths", "W": "Weaknesses", "O": "Opportunities", "T": "Threats"},
        "grids": [{"rows": [["S", "W"], ["O", "T"]], "col_widths": [0.5, 0.5]}],
    },
    "template_ansoff": {
        "kind": "quadrant",
        "caption": "Ansoff growth matrix",
        "note": "Each cell holds the evidence for one growth option.",
        "labels": {"market_penetration": "Market penetration",
                   "market_development": "Market development",
                   "product_development": "Product development",
                   "diversification": "Diversification"},
        "grids": [{"rows": [["market_development", "diversification"],
                            ["market_penetration", "product_development"]],
                   "axis_x": ("Existing products", "New products"),
                   "axis_y": ("Existing markets", "New markets"),
                   "col_widths": [0.5, 0.5]}],
    },
    "template_value_chain": {
        "kind": "chain",
        "caption": "Porter's value chain",
        "note": "Support activities enable the primary activities that deliver "
                "the margin.",
        "labels": {"infrastructure": "Firm infrastructure",
                   "human": "Human resource management",
                   "technology": "Technology development",
                   "procurement": "Procurement",
                   "inbound": "Inbound logistics",
                   "operations": "Operations",
                   "outbound": "Outbound logistics",
                   "marketing": "Marketing and sales",
                   "service": "Service"},
        "grids": [
            {"title": "Support activities",
             "rows": [["infrastructure", "human", "technology", "procurement"]]},
            {"title": "Primary activities",
             "rows": [["inbound", "operations", "outbound", "marketing", "service"]]},
        ],
    },
    "template_vrio": {
        "kind": "columns",
        "caption": "VRIO analysis",
        "note": "The resource is judged against each of the four questions in turn.",
        "labels": {"valuable": "Valuable", "rare": "Rare",
                   "costly_to_imitate": "Costly to imitate",
                   "organized": "Organised to capture value"},
        "grids": [{"rows": [["valuable", "rare", "costly_to_imitate", "organized"]],
                   "col_widths": [0.25, 0.25, 0.25, 0.25]}],
    },
    "template_mckinsey_7s": {
        "kind": "hub",
        "caption": "McKinsey 7S alignment",
        "note": "Shared values hold the other six elements together.",
        "labels": {"strategy": "Strategy", "structure": "Structure", "systems": "Systems",
                   "shared_values": "Shared values", "staff": "Staff", "skills": "Skills",
                   "style": "Style"},
        "grids": [{"rows": [["strategy", "structure", "systems"],
                            [{"key": "shared_values", "span": 3, "role": "hub"}],
                            ["staff", "skills", "style"]],
                   "col_widths": [0.3333, 0.3333, 0.3334]}],
    },
    "template_bcg": {
        "kind": "quadrant",
        "caption": "BCG growth-share matrix",
        "note": "Each cell holds the evidence for one portfolio position.",
        "labels": {"stars": "Stars", "question_marks": "Question marks",
                   "cash_cows": "Cash cows", "dogs": "Dogs"},
        "grids": [{"rows": [["stars", "question_marks"], ["cash_cows", "dogs"]],
                   "axis_x": ("Strong market share", "Low market share"),
                   "axis_y": ("Low industry growth", "High industry growth"),
                   "col_widths": [0.5, 0.5]}],
    },
    "template_ge_mckinsey": {
        "kind": "quadrant",
        "caption": "GE/McKinsey matrix",
        "note": "Each cell holds the evidence for one strategic position.",
        "labels": {"high_high": "High/High", "high_medium": "High/Medium",
                   "high_low": "High/Low", "medium_high": "Medium/High",
                   "medium_medium": "Medium/Medium", "medium_low": "Medium/Low",
                   "low_high": "Low/High", "low_medium": "Low/Medium",
                   "low_low": "Low/Low"},
        "grids": [{"rows": [["high_high", "high_medium", "high_low"],
                            ["medium_high", "medium_medium", "medium_low"],
                            ["low_high", "low_medium", "low_low"]],
                   "axis_x": ("Low competitive strength", "High competitive strength"),
                   "axis_y": ("Low business attractiveness", "High business attractiveness"),
                   "col_widths": [0.3333, 0.3333, 0.3334]}],
    },
    "template_blue_ocean_errc": {
        "kind": "columns",
        "caption": "Blue Ocean four actions (ERRC)",
        "note": "Eliminate, reduce, raise and create are read from left to right.",
        "labels": {"eliminate": "Eliminate", "reduce": "Reduce",
                   "raise": "Raise", "create": "Create"},
        "grids": [{"rows": [["eliminate", "reduce", "raise", "create"]],
                   "col_widths": [0.25, 0.25, 0.25, 0.25]}],
    },
    "template_generic_strategies": {
        "kind": "quadrant",
        "caption": "Porter's generic strategies",
        "note": "Each cell holds the evidence for one generic strategy.",
        "labels": {"low_cost": "Low-Cost",
                   "differentiation": "Differentiation",
                   "focus_low_cost": "Focused Low-Cost",
                   "focus_differentiation": "Focused Differentiation"},
        "grids": [{"rows": [["low_cost", "differentiation"],
                            ["focus_low_cost", "focus_differentiation"]],
                   "axis_x": ("Cost advantage", "Differentiation advantage"),
                   "axis_y": ("Narrow target", "Broad target"),
                   "col_widths": [0.5, 0.5]}],
    },
    "template_porters_diamond": {
        "kind": "quadrant",
        "caption": "Porter's Diamond",
        "note": "The four determinants are read together; government and chance "
                "act on all of them.",
        "labels": {"factor_conditions": "Factor Conditions",
                   "demand_conditions": "Demand Conditions",
                   "related_industries": "Related and Supporting Industries",
                   "firm_strategy": "Firm Strategy, Structure and Rivalry",
                   "government": "Government",
                   "chance": "Chance"},
        "grids": [
            {"title": "Determinants of national advantage",
             "rows": [["demand_conditions", "firm_strategy"],
                      ["factor_conditions", "related_industries"]],
             "col_widths": [0.5, 0.5]},
            {"title": "Influences on the diamond",
             "rows": [["government", "chance"]],
             "col_widths": [0.5, 0.5]},
        ],
    },
    "template_raci": {
        "kind": "columns",
        "caption": "RACI responsibility matrix",
        "note": "Responsible, accountable, consulted and informed are the four "
                "roles assigned to each task.",
        "labels": {"responsible": "Responsible", "accountable": "Accountable",
                   "consulted": "Consulted", "informed": "Informed"},
        "grids": [{"rows": [["responsible", "accountable", "consulted", "informed"]],
                   "col_widths": [0.25, 0.25, 0.25, 0.25]}],
    },
}

#: The chat names the same cells with its own words.  Both names find the cell.
#: A mapping is ``{alias_key: block_key}``; the builder tries both directions.
ALIASES = {
    "template_swot": {"strengths": "S", "weaknesses": "W",
                      "opportunities": "O", "threats": "T"},
    "template_ansoff": {"penetration": "market_penetration",
                        "development": "market_development",
                        "product": "product_development",
                        "diversification": "diversification"},
    "template_vrio": {"costly": "costly_to_imitate",
                      "costly_to_imitate": "costly_to_imitate",
                      "organised": "organized"},
}


def layout_for(template):
    """The layout of a template, or None when the template has no grid."""
    return LAYOUTS.get(str(template or ""))


def _source_for(template, key, cells):
    """The caller's cell for a layout key, following the alias map either way."""
    cells = cells or {}
    if key in cells:
        return cells[key]
    aliases = ALIASES.get(str(template or ""), {})
    for alias_key, block_key in aliases.items():
        if block_key == key and alias_key in cells:
            return cells[alias_key]
    return {}


def build(template, cells, caption=None):
    """The figure for a template, or None when the template has no grid.

    ``cells`` maps a block key to ``{"label", "bullets", "gap"}``.  A cell the
    caller did not supply is drawn with its own label and no content, which the
    renderer shows as the framework's own gap - never as an empty box.
    """
    layout = layout_for(template)
    if not layout:
        return None
    labels = layout.get("labels") or {}
    grids = []
    for grid in layout.get("grids") or []:
        rows = []
        for row in grid.get("rows") or []:
            built = []
            for entry in row:
                if isinstance(entry, dict):
                    key = entry.get("key")
                    span = int(entry.get("span") or 1)
                    role = entry.get("role") or "body"
                else:
                    key = entry
                    span = 1
                    role = "body"
                source = _source_for(template, key, cells)
                built.append({
                    "label": str(source.get("label") or labels.get(key) or key),
                    "bullets": [str(bullet) for bullet in source.get("bullets") or []],
                    "gap": source.get("gap"),
                    "span": span,
                    "role": role,
                    "vmerge": None,
                })
            rows.append(built)
        grids.append({
            "title": grid.get("title"),
            "rows": rows,
            "axis_x": grid.get("axis_x"),
            "axis_y": grid.get("axis_y"),
            "col_widths": grid.get("col_widths"),
        })
    return {"kind": layout.get("kind"),
            "caption": caption or layout.get("caption"),
            "note": layout.get("note"),
            "grids": grids}
