"""Run every finance capability through the paper formatter with a real result.

For each finance tool method this probe finds the capability rows that carry it,
computes the method from the shipped preset's inputs, calls the formatter the
draft uses, and flags raw long decimals, "could not be read" fallbacks and rows
that have no bespoke formatter.

Read-only: it writes nothing and computes nothing beyond the frozen method.

Usage:  PYTHONPATH=src python qa/probe_finance_papers.py [out.txt]
"""
import copy
import re
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.product import capabilities, chat, subjects  # noqa: E402
from bp.server import PRESETS  # noqa: E402

LONG_DECIMAL = re.compile(r"\d+\.\d{6,}")


def preset_for(method_id):
    for name, preset in PRESETS.items():
        if preset.get("method") == method_id:
            return name, preset
    return None, None


def main():
    out = []
    emit = out.append
    rows = capabilities.catalogue()
    by_method = {}
    for row in rows:
        by_method.setdefault(row.get("method"), []).append(row)

    detail = subjects.detail("finance")
    formatter_names = {}
    problems = []
    for tool in detail.get("tools") or []:
        method_id = tool["method"]
        if method_id not in methods.LIBRARY:
            emit("=" * 78)
            emit("%s  (method %s is a template, not a frozen method)" % (tool["key"], method_id))
            continue
        method = methods.LIBRARY[method_id]
        preset_name, preset = preset_for(method_id)
        emit("=" * 78)
        emit("%s  method=%s  preset=%s" % (tool["key"], method_id, preset_name))
        matches = by_method.get(method_id) or []
        if not matches:
            emit("   no capability row carries this method")
            continue
        if preset is None:
            emit("   no preset supplies sample inputs")
            continue
        try:
            output = method.impl(copy.deepcopy(preset["inputs"]))
        except Exception as error:  # noqa: BLE001 - probe only
            emit("   method refused the preset inputs: %s" % error)
            continue
        for row in matches:
            formatter = chat.CAPABILITY_LINES.get(row["key"])
            formatter_names[row["key"]] = getattr(formatter, "__name__", formatter)
            emit("   capability %-26s formatter=%s output_key=%r"
                 % (row["key"], getattr(formatter, "__name__", formatter), row.get("output")))
            if formatter is None:
                problems.append((row["key"], "no bespoke formatter"))
            # Record the result exactly as `chat.run_capability` does: a dict is
            # stringified key by key, a bare value is wrapped under the row's
            # declared output key.  Passing the bare Decimal here would invent a
            # crash the product never sees.
            if isinstance(output, dict):
                recorded = {str(name): str(value) for name, value in output.items()}
            else:
                recorded = {row.get("output") or "value": str(output)}
            try:
                lines = chat._capability_lines(row, {"ok": True, "inputs": preset["inputs"],
                                                     "result": recorded})
            except Exception as error:  # noqa: BLE001 - probe only
                emit("      FORMATTER RAISED: %s" % error)
                problems.append((row["key"], "formatter raised %s" % error))
                continue
            for line in lines:
                flags = []
                if LONG_DECIMAL.search(line):
                    flags.append("raw long decimal")
                if "could not be read" in line:
                    flags.append("fallback")
                if flags:
                    problems.append((row["key"], ", ".join(flags) + ": " + line))
                emit("      " + line + (("   <-- " + ", ".join(flags)) if flags else ""))

    emit("")
    emit("=" * 78)
    emit("PROBLEMS (%d)" % len(problems))
    for key, detail_text in problems:
        emit("  [%s] %s" % (key, detail_text))
    text = "\n".join(out) + "\n"
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(text)
        print("wrote %s" % sys.argv[1])
    else:
        print(text)


if __name__ == "__main__":
    main()
