"""The source credential loader: its own file, allowlisted names, no values in a report."""

import os
import tempfile
import unittest
from unittest import mock

import sys
sys.path.insert(0, "src")

from bp.product import source_env  # noqa: E402


class LoadTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.folder.name, ".env")
        with open(self.path, "w", encoding="utf-8") as stream:
            stream.write("# comment\n"
                         "BRAVE_API_KEY=brave-secret-value\n"
                         "FIRECRAWL_API_KEY='firecrawl-secret-value'\n"
                         "DEEPSEEK_API_KEY=deepseek-secret-value\n"
                         "OPENCODE_API_KEY=opengo-secret-value\n"
                         "OPENGO_SEARCH_URL=https://opengo.example/search\n"
                         "SEMANTIC_SCHOLAR_API_KEY=s2-secret-value\n"
                         "OPENALEX_EMAIL=research@example.org\n"
                         "CROSSREF_MAILTO=research@example.org\n"
                         "FIRECRAWL_KEYLESS=0\n"
                         "GOOGLE_API_KEY=must-not-load\n"
                         "UNRELATED=must-not-load\n")

    def tearDown(self):
        self.folder.cleanup()

    def test_only_the_allowlisted_names_are_loaded_and_mapped(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            report = source_env.load_web_credentials(self.path)
            self.assertEqual(os.environ["BP_BRAVE_API_KEY"], "brave-secret-value")
            self.assertEqual(os.environ["BP_FIRECRAWL_API_KEY"], "firecrawl-secret-value")
            self.assertEqual(os.environ["BP_DEEPSEEK_API_KEY"], "deepseek-secret-value")
            self.assertEqual(os.environ["BP_OPENGO_API_KEY"], "opengo-secret-value")
            self.assertEqual(os.environ["BP_OPENGO_SEARCH_URL"], "https://opengo.example/search")
            self.assertEqual(os.environ["BP_SEMANTIC_SCHOLAR_KEY"], "s2-secret-value")
            self.assertEqual(os.environ["BP_OPENALEX_EMAIL"], "research@example.org")
            self.assertEqual(os.environ["BP_CROSSREF_MAILTO"], "research@example.org")
            self.assertEqual(os.environ["BP_FIRECRAWL_KEYLESS"], "0")
            self.assertNotIn("GOOGLE_API_KEY", os.environ)
            self.assertNotIn("UNRELATED", os.environ)
        self.assertEqual(sorted(report["loaded"]),
                         ["BP_BRAVE_API_KEY", "BP_CROSSREF_MAILTO", "BP_DEEPSEEK_API_KEY",
                          "BP_FIRECRAWL_API_KEY", "BP_FIRECRAWL_KEYLESS", "BP_OPENALEX_EMAIL",
                          "BP_OPENGO_API_KEY", "BP_OPENGO_SEARCH_URL", "BP_SEMANTIC_SCHOLAR_KEY"])
        self.assertTrue(report["brave"])
        self.assertTrue(report["firecrawl"])
        self.assertTrue(report["semantic_scholar"])
        self.assertTrue(report["deepseek"])
        self.assertTrue(report["opengo_key"])
        self.assertNotIn("core", report)

    def test_the_report_never_contains_a_secret_value(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            report = source_env.load_web_credentials(self.path)
        text = repr(report)
        for secret in ("brave-secret-value", "firecrawl-secret-value", "s2-secret-value",
                    "deepseek-secret-value", "opengo-secret-value"):
            self.assertNotIn(secret, text)
        self.assertEqual(report["path"], self.path)

    def test_an_existing_environment_value_is_not_overwritten(self):
        with mock.patch.dict(os.environ, {"BP_BRAVE_API_KEY": "already-set"}, clear=True):
            report = source_env.load_web_credentials(self.path)
            self.assertEqual(os.environ["BP_BRAVE_API_KEY"], "already-set")
            self.assertEqual(os.environ["BP_FIRECRAWL_API_KEY"], "firecrawl-secret-value")
            self.assertEqual(os.environ["BP_DEEPSEEK_API_KEY"], "deepseek-secret-value")
            self.assertEqual(os.environ["BP_OPENGO_API_KEY"], "opengo-secret-value")
            self.assertEqual(os.environ["BP_OPENGO_SEARCH_URL"], "https://opengo.example/search")
        self.assertNotIn("BP_BRAVE_API_KEY", report["loaded"])

    def test_an_empty_value_in_the_file_is_not_loaded(self):
        path = os.path.join(self.folder.name, "empty.env")
        with open(path, "w", encoding="utf-8") as stream:
            stream.write("BRAVE_API_KEY=\nSEMANTIC_SCHOLAR_API_KEY=\n")
        with mock.patch.dict(os.environ, {}, clear=True):
            report = source_env.load_web_credentials(path)
            self.assertNotIn("BP_BRAVE_API_KEY", os.environ)
            self.assertNotIn("BP_SEMANTIC_SCHOLAR_KEY", os.environ)
        self.assertEqual(report["loaded"], [])

    def test_a_missing_file_is_reported_without_raising(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            report = source_env.load_web_credentials(os.path.join(self.folder.name, "absent.env"))
        self.assertIsNone(report["path"])
        self.assertEqual(report["loaded"], [])
        self.assertEqual((report["brave"], report["firecrawl"], report["semantic_scholar"]),
                         (False, False, False))
        self.assertNotIn("core", report)

    def test_the_default_lookup_uses_bp_source_env(self):
        with mock.patch.dict(os.environ, {"BP_SOURCE_ENV": self.path}, clear=True):
            report = source_env.load_web_credentials()
        self.assertEqual(report["path"], self.path)
        self.assertTrue(report["brave"])

    def test_the_project_has_its_own_env_as_the_first_default(self):
        self.assertEqual(source_env.DEFAULT_PATHS[0], str(source_env.PROJECT_ENV))
        self.assertEqual(source_env.PROJECT_ENV.name, ".env")
        self.assertEqual(source_env.PROJECT_ENV.parent.name, "Backend")


class StatusTest(unittest.TestCase):
    def test_web_status_reports_providers_without_a_key(self):
        from bp.product import sources
        with mock.patch.dict(os.environ, {"BP_BRAVE_API_KEY": "brave-secret-value", "BP_FIRECRAWL_KEYLESS": "0"}, clear=True):
            status = sources.web_status()
        self.assertEqual(status["order"], ["opengo", "deepseek", "brave", "firecrawl"])
        self.assertTrue(status["brave"])
        self.assertFalse(status["deepseek"])
        self.assertFalse(status["opengo"])
        self.assertFalse(status["firecrawl"])
        self.assertNotIn("brave-secret-value", repr(status))


if __name__ == "__main__":
    unittest.main()
