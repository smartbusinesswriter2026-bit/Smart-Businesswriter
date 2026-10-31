"""Locate the byte span of a top-level dict assignment in a Python source file."""

import sys


def block_span(src, name):
    """Return (start, end) of `name = { ... }` by brace matching."""
    i = src.find(name + " = {")
    if i == -1:
        raise SystemExit("not found: " + name)
    j = src.index("{", i)
    depth = 0
    k = j
    instr = None
    while k < len(src):
        c = src[k]
        if instr:
            if c == "\\":
                k += 2
                continue
            if c == instr:
                instr = None
        else:
            if c in "\"'":
                instr = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i, k + 1
        k += 1
    raise SystemExit("unbalanced: " + name)


if __name__ == "__main__":
    path = sys.argv[1]
    src = open(path, encoding="utf-8").read()
    for name in sys.argv[2:]:
        a, b = block_span(src, name)
        print("%s span %d %d len %d" % (name, a, b, b - a))
        print("   starts: %r" % src[a:a + 70])
        print("   ends  : %r" % src[b - 70:b])
