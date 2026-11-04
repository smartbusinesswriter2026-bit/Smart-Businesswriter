"""List every top-level dict assignment in a source file, with its byte span."""

import ast
import sys


def main(path, names):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        name = target.id
        if names and name not in names:
            continue
        value = node.value
        if isinstance(value, ast.Dict):
            keys = [k.value for k in value.keys if isinstance(k, ast.Constant)]
            blocks = None
            for k in value.keys:
                if isinstance(k, ast.Constant) and k.value == "blocks":
                    v = value.values[value.keys.index(k)]
                    if isinstance(v, ast.List):
                        out = []
                        for elt in v.elts:
                            if isinstance(elt, ast.Dict):
                                bk = [kk.value for kk in elt.keys if isinstance(kk, ast.Constant)]
                                out.append(bk[0] if bk else "?")
                        blocks = out
            print("line %-6d %-22s keys=%s" % (node.lineno, name, keys))
            if blocks:
                print("           blocks=%s" % (blocks,))


if __name__ == "__main__":
    main(sys.argv[1], set(sys.argv[2:]))
