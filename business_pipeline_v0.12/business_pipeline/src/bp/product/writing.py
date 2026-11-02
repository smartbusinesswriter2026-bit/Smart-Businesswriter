"""Write a sourced research report and export it as Word (.docx).

The report is assembled from the retrieved sources and the worksheet draft.  It
does not invent facts: every claim in the evidence sections is a source title and
a sentence from its abstract, with the citation beside it.  Counts are counts of
the retrieved material, not business results.

The output is deliberately a draft for the student to read, edit and submit.
"""

import re

from . import drafting, docx

MAX_LINE = 900


def _clean(value, limit=MAX_LINE):
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _sentence(source):
    abstract = _clean(source.get("abstract") or source.get("description"), 1200)
    abstract = re.sub(r"^(abstract|summary)\s*[:\-]\s*", "", abstract, flags=re.I)
    if not abstract:
        return ""
    return re.split(r"(?<=[.!?])\s+", abstract)[0][:400]


def _names(source):
    names = [name for name in (source.get("authors_list") or []) if name]
    if names:
        return names
    raw = _clean(source.get("authors"), 300)
    if not raw:
        return []
    return [name.strip() for name in re.split(r";|\s+and\s+", raw) if name.strip()]


ORG_WORDS = {"bank", "commission", "institute", "bureau", "department", "agency", "council",
             "center", "centre", "university", "ministry", "office", "committee", "authority",
             "fund", "association", "union", "nations", "organization", "organisation",
             "administration", "edgar", "sec", "wipo", "unctad", "unesco", "oecd", "imf", "court"}


def _split_name(name):
    name = _clean(name, 160)
    if not name:
        return "", ""
    if "," in name:
        family, given = name.split(",", 1)
        return family.strip(), given.strip()
    parts = name.split()
    if len(parts) == 1:
        return parts[0], ""
    if any(part.lower().strip(".,") in ORG_WORDS for part in parts):
        return name, ""
    return parts[-1], " ".join(parts[:-1])


def _initials(given):
    out = []
    for token in given.replace("-", " - ").split():
        if token == "-":
            out.append("-")
        elif token:
            out.append(token[0].upper() + ".")
    return " ".join(out).replace(" - ", "-")


def _apa_name(name):
    family, given = _split_name(name)
    initials = _initials(given)
    return family + (", " + initials if initials else "")


def _harvard_name(name):
    family, given = _split_name(name)
    initials = _initials(given)
    return family + (", " + initials if initials else "")


def _join_names(names, style):
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return names[0] + (" & " if style == "apa" else " and ") + names[1]
    return ", ".join(names[:-1]) + (", & " if style == "apa" else " and ") + names[-1]


def _family(name):
    return _split_name(name)[0]


def _in_text(source, style):
    names = _names(source)
    year = source.get("year") or "n.d."
    if not names:
        label = _clean(source.get("venue") or source.get("publisher") or source.get("title"), 50)
        return "(" + label + ", " + str(year) + ")"
    families = [_family(name) for name in names]
    if len(families) == 1:
        who = families[0]
    elif len(families) == 2:
        who = families[0] + (" & " if style == "apa" else " and ") + families[1]
    else:
        who = families[0] + " et al."
    return "(" + who + ", " + str(year) + ")"


def _reference(source, style):
    names = _names(source)
    year = str(source.get("year")) if source.get("year") else "n.d."
    title = _clean(source.get("title"), 220)
    venue = _clean(source.get("venue"), 160)
    volume = _clean(source.get("volume"), 30)
    issue = _clean(source.get("issue"), 30)
    pages = _clean(source.get("pages"), 40)
    publisher = _clean(source.get("publisher"), 120)
    link = _clean(source.get("doi") or source.get("url"), 260)
    if style == "apa":
        authors = _join_names([_apa_name(name) for name in names], "apa")
        lead = authors + " (" + year + "). " if authors else title + ". (" + year + "). "
        body = "" if not authors else title + ". "
        if venue:
            body += venue
            if volume:
                body += ", " + volume
            if issue:
                body += "(" + issue + ")"
            if pages:
                body += ", " + pages
            body += "."
        elif publisher:
            body += publisher + "."
        if link:
            body += (" " if body else "") + link
        return _clean(lead + body, 700)
    authors = _join_names([_harvard_name(name) for name in names], "harvard")
    lead = (authors or venue or title) + " (" + year + ") "
    body = "‘" + title + "’" if title else ""
    if venue:
        body += (", " if body else "") + venue
        if volume:
            body += ", " + volume
        if issue:
            body += "(" + issue + ")"
        if pages:
            body += ", pp. " + pages
        body += "."
    elif publisher:
        body += ". " + publisher + "."
    if link:
        body += " doi: " + link if link.startswith("10.") else " Available at: " + link
    return _clean(lead + body, 700)


def in_text(source, style="apa"):
    """Public author-date citation for one source."""
    return _in_text(source, "harvard" if str(style).lower().startswith("harv") else "apa")


