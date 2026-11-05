p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
lines[1987] = '    m_add = re.search(r"additional capital[^\\d]*([\\d,]+(?:\\.\\d+)?)", text, re.I)'
open(p, "w").write("\n".join(lines) + "\n")
print(repr(lines[1987]))
import ast; ast.parse(open(p).read()); print("syntax OK")
