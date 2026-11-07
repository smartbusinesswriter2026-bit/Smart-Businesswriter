src = open("src/bp/product/xlsx.py", encoding="utf-8").read()

# Add dimension element to _sheet_xml
old = """    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<sheetData>']"""
new = """    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<dimension ref="A1:B%d"/>' % max(1, r - 1) if False else '<dimension ref="A1:B1"/>',
             '<sheetData>']"""
# Actually, let's compute dimension properly. We need to know the max row.
# Simpler: just add dimension after we know the row count.
# Let me rewrite _sheet_xml to include dimension
old2 = """def _sheet_xml(rows_data):
    \"\"\"Build worksheet XML from (label, value, style) tuples. value can be float or None.\"\"\"
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<sheetData>']
    r = 1
    for item in rows_data:
        if item is None:
            r += 1
            continue
        if isinstance(item, str):
            item = (item, None, 0)
        label, val, style = item if len(item) == 3 else (item[0], item[1] if len(item) > 1 else None, 0)
        lines.append('<row r="%d">' % r)
        if label is not None and str(label).strip():
            lines.append('<c r="A%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(str(label))))
        if val is not None:
            if isinstance(val, str):
                lines.append('<c r="B%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(val)))
            else:
                lines.append('<c r="B%d" s="%d"><v>%s</v></c>' % (r, style, val))
        lines.append('</row>')
        r += 1
    lines.append('</sheetData>')
    lines.append('<cols><col min="1" max="1" width="44" customWidth="1"/><col min="2" max="2" width="18" customWidth="1"/></cols>')
    lines.append('</worksheet>')
    return "\\n".join(lines)"""

new2 = '''def _sheet_xml(rows_data):
    """Build worksheet XML from (label, value, style) tuples. value can be float or None."""
    # First pass: build rows and count
    row_lines = []
    r = 1
    for item in rows_data:
        if item is None:
            r += 1
            continue
        if isinstance(item, str):
            item = (item, None, 0)
        label, val, style = item if len(item) == 3 else (item[0], item[1] if len(item) > 1 else None, 0)
        row_lines.append('<row r="%d">' % r)
        if label is not None and str(label).strip():
            row_lines.append('<c r="A%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(str(label))))
        if val is not None:
            if isinstance(val, str):
                row_lines.append('<c r="B%d" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>' % (r, escape(val)))
            else:
                row_lines.append('<c r="B%d" s="%d"><v>%s</v></c>' % (r, style, val))
        row_lines.append('</row>')
        r += 1
    max_row = r - 1
    if max_row < 1:
        max_row = 1
    lines = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">',
             '<dimension ref="A1:B%d"/>' % max_row,
             '<sheetData>']
    lines.extend(row_lines)
    lines.append('</sheetData>')
    lines.append('<cols><col min="1" max="1" width="44" customWidth="1"/><col min="2" max="2" width="18" customWidth="1"/></cols>')
    lines.append('</worksheet>')
    return "\\n".join(lines)'''

assert old2 in src, "old _sheet_xml not found"
src = src.replace(old2, new2, 1)
open("src/bp/product/xlsx.py", "w", encoding="utf-8").write(src)
print("patched")
