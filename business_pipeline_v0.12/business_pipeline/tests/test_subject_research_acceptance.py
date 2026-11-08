"""Acceptance suite for the Research & statistics shelf -- one test per row of `qa/manual/research.md`.

The manual is the specification: every `E-res-nnn` row names a test below.  Nothing here is a new
requirement: each expectation is traced to the shipped catalogue (`subjects.detail("research")`), the
frozen method library (`bp.methods.LIBRARY`), the paper rules in `docs/VALIDATION_HARNESS.md` §5
(V-01..V-20), or an owner presentation rule (P1..P6), and the source is cited in the manual.

Rules this file keeps:
  * offline -- no provider key, no network, no model call;
  * it asserts the product's behaviour through the real paths (`Pipeline.run` ->
    `session_paper.sections` -> `session_paper.docx_bytes`), and it never edits an expected value to
    go green;
  * a refusal is a refusal: a test that expects one asserts the reason too;
  * a figure is proved against arithmetic written out in `qa/probe_research_shelf.py`, not against
    the engine's own second route (the trap on this shelf: a statistical "pass" that agreed with
    itself would pass forever).

Run:  PYTHONPATH=src python -m pytest tests/test_subject_research_acceptance.py -q
"""

import os
import re
import sys
import tempfile
import unittest
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
QA = os.path.join(ROOT, "qa")
for path in (SRC, QA):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp import registry, server                              # noqa: E402
from bp.methods import LIBRARY                               # noqa: E402
from bp.orchestrator import Pipeline                         # noqa: E402
from bp.product import session_paper, spreadsheets, subjects  # noqa: E402

import probe_research_shelf as probe                          # noqa: E402

SUBJECT = "research"
RECORDS = ["QNT-STA-01", "QNT-STA-02", "QNT-STA-03", "QNT-STA-04", "QNT-STA-05",
           "QNT-STA-06", "QNT-STA-07", "QNT-STA-08", "QNT-STA-09", "QNT-STA-10"]
#: The four tools that ship with no preset: the student types the figures.
TYPED = ("spearman", "ols_robust", "mann_whitney", "kruskal_wallis")


def page():
    return subjects.detail(SUBJECT)


def tools():
    return page()["tools"]


def records():
    return {row["id"]: row for row in page()["records"]}


def catalogue_ids():
    return [row["id"] for row in page()["catalogue"]]


def deliver(tool):
    """The delivered record for one tool, on the case the manual proves it with."""
    preset = server.PRESETS.get(tool["preset"] or "") or {}
    return Pipeline().run({"objective": preset.get("objective") or "research acceptance",
                           "method": tool["method"],
                           "inputs": probe.case_for(tool)}, lambda spec: True)


_PAPERS = {}


def built(tool):
    """(delivery, bundle, text) for one tool, cached: the paper a reader holds."""
    key = tool["key"]
    if key not in _PAPERS:
        delivery = deliver(tool)
        bundle = {"report": delivery.report, "appendix": delivery.appendix}
        _PAPERS[key] = (delivery, bundle, probe.text_of(session_paper.docx_bytes(bundle)))
    return _PAPERS[key]


def paper_text(tool):
    return built(tool)[2]


def figures_of(tool):
    _delivery, bundle, _text = built(tool)
    return (bundle["appendix"].get("reperform") or {}).get("outputs") or {}


