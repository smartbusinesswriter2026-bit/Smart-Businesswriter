import unittest

from bp import articulation as art


class _Obj:
    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class ArticulationTests(unittest.TestCase):
    def test_all_pass(self):
        tb = _Obj(total_dr=100, total_cr=100)
        is_ = _Obj(net_income=10)
        re_ = _Obj(net_income=10, closing=10)
        bs = _Obj(assets=100, liabilities=60, equity=40, retained_earnings=10, cash=5)
        cf = _Obj(ending_cash=5, cfo=10, cfi=-3, cff= -2, net_change=5)
        self.assertEqual(art.run_gates(tb, is_, re_, bs, cf), [])

    def test_failure(self):
        tb = _Obj(total_dr=100, total_cr=100)
        is_ = _Obj(net_income=10)
        re_ = _Obj(net_income=10, closing=10)
        bs = _Obj(assets=100, liabilities=60, equity=40, retained_earnings=10, cash=999)
        cf = _Obj(ending_cash=5, cfo=10, cfi=-3, cff=-2, net_change=5)
        issues = art.run_gates(tb, is_, re_, bs, cf)
        self.assertTrue(any(i.gate == "cash_articulates_cf_bs" for i in issues))


if __name__ == "__main__":
    unittest.main()
