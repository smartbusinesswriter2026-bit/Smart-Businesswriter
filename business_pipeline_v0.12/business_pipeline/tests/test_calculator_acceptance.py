"""Acceptance suite for the Business Calculator -- one test per row of `qa/manual/calculator.md`.

The manual is the specification: every `E-calc-nnn` row names a test below, and every test
names a row.  Nothing here is a new requirement: each expectation is traced to the shipped
`subjects.CALCULATOR_GROUPS`, the frozen `bp.methods.LIBRARY`, `bp.server.PRESETS`, the paper
rules in `docs/VALIDATION_HARNESS.md` §5 (V-01..V-20), the owner's presentation rules P1..P6,
or a wiring invariant W-01..W-12 set in this session's work order.

Coverage today is *complete but unproved*: `tests/test_product_subjects.py::CalculatorGuardTest`
asserts the union is right, and three other modules assert membership.  Nothing asserted that a
tool, launched the way the panel launches it, produces a delivered paper with its checks at its
declared precision.  This file is that assertion.

Rules this file keeps:
  * offline -- no provider key, no network, no model call;
  * it reads the artefact (`Pipeline.run` -> `session_paper.docx_bytes` -> the text), not a
    proxy for it;
  * a refusal is a refusal: a test that expects one asserts the reason too;
  * the harness is proved before it judges: `probe.prove("operations")` and
    `probe.prove("research")` must both be empty, and one negative control
    (`test_E_calc_024`) shows the gates can fail at all.

Run:  PYTHONPATH=src python -m unittest tests.test_calculator_acceptance -v
"""

import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SRC = os.path.join(ROOT, "src")
QA = os.path.join(ROOT, "qa")
for path in (SRC, QA):
    if path not in sys.path:
        sys.path.insert(0, path)

from bp import server                                    # noqa: E402
from bp.methods import LIBRARY                           # noqa: E402
from bp.orchestrator import Pipeline                     # noqa: E402
from bp.product import api, calc_router, session_paper, subjects   # noqa: E402

import probe_calculator as probe                          # noqa: E402

#: The four tools that ship with no preset -- trap 2.  Anything that indexes
#: `PRESETS[tool["preset"]]` crashes on them.
TYPED = ("kruskal_wallis", "mann_whitney", "ols_robust", "spearman")
#: The one documented composite: a template delivered through the core, not a `Method`.
COMPOSITE = "case_decision"


def tools():
    return subjects.compute_tools()


def by_key():
    return {tool["key"]: tool for tool in tools()}


def group_tools():
    return probe.groups()


_CACHE = {}


def built(key):
    """(delivery, text) for one tool, cached -- the paper a reader holds."""
    if key not in _CACHE:
        delivery, _bundle, text = probe.paper(by_key()[key])
        _CACHE[key] = (delivery, text)
    return _CACHE[key]


def page_text():
    with open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8") as stream:
        return stream.read()


