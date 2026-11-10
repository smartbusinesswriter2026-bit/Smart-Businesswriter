"""The health panel and its route (design lane).

The panel is the owner's view of the pipeline's health.  Two things are
checked here that a Python test of the module cannot check: the page's
inline script still parses (one misplaced brace takes the console down while
every Python test stays green), and the route reads the health module without
starting anything.
"""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "admin-sbw.html"
SERVER = ROOT / "src" / "bp" / "server.py"


def inline_script():
    page = PAGE.read_text(encoding="utf-8")
    start = page.rfind("<script>")
    end = page.find("</script>", start)
    if start == -1 or end == -1:
        raise AssertionError("the admin page carries no inline script")
    return page[start + len("<script>"):end]


class HealthPanelTest(unittest.TestCase):
    def test_the_page_carries_the_pipeline_health_panel(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("renderPipelineHealth", page)
        self.assertIn("/api/ops/health", page)

    def test_the_panel_shows_the_reason_and_the_age_of_each_signal(self):
        page = PAGE.read_text(encoding="utf-8")
        self.assertIn("not measured", page)
        self.assertIn("c.age", page)

    def test_the_route_reads_the_health_module(self):
        source = SERVER.read_text(encoding="utf-8")
        self.assertIn("/api/ops/health", source)
        self.assertIn("_health.health(", source)

    def test_the_route_starts_nothing(self):
        """A health check that starts a loop is a loop with a UI."""
        source = SERVER.read_text(encoding="utf-8")
        start = source.find('if _ops_url.path == "/api/ops/health":')
        self.assertNotEqual(start, -1, "the health route is not wired")
        block = source[start:start + 1200]
        for forbidden in ("autoresearch.start", "growth_loop.start", "job.start",
                          "set_switch", "apply_all"):
            self.assertNotIn(forbidden, block,
                             "the health route must not start anything: %s" % forbidden)

    def test_the_route_is_additive(self):
        """The server's own routes are untouched."""
        source = SERVER.read_text(encoding="utf-8")
        self.assertIn('if self.path == "/api/health":', source)


@unittest.skipUnless(shutil.which("node"), "node is not installed, so the script cannot be parsed here")
class AdminScriptTest(unittest.TestCase):
    def test_the_admin_inline_script_parses(self):
        script = inline_script()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "admin.js")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(script)
            result = subprocess.run([shutil.which("node"), "--check", path],
                                   capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr[-1200:])


if __name__ == "__main__":
    unittest.main()