class RecordHonestyTest(unittest.TestCase):
    """E-res-011..015 -- D-RES-01: a record may not deny a method that ships."""

    #: The five records that read "Method not built" while the page offered a
    #: calculator for the area, and the methods each now claims.
    REPAIRED = {
        "QNT-STA-02": ["power_analysis"],
        "QNT-STA-05": ["reliability_alpha"],
        "QNT-STA-06": ["multiple_comparison", "missing_data_bounds"],
        "QNT-STA-07": ["trend_forecast"],
        "QNT-STA-09": ["difference_in_differences", "regression_discontinuity",
                       "instrumental_variables", "panel_regression"],
    }

    def test_E_res_011__no_record_denies_a_method_that_ships(self):
        problems = []
        for rid, row in records().items():
            status = (row.get("status_note") or "").strip().lower()
            if status.startswith("not implemented") and row["linked_methods"]:
                problems.append("%s says 'not implemented' and links %r"
                                % (rid, row["linked_methods"]))
            if row["status_short"] == "Method not built" and rid not in ("QNT-STA-08",
                                                                        "QNT-STA-10"):
                problems.append("%s still reads 'Method not built'" % rid)
        self.assertEqual(problems, [], "; ".join(problems))

    def test_E_res_012__the_five_repaired_records_link_the_method_they_claim(self):
        rows = records()
        for rid, expected in self.REPAIRED.items():
            self.assertIn(rid, rows, rid)
            self.assertEqual(sorted(rows[rid]["linked_methods"]), sorted(expected), rid)
            self.assertEqual(rows[rid]["form"], "computed", rid)
            self.assertTrue(rows[rid]["status_note"].startswith("partial:"), rid)
            for method in expected:
                self.assertIn(method, LIBRARY,
                              "%s links %r, which is not a frozen method" % (rid, method))

    def test_E_res_013__the_two_unbuilt_records_name_what_is_missing_and_link_nothing(self):
        rows = records()
        for rid in ("QNT-STA-08", "QNT-STA-10"):
            self.assertEqual(rows[rid]["form"], "read_only", rid)
            self.assertEqual(rows[rid]["linked_methods"], [], rid)
            self.assertEqual(rows[rid]["status_short"], "Method not built", rid)
        # and the gap is real: no frozen method computes clusters or structural models
        for method in LIBRARY:
            self.assertNotIn("kmeans", method)
            self.assertNotIn("cluster", method)
            self.assertNotIn("structural", method)

    def test_E_res_014__the_committed_slice_and_the_registry_agree(self):
        registry_records = {row["id"]: row for row in registry.load()["records"]}
        rows = records()
        for rid in RECORDS:
            self.assertIn(rid, rows, rid)
            self.assertEqual(rows[rid]["implementation_status"],
                             registry_records[rid]["implementation_status"], rid)

    def test_E_res_015__a_record_whose_calculator_is_elsewhere_says_which_shelf(self):
        row = records()["QNT-STA-09"]
        self.assertFalse(row.get("tool_here", True),
                         "QNT-STA-09 claims its calculator is on this page")
        self.assertIn("Economics shelf", row["status_note"],
                      "the record does not say where the calculator is")
        self.assertIn("not implemented", row["status_note"],
                      "the record no longer says what it cannot do")


