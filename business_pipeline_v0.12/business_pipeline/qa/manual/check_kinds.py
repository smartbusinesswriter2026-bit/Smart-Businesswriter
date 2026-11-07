import re
src = open("src/bp/product/income_statement.py", encoding="utf-8").read()
kinds = set()
for m in re.finditer(r'return \("([^"]+)",', src):
    kinds.add(m.group(1))
print("kinds:", sorted(kinds))
