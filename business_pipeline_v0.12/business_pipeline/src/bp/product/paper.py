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
    return required


def check(sections, framework="pestel", implications="", answers=None):
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
    required = missing({"framework": framework, "answers": answers or {}}, implications)
    for item in required:
        issues.append({"type": "missing_input", "severity": "high",
                       "detail": "Required before export: %s." % item})
    return {"pass": not any(issue["severity"] == "high" for issue in issues), "issues": issues}
