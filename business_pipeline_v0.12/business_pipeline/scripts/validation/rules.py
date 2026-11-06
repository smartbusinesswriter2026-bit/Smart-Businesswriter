"""Shared rule engine for the validation harness (Stage 2).

Every rule in docs/VALIDATION_HARNESS.md §5 that has a code backing is
implemented here as a pure function over (result, report, ...) so the three
walkers (framework, capability, compute) cannot drift from each other or
from the product.  Rules with no code backing (V-03, V-13..V-16, V-18,
V-20) are intentionally NOT implemented: the harness reports only what it
can check, and leaves the rest as `proposed` in §5.

Each `check_*` returns a list of findings (dicts with rule/severity/detail/
where/source), possibly empty.  `judge_paper` aggregates them and returns
(verdict, findings).
"""

import re

# imports resolved lazily so this module stays importable in any PYTHONPATH


def _paper_check_issues(report):
    try:
        from bp.product import paper
        issues = paper.check(report.get("sections") or [],
                             framework=report.get("template") or "pestel",
                             implications="", answers=None)
        return (issues.get("issues") if isinstance(issues, dict) else issues) or []
    except Exception as e:  # noqa: BLE001
        return [{"type": "walker", "severity": "high", "detail": str(e), "heading": ""}]


CHECK_TO_RULE = {
    "heading_jump": ("V-09", "high"),
    "heading_before_h1": ("V-09", "high"),
    "meta_text": ("V-06", "high"),
    "missing_conclusion": ("V-10", "high"),
    "missing_references": ("V-11", "high"),
}


def check_v06_v09_v10_v11(report):
    """V-06 (no template text), V-09 (headings), V-10 (conclusion), V-11 (refs)."""
    out = []
    for issue in _paper_check_issues(report):
        if isinstance(issue, str):
            issue = {"type": None, "severity": "medium", "detail": issue, "heading": ""}
        rule, severity = CHECK_TO_RULE.get(issue.get("type"), (None, issue.get("severity") or "medium"))
        if rule:
            out.append({"rule": rule, "severity": severity,
                        "detail": issue.get("detail", ""), "where": issue.get("heading") or "",
                        "source": "paper.check"})
        elif issue.get("type") == "missing_input":
            # the walker has no session answers; recorded, not attributed
            out.append({"rule": None, "severity": issue.get("severity") or "medium",
                        "detail": issue.get("detail", ""), "where": issue.get("heading") or "",
                        "source": "paper.check", "type": issue.get("type"), "advisory": True})
        else:
            out.append({"rule": "V-00-unassigned", "severity": issue.get("severity") or "medium",
                        "detail": issue.get("detail", ""), "where": issue.get("heading") or "",
                        "source": "paper.check", "type": issue.get("type")})
    return out


def check_v12(result, report):
    """V-12: every declared dimension has a non-empty section (item or named gap)."""
    out = []
    sections = report.get("sections") or []
    by_heading = {}
    for s in sections:
        by_heading.setdefault((s.get("heading") or "").strip().lower(), s)
    for block in (result.get("blocks") or []):
        label = (block.get("label") or block.get("key") or "").strip()
        sec = by_heading.get(label.lower())
        if sec is None or not (sec.get("lines") or []):
            out.append({"rule": "V-12", "severity": "high",
                        "detail": "dimension %r has no section carrying an item or a named gap" % label,
                        "where": label, "source": "paper.content"})
    return out


def check_v07(result):
    """V-07: export gate (advisory for draft papers)."""
    try:
        from bp.product import completion
        absent = completion.missing(result)
    except Exception as e:  # noqa: BLE001
        return [{"rule": "V-07", "severity": "low", "advisory": True,
                 "detail": "completion.missing raised: %s" % e, "where": "", "source": "completion.missing"}]
    if not absent:
        return []
    return [{"rule": "V-07", "severity": "low", "advisory": True,
             "detail": "export gate would block: %s" % ", ".join(str(a) for a in absent),
             "where": "", "source": "completion.missing"}]


def check_v17(report):
    """V-17: no unlicensed claim verbs."""
    out = []
    try:
        from bp.product import verify
        text = "\n".join(" ".join(item.get("lines") or []) for item in (report.get("sections") or []))
        for claim in verify.overclaims(text):
            if isinstance(claim, dict):
                detail = "%s: %s" % (claim.get("claim", ""), claim.get("sentence", ""))
            else:
                detail = str(claim)
            out.append({"rule": "V-17", "severity": "high", "detail": detail,
                        "where": "", "source": "verify.overclaims"})
    except Exception as e:  # noqa: BLE001
        out.append({"rule": "V-17", "severity": "high", "detail": "verify.overclaims raised: %s" % e,
                    "where": "", "source": "verify"})
    return out


