import ast, json, re

src = open("src/bp/product/income_statement.py").read()
start = src.find("def _classify_account")
end = src.find("\ndef ", start + 1)
func_src = src[start:end]
tree = ast.parse(func_src)

patterns = []
# Walk the function body, find If nodes with test containing re.search, and the return in the body
def extract_if(node):
    global patterns
    if isinstance(node, ast.If):
        # try to get the pattern from the test
        test = node.test
        # handle 'or' (BoolOp)
        # We'll extract re.search calls
        searches = []
        def find_search(n):
            if isinstance(n, ast.Call):
                func = n.func
                if isinstance(func, ast.Attribute) and func.attr == "search":
                    if n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str):
                        searches.append(n.args[0].value)
            for child in ast.iter_child_nodes(n):
                find_search(child)
        find_search(test)
        # find return in body
        for stmt in node.body:
            if isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Tuple):
                elems = stmt.value.elts
                if len(elems) == 2 and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in elems):
                    kind = elems[0].value
                    line = elems[1].value
                    for pat in searches:
                        patterns.append({"pattern": pat, "kind": kind, "line": line})
        # recurse
        for stmt in node.body + node.orelse:
            extract_if(stmt)
    for stmt in getattr(node, "body", []) + getattr(node, "orelse", []):
        if isinstance(stmt, (ast.If, ast.For, ast.While)):
            extract_if(stmt)

# The function body
func_node = tree.body[0]
for stmt in func_node.body:
    extract_if(stmt)

print("extracted:", len(patterns))
# Show a few
for p in patterns[:10]:
    print(" ", p["pattern"][:50], "->", p["kind"], p["line"])
json.dump(patterns, open("src/bp/product/data/classifier_patterns.json", "w"), indent=2)
