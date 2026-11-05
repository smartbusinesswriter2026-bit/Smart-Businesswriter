p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
# Line 130 (1-based) = index 129: rename RULES = ( to _RULES_SEED = (
assert lines[129].strip() == "RULES = (", repr(lines[129])
lines[129] = lines[129].replace("RULES = (", "_RULES_SEED = (", 1)
# After line 176 (index 175), insert import + assignment
insert_at = 176  # 0-based index after line 176
lines = lines[:insert_at] + [
    "",
    "from . import tier1_tables as _t1",
    "RULES = _t1.RULES",
] + lines[insert_at:]
open(p, "w").write("\n".join(lines) + "\n")
print("done")
import ast; ast.parse(open(p).read()); print("syntax OK")
