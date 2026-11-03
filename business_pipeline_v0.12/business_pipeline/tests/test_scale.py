import unittest

from bp import statement_runtime as rt


class ScaleTests(unittest.TestCase):
    def test_large_input_runs(self):
        lines = ["Cash sales of 1000."] * 1000
        text = " ".join(lines)
        r = rt.run(text)
        self.assertEqual(r.status, "ok")
        self.assertTrue(r.gates["tb_balanced"])


if __name__ == "__main__":
    unittest.main()
