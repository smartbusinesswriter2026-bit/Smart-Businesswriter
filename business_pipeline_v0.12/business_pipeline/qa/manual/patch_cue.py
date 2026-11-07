p = "src/bp/product/statements.py"
text = open(p, encoding="utf-8").read()
old = '        return "trial_balance", "Dr/Cr markers", text[:60]'
new = '        return "trial_balance", "trial balance", "the instruction carries Dr/Cr markers"'
assert old in text, "old not found"
text = text.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(text)
print("patched")
