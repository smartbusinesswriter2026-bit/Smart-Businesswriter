p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
# Use a regular (non-raw) string so \\ becomes one backslash in the file.
lines[1987] = '    m_add = re.search(r"additional capital[^\\d]*([\\d,]+(?:\\.\\d+)?)", text, re.I)'.replace("\\\\", "\\")
open(p, "w").write("\n".join(lines) + "\n")
print(repr(lines[1987]))
import ast; ast.parse(open(p).read()); print("syntax OK")
