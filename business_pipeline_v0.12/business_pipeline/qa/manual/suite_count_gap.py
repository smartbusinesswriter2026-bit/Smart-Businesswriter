"""Which tests does the loader count but the runner never runs?

The docs-state contract reads the suite with
``unittest.TestLoader().discover("tests").countTestCases()`` (3828), while a
run of the same suite reports "Ran 3821 tests".  This finds the difference.

    python qa/manual/suite_count_gap.py <suite-err-file>
"""

import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(os.path.dirname(HERE))
TESTS = os.path.join(PROJECT, "tests")
sys.path.insert(0, os.path.join(PROJECT, "src"))
sys.path.insert(0, PROJECT)

VERBOSE = re.compile(r"^(\S+) \(([^)]+)\)(?: \.\.\.|$)")


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            for sub in flatten(item):
                yield sub
        else:
            yield item


def main():
    log = sys.argv[1]
    loaded = set()
    for case in flatten(unittest.TestLoader().discover(start_dir=TESTS)):
        loaded.add(case.id())

    ran = set()
    with open(log, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            match = VERBOSE.match(line.strip())
            if match:
                ran.add(match.group(2))

    only_loaded = sorted(loaded - ran)
    only_ran = sorted(ran - loaded)
    print("loader count : %d" % len(loaded))
    print("ran ids      : %d" % len(ran))
    print("counted but not run : %d" % len(only_loaded))
    for item in only_loaded[:30]:
        print("   " + item)
    print("ran but not counted : %d" % len(only_ran))
    for item in only_ran[:30]:
        print("   " + item)


if __name__ == "__main__":
    main()
