"""The served page's inline script must parse.

The page is one HTML file with one inline script, and a single misplaced brace
takes the whole workbench down while every Python test stays green.  This test
extracts the script and asks a JavaScript parser to check it; without a parser on
the machine it skips rather than pretending to check.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "web" / "index.html"


def inline_script():
    page = PAGE.read_text(encoding="utf-8")
    start = page.rfind("<script>")
    end = page.find("</script>", start)
    if start == -1 or end == -1:
        raise AssertionError("the page carries no inline script")
    return page[start + len("<script>"):end]


@unittest.skipUnless(shutil.which("node"), "node is not installed, so the script cannot be parsed here")
class InlineScriptTest(unittest.TestCase):
    def test_the_inline_script_parses(self):
        script = inline_script()
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "page.js")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(script)
            result = subprocess.run([shutil.which("node"), "--check", path],
                                    capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr[-1200:])

    def test_the_stylesheet_is_not_inside_the_script(self):
        # A CSS rule pasted into the script is a syntax error; this names the
        # mistake rather than letting the parser message carry it alone.
        script = inline_script()
        self.assertNotIn(".doclink{", script)
        self.assertNotIn(".actionbox{", script)


if __name__ == "__main__":
    unittest.main()
