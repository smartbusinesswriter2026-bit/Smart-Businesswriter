"""The catalogue's implementation verdicts must match the engine.

The subject pages show, for every catalogue record, an `implementation_status`
and the methods it links to. Those strings are read by students and are
factual claims about what the system can do, so they must not drift away from
the method library.

This file exists because they had drifted: `QNT-FIN-05 Management accounting`
read "not implemented" while `management_accounts` was implemented, tested and
served on the very page that displayed the verdict - the same for QNT-FIN-03,
QNT-FIN-04, QNT-FIN-06, QNT-FIN-01 (IRR and payback), QNT-STA-03 (chi-square
and ANOVA) and QNT-STA-04 (logistic regression).

The tests are deliberately structural rather than a snapshot of the prose: a
record may reword its status freely, but it may not deny a method the engine
registers, and it may not link a method that does not exist.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from bp.methods import LIBRARY                      # noqa: E402
from bp.product import subjects as subjects         # noqa: E402


def _records():
    return subjects.CATALOGUE


class CatalogueLinksResolve(unittest.TestCase):
    def test_every_linked_method_exists_in_the_library(self):
        """A link to a method id that does not exist is a dead end for the page."""
        missing = []
        for rid, rec in _records().items():
            for link in rec.get("linked_methods") or []:
                mid = link.get("method_id")
                if mid not in LIBRARY:
                    missing.append((rid, mid))
        self.assertEqual(missing, [], "catalogue records link unknown methods: %r" % (missing,))


class CatalogueDoesNotDenyWhatIsBuilt(unittest.TestCase):
    def test_no_record_claims_nothing_while_linking_methods(self):
        """'not implemented' with a linked method is a self-contradiction."""
        contradictory = []
        for rid, rec in _records().items():
            status = (rec.get("implementation_status") or "").strip().lower()
            if status == "not implemented" and (rec.get("linked_methods") or []):
                contradictory.append(rid)
        self.assertEqual(contradictory, [],
                         "records say 'not implemented' but link methods: %r" % (contradictory,))

    def test_accounting_records_claim_the_accounting_methods(self):
        """The Accounting subject page must not deny the methods it is built on."""
        expected = {
            "QNT-FIN-02": ["breakeven", "multi_product_breakeven"],
            "QNT-FIN-05": ["management_accounts"],
            "QNT-FIN-03": ["ratio_analysis"],
        }
        problems = []
        for rid, methods in expected.items():
            rec = _records().get(rid)
            if rec is None:
                problems.append("%s is missing from the catalogue" % rid)
                continue
            status = (rec.get("implementation_status") or "").strip().lower()
            if status == "not implemented":
                problems.append("%s says 'not implemented'" % rid)
            linked = {l.get("method_id") for l in rec.get("linked_methods") or []}
            for m in methods:
                if m not in LIBRARY:
                    problems.append("%s is expected to be implemented but is not in the library" % m)
                elif m not in linked:
                    problems.append("%s does not link %s" % (rid, m))
        self.assertEqual(problems, [], "; ".join(problems))

    def test_finance_records_claim_the_finance_methods(self):
        expected = {
            "QNT-FIN-01": ["npv", "irr", "discounted_payback"],
            # currency_convert is deliberately NOT claimed here: QNT-FIN-04 is scoped to
            # WACC, CAPM, debt capacity and valuation scenarios, and does not mention
            # currency. Claiming it would be an overclaim in the other direction.
            "QNT-FIN-04": ["wacc", "dcf_valuation", "equity_bridge"],
            "QNT-FIN-06": ["unit_economics"],
        }
        problems = []
        for rid, methods in expected.items():
            rec = _records().get(rid)
            if rec is None:
                problems.append("%s is missing from the catalogue" % rid)
                continue
            linked = {l.get("method_id") for l in rec.get("linked_methods") or []}
            for m in methods:
                if m not in linked:
                    problems.append("%s does not link %s" % (rid, m))
        self.assertEqual(problems, [], "; ".join(problems))

    def test_statistics_regression_records_claim_what_is_built(self):
        expected = {
            "QNT-STA-03": ["chi_square", "anova", "kruskal_wallis", "two_way_anova"],
            "QNT-STA-04": ["logistic_regression"],
        }
        problems = []
        for rid, methods in expected.items():
            rec = _records().get(rid)
            if rec is None:
                problems.append("%s is missing from the catalogue" % rid)
                continue
            linked = {l.get("method_id") for l in rec.get("linked_methods") or []}
            for m in methods:
                if m not in linked:
                    problems.append("%s does not link %s" % (rid, m))
        self.assertEqual(problems, [], "; ".join(problems))


class VerdictsAreHonest(unittest.TestCase):
    """The label must describe the delivery form, not grade the framework."""

    def test_every_record_has_a_known_form(self):
        from bp.product.subjects import FORM_SHORT

        for rid, rec in _records().items():
            self.assertIn(rec.get("form"), FORM_SHORT, rid)
            self.assertTrue(rec.get("status_short"), rid)
            self.assertTrue(rec.get("status_note"), rid)

    def test_no_theory_is_presented_as_an_unbuilt_worksheet(self):
        for rid, rec in _records().items():
            if rec.get("type") == "T":
                self.assertEqual(rec.get("form"), "theory", rid)
                self.assertNotIn("not implemented", (rec.get("status_note") or "").lower(), rid)
                self.assertIn("not a worksheet by design", rec.get("status_note"), rid)

    def test_no_read_only_framework_says_not_implemented(self):
        for rid, rec in _records().items():
            if rec.get("form") == "read_only" and rec.get("type") in ("F", "M"):
                self.assertNotIn("not implemented", (rec.get("status_note") or "").lower(), rid)
                self.assertIn("read-only record", rec.get("status_note"), rid)


class SubjectToolsResolve(unittest.TestCase):
    def test_every_subject_tool_resolves_to_something_that_runs(self):
        """A subject tile must resolve either to a registered method or to a
        registered composite preset.

        `case_decision` is a composite preset (it orchestrates NPV over several
        options) rather than a `LIBRARY` entry, so requiring `method in LIBRARY`
        would be wrong. What must hold is that the preset the tile launches
        actually exists - otherwise the button is unreachable.
        """
        from bp.server import PRESETS

        problems = []
        for tool in subjects.compute_tools():
            preset = tool.get("preset")
            mid = tool.get("method")
            if preset and preset not in PRESETS:
                problems.append((tool.get("key"), "preset %r missing" % preset))
                continue
            if not preset and mid not in LIBRARY:
                problems.append((tool.get("key"), "method %r missing and no preset" % mid))
        self.assertEqual(problems, [], "compute tools do not resolve: %r" % (problems,))


if __name__ == "__main__":
    unittest.main()
