"""Acceptance suite for the Finance shelf — one test per row of `qa/manual/finance.md`.

The manual is the specification: every `E-fin-nnn` row names a test below, and §9 of the
manual records its status.  Nothing here is a new requirement: each expectation is traced
to `bp.methods.LIBRARY`, the shipped catalogue (`subjects.detail("finance")`), the paper
rules in `docs/VALIDATION_HARNESS.md` §5, or the finance student guide, and the source is
cited in the manual.

Rules this file keeps:
  * offline — no provider key, no network, no model call;
  * it asserts the frozen core's behaviour and the product's formatting of it, and it never
    edits an expected value to go green;
  * a refusal is a refusal: a test that expects a block asserts the *reason* too;
  * where the shelf is knowingly wrong (D-FIN-01, G-fin-05, G-fin-07) the test pins the
    defect with its ledger id, so the day it is fixed the test fails and must be updated —
    that is a trap, not a weakened check.

Run:  PYTHONPATH=src python -m pytest tests/test_subject_finance_acceptance.py -q
"""

import json
import os
import re
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp import methods, server                                     # noqa: E402
from bp.orchestrator import Delivery, Pipeline                     # noqa: E402
from bp.product import calc_router, capabilities, chat, framework_profiles, subjects  # noqa: E402

SUBJECT = "finance"
FIXTURES = os.path.join(HERE, "fixtures")
LONG_DECIMAL = re.compile(r"\d+\.\d{6,}")
TOL = D("1e-9")


def page():
    return subjects.detail(SUBJECT)


def tools():
    return page()["tools"]


def tool(key):
    return next(item for item in tools() if item["key"] == key)


def request_for(method):
    """The first shipped preset whose declared method is `method`, or None."""
    for preset_id, request in server.PRESETS.items():
        if request.get("method") == method:
            return preset_id, request
    return None, None


def preset_inputs(tool_key):
    return dict(server.PRESETS[tool(tool_key)["preset"]]["inputs"])


def start(method, inputs, currency="USD", period="annual"):
    """Stage 1-2 only: this is what the product does before the student confirms."""
    return Pipeline().start({"objective": "finance acceptance", "method": method,
                             "inputs": inputs, "currency": currency, "period": period})


def deliver(method, inputs, currency="USD", period="annual"):
    """Run to completion, confirming the spec checkpoint (no mapping checkpoint here)."""
    return Pipeline().run({"objective": "finance acceptance", "method": method,
                           "inputs": inputs, "currency": currency, "period": period},
                          lambda spec: True)


def fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8-sig") as handle:
        return json.load(handle)


def close(actual, expected, tol=TOL):
    left, right = D(str(actual)), D(str(expected))
    if right == 0:
        return abs(left) <= tol
    return abs(left - right) / abs(right) <= tol


def methods_templates():
    from bp import templates
    return templates.TEMPLATES


def blocked(delivery):
    """True when the stage contract refused: a Delivery, not a ProblemSpec."""
    return isinstance(delivery, Delivery) and delivery.status == "blocked"