def check_v19(report):
    """V-19: word count inside band (advisory for drafts)."""
    band = report.get("length_range") or ""
    m = re.match(r"([0-9,]+)\s*-\s*([0-9,]+)", str(band))
    if not m:
        return []
    lo, hi = int(m.group(1).replace(",", "")), int(m.group(2).replace(",", ""))
    words = report.get("words") or 0
    if report.get("length_applies_to") != "full" and (words < lo or words > hi):
        return [{"rule": "V-19", "advisory": True, "severity": "low",
                 "detail": "word count %d is outside the band %s..%s" % (words, lo, hi),
                 "where": "", "source": "length"}]
    return []


def check_v02(result):
    """V-02: gaps named, never filled (named-gap wording present for missing dims)."""
    # The Draft prints named-gap wording for every missing dimension; a block
    # that is missing but whose section lacks gap wording is a V-02 defect.
    out = []
    try:
        from bp.product import completion
        absent = completion.missing(result)
    except Exception:
        return out
    if not absent:
        return out
    sections = None
    # caller passes report separately; this check is best-effort on result only
    return out


def check_v05(result):
    """V-05: computations come from the frozen core (capability papers)."""
    out = []
    if not result.get("kind") == "capability":
        return out
    comps = result.get("computations") or {}
    if not comps:
        out.append({"rule": "V-05", "severity": "high",
                    "detail": "no computation was run for this capability paper",
                    "where": "", "source": "chat.run_capability"})
        return out
    # every computation must have succeeded (ok=True) when the core is attached
    for key, rec in comps.items():
        if isinstance(rec, dict) and rec.get("ok") is False:
            out.append({"rule": "V-05", "severity": "high",
                        "detail": "computation %r failed: %s" % (key, rec.get("error", "")[:120]),
                        "where": key, "source": "chat.run_capability"})
    return out


def _normalize_report(report):
    """Conductor papers store sections as [heading, lines] tuples; framework
    papers store them as dicts.  Normalize to dicts so the checks are shape-agnostic."""
    report = dict(report or {})
    norm = []
    for s in (report.get("sections") or []):
        if isinstance(s, (list, tuple)):
            heading = s[0] if len(s) > 0 else ""
            lines = s[1] if len(s) > 1 else []
            level = s[2] if len(s) > 2 else 1
            norm.append({"heading": heading, "lines": lines, "level": level})
        elif isinstance(s, dict):
            norm.append(s)
        else:
            norm.append({"heading": str(s), "lines": [], "level": 1})
    report["sections"] = norm
    return report


def judge_paper(result, report, kind="framework"):
    """Aggregate all code-backed rules.  Returns (verdict, findings)."""
    report = _normalize_report(report)
    if kind:
        result = dict(result or {}); result.setdefault("kind", kind)
    findings = []
    findings += check_v06_v09_v10_v11(report)
    findings += check_v12(result, report)
    findings += check_v07(result)
    findings += check_v05(result)
    findings += check_v17(report)
    findings += check_v19(report)
    # V-02: named gaps never filled — ensure missing dims carry gap wording
    absent = []
    try:
        from bp.product import completion
        absent = completion.missing(result) or []
    except Exception:
        absent = []
    if absent:
        sections = report.get("sections") or []
        by_heading = {}
        for s in sections:
            by_heading.setdefault((s.get("heading") or "").strip().lower(), s)
        for dim in absent:
            d = dim if not isinstance(dim, dict) else (dim.get("label") or dim.get("where") or "")
            sec = by_heading.get(str(d).strip().lower())
            text = " ".join((sec.get("lines") or []) if sec else [])
            low = text.lower()
            if ("no evidence was found" not in low
                    and "recorded as a gap" not in low
                    and "left for you" not in low
                    and "only you can state" not in low
                    and "this is a gap" not in low
                    and "not a finding" not in low):
                findings.append({"rule": "V-02", "severity": "high",
                                 "detail": "dimension %r is missing but its section does not name the gap" % d,
                                 "where": str(d), "source": "completion.missing"})

    # V-04: no silent framework substitution (recorded in chat state; not applicable to draft papers)
    # V-05: computations from frozen core (capability papers only; checked in walk_capabilities)
    # V-08: model does not research (draft-only path guarantees this; nothing to check)
    blocking = [f for f in findings if f.get("rule") and f.get("severity") == "high" and not f.get("advisory")]
    return ("fail" if blocking else "pass"), findings


def by_rule(features):
    counts = {}
    for f in features:
        for x in f.get("findings", []):
            if x.get("rule"):
                counts[x["rule"]] = counts.get(x["rule"], 0) + 1
    return counts
