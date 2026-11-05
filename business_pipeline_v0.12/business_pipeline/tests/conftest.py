"""Suite-wide hygiene.

`bp.product.sources` keeps one process-wide answer cache (`_CACHE`, TTL from
`BP_SOURCE_CACHE_TTL`).  It is right for the app and wrong for the tests: a test
that asserts which provider answered — the Brave-to-Firecrawl fallback — gets the
first test's cached answer instead, so it passes alone and fails in the suite
(D-PLAN-05).  Clearing it between tests keeps every provider test honest without
touching the cache the product relies on.

The learning library is redirected *before* anything imports it.  A test exercise is not a
student's problem, and writing fixtures into the real library drowned 235 real observations under
150 copies of one trial balance and handed that fixture to the model as a "similar solved case".
The tests now keep their own store; the real one is never touched by a test run.
"""

import os
import tempfile

os.environ.setdefault("BP_STATEMENT_LIBRARY_DIR",
                      os.path.join(tempfile.gettempdir(), "bp_test_statement_library"))
os.environ.setdefault("BP_STATEMENT_LIBRARY_ORIGIN", "test")

import pytest

from bp.product import sources


@pytest.fixture(autouse=True)
def _clear_source_cache():
    sources._CACHE.clear()
    yield
    sources._CACHE.clear()
