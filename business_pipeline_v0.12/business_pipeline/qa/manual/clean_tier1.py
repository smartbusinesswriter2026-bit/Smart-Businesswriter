lines = open("src/bp/product/tier1_tables.py").read().splitlines()
lines = [l for l in lines if "echo" not in l and "PYEOF" not in l and "python qa/manual" not in l]
open("src/bp/product/tier1_tables.py", "w").write("\n".join(lines) + "\n")
print("cleaned, lines:", len(lines))
import ast
ast.parse(open("src/bp/product/tier1_tables.py").read())
print("syntax OK")
