"""Apply the build 1.102 documentation updates, preserving CRLF exactly.

Every edit is asserted: a pattern that is not found stops the script, so a
half-applied documentation change cannot happen quietly.
"""
import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOCS = os.path.join(BASE, "docs")

CHANGELOG_ENTRY = """- 1.102 (2026-11-06): **the statements workbook opens in Excel.** The tile's `.xlsx` download was a valid zip of valid XML that Excel refused - "we found a problem with some content", and an empty workbook. The package was written twice, by two writers, and the tile's writer was the broken one. There is now one writer, and the tile's workbook is the workbook the case bundle already shipped.

  - **What Excel was refusing, exactly.** Three defects, each enough on its own: `/xl/theme/theme1.xml`, `/docProps/core.xml` and `/docProps/app.xml` were declared **twice** in `[Content_Types].xml` (a part carries one content type, not two); the `Notes` sheet appeared **twice** (Excel refuses a duplicate sheet name); and `<cols>` was written **after** `</sheetData>` in every worksheet, while `CT_Worksheet` requires `cols` before `sheetData`. The file was also not byte-stable: `writestr` without a timestamp writes the current time into the zip. The API's response was never wrong - it was a valid package that Excel would not open.
  - **One writer, not two.** `spreadsheets.py` already wrote a workbook Excel accepts; `xlsx.py` wrote a second, broken one. The packaging now lives in one place, `spreadsheets.write_xlsx(sheets, places)`, and `xlsx.py` is the statements tile's adapter over it. The case bundle's workbook is **byte-identical** to before (sha256 `801218277774fd0f...`), so nothing a student already downloaded moved.
  - **The workbook the student receives is the one the brief asks for.** One sheet per requested statement (`Income statement`, `Changes in equity`, `Balance sheet`, `Cash flow`), then `Working`, then `Notes` - the names the render brief gives (`docs/MINIMAX_STATEMENT_RENDER.md` section 9), so the tile's download and the case bundle's workbook agree. Amounts are **numbers**, in the record's decimal places (`#,##0.00;(#,##0.00)`), so Excel totals and sorts them; the header row is frozen; column A is sized to the longest label; no cell is merged. The statement of changes in equity now carries its movement figures as numbers with the note beside them, where the old writer left the whole line as text, and the period line reads the record's period instead of `Period:  to `.
  - **A figure the record only renders is not re-typed.** A record whose appendix cannot supply a statement's typed figures (the thinner record shapes the tile also stores) gets that statement as the record rendered it, verbatim. Re-reading a rendered line is how a figure stops being the record's, so the line stays text rather than becoming a number the record does not hold as a value.
  - **The package is guarded now.** `tests/test_statements_xlsx_export.py` (24 tests) checks the rules Excel enforces - a part declared once, a relationship that resolves, a unique legal sheet name, the worksheet children in order - and the workbook itself: the sheet set, typed amounts, the record's places, the frozen header, no merged cell, byte-stability, and no figure the record does not hold. `qa/manual/audit_xlsx_structure.py` runs the same audit as a probe against an openpyxl reference, and `qa/manual/excel_open_check.ps1` opens the file in Excel itself.
  - **Nothing else moved.** No method, preset, input, check, computed number or frozen-core entry changed. The suite holds 3899 tests; the pre-existing failures recorded in `docs/OPEN_ISSUES.md` item 18 are unchanged by this build.

"""

