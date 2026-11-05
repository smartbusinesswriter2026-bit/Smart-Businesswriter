import re
src = open("src/bp/product/income_statement.py").read()
start = src.find("def _classify_account")
end = src.find("\n\n", start)
func = src[start:end]
# Pattern: if re.search(r"...pattern...", a): \n ... return ("kind", "line")
ms = re.findall(r'if re\.search\(r"([^"]+)", a\):', func)
print("simple pattern count:", len(ms))
# Now extract returns
# Use a different approach: find all (pattern, return) pairs by scanning lines
patterns = []
lines = func.splitlines()
i = 0
while i < len(lines):
    line = lines[i]
    m = re.search(r'if re\.search\(r"([^"]+)", a\):', line)
    if m and i + 1 < len(lines):
        # look for return on next non-empty line
        j = i + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        rm = re.search(r'return \("([^"]+)", "([^"]+)"\)', lines[j]) if j < len(lines) else None
        if rm:
            patterns.append({"pattern": m.group(1), "kind": rm.group(1), "line": rm.group(2)})
    i += 1
print("extracted:", len(patterns))
import json
json.dump(patterns, open("src/bp/product/data/classifier_patterns.json", "w"), indent=2)
