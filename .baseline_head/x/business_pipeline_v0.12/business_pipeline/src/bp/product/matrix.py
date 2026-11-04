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
    # ---- Operations management (session 8, owner instruction 2026-11-03) ---------
    # Eleven grids for the eleven operations worksheets.  The geometry is data and
    # the builder writes no content: a cell carries the block's accepted items or
    # the gap the paper already names, so a figure adds no number and no evidence.
    "template_scor": {
        "kind": "chain",
        "caption": "SCOR supply-chain map",
        "note": "Plan and enable govern the four processes the goods pass through.",
        "labels": {"plan": "Plan", "source": "Source", "make": "Make",
                   "deliver": "Deliver", "return": "Return", "enable": "Enable"},
        "grids": [
            {"title": "Plan and enable",
             "rows": [["plan", "enable"]], "col_widths": [0.5, 0.5]},
            {"title": "The processes the goods pass through",
             "rows": [["source", "make", "deliver", "return"]],
             "col_widths": [0.25, 0.25, 0.25, 0.25]},
        ],
    },
    "template_sipoc": {
        "kind": "chain",
        "caption": "SIPOC process map",
        "note": "The boundary runs left to right: what enters, what happens, what leaves.",
        "labels": {"suppliers": "Suppliers", "inputs": "Inputs", "process": "Process steps",
                   "outputs": "Outputs", "customers": "Customers"},
        "grids": [{"rows": [["suppliers", "inputs", "process", "outputs", "customers"]],
                   "col_widths": [0.2, 0.2, 0.2, 0.2, 0.2]}],
    },
    "template_value_stream_map": {
        "kind": "columns",
        "caption": "Value stream map",
        "note": "The flow and its times, what waits, then the judgement and the change.",
        "labels": {"process_steps": "Process steps",
                   "cycle_and_lead_times": "Cycle and lead times",
                   "inventory_wip": "Inventory and work in progress",
                   "waits_delays": "Waits and delays",
                   "value_added": "Value-added assessment",
                   "improvements": "Improvement opportunities"},
        "grids": [
            {"title": "The flow and its times",
             "rows": [["process_steps", "cycle_and_lead_times"]], "col_widths": [0.5, 0.5]},
            {"title": "What waits, and where the flow stops",
             "rows": [["inventory_wip", "waits_delays"]], "col_widths": [0.5, 0.5]},
            {"title": "The judgement and the change",
             "rows": [["value_added", "improvements"]], "col_widths": [0.5, 0.5]},
        ],
    },
    "template_5s": {
        "kind": "columns",
        "caption": "5S workplace audit",
        "note": "The five S are read in order; each rests on the one before it.",
        "labels": {"sort": "Sort", "set_in_order": "Set in order", "shine": "Shine",
                   "standardize": "Standardize", "sustain": "Sustain"},
        "grids": [{"rows": [["sort", "set_in_order", "shine", "standardize", "sustain"]],
                   "col_widths": [0.2, 0.2, 0.2, 0.2, 0.2]}],
    },
    "template_a3": {
        "kind": "columns",
        "caption": "A3 problem solving",
        "note": "The left column states the gap; the right column answers it.",
        "labels": {"problem": "Problem", "current_condition": "Current condition",
                   "target": "Target condition", "causes": "Root causes",
                   "countermeasures": "Countermeasures", "plan": "Plan and owners",
                   "follow_up": "Follow-up"},
        "grids": [{"rows": [["problem", "causes"],
                            ["current_condition", "countermeasures"],
                            ["target", "plan"],
                            [{"key": "follow_up", "span": 2}]]}],
    },
    "template_toc": {
        "kind": "columns",
        "caption": "Theory of Constraints",
        "note": "The five focusing steps are applied in order to one constraint.",
        "labels": {"identify": "Identify the constraint", "exploit": "Exploit the constraint",
                   "subordinate": "Subordinate everything else", "elevate": "Elevate the constraint",
                   "reassess": "Reassess"},
        "grids": [{"rows": [["identify", "exploit", "subordinate", "elevate", "reassess"]],
                   "col_widths": [0.2, 0.2, 0.2, 0.2, 0.2]}],
    },
    "template_root_cause": {
        "kind": "columns",
        "caption": "Root cause analysis",
        "note": "Candidate causes are gathered by category; the root cause is the one the "
                "evidence supports.",
        "labels": {"problem": "Problem", "people": "People", "process": "Process / method",
                   "equipment": "Equipment", "materials": "Materials",
                   "measurement": "Measurement", "environment": "Environment",
                   "root_cause": "Root cause"},
        "grids": [
            {"title": "The effect", "rows": [["problem"]]},
            {"title": "Candidate causes, by category",
             "rows": [["people", "process", "equipment"],
                      ["materials", "measurement", "environment"]],
             "col_widths": [0.3333, 0.3333, 0.3334]},
            {"title": "The cause the evidence supports", "rows": [["root_cause"]]},
        ],
    },
    "template_fmea": {
        "kind": "columns",
        "caption": "Failure mode and effects analysis",
        "note": "Each failure mode is read across to its effect, cause, control and action; "
                "no risk priority number is computed.",
        "labels": {"failure_modes": "Failure modes", "effects": "Effects", "causes": "Causes",
                   "controls": "Current controls", "actions": "Recommended actions",
                   "owners": "Owners and review"},
        "grids": [{"rows": [["failure_modes", "effects", "causes"],
                            ["controls", "actions", "owners"]],
                   "col_widths": [0.3333, 0.3333, 0.3334]}],
    },
    "template_kraljic": {
        "kind": "quadrant",
        "caption": "Kraljic purchasing portfolio",
        "note": "Each item is placed by its profit impact and its supply risk.",
        "labels": {"criteria": "Criteria", "strategic": "Strategic items",
                   "leverage": "Leverage items", "bottleneck": "Bottleneck items",
                   "non_critical": "Non-critical items"},
        "grids": [
            {"title": "How the axes are judged", "rows": [["criteria"]]},
            {"rows": [["leverage", "strategic"], ["non_critical", "bottleneck"]],
             "axis_x": ("Low supply risk", "High supply risk"),
             "axis_y": ("Low profit impact", "High profit impact"),
             "col_widths": [0.5, 0.5]},
        ],
    },
    "template_sop": {
        "kind": "columns",
        "caption": "Sales and operations plan",
        "note": "The plans are read side by side; the last cell records where they disagree.",
        "labels": {"demand_plan": "Demand plan", "supply_plan": "Supply plan",
                   "inventory_plan": "Inventory plan", "capacity_plan": "Capacity plan",
                   "financial_plan": "Financial plan", "decisions": "Gaps and decisions"},
        "grids": [{"rows": [["demand_plan", "supply_plan"],
                            ["inventory_plan", "capacity_plan"],
                            ["financial_plan", "decisions"]],
                   "col_widths": [0.5, 0.5]}],
    },
    "template_pdca": {
        "kind": "columns",
        "caption": "PDCA improvement cycle",
        "note": "Plan, do, check and act are one cycle: the act decides the next one.",
        "labels": {"plan": "Plan", "do": "Do", "check": "Check", "act": "Act"},
        "grids": [{"rows": [["plan", "do", "check", "act"]],
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
    # Porter's nine activities: the profile (and the worksheet form) name the blocks
    # in full, the chain layout names the nine bands in short.  Without this map the
    # figure looked each short key up in the completion's cells, found nothing, and
    # drew nine evidence boxes with no bullet and no gap in them.
    "template_value_chain": {"firm_infrastructure": "infrastructure",
                             "human_resource_management": "human",
                             "technology_development": "technology",
                             "procurement": "procurement",
                             "inbound_logistics": "inbound",
                             "operations": "operations",
                             "outbound_logistics": "outbound",
                             "marketing_and_sales": "marketing",
                             "service": "service"},
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
