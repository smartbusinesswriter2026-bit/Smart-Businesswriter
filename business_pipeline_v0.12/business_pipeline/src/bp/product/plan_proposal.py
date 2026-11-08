"""A typed plan proposal shown before the student confirms the plan.

The proposal is a reading, not a repetition of the brief.  It says what the
pipeline thinks the instruction asks, which framework(s) fit, which
computations are available, what the paper could argue, what evidence is
needed, and what is missing.

Nothing here computes, retrieves or writes prose.  It only assembles a
proposal from closed registries so the student can accept, refine or change it.
"""

from __future__ import annotations

import re

from . import capabilities, instruction_reading, paper_families

FORMAT = "bp-plan-proposal/1"

STOP = set(
    "a an the and or of to in on for with by at from as is are was were be been it its this that these those "
    "we our us you your i my me they their them not no do does did can could should would will may might have "
    "has had how what when where which who why if then than so such about into over under between among after "
    "before during each per via also more most much many some any other another own same very".split()
)


def _words(text):
    return [word for word in re.findall(r"[a-z][a-z0-9'-]+", (text or "").lower())
            if len(word) > 2 and word not in STOP]


def _scope_terms(brief):
    return sorted(set(_words(brief)))


def _numbers(brief):
    return set(re.findall(r"\d+(?:[.,]\d+)?", brief or ""))


def _framework_options(choices, reading):
    selected = set(reading.selected)
    options = []
    for key, label in choices:
        options.append({
            "id": key,
            "label": label,
            "suggested": key in selected or (key == "none" and not selected),
            "role": instruction_reading.FRAMEWORK_ROLES.get(key, "none"),
        })
    return options


def _business_plan_brief(brief):
    """A business plan states its own tables: the plan service computes them, not a lone block."""
    try:
        from . import declared
        return declared.is_business_plan(brief)
    except Exception:
        # A reader failure must not turn a plan brief into a framework paper.
        return False


def _business_plan_computation():
    row = capabilities.ENTRIES.get("business_plan")
    if not row:
        return []
    return [{
        "key": "business_plan",
        "label": row.get("label") or "Business plan financials",
        "why": ("the brief declares a startup budget, its funding and a revenue driver; "
                "the plan computes them in the guide's order"),
        "needs": row.get("slot") or [],
        "licenses": row.get("licenses") or "",
    }]


def _computations(brief, framework, limit=3):
    rows = []
    for key, row in capabilities.ENTRIES.items():
        if _business_plan_brief(brief) and key in ("breakeven", "startup_capital", "cash_runway"):
            # The business plan's financial plan supersedes a single break-even block.
            continue
        for cue in row.get("any_of") or []:
            try:
                if re.search(cue, brief, re.I):
                    if framework and framework != "none" and row.get("applies_to") and framework not in row["applies_to"]:
                        break
                    rows.append({
                        "key": key,
                        "label": row.get("label") or key,
                        "why": "the brief contains the cue: " + cue,
                        "needs": row.get("slot") or [],
                        "licenses": row.get("licenses") or "",
                    })
                    break
            except re.error:
                continue
    return rows[:limit]


def _decision_from_brief(brief):
    text = str(brief or "").strip()
    match = re.search(r"objective\s*:\s*(.+?)(?=\s+(?:inputs?|analy[sz]e|validation|output)\s*:|$)", text, re.I | re.S)
    if match:
        text = match.group(1).strip()
    else:
        text = re.split(r"(?<=[.?!])\s+|\n", text, maxsplit=1)[0]
    text = text.split("\n", 1)[0].strip()
    # The objective sentence often continues with a handling instruction
    # ("Treat ...", "Use ...", "Do not ...").  That is not the decision.
    text = re.split(r"\b(?:Treat|Use|Do not|Ensure|Label|Analy[sz]e|Output)\b", text, maxsplit=1)[0].strip()
    return text[:300].rstrip(" .?!")


