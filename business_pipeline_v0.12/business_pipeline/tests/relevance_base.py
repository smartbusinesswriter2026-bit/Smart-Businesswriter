"""Shared base class for the Relevance Research Agent tests.

The RRA writes to `state/relevance/`.  These tests point that at a temporary
directory so a test run never touches the real state, and they restore the
environment afterwards so one test cannot leak a switch into the next.
"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, "src")

REPO_ROOT = Path(__file__).resolve().parents[1]


class RelevanceTestCase(unittest.TestCase):
    """A test case with an isolated state directory and a clean environment."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="rra-test-")
        self._saved_env = dict(os.environ)
        os.environ["BP_STATE_DIR"] = os.path.join(self._tmp, "state")
        # The suite shares one ops log (conftest.py points BP_OPS_LOG at a
        # common directory), so a finding written by one test is still there
        # for the next.  The RRA's tests read the log, so they keep their own.
        os.environ["BP_OPS_LOG"] = os.path.join(self._tmp, "ops_log")
        # The registries live in the repository; the tests read them for real.
        self._state_dir = Path(self._tmp) / "state"
        # The RRA's provider and models come from Backend/.env, and the server
        # loads them into the process on import.  A test must start from a
        # known state, or one test's environment decides another's answer.
        for name in ("BP_RELEVANCE_PROVIDER", "BP_RELEVANCE_MODEL",
                     "BP_RELEVANCE_DISCOVERY_MODEL", "BP_RELEVANCE_EXTRACT_MODEL",
                     "BP_RELEVANCE_DESIGN_MODEL", "BP_RELEVANCE_ENABLED"):
            os.environ.pop(name, None)

    def tearDown(self):
        for name in list(os.environ.keys()):
            if name not in self._saved_env:
                os.environ.pop(name, None)
        for name, value in self._saved_env.items():
            os.environ[name] = value
        shutil.rmtree(self._tmp, ignore_errors=True)

    # -- helpers ----------------------------------------------------------

    def set_env(self, **values):
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = str(value)

    def unset_env(self, *names):
        for name in names:
            os.environ.pop(name, None)
