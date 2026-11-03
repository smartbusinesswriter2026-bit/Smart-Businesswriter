"""Read the statements workbook back and prove what the record holds.

The workbook the student downloads is built from the frozen record; this script opens that
workbook with the read-back harness (`tests/xlsx_read.py`) and checks the things the
renderer must preserve:

* one sheet per requested statement, in typed cells;
* the income statement foots to the record's net income;
* the balance sheet balances (assets = liabilities + equity);
* the three cash-flow reconciliations hold;
* a cash flow the record withheld is not a sheet, and the working papers say why;
* an income-statement-only request produces exactly one statement sheet;
* two exports of the same record are byte-identical;
* no figure on any sheet is a figure the record does not hold.

Run from anywhere:

    python qa/manual/demo_statements_workbook.py
"""

import json
import os
import sys
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
for path in (os.path.join(ROOT, "src"), os.path.join(ROOT, "tests")):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp.product import spreadsheets            # noqa: E402
import product_statements_fixture as fixture   # noqa: E402
import xlsx_read                               # noqa: E402

STATEMENT_SHEETS = ("Income statement", "Changes in equity", "Balance sheet", "Cash flow")

failures = []


def check(ok, message):
    print("  %s %s" % ("PASS" if ok else "FAIL", message))
    if not ok:
        failures.append(message)


def bundle_for(record):
    """The workbook the writer produces for a statements record."""
    return {"id": "fixture", "title": "Statements fixture", "method": "management_accounts",
            "tier": "T2", "created_at": "2026-11-04T00:00:00Z",
            "delivery": {"appendix": {"accounts": record["core"]["appendix"]}}}


def labelled(rows):
    """The label/amount pairs of a sheet: the label in column A, the amount in column B."""
    found = {}
    for row in rows:
        cells = [cell for cell in row if cell != ""]
        if len(cells) < 2:
            continue
        label = next((cell for cell in cells if isinstance(cell, str) and cell.strip()), None)
        if label is None:
            continue
        value = next((cell for cell in cells[cells.index(label) + 1:] if isinstance(cell, Decimal)), None)
        if value is not None:
            found.setdefault(label.strip(), value)
    return found


def main():
    record = fixture.load()
    appendix = record["core"]["appendix"]
    data = spreadsheets.to_xlsx(bundle_for(record))
    sheets = xlsx_read.read(data)

    print("SHEETS: %s\n" % ", ".join(sheets))

    print("The statements are typed cells")
    for name in STATEMENT_SHEETS:
        rows = sheets.get(name) or []
        amounts = [cell for row in rows for cell in row if isinstance(cell, Decimal)]
        check(bool(rows) and bool(amounts), "%s: %d rows, %d amounts written as numbers"
              % (name, len(rows), len(amounts)))

    print("\nThe income statement foots to the record's net income")
    income = labelled(sheets["Income statement"])
    revenue = income["Total revenue"]
    expenses = income["Total expenses"]
    net_income = income["Net income"]
    check(revenue - expenses == net_income,
          "total revenue %s less total expenses %s = net income %s" % (revenue, expenses, net_income))
    check(net_income == Decimal(record["core"]["scalars"]["net_income"]),
          "net income on the sheet is the record's net income (%s)" % record["core"]["scalars"]["net_income"])

    print("\nThe balance sheet balances")
    balance = labelled(sheets["Balance sheet"])
    check(balance["Total assets"] == Decimal(record["core"]["scalars"]["total_assets"]),
          "total assets %s" % balance["Total assets"])
    check(balance["Total liabilities"] + balance["Total equity"] == balance["Total assets"],
          "total liabilities %s + total equity %s = total assets %s"
          % (balance["Total liabilities"], balance["Total equity"], balance["Total assets"]))
    check(balance["Total liabilities and equity"] == balance["Total assets"],
          "total liabilities and equity %s" % balance["Total liabilities and equity"])

    print("\nThe three cash flow reconciliations hold")
    cash = labelled(sheets["Cash flow"])
    working = labelled(sheets["Working"])
    operating, investing, financing = (cash["Total operating activities"], cash["Total investing activities"],
                                       cash["Total financing activities"])
    net = cash["Net change in cash"]
    check(operating + investing + financing == net,
          "operating %s + investing %s + financing %s = net change in cash %s"
          % (operating, investing, financing, net))
    check(working["Net change in cash, direct route"] == working["Net change in cash, indirect route"],
          "the direct route %s and the indirect route %s agree"
          % (working["Net change in cash, direct route"], working["Net change in cash, indirect route"]))
    opening = cash["Cash at start of period"]
    check(cash["Cash at end of period"] - opening == net,
          "ending cash %s less opening cash %s = the change %s"
          % (cash["Cash at end of period"], opening, net))
    balance_cash = Decimal(appendix["balance_sheet_groups"]["groups"]["current_assets"]["Cash"])
    check(cash["Cash at end of period"] == balance_cash,
          "the cash flow's ending cash %s is the balance sheet's cash line %s"
          % (cash["Cash at end of period"], balance_cash))

    print("\nA cash flow the record withheld is not a sheet")
    withheld = dict(appendix)
    withheld["requested"] = ["IS", "BS", "CF"]
    withheld["cash_flow_withheld_because"] = ("a cash flow statement needs the period's flows or a prior "
                                               "balance sheet, and the instruction supplies one trial balance")
    withheld_sheets = xlsx_read.read(spreadsheets.to_xlsx(bundle_for({"core": {"appendix": withheld}})))
    check("Cash flow" not in withheld_sheets, "no cash flow sheet")
    reason = " ".join(str(cell) for row in withheld_sheets["Working"] for cell in row)
    check("balance sheet" in reason, "the working papers carry the reason it was withheld")

    print("\nAn income-statement-only request produces exactly one statement sheet")
    only = dict(appendix)
    only["requested"] = ["IS"]
    only_sheets = xlsx_read.read(spreadsheets.to_xlsx(bundle_for({"core": {"appendix": only}})))
    written = [name for name in only_sheets if name in STATEMENT_SHEETS]
    check(written == ["Income statement"], "the statement sheets are %s" % (written or "none"))

    print("\nTwo exports of the same record are byte-identical")
    check(spreadsheets.to_xlsx(bundle_for(record)) == data, "the second export matches the first byte for byte")

    print("\nNo figure on any sheet is a figure the record does not hold")
    held = fixture.typed_numbers(record)
    rendered = set()
    for rows in sheets.values():
        rendered.update(xlsx_read.numbers(rows))
        rendered.update(xlsx_read.numbers_in_text(rows))
    invented = sorted(value for value in rendered if value not in held)
    check(invented == [], "every figure is one the record holds (unheld: %s)" % (invented or "none"))

    print("\n%s" % ("ALL CHECKS PASSED" if not failures else "FAILURES: %s" % failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
