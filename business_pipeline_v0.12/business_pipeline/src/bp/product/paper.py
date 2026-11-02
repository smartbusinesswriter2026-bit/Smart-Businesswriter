"""Paper structure and the export gate (product layer).

The chat owns the paper plan; this module gives it a small, explicit shape:
sections carry a heading level, so a framework is level 1 and its dimensions are
level 2.  It also defines what must be present before a Word file may leave the
system, so a submitted paper never contains template instructions.
"""

from . import capabilities

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


def section(heading, level, lines=None, figure=None):
    return {"heading": heading, "level": level, "lines": list(lines or []),
            "figure": figure or None}


def figure_text(figure):
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
    return " ".join(part for part in parts if part)


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
    base = _missing_base(state, implications)
    # A figure that no longer reproduces from its own inputs or a sentence that
    # claims more than a method licenses blocks export.
    return list(base) + list(state.get("recompute_problems") or []) \
        + list(state.get("claim_problems") or []) + _rubric_missing(state)


def rubric_gate_on(state):
    """The rubric gate is on unless the student turned it off for this paper."""
    return (state or {}).get("rubric_gate", True) is not False


def _rubric_coverage(state):
    coverage = (state or {}).get("rubric")
    return coverage if isinstance(coverage, dict) else None


def _rubric_missing(state):
    """The criteria a rubric states that the paper does not address.

    A criterion the rubric weights is the document's own statement of what must be
    present, so leaving it out blocks export until the student writes it — or turns
    the gate off, which demotes every row to a warning and is recorded.  Nothing
    here fills the gap: the student writes it, the system only refuses to call the
    paper finished.
    """
    coverage = _rubric_coverage(state)
    if not coverage or not rubric_gate_on(state):
        return []
    return ["the '" + str(name) + "' criterion your rubric states"
            for name in coverage.get("blocking") or []]


def _missing_base(state, implications=""):
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
    recorded = state.get("computations") or {}
    for row in (state.get("selection") or {}).get("selected") or []:
        data = recorded.get(row.get("key")) or {}
        if not data.get("ok"):
            required.append("the " + str(row.get("label") or row.get("key")).lower() + " figures")
    # Legacy: a case saved before capabilities carries `computation` and no selection.
    attached = state.get("computation") or {}
    if attached.get("key") and not (attached.get("inputs") or {}):
        try:
            label = capabilities.entry(attached["key"])["label"].lower()
        except KeyError:
            label = str(attached["key"]).replace("_", " ")
        required.append("the " + label + " inputs")
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


def rubric_section(coverage):
    """The mechanical coverage table: what the rubric asked for, and what the paper does.

    Shared by both paper paths — a completed worksheet and a conducted paper — so the
    same coverage table is printed (and read) the same way whichever route produced
    the paper.  Nothing here marks the paper or awards a score.
    """
    rows = coverage.get("criteria") or []
    lines = ["Your rubric states %d assessment %s. This table records whether each one is "
             "present in the paper above. It does not mark the paper and no score is given."
             % (len(rows), "criterion" if len(rows) == 1 else "criteria")]
    for row in rows:
        weight = (" (" + str(row["weight_text"]) + ")") if row.get("weight_text") else ""
        if row["status"] == "addressed":
            where = row.get("where") or []
            lines.append("• " + str(row["name"]) + weight + ": addressed in "
                         + (", ".join(where) if where else "the paper") + ".")
        elif row["status"] == "partially":
            lines.append("• " + str(row["name"]) + weight + ": partly addressed — "
                         + (row.get("note") or "the section is present but an element it asks for "
                                               "is not stated") + ".")
        else:
            lines.append("• " + str(row["name"]) + weight + ": not addressed by this paper. "
                         "Treat this as a gap you still have to write.")
    if coverage.get("gaps"):
        lines.append("The gaps named above are reported, not filled: this system does not write "
                     "the missing analysis for you.")
    return section("Rubric coverage", H1, lines)


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
    texts = []
    for item in sections:
        texts.append(" ".join(item.get("lines") or []))
        texts.append(figure_text(item.get("figure")))
    texts = " ".join(texts).lower()
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
    coverage = _rubric_coverage(target)
    if coverage:
        gate_on = rubric_gate_on(target)
        blocking = set(coverage.get("blocking") or [])
        for name in coverage.get("gaps") or []:
            if gate_on and name in blocking:
                continue  # already reported as required before export, by missing()
            issues.append({"type": "rubric_criterion_gap", "severity": "medium",
                           "detail": "Your rubric's '%s' criterion is not addressed by this "
                                     "paper." % name})
    return {"pass": not any(issue["severity"] == "high" for issue in issues), "issues": issues}
