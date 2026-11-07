import zipfile, io, openpyxl

# Generate reference with openpyxl
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Income Statement"
ws["A1"] = "Income Statement"
ws["A2"] = "Period: 2026-01-01 to 2026-12-31"
ws["B5"] = 200000
ws["B5"].number_format = "#,##0.00"
buf = io.BytesIO()
wb.save(buf)
buf.seek(0)
ref_zip = zipfile.ZipFile(buf)

# Load my file
my_zip = zipfile.ZipFile("C:/Users/Roderick/AppData/Local/Temp/opencode/final_check.xlsx")

print("Reference files:", sorted(ref_zip.namelist()))
print("My files:", sorted(my_zip.namelist()))
print()

# Compare content types
print("=== Reference [Content_Types].xml ===")
print(ref_zip.read("[Content_Types].xml").decode("utf-8"))
print()
print("=== My [Content_Types].xml ===")
print(my_zip.read("[Content_Types].xml").decode("utf-8"))