class WiringInvariantTest(unittest.TestCase):
    """W-01..W-05: the calculator is wired to the shelves, and nothing drifted."""

    def test_E_calc_001__every_page_tool_appears_in_a_calculator_group(self):
        """W-01 -- a shelf tool added without a group entry is dark on the calculator."""
        on_pages = {tool["key"] for tool in tools()}
        grouped = set()
        for _id, _label, keys in group_tools():
            grouped.update(keys)
        self.assertEqual(on_pages - grouped, set(),
                         "a tool on a subject page is not reachable from any calculator group")

    def test_E_calc_002__every_calculator_entry_names_a_real_tool_and_equals_compute_tools(self):
        """W-02 -- a typo in a group list would silently drop a tool."""
        known = {tool["key"] for tool in tools()}
        grouped = set()
        for _id, _label, keys in group_tools():
            for key in keys:
                self.assertIn(key, known, "calculator names %r, which is not a TOOL_INFO key" % key)
                grouped.add(key)
        self.assertEqual(grouped, known,
                         "the distinct set of calculator keys is not compute_tools()")

    def test_E_calc_003__no_group_is_empty(self):
        """W-02 -- an empty group is a broken chip on the page."""
        for group_id, label, keys in group_tools():
            self.assertTrue(keys, "group %r is empty" % group_id)
            self.assertTrue(label.strip(), "group %r has no label" % group_id)

    def test_E_calc_004__the_eight_groups_are_in_business_function_order(self):
        """The order is the page's taxonomy, and it is asserted as an ordered list."""
        self.assertEqual([group_id for group_id, _l, _k in group_tools()],
                         ["finance", "accounting", "statistics", "economics",
                          "entrepreneurship", "operations", "marketing", "people"])

    def test_E_calc_005__the_inventory_is_8_groups_206_entries_148_distinct(self):
        """The inventory the manual reconciles, measured rather than copied."""
        ordered = group_tools()
        distinct = {key for _id, _l, keys in ordered for key in keys}
        self.assertEqual(len(ordered), 8)
        self.assertEqual(sum(len(keys) for _id, _l, keys in ordered), 206)
        self.assertEqual(len(distinct), 148)
        self.assertEqual(len(tools()), 148)

    def test_E_calc_006__a_shared_key_gives_the_same_numbers_from_every_group(self):
        """W-03 -- one method, one answer; 31 keys are deliberately listed in >1 group."""
        keys = probe.shared_keys()
        self.assertEqual(len(keys), 31,
                         "the shared-key count moved: re-read the manual's inventory row")
        self.assertIn("chi_square", keys)
        self.assertIn("forecast", keys)
        counts = probe.group_count(group_tools())
        self.assertEqual(counts["chi_square"], 5)
        self.assertEqual(counts["forecast"], 6)
        # Pin the whole sharing distribution, not just the total: a taxonomy edit that
        # moved one key from 2 groups to 3 would keep the count at 31 and go unnoticed
        # (which is exactly how the work order's "33" could never be reproduced -- see
        # qa/manual/calculator.md DISPUTED-1, resolved by scanning all 36 revisions of
        # subjects.py: the count has been 31 since 2026-11-02 and was never 33).
        distribution = sorted(__import__("collections").Counter(counts.values()).items())
        self.assertEqual(distribution, [(1, 117), (2, 19), (3, 5), (4, 1), (5, 4), (6, 2)],
                         "the sharing distribution moved: re-read the manual's inventory")
        self.assertEqual(probe.shared_report(), [],
                         "a shared key gave a different paper from a different group")

    def test_E_calc_007__every_tool_resolves_to_a_library_method_or_the_documented_composite(self):
        """W-04 -- 130 of the 148 keys are not method ids; resolve `method`, never `key`."""
        unknown = []
        for tool in tools():
            if tool["method"] == COMPOSITE:
                continue
            if tool["method"] not in LIBRARY:
                unknown.append((tool["key"], tool["method"]))
        self.assertEqual(unknown, [],
                         "a calculator tool runs a method the library does not declare")
        # the composite is the documented exemption and must stay exactly one
        composites = [tool["key"] for tool in tools() if tool["method"] == COMPOSITE]
        self.assertEqual(composites, [COMPOSITE])
        # trap 1, made explicit: the key is NOT the method for most of the shelf
        key_hits = [tool["key"] for tool in tools() if tool["key"] in LIBRARY]
        self.assertEqual(len(tools()) - len(key_hits), 130)

    def test_E_calc_008__every_preset_exists_and_runs_its_declared_method(self):
        """W-05 -- a preset retargeted at another method is a wrong number on the page."""
        for tool in tools():
            if not tool["preset"]:
                continue
            self.assertIn(tool["preset"], server.PRESETS,
                          "%s names a preset that does not exist" % tool["key"])
            self.assertEqual(server.PRESETS[tool["preset"]]["method"], tool["method"],
                             "%s: preset %r runs a different method"
                             % (tool["key"], tool["preset"]))



