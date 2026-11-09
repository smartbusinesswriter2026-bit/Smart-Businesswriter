"""The served build number, in one place.

The workbench shows it in the top bar.  It lives here as a constant rather than as a
literal in the page for one reason: `tests/test_docs_sync.py` proves this number
equals the newest build in `docs/CHANGELOG.md`, which is the same number `HOME.md`
and `HANDOFF.md` must state.  So the pill cannot claim a build the tree is not --
which it did for many builds, reading "v1.45" while the tree was at 1.76 (D-PM-07).

Bump this when the changelog gets a new `- X.YY (date):` bullet.  Nothing else needs
to change: the page reads it from `/api/health` at boot.
"""

VERSION = "1.148"
