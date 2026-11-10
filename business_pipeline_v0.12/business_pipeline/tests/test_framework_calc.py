"""Portfolio arithmetic is the core's; the adapter only calls and classifies."""

import sys
import unittest

sys.path.insert(0, "src")

from bp.product import framework_calc  # noqa: E402


def fake_core(name, inputs):
    if name == "market_share":
        firm = float(inputs["firm_sales"])
        rival = float(inputs["largest_competitor_sales"])
        market = float(inputs["market_sales"])
        return {"relative_market_share": firm / rival, "market_share": firm / market}
    if name == "weighted_summary":
        values = [float(value) for value in inputs["values"]]
        weights = [float(weight) for weight in inputs["weights"]]
        return {"weighted_mean": sum(v * w for v, w in zip(values, weights)) / sum(weights)}
    if name == "fmea_rpn":
        severity = float(inputs["severity"])
        occurrence = float(inputs["occurrence"])
        detection = float(inputs["detection"])
        return {"severity": severity, "occurrence": occurrence, "detection": detection,
                "rpn": severity * occurrence * detection}
    if name == "five_s_score":
        scores = [float(value) for value in inputs["scores"]]
        maximum = float(inputs["maximum"])
        total = sum(scores)
        max_total = maximum * len(scores)
        return {"n": len(scores), "total": total, "max_total": max_total,
                "score_rate": total / max_total}
    raise KeyError(name)


class BcgTest(unittest.TestCase):
    def setUp(self):
        framework_calc.set_method_compute(fake_core)

    def tearDown(self):
        framework_calc.set_method_compute(None)

    def test_relative_share_and_growth_come_from_the_core_then_classify(self):
        units = [
            {"unit": "Fresh", "market": "grocery", "growth": 0.08,
             "own_share": 0.30, "competitor_share": 0.15},
            {"unit": "Home", "market": "household", "growth": 0.01,
             "own_share": 0.10, "competitor_share": 0.20},
            {"unit": "Edge", "market": "grocery", "growth": 0.03,
             "own_share": 0.21, "competitor_share": 0.20},
        ]
        result = framework_calc.bcg(units, growth_cutoff=0.03)
        self.assertTrue(result["ok"], result)
        rows = result["rows"]
        self.assertEqual(rows[0][4], "Star")
        self.assertEqual(rows[1][4], "Dog")
        self.assertEqual(rows[2][4], "Star")
        self.assertIn("threshold", rows[2][5])

    def test_the_cutoff_defaults_to_the_portfolio_average(self):
        units = [
            {"unit": "Fresh", "growth": 0.08, "own_share": 0.30, "competitor_share": 0.15},
            {"unit": "Home", "growth": 0.01, "own_share": 0.10, "competitor_share": 0.20},
        ]
        result = framework_calc.bcg(units)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0][4], "Star")
        self.assertEqual(result["rows"][1][4], "Dog")
        self.assertIn("portfolio average", " ".join(result["lines"]))

    def test_a_unit_without_growth_is_not_placed(self):
        result = framework_calc.bcg([{"unit": "A", "own_share": 0.2,
                                      "competitor_share": 0.1}])
        self.assertFalse(result["ok"])
        self.assertEqual(result["rows"][0][4], "Not placed")
        self.assertTrue(any("growth" in problem for problem in result["problems"]))

    def test_no_core_means_no_figure(self):
        framework_calc.set_method_compute(None)
        result = framework_calc.bcg([{"unit": "A", "growth": 0.04,
                                      "own_share": 0.2, "competitor_share": 0.1}])
        self.assertFalse(result["ok"])
        self.assertTrue(any("core is not attached" in problem
                            for problem in result["problems"]), result["problems"])

    def test_for_template_reads_the_brief_table(self):
        brief = ("Unit | Market | Growth | Own share | Top competitor share\n"
                 "A | grocery | 4% | 30% | 15%\n")
        result = framework_calc.for_template("template_bcg", brief)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0][4], "Star")


class QualityCalcTest(unittest.TestCase):
    def setUp(self):
        framework_calc.set_method_compute(fake_core)

    def tearDown(self):
        framework_calc.set_method_compute(None)

    def test_rpn_is_the_product_and_the_pareto_is_ranked(self):
        rows = [{"id": "1", "failure": "Seal leaks", "severity": 7,
                 "occurrence": 4, "detection": 3},
                {"id": "2", "failure": "Wrong part", "severity": 4,
                 "occurrence": 6, "detection": 2}]
        result = framework_calc.fmea(rows)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0][5], "84.00")
        self.assertEqual(result["chart"]["kind"], "pareto")
        self.assertEqual(result["chart"]["points"][0]["label"], "Seal leaks")
        self.assertEqual(result["chart"]["points"][0]["cumulative"], "84.00")

    def test_a_severity_nine_is_a_priority_whatever_the_rpn(self):
        result = framework_calc.fmea([{"id": "1", "failure": "Safety",
                                       "severity": 9, "occurrence": 1,
                                       "detection": 1}])
        self.assertEqual(result["rows"][0][6], "Severity 9-10")

    def test_the_five_s_scores_come_from_the_core(self):
        rows = [{"category": "Sort", "score": 3, "maximum": 4},
                {"category": "Sort", "score": 2, "maximum": 4},
                {"category": "Shine", "score": 4, "maximum": 4}]
        result = framework_calc.five_s(rows)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0][4], "62.5")
        self.assertEqual(result["chart"]["kind"], "bar")
        self.assertEqual(len(result["chart"]["points"]), 2)

    def test_for_quality_reads_the_table(self):
        brief = ("ID | Failure mode | S | O | D\n"
                 "1 | Seal leaks | 7 | 4 | 3\n"
                 "2 | Wrong part | 4 | 6 | 2\n")
        result = framework_calc.for_quality("fmea", brief)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0][5], "84.00")


class GeTest(unittest.TestCase):
    def setUp(self):
        framework_calc.set_method_compute(fake_core)

    def tearDown(self):
        framework_calc.set_method_compute(None)

    def test_weighted_totals_come_from_the_core_and_map_to_a_zone(self):
        units = [{
            "unit": "Fresh",
            "attractiveness": {"values": [4, 5], "weights": [50, 50]},
            "strength": {"values": [4, 4], "weights": [60, 40]},
        }]
        result = framework_calc.ge(units)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["rows"][0][1], "4.50")
        self.assertEqual(result["rows"][0][2], "4.00")
        self.assertEqual(result["rows"][0][3], "Invest / grow")

    def test_weights_that_do_not_sum_to_one_hundred_are_refused(self):
        units = [{
            "unit": "Fresh",
            "attractiveness": {"values": [4, 5], "weights": [50, 40]},
            "strength": {"values": [4, 4], "weights": [60, 40]},
        }]
        result = framework_calc.ge(units)
        self.assertFalse(result["ok"])
        self.assertTrue(any("sum to 100" in problem for problem in result["problems"]))


if __name__ == "__main__":
    unittest.main()