WORKLOG_ENTRY = """## 2026-11-06 - [statements] The tile's workbook opens in Excel

**Ask.** The statements tile's `.xlsx` download came back as a file Excel would not open - "empty content" - while the API answered with a valid base64 payload of a valid zip of valid XML, and openpyxl read it without complaint. The export had to be fixed so that the student receives a workbook Excel opens, carrying the statements the render brief asks for.

**Did.**

- **The three defects Excel was refusing, named.** `/xl/theme/theme1.xml`, `/docProps/core.xml` and `/docProps/app.xml` were declared **twice** in `[Content_Types].xml` - a part carries one content type, not two. The `Notes` sheet was written **twice** - Excel refuses a duplicate sheet name. And `<cols>` was written **after** `</sheetData>` in every worksheet, while `CT_Worksheet` requires `cols` before `sheetData`. The package was also not byte-stable: `writestr` without a timestamp writes the current time into the zip, so two exports of one record differed.
- **One writer, not two.** `spreadsheets.py` already wrote a workbook Excel accepts; `xlsx.py` wrote a second, broken one, and it was the only workbook writer in the tree that no test covered. The packaging now lives in one place, `spreadsheets.write_xlsx(sheets, places)`, and `xlsx.py` is the statements tile's adapter over it. **The case bundle's workbook is byte-identical to before** (sha256 `801218277774fd0f...`), so nothing a student already downloaded moved.
- **The workbook the student receives is the one the brief asks for.** One sheet per requested statement - `Income statement`, `Changes in equity`, `Balance sheet`, `Cash flow` - then `Working`, then `Notes`, the names the render brief gives (`docs/MINIMAX_STATEMENT_RENDER.md` section 9), so the tile's download and the case bundle's workbook agree. The amounts are **numbers** in the record's decimal places (`#,##0.00;(#,##0.00)`), so Excel totals and sorts them; the header row is frozen; column A is sized to the longest label; no cell is merged. The statement of changes in equity now carries its movement figures as numbers with the note beside them, where the old writer left the whole line as text, and the period line reads the record's period instead of `Period:  to `.
- **A figure the record only renders is not re-typed.** A record whose appendix cannot supply a statement's typed figures - the thinner record shapes the tile also stores - gets that statement as the record rendered it, verbatim. Re-reading a rendered line is how a figure stops being the record's, so the line stays text rather than becoming a number the record does not hold as a value.
- **The package is guarded now.** `tests/test_statements_xlsx_export.py` (24 tests) checks the rules Excel enforces - a part declared once, a relationship that resolves, a unique legal sheet name, the worksheet children in order - and the workbook itself: the sheet set, typed amounts, the record's places, the frozen header, no merged cell, byte-stability, and no figure the record does not hold. `qa/manual/audit_xlsx_structure.py` runs the same audit as a probe against an openpyxl reference, and `qa/manual/excel_open_check.ps1` opens the file in Excel itself.

**Did not move.** No method, preset, input, check, computed number or frozen-core entry changed. The statements, their figures and the request contract are exactly what they were; only the file the student downloads is different.

**Verified.**

- **Excel opens it.** `qa/manual/excel_open_check.ps1` opens the rendered workbook in Excel 16.0: six sheets, each with its data, and no repair. The same script on the pre-repair file fails outright - Excel refuses to open it - which is the symptom the owner reported. Excel reads an amount cell as a `Double` (a number, not text), showing `200,000.00` under the format `#,##0.00;(#,##0.00)`.
- **The audit is clean.** `qa/manual/audit_xlsx_structure.py` reports "no structural problem found": no part declared twice, every part with a content type, every relationship resolving, unique legal sheet names, and every worksheet's children in the order `CT_Worksheet` requires.
- **Byte-stability.** Two renders of the same record are the same bytes (sha256 `c250877dd61f01be...`).
- **The suite is 3899 tests.** The failures that remain are the ones recorded in `docs/OPEN_ISSUES.md` item 18 (`schedules.py` shadowing a frozen core module, and `tier1_tables.py` importing `bp.product`); they are in files this increment does not touch, and both changed files pass the product-boundary rules themselves.

"""

