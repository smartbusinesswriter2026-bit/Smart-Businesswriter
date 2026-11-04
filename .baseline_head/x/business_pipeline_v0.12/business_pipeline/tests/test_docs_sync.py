"""Docs-state sync tests: fail when the documentation drifts from the code.

These tests are the mirror image of the repo's own rule that "a broken map is
worse than no map" (docs/HOME.md).  Every expectation is taken from a source
that is NOT the document being checked:

* the test count comes from loading the real suite
  (``unittest.TestLoader().discover("tests")``), not from any document;
* the build version comes from the newest entry in ``docs/CHANGELOG.md``;
* the method ids come from the imported ``bp.methods.LIBRARY``;
* the decision ids come from the mentions in the documents and the rows in
  ``docs/DECISIONS.md`` (one direction only: a mentioned id must have a row,
  a row need not be mentioned);
* the document spine comes from the files that exist in ``docs/``.

So no assertion compares a document with itself, and every one of them can
fail: if a document's number, version, list or link drifts, the test fails
with the two values side by side.

Run with the normal suite:

    $env:PYTHONPATH="src"; python -m unittest discover -s tests
"""

import fnmatch
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DOCS = REPO / "docs"
TESTS = REPO / "tests"
README = REPO / "README.md"

# The method library is the code-side truth for the method ids.  Import it from
# this checkout, so the test does not depend on the caller's working directory.
_SRC = REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from bp.methods import LIBRARY  # noqa: E402  (path set above)

# --- a bare method id: snake_case, no dots, no spaces -------------------------
_ID_RE = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
# --- one entry of the README method list: 'id' or 'id (description)' ---------
_README_ITEM_RE = re.compile(r"([a-z][a-z0-9]*(?:_[a-z0-9]+)*)\s*(?:\(.*\))?")
# --- a decision id as written in the documents (B-001, B-001a) ----------------
_DECISION_RE = re.compile(r"B-\d{3}[a-z]?")

_SUITE_COUNT = None


def _read(path):
    return path.read_text(encoding="utf-8")


def _suite_count():
    """Count the real suite: load every test module and count the cases.

    The count is taken from the code, never from a document.
    """
    global _SUITE_COUNT
    if _SUITE_COUNT is None:
        loader = unittest.TestLoader()
        suite = loader.discover(start_dir=str(TESTS))
        _SUITE_COUNT = suite.countTestCases()
    return _SUITE_COUNT


def _claim(text, pattern, what):
    """Return the first captured group of ``pattern`` or fail loudly.

    A missing pattern is a failure, never a silently skipped check.
    """
    match = re.search(pattern, text)
    if not match:
        raise AssertionError("could not find %s (looked for %r)" % (what, pattern))
    return match.group(1)


def _home_test_count(text):
    return int(_claim(text, r"\*\*(\d+)\s+tests\*\*", "the test count in docs/HOME.md"))


def _handoff_test_count(text):
    return int(_claim(text, r"Tests\s*:\s*(\d+)\s+tests", "the test count in docs/HANDOFF.md"))


def _contributors_test_count(text):
    return int(_claim(text, r"currently\s+(\d+)\s+tests", "the test count in docs/CONTRIBUTORS.md"))


def _home_build(text):
    return _claim(text, r"Last verified with build \*\*(\d+\.\d+)\*\*", "the build in docs/HOME.md")


def _handoff_build(text):
    return _claim(text, r"Build\s*:\s*(\d+\.\d+)", "the build in docs/HANDOFF.md")


def _changelog_builds(text):
    """Every '- X.YY (date):' bullet in the changelog, as version tuples."""
    builds = []
    for match in re.finditer(r"^-\s+(\d+)\.(\d+)\s+\(", text, re.M):
        builds.append((int(match.group(1)), int(match.group(2))))
    return builds


def _newest_build(text):
    """The newest build version in the changelog, as 'X.YY'."""
    builds = _changelog_builds(text)
    if not builds:
        raise AssertionError("docs/CHANGELOG.md has no '- X.YY (date):' bullet")
    major, minor = max(builds)
    return "%d.%d" % (major, minor)


def _decision_rows(text):
    """The decision ids that have a row in the decision register."""
    return set(re.findall(r"^\|\s*(B-\d{3}[a-z]?)\s*\|", text, re.M))