def _claims(decision, framework, business_plan=False):
    if business_plan:
        return [
            {"text": "The plan will show whether the declared funding covers the startup cost "
                     "and whether cash survives the first year.", "status": "proposed",
             "support": "the case's own tables"},
            {"text": "Every figure comes from the case's tables; a figure the case does not state "
                     "is named as a gap, not filled.", "status": "proposed",
             "support": "the plan reader and the frozen core"},
        ]
    text = "The paper will assess: " + _decision_from_brief(decision or "the instruction") + "."
    conditional = {
        "five_forces": "If rivalry and entry barriers are high, the paper can argue that entry is unattractive.",
        "pestel": "If the external conditions are adverse, the paper can argue for delay or a narrower entry.",
        "swot": "If internal weaknesses outweigh the external opportunities, the paper can argue against the action.",
        "ansoff": "If market development exposes less capital than diversification, the paper can argue for market development.",
        "value_chain": "If the costliest activities are not the value-creating ones, the paper can argue for a targeted cost programme.",
        "vrio": "If the resource fails one of the VRIO tests, the paper can argue that the advantage is not durable.",
        "breakeven": "If the declared volume is below break-even, the paper can argue that the price or cost structure must change.",
        "none": "The paper can argue from the evidence without imposing a framework.",
    }
    return [
        {"text": text, "status": "proposed", "support": "student-approved decision"},
        {"text": conditional.get(framework or "none", "The claim will be stated after the evidence is reviewed."),
         "status": "proposed_conditional", "support": "requires evidence"},
    ]


def _structure(archetype, brief=""):
    if _business_plan_brief(brief):
        # The uploaded generation guide's Part 13 skeleton is the structure of a
        # business plan, so the paper follows the template the owner supplied.
        from . import plan_schema
        return list(plan_schema.SECTIONS)
    row = paper_families.archetype(archetype or "analytical_report") or {}
    return list(row.get("required_sections") or [])


def build(brief, reading, slots, archetype, framework, choices, answers=None,
          business_plan=None):
    """Build the proposal dict stored on the chat state."""
    answers = answers or {}
    decision = _decision_from_brief(answers.get("decision") or brief)
    selected = list(reading.selected)
    if business_plan is None:
        business_plan = _business_plan_brief(brief)
    if business_plan:
        # A plan is a template with its own sections, not a framework paper.  The
        # candidate never sees a framework question it does not need.
        framework = "none"
    framework = framework or (selected[0] if selected else None)
    computations = (_business_plan_computation() if business_plan
                    else _computations(brief, framework))
    evidence = []
    if framework and framework != "none":
        from . import chat as chat_module
        config = chat_module.FRAMEWORKS.get(framework) or {}
        for key, label, cues, category in config.get("dimensions") or []:
            evidence.append({"key": key, "label": label, "category": category})
    if not evidence:
        evidence = [{"key": "evidence", "label": "Evidence", "category": None}]
    scope = {
        "terms": _scope_terms(brief),
        "numbers": sorted(_numbers(brief)),
        "geography": answers.get("geography") or "Global",
        "period": answers.get("period") or "10",
    }
    gaps = []
    if not business_plan and not computations:
        gaps.append("No computation cue was found; the paper may be framework-only.")
    return {
        "format": FORMAT,
        "paper": "business_plan" if business_plan else "paper",
        "framework_required": False,
        "reading": {
            "decision": decision,
            "intent": "paper",
            "framework_mentions": [{"id": m.framework_id, "role": m.role} for m in reading.mentions],
            "status": reading.status,
            "slots": [{"name": s.name, "value": s.value, "kind": s.kind, "status": s.status} for s in slots],
        },
        "framework_options": _framework_options(choices, reading),
        "selected_framework": framework,
        "computations": computations,
        "claims": _claims(decision, framework, business_plan),
        "evidence_needs": evidence,
        "structure": _structure(archetype, brief),
        "gaps": gaps,
        "scope": scope,
        "guard": {
            "no_new_entities_outside_brief": True,
            "no_new_numbers": True,
            "closed_frameworks": True,
            "closed_computations": True,
        },
    }


def guard_edit(proposal, changes, brief):
    """Check a proposed edit.  Returns a list of problems; empty means allowed."""
    problems = []
    if not isinstance(changes, dict):
        return ["the edit must be an object"]
    brief_numbers = set(re.findall(r"\d+(?:[.,]\d+)?", brief or ""))
    text = str(changes.get("text") or "")
    if text:
        for number in re.findall(r"\d+(?:[.,]\d+)?", text):
            if number not in brief_numbers:
                problems.append("the number " + number + " is not in your brief; declare it as an input instead of adding it in an edit")
        reading = instruction_reading.read_frameworks(text)
        allowed_frameworks = {row["id"] for row in (proposal or {}).get("framework_options") or []}
        for mention in reading.mentions:
            if mention.framework_id not in allowed_frameworks:
                problems.append("the framework " + mention.framework_id + " is outside the proposed options")
    framework = changes.get("framework")
    if framework is not None:
        allowed = {row["id"] for row in (proposal or {}).get("framework_options") or []}
        if framework not in allowed:
            problems.append("the framework " + str(framework) + " is not one of the proposed options")
    return problems
