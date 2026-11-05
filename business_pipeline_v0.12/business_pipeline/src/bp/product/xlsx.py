"""Excel (.xlsx) export of a stored statements record (product layer, openpyxl).

Produces a real .xlsx workbook with one sheet per rendered statement.  Every figure
is read from the stored record's rendered text — nothing is recomputed, and the same
parser works for every route (plan, schedule, owner-equity, …).

Layout: title row, then label/amount pairs extracted from the fixed-width rendered
text.  Heading and prose lines (no trailing amount) are written as label-only rows.
"""
import io
import re
from decimal import Decimal, InvalidOperation
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


def _money(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    text = str(v).strip().replace(",", "").strip("()")
    try:
        d = Decimal(text)
        return float(d)
    except (InvalidOperation, ValueError):
        return None


def _line_value(line):
    """(label, Decimal) for a rendered line ending in an amount, else (line, None)."""
    text = str(line or "").rstrip()
    m = re.match(r"^(.*?)\s{2,}(\S+)$", text)
    if not m:
        return text.strip(), None
    try:
        val = Decimal(m.group(2).replace(",", "").strip("()"))
        if m.group(2).startswith("("):
            val = -val
    except (InvalidOperation, ValueError):
        return text.strip(), None
    return m.group(1).strip(), val


def _parse_statement(text):
    """Return list of (label, amount_or_None) rows from rendered statement text."""
    rows = []
    for line in str(text or "").splitlines():
        if not line.strip():
            rows.append(("", None))
            continue
        label, val = _line_value(line)
        rows.append((label, val))
    return rows


def _is_heading(label):
    """A line that is a section title (no amount, short, all-caps or known heading)."""
    if not label:
        return False
    if label.isupper() and len(label) < 60:
        return True
    return False


_SHEET_NAMES = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
    "equity": "Statement of Equity",
    "cash_flow": "Cash Flow Statement",
    "trial_balance": "Trial Balance",
    "notes": "Notes",
}


def render_bytes(record):
    """The whole .xlsx as bytes, built from the stored record."""
    wb = Workbook()
    wb.remove(wb.active)

    statements = record.get("statements") or {}
    # Fall back to statements_only text for routes that store everything in one field
    statements_only = record.get("statements_only") or ""
    period = (record.get("reading") or {}).get("period") or {}
    end_date = period.get("end", "")
    currency = (record.get("reading") or {}).get("currency", "USD")

    # Styles
    bold = Font(bold=True)
    title_font = Font(bold=True, size=14)
    section_font = Font(bold=True, size=11)
    total_font = Font(bold=True)
    thin = Side(style="thin", color="BFBFBF")
    border = Border(bottom=thin)
    money_fmt = '#,##0.00'

    sheets_created = 0
    for key, title in _SHEET_NAMES.items():
        text = statements.get(key)
        if not text:
            continue
        rows = _parse_statement(text)
        if not any(label or val is not None for label, val in rows):
            continue
        ws = wb.create_sheet(title)
        ws["A1"] = title
        ws["A1"].font = title_font
        ws["A2"] = f"Period: {period.get('start','')} to {end_date}"
        ws["A3"] = f"Currency: {currency}"
        r = 5
        for label, val in rows:
            if not label and val is None:
                r += 1
                continue
            if _is_heading(label) and val is None:
                ws.cell(row=r, column=1, value=label).font = section_font
                r += 1
                continue
            ws.cell(row=r, column=1, value=label)
            if val is not None:
                c = ws.cell(row=r, column=2, value=float(val))
                c.number_format = money_fmt
            r += 1
        ws.column_dimensions["A"].width = 44
        ws.column_dimensions["B"].width = 16
        sheets_created += 1

    # If no structured sheets, create one from statements_only
    if sheets_created == 0 and statements_only:
        ws = wb.create_sheet("Statements")
        ws["A1"] = "Financial Statements"
        ws["A1"].font = title_font
        r = 3
        for line in statements_only.splitlines():
            ws.cell(row=r, column=1, value=line)
            r += 1
        ws.column_dimensions["A"].width = 80

    # Scalars sheet (headline figures)
    scalars = (record.get("core") or {}).get("scalars") or {}
    if scalars:
        ws = wb.create_sheet("Key Figures")
        ws["A1"] = "Key Figures"
        ws["A1"].font = title_font
        ws["A2"] = f"Period: {period.get('start','')} to {end_date}"
        r = 4
        ws.cell(row=r, column=1, value="Figure").font = bold
        ws.cell(row=r, column=2, value="Value").font = bold
        r += 1
        for key, val in scalars.items():
            ws.cell(row=r, column=1, value=key.replace("_", " ").title())
            v = _money(val)
            if v is not None:
                c = ws.cell(row=r, column=2, value=v)
                c.number_format = money_fmt
            else:
                ws.cell(row=r, column=2, value=str(val))
            r += 1
        ws.column_dimensions["A"].width = 36
        ws.column_dimensions["B"].width = 16

    # Checks sheet
    checks = record.get("checks") or []
    if checks:
        ws = wb.create_sheet("Checks")
        ws["A1"] = "Verification Checks"
        ws["A1"].font = title_font
        r = 3
        ws.cell(row=r, column=1, value="Check").font = bold
        ws.cell(row=r, column=2, value="Result").font = bold
        ws.cell(row=r, column=3, value="Detail").font = bold
        r += 1
        for ch in checks:
            if isinstance(ch, dict):
                ws.cell(row=r, column=1, value=ch.get("name", ""))
                ws.cell(row=r, column=2, value="PASS" if ch.get("ok") else "FAIL")
                ws.cell(row=r, column=3, value=str(ch.get("detail", ""))[:200])
            elif isinstance(ch, (list, tuple)) and len(ch) >= 2:
                ws.cell(row=r, column=1, value=str(ch[0]))
                ws.cell(row=r, column=2, value="PASS" if ch[1] else "FAIL")
                if len(ch) > 2:
                    ws.cell(row=r, column=3, value=str(ch[2])[:200])
            r += 1
        ws.column_dimensions["A"].width = 44
        ws.column_dimensions["B"].width = 10
        ws.column_dimensions["C"].width = 60

    if len(wb.sheetnames) == 0:
        ws = wb.create_sheet("Statements")
        ws["A1"] = "No statements available"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
