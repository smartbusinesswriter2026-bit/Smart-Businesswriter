src = open("web/index.html", encoding="utf-8").read()
# Fix the revoke timeout for all downloads (xlsx, docx, explanation)
src = src.replace("setTimeout(function () { URL.revokeObjectURL(url); link.remove(); }, 0);",
                  "setTimeout(function () { URL.revokeObjectURL(url); link.remove(); }, 4000);")
open("web/index.html", "w", encoding="utf-8").write(src)
print("patched")
