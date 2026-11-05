import sys, os, json
sys.path.insert(0, "src")
from bp.product import statements as S
from bp.product import income_statement as IS
from bp.product import schedules as SCH

# Seed RULES
rules_seed = []
for i, rule in enumerate(S.RULES):
    rules_seed.append({
        "pattern": rule[0],
        "type": rule[1],
        "section": rule[2],
        "line": rule[3],
        "role": rule[4],
        "activity": rule[5],
        "contra": rule[6],
    })

# Seed classifier patterns: extract from _classify_account source
# We'll store as ordered list of (pattern, kind, line) by parsing the function
import re
src = open("src/bp/product/income_statement.py").read()
# Find _classify_account function
start = src.find("def _classify_account")
end = src.find("\n\n", start)
func_src = src[start:end]
# Extract if re.search(pattern, a) ... return (kind, line)
patterns = []
for m in re.finditer(r'if re\.search\(r"([^"]+)", a\):\s*\n\s*return \("([^"]+)", "([^"]+)"\)', func_src):
    patterns.append({"pattern": m.group(1), "kind": m.group(2), "line": m.group(3)})
# Also handle re.search with a variable or multi-line
# The generic fallback
# Store as list
classifier_seed = patterns

# Seed SCHEMAS
schemas_seed = {}
for kind, schema in SCH.SCHEMAS.items():
    schemas_seed[kind] = {
        "request": schema["request"],
        "required": list(schema.get("required", ())),
        "require_all": list(schema.get("require_all", ())),
        "require_any": list(schema.get("require_any", ())) if schema.get("require_any") else [],
        "figures": [[k, p, s] for k, p, s in schema.get("figures", ())],
    }

seed = {
    "version": 1,
    "rules": rules_seed,
    "classifier": classifier_seed,
    "schemas": schemas_seed,
}

out_path = os.path.join("src", "bp", "product", "data", "tier1_tables.json")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(seed, f, indent=2, ensure_ascii=False)
print("RULES:", len(rules_seed))
print("classifier patterns:", len(classifier_seed))
print("schemas:", len(schemas_seed))
print("written to:", out_path)
