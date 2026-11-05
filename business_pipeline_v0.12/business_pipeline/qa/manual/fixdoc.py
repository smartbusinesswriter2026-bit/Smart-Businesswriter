p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
target = lines[1960]
lines[1960] = target.replace("\\", "")
open(p, "w").write("\n".join(lines) + "\n")
print("fixed:", repr(lines[1960]))
