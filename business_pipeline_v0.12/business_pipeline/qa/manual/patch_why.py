p = "src/bp/product/statements.py"
text = open(p, encoding="utf-8").read()
old = '        "why": "cue \'" + cue + "\' in: " + (sentence or cue),'
new = '        "why": ("Trial balance read from Dr/Cr markers." if cue == "trial balance" else "cue \'" + cue + "\' in: " + (sentence or cue)),'
assert old in text, "old not found"
text = text.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(text)
print("patched")