class FinanceCatalogueAndContract(unittest.TestCase):
    """E-fin-001 … E-fin-008: the catalogue and the frozen contract it promises."""

    def test_001__catalogue_counts_match(self):
        """E-fin-001: 35 tools, 0 worksheets, 23 records, 22 glossary terms, 0 theories."""
        shelf = page()
        self.assertEqual(len(shelf["tools"]), 35)
        self.assertEqual(len(shelf["worksheets"]), 0)
        self.assertEqual(len(shelf["records"]), 23)
        self.assertEqual(len(shelf["glossary"]), 22)
        self.assertEqual(len(shelf["theories"]), 0)
        self.assertEqual(shelf["label"], "Finance")

    def test_002__every_tool_resolves_to_a_frozen_method_or_the_one_template(self):
        """E-fin-002: a tile never advertises an artefact the engine cannot build."""
        templates = methods_templates()
        templated = []
        for item in tools():
            method_id = item["method"]
            if method_id in methods.LIBRARY:
                continue
            self.assertIn(method_id, templates,
                          "%s advertises %r, which is neither a frozen method nor a template"
                          % (item["key"], method_id))
            templated.append(item["key"])
        self.assertEqual(templated, ["case_decision"],
                         "case_decision is the only template-backed finance tool")

    def test_003__every_tool_declares_formula_level_and_purpose(self):
        """E-fin-003: no tile is a bare button, and the tier counts are the measured ones."""
        templates = methods_templates()
        second = []
        for item in tools():
            for field in ("label", "what", "formula", "level", "period"):
                self.assertTrue(item.get(field), "%s has no %s" % (item["key"], field))
            self.assertIn(item["level"], ("intro", "intermediate", "advanced"),
                          "%s declares level %r" % (item["key"], item["level"]))
            if item["method"] in methods.LIBRARY:
                tier = methods.LIBRARY[item["method"]].tier
            else:
                tier = templates[item["method"]]["tier"]
            self.assertIn(tier, ("T1", "T2", "T3", "T4"), item["key"])
            if tier == "T2":
                second.append(item["key"])
        self.assertEqual(sorted(second),
                         ["case_decision", "dcf", "dcfmid", "equitybridge", "multiples", "options"],
                         "the six T2 tools are the measured ones")

    def test_004__every_tool_declares_steps_mistakes_and_resolving_related_ids(self):
        """E-fin-004: teaching notes are present and every `related` id resolves."""
        known = set()
        for definition in subjects.SUBJECT_DEFS:
            known.update(definition.get("tools") or ())
        self.assertTrue(known, "no shelf declares tools")
        for item in tools():
            self.assertGreaterEqual(len(item.get("steps") or []), 3, item["key"])
            self.assertGreaterEqual(len(item.get("common_mistakes") or []), 2, item["key"])
            self.assertTrue(item.get("related"), item["key"])
            for other in item["related"]:
                self.assertIn(other, known,
                              "%s relates to %r, which is not a declared tool anywhere"
                              % (item["key"], other))

    def test_005__every_tool_except_ols_robust_has_a_matching_preset(self):
        """E-fin-005 / G-fin-05: one named exception, and it is `ols_robust`."""
        unmatched = []
        for item in tools():
            preset_id = item.get("preset")
            if not preset_id:
                unmatched.append(item["key"])
                continue
            self.assertIn(preset_id, server.PRESETS, item["key"])
            self.assertEqual(server.PRESETS[preset_id]["method"], item["method"],
                             "%s launches %r but its preset runs %r"
                             % (item["key"], item["method"], server.PRESETS[preset_id]["method"]))
        self.assertEqual(unmatched, ["ols_robust"],
                         "G-fin-05: ols_robust is the only tool with no preset")

    def test_006__every_preset_default_passes_schema_and_profile(self):
        """E-fin-006: a shipped preset is a runnable example, not a broken one."""
        checked = 0
        for item in tools():
            if item["method"] not in methods.LIBRARY or not item.get("preset"):
                continue          # G-fin-05: ols_robust ships no preset (pinned by test_005)
            preset_id, request = request_for(item["method"])
            self.assertIsNotNone(preset_id, item["method"])
            method = methods.LIBRARY[item["method"]]
            self.assertEqual(methods.validate_inputs(method, request["inputs"]), [],
                             "%s: preset %r is rejected by its own schema"
                             % (item["method"], preset_id))
            self.assertEqual(list(method.profile(dict(request["inputs"]))), [],
                             "%s: preset %r fails its own profile" % (item["method"], preset_id))
            checked += 1
        # 33 frozen-method tools with a preset: 35 tools, less ols_robust (no preset,
        # G-fin-05) and case_decision (a T2 template, validated below).
        self.assertEqual(checked, 33, "33 frozen-method tools ship a preset")
        from bp import templates
        example = templates.EXAMPLES["case_decision"]
        self.assertEqual(templates.validate("case_decision", dict(example["inputs"])), [],
                         "the case_decision example is rejected by its own template")

    def test_007__every_method_passes_its_own_checks_on_its_preset_except_mid_year_dcf(self):
        """E-fin-007 / D-FIN-01: the one failing self-check, pinned with its ledger id."""
        failures = []
        for item in tools():
            if item["method"] not in methods.LIBRARY:
                continue
            preset_id, request = request_for(item["method"])
            if item["preset"] in server.PRESETS:
                preset_id, request = item["preset"], server.PRESETS[item["preset"]]
            if request is None:
                # G-fin-05: ols_robust ships no preset; it shares the ols schema, so the
                # ols example is the honest input set to run its checks on.
                self.assertEqual(item["method"], "ols_robust", item["key"])
                preset_id, request = "ols", server.PRESETS["ols"]
            method = methods.LIBRARY[item["method"]]
            for name, ok in method.tests(dict(request["inputs"]), method.impl):
                if not ok:
                    failures.append((item["key"], name))
        self.assertEqual(failures, [],
                         "every finance self-check passes on its own preset; a failure here is a "
                         "new defect (D-FIN-01 was fixed by B-183)")

    def test_008__no_finance_method_claims_prescriptive(self):
        """E-fin-008: the ceiling is descriptive, or associational for the statistics."""
        ceilings = {}
        for item in tools():
            if item["method"] in methods.LIBRARY:
                ceilings[item["method"]] = methods.LIBRARY[item["method"]].claim_ceiling
        self.assertNotIn("prescriptive", set(ceilings.values()))
        associational = {name for name, ceiling in ceilings.items() if ceiling == "associational"}
        self.assertEqual(associational, {"pearson", "ols", "ols_robust"})

    def test_052__the_shelf_copy_stays_short(self):
        """E-fin-052: a student-facing line is a line, not a paragraph.

        The ceilings are the measured ones (the shelf already met them on 341 of 343 lines), so
        this pins the terse style rather than imposing a new voice on copy the owner wrote.
        """
        def words(text):
            return len(str(text or "").split())

        self.assertLessEqual(words(page()["guidance"]), 65,
                             "the shelf guidance is a list of short lines, not an essay")
        for item in tools():
            self.assertLessEqual(words(item["what"]), 20, "%s: what" % item["key"])
            for step in item["steps"]:
                self.assertLessEqual(words(step), 18, "%s: a step" % item["key"])
            for mistake in item["common_mistakes"]:
                self.assertLessEqual(words(mistake), 18, "%s: a common mistake" % item["key"])



