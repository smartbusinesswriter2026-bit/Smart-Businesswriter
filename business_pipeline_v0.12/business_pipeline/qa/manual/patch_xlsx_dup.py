src = open("src/bp/product/xlsx.py", encoding="utf-8").read()

# Remove the duplicate Notes sheet block
old_block = '''    # Notes sheet
    notes_text = (record.get("statements") or {}).get("notes", "")
    if notes_text:
        rows = [("Notes", None, 2)]
        rows.append(None)
        for line in notes_text.splitlines():
            rows.append((line, None, 0))
        sheet_names.append("Notes")
        sheet_defs.append(("Notes", _sheet_xml_text(rows)))
'''

new_block = '''    # Notes sheet is already created from _SHEET_NAMES above (key="notes").
    # Do not create a duplicate.
'''

assert old_block in src, "old block not found"
src = src.replace(old_block, new_block, 1)
open("src/bp/product/xlsx.py", "w", encoding="utf-8").write(src)
print("patched")
