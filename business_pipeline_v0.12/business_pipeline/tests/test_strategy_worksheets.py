"""The eight strategy worksheets added in B-108.

These are T4 structure-and-evidence worksheets: the student supplies every item,
the system places it, reproduces it verbatim, names the gaps and derives no
score, ranking, probability or verdict.  The tests exercise the shared builders
(canvas, declared matrix, VRIO) and the two places where a framework could
silently become a scoring machine.
"""

import copy
import sys
import unittest

sys.path.insert(0, "src")
from bp import templates as T, registry as R  # noqa: E402
from bp.methods import DataError  # noqa: E402
from bp.orchestrator import Pipeline  # noqa: E402

NEW = {
    "template_pestel": "STR-06",
    "template_value_chain": "STR-03",
    "template_ansoff": "STR-09",
    "template_blue_ocean_errc": "STR-13",
    "template_activity_system_fit": "STR-04",
    "template_scenario_planning": "STR-14",
    "template_strategic_group_map": "STR-12",
    "template_vrio": "STR-08",
}
yes = lambda _s: True


def example(kind):
    return copy.deepcopy(T.EXAMPLES[kind])


def run(req):
    pipeline = Pipeline()
    return pipeline, pipeline.run(req, yes)


class RegistrationTest(unittest.TestCase):
    def test_every_new_worksheet_is_registered_as_t4_and_links_its_record(self):
        for kind, rid in NEW.items():
            template = T.TEMPLATES[kind]
            self.assertEqual(template["tier"], "T4", kind)
            self.assertEqual(template["registry_ids"], [rid], kind)
            self.assertEqual(R.get(rid)["template"], kind, rid)
            self.assertEqual(R.get(rid)["form"], "worksheet", rid)

    def test_every_new_worksheet_describes_its_limits_and_unsupported_use(self):
        for kind in NEW:
            described = T.describe(kind)
            self.assertTrue(described["intended_use"], kind)
            self.assertTrue(described["unsupported_use"], kind)
            self.assertTrue(described["limitations"], kind)
            self.assertTrue(described["defaults"], kind)
            self.assertTrue(described["planned_checks"], kind)
            self.assertIn("blocks" if kind in T.CANVAS_BLOCKS else (
                "resources" if kind == "template_vrio" else "rows"), described["input_help"], kind)

    def test_the_management_page_offers_all_eight_and_the_registry_agrees(self):
        from bp.product import subjects

        page = subjects.detail("management")
        offered = {worksheet["template"] for worksheet in page["worksheets"]}
        self.assertTrue(set(NEW).issubset(offered))
        self.assertFalse({row["id"] for row in page["records"]} & {w["catalogue_id"] for w in page["worksheets"]})


class ExampleTest(unittest.TestCase):
    def test_every_example_runs_and_passes_its_own_checks(self):
        for kind in NEW:
            out = T.run_template(kind, example(kind)["inputs"])
            self.assertTrue(all(ok for _, ok in out["results"]), (kind, out["results"]))
            self.assertTrue(out["counts"], kind)

    def test_no_new_worksheet_can_return_a_score_ranking_or_probability(self):
        for kind in NEW:
            out = T.run_template(kind, example(kind)["inputs"])
            analysis = out["analysis"]
            for forbidden in ("score", "overall", "ranking", "total_score", "probability", "verdict"):
                self.assertNotIn(forbidden, analysis, (kind, forbidden))
                self.assertNotIn(forbidden, out["counts"], (kind, forbidden))

    def test_each_worksheet_delivers_end_to_end_as_t4(self):
        for kind in ("template_pestel", "template_vrio", "template_scenario_planning"):
            request = example(kind)
            request["objective"] = "Work through the worksheet"
            _, delivery = run(request)
            self.assertEqual((delivery.status, delivery.tier), ("delivered", "T4"), kind)
            self.assertTrue(("no facts of its own" in delivery.report) or ("predicts nothing" in delivery.report), kind)
            self.assertEqual(delivery.appendix["template"]["registry_ids"], [NEW[kind]], kind)


