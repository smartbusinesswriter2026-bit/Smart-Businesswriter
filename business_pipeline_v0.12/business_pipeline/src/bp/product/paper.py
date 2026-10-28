"""Paper structure and the export gate (product layer).

The chat owns the paper plan; this module gives it a small, explicit shape:
sections carry a heading level, so a framework is level 1 and its dimensions are
level 2.  It also defines what must be present before a Word file may leave the
system, so a submitted paper never contains template instructions.
"""

H1, H2, H3 = 1, 2, 3

META = (
    "(your analysis)", "not supplied yet", "add your implications before submitting",
    "the system does not infer", "[your name]", "[your institution]",
)


class ExportBlocked(ValueError):
    """The paper is not complete enough to export, and says what is missing."""

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__("Export blocked: " + "; ".join(self.missing))


def section(heading, level, lines=None):
    return {"heading": heading, "level": level, "lines": list(lines or [])}


def paragraph(lines):
    """Join section lines into one paragraph, dropping bullet markers."""
    parts = []
    for line in lines or []:
        text = str(line or "").strip().lstrip("•-").strip()
        if text:
            parts.append(text)
    return " ".join(parts)


def flatten(sections):
    """The legacy [heading, lines] view used by the existing chat UI."""
    return [[item["heading"], item["lines"]] for item in sections]


def missing(state, implications=""):
    """What must be supplied before export.  Evidence gaps are not blockers."""
    if state.get("profile") == "business_plan":
        return _plan_missing(state)
    answers = state.get("answers") or {}
    framework = state.get("framework") or "pestel"
    required = []
    if not str(implications or "").strip():
        required.append("implications")
    if framework in ("swot", "pestel_swot"):
        if not (answers.get("strengths") or []):
            required.append("at least one strength")
        if not (answers.get("weaknesses") or []):
            required.append("at least one weakness")
    if framework == "vrio":
        if not (answers.get("resources") or []):
            required.append("at least one resource")
        if not (answers.get("valuable") or []):
            required.append("at least one value judgment")
    attached = state.get("computation") or {}
    if attached.get("key") == "breakeven":
        inputs = attached.get("inputs") or {}
        if not all(str(inputs.get(name, "")).strip() for name in ("fixed", "price", "variable")):
            required.append("the break-even inputs")
    return required


def _plan_missing(state):
    """A business plan needs its student fields and every required block.

    A computation that refused is named with its reason, so an unbalanced
    opening balance sheet or a loan repaid faster than it is owed blocks export
    instead of being hidden.
    """
    plan = state.get("plan") or {}
    supplied = (state.get("answers") or {}).get("inputs") or {}
    required = []
    for field in plan.get("fields") or []:
        if field.get("required") and not supplied.get(field.get("key")):
            required.append(field.get("label") or field.get("key"))
    results = state.get("computations") or {}
    for block in plan.get("blocks") or []:
        if not block.get("required"):
            continue
        data = results.get(block.get("key"))
        if not data:
            required.append("the " + str(block.get("label") or block.get("key")).lower() + " computation")
        elif not data.get("ok"):
            required.append(str(block.get("label") or block.get("key")) + ": " +
                             str(data.get("error") or "the computation did not run"))
    return required


def check(sections, framework="pestel", implications="", answers=None, state=None):
    """Structural coherence checks.  Returns high/medium/low issues."""
    issues = []
    seen_h1 = False
    previous_level = 0
    for item in sections:
        level = item.get("level", 1)
        if level > previous_level + 1:
            issues.append({"type": "heading_jump", "severity": "high",
                           "detail": "%s jumps from level %d to %d." % (item.get("heading"), previous_level, level)})
        if level == 1:
            seen_h1 = True
        elif not seen_h1:
            issues.append({"type": "heading_before_h1", "severity": "high",
                           "detail": "%s appears before any level 1 heading." % item.get("heading")})
        previous_level = level
    texts = " ".join(" ".join(item.get("lines") or []) for item in sections).lower()
    for phrase in META:
        if phrase in texts:
            issues.append({"type": "meta_text", "severity": "high",
                           "detail": "Instructional text remains in the paper: %r." % phrase})
    if not any(item.get("heading") == "Conclusion" for item in sections):
        issues.append({"type": "missing_conclusion", "severity": "high",
                       "detail": "The paper has no Conclusion."})
    if not any(item.get("heading") in ("References", "Bibliography") for item in sections):
        issues.append({"type": "missing_references", "severity": "high",
                       "detail": "The paper has no reference list."})
    target = state if isinstance(state, dict) else {"framework": framework, "answers": answers or {}}
    required = missing(target, implications)
    for item in required:
        issues.append({"type": "missing_input", "severity": "high",
                       "detail": "Required before export: %s." % item})
    return {"pass": not any(issue["severity"] == "high" for issue in issues), "issues": issues}
