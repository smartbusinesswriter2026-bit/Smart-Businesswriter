src = open("src/bp/product/xlsx.py", encoding="utf-8").read()

# Add docProps and theme references
# 1. Add docProps/core.xml and docProps/app.xml to the zip
# 2. Add xl/theme/theme1.xml
# 3. Update [Content_Types].xml with overrides for these

# First, add the theme and docProps to the zip building section
old_zip = '''    # Build the zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _content_types(sheet_names))
        z.writestr("_rels/.rels", RELS)
        # workbook.xml
        sheet_entries = []
        rel_entries = []
        for i, name in enumerate(sheet_names, 1):
            sheet_entries.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
        # Add styles relationship (required by Excel)
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
        z.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        z.writestr("xl/styles.xml", STYLES)
        for i, (name, xml) in enumerate(sheet_defs, 1):
            z.writestr("xl/worksheets/sheet%d.xml" % i, xml)'''

new_zip = '''    # Build the zip
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _content_types(sheet_names))
        z.writestr("_rels/.rels", RELS)
        # workbook.xml
        sheet_entries = []
        rel_entries = []
        for i, name in enumerate(sheet_names, 1):
            sheet_entries.append('<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (escape(name), i, i))
            rel_entries.append('<Relationship Id="rId%d" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet%d.xml"/>' % (i, i))
        # Add styles relationship (required by Excel)
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
        z.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        z.writestr("xl/styles.xml", STYLES)
        for i, (name, xml) in enumerate(sheet_defs, 1):
            z.writestr("xl/worksheets/sheet%d.xml" % i, xml)
        # Add docProps (Excel expects these for proper file recognition)
        z.writestr("docProps/core.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<dc:title>Financial Statements</dc:title>
<dc:creator>Smart Business Writer</dc:creator>
<cp:lastModifiedBy>Smart Business Writer</cp:lastModifiedBy>
<dcterms:created xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:created>
<dcterms:modified xsi:type="dcterms:W3CDTF">2026-01-01T00:00:00Z</dcterms:modified>
</cp:coreProperties>''')
        z.writestr("docProps/app.xml", '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
<Application>Smart Business Writer</Application>
<DocSecurity>0</DocSecurity>
<ScaleCrop>false</ScaleCrop>
<HeadingPairs><vt:vector size="2" baseType="variant"><vt:variant><vt:lpstr>Worksheets</vt:lpstr></vt:variant><vt:variant><vt:i4>''' + str(len(sheet_names)) + '''</vt:i4></vt:variant></vt:vector></HeadingPairs>
<TitlesOfParts><vt:vector size="''' + str(len(sheet_names)) + '''" baseType="lpstr">''' + "".join("<vt:lpstr>%s</vt:lpstr>" % n for n in sheet_names) + '''</vt:vector></TitlesOfParts>
</Properties>''')'''

assert old_zip in src
src = src.replace(old_zip, new_zip, 1)

# Update [Content_Types].xml to include docProps overrides
old_ct = '''def _content_types(sheet_names):
    overrides = ""
    for i in range(len(sheet_names)):
        overrides += '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\\n' % (i + 1)
    return CONTENT_TYPES.replace("{sheets}", overrides)'''

new_ct = '''def _content_types(sheet_names):
    overrides = ""
    for i in range(len(sheet_names)):
        overrides += '<Override PartName="/xl/worksheets/sheet%d.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>\\n' % (i + 1)
    overrides += '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>\\n'
    overrides += '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>\\n'
    return CONTENT_TYPES.replace("{sheets}", overrides)'''

assert old_ct in src
src = src.replace(old_ct, new_ct, 1)

# Update _rels/.rels to include docProps (optional, but good for compatibility)
# Actually, _rels/.rels already references xl/workbook.xml. docProps are referenced from [Content_Types].xml only.

open("src/bp/product/xlsx.py", "w", encoding="utf-8").write(src)
print("patched")