class MatrixValidationTest(unittest.TestCase):
    def errors(self, kind, inputs):
        return " | ".join(T.validate(kind, inputs))

    def base(self, kind):
        return copy.deepcopy(T.EXAMPLES[kind]["inputs"])

    def test_row_column_and_cell_counts_are_enforced(self):
        inputs = self.base("template_scenario_planning")
        self.assertIn("2 to 4", self.errors("template_scenario_planning", {**inputs, "rows": inputs["rows"][:1]}))
        self.assertIn("2 to 6", self.errors("template_scenario_planning", {**inputs, "columns": inputs["columns"][:1]}))
        self.assertIn("non-empty list", self.errors("template_scenario_planning", {**inputs, "cells": []}))

    def test_a_cell_must_cite_a_declared_row_and_column(self):
        inputs = self.base("template_scenario_planning")
        bad = copy.deepcopy(inputs["cells"])
        bad[0]["row"] = "NOPE"
        self.assertIn("'row' must be one of", self.errors("template_scenario_planning", {**inputs, "cells": bad}))
        bad = copy.deepcopy(inputs["cells"])
        bad[0]["column"] = "NOPE"
        self.assertIn("'column' must be one of", self.errors("template_scenario_planning", {**inputs, "cells": bad}))

    def test_a_duplicate_cell_is_refused(self):
        inputs = self.base("template_scenario_planning")
        cells = inputs["cells"] + [copy.deepcopy(inputs["cells"][0])]
        self.assertIn("duplicate cell", self.errors("template_scenario_planning", {**inputs, "cells": cells}))

    def test_strategic_group_map_requires_two_justified_axes_and_a_group(self):
        inputs = self.base("template_strategic_group_map")
        self.assertIn("'rationale' is required",
                      self.errors("template_strategic_group_map", {**inputs, "columns": [dict(c, rationale=None) if i else c for i, c in enumerate(inputs["columns"])]}))
        self.assertIn("'group' is required",
                      self.errors("template_strategic_group_map", {**inputs, "rows": [dict(r, group=None) if i == 0 else r for i, r in enumerate(inputs["rows"])]}))
        self.assertIn("2 to 2", self.errors("template_strategic_group_map",
                                            {**inputs, "columns": inputs["columns"] + [{"id": "Z", "text": "Third axis", "rationale": "x"}]}))

    def test_empty_cells_are_named_and_never_filled(self):
        inputs = self.base("template_scenario_planning")
        missing = inputs["cells"].pop()
        analysis = T.build_matrix("template_scenario_planning", inputs)
        self.assertIn(f"{missing['row']}:{missing['column']}", analysis["audit"]["empty_cells"])
        _, listing = T.render_matrix(analysis)
        self.assertIn("No evidence supplied.", listing)


class VrioTest(unittest.TestCase):
    def test_answers_evidence_and_counts(self):
        analysis = T.build_vrio(copy.deepcopy(T.EXAMPLES["template_vrio"]["inputs"]))
        self.assertEqual(analysis["counts"]["n_resources"], 2)
        self.assertEqual(analysis["counts"]["n_evidence"], 6)
        self.assertEqual(analysis["counts"]["n_unsure"], 1)
        self.assertEqual(analysis["audit"]["unsupported_answers"], ["R2:organized"])
        self.assertEqual(analysis["counts"]["n_with_conclusion"], 1)

    def test_a_yes_or_no_without_evidence_is_flagged_but_unsure_is_not(self):
        analysis = T.build_vrio(copy.deepcopy(T.EXAMPLES["template_vrio"]["inputs"]))
        self.assertIn("R2:organized", analysis["audit"]["unsupported_answers"])
        self.assertNotIn("R1:organized", analysis["audit"]["unsupported_answers"])

    def test_no_competitive_implication_is_derived(self):
        analysis = T.build_vrio(copy.deepcopy(T.EXAMPLES["template_vrio"]["inputs"]))
        for forbidden in ("verdict", "implication", "score", "overall"):
            self.assertNotIn(forbidden, analysis)
        text, listing = T.render_vrio(analysis)
        self.assertIn("does not derive a verdict", text)
        self.assertIn("No conclusion supplied; the system does not derive one.", listing)

    def test_answers_and_conclusions_must_be_yours_and_well_formed(self):
        inputs = copy.deepcopy(T.EXAMPLES["template_vrio"]["inputs"])
        bad = copy.deepcopy(inputs)
        bad["resources"][0]["answers"]["rare"] = "maybe"
        self.assertIn("must be one of", " | ".join(T.validate("template_vrio", bad)))
        bad = copy.deepcopy(inputs)
        del bad["resources"][0]["answers"]["organized"]
        self.assertIn("'answers' must carry exactly", " | ".join(T.validate("template_vrio", bad)))
        bad = copy.deepcopy(inputs)
        bad["resources"][0]["evidence"][0]["question"] = "brand"
        self.assertIn("'question' must be one of", " | ".join(T.validate("template_vrio", bad)))
        bad = copy.deepcopy(inputs)
        bad["resources"][0]["conclusion"] = "line one\nline two"
        self.assertIn("one line", " | ".join(T.validate("template_vrio", bad)))
        bad = copy.deepcopy(inputs)
        bad["resources"][0]["evidence"][0]["provenance"] = "sourced"
        self.assertIn("needs a 'source'", " | ".join(T.validate("template_vrio", bad)))

    def test_the_builder_blocks_invalid_input(self):
        with self.assertRaises(DataError):
            T.build_vrio({"resources": []})


class GovernanceTest(unittest.TestCase):
    def test_no_new_record_still_reads_not_implemented(self):
        for rid in NEW.values():
            self.assertNotIn("not implemented", R.get(rid)["implementation_status"].lower(), rid)

    def test_declared_answers_are_not_a_score(self):
        """A VRIO worksheet that turns four answers into a number would be the trap."""
        analysis = T.build_vrio(copy.deepcopy(T.EXAMPLES["template_vrio"]["inputs"]))
        rendered = str(analysis).lower()
        self.assertNotIn("sustained advantage:", rendered)
        self.assertNotIn("competitive advantage:", rendered)
        self.assertNotIn("score", rendered)


if __name__ == "__main__":
    unittest.main()
