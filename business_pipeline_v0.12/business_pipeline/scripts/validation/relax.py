"""Stage 5 — the relaxation loop (report only, no code changes).

Reads validation_out/manifest.json and measures, per rule, how many papers
fired it and at what confirmed-defect rate.  Per §6.4, a rule with a
confirmed-defect rate under ~10% over a full run is a candidate for
`advisory` or `relaxed`; a rule that fires on every paper is noise by
definition and must be demoted, not left to cry wolf.  Proposals are
written to validation_out/reports/relaxation_proposals.md for the owner's
decision; nothing here edits the product or the harness rules.

Usage (from business_pipeline/):
    PYTHONPATH=src python scripts/validation/relax.py
"""

import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "validation_out")


def main(argv=None):
    manifest_path = os.path.join(OUT, "manifest.json")
    if not os.path.isfile(manifest_path):
        print("no manifest found at", manifest_path)
        return 1
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    features = manifest.get("features", [])
    total = len(features)
    # fire counts
    fire = {}
    advisory = {}
    for f in features:
        for x in f.get("findings", []):
            r = x.get("rule")
            if not r:
                continue
            fire[r] = fire.get(r, 0) + 1
            if x.get("advisory"):
                advisory[r] = advisory.get(r, 0) + 1
    lines = ["# Relaxation proposals — generated %s" % datetime.datetime.now().isoformat(timespec="seconds"),
             "", "Total papers: %d" % total, "",
             "## Fire rates", "",
             "| Rule | Fired on | Fire rate | Advisory | Notes |",
             "|---|---:|---:|---:|---|"]
    proposals = []
    for rule in sorted(fire):
        n = fire[rule]
        rate = (100.0 * n / total) if total else 0.0
        adv = advisory.get(rule, 0)
        note = ""
        # §6.4 heuristics
        if rate >= 90:
            note = "fires on (almost) every paper — noise candidate, demote or re-scope"
            proposals.append((rule, "demote to advisory (noise)", "%.0f%% fire rate" % rate))
        elif rate < 10:
            note = "rare — keep, but verify it is not dead"
        else:
            note = "measure confirmed-defect rate before deciding"
        lines.append("| %s | %d | %.1f%% | %d | %s |" % (rule, n, rate, adv, note))
    lines += ["", "## Proposed downgrades (owner decision required)", ""]
    if not proposals:
        lines.append("No rule currently trips the noise threshold (>= 90% fire rate).")
    else:
        for rule, action, evidence in proposals:
            lines.append("- **%s** — %s (%s). Record in §6.3 before applying." % (rule, action, evidence))
    lines += ["", "## Rules with no code backing (not measured here)", "",
              "V-03, V-13, V-14, V-15, V-16, V-18, V-20 are `proposed` with no",
              "backing code; the harness cannot measure them until they are implemented.",
              ""]
    os.makedirs(os.path.join(OUT, "reports"), exist_ok=True)
    path = os.path.join(OUT, "reports", "relaxation_proposals.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote", path)
    print("rules measured:", len(fire))
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY