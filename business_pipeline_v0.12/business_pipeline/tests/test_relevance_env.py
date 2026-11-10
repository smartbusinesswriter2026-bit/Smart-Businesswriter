"""Tests for the RRA's own environment names.

The RRA reads its provider and its models from `Backend/.env` under its own
`BP_RELEVANCE_*` names.  The server's loader maps the `.env` names onto the
`BP_*` names the product reads; the RRA's names must be in that map, or the
per-stage models never reach the process.
"""
import io
import os
import tempfile
import unittest

from tests.relevance_base import RelevanceTestCase  # noqa: E402


class ServerEnvMappingTest(RelevanceTestCase):
    def _write_env(self, text):
        handle = tempfile.NamedTemporaryFile("w", suffix=".env", delete=False,
                                             encoding="utf-8")
        handle.write(text)
        handle.close()
        return handle.name

    def test_the_rra_names_are_in_the_server_loader(self):
        import inspect
        import bp.server as server
        source = inspect.getsource(server._load_opencode_env)
        for expected in ("BP_RELEVANCE_MODEL", "BP_RELEVANCE_EXTRACT_MODEL",
                         "BP_RELEVANCE_DESIGN_MODEL",
                         "BP_RELEVANCE_DISCOVERY_MODEL",
                         "BP_RELEVANCE_PROVIDER"):
            self.assertIn(expected, source,
                          "%s must be mapped by the server's env loader" % expected)

    def test_an_exported_name_wins_over_the_file(self):
        import bp.server as server
        path = self._write_env("BP_RELEVANCE_MODEL=from-the-file\n")
        saved = os.environ.get("BP_RELEVANCE_MODEL")
        os.environ["BP_RELEVANCE_MODEL"] = "from-the-environment"
        try:
            server._load_opencode_env()
            self.assertEqual(os.environ.get("BP_RELEVANCE_MODEL"),
                             "from-the-environment")
        finally:
            if saved is None:
                os.environ.pop("BP_RELEVANCE_MODEL", None)
            else:
                os.environ["BP_RELEVANCE_MODEL"] = saved
        os.unlink(path)


class RelevanceModelNamesTest(RelevanceTestCase):
    def test_the_stage_names_cover_the_three_reading_stages(self):
        from bp.product.relevance import model as rmodel
        self.assertIn("relevance-extract", rmodel.STAGE_MODELS)
        self.assertIn("relevance-design", rmodel.STAGE_MODELS)
        self.assertIn("relevance-discovery-query", rmodel.STAGE_MODELS)

    def test_a_stage_override_beats_the_default(self):
        from bp.product.relevance import model as rmodel
        self.set_env(BP_RELEVANCE_MODEL="model-a",
                     BP_RELEVANCE_EXTRACT_MODEL="model-b")
        self.assertEqual(rmodel.model_names("relevance-extract")[1], "model-b")
        # The design stage has no override, so it takes the default.
        self.assertEqual(rmodel.model_names("relevance-design")[1], "model-a")

    def test_a_stage_override_in_the_environment_wins_over_the_default(self):
        from bp.product.relevance import model as rmodel
        self.set_env(BP_RELEVANCE_MODEL="model-a",
                     BP_RELEVANCE_DESIGN_MODEL="model-c")
        self.assertEqual(rmodel.model_names("relevance-design")[1], "model-c")


if __name__ == "__main__":
    unittest.main()
