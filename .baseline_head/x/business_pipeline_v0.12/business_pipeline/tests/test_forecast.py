import sys, json, os, unittest
from decimal import Decimal as D
sys.path.insert(0, "src")
from bp import methods
from bp.methods import LIBRARY, forecast_impl, validate_inputs
from bp.orchestrator import Pipeline
from bp.session import SessionManager

yes = lambda s: True
GOLD = json.load(open(os.path.join(os.path.dirname(__file__), "fixtures", "forecast_golden.json")))
SERIES = ["10", "12", "11", "14", "13", "16", "15", "18", "17", "20", "19", "22"]
def req(values=SERIES, horizon=None, codes=None, **kw):
    r = {"objective": "Forecast the next periods", "method": "trend_forecast", "unit": "units", "inputs": {"values": values, "missing_codes": codes or []}}
    if horizon is not None: r["inputs"]["horizon"] = str(horizon)
    r.update(kw); return r

class Golden(unittest.TestCase):
    def test_against_offline_scipy_references(self):
        for c in GOLD:
            out = forecast_impl({"values": c["values"], "missing_codes": c["missing_codes"], "horizon": str(c["horizon"])})
            for k, v in c["expected"].items(): self.assertLessEqual(abs(float(out[k]) - float(v)), 1e-9 * max(1, abs(float(v))), f"{c['name']}.{k}")

class Inputs(unittest.TestCase):
    def blocked(self, r, text):
        d = Pipeline().run(r, yes); self.assertEqual(d.status, "blocked"); self.assertIn(text, d.blocked_reason); return d
    def test_schema(self):
        m = LIBRARY["trend_forecast"]
        self.assertTrue(any("at least 6 items" in e for e in validate_inputs(m, {"values": ["1", "2"]})))
        self.assertTrue(any("horizon" in e for e in validate_inputs(m, {"values": SERIES, "horizon": "x"})))
    def test_horizon_must_be_a_whole_number_in_range(self):
        self.blocked(req(horizon="2.5"), "whole number between 1 and 12")
        self.blocked(req(horizon="0"), "whole number between 1 and 12")
        self.blocked(req(horizon="13"), "whole number between 1 and 12")
    def test_too_few_valid_observations_block(self):
        self.blocked(req(["1", "2", "99", "99", "99", "99"], codes=["99"]), "fewer than six valid")
    def test_constant_series_blocks(self):
        self.blocked(req(["5"] * 8), "constant")
    def test_delivered(self):
        self.assertEqual(Pipeline().run(req(), yes).status, "delivered")

class EndToEnd(unittest.TestCase):
    def ok(self, r):
        p = Pipeline(); d = p.run(r, yes); self.assertEqual(d.status, "delivered", d.blocked_reason); return p, d
    def test_forecast_report(self):
        p, d = self.ok(req())
        for frag in ("linear trend on 12 observations", "slope of 1.003 per period", "forecast for the next 3 period(s) is 22.106",
                     "interval at level 95.00% from 19.373 to 24.839", "24.113", "below the reporting floor",
                     "out-of-sample check on the last 3 periods, held out before fitting, gave a mean absolute error of 1.133, with 100.00% of the held-out values inside the prediction intervals",
                     "does not show causation", "series is short", "ignores seasonality"): self.assertIn(frag, d.report)
        self.assertNotIn("{{", d.report)
        a = {x.id: x for x in p.store.all()}; self.assertEqual(a["forecast_1"].value.unit, "units"); self.assertEqual(a["p_slope"].value.unit, "probability"); self.assertEqual(a["coverage_holdout"].value.unit, "rate"); self.assertEqual(a["n_holdout"].value.precision, 0); self.assertEqual(a["horizon"].value.precision, 0)
    def test_out_of_sample_holdout_excludes_the_recent_past(self):
        # linear for periods 1..6, then a break at periods 7..8: the held-out fit (on 1..6) predicts 7 and 8, so mae = 6 and coverage = 1/2
        _, d = self.ok(req(["1", "2", "3", "4", "5", "6", "7", "20"], horizon="1"))
        self.assertIn("mean absolute error of 6.000, with 50.00%", d.report)
    def test_missing_code_counts_and_positions_kept(self):
        _, d = self.ok(req(GOLD[1]["values"], codes=GOLD[1]["missing_codes"], horizon="2"))
        self.assertIn("1 entries excluded as missing", d.report); self.assertIn("linear trend on 11 observations", d.report)
    def test_synthetic_label(self):
        _, d = self.ok(req(provenance={"values": "synthetic"})); self.assertIn("synthetic data", d.report)
    def test_plan_and_states(self):
        s = SessionManager().create(req()); self.assertEqual(s.plan["fallbacks"], {}); self.assertIn("Out-of-sample check", " ".join(a["question"] for a in s.plan["ambiguities"]))
        s.confirm(True); d = s.to_dict(); self.assertEqual(d["stage_states"]["verification"], "passed")

class WrongImplementations(unittest.TestCase):
    def run_bad(self, bad):
        orig = LIBRARY["trend_forecast"]; LIBRARY["trend_forecast"] = orig.__class__(**{**orig.__dict__, "impl": bad})
        try: return Pipeline().run(req(), yes)
        finally: LIBRARY["trend_forecast"] = orig
    def test_forecast_bugs_blocked(self):
        g = forecast_impl
        bugs = {"flat_forecast": lambda i: {**g(i), **{f"forecast_{h}": D(str(i["values"][-1])) for h in range(1, int(D(str(i.get('horizon', '1')))) + 1)}},
                "narrow_interval": lambda i: {**g(i), "ci_lower_1": g(i)["forecast_1"] - D("0.1")},
                "mae_negative": lambda i: {**g(i), "mae_holdout": -g(i)["mae_holdout"]},
                "coverage_over_one": lambda i: {**g(i), "coverage_holdout": D("1.5")},
                "slope_flipped": lambda i: {**g(i), "slope": -g(i)["slope"]}}
        for name, bad in bugs.items(): self.assertEqual(self.run_bad(bad).status, "blocked", name)
    def test_discovery(self):
        d = methods.describe("trend_forecast"); self.assertEqual(d["claim_ceiling"], "predictive"); self.assertEqual(d["assumption_checks"], []); self.assertIn("Extrapolation", d["limitations"][1])
if __name__ == "__main__": unittest.main()
