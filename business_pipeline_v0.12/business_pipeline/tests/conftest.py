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

# The ops log is the owner's admin panel.  A test that exercises a refusal on purpose
# (the instrument ticker test, for one) used to append to the live errors.jsonl, so the
# panel filled with failures no one could repair.  Tests keep their own log; a test that
# asserts on the log sets BP_OPS_LOG itself.
os.environ.setdefault("BP_OPS_LOG", os.path.join(tempfile.gettempdir(), "bp_test_ops_log"))

# A verified fix appends a golden case to the regression file.  A unit test that mocks
# a fix into passing must not write that case into the owner's real regression suite.
os.environ.setdefault("BP_REGRESSION_CASES",
                      os.path.join(tempfile.gettempdir(), "bp_test_regression_cases.jsonl"))

# Background reading is no longer part of the pipeline; the flag stays off so
# an inherited environment cannot turn a live call on.
os.environ["BP_ORIENTATION"] = "0"
# The learning log writes to the live corpus service.  A test exercise is not a
# student's search, so the fixtures never reach the real corpus history.  Forced,
# not defaulted, so an inherited app setting cannot turn the live call back on.
os.environ["BP_LEARNING_LOG"] = "0"

# The model lanes are live HTTPS calls (see `tests/__init__.py`).  pytest may import
# a test file without importing the package first, so the keys are cleared here too.
for _name in ("BP_LLM_PROVIDER", "BP_LLM_MODEL", "BP_LLM_MODEL_TIER2", "BP_LLM_MODEL_TIER3",
              "BP_LLM_REVIEWER_MODEL", "BP_LLM_BASE_URL", "BP_LLM_URL", "BP_LLM_KEY",
              "BP_OPENGO_API_KEY", "OPENCODE_API_KEY",
              "BP_PROSE_URL", "BP_PROSE_MODEL", "BP_OLLAMA_URL", "BP_OLLAMA_HOST",
              "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY"):
    os.environ[_name] = ""

import pytest

from bp.product import sources


@pytest.fixture(autouse=True)
def _clear_source_cache():
    sources._CACHE.clear()
    yield
    sources._CACHE.clear()
