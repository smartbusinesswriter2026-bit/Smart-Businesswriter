"""Build the downloadable chart samples.

Run from the project root with the offline generators installed:

    python qa/manual/make_chart_samples.py

The files are static samples served from `web/assets/samples/`; the product
runtime does not import openpyxl or python-docx.
"""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGET = os.path.join(ROOT, "web", "assets", "samples")
ROWS = [("Quarter", "Revenue"), ("Q1", 120000), ("Q2", 240000),
        ("Q3", 360000), ("Q4", 480000)]


def write_xlsx(path):
    from openpyxl import Workbook
    book = Workbook()
    sheet = book.active
    sheet.title = "Revenue"
    for row in ROWS:
        sheet.append(list(row))
    book.save(path)


def write_docx(path):
    from docx import Document
    document = Document()
    document.add_heading("Revenue by quarter", level=1)
    document.add_paragraph(
        "Make a bar chart of revenue by quarter. The figures are in the table below.")
    table = document.add_table(rows=len(ROWS), cols=2)
    table.style = "Table Grid"
    for index, row in enumerate(ROWS):
        table.rows[index].cells[0].text = str(row[0])
        table.rows[index].cells[1].text = str(row[1])
    document.add_paragraph(
        "The market grew 12% last year, but that sentence is not part of the table.")
    document.save(path)


def main():
    os.makedirs(TARGET, exist_ok=True)
    write_xlsx(os.path.join(TARGET, "chart-data.xlsx"))
    write_docx(os.path.join(TARGET, "chart-instruction.docx"))
    print("wrote", TARGET)


if __name__ == "__main__":
    main()
