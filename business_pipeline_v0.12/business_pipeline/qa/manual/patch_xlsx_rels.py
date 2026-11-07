src = open("src/bp/product/xlsx.py", encoding="utf-8").read()

# Fix 1: Add styles.xml relationship to workbook.xml.rels
old_rels = '''SHEET_REL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}
</Relationships>"""'''

new_rels = '''SHEET_REL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}
<Relationship Id="rId{sid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""'''

assert old_rels in src
src = src.replace(old_rels, new_rels, 1)

# Fix 2: Update the rels generation to include styles relationship ID
old_rel_gen = '''        rel_entries = []
        for i, name in enumerate(sheet_names, 1):
            sheet_entries.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
        wb_xml = WORKBOOK.replace("{sheets}", "\\n".join(sheet_entries))
        z.writestr("xl/workbook.xml", wb_xml)
        z.writestr("xl/_rels/workbook.xml.rels", SHEET_REL.replace("{rels}", "\\n".join(rel_entries)))'''

new_rel_gen = '''        rel_entries = []
        for i, name in enumerate(sheet_names, 1):
            sheet_entries.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
        # Add styles relationship (required by Excel)
        styles_rid = len(sheet_names) + 1
        rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % styles_rid)
        wb_xml = WORKBOOK.replace("{sheets}", "\\n".join(sheet_entries))
        # Add workbookPr and calcPr (Excel expects these)
        wb_xml = wb_xml.replace("<sheets>", "<workbookPr/><bookViews><workbookView/></bookViews><sheets>")
        wb_xml = wb_xml.replace("</sheets>", "</sheets><calcPr calcId=\\"124519\\" fullCalcOnLoad=\\"1\\"/>")
        z.writestr("xl/workbook.xml", wb_xml)
        z.writestr("xl/_rels/workbook.xml.rels", SHEET_REL.replace("{rels}", "\\n".join(rel_entries)).replace("{sid}", str(styles_rid)))'''

assert old_rel_gen in src
src = src.replace(old_rel_gen, new_rel_gen, 1)

# Fix 3: Update SHEET_REL template to use {sid} for styles rid
old_sheet_rel = '''SHEET_REL = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
{rels}
<Relationship Id="rId{sid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""'''
# The {sid} replacement is already handled above via .replace("{sid}", ...)
# But the template still has {sid} placeholder. Let me just use a fixed approach.
# Actually, let me simplify: just put styles rid at the end with a fixed formula.

open("src/bp/product/xlsx.py", "w", encoding="utf-8").write(src)
print("patched")
PYEOF
python qa/manual/patch_xlsx_rels.py 2>&1 | Select-Object -Last 5