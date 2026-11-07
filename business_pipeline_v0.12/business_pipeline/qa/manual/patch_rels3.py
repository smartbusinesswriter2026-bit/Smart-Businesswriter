src = open("src/bp/product/xlsx.py", encoding="utf-8").read()

old = '''        wb_xml = WORKBOOK.replace("{sheets}", "\\n".join(sheet_entries))
        z.writestr("xl/workbook.xml", wb_xml)
        z.writestr("xl/_rels/workbook.xml.rels", SHEET_REL.replace("{rels}", "\\n".join(rel_entries)))'''

new = '''        # Add styles relationship (required by Excel)
        styles_rid = len(sheet_names) + 1
        rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' % styles_rid)
        wb_xml = WORKBOOK.replace("{sheets}", "\\n".join(sheet_entries))
        # Add workbookPr, bookViews, calcPr (Excel expects these)
        wb_xml = wb_xml.replace("<sheets>", "<workbookPr/><bookViews><workbookView/></bookViews><sheets>")
        wb_xml = wb_xml.replace("</sheets>", "</sheets><calcPr calcId=\\"124519\\" fullCalcOnLoad=\\"1\\"/>")
        z.writestr("xl/workbook.xml", wb_xml)
        # Build rels with styles relationship
        rels_xml = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\\n'
        rels_xml += '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\\n'
        rels_xml += "\\n".join(rel_entries)
        rels_xml += "\\n</Relationships>"
        z.writestr("xl/_rels/workbook.xml.rels", rels_xml)'''

assert old in src, "old not found"
src = src.replace(old, new, 1)
open("src/bp/product/xlsx.py", "w", encoding="utf-8").write(src)
print("patched")