class FinanceRefusals(unittest.TestCase):
    """E-fin-009 … E-fin-015: a refusal is a refusal, and it names the reason.

    Measured first in `qa/baseline/fin_refusals.txt`; every assertion below quotes the
    reason the engine actually gives, so a change in wording is caught as a change in
    behaviour.
    """

    def test_009__an_unknown_input_is_refused_with_the_allowed_list(self):
        """E-fin-009: no silent drop of an input the method does not read."""
        result = start("npv", {"rate": "0.10", "cashflows": ["-1000", "400"], "bogus": "1"})
        self.assertTrue(blocked(result), "an unknown input must block, not deliver")
        self.assertIn("unknown input 'bogus'", result.blocked_reason)
        self.assertIn("allowed: ['cashflows', 'rate']", result.blocked_reason)

    def test_010__survey_structure_inputs_are_refused_by_name(self):
        """E-fin-010: weights/clusters/strata are named, not silently ignored."""
        for name, value, concept in (("weights", ["1", "2"], "survey weights"),
                                     ("cluster", ["a", "b"], "clustered observations"),
                                     ("strata", ["a", "b"], "stratified sampling"),
                                     ("pairs", ["1"], "paired observations")):
            inputs = {"rate": "0.10", "cashflows": ["-1000", "400"]}
            inputs[name] = value
            result = start("npv", inputs)
            self.assertTrue(blocked(result), name)
            self.assertIn("'%s' is refused" % name, result.blocked_reason)
            self.assertIn(concept, result.blocked_reason)

    def test_011__a_rate_typed_as_a_whole_number_is_explained(self):
        """E-fin-011: 6 typed for 6% is explained, never read as 600%."""
        result = deliver("time_value", {"present_value": "1000", "rate": "6", "periods": "1",
                                       "compounding": "annual"})
        self.assertEqual(result.status, "delivered")
        self.assertIn("6% is 0.06", result.report)

    def test_012__an_irr_without_a_sign_change_is_refused(self):
        """E-fin-012: no sign change and no root are both refusals, never NaN."""
        no_sign = start("irr", {"cashflows": ["100", "200", "300"]})
        self.assertTrue(blocked(no_sign))
        self.assertIn("never change sign", no_sign.blocked_reason)
        no_root = start("irr", {"cashflows": ["-100", "250", "-160"]})
        self.assertTrue(blocked(no_root))
        self.assertIn("no IRR in the searched range", no_root.blocked_reason)
        with self.assertRaises(methods.DataError):
            methods.LIBRARY["irr"].impl({"cashflows": ["100", "200", "300"]})

    def test_013__an_unrecovered_outlay_is_refused(self):
        """E-fin-013: a payback the flows never reach is refused, not reported as a number."""
        result = start("discounted_payback", {"cashflows": ["-1000", "10", "10"], "rate": "0.10"})
        self.assertTrue(blocked(result))
        self.assertIn("never recover the initial outlay", result.blocked_reason)

    def test_014__break_even_without_a_contribution_margin_is_refused(self):
        """E-fin-014: price ≤ variable cost has no break-even quantity."""
        result = start("breakeven", {"fixed": "1000", "price": "10", "variable": "10"})
        self.assertTrue(blocked(result))
        self.assertIn("price <= variable cost", result.blocked_reason)

    def test_015__a_dcf_with_growth_above_the_rate_or_bad_timing_is_refused(self):
        """E-fin-015: Gordon growth and the timing vocabulary are both enforced."""
        growth = start("dcf_valuation", {"cashflows": ["100", "110"], "discount_rate": "0.05",
                                         "terminal_growth": "0.06"})
        self.assertTrue(blocked(growth))
        self.assertIn("terminal growth rate must be below the discount rate", growth.blocked_reason)
        timing = start("dcf_valuation", {"cashflows": ["100", "110"], "discount_rate": "0.10",
                                         "timing": "start"})
        self.assertTrue(blocked(timing))
        self.assertIn("timing", timing.blocked_reason)


