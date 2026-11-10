"""RRA back-test harness.

Measures the RRA against the seeded back-test set:
  recall        — of the seeded known gaps, how many did the RRA rediscover?
  false-gap rate— of the seeded present items, how many did the RRA wrongly flag?

Recall is measured on the **title**: a seeded gap counts as rediscovered when a
produced gap names it (case-insensitive, whitespace-collapsed, alias-tolerant).
A seeded present item counted as a false flag when a produced gap names it.

This is a measurement harness; it never changes the system's behaviour.
"""
import re

from .s0_scope import load_backtest


def _norm(text):
    """Normalize a title for comparison: lowercase, alphanumeric only."""
    return re.sub(r"[^a-z0-9]+", "", str(text or "").lower())


def _alias_forms(title):
    """The normalized title plus a few common alias forms."""
    forms = {_norm(title)}
    raw = str(title or "").lower()
    # drop parentheses content and common qualifiers
    stripped = re.sub(r"\([^)]*\)", "", raw).strip()
    forms.add(_norm(stripped))
    forms.add(_norm(re.sub(r"\b(the|a|an)\b", "", stripped)))
    return {f for f in forms if f}


def _matches(needle, haystack_forms):
    """Does the needle match any of the haystack's alias forms?"""
    needle_form = _norm(needle)
    if not needle_form:
        return False
    if needle_form in haystack_forms:
        return True
    # Containment: a gap titled "Balanced Scorecard" matches a seeded
    # "Balanced Scorecard (BSC)" and the other way round.
    for form in haystack_forms:
        if form and (form in needle_form or needle_form in form):
            return True
    return False


def evaluate(produced_gaps=None, backtest=None, taxonomy=None, coverage_rows=None):
    """Evaluate the RRA against the back-test set.

    Returns a dict with recall, false_gap_rate, the counts, and the misses.

    A seeded gap counts as rediscovered when:
      - the RRA produced a gap naming it (a strict promotion), **or**
      - the RRA's coverage verdict names it as `parked` — recognising that an
        item exists but is on the parked list is a correct identification, not
        a proposal to build it.

    A seeded present item counts as a false flag when the RRA produced a gap
    naming it, or its coverage verdict says `missing`.
    """
    if backtest is None:
        backtest = load_backtest()
    if not backtest:
        return {"error": "no back-test set found (qa/relevance/backtest.json)"}

    produced = list(produced_gaps or [])
    produced_forms = []
    for gap in produced:
        title = gap.get("title", "") if isinstance(gap, dict) else getattr(gap, "title", "")
        produced_forms.append((title, _alias_forms(title)))

    # Coverage verdicts: item -> status
    coverage = {}
    for row in (coverage_rows or []):
        rd = row.to_dict() if hasattr(row, "to_dict") else row
        label = rd.get("taxonomy_item", "")
        coverage[_norm(label)] = rd.get("status", "")

    seeded_gaps = backtest.get("seeded_gaps", []) or []
    seeded_present = backtest.get("seeded_present", []) or []
    thresholds = backtest.get("thresholds", {}) or {}

    def coverage_status(title):
        """The coverage verdict for a title, matched alias-tolerantly."""
        best = ""
        for label, status in coverage.items():
            if label and (label in _norm(title) or _norm(title) in label):
                if status == "parked" or status == "missing":
                    return status
                if not best:
                    best = status
        return best

    # ── Recall ──
    found, missed = [], []
    for item in seeded_gaps:
        label = item.get("notes", "") or item.get("id", "")
        title = item.get("title", "") or item.get("taxonomy_id", "")
        matched = None
        how = ""
        for ptitle, pforms in produced_forms:
            if _matches(title, pforms) or _matches(label, pforms):
                matched = ptitle
                how = "gap"
                break
        if matched is None:
            status = coverage_status(title)
            if status == "parked":
                matched = "coverage: parked"
                how = "parked"
        if matched is not None:
            found.append({"id": item.get("id", ""), "title": title,
                          "matched": matched, "how": how})
        else:
            missed.append({"id": item.get("id", ""), "title": title,
                           "taxonomy_id": item.get("taxonomy_id", "")})

    # ── False flags ──
    false_flags = []
    for item in seeded_present:
        label = item.get("notes", "") or item.get("id", "")
        title = item.get("title", "") or item.get("taxonomy_id", "")
        for ptitle, pforms in produced_forms:
            if _matches(title, pforms) or _matches(label, pforms):
                false_flags.append({"id": item.get("id", ""), "title": title,
                                    "flagged_as": ptitle, "how": "gap"})
                break
        else:
            status = coverage_status(title)
            if status == "missing":
                false_flags.append({"id": item.get("id", ""), "title": title,
                                    "flagged_as": "coverage: missing", "how": "coverage"})

    total_gaps = len(seeded_gaps)
    total_present = len(seeded_present)
    recall = (len(found) / total_gaps) if total_gaps else 0.0
    false_rate = (len(false_flags) / total_present) if total_present else 0.0

    min_recall = float(thresholds.get("min_recall", 0.8))
    max_false = float(thresholds.get("max_false_gap_rate", 0.0))
    min_count = int(thresholds.get("min_recall_count", 8))
    max_flags = int(thresholds.get("max_false_flags", 0))

    passed = (recall >= min_recall and len(found) >= min_count
              and false_rate <= max_false and len(false_flags) <= max_flags)

    return {
        "produced_gap_count": len(produced),
        "seeded_gap_count": total_gaps,
        "seeded_present_count": total_present,
        "found_count": len(found),
        "missed_count": len(missed),
        "false_flag_count": len(false_flags),
        "recall": round(recall, 4),
        "false_gap_rate": round(false_rate, 4),
        "found": found,
        "missed": missed,
        "false_flags": false_flags,
        "thresholds": {
            "min_recall": min_recall,
            "min_recall_count": min_count,
            "max_false_gap_rate": max_false,
            "max_false_flags": max_flags,
        },
        "passed": passed,
    }


def run_backtest(produced_gaps=None, backtest=None):
    """Run the back-test and return the evaluation dict."""
    return evaluate(produced_gaps=produced_gaps, backtest=backtest)