def _readme_method_ids(text):
    """The method ids listed on the README's 'Methods: ...' line.

    The list is a comma-separated run of bare ids, each optionally followed by a
    parenthetical description ('pearson (falls back to spearman)').  The list
    ends at the first period that is not inside a parenthetical; after that the
    line is prose.  An entry that is not exactly 'id' or 'id (description)'
    also ends the list.
    """
    match = re.search(r"Methods:([^\n]*)", text)
    if not match:
        raise AssertionError("README.md has no 'Methods: ...' line")
    segment = match.group(1)

    items = []
    current = []
    depth = 0
    for char in segment:
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        if char == "." and depth == 0:
            break  # the method list has ended; the rest of the line is prose
        if char == "," and depth == 0:
            items.append("".join(current))
            current = []
            continue
        current.append(char)
    items.append("".join(current))

    ids = []
    for item in items:
        item = item.strip()
        if not item:
            continue
        entry = _README_ITEM_RE.fullmatch(item)
        if not entry:
            break  # not a method entry: the list has ended
        ids.append(entry.group(1))
    if not ids:
        raise AssertionError("no method ids could be read from the README 'Methods: ...' line")
    return set(ids)


def _home_spine(text):
    """Section 4 of docs/HOME.md, the documentation-spine table."""
    match = re.search(r"##\s*4\.\s*The documentation spine(.*?)(?=\n##\s|\Z)", text, re.S)
    if not match:
        raise AssertionError("docs/HOME.md has no '## 4. The documentation spine' section")
    return match.group(1)


def _spine_globs(spine):
    """Wildcard tokens used by the spine to cover a family of documents."""
    return re.findall(r"`([^`]*[\*\?][^`]*)`", spine)


def _covered_by_spine(name, spine, globs):
    """Is a document covered by the spine table?

    Either it is linked directly, or a wildcard row in the table covers it
    (the table covers the historical stage reports as `STAGE*_REPORT.md`).
    """
    if re.search(r"\]\(" + re.escape(name) + r"\)", spine):
        return True
    return any(fnmatch.fnmatch(name, glob) for glob in globs)


def _replace_group(text, pattern, new):
    """Rewrite the first captured group of ``pattern`` with ``new``."""
    return re.sub(pattern, lambda m: m.group(0).replace(m.group(1), new), text, count=1)