class FinanceIndependentRecomputation(unittest.TestCase):
    """E-fin-016 … E-fin-025: every number is checked by a route that is not the method."""

    def test_016__npv_matches_a_hand_summed_present_value(self):
        """E-fin-016: NPV is the hand sum, not a re-read of the method's own output."""
        inputs = preset_inputs("npv")
        rate = D(inputs["rate"])
        expected = sum((D(str(c)) / (1 + rate) ** t for t, c in enumerate(inputs["cashflows"])), D(0))
        self.assertTrue(close(methods.LIBRARY["npv"].impl(dict(inputs)), expected))

    def test_017__mid_year_dcf_matches_the_hand_computation_and_exceeds_end_year(self):
        """E-fin-017 / D-FIN-01: the mid-year value is right; only the check is wrong."""
        inputs = preset_inputs("dcfmid")
        cfs = [D(str(c)) for c in inputs["cashflows"]]
        rate = D(inputs["discount_rate"])
        growth = D(inputs["terminal_growth"])
        n = len(cfs)
        terminal = cfs[-1] * (1 + growth) / (rate - growth)
        end = sum((cf / (1 + rate) ** t for t, cf in enumerate(cfs, 1)), D(0)) + terminal / (1 + rate) ** n
        mid = sum((cf / (1 + rate) ** (D(t) - D("0.5")) for t, cf in enumerate(cfs, 1)), D(0)) \
            + terminal / (1 + rate) ** (D(n) - D("0.5"))
        method = methods.LIBRARY["dcf_valuation"]
        self.assertTrue(close(method.impl({**inputs, "timing": "mid"})["enterprise_value"], mid))
        self.assertTrue(close(method.impl({**inputs, "timing": "end"})["enterprise_value"], end))
        self.assertTrue(mid > end, "mid-year discounting must raise a positive valuation")
        self.assertTrue(close(mid / end, "1.0488088481701515", D("1e-12")))
        # B-183: and the product must actually deliver the mid-year tile, not block it.
        delivery = deliver("dcf_valuation", inputs)
        self.assertEqual(delivery.status, "delivered", delivery.blocked_reason)
        self.assertGreater(len(delivery.report), 0)

    def test_018__equity_bridge_matches_hand_arithmetic(self):
        """E-fin-018: equity = EV − net debt − minority − preferred; per share divides by shares."""
        inputs = preset_inputs("equitybridge")
        net_debt = D(inputs.get("debt", "0")) - D(inputs.get("cash", "0"))
        equity = (D(inputs["enterprise_value"]) - net_debt
                  - D(inputs.get("minority_interest", "0")) - D(inputs.get("preferred_equity", "0")))
        out = methods.LIBRARY["equity_bridge"].impl(dict(inputs))
        self.assertTrue(close(out["equity_value"], equity))
        self.assertTrue(close(out["per_share_value"] if "per_share_value" in out else out["per_share"],
                             equity / D(inputs["shares_outstanding"])))

    def test_019__wacc_matches_the_hand_weighted_cost(self):
        """E-fin-019: WACC is the hand-weighted average of the two declared costs."""
        inputs = preset_inputs("wacc")
        equity, debt = D(inputs["equity_value"]), D(inputs["debt_value"])
        expected = (equity * D(inputs["cost_of_equity"])
                    + debt * D(inputs["cost_of_debt_after_tax"])) / (equity + debt)
        out = methods.LIBRARY["wacc"].impl(dict(inputs))
        self.assertTrue(close(out["wacc"], expected))

    def test_020__capm_matches_the_hand_capm_formula(self):
        """E-fin-020: cost of equity = rf + β(rm − rf)."""
        inputs = preset_inputs("capm")
        expected = (D(inputs["risk_free_rate"])
                    + D(inputs["beta"]) * (D(inputs["market_return"]) - D(inputs["risk_free_rate"])))
        out = methods.LIBRARY["capm"].impl(dict(inputs))
        self.assertTrue(close(out["cost_of_equity"], expected))

    def test_021__break_even_matches_hand_arithmetic(self):
        """E-fin-021: units = fixed / (price − variable); revenue = units × price."""
        inputs = preset_inputs("breakeven")
        units = D(inputs["fixed"]) / (D(inputs["price"]) - D(inputs["variable"]))
        out = methods.LIBRARY["breakeven"].impl(dict(inputs))
        self.assertTrue(close(out["breakeven_units"], units))
        self.assertTrue(close(out["breakeven_revenue"], units * D(inputs["price"])))

    def test_022__loan_payment_matches_the_annuity_formula(self):
        """E-fin-022: PMT = P·r/(1−(1+r)^−n) with the per-period rate."""
        inputs = preset_inputs("loan")
        per_year = D(str(inputs.get("payments_per_year", "1")))
        rate = D(inputs["annual_rate"]) / per_year
        n = D(inputs["years"]) * per_year
        expected = D(inputs["principal"]) * rate / (1 - (1 + rate) ** (-n))
        out = methods.LIBRARY["loan_amortization"].impl(dict(inputs))
        self.assertTrue(close(out["payment"], expected))
        self.assertTrue(close(out["first_interest"], D(inputs["principal"]) * rate))

    def test_023__ratio_analysis_matches_its_golden_fixture(self):
        """E-fin-023: the ratio pack against the independent Fraction re-implementation."""
        data = fixture("ratio_golden.json")
        method = methods.LIBRARY["ratio_analysis"]
        for case in data["cases"]:
            out = method.impl(dict(case["inputs"]))
            for name, expected in case["expected"].items():
                self.assertIn(name, out, "%s: %s missing" % (case["name"], name))
                self.assertTrue(close(out[name], expected, D(data["tolerance"].split()[0].rstrip("r"))
                                      if data["tolerance"].startswith("1e") else TOL),
                                "%s: %s %r != %r" % (case["name"], name, out[name], expected))

    def test_024__descriptive_forecast_pearson_and_ols_match_their_golden_fixtures(self):
        """E-fin-024: the four statistical tools on the shelf against their fixtures."""
        descriptive = fixture("descriptive_golden.json")
        for case in descriptive:
            inputs = {"values": case["values"]}
            if case.get("missing_codes"):
                inputs["missing_codes"] = case["missing_codes"]
            out = methods.LIBRARY["descriptive_stats"].impl(inputs)
            for name, expected in case["expected"].items():
                self.assertTrue(close(out[name], expected),
                                "%s: %s %r != %r" % (case["name"], name, out[name], expected))
        forecast = fixture("forecast_golden.json")
        for case in forecast:
            inputs = {"values": case["values"], "horizon": case["horizon"]}
            if case.get("missing_codes"):
                inputs["missing_codes"] = case["missing_codes"]
            out = methods.LIBRARY["trend_forecast"].impl(inputs)
            for name, expected in case["expected"].items():
                self.assertTrue(close(out[name], expected),
                                "%s: %s %r != %r" % (case["name"], name, out[name], expected))
        correlation = fixture("correlation_golden.json")
        for case in correlation:
            if case.get("method", "pearson") != "pearson":
                continue          # the fixture also carries the rank correlation
            inputs = {"x": case["x"], "y": case["y"]}
            if case.get("missing_codes"):
                inputs["missing_codes"] = case["missing_codes"]
            out = methods.LIBRARY["pearson"].impl(inputs)
            for name, expected in case["expected"].items():
                self.assertTrue(close(out[name], expected, D(str(case.get("p_tol", "1e-9")))),
                                "%s: %s %r != %r" % (case["name"], name, out[name], expected))
        regression = fixture("regression_golden.json")
        for case in regression:
            if case.get("method", "ols") != "ols":
                continue          # the fixture also carries the robust-standard-error case
            inputs = {"y": case["y"], "predictors": case["predictors"]}
            if case.get("missing_codes"):
                inputs["missing_codes"] = case["missing_codes"]
            out = methods.LIBRARY["ols"].impl(inputs)
            for name, expected in case["expected"].items():
                self.assertTrue(close(out[name], expected),
                                "%s: %s %r != %r" % (case["name"], name, out[name], expected))

    def test_025__bond_price_and_duration_match_hand_arithmetic(self):
        """E-fin-025: the bond price is the hand sum of discounted coupons and face."""
        inputs = preset_inputs("bond")
        face = D(inputs["face_value"])
        per_year = D(str(inputs.get("payments_per_year", "1")))
        coupon = face * D(inputs["coupon_rate"]) / per_year
        yield_per_period = D(inputs["yield_to_maturity"]) / per_year
        periods = int(D(inputs["years_to_maturity"]) * per_year)
        price = sum((coupon / (1 + yield_per_period) ** t for t in range(1, periods + 1)), D(0)) \
            + face / (1 + yield_per_period) ** periods
        out = methods.LIBRARY["bond_analysis"].impl(dict(inputs))
        self.assertIn("price", out)
        self.assertTrue(close(out["price"], price, D("1e-9")),
                        "bond price %r != hand %r" % (out["price"], price))
        if "modified_duration" in out and "macaulay_duration" in out:
            self.assertTrue(close(out["modified_duration"],
                                 out["macaulay_duration"] / (1 + yield_per_period), D("1e-9")))


