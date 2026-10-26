import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "serve.py")


class LauncherTest(unittest.TestCase):
    """The single local run path resolves its configuration without serving (Phase 2b)."""

    def test_check_prints_the_resolved_configuration(self):
        with tempfile.TemporaryDirectory() as folder:
            environment = {**os.environ,
                           "BP_CASES_DIR": os.path.join(folder, "cases"),
                           "BP_STATE_DIR": os.path.join(folder, "state"),
                           "BP_REQUEST_LOG": ""}
            result = subprocess.run([sys.executable, SCRIPT, "--check"], capture_output=True, text=True,
                                    env=environment, cwd=ROOT, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual(config["format"], "bp-launcher/1")
            self.assertEqual((config["host"], config["port"], config["sandbox"]), ("127.0.0.1", 8000, True))
            self.assertIsNone(config["request_log"])
            self.assertEqual(config["case_store"], os.path.join(folder, "cases"))
            self.assertEqual(config["state_dir"], os.path.join(folder, "state"))

    def test_bad_arguments_are_refused(self):
        for arguments in (["--port", "abc"], ["--unknown"]):
            result = subprocess.run([sys.executable, SCRIPT] + arguments, capture_output=True, text=True,
                                    cwd=ROOT, timeout=120)
            self.assertNotEqual(result.returncode, 0, arguments)


if __name__ == "__main__":
    unittest.main()