class DeliveryTest(unittest.TestCase):
    """W-06..W-09: every tool delivers a paper, with its checks, at its precision."""

    def test_E_calc_009__every_tool_on_the_calculator_delivers_a_paper(self):
        """P6 -- a tool that cannot be launched is dark, however green its unit test is."""
        failures = []
        for tool in tools():
            delivery, text = built(tool["key"])
            if delivery.status != "delivered":
                failures.append((tool["key"], delivery.blocked_reason))
            elif not text.strip():
                failures.append((tool["key"], "delivered an empty paper"))
        self.assertEqual(failures, [], "a calculator tool did not deliver a paper")

    def test_E_calc_010__the_four_typed_tools_run_end_to_end_with_no_preset(self):
        """W-06 / trap 2 -- preset is None, so the figures are typed."""
        typed = [tool for tool in tools() if not tool["preset"]]
        self.assertEqual(sorted(tool["key"] for tool in typed), list(TYPED))
        for tool in typed:
            self.assertIsNone(tool["preset"])
            delivery, text = built(tool["key"])
            self.assertEqual(delivery.status, "delivered", "%s did not deliver" % tool["key"])
            outputs = (delivery.appendix.get("reperform") or {}).get("outputs") or {}
            self.assertTrue(outputs, "%s delivered an empty success" % tool["key"])
            self.assertEqual(probe.gates(tool, delivery, text), [],
                             "%s failed a gate" % tool["key"])

    def test_E_calc_011__a_typed_tool_sent_empty_inputs_blocks_with_a_reason(self):
        """W-06 -- the UI sends `{}` when preset is null; that must fail closed, not crash."""
        for key in TYPED:
            tool = by_key()[key]
            delivery = Pipeline().run({"objective": "empty inputs", "method": tool["method"],
                                       "inputs": {}}, lambda spec: True)
            self.assertEqual(delivery.status, "blocked",
                             "%s accepted empty inputs as a delivery" % key)
            self.assertTrue(delivery.blocked_reason.strip(),
                            "%s blocked with no reason" % key)
            self.assertEqual(delivery.report.strip(), "",
                             "%s blocked but still wrote a result" % key)

    def test_E_calc_012__every_delivered_tool_prints_all_its_declared_checks(self):
        """W-07 -- a check that cannot run must block, never silently pass."""
        failures = []
        for tool in tools():
            delivery, text = built(tool["key"])
            declared = [name for name in (delivery.appendix.get("tests") or [])
                        if str(name).strip()]
            if not declared:
                failures.append((tool["key"], "declared no checks"))
                continue
            for name in declared:
                if text.count(probe._plain(name) + ".") != 1:
                    failures.append((tool["key"], name))
        self.assertEqual(failures, [], "a check was skipped, renamed or printed twice")

    def test_E_calc_013__every_figure_prints_at_its_declared_precision(self):
        """W-08 -- and no figure carries six or more decimals (D-RES-05 / B-214 house rule)."""
        for tool in tools():
            delivery, text = built(tool["key"])
            self.assertEqual(probe.gates(tool, delivery, text), [],
                             "%s fails a delivery gate" % tool["key"])
            self.assertNotRegex(text, r"\d\.\d{6,}",
                                "%s prints a figure at six or more decimal places"
                                % tool["key"])

    def test_E_calc_014__no_paper_prints_a_python_repr_or_scientific_notation(self):
        """W-08 / P4 -- a repr or an exponent is not a figure a student can read."""
        for tool in tools():
            _delivery, text = built(tool["key"])
            for mark in ("{'", "['", "Decimal(", "'}"):
                self.assertNotIn(mark, text, "%s prints %r" % (tool["key"], mark))

    def test_E_calc_015__a_refusal_names_its_reason_and_never_renders_as_delivered(self):
        """W-09 -- silent success is a BLOCKER; a refusal without a reason is one too."""
        refusal = Pipeline().run({"objective": "unknown", "method": "no_such_method",
                                  "inputs": {}}, lambda spec: True)
        self.assertEqual(refusal.status, "blocked")
        self.assertIn("unknown method", refusal.blocked_reason)
        self.assertEqual(refusal.report.strip(), "", "a blocked run wrote a result")


class SearchAndPanelTest(unittest.TestCase):
    """W-10..W-11: the search and ask surfaces reach a tool and never invent one."""

    def test_E_calc_016__the_search_reaches_every_tool_by_its_own_name(self):
        """W-10 -- the panel filters on `label + method + what`; every tool must match itself."""
        for group_id, _label, keys in group_tools():
            for key in keys:
                tool = by_key()[key]
                haystack = ("%s %s %s" % (tool["label"], tool["method"], tool["what"])).lower()
                self.assertIn(tool["label"].lower(), haystack,
                              "%s is unreachable from group %s" % (key, group_id))

    def test_E_calc_017__the_ask_surface_routes_a_sentence_to_a_real_tool(self):
        """W-10 -- a named calculation reaches its tool, with a plan, and runs nothing yet."""
        payload = calc_router.plan("break-even with 1200 fixed cost, price 20, variable 12")
        self.assertEqual(payload["outcome"], "run")
        self.assertEqual(payload["tool"], "breakeven")
        self.assertIn(payload["tool"], by_key())

    def test_E_calc_018__an_unknown_sentence_never_invents_a_tool(self):
        """W-10 -- the router returns no tool and says why, rather than the nearest match."""
        for sentence in ("largest prime under a million", "what is the meaning of life"):
            payload = calc_router.plan(sentence)
            self.assertNotEqual(payload["outcome"], "run",
                                "the router invented a run for %r" % sentence)
            self.assertIsNone(payload.get("tool"),
                              "the router invented tool %r for %r"
                              % (payload.get("tool"), sentence))
            self.assertTrue(payload.get("reason", "").strip(),
                            "no reason given for %r" % sentence)

    def test_E_calc_019__an_unknown_route_is_404_naming_it(self):
        """W-10 -- the route surface refuses by name; it does not serve something else."""
        status, payload = api.handle("POST", "/api/cases/calculator/nonsense", {})
        self.assertEqual(status, 404)
        self.assertIn("unknown", payload["error"])

    def test_E_calc_020__the_panel_note_stays_true(self):
        """W-11 -- the note is published to students and must not drift."""
        note = subjects.calculator_groups()["note"]
        self.assertIn("computes nothing", note)
        self.assertIn("free-form arithmetic is not supported", note)
        self.assertIn("The Business Calculator arranges inputs", note)
        self.assertIn("computes nothing itself", page_text())