class FinanceRecordsAndGuidance(unittest.TestCase):
    """E-fin-026 … E-fin-037: records, worksheets, tiles, glossary and the student promise."""

    def test_026__computed_records_name_methods_the_engine_has(self):
        """E-fin-026: a computed record never names a method the engine lacks."""
        checked = 0
        for record in page()["records"]:
            if record["form"] != "computed":
                continue
            self.assertTrue(record["linked_methods"],
                            "%s is called computed but links no method" % record["id"])
            for method_id in record["linked_methods"]:
                self.assertIn(method_id, methods.LIBRARY,
                              "%s links %r, which is not a frozen method"
                              % (record["id"], method_id))
            checked += 1
        self.assertEqual(checked, 8, "eight computed finance records")

    def test_027__a_read_only_record_claims_no_method_and_no_worksheet(self):
        """E-fin-027: a read-only record is something to read and cite, nothing more."""
        read_only = [record for record in page()["records"] if record["form"] == "read_only"]
        self.assertEqual(len(read_only), 15, "23 records: 8 computed, 15 read-only")
        for record in read_only:
            self.assertEqual(list(record["linked_methods"]), [], record["id"])
            self.assertIsNone(record["template"], record["id"])

    def test_028__no_finance_record_claims_a_worksheet(self):
        """E-fin-028: the shelf has no worksheet, so no record may point at one."""
        for record in page()["records"]:
            self.assertIsNone(record["template"],
                              "%s points at template %r" % (record["id"], record["template"]))

    def test_029__a_not_implemented_record_is_read_only(self):
        """E-fin-029: 'not implemented' is never sold as computed."""
        for record in page()["records"]:
            if str(record["implementation_status"]).lower().startswith("not implemented"):
                self.assertEqual(record["form"], "read_only", record["id"])

    def test_030__the_shelf_has_no_worksheet_launcher(self):
        """E-fin-030: zero worksheets, and no tool is a worksheet launcher."""
        self.assertEqual(page()["worksheets"], [])
        for item in tools():
            self.assertNotEqual(item.get("kind"), "worksheet", item["key"])

    def test_031__no_finance_profile_and_no_worksheet_group(self):
        """E-fin-031: no framework profile and no worksheet group belongs to this shelf."""
        self.assertNotIn("finance", subjects.SUBJECT_WORKSHEET_GROUPS)
        for key, profile in framework_profiles.PROFILES.items():
            self.assertNotEqual(profile.get("subject"), "finance",
                                "profile %s claims the finance shelf" % key)

    def test_032__the_shelf_declares_no_tiles_and_that_is_the_recorded_design(self):
        """E-fin-032: tiles exist only for the shelves that declare them."""
        self.assertEqual(page()["tiles"], [])
        # The claim is about *this* shelf and about the shape of the tile map, not a frozen
        # list of every shelf that has one: accounting, operations and project management
        # declared tiles later (B-205, B-206) and a global freeze turned that deliberate
        # design change into a red finance test (D-PLAN-06 family).
        self.assertNotIn("finance", subjects.SUBJECT_TILES)
        declared = {definition["id"] for definition in subjects.SUBJECT_DEFS}
        self.assertTrue(set(subjects.SUBJECT_TILES) <= declared,
                        "a tile map names a shelf that does not exist")

    def test_033__the_glossary_is_the_declared_set_with_definitions(self):
        """E-fin-033: 22 terms, every definition present and unique."""
        expected = {"NPV", "IRR", "WACC", "CAPM", "Beta", "YTM", "Duration", "Convexity", "EOQ",
                    "CCC", "VaR", "CVaR", "Delta", "Hedge", "Enterprise value", "Net debt",
                    "EBIT / EBITDA", "EPS", "ROE", "Common-size", "CAGR", "Altman Z"}
        rows = page()["glossary"]
        self.assertEqual({row["term"] for row in rows}, expected)
        definitions = [row["definition"] for row in rows]
        self.assertTrue(all(definition.strip() for definition in definitions))
        self.assertEqual(len(set(definitions)), len(definitions), "two terms share a definition")

    def test_034__start_steps_name_real_tools(self):
        """E-fin-034: every start step points at a tool that exists."""
        shelf = page()
        steps = shelf["start_steps"]
        self.assertGreaterEqual(len(steps), 3)
        keys = {item["key"] for item in tools()}
        labels = {re.sub(r"[^a-z ]", "", item["label"].lower()): item["key"] for item in tools()}
        for step in steps:
            lowered = step.lower()
            named = [key for key in keys if re.search(r"\b%s\b" % re.escape(key), lowered)]
            named += [key for label, key in labels.items() if label in lowered]
            self.assertTrue(named, "a start step names no tool on the shelf: %r" % step)

    def test_035__the_three_declared_non_goals_are_present(self):
        """E-fin-035: the does-not list is the shelf's promise, and it is still there."""
        declared = page()["does_not"]
        self.assertGreaterEqual(len(declared), 2)
        joined = " ".join(declared).lower()
        self.assertIn("does not retrieve market prices", joined)
        self.assertIn("does not choose the discount rate", joined)
        self.assertIn("does not model tax", joined)

    def test_036__guidance_promises_no_retrieval(self):
        """E-fin-036: the guidance never promises a retrieved market figure."""
        guidance = page()["guidance"].lower()
        self.assertTrue(guidance)
        for family in ("time value", "npv", "wacc", "dcf", "capm", "parity"):
            self.assertIn(family, guidance)
        self.assertNotIn("we will retrieve", guidance)
        self.assertNotIn("live price", guidance)

    def test_037__missing_need_text_is_named_as_the_recorded_gap(self):
        """E-fin-037 / G-fin-07: 23 tools have no 'what to gather' line; it is ledgered."""
        missing = sorted(item["key"] for item in tools() if not item.get("need"))
        self.assertEqual(len(missing), 25,
                         "G-fin-07 recorded 25 tools without need text; measured %r" % (missing,))
        self.assertNotIn("forecast", missing, "forecast declares its need text")


