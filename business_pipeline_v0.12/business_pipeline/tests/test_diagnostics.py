import unittest

from bp import diagnostics as dg


class DiagnosticsTests(unittest.TestCase):
    def test_str_format(self):
        d = dg.Diagnostic(stage="RESOLVE", gate="policy_required", input_ref=None,
                          expected=["full_year", "pro_rata"], actual=None,
                          hint="add a policy claim", severity="fail")
        s = str(d)
        self.assertIn("[fail]", s)
        self.assertIn("RESOLVE.policy_required", s)
        self.assertIn("hint:", s)


if __name__ == "__main__":
    unittest.main()
