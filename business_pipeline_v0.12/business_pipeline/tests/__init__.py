"""The test package.

Two product layers make live HTTPS calls: the background-reading layer
and the model lanes (analysis drafting, gap questions).  A unit test
must not depend on the network or wait on it, so both are disabled before any
test module imports the code that reads them.  `conftest.py` repeats the settings
for pytest, which may import a test file without importing this package first.
"""

import os

# Forced, not defaulted: a parent shell that serves the product may export these
# for the app, and a test run must still be offline.
os.environ["BP_ORIENTATION"] = "0"
os.environ["BP_LEARNING_LOG"] = "0"

#: The model lanes are live HTTPS calls: the analysis lane drafts a part from the
#: instruction and the proposal lane writes a question for a gap.  A machine that
#: serves the product has the keys set, so a suite that inherits them reaches the
#: network from inside a test - it waits on a provider, and two runs of the same
#: template no longer produce the same bytes.  They are cleared here, once, before
#: any test module imports the code that reads them; a test that wants a model
#: attaches its own stub.
MODEL_VARS = ("BP_LLM_PROVIDER", "BP_LLM_MODEL", "BP_LLM_MODEL_TIER2", "BP_LLM_MODEL_TIER3",
              "BP_LLM_REVIEWER_MODEL", "BP_LLM_BASE_URL", "BP_LLM_URL", "BP_LLM_KEY",
              "BP_OPENGO_API_KEY", "OPENCODE_API_KEY",
              "BP_PROSE_URL", "BP_PROSE_MODEL", "BP_OLLAMA_URL", "BP_OLLAMA_HOST",
              "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "DEEPSEEK_API_KEY")
# Set, not popped: `bp.server` maps `Backend/.env` onto these names for any key that
# is *absent*, so an empty value is what keeps them unset when that module is imported.
# With no key the lanes answer "not configured"; a test that wants one patches
# `prose.available` and `prose._call` (see `tests/test_matrix_assist.py`).
for _name in MODEL_VARS:
    os.environ[_name] = ""
