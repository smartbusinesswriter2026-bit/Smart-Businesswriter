"""List every anomaly in the finance contract dump, as candidate defects.

Reads the JSON written by `qa/probe_finance_contracts.py` and prints only the
rows that break a rule the manual will state.  Nothing is changed.

Usage:  python qa/audit_finance.py qa/baseline/finance_contracts.json [out.txt]
"""
import json
import sys

VALID_TIERS = {"T1", "T2", "T3", "T4"}
VALID_CEILINGS = {"descriptive", "associational", "predictive"}


def main(argv):
    data = json.load(open(argv[1], encoding="utf-8-sig"))
    lines = []
    emit = lines.append
    emit("# Finance contract anomalies")
    emit("")
    for row in data["rows"]:
        c = row["contract"]
        run = row.get("run_on_preset_defaults") or {}
        found = []
        if not c.get("in_library"):
            found.append("method %r is not in LIBRARY" % row["method"])
        else:
            if not c.get("intended_use"):
                found.append("empty intended_use")
            if not c.get("unsupported_use"):
                found.append("empty unsupported_use")
            if not c.get("assumptions"):
                found.append("empty assumptions")
            if not c.get("limitations"):
                found.append("empty limitations")
            if not c.get("test_names"):
                found.append("empty test_names")
            if c.get("tier") not in VALID_TIERS:
                found.append("tier %r not in T1..T4" % c.get("tier"))
            if c.get("claim_ceiling") not in VALID_CEILINGS:
                found.append("claim_ceiling %r invalid" % c.get("claim_ceiling"))
            if not c.get("metric"):
                found.append("empty metric")
            if not c.get("unit"):
                found.append("empty unit")
            for field in c.get("schema") or []:
                if not field.get("type") or not field.get("desc"):
                    found.append("schema field %r lacks type or desc" % field.get("name"))
        if not row.get("preset"):
            found.append("tool declares no preset")
        elif row.get("preset_matches_tool") is False:
            found.append("preset %r does not launch %r" % (row["preset"], row["method"]))
        if run.get("input_errors"):
            found.append("preset default inputs rejected: %s" % (run["input_errors"],))
        if run.get("error"):
            found.append("run failed: %s" % run["error"])
        if run.get("checks_all_ok") is False:
            failing = [n for n, ok in run.get("checks") or [] if not ok]
            found.append("self-test failing: %s" % (failing,))
        if run.get("profile_issues"):
            found.append("profile issues: %s" % (run["profile_issues"],))
        if not row.get("formula"):
            found.append("tile declares no formula")
        if not row.get("need"):
            found.append("tile declares no 'what to gather' text")
        if row.get("steps", 0) < 3:
            found.append("tile has fewer than 3 steps")
        if row.get("common_mistakes", 0) < 2:
            found.append("tile has fewer than 2 common mistakes")
        if not row.get("related"):
            found.append("tile declares no related tools")
        if found:
            emit("## [%s] %s" % (row["tool"], row["method"]))
            for item in found:
                emit("  - %s" % item)
            emit("")
    emit("presets whose method is not in LIBRARY: %s" % (data["presets_with_unknown_method"],))
    text = "\n".join(lines) + "\n"
    if len(argv) > 2:
        open(argv[2], "w", encoding="utf-8").write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
