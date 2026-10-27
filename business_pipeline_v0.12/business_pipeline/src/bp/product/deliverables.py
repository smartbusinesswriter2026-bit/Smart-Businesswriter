"""Deliverable profiles: what a student is producing, and therefore which formats and blocks apply.

The mistake this replaces was offering four formats for everything. A slide deck of an accounting
submission is not the Word document in landscape - it is a different artefact with different content. So the
student picks the **artefact**, and the format menu follows from it.

Three layers:

* **blocks** - a small fixed vocabulary assembled from the *stored* bundle (statements, workings, checks,
  limitations, citation, headline, artifact table). Nothing here recomputes a number.
* **profiles** - data: which blocks an artefact contains, which formats can carry it, and the default.
* **renderers** - format-specific, handed the blocks.

A format is only offered when a renderer exists for it. `presentation` is declared but not offered: the
PowerPoint renderer is not built, and pretending otherwise would produce an artefact nobody has looked at
opening.
"""

import os

BLOCK_LABELS = {
    "statements": "Statements",
    "workings": "Workings",
    "checks": "Verification checks",
    "limitations": "Limitations",
    "citation": "How this was produced",
    "headline": "Headline figures",
    "artifact_table": "Recorded values",
}

PROFILES = {
    "submission": {
        "label": "Assignment submission",
        "audience": "A marker reading the finished work.",
        "blocks": ["statements", "workings", "checks", "limitations", "citation"],
        "formats": ["docx", "html"],
        "default": "docx",
        "available": True,
    },
    "workpapers": {
        "label": "Working papers",
        "audience": "An examiner auditing the figures cell by cell.",
        "blocks": ["statements", "artifact_table", "citation"],
        "formats": ["xlsx", "spreadsheetml", "csv"],
        "default": "xlsx",
        "available": True,
    },
    "presentation": {
        "label": "Case presentation",
        "audience": "A tutorial group or a viva panel.",
        "blocks": ["headline", "statements", "checks", "citation"],
        "formats": [],
        "default": None,
        "available": False,
        "reason": "the PowerPoint renderer is not built yet; use the submission for now",
    },
}


class DeliverableError(ValueError):
    """The profile or the profile/format pair cannot be produced."""


def profile(name):
    if name not in PROFILES:
        raise DeliverableError(f"unknown deliverable {name!r}; known: {sorted(PROFILES)}")
    entry = PROFILES[name]
    if not entry["available"]:
        raise DeliverableError(f"{entry['label']} is not available: {entry.get('reason', 'no renderer')}")
    return entry


def check_pair(name, fmt):
    """Refuse a pair that cannot carry the artefact, naming what can."""
    entry = profile(name)
    if fmt not in entry["formats"]:
        raise DeliverableError(
            "%s cannot be produced as %s; it can be produced as %s"
            % (entry["label"], fmt, " or ".join(entry["formats"])))
    return entry


def infer(fmt):
    """The artefact a format belongs to, for callers that do not name one.

    Kept for older clients: the UI always sends the artefact, because choosing the format first is what this
    design replaces. When it has to guess, it says which artefact it used in the response.
    """
    for name, entry in PROFILES.items():
        if entry["available"] and fmt in entry["formats"]:
            return name
    raise DeliverableError(f"no deliverable offers {fmt!r}")


def catalogue():
    """What the UI shows: each available artefact, its formats and its default. Never a free menu."""
    return [{"id": key, "label": value["label"], "audience": value["audience"],
             "formats": list(value["formats"]), "default": value["default"],
             "available": value["available"], "reason": value.get("reason")}
            for key, value in sorted(PROFILES.items())]


def _appendix(bundle):
    delivery = bundle.get("delivery") if isinstance(bundle, dict) else None
    return delivery.get("appendix") if isinstance(delivery, dict) else None


def _accounts(bundle):
    appendix = _appendix(bundle)
    accounts = appendix.get("accounts") if isinstance(appendix, dict) else None
    return accounts if isinstance(accounts, dict) else {}


def _lines(value):
    if not isinstance(value, str):
        return []
    return value.splitlines()


def block(bundle, name):
    """One block, assembled from the stored bundle. Returns a list of lines; never computes."""
    appendix = _appendix(bundle) or {}
    accounts = _accounts(bundle)
    if name == "statements":
        value = accounts.get("statements_export")
        if isinstance(value, str):
            return _lines(value)
        if isinstance(value, dict):
            # the exporter hands back one string per statement, not one blob; a submission needs them all,
            # in reading order, and must not fall back to "combined" (that would repeat every line)
            out = []
            for key in ("trial_balance", "income_statement", "balance_sheet", "cash_flow",
                        "reconciliation", "notes"):
                part = value.get(key)
                if isinstance(part, str) and part.strip():
                    out.extend(part.splitlines())
                    out.append("")
            if not out:
                out = _lines(value.get("combined"))
            return out
        return []
    if name == "workings":
        out = []
        t_accounts = accounts.get("t_accounts_export") or {}
        for code in sorted(t_accounts):
            out.extend(_lines(t_accounts[code]))
            out.append("")
        journal = _lines(accounts.get("journal_export"))
        if journal:
            out.append("")
            out.extend(journal)
        return out
    if name == "checks":
        checks = accounts.get("checks")
        if isinstance(checks, list) and checks:
            return ["%s  %s" % ("PASS" if len(c) > 1 and c[1] else "FAIL", c[0]) for c in checks]
        names = appendix.get("tests") or []
        return ["planned: %s" % n for n in names]
    if name == "limitations":
        return list(appendix.get("limitations") or [])
    if name == "headline":
        reperform = bundle.get("reperform") if isinstance(bundle, dict) else None
        outputs = reperform.get("outputs") if isinstance(reperform, dict) else None
        if not isinstance(outputs, dict):
            return []
        return ["%s: %s" % (key, value) for key, value in sorted(outputs.items())]
    if name == "artifact_table":
        from . import export as case_export
        rows = case_export.artifact_rows(bundle)
        return ["%s = %s %s  [%s]" % (r["id"], "" if r["value"] is None else r["value"],
                                      r.get("unit") or "", r.get("derivation") or "") for r in rows]
    if name == "citation":
        reperform = bundle.get("reperform") if isinstance(bundle, dict) else {}
        reperform = reperform if isinstance(reperform, dict) else {}
        method = (reperform.get("method") or {}).get("id") or "unknown method"
        out = ["Method: %s (version %s)" % (method, (reperform.get("method") or {}).get("version") or "?")]
        if reperform.get("spec_hash"):
            out.append("Specification hash: %s" % reperform["spec_hash"])
        if appendix.get("code_hash"):
            out.append("Code hash: %s" % appendix["code_hash"])
        if reperform.get("statements_hash"):
            out.append("Document hash: %s" % reperform["statements_hash"])
        out.append("These figures can be re-run from the stored bundle; the hash identifies the document.")
        return out
    raise DeliverableError(f"unknown block {name!r}")


def sections(bundle, profile_name):
    """The profile's blocks, in order, as (heading, lines) pairs."""
    entry = profile(profile_name)
    out = []
    for name in entry["blocks"]:
        lines = block(bundle, name)
        if lines:
            out.append((BLOCK_LABELS.get(name, name), lines))
    return out


def write_export(bundle, profile_name, fmt, destination):
    """Produce the artefact and return a small report. Only implemented pairs reach here."""
    entry = check_pair(profile_name, fmt)
    if fmt == "docx":
        from . import docx
        result = docx.render_file(_title(bundle), sections(bundle, profile_name), destination)
    elif fmt == "html":
        from . import report_html
        result = report_html.render_file(_title(bundle), sections(bundle, profile_name), destination)
    elif fmt == "csv":
        from . import spreadsheets
        result = {"path": spreadsheets.export_csv(bundle, destination)}
    elif fmt == "xlsx":
        from . import spreadsheets
        result = dict(spreadsheets.export_xlsx(bundle, destination))
    elif fmt == "spreadsheetml":
        from . import spreadsheets
        result = dict(spreadsheets.export_spreadsheetml(bundle, destination, sha=True))
    else:                                                                   # pragma: no cover - guarded above
        raise DeliverableError(f"no renderer for {fmt}")
    return {"deliverable": profile_name, "label": entry["label"], "format": fmt, **result}


def _title(bundle):
    if not isinstance(bundle, dict):
        return "Case export"
    title = bundle.get("title")
    case_id = bundle.get("id")
    if title and case_id:
        return "%s (case %s)" % (title, case_id)
    return title or case_id or "Case export"
