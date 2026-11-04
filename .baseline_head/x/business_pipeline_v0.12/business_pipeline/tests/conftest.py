"""Suite-wide hygiene.

`bp.product.sources` keeps one process-wide answer cache (`_CACHE`, TTL from
`BP_SOURCE_CACHE_TTL`).  It is right for the app and wrong for the tests: a test
that asserts which provider answered — the Brave-to-Firecrawl fallback — gets the
first test's cached answer instead, so it passes alone and fails in the suite
(D-PLAN-05).  Clearing it between tests keeps every provider test honest without
touching the cache the product relies on.
"""

import pytest

from bp.product import sources


@pytest.fixture(autouse=True)
def _clear_source_cache():
    sources._CACHE.clear()
    yield
    sources._CACHE.clear()
