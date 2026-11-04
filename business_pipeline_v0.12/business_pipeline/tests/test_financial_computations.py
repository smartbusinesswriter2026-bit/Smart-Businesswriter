"""The financial-computations engine: 128 specs, honest gaps, and the global-product rule.

The engine was built in one pass and had no test module at all, so every claim about
it was a claim about the source rather than about its behaviour.  These tests are the
contract, and each one is a behaviour that was wrong before:

* a spec whose producer is registered after it used to record a gap for a value the
  engine had computed;
* a value produced in one section never reached a spec in another, so seventy-two
  specs reported a gap for something already known;
* eight input patterns captured a word instead of the number, so the figure was
  silently dropped;
* one spec was labelled "Peso/Dollar Change", which is a home-currency name in a
  product that must stay global.
"""

import os
import re
import sys
import unittest
from decimal import Decimal as D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import financial_computations as fc  # noqa: E402


class RegistryTest(unittest.TestCase):
    """The catalogue: 128 specs, eleven sections, nothing anonymous."""

    def test_the_engine_carries_128_specs_in_11_sections(self):
        specs = fc.REGISTRY.all()
        self.assertEqual(len(specs), 128)
        counts = {}
        for spec in specs:
            counts[spec.section] = counts.get(spec.section, 0) + 1
        self.assertEqual(counts, {"A": 18, "B": 16, "C": 28, "D": 13, "E": 6,
                                  "F": 5, "G": 10, "H": 7, "I": 9, "J": 10, "K": 6})

    def test_every_spec_declares_its_inputs_a_formula_and_an_output(self):
        for spec in fc.REGISTRY.all():
            self.assertTrue(spec.inputs, "%s declares no inputs" % spec.id)
            self.assertTrue(spec.formula, "%s declares no formula" % spec.id)
            self.assertTrue(spec.output_name, "%s declares no output" % spec.id)
            self.assertTrue(spec.description, "%s declares no description" % spec.id)
            self.assertTrue(spec.label, "%s declares no label" % spec.id)

    def test_no_two_specs_share_an_output_name(self):
        names = [spec.output_name for spec in fc.REGISTRY.all()]
        self.assertEqual(len(names), len(set(names)))

    def test_every_dependency_names_a_real_spec_or_a_declared_input(self):
        ids = {spec.id for spec in fc.REGISTRY.all()}
        outputs = {spec.output_name for spec in fc.REGISTRY.all()}
        for spec in fc.REGISTRY.all():
            for dep in spec.depends_on:
                self.assertTrue(dep in ids or dep in outputs or dep in fc.COMMON_PATTERNS,
                                "%s depends on %s, which nothing supplies" % (spec.id, dep))


class OrderingTest(unittest.TestCase):
    """A producer is computed before its consumer, in a section or across sections."""

    def test_a_producer_registered_after_its_consumer_still_computes(self):
        raw = {"direct_materials_beg": D("10000"), "purchases": D("50000"), "freight_in": D("2000"),
               "direct_materials_end": D("8000"), "direct_labor": D("20000"),
               "factory_overhead": D("10000"), "beg_wip": D("5000"), "end_wip": D("7000")}
        pack = fc.compute_section("A", raw)
        used = pack.results["direct_materials_used"]
        self.assertTrue(used.ok, used.gap)
        self.assertEqual(used.value, D("54000"))
        # cogs_manufactured is registered *before* the spec that produces its
        # first input; before the fix it recorded a gap here.
        cogs = pack.results["cogs_manufactured"]
        self.assertTrue(cogs.ok, cogs.gap)
        self.assertEqual(cogs.value, D("82000"))

    def test_a_value_produced_in_one_section_reaches_the_next(self):
        raw = {"gross_sales": D("200000"), "sales_returns": D("0"), "sales_discounts": D("0"),
               "sales_allowances": D("0"), "item_value": D("50000")}
        packs = fc.compute_all_sections("compute the common size income statement", raw, ["A", "E"])
        self.assertTrue(packs["A"].results["net_sales"].ok)
        common = packs["E"].results["common_size_income_statement"]
        self.assertTrue(common.ok, common.gap)
        self.assertEqual(common.value, D("25"))

    def test_the_sections_are_computed_in_dependency_order(self):
        order = fc._section_order(["E", "A"])
        self.assertLess(order.index("A"), order.index("E"))


