"""Emit the finance tool table as markdown rows, from the measured contract dump.

Usage:  python qa/manual_finance_tables.py qa/baseline/finance_contracts.json [out.md]
"""
import json
import sys


def main(argv):
    data = json.load(open(argv[1], encoding="utf-8-sig"))
    lines = []
    emit = lines.append
    emit("| Tool | Method | Tier | Metric / unit | Claim ceiling | Required inputs | "
         "Optional inputs | Preset |")
    emit("|---|---|---|---|---|---|---|---|")
    for row in data["rows"]:
        c = row["contract"]
        schema = c.get("schema") or []
        required = ", ".join("`%s`" % f["name"] for f in schema if f.get("required", True))
        optional = ", ".join("`%s`" % f["name"] for f in schema if not f.get("required", True))
        if not c.get("in_library"):
            emit("| `%s` | `%s` (T2 template) | T2 | n/a | descriptive | `facts`, `alternatives` | — "
                 "| `%s` |" % (row["tool"], row["method"], row["preset"] or "—"))
            continue
        emit("| `%s` | `%s` | %s | %s / %s | %s | %s | %s | `%s` |"
             % (row["tool"], row["method"], c.get("tier"), c.get("metric"), c.get("unit"),
                c.get("claim_ceiling"), required or "—", optional or "—",
                row["preset"] or "*(none)*"))
    text = "\n".join(lines) + "\n"
    if len(argv) > 2:
        open(argv[2], "w", encoding="utf-8").write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)


if __name__ == "__main__":
    main(sys.argv)
