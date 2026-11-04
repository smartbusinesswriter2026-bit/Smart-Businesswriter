"""Report duplicate top-level definitions in a module (a shadowing bug class).

Usage:  python qa/probe_duplicates.py src/bp/product/chat.py [more.py ...]
"""
import ast
import sys


def main(argv):
    for path in argv[1:]:
        with open(path, encoding="utf-8") as handle:
            tree = ast.parse(handle.read(), path)
        seen = {}
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                seen.setdefault(node.name, []).append(node.lineno)
        duplicates = {name: lines for name, lines in seen.items() if len(lines) > 1}
        print("%s: %d duplicate definitions" % (path, len(duplicates)))
        for name in sorted(duplicates):
            print("   %-28s lines %s" % (name, duplicates[name]))


if __name__ == "__main__":
    main(sys.argv)
