p = "src/bp/product/statements.py"
lines = open(p).read().splitlines()
# Replace lines 1988-1990 (1-based) with clean code
old = lines[1987:1990]
lines[1987:1990] = [
    '    additional = Decimal(0)',
    '    m_add = re.search(r"additional capital.{0,40}", text, re.I)',
    '    if m_add:',
    '        nums = re.findall(r"[0-9][0-9,]*(?:\\.[0-9]+)?", m_add.group(0))',
    '        if nums:',
    '            additional = Decimal(nums[-1].replace(",", ""))',
]
open(p, "w").write("\n".join(lines) + "\n")
print("done")
import ast; ast.parse(open(p).read()); print("syntax OK")
# remove the now-duplicate additional=0 line above
