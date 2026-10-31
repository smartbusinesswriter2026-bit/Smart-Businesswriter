import sys, os, io
sys.path.insert(0, "src")
from bp.product import documents
out = io.open(r"D:\SMART BUSINESSWRITER\.uitmp\owner_docs.txt", "w", encoding="utf-8")
for name in ("1.docx", "2.docx"):
    path = os.path.join(r"D:\SMART BUSINESSWRITER\TESTS\INITIAL TEST", name)
    data = open(path, "rb").read()
    rec = documents.extract(name, data)
    out.write("=" * 78 + "\n")
    out.write("%s | kind: %s | bytes: %s | provenance: %s\n" % (name, rec["kind"], rec["bytes"], rec["provenance"]))
    out.write("warnings: %s\n" % (rec.get("warnings"),))
    out.write("-" * 78 + "\n")
    out.write(rec["text"] + "\n")
out.close()
print("written")