DECISION_ROW = (
    "| B-219 | PROVISIONAL (measured repair, 2026-11-06 - the statements tile's workbook; no new owner instruction) | "
    "**There is one OOXML writer in the product layer, and the tile's workbook is the workbook the case bundle already shipped.** "
    "`src/bp/product/xlsx.py` wrote a second package beside `spreadsheets.py`, and that second package was the broken one: "
    "`/xl/theme/theme1.xml`, `/docProps/core.xml` and `/docProps/app.xml` were declared twice in `[Content_Types].xml`, the "
    "`Notes` sheet was written twice, `<cols>` came after `</sheetData>` in every worksheet, and the zip carried the current time, "
    "so two exports of one record differed. Excel refuses all of that; openpyxl does not, which is why the file read clean and "
    "would not open. The packaging now lives in `spreadsheets.write_xlsx(sheets, places)` alone, `xlsx.py` is the statements "
    "tile's adapter over it, and the case bundle's workbook is byte-identical to before (sha256 `801218277774fd0f...`). | "
    "Two writers of one format is how the two drifted apart: `spreadsheets.py` was written against the render brief and opens in "
    "Excel, and `xlsx.py` was written later, separately, and never did - it had no test, and the only reader it had was "
    "`openpyxl`, which is more forgiving than the application the student opens the file in. Fixing the three defects in place "
    "would have left two package structures to keep right, and the next one would drift the same way. One writer is also the "
    "smaller change: the tile's workbook then *is* the workbook the case bundle already proved, and the case bundle's bytes are "
    "pinned so a future drift is visible. | "
    "Trap: `tests/test_statements_xlsx_export.py` (24 tests) fails on the pre-repair code - a part declared once, a relationship "
    "that resolves, a unique legal sheet name, the worksheet children in the order `CT_Worksheet` requires, the sheet set, typed "
    "amounts, the record's places, the frozen header, no merged cell, byte-stability, and no figure the record does not hold. "
    "Measurement: `qa/manual/audit_xlsx_structure.py` (the same audit as a probe, against an openpyxl reference) and "
    "`qa/manual/excel_open_check.ps1` (opens the file in Excel itself). |\n"
)

HANDOFF_OLD_TAIL = ("The tile's download route still offers text only, so the workbook is not yet what the student receives.")
HANDOFF_NEW_TAIL = (
    "The tile's download route now offers the workbook itself (build 1.102): `src/bp/product/xlsx.py` writes it through the one "
    "OOXML writer, `spreadsheets.write_xlsx`, and `tests/test_statements_xlsx_export.py` (24 tests) checks the package the way "
    "Excel reads it - a part declared once, a relationship that resolves, a unique legal sheet name, the worksheet children in "
    "the order `CT_Worksheet` requires - together with the sheet set, typed amounts, the record's places and byte-stability."
)


def read(name):
    with io.open(os.path.join(DOCS, name), encoding="utf-8", newline="") as stream:
        return stream.read()


def write(name, text):
    with io.open(os.path.join(DOCS, name), "w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def sub(text, old, new, label):
    if old not in text:
        raise SystemExit("NOT FOUND (%s): %r" % (label, old[:80]))
    if text.count(old) != 1:
        raise SystemExit("NOT UNIQUE (%s): %r appears %d times" % (label, old[:60], text.count(old)))
    return text.replace(old, new)


def main():
    # -- CHANGELOG --------------------------------------------------------
    changelog = read("CHANGELOG.md")
    write("CHANGELOG.md", CHANGELOG_ENTRY + changelog)

    # -- WORKLOG ----------------------------------------------------------
    worklog = read("WORKLOG.md")
    write("WORKLOG.md", WORKLOG_ENTRY + worklog)

    # -- DECISIONS --------------------------------------------------------
    decisions = read("DECISIONS.md")
    if "| B-219 |" in decisions:
        raise SystemExit("B-219 already has a row")
    if not decisions.endswith("\n"):
        decisions += "\n"
    write("DECISIONS.md", decisions + DECISION_ROW)

    # -- HOME -------------------------------------------------------------
    home = read("HOME.md")
    home = sub(home,
               "Last verified with build **1.101**, **3873 tests**, 2026-11-06.",
               "Last verified with build **1.102**, **3899 tests**, 2026-11-06.",
               "HOME build and count")
    write("HOME.md", home)

    # -- HANDOFF ----------------------------------------------------------
    handoff = read("HANDOFF.md")
    handoff = sub(handoff, "Build        : 1.101 (see docs/CHANGELOG.md)",
                  "Build        : 1.102 (see docs/CHANGELOG.md)", "HANDOFF build")
    handoff = sub(handoff, "Tests        : 3873 tests;", "Tests        : 3899 tests;",
                  "HANDOFF count")
    handoff = sub(handoff, HANDOFF_OLD_TAIL, HANDOFF_NEW_TAIL, "HANDOFF stale claim")
    write("HANDOFF.md", handoff)

    # -- CONTRIBUTORS -----------------------------------------------------
    contributors = read("CONTRIBUTORS.md")
    contributors = sub(contributors, "currently 3873 tests", "currently 3899 tests",
                       "CONTRIBUTORS count")
    write("CONTRIBUTORS.md", contributors)

    print("documentation updated")


if __name__ == "__main__":
    main()
