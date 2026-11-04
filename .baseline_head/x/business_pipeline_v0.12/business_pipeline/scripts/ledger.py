"""The counted numbers the documents store, measured and rewritten in one command.

Three lanes commit into this tree, and a number written into prose goes stale within
minutes: the suite count moved 3410 -> 3412 -> 3425 in twenty minutes, and a
reachability ledger was stale twice in one day.  Every one of those was repaired by
hand, from a throwaway script in a temp folder.

    python scripts/ledger.py            # report, and exit 1 if anything is stale
    python scripts/ledger.py --check    # the same, quiet
    python scripts/ledger.py --fix      # rewrite only the numbers this script owns

What it **owns** - it will rewrite these, because they are data:

* the suite count in `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`
* the build in `docs/HOME.md`, `docs/HANDOFF.md`, and `src/bp/build.py` (the constant
  the page paints into the top bar, D-PM-07) - each must equal the newest
  `docs/CHANGELOG.md` build, which is the authority

What it only **reports** - a test expectation is code, and a person changes it:

* the worksheets no shelf offers (`tests/test_worksheet_reachability.KNOWN_UNSERVED`)
* the profiles no shelf reaches (`tests/test_subject_management_acceptance`, E-mgt-043)

It reads the documents with `tests/test_docs_sync.py`'s own parsers, so the script and
the test cannot disagree about what a document says: there is one reader, not two.
Standard library only; it touches no product module and no test.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# The measurement must be the canonical one.  `python -c` and pytest both have the app
# directory on sys.path and count 3478 where a script run from `scripts/` counts 3476 -
# discovered the hard way: this script reported a 2-test gap that was its own.  Put the
# app directory on the path first, then the two the tests use.
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "tests"))

import test_docs_sync as D                                        # noqa: E402  (path set above)
from bp.product import framework_profiles, subjects               # noqa: E402


#: (document, the test's own parser, the same pattern for rewriting, what it is).
#: Parser and pattern are `test_docs_sync`'s, imported rather than copied.
COUNT_CLAIMS = (
    ("docs/HOME.md", D._home_test_count, r"\*\*(\d+)\s+tests\*\*"),
    ("docs/HANDOFF.md", D._handoff_test_count, r"Tests\s*:\s*(\d+)\s+tests"),
    ("docs/CONTRIBUTORS.md", D._contributors_test_count, r"currently\s+(\d+)\s+tests"),
)
BUILD_CLAIMS = (
    ("docs/HOME.md", D._home_build, r"Last verified with build \*\*(\d+\.\d+)\*\*"),
    ("docs/HANDOFF.md", D._handoff_build, r"Build\s*:\s*(\d+\.\d+)"),
    ("src/bp/build.py", None, r'VERSION = "(\d+\.\d+)"'),
)


def _read(relative):
    with open(os.path.join(ROOT, *relative.split("/")), encoding="utf-8") as stream:
        return stream.read()


def _write(relative, text):
    path = os.path.join(ROOT, *relative.split("/"))
    with open(path, "w", encoding="utf-8", newline="") as stream:
        stream.write(text)


def measures(settle=1.5):
    """The count and the build, measured twice.

    A discovery count is not stable while another lane is writing: this script's first
    run read 3476 against a documented 3478, and 3478 three seconds later.  A fixer
    that trusted one reading would have written a wrong number into three documents and
    been "repaired" again by the next lane.  So the count is taken twice, and a tree
    that gives two answers is reported as moving, never written to.
    """
    first = D._suite_count()
    time.sleep(settle)
    D._SUITE_COUNT = None                    # force a fresh discovery
    second = D._suite_count()
    if first != second:
        raise RuntimeError("the tree is being written right now (count read %d, then %d)"
                           % (first, second))
    return second, D._newest_build(_read("docs/CHANGELOG.md"))


def _stale():
    """Every stored number that is not the measured one, as (where, was, should be)."""
    count, newest = measures()
    out = []
    for path, parse, pattern in COUNT_CLAIMS:
        try:
            stored = parse(_read(path))
        except AssertionError as problem:
            out.append((path, "unreadable (%s)" % problem, count))
            continue
        if stored != count:
            out.append((path, stored, count))
    for path, parse, pattern in BUILD_CLAIMS:
        try:
            stored = parse(_read(path)) if parse else D._claim(_read(path), pattern, path)
        except AssertionError as problem:
            out.append((path, "unreadable (%s)" % problem, newest))
            continue
        if str(stored) != newest:
            out.append((path, stored, newest))
    return out, count, newest


def _ledgers():
    """The two sets a person must move by hand, reported with the measured values."""
    rows = []
    try:
        from test_worksheet_reachability import KNOWN_UNSERVED, served
        unserved = set(subjects.WORKSHEETS) - served()
        rows.append(("worksheets no shelf offers", sorted(unserved),
                     "" if unserved == KNOWN_UNSERVED else
                     "the set MOVED: wire the worksheet or ledger it in "
                     "tests/test_worksheet_reachability.py"))
    except Exception as problem:                                  # noqa: BLE001
        rows.append(("worksheets no shelf offers", None, "unreadable: %s" % problem))
    try:
        reached = set()
        for row in subjects.catalogue()["subjects"]:
            for sheet in subjects.detail(row["id"])["worksheets"]:
                reached.add(sheet["template"])
        unreachable = sorted(t for t in framework_profiles.PROFILES if t not in reached)
        rows.append(("profiles no shelf reaches", unreachable,
                     "E-mgt-043 asserts a literal: re-measure it, do not re-copy it"))
    except Exception as problem:                                  # noqa: BLE001
        rows.append(("profiles no shelf reaches", None, "unreadable: %s" % problem))
    return rows


def check(quiet=False):
    try:
        stale, count, newest = _stale()
    except RuntimeError as moving:
        print("ledger: %s - nothing checked and nothing written; re-run when it settles"
              % moving)
        return 2
    if not quiet:
        print("measured: %d tests, build %s (the newest docs/CHANGELOG.md bullet)"
              % (count, newest))
        for name, value, note in _ledgers():
            if isinstance(value, list):
                print("  %-28s %d: %s" % (name, len(value), ", ".join(value) or "-"))
            else:
                print("  %-28s %s" % (name, value))
            if note:
                print("      %s" % note)
    if not stale:
        print("ledger: every stored number is the measured one")
        return 0
    print("ledger: %d stored number(s) are stale" % len(stale))
    for path, was, should in stale:
        print("  %-24s has %s, the tree is %s" % (path, was, should))
    print("fix with: python scripts/ledger.py --fix")
    return 1


def fix():
    """Rewrite the numbers this script owns; never a test, never the prose around them."""
    try:
        stale, count, newest = _stale()
    except RuntimeError as moving:
        print("ledger: %s - refusing to write a number the tree may not keep" % moving)
        return 2
    if not stale:
        print("ledger: nothing to fix - every stored number is the measured one")
        return 0
    wanted = {path for path, _, _ in stale}
    for path in sorted(wanted):
        text = before = _read(path)
        for claim_path, _, pattern in COUNT_CLAIMS:
            if claim_path == path:
                text = D._replace_group(text, pattern, str(count))
        for claim_path, _, pattern in BUILD_CLAIMS:
            if claim_path == path:
                text = D._replace_group(text, pattern, newest)
        if text != before:
            _write(path, text)
            print("wrote %s" % path)
    remaining = _stale()[0]
    if remaining:
        print("ledger: still stale after the fix")
        for path, was, should in remaining:
            print("  %-24s has %s, the tree is %s" % (path, was, should))
        return 1
    print("ledger: fixed - %d number(s) now match the tree" % len(stale))
    return 0


if __name__ == "__main__":
    argument = (sys.argv[1] if len(sys.argv) > 1 else "").lower()
    sys.exit(fix() if argument == "--fix" else check(quiet=argument == "--check"))

