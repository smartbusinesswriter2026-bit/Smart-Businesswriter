"""Second probe: topological ordering and capture-group patterns in the engine."""
import os
import re
import sys

ROOT = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import financial_computations as fc  # noqa: E402

specs = fc.REGISTRY.all()
order = {s.id: i for i, s in enumerate(specs)}
owner = {s.output_name: s for s in specs}

print("=" * 72)
print("A. registration order vs depends_on")
print("=" * 72)
bad = []
for s in specs:
    for dep in s.depends_on:
        producer = owner.get(dep)
        if producer is not None and producer.section == s.section:
            if order[producer.id] > order[s.id]:
                bad.append((s.id, dep, producer.id))
print("  inversions inside a section:", len(bad))
for b in bad:
    print("     consumer %-28s needs %-22s produced later by %s" % b)

print()
print("=" * 72)
print("B. COMMON_PATTERNS whose FIRST capture group is not the number")
print("=" * 72)
numeric = re.compile(r"\[\\?d|0-9")
broken = []
for name, pattern in fc.COMMON_PATTERNS.items():
    try:
        re.compile(pattern, re.I)
    except re.error:
        broken.append((name, pattern, "does not compile"))
        continue
    # find the body of the first capturing group by scanning the pattern text
    src = pattern
    group1 = None
    i = 0
    depth = 0
    while i < len(src):
        ch = src[i]
        if ch == "\\":
            i += 2
            continue
        if ch == "(":
            if src[i:i + 3] == "(?:":
                i += 3
                continue
            if src[i:i + 2] == "(?":
                j = src.find(")", i)
                if j == -1:
                    break
                i = j + 1
                continue
            depth += 1
            if depth == 1:
                start = i + 1
                d2 = 1
                j = start
                while j < len(src) and d2:
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "(":
                        if src[j:j + 3] == "(?:":
                            j += 3
                            continue
                        d2 += 1
                    elif src[j] == ")":
                        d2 -= 1
                    j += 1
                group1 = src[start:j - 1]
                break
        i += 1
    if group1 is None:
        broken.append((name, pattern, "no capture group"))
    elif not numeric.search(group1):
        broken.append((name, pattern, "group(1) = %r" % group1))
print("  broken patterns:", len(broken))
for name, pattern, why in broken:
    print("     %-24s %s" % (name, why))
    print("        %s" % pattern)
