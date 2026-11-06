"""The test package.

The product's background-reading layer (Wikipedia) is a live web call.  A unit
test must not depend on the network or wait on it, so it is disabled before any
test module imports the retrieval engine.  `conftest.py` repeats the setting for
pytest, which may import a test file without importing this package first.
"""

import os

os.environ.setdefault("BP_ORIENTATION", "0")
os.environ.setdefault("BP_LEARNING_LOG", "0")
