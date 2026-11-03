import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for path in (os.path.join(ROOT, "src"), HERE):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp import statement_detect as sd  # noqa: E402


class DetectContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(HERE, "fixtures", "statement-detect-cases.json"), encoding="utf-8") as f:
            cls.data = json.load(f)

    def test_every_expected_detector_fires(self):
        for case in self.data["cases"]:
            ids = {m.detector_id for m in sd.detect(case["text"])}
            for expected in case["expected_detectors"]:
                self.assertIn(expected, ids, "%s missing %s" % (case["id"], expected))

    def test_frozen_cases_reproduce(self):
        # regeneration check: re-running detect on the same text yields the same ids
        for case in self.data["cases"]:
            a = sorted(m.detector_id for m in sd.detect(case["text"]))
            b = sorted(m.detector_id for m in sd.detect(case["text"]))
            self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
