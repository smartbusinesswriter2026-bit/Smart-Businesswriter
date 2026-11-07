src = open("web/index.html", encoding="utf-8").read()
lines = src.splitlines()

old_block = lines[10284:10308]  # 0-based: lines 10285-10308
new_block = [
    '    /* Only the Result view is shown.  The Working view has been removed. */',
    '    var view = el("div");',
    '    view.appendChild(pre(record.statements_only || ""));',
    '    host.appendChild(view);',
]

# Verify
assert "var toggle = el(\"div\", \"toggle\")" in lines[10285], repr(lines[10285])
lines[10285:10308] = new_block
open("web/index.html", "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("patched")