def reference(source, style="apa"):
    """Public reference-list entry for one source."""
    return _reference(source, "harvard" if str(style).lower().startswith("harv") else "apa")


def _source_map(sources):
    by_title = {}
    for source in sources:
        title = _clean(source.get("title"), 120).lower()
        if title:
            by_title[title] = source
    return by_title


def compose(template, objective, sources, draft=None, framework=None, style="apa"):
    """Return a report object: title, sections (heading, lines), references, note."""
    style = "harvard" if str(style or "").lower().startswith("harv") else "apa"
    draft = draft or drafting.draft(template, sources)
    sources = [source for source in (sources or []) if isinstance(source, dict) and source.get("title")]
    labels = draft.get("labels") or {}
    assigned = draft.get("assigned") or []
    by_title = _source_map(sources)
    counts = draft.get("counts") or {}
    n_items = draft.get("n_items") or 0
    question = _clean(objective, 300) or "the research question"

    sections = []
    sections.append(("Purpose and method", [
        "This report responds to: " + question + ".",
        "It uses the " + _clean(framework, 120) + " worksheet as its structure, and draws only on sources "
        "retrieved by the source finder. Each evidence item below is a source title and a sentence from "
        "its abstract, with the citation beside it." if framework else
        "It uses the selected framework worksheet as its structure, and draws only on sources retrieved by "
        "the source finder. Each evidence item below is a source title and a sentence from its abstract, "
        "with the citation beside it.",
        "The worksheet does not score, rank or recommend. The report is a draft for review, not a "
        "submission and not a recommendation.",
    ]))

    placed = {key: [item for item in assigned if item.get("block") == key] for key in labels}
    filled = [labels[key] for key in labels if placed.get(key)]
    empty = [labels[key] for key in labels if not placed.get(key)]
    summary = [
        "The search supplied " + str(len(sources)) + " source(s); the framework placed " + str(n_items) +
        " item(s) across " + str(len(filled)) + " dimension(s).",
    ]
    if filled:
        summary.append("Dimensions with evidence: " + ", ".join(filled) + ".")
    if empty:
        summary.append("Dimensions with no retrieved evidence: " + ", ".join(empty) + ". These are gaps, "
                       "not findings; do not read an empty dimension as unimportant.")
    if draft.get("unmatched"):
        summary.append("Some sources matched no dimension and are listed under Gaps and limits.")
    sections.append(("Summary", summary))

    for key, label in labels.items():
        items = placed.get(key) or []
        if not items:
            sections.append((label, ["No retrieved source was placed in this dimension. Treat this as a gap "
                                     "in the evidence, not as a conclusion."]))
            continue
        lines = [str(len(items)) + " retrieved source(s) were placed in this dimension."]
        for item in items:
            source = by_title.get(_clean(item.get("title"), 120).lower(), {})
            quote = _sentence(source)
            line = "• " + _clean(item.get("title"), 220)
            if quote and quote.lower() not in line.lower():
                line += ". The retrieved text says: “" + quote + "”"
            citation = _in_text(source, style) if source else "(" + _clean(item.get("citation"), 300) + ")"
            line += " " + citation + "."
            lines.append(line)
        sections.append((label, lines))

    gaps = ["No source was placed in: " + ", ".join(empty) + "."] if empty else []
    for item in draft.get("unmatched") or []:
        gaps.append("Not placed: " + _clean(item.get("title"), 220) + " — " + _clean(item.get("reason"), 120) + ".")
    gaps += [
        "Placement uses keyword cues; a source can be relevant to more than one dimension.",
        "The report quotes titles and abstracts. It does not verify the claims inside the sources.",
        "No financial figure is computed here. A quantitative question needs the matching method and its checks.",
        "The search may be incomplete: databases differ in coverage and some were rate-limited or not configured.",
    ]
    sections.append(("Gaps and limits", gaps))

    references, seen = [], set()
    for source in sources:
        key = (source.get("doi") or _clean(source.get("title"), 120).lower())
        if key in seen:
            continue
        seen.add(key)
        references.append(_reference(source, style))
    heading = "References" if style == "apa" else "Bibliography"
    sections.append((heading, references or ["No sources were retrieved."]))

    title = "Research report: " + question
    return {"title": title, "sections": sections, "references": references, "style": style,
            "template": template, "n_sources": len(sources), "n_items": n_items,
            "labels": labels, "counts": counts,
            "note": "Draft assembled from retrieved sources. Review it, edit it and cite the sources before submitting."}


def filename(report):
    base = re.sub(r"[^a-z0-9]+", "-", (report.get("title") or "research-report").lower()).strip("-")
    return (base[:60] or "research-report") + ".docx"


def docx_bytes(report):
    """The report as a Word document in APA or Harvard layout."""
    return docx.render_academic(report["title"], report["sections"], report.get("style", "apa"))
