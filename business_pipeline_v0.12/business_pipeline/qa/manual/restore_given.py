p = "src/bp/product/income_statement.py"
lines = open(p).read().splitlines()
insert_at = 626  # 0-based index; insert before line 627 (blank line before detect_eps)
block = [
"",
"def detect_given_balances(text: str) -> bool:",
'    """Return True if the problem lists multiple account balances with amounts."""',
"    low = text.lower()",
"    matches = 0",
"    for pattern, _ in GIVEN_BALANCES_DETECTORS:",
"        if re.search(pattern, low):",
"            matches += 1",
"    return matches >= 2  # Need at least 2 account types to be a \"given balances\" problem",
"",
]
lines = lines[:insert_at] + block + lines[insert_at:]
open(p, "w").write("\n".join(lines) + "\n")
print("done")
# verify
import ast; ast.parse(open(p).read()); print("syntax OK")
