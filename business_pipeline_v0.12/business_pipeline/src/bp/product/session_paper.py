"""The paper for one delivered computation (product layer, standard library only).

Every delivered result already carries a report and an appendix.  This module turns exactly
that record into a downloadable paper: the same sentences, the same honesty block, the same
assumptions, limitations and checks, and the same specification hash.  It computes nothing and
adds no sentence the screen does not show.

The one addition is the **declared-sources** list (B-182): the student's own citations, listed
in their own section, labelled as not evidence.  They are never merged into the references of
retrieved evidence, because the paper's evidence claim is about what the system retrieved.
"""

FORMAT = "bp-paper/1"

#: Said in prose, not only in the heading, so a reader who skims the citations still sees it.
DECLARED_LEAD = ("These are the sources you declared. They are your citations, this system has not "
                 "verified them, and they are not evidence: a part of the paper with no retrieved "
                 "evidence still names that gap.")

#: How each heading is written.  The order is the reading order of the paper.
HEADINGS = (("report", "Result"), ("figures", "Inputs and results"),
            ("honesty", "Honesty: what was not done"),
            ("assumptions", "Assumptions made"), ("limitations", "Limitations"),
            ("declared", "Sources you declared (not evidence)"),
            ("checks", "How the figures were checked"))


def _plain(name):
    """A machine name as a readable phrase: `arc_elasticity_equals_percentage_changes`."""
    text = str(name or "").replace("_", " ").strip()
    return (text[:1].upper() + text[1:]) if text else ""


def _render(key, value, method):
    """One figure as a reader can use it: the core's declared precision, no Python repr."""
    from decimal import Decimal, InvalidOperation
    if isinstance(value, (list, tuple)):
        return "%s: %s" % (_plain(key), ", ".join(str(item) for item in value))
    unit = precision = None
    if method is not None and getattr(method, "typing", None):
        try:
            unit, precision = method.typing(key)
        except Exception:                                   # noqa: BLE001
            unit = precision = None
    text = str(value)
    if precision is not None:
        try:
            quantum = Decimal(1).scaleb(-int(precision))
            text = format(Decimal(text).quantize(quantum), "f")
        except (InvalidOperation, ValueError, TypeError):
            text = str(value)
    return "%s: %s" % (_plain(key), text)


def _figure_lines(appendix):
    """The inputs and outputs as readable lines, at the method's own declared precision."""
    from ..methods import LIBRARY
    record = (appendix or {}).get("reperform") or {}
    method_id = ((appendix or {}).get("method") or {}).get("id")
    method = LIBRARY.get(method_id) if method_id else None
    lines = []
    inputs = record.get("inputs") or {}
    if isinstance(inputs, dict) and inputs:
        lines.append("What you declared")
        lines.extend(_render(key, value, method) for key, value in inputs.items())
    outputs = record.get("outputs") or {}
    if isinstance(outputs, dict) and outputs:
        if lines:
            lines.append("")
        lines.append("What was computed")
        lines.extend(_render(key, value, method) for key, value in outputs.items())
    return lines



def title_for(delivery, fallback="Business computation"):
    appendix = (delivery or {}).get("appendix") or {}
    method = (appendix.get("method") or {})
    label = method.get("id") or ""
    return ("Computation: " + label.replace("_", " ")) if label else fallback


def _lines(value):
    if isinstance(value, str):
        return [line for line in value.splitlines() if line.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if str(item).strip()]
    return []


def sections(delivery, declared_sources=None, title=None):
    """[(heading, [lines]), ...] for the paper, in reading order.

    `declared_sources` is the student's own citation list (B-182).  It is placed after the
    limitations and before the checks so that it reads as their bibliography, and its heading
    says what it is: not evidence.
    """
    delivery = delivery or {}
    appendix = delivery.get("appendix") or {}
    body = {"report": _lines(delivery.get("report")),
            "figures": _figure_lines(appendix),
            "honesty": [("%s: %s" % (key.replace("_", " "), value))
                        for key, value in (appendix.get("honesty") or {}).items() if value],
            "assumptions": _lines(appendix.get("assumptions")),
            "limitations": _lines(appendix.get("limitations")),
            "declared": ([DECLARED_LEAD] + _lines(declared_sources)) if _lines(declared_sources) else [],
            "checks": [_plain(name) + "." for name in _lines(appendix.get("tests"))]}
    out = []
    for key, heading in HEADINGS:
        if body[key]:
            out.append((heading, body[key]))
    # The audit block (method, version, specification hash) was DELETED from the paper at
    # the owner's instruction: a student's paper must not carry a specification footer.
    # The record itself still exists in the store and every figure remains re-runnable
    # from it; the paper simply no longer prints the identifier.
    return out


def markdown(delivery, declared_sources=None, title=None):
    """The paper as Markdown, for the reader who wants the text."""
    name = title or title_for(delivery)
    parts = ["# " + name, ""]
    for heading, lines in sections(delivery, declared_sources, name):
        parts.append("## " + heading)
        parts.append("")
        parts.extend(lines)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def docx_bytes(delivery, declared_sources=None, title=None):
    """The paper as Word bytes, through the repository's own stdlib .docx writer."""
    from . import docx
    name = title or title_for(delivery)
    return docx.render_bytes(name, sections(delivery, declared_sources, name))


def xlsx_bytes(delivery, declared_sources=None, title=None, session_id=None):
    """The same record as a workbook: what you declared, what was computed, the checks.

    Every cell is copied from the stored delivery; nothing is recomputed here.
    """
    from . import spreadsheets
    appendix = (delivery or {}).get("appendix") or {}
    method = appendix.get("method") or {}
    bundle = {"id": session_id, "title": title or title_for(delivery),
              "method": method.get("id"), "tier": (delivery or {}).get("tier"),
              "spec_hash": appendix.get("spec_hash"),
              "created_at": appendix.get("run_id") or "",
              "delivery": delivery, "artifacts": appendix.get("artifacts")}
    if declared_sources:
        bundle["declared_sources"] = list(declared_sources)
    return spreadsheets.to_xlsx(bundle)


def filename(delivery, fmt, title=None):
    """A readable download name; never an id."""
    stem = (title or title_for(delivery)).strip() or "computation"
    safe = "".join(char if char.isalnum() or char in " -_" else " " for char in stem)
    safe = " ".join(safe.split())[:90] or "computation"
    return safe + (".xlsx" if fmt == "xlsx" else ".docx")
