"""Print the failure list of one unittest run."""
import re
import sys
from collections import Counter

LINE = re.compile(r"^(FAIL|ERROR):\s+(\S+)\s+\(([^)]+)\)")


def main(path):
    found = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = LINE.match(line.strip())
            if match:
                kind, test, where = match.groups()
                found.append((kind, where, test))
    print("%s: %d problems" % (path, len(found)))
    print()
    for kind in ("FAIL", "ERROR"):
        rows = sorted(item for item in found if item[0] == kind)
        print("--- %s (%d) ---" % (kind, len(rows)))
        for _kind, where, test in rows:
            print("   %s.%s" % (where, test))
        print()
    modules = Counter(item[1].split(".")[0] for item in found)
    print("by module:")
    for name, count in modules.most_common():
        print("   %-46s %d" % (name, count))


if __name__ == "__main__":
    main(sys.argv[1])
