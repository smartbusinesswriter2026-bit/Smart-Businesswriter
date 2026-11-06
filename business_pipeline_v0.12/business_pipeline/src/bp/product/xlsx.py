"""Excel (.xlsx) export of a stored statements record (product layer, stdlib only).

The statements tile offers the student a workbook: the statements that were asked
for, the working papers behind them and the notes.

**The package is written by `spreadsheets.write_xlsx`, the one OOXML writer in the
product layer** - `zipfile` and XML only, no third-party package, and a single place
where the structure Excel enforces has to be right.  This module owns *what* the
workbook holds, never a figure: every cell is copied from the frozen record.

The statement sheets are built from the record's **typed** figures (the appendix's
`income_groups`, `balance_sheet_groups`, `cash_flow` and `equity_statement`), so an
amount on the sheet is the figure the core computed and stored.  A record whose
appendix cannot supply them - the thinner record shapes the tile also stores - keeps
its own rendered statements, as the record wrote them.

Excel is strict about the package and openpyxl is not: a workbook can be a valid zip
of valid XML that Excel refuses to open ("we found a problem with some content"), so
the structure is covered by `tests/test_statements_xlsx_export.py` and by
`qa/manual/audit_xlsx_structure.py`.
"""
from decimal import Decimal

from . import spreadsheets

#: The record's own key for each statement code.
RECORD_KEYS = {"IS": "income_statement", "RE": "equity",
               "BS": "balance_sheet", "CF": "cash_flow"}

#: The working sheet's columns: the journal and the trial balance are text, a check is
#: a name, a result and a detail.
WORKING_WIDTHS = (46, 18, 52)


def _working_rows(record):
    """The working papers: the journal, the trial balance and the checks."""
    working = record.get("working") or {}
    rows = []
    for title, key in (("Journal", "journal"), ("Trial balance", "trial_balance")):
        text = working.get(key) or ""
        if not str(text).strip():
            continue
        if rows:
            rows.append([])
        rows.append([(title, spreadsheets.ST_GROUP)])
        for line in str(text).splitlines():
            if line.strip():
                rows.append([(line.rstrip(), spreadsheets.ST_TEXT)])
    checks = record.get("checks") or []
    if checks:
        if rows:
            rows.append([])
        rows.append([("Checks", spreadsheets.ST_GROUP)])
        for check in checks:
            if isinstance(check, dict):
                name, ok, detail = check.get("name", ""), check.get("ok"), check.get("detail", "")
            elif isinstance(check, (list, tuple)) and len(check) >= 2:
                name, ok = check[0], check[1]
                detail = check[2] if len(check) > 2 else ""
            else:
                continue
            result = "PASS" if ok else "FAIL"
            rows.append([(str(name), spreadsheets.ST_TEXT),
                         (result, spreadsheets.ST_PASS if ok else spreadsheets.ST_FAIL),
                         (str(detail), spreadsheets.ST_TEXT)])
    return rows


def _carries_figures(rows):
    """Whether the rows carry a figure at all.

    A record whose appendix cannot supply the typed figures still carries them in
    its own rendered statements.  Without this the workbook would show a sheet of
    named gaps for a record that holds every figure.
    """
    for row in rows:
        for cell in row:
            value = cell[0] if isinstance(cell, tuple) else cell
            if isinstance(value, Decimal):
                return True
    return False


def _text_rows(text):
    """The record's own rendering of a statement, one line per row.

    A figure the record only renders is not re-typed into a number: re-reading a
    rendered line is how a figure stops being the record's.
    """
    return [[(line.rstrip(), spreadsheets.ST_TEXT)] for line in str(text or "").splitlines()]


def render_bytes(record):
    """The workbook for a stored statements record, as .xlsx bytes.

    One sheet per requested statement, then the working papers, then the notes.  The
    request decides which statements are written: a statement that was computed but
    not asked for is not a sheet, and a cash flow that was withheld is named in the
    working with the record's own reason.

    A statement is written from the appendix's typed figures when the record holds
    them, and from the record's own rendering when it does not - so a sheet never
    says a figure is missing while the record carries it.
    """
    accounts = (record.get("core") or {}).get("appendix") or {}
    statements = record.get("statements") or {}
    typed = {name: (rows, options)
             for name, rows, options in spreadsheets.statement_sheets(accounts, record)}

    sheets = []
    for code, name in spreadsheets.STATEMENT_SHEETS:
        text = statements.get(RECORD_KEYS[code]) or ""
        rows, options = typed.get(name, (None, None))
        if rows is not None and spreadsheets.holds_statement(accounts, code):
            sheets.append((name, rows, options))
        elif str(text).strip():
            sheets.append((name, _text_rows(text), {"widths": (110,), "freeze": 2}))

    working_rows, working_options = typed.get("Working", ([], {}))
    if working_rows and not _carries_figures(working_rows):
        # the appendix carries no typed working papers, so the record's own are used
        rows = _working_rows(record)
        if rows:
            working_rows = rows
            working_options = {"widths": WORKING_WIDTHS, "freeze": 2}
    if working_rows:
        sheets.append(("Working", working_rows, working_options))

    if "Notes" in typed:
        sheets.append(("Notes", typed["Notes"][0], typed["Notes"][1]))
    else:
        notes = statements.get("notes") or ""
        if notes.strip():
            rows = [[(line, spreadsheets.ST_TITLE if not index else spreadsheets.ST_TEXT)]
                    for index, line in enumerate(str(notes).splitlines())]
            sheets.append(("Notes", rows, {"widths": (110,), "freeze": 1}))

    if not sheets:
        sheets.append(("Statements", [[("This record carries no statement to show.",
                                         spreadsheets.ST_NOTE)]], {}))
    places = ((accounts.get("engagement") or {}).get("places") or 2)
    return spreadsheets.write_xlsx(sheets, places)
