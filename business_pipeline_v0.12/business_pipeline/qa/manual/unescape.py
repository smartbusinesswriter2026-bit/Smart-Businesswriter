p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
start, end = 1960, 2100  # 1-based inclusive
for i in range(start-1, end):
    lines[i] = lines[i].replace("\\\\", "\\").replace('\\"', '"')
open(p, "w").write("\n".join(lines) + "\n")
print("done")
# verify syntax
import ast
ast.parse(open(p).read())
print("syntax OK")