class GapTest(unittest.TestCase):
    """A missing input is named. It is never filled."""

    def test_a_declared_input_computes(self):
        pack = fc.compute_section("F", {"current_assets": D("50000"),
                                        "current_liabilities": D("20000")})
        ratio = pack.results["current_ratio"]
        self.assertTrue(ratio.ok, ratio.gap)
        self.assertEqual(ratio.value, D("2.5"))

    def test_a_missing_input_is_named_and_the_figure_is_not_invented(self):
        pack = fc.compute_section("F", {})
        for result in pack.results.values():
            if result.ok:
                continue
            self.assertTrue(result.gap, "%s failed without naming its gap" % result.spec_id)
            self.assertEqual(result.value, D("0"))
            for name in result.gap.split(", "):
                self.assertIn(name, pack.gaps)

    def test_the_gaps_name_the_input_that_is_missing(self):
        pack = fc.compute_section("F", {"current_assets": D("50000")})
        ratio = pack.results["current_ratio"]
        self.assertFalse(ratio.ok)
        self.assertIn("current_liabilities", ratio.gap)


class InputPatternTest(unittest.TestCase):
    """The patterns capture the number, not the word before it."""

    def test_every_pattern_captures_the_number(self):
        sample = "Total 1,234.56 here"
        for name, pattern in fc.COMMON_PATTERNS.items():
            match = re.search(pattern, sample, re.I)
            if not match:
                continue
            try:
                D(match.group(1).replace(",", ""))
            except Exception:
                self.fail("%s captures %r instead of the number" % (name, match.group(1)))

    def test_the_patterns_that_captured_the_wrong_group_capture_the_number(self):
        raw = fc.parse_inputs_from_text(
            "Beginning direct materials 10,000. Ending direct materials 8,000. "
            "General and administrative expenses 5,000. Gain on disposal 2,000. "
            "Loss on sale 1,000. Equipment cost 45,000. Prior year net sales 90,000. "
            "Prior year total assets 80,000.", fc.COMMON_PATTERNS)
        self.assertEqual(raw["direct_materials_beg"], D("10000"))
        self.assertEqual(raw["direct_materials_end"], D("8000"))
        self.assertEqual(raw["general_expenses"], D("5000"))
        self.assertEqual(raw["gain_on_disposal"], D("2000"))
        self.assertEqual(raw["loss_on_disposal"], D("1000"))
        self.assertEqual(raw["ppe_cost"], D("45000"))
        self.assertEqual(raw["prior_net_sales"], D("90000"))
        self.assertEqual(raw["prior_total_assets"], D("80000"))


class GlobalProductTest(unittest.TestCase):
    """The product is global: no home exchange, no home country, no home currency."""

    FORBIDDEN = re.compile(
        r"\b(peso|pesos|php|philippines?|filipino|manila|pse|psei)\b", re.I)

    def test_no_spec_names_a_home_country_or_home_currency(self):
        for spec in fc.REGISTRY.all():
            blob = " ".join([spec.id, spec.label, spec.output_name,
                             spec.formula, spec.description])
            found = self.FORBIDDEN.search(blob)
            self.assertIsNone(found, "%s names %s" % (spec.id, found.group(0) if found else ""))


class RoutingTest(unittest.TestCase):
    """The engine answers a computation question, and stays out of the way otherwise."""

    def test_a_bare_trial_balance_does_not_trigger_the_engine(self):
        text = ("The following trial balance was extracted at 31 December 2026.\n"
                "Cash 50,000\nCapital 50,000")
        self.assertEqual(fc.detect_sections(text), [])

    def test_a_ratio_question_names_its_sections(self):
        self.assertEqual(sorted(fc.detect_sections(
            "Calculate the current ratio and the return on assets.")), ["F", "I"])

    def test_a_computation_cue_is_required(self):
        self.assertEqual(fc.detect_sections(
            "The trial balance lists cash of 50,000 and capital of 50,000."), [])


if __name__ == "__main__":
    unittest.main()
