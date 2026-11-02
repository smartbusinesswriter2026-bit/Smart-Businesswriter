"""Print the finance pipeline probe as one line per tool.

Usage:  python qa/summarise_finance_pipeline.py qa/baseline/finance_pipeline.json [out.txt]
"""
import json
import sys


def main(argv):
    data = json.load(open(argv[1], encoding="utf-8-sig"))
    lines = []
    for row in data["rows"]:
        r = row["result"]
        if "note" in r or "raised" in r:
            lines.append("%-16s %-26s !!! %s" % (row["tool"], row["method"],
                                                 r.get("note") or r.get("raised")))
            continue
        failing = [k for k, v in (r.get("checks") or {}).items() if not v]
        lines.append("%-16s %-26s status=%-9s tier=%s checks=%s refs=%s chars=%s%s"
                     % (row["tool"], row["method"], r.get("status"), r.get("tier"),
                        len(r.get("checks") or {}), r.get("unresolved_refs"),
                        r.get("report_chars"),
                        ("  FAILING=" + str(failing)) if failing else ""))
        if r.get("status") != "delivered":
            lines.append("      blocked: %s" % (r.get("blocked_reason"),))
    text = "\n".join(lines) + "\n"
    if len(argv) > 1:
        if len(argv) > 2:
            open(argv[2], "w", encoding="utf-8").write(text)
            print("wrote %s" % argv[2])
        else:
            print(text)


if __name__ == "__main__":
    main(sys.argv)
