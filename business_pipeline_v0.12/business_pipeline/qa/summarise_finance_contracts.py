"""Print the finance contract dump as compact rows for the QA manual.

Usage:  python qa/summarise_finance_contracts.py qa/baseline/finance_contracts.json [out.txt]
"""
import json
import sys


def main(argv):
    data = json.load(open(argv[1], encoding="utf-8-sig"))
    lines = []
    emit = lines.append
    emit("tool_count: %s" % data["tool_count"])
    emit("presets whose method is not in LIBRARY: %s" % (data["presets_with_unknown_method"],))
    emit("")
    for row in data["rows"]:
        c = row["contract"]
        run = row.get("run_on_preset_defaults") or {}
        emit("[%s] %s" % (row["tool"], row["method"]))
        emit("  group=%s level=%s period=%s preset=%s preset_matches=%s"
             % (row["group"], row["level"], row["period"], row["preset"],
                row.get("preset_matches_tool")))
        emit("  RADIO in_library=%s tier=%s metric=%s unit=%s ceiling=%s"
             % (c.get("in_library"), c.get("tier"), c.get("metric"), c.get("unit"),
                c.get("claim_ceiling")))
        emit("  tests=%s typing=%s mapping=%s assumption_checks=%s"
             % (len(c.get("test_names") or []), c.get("has_typing"), c.get("has_mapping"),
                len(c.get("assumption_check_names") or [])))
        emit("  intended_use: %s" % c.get("intended_use"))
        emit("  unsupported_use: %s" % c.get("unsupported_use"))
        schema = c.get("schema") or []
        required = [f["name"] for f in schema if f.get("required", True)]
        optional = [f["name"] for f in schema if not f.get("required", True)]
        emit("  schema required=%s" % required)
        emit("  schema optional=%s" % optional)
        emit("  schema detail: %s" % [(f["name"], f.get("type"), f.get("items"),
                                       f.get("choices")) for f in schema])
        emit("  preset_used=%s input_errors=%s checks_all_ok=%s profile_issues=%s error=%s"
             % (run.get("preset_used"), run.get("input_errors"), run.get("checks_all_ok"),
                run.get("profile_issues"), run.get("error")))
        emit("  outputs: %s" % (run.get("output_keys"),))
        emit("  values: %s" % (run.get("output"),))
        emit("  checks: %s" % (run.get("checks"),))
        emit("  tile formula: %s" % row.get("formula"))
        emit("  steps=%s mistakes=%s related=%s diagram=%s"
             % (row["steps"], row["common_mistakes"], row["related"], row["diagram"]))
        emit("")
    text = "\n".join(lines) + "\n"
    if len(argv) > 2:
        open(argv[2], "w", encoding="utf-8").write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
