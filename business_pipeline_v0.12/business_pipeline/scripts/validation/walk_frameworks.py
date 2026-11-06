"""Stage 1 — the framework walker.

For every entry in `framework_profiles.PROFILES` this drives the product's own
path — `completion.complete` → `completion.missing` → `completion.draft` →
`completion.draft_bytes` — with retrieval frozen to `evidence/shared.json`
(no network, no model: BP_LLM_PROVIDER is unset, llm.from_env() returns None,
so every paper is the deterministic Draft).  It then judges each paper with the
§5 rules that have a code backing and writes:

    validation_out/
      manifest.json                  (the §10 shape: {"features": [...]})
      INDEX.html
      reports/<subject>.md
      <subject>/<feature-id>__apa.docx

Usage (from business_pipeline/):
    PYTHONPATH=src python scripts/validation/walk_frameworks.py [--limit N]
                                                               [--subject accounting]
                                                               [--out validation_out]
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))          # business_pipeline/
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

# ── Environment: draft-only, no model lane ───────────────────────────────
for var in ("BP_LLM_PROVIDER", "BP_LLM_MODEL", "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "BP_OPENGO_API_KEY",
            "OPENCODE_API_KEY"):
    os.environ.pop(var, None)

from bp.product import completion, framework_profiles, paper, verify  # noqa: E402
import bp.product.sources as sources                                   # noqa: E402

SHARED_PACK = os.path.join(HERE, "evidence", "shared.json")

# ── The generic instruction for every paper ──────────────────────────────

INSTRUCTION = (
    "A mid-sized consumer-goods company is deciding whether to expand into a "
    "neighbouring regional market next year. Sales last year were USD 12 million "
    "with gross margin of 38% and fixed costs of USD 3.1 million. The scope covers "
    "the company's main urban store — including its in-store bakery counter — for "
    "workplace or area analysis, its home-delivery operation for process analysis, "
    "and the packaged-snacks product line for product analysis. Draft the {label} "
    "for the launch decision. Use USD and name any information that is missing."
)

#: A profile with a non-industry unit of analysis refuses an anonymous unit.
#: The walker declares the unit through the same structured parameter the
#: product's own UI sends: `unit_value`. (§4.3 still applies — these are test
#: brief details, not evidence.)
UNIT_VALUE = {
    "process": "the home-delivery process of the urban store",
    "unit": "the packaged-snacks business line",
    "country": None,
}
PESTEL_COUNTRY = "Canada"

# ── Judge: the §5 rules that have a code backing ─────────────────────────

CHECK_TO_RULE = {
    "heading_jump": ("V-09", "high"),
    "heading_before_h1": ("V-09", "high"),
    "meta_text": ("V-06", "high"),
    "missing_conclusion": ("V-10", "high"),
    "missing_references": ("V-11", "high"),
}


def load_subject_map():
    with open(os.path.join(HERE, "subject_map.json"), encoding="utf-8") as f:
        return json.load(f)


def load_pack():
    with open(SHARED_PACK, encoding="utf-8") as fh:
        doc = json.load(fh)
    pack = doc.get("sources") if isinstance(doc, dict) else doc
    assert isinstance(pack, list) and pack, "shared evidence pack is empty"
    return pack


def subject_of(template, subject_map):
    declared = (framework_profiles.PROFILES[template].get("subject") or "").replace("_", "-")
    if template in subject_map.get("overrides", {}):
        return subject_map["overrides"][template]
    if declared in subject_map.get("shelves", []):
        return declared
    return subject_map.get("default_subject", "research")


def freeze_retrieval(pack):
    """Replace sources.search_academic / search_web with deterministic, offline
    fakes backed by the shared pack.  Matching is deliberately strict — a thin
    pack produces thin papers with named gaps, which is the honest state the
    harness is meant to see (§8).  The same records serve every subject: the
    shared-pack first-pass recommendation, which the report will show as fewer
    accepted items, not as invented evidence.
    """

    def _match(query, rec, min_hits):
        hay = ((rec.get("title") or "") + " " + (rec.get("abstract") or "")).lower()
        words = {w for w in re.findall(r"[a-z][a-z0-9'-]+", (query or "").lower()) if len(w) > 3}
        return sum(1 for w in words if w in hay) >= min_hits

    def search_academic(query, databases=None, limit=20, year_from=None):
        min_hits = 2 if (not databases or databases == ["corpus"]) else 3
        results = []
        for rec in pack:
            if _match(query, rec, min_hits) and \
                    (not year_from or int(str(rec.get("year", "0"))[:4]) >= year_from):
                results.append(dict(rec))
                if len(results) >= limit:
                    break
        return {"query": query, "results": results, "errors": [],
                "databases": databases or [], "retrieved_at": None,
                "timings": {}, "cached": True}

    def search_web(query, *_args, **_kwargs):
        return {"query": query, "results": [], "errors": [],
                "notice": "harness: frozen pack serves no web results"}

    sources.search_academic = search_academic
    sources.search_web = search_web
    return sources


def judge(result, report):
    """Return (verdict, findings) for one paper."""
    findings = []
    absent = completion.missing(result)
    for item in absent:
        where, rule = (item, "V-12")
        if isinstance(item, dict):
            where = item.get("where") or item.get("detail") or ""
            rule = item.get("rule") or "V-12"
        findings.append({"rule": rule, "severity": "high",
                         "detail": "dimension carries neither an accepted item nor a named gap",
                         "where": str(where), "source": "completion.missing"})
    issues = paper.check(report["sections"], framework=report.get("template") or "pestel",
                         implications="", answers=None)
    check_issues = (issues.get("issues") if isinstance(issues, dict) else issues) or []
    for issue in check_issues:
        if isinstance(issue, str):
            issue = {"type": None, "severity": "medium", "detail": issue, "heading": ""}
        rule, severity = CHECK_TO_RULE.get(issue.get("type"), (None, issue.get("severity") or "medium"))
        if rule:
            findings.append({"rule": rule, "severity": severity,
                             "detail": issue.get("detail", ""), "where": issue.get("heading") or "",
                             "source": "paper.check"})
        else:
            # an issue type the registry does not name yet: recorded, not attributed
            advisory_only = issue.get("type") == "missing_input"  # the walker has no session answers
            findings.append({"rule": None if advisory_only else "V-00-unassigned",
                             "severity": issue.get("severity") or "medium",
                             "detail": issue.get("detail", ""), "where": issue.get("heading") or "",
                             "source": "paper.check", "type": issue.get("type")})
    text = "\n".join(" ".join(item.get("lines") or []) for item in report["sections"])
    for claim in verify.overclaims(text):
        findings.append({"rule": "V-17", "severity": "high", "detail": claim,
                         "where": "", "source": "verify.overclaims"})
    band = report.get("length_range") or ""
    band_match = re.match(r"([0-9,]+)\s*-\s*([0-9,]+)", str(band))
    lo, hi = ((int(band_match.group(1).replace(",", "")), int(band_match.group(2).replace(",", "")))
              if band_match else (0, 10 ** 6))
    words = report.get("words") or 0
    # The band governs the Full paper; a deterministic Draft reports its own count
    # (report["length_applies_to"] == "full"), so the band is advisory-only here.
    if band_match and report.get("length_applies_to") != "full" and (words < lo or words > hi):
        findings.append({"rule": "V-19", "advisory": True, "severity": "low",
                         "detail": "word count %d is outside the band %s..%s" % (words, lo, hi),
                         "where": "", "source": "length"})
    blocking = [f for f in findings if f.get("rule") and f.get("severity") == "high" and not f.get("advisory")]
    return ("fail" if blocking else "pass"), findings


def _finding_names(entries, limit=2):
    names = []
    for x in entries:
        if x.get("rule"):
            names.append("%s %s: %s" % (x["rule"], x.get("where") or "",
                                        (x.get("detail") or "")[:70]))
            if len(names) >= limit:
                break
    extra = len([x for x in entries if x.get("rule")]) - len(names)
    if extra > 0:
        names.append("(+%d more)" % extra)
    return "; ".join(names) or "—"


def write_paper_lines(report_path, features):
    if not features:
        return
    write_header = not os.path.isfile(report_path)
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "a", encoding="utf-8") as fh:
        if write_header:
            fh.write("## %s\n\n| Feature | Verdict | Findings |\n|---|---|---|\n" % features[0]["subject"])
        for entry in features:
            fh.write("| %s | %s | %s |\n" % (entry["label"], entry["verdict"], _finding_names(entry.get("findings", []))))
        fails = sum(1 for fe in features if fe["verdict"] != "pass")
        fh.write("\n%d features, %d pass, %d fail. Papers: `validation_out/%s/`\n\n"
                 % (len(features), len(features) - fails, fails, features[0]["subject"]))


def index_html(subjects_data, generated_at):
    parts = ["<!doctype html><meta charset='utf-8'><title>Validation — framework papers</title>",
             "<style>body{font-family:system-ui;margin:24px}h2{margin-top:28px}",
             "table{border-collapse:collapse;font-size:13px}td,th{border:1px solid #ccc;padding:4px 8px}",
             ".pass{color:#2c8}.fail{color:#c44;font-weight:600}</style>",
             "<h1>Validation — framework papers</h1><p>Generated %s</p>" % generated_at]
    total_pass = total = 0
    for subject, features in subjects_data:
        ok = sum(1 for f in features if f["verdict"] == "pass")
        total += len(features)
        total_pass += ok
        parts.append("<h2>%s — %d/%d pass</h2><table><tr><th>Feature</th><th>Verdict</th><th>Findings</th></tr>"
                     % (subject, ok, len(features)))
        for f in features:
            cls = "pass" if f["verdict"] == "pass" else "fail"
            parts.append("<tr><td>%s</td><td class='%s'>%s</td><td>%s</td></tr>"
                         % (f["label"], cls, f["verdict"], _finding_names(f.get("findings", []), limit=4)))
        parts.append("</table>")
    parts.append("<h2>Total — %d/%d pass</h2>" % (total_pass, total))
    return "\n".join(parts)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "validation_out"))
    ap.add_argument("--limit", type=int, default=0, help="stop after N profiles (0 = all)")
    ap.add_argument("--subject", default=None, help="restrict to one subject slug")
    args = ap.parse_args(argv)

    subject_map = load_subject_map()
    freeze_retrieval(load_pack())

    templates = sorted(framework_profiles.PROFILES)
    if args.subject:
        templates = [t for t in templates if subject_of(t, subject_map) == args.subject]
    if args.limit:
        templates = templates[:args.limit]

    out = args.out
    os.makedirs(out, exist_ok=True)
    for old in ("manifest.json", "INDEX.html"):
        path = os.path.join(out, old)
        if os.path.isfile(path):
            os.remove(path)
    for name in os.listdir(os.path.join(out, "reports")) if os.path.isdir(os.path.join(out, "reports")) else []:
        os.remove(os.path.join(out, "reports", name))

    generated_at = datetime.datetime.now().isoformat(timespec="seconds")
    features = []
    for t in templates:
        profile = framework_profiles.PROFILES[t]
        subject = subject_of(t, subject_map)
        entry = {"subject": subject, "kind": "framework", "id": t,
                 "label": profile.get("label") or t, "feature": "framework"}
        try:
            instruction = INSTRUCTION.format(label=profile.get("label") or t)
            unit_field = (profile.get("unit") or {}).get("field") or "industry"
            if unit_field == "country":
                declared, country = UNIT_VALUE.get("process") or INSTRUCTION, PESTEL_COUNTRY
            else:
                declared = UNIT_VALUE.get(unit_field)
                country = None
            result = completion.complete(t, instruction, industry="consumer goods",
                                         country=country, unit_value=declared)
            report = completion.draft(result, "apa", "draft", "mid")
            verdict, findings = judge(result, report)
            data = completion.draft_bytes(result, "apa", report=report, length="mid")
            fname = "%s__apa.docx" % t
            os.makedirs(os.path.join(out, subject), exist_ok=True)
            with open(os.path.join(out, subject, fname), "wb") as fh:
                fh.write(data)
            entry.update({"paper": "%s/%s" % (subject, fname),
                          "sha256": hashlib.sha256(data).hexdigest(),
                          "words": report.get("words"),
                          "verdict": verdict, "findings": findings})
            print("%s %s %s (%d words, %d findings)" % (
                subject, t, verdict, report.get("words") or 0, len(findings)))
        except Exception as error:  # noqa: BLE001 — a walker error is a finding too
            entry.update({"verdict": "fail", "paper": None,
                          "findings": [{"rule": "V-00-walker", "severity": "high",
                                        "detail": "walker error: %s" % str(error)[:300],
                                        "where": "", "source": "walker"}]})
            print("%s %s ERROR %s" % (subject, t, str(error)[:80]))
        features.append(entry)

    manifest = {"generated_at": generated_at,
                "git_commit": os.environ.get("BP_GIT_COMMIT") or "",
                "build": "v0.12",
                "subject_map_version": subject_map.get("version", 1),
                "features": features,
                "summary": {"pass": sum(1 for f in features if f["verdict"] == "pass"),
                            "fail": sum(1 for f in features if f["verdict"] != "pass"),
                            "by_rule": _by_rule(features)}}
    with open(os.path.join(out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, ensure_ascii=False)

    groups = {}
    for f in features:
        groups.setdefault(f["subject"], []).append(f)
    subjects_data = sorted(groups.items())
    for subject, feats in subjects_data:
        write_paper_lines(os.path.join(out, "reports", "%s.md" % subject), feats)
    with open(os.path.join(out, "INDEX.html"), "w", encoding="utf-8") as fh:
        fh.write(index_html(subjects_data, generated_at))
    print("manifest: %d features, %d pass, %d fail" % (
        len(features), manifest["summary"]["pass"], manifest["summary"]["fail"]))
    return 0


def _by_rule(features):
    counts = {}
    for f in features:
        for x in f.get("findings", []):
            if x.get("rule"):
                counts[x["rule"]] = counts.get(x["rule"], 0) + 1
    return counts


if __name__ == "__main__":
    sys.exit(main())
