"""The scaffold generator: a reviewable skeleton, never a working capability."""
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, "src")

from bp.product import scaffold  # noqa: E402


class ScaffoldTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="bp-scaffold-")
        self.previous = os.environ.get("BP_SCAFFOLD_ROOT")
        os.environ["BP_SCAFFOLD_ROOT"] = self.root

    def tearDown(self):
        if self.previous is None:
            os.environ.pop("BP_SCAFFOLD_ROOT", None)
        else:
            os.environ["BP_SCAFFOLD_ROOT"] = self.previous
        shutil.rmtree(self.root, ignore_errors=True)

    def test_the_scaffold_writes_five_provisional_files(self):
        result = scaffold.generate("economics", "newtile",
                                   "Value a forest's carbon credits over ten years.")
        self.assertEqual(result["subject"], "economics")
        self.assertEqual(result["tile"], "newtile")
        names = sorted(os.path.basename(path) for path in result["paths"])
        self.assertEqual(names, ["README.md", "capability_entry.py", "method_stub.py",
                                 "preset.json", "test_sketch.py"])
        for path in result["paths"]:
            self.assertTrue(os.path.isfile(path), path)
        for name in ("method_stub.py", "capability_entry.py", "test_sketch.py", "README.md"):
            with open(os.path.join(result["folder"], name), encoding="utf-8") as handle:
                self.assertIn("PROVISIONAL", handle.read(), name)

    def test_the_readme_carries_the_growth_brief_and_the_research_order(self):
        result = scaffold.generate("economics", "newtile", "A gap the system cannot answer.")
        with open(os.path.join(result["folder"], "README.md"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("Known mistakes to avoid", text)
        self.assertIn("local first", text)
        self.assertIn("vetted source finder", text)

    def test_the_scaffold_is_not_wired_into_the_running_system(self):
        result = scaffold.generate("economics", "newtile", "A gap.")
        with open(os.path.join(result["folder"], "method_stub.py"), encoding="utf-8") as handle:
            text = handle.read()
        self.assertIn("not wired into the running system", text)
        self.assertIn("raise NotImplementedError", text)


if __name__ == "__main__":
    unittest.main()
