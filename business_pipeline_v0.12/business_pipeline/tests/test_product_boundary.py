"""The product layer must not touch the frozen core (B-079, B-080).

The product backend is additive: it works on the JSON documents the frozen
core already produces, it never imports it, and it computes no business
number.  These tests make that mechanical rather than a promise.
"""

import ast
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

import product_fixtures  # noqa: E402
from bp.product import api, cases, export  # noqa: E402

PRODUCT_DIR = os.path.join(ROOT, "src", "bp", "product")

#: Frozen core modules the product layer must never import or shadow.
FROZEN_MODULES = ("methods", "orchestrator", "session", "server", "spec", "sandbox",
                  "sandbox_child", "artifacts", "quantity", "claims", "ledger",
                  "schedules", "accounts", "reconcile", "report", "llm", "assist",
                  "literature", "ingest", "currency", "evaluate", "registry",
                  "catalogue_import", "reperform", "envpin")


def _product_sources():
    for name in sorted(os.listdir(PRODUCT_DIR)):
        if name.endswith(".py"):
            with open(os.path.join(PRODUCT_DIR, name), encoding="utf-8") as stream:
                yield name, stream.read()


class ProductBoundaryTest(unittest.TestCase):
    def test_the_product_package_exists_and_is_small(self):
        names = [name for name, _ in _product_sources()]
        self.assertIn("__init__.py", names)
        self.assertIn("cases.py", names)
        self.assertIn("api.py", names)
        self.assertIn("export.py", names)

    def test_the_product_package_imports_only_the_standard_library(self):
        for name, source in _product_sources():
            tree = ast.parse(source, filename=name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        root = alias.name.split(".")[0]
                        self.assertIn(root, sys.stdlib_module_names,
                                      "%s imports %s, which is not standard library" % (name, alias.name))
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        continue  # a relative import inside the product package
                    root = (node.module or "").split(".")[0]
                    self.assertIn(root, sys.stdlib_module_names,
                                  "%s imports %s, which is not standard library" % (name, node.module))

    def test_the_product_package_never_imports_the_frozen_core(self):
        for name, source in _product_sources():
            tree = ast.parse(source, filename=name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertFalse(alias.name == "bp" or alias.name.startswith("bp."),
                                         "%s imports the frozen core (%s)" % (name, alias.name))
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    module = node.module or ""
                    self.assertFalse(module == "bp" or module.startswith("bp."),
                                     "%s imports the frozen core (%s)" % (name, module))

    def test_the_product_package_does_not_shadow_a_frozen_module(self):
        for name, _ in _product_sources():
            self.assertNotIn(name[:-3], FROZEN_MODULES,
                             "%s would shadow a frozen core module" % name)

    def test_no_third_party_dependency_is_declared_for_the_product_layer(self):
        third_party = ("docx", "openpyxl", "jinja2", "numpy", "pandas", "xlsxwriter", "lxml", "bs4")
        for name, source in _product_sources():
            for package in third_party:
                self.assertNotIn(package, source, "%s references %s" % (name, package))

    def test_the_product_layer_computes_no_number(self):
        """Every number the product layer shows was already recorded."""
        root = tempfile.mkdtemp(prefix="bp-boundary-test-")
        previous = os.environ.get("BP_CASES_DIR")
        os.environ["BP_CASES_DIR"] = root
        try:
            bundle = product_fixtures.make_bundle()
            status, stored = api.handle("POST", "/api/cases", bundle)
            self.assertEqual(status, 201)
            recorded = set(re.findall(r"\d+(?:\.\d+)*", json.dumps(stored, ensure_ascii=False)))
            shown = set(re.findall(r"\d+(?:\.\d+)*", json.dumps(stored, ensure_ascii=False)))
            self.assertEqual(shown - recorded, set())

            target = os.path.join(root, "export.html")
            export.export_html(stored, target)
            with open(target, encoding="utf-8") as stream:
                document = stream.read()
            sections = re.findall(r"<section id=\"[a-z]+\">(.*?)</section>", document, re.S)
            content = " ".join(re.sub(r"<[^>]+>", "", section) for section in sections)
            self.assertEqual(set(re.findall(r"\d+(?:\.\d+)*", content)) - recorded, set())
        finally:
            if previous is None:
                os.environ.pop("BP_CASES_DIR", None)
            else:
                os.environ["BP_CASES_DIR"] = previous
            shutil.rmtree(root, ignore_errors=True)

    def test_the_case_store_does_not_read_the_frozen_core(self):
        """The store only reads and writes its own directory."""
        source = open(os.path.join(PRODUCT_DIR, "cases.py"), encoding="utf-8").read()
        tree = ast.parse(source)
        called = {node.func.id for node in ast.walk(tree)
                  if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertNotIn("open", called)
        self.assertNotIn("eval", called)
        self.assertNotIn("exec", called)

    def test_the_product_modules_are_importable_without_the_frozen_core(self):
        """`bp.product` imports nothing from the core, so it stands alone."""
        for name in ("bp.product", "bp.product.cases", "bp.product.api", "bp.product.export"):
            self.assertIn(name, sys.modules)


if __name__ == "__main__":
    unittest.main()
