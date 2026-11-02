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
HEADINGS = (("report", "Result"), ("honesty", "Honesty: what was not done"),
            ("assumptions", "Assumptions (as recorded)"), ("limitations", "Limitations (as recorded)"),
            ("declared", "Sources you declared (not evidence)"), ("checks", "Checks recorded"))


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
            "honesty": [("%s: %s" % (key.replace("_", " "), value))
                        for key, value in (appendix.get("honesty") or {}).items() if value],
            "assumptions": _lines(appendix.get("assumptions")),
            "limitations": _lines(appendix.get("limitations")),
            "declared": ([DECLARED_LEAD] + _lines(declared_sources)) if _lines(declared_sources) else [],
            "checks": _lines(appendix.get("tests"))}
    out = []
    for key, heading in HEADINGS:
        if body[key]:
            out.append((heading, body[key]))
    method = appendix.get("method") or {}
    citation = ["Method: %s (version %s)" % (method.get("id") or "unknown",
                                             method.get("version") or "?")]
    if appendix.get("spec_hash"):
        citation.append("Specification hash: " + str(appendix["spec_hash"]))
    citation.append("Every figure in this paper can be re-run from the stored specification; "
                    "the hash identifies it.")
    out.append(("How this was produced", citation))
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


def filename(delivery, fmt, title=None):
    """A readable download name; never an id."""
    stem = (title or title_for(delivery)).strip() or "computation"
    safe = "".join(char if char.isalnum() or char in " -_" else " " for char in stem)
    safe = " ".join(safe.split())[:90] or "computation"
    return safe + (".md" if fmt == "md" else ".docx")