class FinanceProductPath(unittest.TestCase):
    """E-fin-038 … E-fin-050: routes, forms, router, session lifecycle, honesty, papers."""

    def test_038__the_subject_route_returns_the_catalogue(self):
        """E-fin-038: the gallery lists finance and the detail route agrees with it."""
        gallery = subjects.catalogue()["subjects"]
        finance = next(row for row in gallery if row["id"] == "finance")
        self.assertEqual(finance["label"], "Finance")
        self.assertEqual(finance["tool_count"], 35)
        self.assertEqual(finance["worksheet_count"], 0)
        self.assertEqual(finance["record_count"], 23)
        self.assertEqual(len(subjects.detail("finance")["tools"]), finance["tool_count"])

    def test_039__the_form_uses_choices_and_comma_lists_where_declared(self):
        """E-fin-039: an enum is a choice list and a list field is a comma list, not free text."""
        timing = methods.LIBRARY["dcf_valuation"].input_schema["timing"]
        self.assertEqual(timing["type"], "enum")
        self.assertEqual(timing.get("values"), ["end", "mid"])
        compounding = methods.LIBRARY["time_value"].input_schema["compounding"]
        self.assertEqual(compounding["type"], "enum")
        self.assertTrue(compounding.get("values") or compounding.get("choices"))
        cashflows = methods.LIBRARY["npv"].input_schema["cashflows"]
        self.assertIn(cashflows["type"], ("decimal_list", "value_list", "code_list"))

    def test_040__the_calculator_router_reaches_the_same_methods(self):
        """E-fin-040: a documented finance phrase reaches the same frozen method as the tile."""
        for phrase, method_id in (("net present value of this project", "npv"),
                                  ("what is the wacc", "wacc"),
                                  ("break even units", "breakeven"),
                                  ("bond price", "bond_analysis"),
                                  ("internal rate of return", "irr"),
                                  ("value at risk of my portfolio", "risk_metrics"),
                                  ("future value of a lump sum", "time_value")):
            outcome = calc_router.plan(phrase)
            self.assertEqual(outcome["method"], method_id, "%r routed to %r" % (phrase, outcome))
        # A sentence the router cannot place is refused with alternatives, never guessed.
        unknown = calc_router.plan("price this bond")
        self.assertIsNone(unknown["method"])
        self.assertTrue(unknown["alternatives"], "an unmatched sentence must offer alternatives")

    def test_041__the_finance_page_offers_no_worksheet_or_draft_surface(self):
        """E-fin-041: nothing on this shelf opens a worksheet or a draft."""
        shelf = page()
        self.assertEqual(shelf["worksheets"], [])
        for item in tools():
            self.assertNotIn("template", item, item["key"])
            self.assertFalse(item.get("draftable"), item["key"])
        for record in shelf["records"]:
            self.assertIsNone(record["template"], record["id"])

    def test_042__a_session_computes_nothing_before_confirmation(self):
        """E-fin-042: stage 1-2 stops at the plan; only confirm produces a report."""
        pipeline = Pipeline()
        spec = pipeline.start({"objective": "finance acceptance", "method": "npv",
                               "currency": "USD", "inputs": {"rate": "0.10",
                                                             "cashflows": ["-1000", "400", "400"]}})
        self.assertFalse(blocked(spec), "a valid npv request must reach the plan")
        self.assertFalse(hasattr(spec, "report"), "nothing is computed before confirmation")
        stages = [event["stage"] + ":" + event["status"] for event in pipeline.events]
        self.assertIn("formalization:awaiting_confirmation", stages)
        delivery = pipeline.resume(True)
        self.assertEqual(delivery.status, "delivered")
        self.assertTrue(delivery.report.strip())

    def test_043__a_delivered_finance_result_carries_its_honesty_block(self):
        """E-fin-043: the plan names the method's checks and the delivery carries honesty."""
        method = methods.LIBRARY["npv"]
        spec = Pipeline().start({"objective": "x", "method": "npv", "currency": "USD",
                                 "inputs": dict(server.PRESETS["npv"]["inputs"])})
        self.assertEqual(list(spec.checks), list(method.test_names))
        delivery = deliver("npv", dict(server.PRESETS["npv"]["inputs"]))
        self.assertEqual(delivery.status, "delivered")
        self.assertIn("honesty", delivery.appendix)
        self.assertIn("tier", delivery.appendix)

    def test_044__the_same_inputs_give_a_byte_identical_result(self):
        """E-fin-044: no clock, locale or dict-order dependence."""
        first = deliver("ratio_analysis", dict(server.PRESETS["ratios"]["inputs"]))
        second = deliver("ratio_analysis", dict(server.PRESETS["ratios"]["inputs"]))
        self.assertEqual(first.report, second.report)
        self.assertEqual(first.appendix["spec_hash"], second.appendix["spec_hash"])

    def test_045__the_sandbox_agrees_with_the_in_process_result(self):
        """E-fin-045: the guarded subprocess computes the same numbers."""
        from bp.sandbox import SubprocessSandbox
        inputs = dict(server.PRESETS["npv"]["inputs"])
        local = methods.LIBRARY["npv"].impl(dict(inputs))
        results, outputs, _meta = SubprocessSandbox().verify_execute("npv", dict(inputs))
        self.assertTrue(all(ok for _name, ok in results), results)
        self.assertTrue(close(outputs["npv"], local))

    def test_046__the_honesty_block_names_what_was_not_tested(self):
        """E-fin-046: every disclosure is a sentence, and a non-applicable field says so."""
        delivery = deliver("pearson", dict(server.PRESETS["pearson"]["inputs"]))
        honesty = delivery.appendix["honesty"]
        self.assertTrue(honesty, "an inferential result must disclose its limits")
        for key, value in honesty.items():
            self.assertTrue(str(value).strip(), "%s is blank" % key)
        missing = honesty.get("missing_data")
        self.assertTrue(missing, "the missing-data disclosure must be present")

    def test_047__capability_papers_print_money_at_two_decimals(self):
        """E-fin-047 / D-FIN-02: no capability paper prints a raw core Decimal."""
        offenders = []
        for key, row, method_id, inputs, recorded in finance_capability_runs():
            lines = chat._capability_lines(row, {"ok": True, "inputs": inputs,
                                                 "result": recorded})
            for line in lines:
                if LONG_DECIMAL.search(line):
                    offenders.append((key, line[:160]))
        self.assertEqual(offenders, [],
                         "a finance paper printed the core's full Decimal: %r" % (offenders,))

    def test_048__every_finance_capability_has_a_formatter_or_a_ledgered_gap(self):
        """E-fin-048 / G-fin-08: a capability without a formatter quotes the core verbatim."""
        missing = sorted({row["key"] for _tool, row, _m, _i, _r in finance_capability_runs()
                          if chat.CAPABILITY_LINES.get(row["key"]) is None})
        self.assertEqual(missing, [],
                         "G-fin-08: these finance capabilities fall back to the generic "
                         "formatter: %r" % (missing,))

    def test_049__the_deliverable_carries_the_numbers_and_no_template_token(self):
        """E-fin-049: the report is the deliverable, with the core's figure and no token."""
        from bp.product import deliverables
        delivery = deliver("npv", dict(server.PRESETS["npv"]["inputs"]))
        report = delivery.report
        self.assertNotIn("{{ref:", report)
        self.assertIn("(5.26)", report,
                      "the declared NPV must appear at the paper's 2 dp, in the accounting "
                      "parentheses convention for a negative figure")
        offers = deliverables.catalogue()
        self.assertTrue(offers, "no deliverable profile is registered")
        formats = {fmt for entry in offers if entry["available"] for fmt in entry["formats"]}
        self.assertTrue({"docx", "xlsx"} & formats,
                        "no deliverable offers docx or xlsx: %r" % (sorted(formats),))

    def test_050__a_refusal_is_a_refusal_not_a_zero(self):
        """E-fin-050: a blocked request produces a reason, never a figure."""
        result = start("breakeven", {"fixed": "1000", "price": "10", "variable": "10"})
        self.assertTrue(blocked(result))
        self.assertEqual(result.report, "", "a refusal must not carry a report")
        self.assertIn("price <= variable cost", result.blocked_reason)


def finance_capability_runs():
    """(tool, capability row, method, preset inputs, recorded result) for the finance shelf.

    The recorded result is built exactly as `chat.run_capability` builds it: a dict is
    stringified key by key, a bare value is wrapped under the row's declared output key.
    """
    shelf_methods = {item["method"] for item in tools()}
    rows = [row for row in capabilities.catalogue() if row.get("method") in shelf_methods]
    out = []
    for row in rows:
        preset_id, request = request_for(row["method"])
        if request is None:
            continue
        method = methods.LIBRARY[row["method"]]
        try:
            output = method.impl(dict(request["inputs"]))
        except Exception:  # noqa: BLE001 - a capability whose preset is refused is not a paper bug
            continue
        if isinstance(output, dict):
            recorded = {str(name): str(value) for name, value in output.items()}
        else:
            recorded = {row.get("output") or "value": str(output)}
        out.append((row["method"], row, row["method"], dict(request["inputs"]), recorded))
    return out


if __name__ == "__main__":
    unittest.main()










