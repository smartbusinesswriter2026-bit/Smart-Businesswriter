# Instruction Block for Cline/MiniMax: Fix XLSX Export (Excel Shows Empty Content)

## Context
The XLSX export at `src/bp/product/xlsx.py` produces files that openpyxl can read but Excel shows "empty content" or refuses to open. The backend API returns valid data (base64-encoded, valid zip, valid XML). The issue is in the OOXML structure.

## Current File
`src/bp/product/xlsx.py` (372 lines) — uses zipfile + XML (no openpyxl, per product boundary test).

## What Has Been Tried
1. Removed duplicate "Notes" sheet name (was causing Excel to reject)
2. Fixed styles.xml element order (numFmts before fonts)
3. Added default style to styles.xml
4. Added dimension element to each worksheet
5. Added docProps (core.xml, app.xml) and theme1.xml
6. Added workbookPr, bookViews, calcPr to workbook.xml
7. Added styles relationship to workbook.xml.rels

## Still Failing
Excel still shows "empty content" when the downloaded file is opened.

## What Cline/MiniMax Must Do

### Step 1: Compare against openpyxl reference
Generate a reference XLSX using openpyxl (which Excel accepts) and diff every XML part against our file. Find the exact structural difference.

```python
import openpyxl, io, zipfile
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Income Statement"
ws["A1"] = "Income Statement"
ws["A5"] = "Sales Revenue"
ws["B5"] = 200000
ws["B5"].number_format = "#,##0.00"
buf = io.BytesIO()
wb.save(buf)
buf.seek(0)
ref = zipfile.ZipFile(buf)
# Compare ref.namelist() with our file's namelist()
# Diff each XML file
```

### Step 2: Check these specific issues

1. **[Content_Types].xml** — Does it list ALL parts? Missing `sharedStrings.xml` if using shared strings. Missing `xl/theme/theme1.xml` override. Missing `docProps/core.xml` and `docProps/app.xml` overrides.

2. **xl/_rels/workbook.xml.rels** — Must include relationship for:
   - styles.xml (type: styles)
   - theme/theme1.xml (type: theme)
   - (sharedStrings.xml if using shared strings)

3. **xl/workbook.xml** — Must have:
   - `<workbookPr/>` element
   - `<bookViews><workbookView/></bookViews>`
   - `<sheets>` with valid sheet entries
   - `<calcPr calcId="124519" fullCalcOnLoad="1"/>`
   - Sheet names must be unique and <= 31 chars

4. **xl/styles.xml** — Element order (STRICT):
   - numFmts → fonts → fills → borders → cellStyleXfs → cellXfs → cellStyles → dxfs → tableStyles
   - First cellXfs entry (xfId="0") must be the default style

5. **xl/worksheets/sheetN.xml** — Each must have:
   - `<dimension ref="A1:B{max_row}"/>`
   - `<sheetData>` with valid `<row>` and `<c>` elements
   - `<cols>` before `<sheetData>`
   - Cell references must be valid (A1, B1, etc.)

6. **Shared strings** — Excel prefers shared strings over inline strings. Consider using a sharedStrings.xml part.

7. **_rels/.rels** — Must reference xl/workbook.xml

### Step 3: The Minimax Design (from MINIMAX_STATEMENT_RENDER.md)

- One sheet per requested statement: Income Statement, Balance Sheet, Changes in Equity, Cash Flow Statement
- Then: Working, Notes
- Column A = label, Column B = amount (right-aligned, typed numbers)
- Detail rows indent; group headings bold; subtotals bold with top border; totals bold with double bottom border
- Amounts: record's decimal places, thousands separator, (1,234.00) for negatives
- Blank row between sections, never between subtotal and total
- Freeze header row; column A width from longest label (bounded); do not merge cells
- Working sheet: journal, trial balance, checks
- Notes sheet: record's notes text verbatim
- No third-party dependency (zipfile + XML)
- Byte-stability (fixed zip timestamp)

### Step 4: Implementation Pattern

Follow `src/bp/product/spreadsheets.py` which already builds valid xlsx by hand. Use its `_sheet()`, `_write()`, `_styles_xml()` helpers. The key is to match openpyxl's output structure exactly.

### Step 5: Test

1. Generate xlsx from a test record
2. Open in Excel (or LibreOffice) — must show all sheets with data
3. Verify no "empty content" or "unreadable content" errors
4. Verify typed numbers (not text) in amount column
5. Verify byte-stability (same hash on re-render)

### Files to Modify
- `src/bp/product/xlsx.py` — main export file
- `src/bp/product/spreadsheets.py` — reference implementation (already valid)

### Key Constraint
- No third-party dependency (tests/test_product_boundary.py fails if any product module imports openpyxl, xlsxwriter, pandas, or docx)
- The `handle()` function calls `xlsx_export.render_bytes(record)` at line ~2976

### Current Call Site
```python
# In statements.py handle(), around line 2975:
from . import xlsx as xlsx_export
data = xlsx_export.render_bytes(record)
```

The function takes a statements record dict and returns bytes.
PYEOF
echo "written"