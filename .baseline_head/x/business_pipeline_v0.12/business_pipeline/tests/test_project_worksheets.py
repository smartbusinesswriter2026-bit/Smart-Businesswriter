"""The four project-management worksheets added in B-119.

These are T4 structure-and-evidence worksheets: the student supplies every item,
the system places it, reproduces it verbatim, names the gaps and derives no
score, ranking, probability or verdict.  Charter and WBS use the shared canvas
builder; RACI and the risk register use the shared declared-matrix builder, with
two extra RACI checks (exactly one accountable role and at least one responsible
role per activity).
"""

import copy
import sys
import unittest

sys.path.insert(0, "src")
from bp import registry as R, templates as T  # noqa: E402
from bp.methods import DataError  # noqa: E402

NEW = {
    "template_project_charter": "PM-05",
    "template_wbs": "PM-09",
    "template_raci": "PM-10",
    "template_risk_register": "PM-06",
    "template_stakeholder_plan": "PM-15",
    "template_lessons_learned": "PM-16",
}


def example(kind):
    return copy.deepcopy(T.EXAMPLES[kind])


def results(kind, req):
    out = T.run_template(kind, req["inputs"])
    return {name: ok for name, ok in out["results"]}, out


class RegistrationTest(unittest.TestCase):
    def test_every_new_worksheet_is_t4_and_links_its_record(self):
        for kind, rid in NEW.items():
            template = T.TEMPLATES[kind]
            self.assertEqual(template["tier"], "T4", kind)
            self.assertEqual(template["registry_ids"], [rid], kind)
            self.assertEqual(R.get(rid)["template"], kind, rid)
            self.assertEqual(R.get(rid)["form"], "worksheet", rid)

    def test_every_new_worksheet_declares_the_form_the_page_renders(self):
        expected = {"template_project_charter": "canvas", "template_wbs": "canvas",
                    "template_raci": "matrix", "template_risk_register": "matrix",
                    "template_stakeholder_plan": "canvas", "template_lessons_learned": "canvas"}
        for kind, form_kind in expected.items():
            self.assertEqual(T.describe(kind)["form_kind"], form_kind, kind)

    def test_every_new_worksheet_describes_its_limits_and_unsupported_use(self):
        for kind in NEW:
            described = T.describe(kind)
            self.assertTrue(described["intended_use"], kind)
            self.assertTrue(described["unsupported_use"], kind)
            self.assertTrue(described["limitations"], kind)
            self.assertTrue(described["defaults"], kind)
            self.assertTrue(described["planned_checks"], kind)
            self.assertIn("blocks" if kind in T.CANVAS_BLOCKS else "rows",
                          described["input_help"], kind)

    def test_the_pm_page_offers_all_six_and_no_record_is_repeated(self):
        from bp.product import subjects

        page = subjects.detail("project-management")
        offered = {worksheet["template"] for worksheet in page["worksheets"]}
        self.assertTrue(set(NEW).issubset(offered))
        self.assertFalse({row["id"] for row in page["records"]}
                         & {w["catalogue_id"] for w in page["worksheets"]})

    def test_the_registry_accepts_the_new_template_links(self):
        self.assertEqual(R.validate(R.load()), [])


class ExampleTest(unittest.TestCase):
    def test_every_example_runs_and_passes_its_own_checks(self):
        for kind in NEW:
            checks, out = results(kind, example(kind))
            self.assertTrue(all(checks.values()), (kind, [k for k, ok in checks.items() if not ok]))
            self.assertTrue(out["counts"], kind)

    def test_no_example_returns_a_score_ranking_probability_or_verdict(self):
        for kind in NEW:
            _, out = results(kind, example(kind))
            for forbidden in ("score", "overall", "ranking", "probability", "verdict", "total_score"):
                self.assertNotIn(forbidden, out["analysis"], (kind, forbidden))
                self.assertNotIn(forbidden, out["counts"], (kind, forbidden))

    def test_every_supplied_text_is_reproduced_verbatim(self):
        for kind in NEW:
            req = example(kind)
            _, out = results(kind, req)
            texts = []
            if "blocks" in req["inputs"]:
                texts = [item["text"] for items in req["inputs"]["blocks"].values() for item in items]
            else:
                texts = ([row["text"] for row in req["inputs"]["rows"]]
                         + [column["text"] for column in req["inputs"]["columns"]]
                         + [cell["text"] for cell in req["inputs"]["cells"]])
            for text in texts:
                self.assertIn(text, out["listing"], (kind, text))


class RaciTest(unittest.TestCase):
    def test_one_accountable_role_per_activity_is_checked(self):
        req = example("template_raci")
        # A1 already has one A; make its R cell a second A.
        cell = next(c for c in req["inputs"]["cells"] if c["row"] == "A1" and c["text"] == "R")
        cell["text"] = "A"
        checks, _ = results("template_raci", req)
        self.assertFalse(checks["every_activity_has_exactly_one_accountable"])

    def test_at_least_one_responsible_role_per_activity_is_checked(self):
        req = example("template_raci")
        # A1 has one R; change it to C and leave no R on that activity.
        cell = next(c for c in req["inputs"]["cells"] if c["row"] == "A1" and c["text"] == "R")
        cell["text"] = "C"
        checks, _ = results("template_raci", req)
        self.assertFalse(checks["every_activity_has_at_least_one_responsible"])

    def test_a_cell_must_start_with_r_a_c_or_i(self):
        req = example("template_raci")
        req["inputs"]["cells"][0]["text"] = "Owns the budget"
        with self.assertRaises(DataError):
            T.run_template("template_raci", req["inputs"])


class RiskRegisterTest(unittest.TestCase):
    def test_an_empty_cell_is_named_and_not_filled(self):
        req = example("template_risk_register")
        req["inputs"]["cells"].pop()
        checks, out = results("template_risk_register", req)
        self.assertTrue(checks["empty_cells_reported_not_filled"])
        self.assertEqual(out["analysis"]["counts"]["n_empty_cells"], 1)

    def test_no_probability_expected_value_or_score_is_computed(self):
        _, out = results("template_risk_register", example("template_risk_register"))
        for forbidden in ("probability", "expected_value", "expected_loss", "risk_score", "ranking"):
            self.assertNotIn(forbidden, out["analysis"])
            self.assertNotIn(forbidden, out["counts"])


if __name__ == "__main__":
    unittest.main()