class DownloadTest(unittest.TestCase):
    """W-12: the calculator is a download surface too -- P1..P6 hold on the artefact."""

    def test_E_calc_021__a_downloaded_paper_carries_no_markdown_or_spec_hash(self):
        for tool in tools():
            delivery, text = built(tool["key"])
            bundle = {"report": delivery.report, "appendix": delivery.appendix}
            payload = session_paper.docx_bytes(bundle)
            self.assertNotIn(b"spec_hash", payload,
                             "%s: the paper bytes carry a specification hash" % tool["key"])
            for mark in ("##", "**", "```", "Diagram to draw"):
                self.assertNotIn(mark, text,
                                 "%s prints %r in a downloaded paper" % (tool["key"], mark))

    def test_E_calc_022__the_download_buttons_survive_in_the_page(self):
        """W-12 -- #chartbtn/#expbtn/#expzip stay wired and stay off the calculator panel."""
        page = page_text()
        for button in ("chartbtn", "expbtn", "expzip"):
            self.assertIn('id="%s"' % button, page, "%s is missing" % button)
            self.assertIn('$("#%s").onclick' % button, page, "%s is not wired" % button)
        panel = page.split('id="panel-calculator"', 1)[1].split("</section>", 1)[0]
        for button in ("chartbtn", "expbtn", "expzip"):
            self.assertNotIn(button, panel,
                             "%s leaked into the calculator panel" % button)


class HarnessHygieneTest(unittest.TestCase):
    """The harness is proved before it judges, and the numbers it quotes are re-measured."""

    def test_E_calc_023__the_harness_reports_nothing_on_a_shelf_whose_suite_is_green(self):
        """A harness is a suspect until it has been aimed at a shelf it did not build."""
        self.assertEqual(probe.prove("operations"), [],
                         "the probe reports a problem on operations, whose suite is green")
        self.assertEqual(probe.prove("research"), [],
                         "the probe reports a problem on research, whose suite is green")

    def test_E_calc_024__the_gates_have_teeth(self):
        """A negative control: the gate must fail on a real breach, or it proves nothing."""
        tool = by_key()["npv"]
        delivery, _text = built("npv")
        # 1. a raw, unrounded Decimal in the report text (the D-RES-05 shape)
        broken = {"report": delivery.report + "\nThe npv is 2586.473380864479782327671368.",
                  "appendix": delivery.appendix}
        payload = session_paper.docx_bytes(broken)
        failures = probe.gates(tool, delivery, probe.text_of(payload),
                               appendix=delivery.appendix)
        self.assertTrue(any("6+ decimal" in item for item in failures),
                        "the gate missed a 30-digit Decimal: %r" % failures)
        # 2. a declared check that the paper does not print.  The paper renders its checks
        # from the appendix, so the text is the real one and the *declaration* carries the
        # extra name -- exactly the shape of a check that silently stopped being printed.
        thin = json.loads(json.dumps(delivery.appendix, default=str))
        thin["tests"] = list(thin.get("tests") or []) + ["a_check_no_paper_prints"]
        failures = probe.gates(tool, delivery, built("npv")[1], appendix=thin)
        self.assertTrue(any("check not printed" in item for item in failures),
                        "the gate missed a missing check: %r" % failures)
        # and the unbroken paper still passes, so the control is not just always-red
        self.assertEqual(probe.gates(tool, delivery, built("npv")[1]), [])

    def test_E_calc_025__the_library_and_the_frozen_fixture_are_the_numbers_measured(self):
        fixture = json.load(open(os.path.join(ROOT, "tests", "fixtures", "frozen_contract.json"),
                                 encoding="utf-8"))
        self.assertEqual(len(LIBRARY), 209)
        self.assertEqual(len(server.PRESETS), 144)
        self.assertEqual(len(fixture["methods"]), 209)
        self.assertEqual(len(fixture["presets"]), 144)
        for method_id in {tool["method"] for tool in tools()}:
            if method_id == COMPOSITE:
                continue
            self.assertIn(method_id, fixture["methods"],
                          "%s runs a method the frozen contract does not pin" % method_id)


if __name__ == "__main__":
    unittest.main()