class DocsStateSyncTest(unittest.TestCase):
    """The documents must agree with the code they describe."""

    maxDiff = None

    # -- 1. the test count in the documents must be the real count ------------
    def test_documented_test_count_matches_the_real_suite(self):
        count = _suite_count()
        claims = (
            ("docs/HOME.md", _home_test_count(_read(DOCS / "HOME.md"))),
            ("docs/HANDOFF.md", _handoff_test_count(_read(DOCS / "HANDOFF.md"))),
            ("docs/CONTRIBUTORS.md", _contributors_test_count(_read(DOCS / "CONTRIBUTORS.md"))),
        )
        for name, claimed in claims:
            self.assertEqual(
                claimed,
                count,
                "%s says %d tests, but the suite holds %d tests" % (name, claimed, count),
            )

    # -- 2. the build in the documents must be the newest changelog build -----
    def test_documented_build_matches_the_newest_changelog_entry(self):
        build = _newest_build(_read(DOCS / "CHANGELOG.md"))
        home = _home_build(_read(DOCS / "HOME.md"))
        handoff = _handoff_build(_read(DOCS / "HANDOFF.md"))
        self.assertEqual(
            home, build, "docs/HOME.md says build %s, but the newest changelog entry is %s" % (home, build)
        )
        self.assertEqual(
            handoff,
            build,
            "docs/HANDOFF.md says build %s, but the newest changelog entry is %s" % (handoff, build),
        )

    def test_the_served_build_is_the_newest_changelog_build(self):
        """The top bar cannot state a build the tree is not (D-PM-07).

        The pill read "v1.45" for many builds because the number was a literal in
        `web/index.html` that nothing refreshed.  It now comes from `/api/health`,
        which reports `bp.build.VERSION`, and this pins that constant to the newest
        changelog entry - the same number HOME.md and HANDOFF.md must state - so the
        three cannot drift apart again.
        """
        from bp import build as build_info
        from bp.product import ops
        newest = _newest_build(_read(DOCS / "CHANGELOG.md"))
        self.assertEqual(build_info.VERSION, newest,
                         "bp/build.py says %s, the newest changelog entry is %s"
                         % (build_info.VERSION, newest))
        report = ops.health({"sandbox": "on"})
        self.assertEqual(report.get("build"), newest, "the health report states another build")
        page = _read(REPO / "web" / "index.html")
        # the number is painted from the server, not written into the markup
        self.assertIn('id="buildpill"', page)
        self.assertIn("paintBuild(", page)
        self.assertIn("/api/health", page)
        self.assertNotIn(">v1.45<", page)

    # -- 3. every decision id mentioned must exist in the register ------------
    def test_every_mentioned_decision_id_has_a_row_in_the_decision_register(self):
        mentioned = {}
        for path in sorted(DOCS.glob("*.md")) + [README]:
            ids = set(_DECISION_RE.findall(_read(path)))
            if ids:
                mentioned[path.name] = ids
        rows = _decision_rows(_read(DOCS / "DECISIONS.md"))
        missing = {name: sorted(ids - rows) for name, ids in mentioned.items() if ids - rows}
        self.assertEqual(
            missing,
            {},
            "these decision ids are mentioned but have no '| B-xxx |' row in docs/DECISIONS.md: %s"
            % missing,
        )

    # -- 4. the README method list must match the method library --------------
    def test_readme_method_list_matches_the_method_library(self):
        documented = _readme_method_ids(_read(README))
        implemented = set(LIBRARY)
        self.assertEqual(
            documented - implemented,
            set(),
            "README.md lists method ids that bp.methods.LIBRARY does not have: %s"
            % sorted(documented - implemented),
        )
        self.assertEqual(
            implemented - documented,
            set(),
            "bp.methods.LIBRARY has method ids that README.md does not list: %s"
            % sorted(implemented - documented),
        )

    # -- 5. every document must be reachable from the documentation spine -----
    def test_every_doc_file_is_covered_by_the_home_documentation_spine(self):
        home = _read(DOCS / "HOME.md")
        spine = _home_spine(home)
        globs = _spine_globs(spine)
        uncovered = [
            path.name
            for path in sorted(DOCS.glob("*.md"))
            if not _covered_by_spine(path.name, spine, globs)
        ]
        self.assertEqual(
            uncovered,
            [],
            "these documents in docs/ have no row in the documentation spine "
            "(docs/HOME.md section 4): %s" % uncovered,
        )

    # -- 6. the parked queue must be linked from the two entry points ---------
    def test_parked_queue_is_linked_from_home_and_contributors(self):
        for path in (DOCS / "HOME.md", DOCS / "CONTRIBUTORS.md"):
            self.assertRegex(
                _read(path),
                r"\]\(PARKED_QUEUE\.md\)",
                "%s does not link docs/PARKED_QUEUE.md" % path.name,
            )

    # -- 7. no tautology: the checks read the documents and the code ---------
    def test_the_checks_read_the_documents_and_the_code_not_a_constant(self):
        """Each claim is read from the document, each expectation from the code.

        If a check compared a document with itself it could never fail, so this
        test proves both halves: rewriting a document's own digits changes what
        that document claims, while the expected values (the suite count and
        the newest changelog build) do not move.
        """
        count = _suite_count()
        build = _newest_build(_read(DOCS / "CHANGELOG.md"))

        cases = (
            ("docs/HOME.md", _read(DOCS / "HOME.md"), r"\*\*(\d+)\s+tests\*\*", _home_test_count),
            ("docs/HANDOFF.md", _read(DOCS / "HANDOFF.md"), r"Tests\s*:\s*(\d+)\s+tests", _handoff_test_count),
            (
                "docs/CONTRIBUTORS.md",
                _read(DOCS / "CONTRIBUTORS.md"),
                r"currently\s+(\d+)\s+tests",
                _contributors_test_count,
            ),
            ("docs/HOME.md", _read(DOCS / "HOME.md"), r"Last verified with build \*\*(\d+\.\d+)\*\*", _home_build),
            ("docs/HANDOFF.md", _read(DOCS / "HANDOFF.md"), r"Build\s*:\s*(\d+\.\d+)", _handoff_build),
        )
        for name, text, pattern, parse in cases:
            original = parse(text)
            mutated = parse(_replace_group(text, pattern, "999" if "tests" in pattern else "9.99"))
            self.assertNotEqual(
                mutated,
                original,
                "%s: rewriting %r did not change what it claims, so the check cannot fail" % (name, pattern),
            )

        # the expected side comes from the code and the changelog, not the documents
        self.assertEqual(_suite_count(), count, "the suite count moved while reading the documents")
        self.assertEqual(
            _newest_build(_read(DOCS / "CHANGELOG.md")),
            build,
            "the newest changelog build moved while reading the documents",
        )
        self.assertGreater(count, 0, "the real suite count is zero; the discovery did not work")


if __name__ == "__main__":
    unittest.main()
