"""PROVISIONAL tests for marketing/A-framework-the-product-lacks.

PROVISIONAL - generated scaffold, not wired into the running system

The human writes the real expectations.  This sketch only pins the shape so the
suite cannot be green by construction with no assertions.
"""
import unittest


class AFrameworkTheProductLacksTest(unittest.TestCase):
    def test_the_method_is_defined(self):
        from bp import methods
        self.assertIn("A-framework-the-product-lacks", methods.LIBRARY)

    def test_a_declared_input_round_trips(self):
        self.skipTest("write the first real case: declare figures, run, assert the result")


if __name__ == "__main__":
    unittest.main()
