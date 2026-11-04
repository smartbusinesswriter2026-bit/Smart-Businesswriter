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
            credentials = os.path.join(folder, ".env")
            with open(credentials, "w", encoding="utf-8") as stream:
                stream.write("BRAVE_API_KEY=launcher-secret\n")
            environment = {**os.environ,
                           "BP_CASES_DIR": os.path.join(folder, "cases"),
                           "BP_STATE_DIR": os.path.join(folder, "state"),
                           "BP_REQUEST_LOG": "",
                           "BP_SOURCE_ENV": credentials}
            environment.pop("BP_BRAVE_API_KEY", None)
            environment.pop("BP_DEEPSEEK_API_KEY", None)
            environment.pop("BP_OPENGO_API_KEY", None)
            environment.pop("BP_OPENGO_SEARCH_URL", None)
            result = subprocess.run([sys.executable, SCRIPT, "--check"], capture_output=True, text=True,
                                    env=environment, cwd=ROOT, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            config = json.loads(result.stdout)
            self.assertEqual(config["format"], "bp-launcher/1")
            self.assertEqual((config["host"], config["port"], config["sandbox"]), ("127.0.0.1", 8000, True))
            self.assertIsNone(config["request_log"])
            self.assertEqual(config["case_store"], os.path.join(folder, "cases"))
            self.assertEqual(config["state_dir"], os.path.join(folder, "state"))
            self.assertEqual(config["web_search"]["order"], ["opengo", "deepseek", "brave", "firecrawl"])
            self.assertTrue(config["web_search"]["brave"])
            self.assertFalse(config["web_search"]["deepseek"])
            self.assertIn("BP_BRAVE_API_KEY", config["web_search"]["loaded"])
            self.assertNotIn("launcher-secret", result.stdout)
            self.assertIn("semantic_scholar", config["academic_search"])
            self.assertNotIn("core", config["academic_search"])

    def test_bad_arguments_are_refused(self):
        for arguments in (["--port", "abc"], ["--unknown"]):
            result = subprocess.run([sys.executable, SCRIPT] + arguments, capture_output=True, text=True,
                                    cwd=ROOT, timeout=120)
            self.assertNotEqual(result.returncode, 0, arguments)


if __name__ == "__main__":
    unittest.main()