class PaperTest(unittest.TestCase):
    """E-res-016..026 -- the papers, read on the artefact (P6)."""

    def test_E_res_016__every_tool_delivers_a_paper_in_the_declared_order(self):
        order = [heading for _key, heading in session_paper.HEADINGS]
        for tool in tools():
            delivery, bundle, text = built(tool)
            self.assertEqual(delivery.status, "delivered", "%s: %s"
                             % (tool["key"], delivery.blocked_reason))
            present = [line for line in text.splitlines() if line in order]
            self.assertEqual(present, sorted(present, key=order.index),
                             "%s prints its sections out of order: %r" % (tool["key"], present))
            for required in ("Result", "Inputs and results", "Honesty: what was not done",
                             "How the figures were checked"):
                self.assertIn(required, present, "%s has no %r section" % (tool["key"], required))
            # B-215 (owner unfreeze): a fifth honesty field carries a descriptive method's own
            # caveats, so all 21 papers state what they cannot establish.  Before it, `power` and
            # `missing` printed no honesty heading at all and this test pinned that gap.
            honesty = bundle["appendix"].get("honesty") or {}
            self.assertTrue(any(honesty.values()), "%s discloses nothing" % tool["key"])

    def test_E_res_017__every_declared_check_is_printed_and_none_is_renamed(self):
        for tool in tools():
            method = LIBRARY[tool["method"]]
            delivery, _bundle, text = built(tool)
            self.assertTrue(method.test_names, "%s declares no checks" % tool["method"])
            self.assertEqual(len(delivery.appendix["tests"]), len(method.test_names),
                             "%s ran %d checks of %d declared"
                             % (tool["key"], len(delivery.appendix["tests"]),
                                len(method.test_names)))
            for name in method.test_names:
                self.assertIn(probe._plain(name) + ".", text,
                              "%s does not print the %r check" % (tool["key"], name))

    def test_E_res_018__every_paper_prints_its_assumptions_and_limitations(self):
        for tool in tools():
            method = LIBRARY[tool["method"]]
            text = paper_text(tool)
            self.assertTrue(method.assumptions, tool["method"])
            self.assertTrue(method.limitations, tool["method"])
            for sentence in method.assumptions:
                self.assertIn(sentence, text, "%s drops an assumption" % tool["key"])

    def test_E_res_019__every_figure_prints_at_the_methods_declared_precision(self):
        for tool in tools():
            _delivery, bundle, text = built(tool)
            checked, mismatched, _unchecked = probe.precision_report(tool, bundle, text)
            self.assertGreater(checked, 0, "%s printed no figure at a declared precision"
                               % tool["key"])
            self.assertEqual(mismatched, 0, "%s printed a figure at the wrong precision"
                             % tool["key"])
            # D-RES-05 (B-214): a figure at six or more decimals reads as an unrounded Decimal.
            # The declaration is what makes it right; this asserts no method on this shelf
            # declares that many, so the paper cannot print one.
            self.assertNotRegex(text, r"\d\.\d{6,}",
                                "%s prints a figure at six or more decimal places" % tool["key"])

    def test_E_res_020__no_paper_prints_a_python_repr(self):
        for tool in tools():
            text = paper_text(tool)
            for mark in ("{'", "['", "'}", "']", "Decimal(", "None"):
                self.assertNotIn(mark, text, "%s prints %r" % (tool["key"], mark))

    def test_E_res_021__two_identical_runs_produce_identical_bytes(self):
        tool = next(row for row in tools() if row["key"] == "welch")
        delivery = built(tool)[0]
        first = session_paper.docx_bytes({"report": delivery.report,
                                          "appendix": delivery.appendix})
        again = deliver(tool)
        second = session_paper.docx_bytes({"report": again.report, "appendix": again.appendix})
        self.assertEqual(first, second, "the same inputs produced different paper bytes")

    def test_E_res_023__the_hash_stays_in_the_record(self):
        tool = next(row for row in tools() if row["key"] == "welch")
        delivery = built(tool)[0]
        self.assertTrue(delivery.appendix.get("spec_hash"),
                        "the record carries no specification hash")


    def test_E_res_022__no_download_carries_a_specification_footer_or_a_hash(self):
        footer = ("How this was produced", "Specification hash", "Code hash", "Outputs hash",
                  "Document hash")
        tool = next(row for row in tools() if row["key"] == "welch")
        delivery = built(tool)[0]
        marker = "spec-" + "c" * 59
        bundle = {"id": "res-p3", "title": "Welch two-sample t-test", "method": tool["method"],
                  "spec_hash": marker, "outputs_hash": marker,
                  "delivery": {"report": delivery.report, "appendix": delivery.appendix}}
        downloads = {
            "computation": "\n".join(line for _heading, lines in
                                     session_paper.sections(bundle["delivery"]) for line in lines),
            "csv": spreadsheets.to_csv(bundle),
            "spreadsheetml": spreadsheets.to_spreadsheetml(bundle),
        }
        for name, text in downloads.items():
            self.assertTrue(text.strip(), "%s is empty" % name)
            for fragment in footer:
                self.assertNotIn(fragment, text, "%s still prints %r" % (name, fragment))
            self.assertNotIn("cccccccccc", text, "%s shows part of the hash" % name)
        self.assertEqual(bundle["spec_hash"], marker)

    def test_E_res_024__there_is_no_markdown_download_anywhere(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        for forbidden in ('format: "md"', "format:'md'", "Download (Markdown)", "Markdown)"):
            self.assertNotIn(forbidden, page_html, forbidden)
        server_py = open(os.path.join(SRC, "bp", "server.py"), encoding="utf-8").read()
        self.assertNotIn("session_paper.markdown", server_py)
        api_py = open(os.path.join(SRC, "bp", "product", "api.py"), encoding="utf-8").read()
        self.assertNotIn('"md"', api_py)

    def test_E_res_025__no_paper_or_page_promises_a_diagram(self):
        for relative in (("bp", "product", "session_paper.py"), ("bp", "product", "docx.py")):
            source = open(os.path.join(SRC, *relative), encoding="utf-8").read()
            self.assertNotIn("Diagram to draw", source, relative[-1])
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        self.assertNotIn("Diagram to draw", page_html)
        for tool in tools():
            self.assertNotIn("Diagram to draw", paper_text(tool), tool["key"])

    def test_E_res_026__the_chart_and_export_cards_keep_the_ids_the_script_binds(self):
        page_html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
        for anchor in ("chartbtn", "expbtn", "expzip"):
            self.assertIn('id="%s"' % anchor, page_html,
                          "the inline script binds #%s unguarded" % anchor)


class FigureTest(unittest.TestCase):
    """E-res-027..046 -- every figure proved by hand, on the paper (§4.5)."""

    def figure(self, key, name):
        tool = next(t for t in tools() if t["key"] == key)
        return probe.printed_figure(paper_text(tool), name)

    def test_E_res_027__descriptive_statistics_on_the_hand_case(self):
        # values 2,4,4,4,5,5,7,9: n=8, mean 5, median 4.5, variance 32/7=4.5714, sd 2.1381
        self.assertEqual(self.figure("descriptive", "n"), "8")
        self.assertEqual(self.figure("descriptive", "mean"), "5.00")
        self.assertEqual(self.figure("descriptive", "median"), "4.50")
        self.assertEqual(self.figure("descriptive", "variance"), "4.57")
        self.assertEqual(self.figure("descriptive", "sd"), "2.14")

    def test_E_res_028__pearson_r_and_its_t_test(self):
        # x=1..5, y=2,3,5,4,6: r = 9/sqrt(10*10) = 0.9; t = 0.9*sqrt(3)/sqrt(0.19) = 3.5762
        self.assertEqual(self.figure("pearson", "r"), "0.900")
        self.assertEqual(self.figure("pearson", "r_squared"), "0.810")
        self.assertEqual(self.figure("pearson", "p_value"), "0.0374")

    def test_E_res_029__spearman_rho_on_six_ranked_pairs(self):
        # d = 1,-1,1,-1,1,-1 -> sum d^2 = 6 -> rho = 1 - 36/210 = 0.828571
        self.assertEqual(self.figure("spearman", "rho"), "0.829")

    def test_E_res_030__welch_uses_the_welch_satterthwaite_df_not_n1_plus_n2_minus_2(self):
        # a=1,2,3,4 (mean 2.5, var 1.6667), b=5,6,7 (mean 6, var 1): diff -3.5,
        # se 0.8660, t -4.0415, df = 0.75^2/((0.41667^2/3)+(0.33333^2/2)) = 4.9591
        self.assertEqual(self.figure("welch", "diff"), "-3.500")
        self.assertEqual(self.figure("welch", "se_diff"), "0.866")
        self.assertEqual(self.figure("welch", "t_stat"), "-4.041")
        self.assertEqual(self.figure("welch", "df"), "4.959")
        self.assertNotEqual(self.figure("welch", "df"), "5.000",
                            "the pooled df (n1+n2-2) was used instead of Welch's")
        self.assertEqual(self.figure("welch", "p_value"), "0.0101")

    def test_E_res_031__one_way_anova_f_and_its_two_degrees_of_freedom(self):
        # groups 1-3, 4-6, 7-9: SSB 54 (df 2), SSW 6 (df 6), F = 27, eta2 = 54/60 = 0.9
        self.assertEqual(self.figure("anova", "f_stat"), "27.000")
        self.assertEqual(self.figure("anova", "df_between"), "2")
        self.assertEqual(self.figure("anova", "df_within"), "6")
        self.assertEqual(self.figure("anova", "eta_squared"), "0.900")

    def test_E_res_032__kruskal_wallis_h_on_complete_separation(self):
        # N=9, rank sums 6, 15, 24: H = 12/(9*10)*279 - 30 = 7.2, df 2
        self.assertEqual(self.figure("kruskal_wallis", "h_stat"), "7.200")
        self.assertEqual(self.figure("kruskal_wallis", "df"), "2")

    def test_E_res_033__chi_square_two_by_two_matches_the_closed_form(self):
        # [[20,30],[30,20]]: expected 25 everywhere, chi2 = 4*25/25 = 4.0,
        # p = erfc(sqrt(2)) = 0.0455, Cramer's V = sqrt(4/100) = 0.2
        self.assertEqual(self.figure("chi_square", "chi_squared"), "4.000")
        self.assertEqual(self.figure("chi_square", "df"), "1")
        self.assertEqual(self.figure("chi_square", "p_value"), "0.0455")
        self.assertEqual(self.figure("chi_square", "cramers_v"), "0.200")

    def test_E_res_034__ols_coefficients_and_residual_degrees_of_freedom(self):
        # y = 2,4,5,4,5,7,8,9 on x = 1..8: slope 38/42 = 0.904762, intercept 1.428571,
        # R2 = 38/42, F = (0.904762/0.095238)*6 = 57, residual se 0.7767
        self.assertEqual(self.figure("ols", "coef_x"), "0.905")
        self.assertEqual(self.figure("ols", "coef_intercept"), "1.429")
        self.assertEqual(self.figure("ols", "r_squared"), "0.905")
        self.assertEqual(self.figure("ols", "f_stat"), "57.000")
        self.assertEqual(self.figure("ols", "residual_se"), "0.777")
        self.assertEqual(self.figure("ols", "df_residual"), "6")

    def test_E_res_035__robust_ols_keeps_the_coefficients_and_changes_only_the_errors(self):
        for name in ("coef_x", "coef_intercept"):
            self.assertEqual(self.figure("ols", name), self.figure("ols_robust", name))
        self.assertNotEqual(self.figure("ols", "se_x"), self.figure("ols_robust", "se_x"),
                            "HC3 standard errors are identical to the classical ones")

    def test_E_res_036__one_sample_t_against_the_published_reference_value(self):
        # values 1..11 (mean 6, sd sqrt(11), se 1), mu0 = 4 -> t = 2.0, df = 10
        # published: P(|T| > 2.0) at df 10 is 0.0734
        # The engine declares `df` as a ratio at 3 dp, so it prints 10.000; the value is
        # what matters here, and the declared precision is checked by E-res-019.
        self.assertEqual(self.figure("onesample", "t_stat"), "2.000")
        self.assertEqual(float(self.figure("onesample", "df")), 10.0)
        self.assertEqual(self.figure("onesample", "p_value"), "0.0734")

    def test_E_res_037__paired_t_on_the_five_pairs(self):
        # before 10,12,11,9,13 after 12,13,12,10,14: diffs 2,1,1,1,1
        # mean 1.2, sd 0.4472, se 0.2, t = 6.0, df 4 -> p 0.0039
        self.assertEqual(self.figure("paired", "mean_diff"), "-1.20")
        self.assertEqual(self.figure("paired", "sd_diff"), "0.45")
        self.assertEqual(self.figure("paired", "se_diff"), "0.20")
        self.assertEqual(self.figure("paired", "t_stat"), "-6.000")
        self.assertEqual(self.figure("paired", "p_value"), "0.0039")

    def test_E_res_038__cronbach_alpha_matches_the_sum_formula(self):
        # alpha = k/(k-1) * (1 - sum(item variances)/total variance), recomputed in the kit
        tool = next(t for t in tools() if t["key"] == "alpha")
        kit = probe.independent("reliability_alpha", probe.case_for(tool))
        engine = float(figures_of(tool)["alpha"])
        self.assertAlmostEqual(engine, kit["alpha"], places=4)
        self.assertEqual(self.figure("alpha", "alpha"), "%.4f" % kit["alpha"])

    def test_E_res_039__a_weighted_summary_at_equal_and_unequal_weights(self):
        # 1,2,3,4 with weights 1,1,1,3: (1+2+3+12)/6 = 3.00
        self.assertEqual(self.figure("weighted", "weighted_mean"), "3.00")
        self.assertEqual(self.figure("weighted", "sum_weights"), "6.0000")

    def test_E_res_040__holm_adjustment_matches_the_hand_computation(self):
        # p = 0.01, 0.04, 0.03 -> sorted 0.01, 0.03, 0.04 -> x3, x2, x1 = 0.03, 0.06, 0.04
        # -> monotone max = 0.03, 0.06, 0.06; one test is rejected at alpha 0.05.
        outputs = figures_of(next(t for t in tools() if t["key"] == "multicomp"))
        adjusted = [float(outputs["p_adj_%d" % index]) for index in (1, 2, 3)]
        self.assertEqual(outputs["n_tests"], "3")
        self.assertEqual(sorted(adjusted), [0.03, 0.06, 0.06])
        self.assertEqual(outputs["n_rejected"], "1")
        raw = sorted(float(value) for value in probe.case_for(
            next(t for t in tools() if t["key"] == "multicomp"))["p_values"])
        for index, value in enumerate(sorted(adjusted)):
            self.assertGreaterEqual(value + 1e-12, raw[index],
                                    "an adjusted p is below its raw p")

    def test_E_res_041__missing_data_bounds_bracket_the_observed_mean(self):
        # 10,12,"",14,99(code 99),16 -> 4 valid, mean 13; fill the two with 10 .. 16
        self.assertEqual(self.figure("missing", "n_valid"), "4")
        self.assertEqual(self.figure("missing", "n_missing"), "2")
        self.assertEqual(self.figure("missing", "mean_observed"), "13.00")
        self.assertEqual(self.figure("missing", "bound_low"), "12.00")
        self.assertEqual(self.figure("missing", "bound_high"), "14.00")

    def test_E_res_042__power_against_the_normal_approximation(self):
        # effect 5, sd 10/12, n 30/40: se = sqrt(10^2/30+12^2/40) = 2.6325, ncp 1.899
        # power = P(Z > 1.96 - ncp) + P(Z < -1.96 - ncp) = 0.4757
        self.assertEqual(self.figure("power", "se"), "2.63")
        self.assertEqual(self.figure("power", "ncp"), "1.899")
        self.assertEqual(self.figure("power", "z_alpha"), "1.960")
        self.assertEqual(self.figure("power", "power"), "0.4757")

    def test_E_res_043__posthoc_reports_one_test_per_pair_and_adjusts_upward(self):
        outputs = figures_of(next(t for t in tools() if t["key"] == "posthoc"))
        pairs = [key for key in outputs if key.startswith("p_raw_")]
        self.assertEqual(len(pairs), 3, "three groups give three pairs")
        self.assertEqual(outputs["n_pairs"], "3")
        for raw in pairs:
            self.assertGreaterEqual(float(outputs["p_adj_" + raw.split("p_raw_")[1]]),
                                    float(outputs[raw]) - 1e-12)

    def test_E_res_044__two_way_anova_sums_of_squares_decompose_the_total(self):
        outputs = figures_of(next(t for t in tools() if t["key"] == "factorial"))
        parts = sum(float(outputs[key]) for key in ("ss_a", "ss_b", "ss_ab", "ss_error"))
        self.assertAlmostEqual(parts, float(outputs["ss_total"]), places=6)
        self.assertAlmostEqual(float(outputs["ms_error"]),
                               float(outputs["ss_error"]) / 4.0, places=6)

    def test_E_res_045__a_logistic_odds_ratio_is_the_exponent_of_its_coefficient(self):
        import math
        outputs = figures_of(next(t for t in tools() if t["key"] == "logit"))
        for name in ("size", "group", "intercept"):
            self.assertAlmostEqual(float(outputs["odds_ratio_" + name]),
                                   math.exp(float(outputs["coef_" + name])), places=3)

    def test_E_res_046__the_forecast_slope_is_the_least_squares_slope_of_the_series(self):
        # 1,2,2,4,4,5,7 on t = 1..7: slope 26/28 = 0.928571, intercept -0.142857
        self.assertEqual(self.figure("forecast", "slope"), "0.929")
        self.assertEqual(self.figure("forecast", "intercept"), "-0.143")


class InventoryTest(unittest.TestCase):
    """E-res-001..010 -- the shelf, reconciled against the catalogue."""

    def test_E_res_001__the_shelf_declares_21_tools_with_distinct_keys(self):
        rows = tools()
        self.assertEqual(len(rows), 21)
        self.assertEqual(len({row["key"] for row in rows}), 21, "a tool key is declared twice")
        for row in rows:
            self.assertTrue(row["label"] and row["what"], row["key"])
            self.assertEqual(row["kind"], "compute")

    def test_E_res_002__every_tool_resolves_to_a_frozen_method_and_a_runnable_preset(self):
        for row in tools():
            self.assertIn(row["method"], LIBRARY, "%s launches %r, not a frozen method"
                          % (row["key"], row["method"]))
            if row["key"] in TYPED:
                self.assertIsNone(row["preset"], "%s is a typed-input tool" % row["key"])
                continue
            self.assertIsNotNone(row["preset"], "%s ships no preset and no typed case" % row["key"])
            self.assertIn(row["preset"], server.PRESETS, row["key"])
            self.assertEqual(server.PRESETS[row["preset"]]["method"], row["method"],
                             "%s launches %r but its preset runs %r"
                             % (row["key"], row["method"],
                                server.PRESETS[row["preset"]]["method"]))

    def test_E_res_003__the_shelf_has_no_worksheets_theories_or_glossary(self):
        self.assertEqual(page()["worksheets"], [])
        self.assertEqual(page()["theories"], [])
        self.assertEqual(page()["glossary"], [])

    def test_E_res_004__ten_records_with_eight_computed_and_two_unbuilt(self):
        self.assertEqual(catalogue_ids(), RECORDS)
        forms = {rid: row["form"] for rid, row in records().items()}
        self.assertEqual(sorted(rid for rid, form in forms.items() if form == "computed"),
                         ["QNT-STA-01", "QNT-STA-02", "QNT-STA-03", "QNT-STA-04",
                          "QNT-STA-05", "QNT-STA-06", "QNT-STA-07", "QNT-STA-09"])
        self.assertEqual(sorted(rid for rid, form in forms.items() if form == "read_only"),
                         ["QNT-STA-08", "QNT-STA-10"])

    def test_E_res_005__the_shelf_is_cross_cutting_and_says_it_does_not_prove_causality(self):
        self.assertTrue(page()["cross_cutting"])
        self.assertEqual(len(page()["start_steps"]), 4)
        self.assertTrue(any("does not prove causality" in line.lower()
                            for line in page()["does_not"]),
                        "the shelf's own promise about causality is missing")

    def test_E_res_006__four_tiles_whose_keys_are_the_tool_groups(self):
        tiles = {tile["key"]: tile for tile in page()["tiles"]}
        self.assertEqual(sorted(tiles), ["Check the design", "Compare groups",
                                         "Describe the data", "Relate variables"])
        groups = {row["group"] for row in tools()}
        self.assertEqual(groups, set(tiles), "a tool group has no tile, or a tile has no group")
        for row in tools():
            holders = [key for key, tile in tiles.items()
                       if row["key"] in [t["key"] for t in tile["tools"]]]
            self.assertEqual(len(holders), 1, "%s is in %d tiles" % (row["key"], len(holders)))

    def test_E_res_007__every_record_sits_in_one_tile_and_every_tile_names_a_need(self):
        placed = []
        for key, tile in {tile["key"]: tile for tile in page()["tiles"]}.items():
            placed.extend(row["id"] for row in tile["records"])
            self.assertTrue(tile["need"], "%s declares no need" % key)
            self.assertTrue(tile["tools"], "%s holds no calculator" % key)
            self.assertTrue(tile["what"], "%s declares no description" % key)
        self.assertEqual(sorted(placed), RECORDS, "a record is in no tile, or in two")

    def test_E_res_008__the_catalogue_row_agrees_with_the_detail_page(self):
        entry = next(row for row in subjects.catalogue()["subjects"] if row["id"] == SUBJECT)
        self.assertEqual(entry["tool_count"], len(tools()))
        self.assertEqual(entry["worksheet_count"], 0)
        self.assertEqual(entry["record_count"], 10)
        self.assertEqual(entry["theory_count"], 0)
        self.assertEqual(entry["catalogue_count"], 10)
        self.assertTrue(entry["cross_cutting"])

    def test_E_res_009__thirteen_tool_keys_are_not_library_ids(self):
        """D-RES-02, the trap: a probe that resolves `key` reports 13 false defects."""
        by_key = [row["key"] for row in tools() if row["key"] in LIBRARY]
        by_method = [row["method"] for row in tools() if row["method"] in LIBRARY]
        self.assertEqual(len(by_key), 8, "the count of keys that ARE library ids moved: %r" % by_key)
        self.assertEqual(len(by_method), 21, "a tool's method does not resolve: %r" % by_method)

    def test_E_res_010__the_page_declares_four_groups_and_leaves_the_null_levels_alone(self):
        """The page groups by `group` when every tool has one; the levels stay as they are.

        Nine tools declare no level.  That is not a defect to paper over with an invented
        level: with every tool grouped, the page groups by the four tiles, so a null level
        is never used to place a calculator.
        """
        self.assertEqual(len({row["group"] for row in tools()}), 4)
        self.assertEqual(sum(1 for row in tools() if row["group"]), 21)
        levels = [row["level"] for row in tools() if row["level"]]
        self.assertEqual(len(levels), 12, "the declared levels moved")
        self.assertEqual(sorted(set(levels)), ["advanced", "intermediate", "intro"])


class RefusalTest(unittest.TestCase):
    """E-res-047..050 -- a refusal names its reason, and the ceiling is kept."""

    def run_case(self, method, inputs):
        return Pipeline().run({"objective": "research refusal", "method": method,
                               "inputs": inputs}, lambda spec: True)

    def test_E_res_047__a_perfect_fit_is_refused_with_a_reason(self):
        delivery = self.run_case("trend_forecast", {"values": [1, 2, 3, 4, 5, 6, 7], "horizon": 2})
        self.assertNotEqual(delivery.status, "delivered")
        self.assertIn("perfect fit", (delivery.blocked_reason or "").lower(),
                      "the refusal does not say why: %r" % delivery.blocked_reason)

    def test_E_res_048__a_binary_float_is_refused_with_a_reason(self):
        delivery = self.run_case("multiple_comparison",
                                 {"p_values": [0.01, 0.04, 0.03], "method": "holm"})
        self.assertNotEqual(delivery.status, "delivered")
        self.assertIn("exact decimals", (delivery.blocked_reason or ""),
                      "the refusal does not explain the typing rule: %r" % delivery.blocked_reason)

    def test_E_res_049__a_group_with_too_few_observations_is_refused(self):
        delivery = self.run_case("welch_t", {"groups": {"a": [1, 2], "b": [3, 4, 5]}})
        self.assertNotEqual(delivery.status, "delivered",
                            "a group of two observations was compared without comment")
        self.assertTrue(delivery.blocked_reason, "the refusal carries no reason")

    def test_E_res_050__no_paper_asserts_causation_from_an_observational_design(self):
        """Every tool on this shelf is associational, descriptive or predictive.

        The shelf's own promise is "It does not prove causality from observational data", so
        the paper may describe a difference or an association, and must not say the data
        produces one.  A phrase is allowed only where the same sentence denies it, or where
        it is the standard technical term for an ANOVA effect.
        """
        causal = ("causes", "caused by", "leads to", "because of", "results in",
                  "gives rise to")
        technical = ("simple effect of", "main effect of", "interaction effect of",
                     "fixed effect of", "random effect of", "marginal effect of")
        negations = ("not", "no ", "cannot", "never", "without")
        offenders = []
        for tool in tools():
            method = LIBRARY[tool["method"]]
            self.assertNotEqual(method.claim_ceiling, "causal",
                                "%s claims a causal ceiling" % tool["method"])
            _delivery, _bundle, text = built(tool)
            body = text.split("Honesty: what was not done")[0]
            for sentence in re.split(r"(?<=[.!?])\s+", body):
                low = sentence.lower()
                hits = [phrase for phrase in causal if phrase in low]
                if "effect of" in low and not any(term in low for term in technical):
                    hits.append("effect of")
                if hits and not any(neg in low for neg in negations):
                    offenders.append((tool["key"], hits[0], sentence.strip()[:120]))
        self.assertEqual(offenders, [], "a paper asserts causation: %r" % (offenders,))


class TrapTest(unittest.TestCase):
    """E-res-051..053 -- the shelf-wide traps that make the other tests trustworthy."""

    def test_E_res_051__every_method_declares_its_own_precision_hook(self):
        hookless = sorted(key for key, method in LIBRARY.items()
                          if not callable(getattr(method, "typing", None)))
        self.assertEqual(hookless, [], "a method prints figures without declaring a precision")

    def test_E_res_052__the_probe_reports_no_disagreement_on_this_shelf(self):
        """The harness is a suspect until it has been pointed at a shelf we trust."""
        rows = probe.verify(SUBJECT)
        compared = sum(row[1] for row in rows)
        disagreements = sum(row[2] for row in rows)
        self.assertGreaterEqual(compared, 55,
                                "the kit compared only %d figures: the harness is not reading "
                                "the paper" % compared)
        self.assertEqual(disagreements, 0, "the engine disagrees with the independent arithmetic")
        self.assertEqual(probe.prove("operations"), [],
                         "the harness reports a problem on a shelf whose suite is green")

    def test_E_res_053__the_library_and_the_frozen_fixture_are_the_numbers_measured(self):
        import json
        fixture = json.load(open(os.path.join(ROOT, "tests", "fixtures", "frozen_contract.json"),
                                 encoding="utf-8"))
        self.assertEqual(len(LIBRARY), 211)
        self.assertEqual(len(server.PRESETS), 144)
        self.assertEqual(len(fixture["methods"]), 211)
        self.assertEqual(len(fixture["presets"]), 144)
        for method_id in {tool["method"] for tool in tools()}:
            self.assertIn(method_id, fixture["methods"],
                          "%s runs a method the frozen contract does not pin" % method_id)

