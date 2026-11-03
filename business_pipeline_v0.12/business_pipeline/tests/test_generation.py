import unittest

from bp import generation as gen


class GenTests(unittest.TestCase):
    def test_ok(self):
        spec = gen.ProblemSpec(scenario="s", transactions=[], adjustments=[],
                              policies={}, given_facts={})
        text, stmts = gen.generate_problem(spec, lambda t: {"status": "ok", "statements": {"IS": {}}})
        self.assertIn("s", text)

    def test_fail(self):
        spec = gen.ProblemSpec(scenario="s", transactions=[], adjustments=[],
                              policies={}, given_facts={})
        with self.assertRaises(ValueError):
            gen.generate_problem(spec, lambda t: {"status": "failed", "diagnostics": ["x"]})


if __name__ == "__main__":
    unittest.main()
