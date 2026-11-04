"""Print the dumped subject catalogue as compact rows for the QA manual.

Usage:  python qa/summarise_subject.py qa/baseline/accounting_catalogue.json
"""
import json
import sys


def main(argv):
    path = argv[1] if len(argv) > 1 else "qa/baseline/accounting_catalogue.json"
    data = json.load(open(path, encoding="utf-8-sig"))
    lines = []
    emit = lines.append
    emit("counts: %s" % (data["counts"],))
    definition = data["definition"]
    emit("tools in def: %d | worksheets: %s" % (len(definition["tools"]), definition["worksheets"]))
    emit("catalogue_ids: %s" % (definition["catalogue_ids"],))
    emit("")
    emit("== TOOLS ==")
    for tool in data["tools"]:
        emit("[%s] preset=%s method=%s group=%s period=%s" %
             (tool["key"], tool["preset"], tool["method"], tool.get("group"), tool.get("period")))
        emit("   label: %s" % tool["label"])
        emit("   what : %s" % tool.get("what"))
        emit("   need : %s" % tool.get("need"))
        emit("   level: %s" % tool.get("level"))
        emit("   formula: %s" % tool.get("formula"))
        emit("   steps: %d | mistakes: %d | related: %s" %
             (len(tool.get("steps") or []), len(tool.get("common_mistakes") or []),
              tool.get("related")))
        emit("   diagram: %s" % tool.get("diagram"))
    emit("")
    emit("== WORKSHEETS ==")
    for sheet in data["worksheets"]:
        emit(str(sheet))
    emit("")
    emit("== RECORDS ==")
    for row in data["records"]:
        emit(str({k: row.get(k) for k in ("id", "name", "form", "summary", "implementation_status",
                                          "template", "methods", "form_short", "worksheet")}))
    emit("")
    emit("== TILES ==")
    for tile in data["tiles"]:
        emit(str(tile))
    text = "\n".join(lines) + "\n"
    if len(argv) > 2:
        with open(argv[2], "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s" % argv[2])
    else:
        print(text)



if __name__ == "__main__":
    main(sys.argv)
