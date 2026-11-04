import unittest

from bp import determinism as det


class DeterminismTests(unittest.TestCase):
    def test_hash_inputs_stable(self):
        h1 = det.hash_inputs("abc", "v1")
        h2 = det.hash_inputs("abc", "v1")
        self.assertEqual(h1, h2)

    def test_hash_outputs_stable(self):
        h1 = det.hash_outputs({"a": 1}, {"x": "5"})
        h2 = det.hash_outputs({"a": 1}, {"x": "5"})
        self.assertEqual(h1, h2)

    def test_assert_deterministic_ok(self):
        def run_fn(t):
            return {"output_hash": "same"}
        det.assert_deterministic(run_fn, "x", runs=3)

    def test_assert_deterministic_fail(self):
        counter = {"n": 0}
        def run_fn(t):
            counter["n"] += 1
            return {"output_hash": str(counter["n"])}
        with self.assertRaises(det.DeterminismFailure):
            det.assert_deterministic(run_fn, "x", runs=3)


if __name__ == "__main__":
    unittest.main()
