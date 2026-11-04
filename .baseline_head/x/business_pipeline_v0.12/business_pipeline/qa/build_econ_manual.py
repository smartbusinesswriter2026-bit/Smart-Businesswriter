"""Append sections 3, 4 and 5 to `qa/manual/economics.md` from the live registries.

Section 3 is one row per compute tool; sections 4 and 5 are the worksheets (none)
and the records / theories / glossary. Regenerated, never hand-edited, so a row
cannot drift from `bp.methods.LIBRARY` or `subjects.detail("economics")`.

Usage:  python qa/build_econ_manual.py
"""
import json
import pathlib
import sys

sys.path.insert(0, "src")

from bp.methods import LIBRARY          # noqa: E402
from bp.product import subjects         # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent
BASE = APP / "qa" / "baseline"
MANUAL = APP / "qa" / "manual" / "economics.md"
MARKER = "## 6. Student guidance"


def short(text, limit):
    text = (text or "").replace("|", "/").strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def tool_section(add, tools, runs):
    add("## 3. Compute tools — one row per tool")
    add("")
    add("Sources: *claims*, *refuses*, *checks*, *ceiling* and *inputs* are rank 1")
    add("(`bp.methods.LIBRARY`); *formula* and *level* are rank 5")
    add("(`subjects.detail(\"economics\")[\"tools\"]`); *outputs* and their units come from the")
    add("method's own `typing()` hook, read from a real run of the preset. `L` marks a list")
    add("input, `R` a record list; `opt` marks an optional input. A percentage is a fraction of")
    add("one (0.06 = 6%), never the number 6. Each row's acceptance ID is its test in §9.")
    add("")
    for number, tool in enumerate(tools, start=1):
        method = LIBRARY[tool["method"]]
        row = runs.get(tool["key"], {})
        inputs = []
        for name in sorted(method.input_schema or {}):
            spec = method.input_schema[name]
            kind = spec.get("type") or "?"
            mark = {"decimal_list": "L", "value_list": "L", "records": "R",
                    "column_map": "R", "count_table": "R",
                    "code_list": "L"}.get(kind, "")
            optional = "" if spec.get("required", True) else " opt"
            inputs.append("`%s`%s%s" % (name, mark, optional))
        outputs = ["%s (%s)" % (name, unit)
                   for name, unit in (row.get("units") or {}).items()]
        add("### %03d. %s — `%s`" % (number, tool["label"], tool["key"]))
        add("")
        add("- **Acceptance:** E-eco-%03d" % number)
        add("- **Method / preset:** `%s` / `%s` · **tier** %s · **level** %s"
            % (tool["method"], tool["preset"], method.tier, tool.get("level")))
        add("- **Row unit / claim ceiling:** %s / **%s**"
            % (method.unit, method.claim_ceiling))
        add("- **Claims:** %s" % short(method.intended_use, 320))
        add("- **Refuses:** %s" % short(method.unsupported_use, 320))
        add("- **Formula (student note):** %s" % short(tool.get("formula"), 260))
        add("- **Inputs:** %s" % (", ".join(inputs) or "_none_"))
        add("- **Outputs (method typing):** %s" % (", ".join(outputs) or "_none_"))
        add("- **Checks:** %s" % ", ".join(method.test_names or ()))
        add("- **Assumptions:** %s" % short("; ".join(method.assumptions or ()), 260))
        add("")


def main():
    detail = subjects.detail("economics")
    tools = detail["tools"]
    runs = {row["tool"]: row for row in
            json.loads((BASE / "econ_tools_report.json").read_text(encoding="utf-8"))["tools"]}
    text = MANUAL.read_text(encoding="utf-8")
    head, tail = text.split(MARKER, 1)

    lines = []
    add = lines.append
    tool_section(add, tools, runs)

    add("## 4. Worksheets and framework profiles")
    add("")
    add("**None.** `subjects.detail(\"economics\")[\"worksheets\"]` is empty (%d), every tile's"
        % len(detail["worksheets"]))
    add("`worksheets` list is empty, and no economics record names a `template`. The shelf is")
    add("arithmetic only; `does_not` says so and the student guide repeats it. This is a declared")
    add("scope statement (`CURRICULUM_MAP.md` places this shelf's coverage entirely in tools), not")
    add("a missing feature, and no E-row promises a paper from this shelf.")
    add("")
    add("## 5. Records, theories and glossary")
    add("")
    add("### 5.1 Catalogue records (%d)" % len(detail["records"]))
    add("")
    add("| id | name | type | form | template | linked methods | declared status |")
    add("|---|---|---|---|---|---|---|")
    for record in detail["records"]:
        add("| `%s` | %s | %s | %s | %s | %s | %s |"
            % (record.get("id"), record.get("name"), record.get("type"),
               record.get("form"), record.get("template") or "—",
               ", ".join("`%s`" % m for m in record.get("linked_methods") or []) or "—",
               short(record.get("status_short"), 40)))
    add("")
    add("Every record is read-only catalogue material: `template` is `None` for all five and each")
    add("links only methods that exist. A record naming a worksheet the engine does not have, or a")
    add("method absent from `LIBRARY`, is a defect (E-eco-070).")
    add("")
    for record in detail["records"]:
        add("- **%s %s** — %s" % (record.get("id"), record.get("name"),
                                  record.get("status_note") or ""))
    add("")
    add("### 5.2 Theories (%d)" % len(detail["theories"]))
    add("")
    add("None on this shelf; the reading lenses live on Research & statistics.")
    add("")
    add("### 5.3 Glossary (%d terms)" % len(detail["glossary"]))
    add("")
    add("| term | definition |")
    add("|---|---|")
    for entry in detail["glossary"]:
        add("| %s | %s |" % (entry["term"], short(entry["definition"], 200)))
    add("")
    add("### 5.4 Tiles (%d)" % len(detail["tiles"]))
    add("")
    add("| key | label | tools | worksheets |")
    add("|---|---|---|---|")
    for tile in detail["tiles"]:
        add("| `%s` | %s | %d | %s |"
            % (tile["key"], tile["label"], len(tile.get("tools") or []),
               ", ".join(tile.get("worksheets") or []) or "—"))
    add("")
    add("The tile-level `need` text tells the student what to gather for the whole group. The")
    add("per-tool `need` is present for only 7 of 59 tools (`TOOL_NEEDS` carries `npv`, `forecast`,")
    add("`descriptive`, `pearson`, `ols`, `chi_square`, `power`); the other 52 tool cards render")
    add("without a *what you need* line — ledgered `G-eco-01` and tested as a fallback, never")
    add("faked (E-eco-080).")
    add("")

    MANUAL.write_text(head + "\n".join(lines) + "\n" + MARKER + tail, encoding="utf-8")
    print("wrote sections 3-5, %d lines" % len(lines))


if __name__ == "__main__":
    main()

