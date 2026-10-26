"""The self-contained HTML export (product layer).

The export copies what was recorded: the delivered report text and the stored
artifact values.  Nothing is re-rounded, re-formatted or recomputed.
"""

import html
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import export  # noqa: E402


def _sections(document):
    """The content sections of the exported file."""
    return {name: body for name, body in re.findall(
        r"<section id=\"([a-z]+)\">(.*?)</section>", document, re.S)}


def _text_only(markup):
    """The text of a piece of markup, without the tags."""
    return html.unescape(re.sub(r"<[^>]+>", "", markup))


def _numbers(text):
    return set(re.findall(r"\d+(?:\.\d+)*", text))


class ExportHtmlTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-export-test-")
        self.target = os.path.join(self.root, "case.html")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_export_is_written_and_readable(self):
        path = export.export_html(product_fixtures.make_bundle(), self.target)
        self.assertEqual(path, self.target)
        self.assertTrue(os.path.exists(self.target))
        with open(self.target, encoding="utf-8") as stream:
            document = stream.read()
        self.assertTrue(document.startswith("<!doctype html>"))

    def test_the_report_text_is_verbatim(self):
        export.export_html(product_fixtures.make_bundle(), self.target)
        with open(self.target, encoding="utf-8") as stream:
            document = stream.read()
        body = re.search(r"<pre class=\"report\">(.*?)</pre>", _sections(document)["report"], re.S).group(1)
        self.assertIn(html.escape(product_fixtures.REPORT, quote=False), body)
        self.assertEqual(html.unescape(body).strip(), product_fixtures.REPORT.strip())

    def test_the_stored_artifact_values_are_verbatim(self):
        export.export_html(product_fixtures.make_bundle(), self.target)
        with open(self.target, encoding="utf-8") as stream:
            document = stream.read()
        table = _sections(document)["artifacts"]
        self.assertIn("50.00", table)
        self.assertNotIn("50.0<", table)
        self.assertIn("npv", table)
        self.assertIn("npv = sum", table)

    def test_the_export_is_self_contained(self):
        export.export_html(product_fixtures.make_bundle(), self.target)
        with open(self.target, encoding="utf-8") as stream:
            document = stream.read()
        self.assertNotIn("http://", document)
        self.assertNotIn("https://", document)
        self.assertNotIn("<script", document)
        self.assertNotIn("src=", document)

    def test_the_export_contains_no_number_that_was_not_recorded(self):
        bundle = product_fixtures.make_bundle()
        export.export_html(bundle, self.target)
        with open(self.target, encoding="utf-8") as stream:
            document = stream.read()
        import json
        recorded = _numbers(json.dumps(bundle, ensure_ascii=False))
        content = " ".join(_text_only(body) for body in _sections(document).values())
        self.assertEqual(_numbers(content) - recorded, set())

    def test_a_bundle_without_a_delivery_is_handled(self):
        bundle = product_fixtures.make_bundle()
        bundle["delivery"] = {"report": "", "appendix": {}}
        export.export_html(bundle, self.target)
        with open(self.target, encoding="utf-8") as stream:
            document = stream.read()
        self.assertIn("not recorded", document)

    def test_the_export_refuses_a_non_object_bundle(self):
        with self.assertRaises(ValueError):
            export.export_html("not a bundle", self.target)

    def test_the_export_writes_into_a_missing_directory(self):
        target = os.path.join(self.root, "nested", "deeper", "case.html")
        export.export_html(product_fixtures.make_bundle(), target)
        self.assertTrue(os.path.exists(target))

    def test_the_export_leaves_no_temporary_files_behind(self):
        export.export_html(product_fixtures.make_bundle(), self.target)
        self.assertEqual([name for name in os.listdir(self.root) if name.startswith(".tmp")], [])


if __name__ == "__main__":
    unittest.main()
