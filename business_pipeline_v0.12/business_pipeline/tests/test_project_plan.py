"""The project-plan record: validation, cost roll-up, schedule rows and tables."""

import unittest

from bp.product import project_plan


def record():
    return {
        "charter": {
            "title": "Meal counter",
            "objective": "Open a campus meal counter",
            "sponsor": "Dean",
            "scope_in": ["Counter", "Menu"],
            "scope_out": ["Delivery"],
            "deliverables": ["Counter built", "Menu approved"],
            "success_measures": ["Break-even in 12 months"],
            "budget_total": 25000,
            "currency": "USD",
        },
        "wbs": [
            {"id": "1", "parent": None, "level": 1, "name": "Design", "acceptance": "", "owner": "", "cost": 0},
            {"id": "1.1", "parent": "1", "level": 2, "name": "Drawings", "acceptance": "Signed", "owner": "Architect", "cost": 12000},
            {"id": "1.2", "parent": "1", "level": 2, "name": "Permit", "acceptance": "Issued", "owner": "PM", "cost": 8000},
            {"id": "2", "parent": None, "level": 1, "name": "Build", "acceptance": "", "owner": "", "cost": 0},
            {"id": "2.1", "parent": "2", "level": 2, "name": "Fit-out", "acceptance": "Handover", "owner": "Builder", "cost": 5000},
        ],
        "activities": [
            {"id": "A1", "name": "Draw", "wbs": "1.1", "duration": 5, "predecessors": [], "resource": "Architect"},
            {"id": "A2", "name": "Permit", "wbs": "1.2", "duration": 3, "predecessors": ["A1"], "resource": "PM"},
            {"id": "A3", "name": "Fit-out", "wbs": "2.1", "duration": 4, "predecessors": ["A2"], "resource": "Builder"},
        ],
        "resources": [{"name": "Architect", "role": "Design", "capacity": 1},
                      {"name": "PM", "role": "Management", "capacity": 1},
                      {"name": "Builder", "role": "Build", "capacity": 1}],
        "raci": [
            {"activity": "A1", "role": "Design", "letter": "R"},
            {"activity": "A1", "role": "Management", "letter": "A"},
            {"activity": "A2", "role": "Management", "letter": "R"},
            {"activity": "A2", "role": "Management", "letter": "A"},
            {"activity": "A3", "role": "Build", "letter": "R"},
            {"activity": "A3", "role": "Management", "letter": "A"},
        ],
        "risks": [{"id": "R1", "description": "Permit delay", "likelihood": "Medium",
                   "impact": "High", "response": "Apply early", "owner": "PM"}],
        "options": {"pert": False, "contingency_pct": 10},
    }


class ValidationTest(unittest.TestCase):
    def test_a_complete_record_has_no_problems(self):
        self.assertEqual(project_plan.validate(project_plan.normalise(record())), [])

    def test_a_work_package_needs_an_owner(self):
        data = record()
        data["wbs"][1]["owner"] = ""
        problems = project_plan.validate(project_plan.normalise(data))
        self.assertTrue(any("1.1 has no owner" in problem for problem in problems), problems)

    def test_a_work_package_needs_a_cost_and_acceptance(self):
        data = record()
        data["wbs"][1]["cost"] = None
        data["wbs"][1]["acceptance"] = ""
        problems = project_plan.validate(project_plan.normalise(data))
        self.assertTrue(any("1.1 has no cost" in problem for problem in problems), problems)
        self.assertTrue(any("1.1 has no acceptance" in problem for problem in problems), problems)

    def test_a_parent_cost_is_refused(self):
        data = record()
        data["wbs"][0]["cost"] = 100
        problems = project_plan.validate(project_plan.normalise(data))
        self.assertTrue(any("parent" in problem for problem in problems), problems)

    def test_a_duplicate_wbs_id_is_refused(self):
        data = record()
        data["wbs"].append(dict(data["wbs"][1]))
        problems = project_plan.validate(project_plan.normalise(data))
        self.assertTrue(any("duplicate WBS id" in problem for problem in problems), problems)

    def test_raci_needs_one_a_and_one_r(self):
        data = record()
        data["raci"] = [row for row in data["raci"] if row["activity"] != "A1"]
        problems = project_plan.validate(project_plan.normalise(data))
        self.assertTrue(any("A1 needs exactly one accountable" in problem for problem in problems), problems)

    def test_a_risk_needs_an_owner_and_response(self):
        data = record()
        data["risks"][0]["owner"] = ""
        data["risks"][0]["response"] = ""
        problems = project_plan.validate(project_plan.normalise(data))
        self.assertTrue(any("R1 needs a response" in problem for problem in problems), problems)


class RollupTest(unittest.TestCase):
    def test_cost_rolls_up_from_the_leaves_only(self):
        rolled = project_plan.rollup(project_plan.normalise(record()))
        self.assertEqual(rolled["by_node"]["1"], 20000)
        self.assertEqual(rolled["by_node"]["2"], 5000)
        self.assertEqual(rolled["total"], 25000)
        self.assertEqual(rolled["variance"], 0)
        self.assertEqual(rolled["uncosted"], [])

    def test_contingency_is_applied_only_when_declared(self):
        rolled = project_plan.rollup(project_plan.normalise(record()))
        self.assertEqual(rolled["contingency"], 2500)
        self.assertEqual(rolled["with_contingency"], 27500)


class ScheduleTest(unittest.TestCase):
    def test_activity_rows_use_the_frozen_shape(self):
        rows = project_plan.schedule_inputs(project_plan.normalise(record()))
        self.assertEqual(rows["estimate"], "single")
        self.assertEqual([row["id"] for row in rows["activities"]], ["A1", "A2", "A3"])
        self.assertEqual(rows["activities"][1]["predecessors"], "A1")

    def test_the_schedule_runs_through_the_core(self):
        def run(method, inputs):
            self.assertEqual(method, "cpm_schedule")
            return {"project_duration": 12, "es_A1": 0, "ef_A1": 5, "ls_A1": 0, "lf_A1": 5,
                    "float_A1": 0, "critical_A1": 1}
        data = project_plan.normalise(record())
        out = project_plan.schedule(data, run)
        self.assertTrue(out["ok"])
        rows = project_plan.schedule_rows(data, out["result"])
        self.assertEqual(rows[0][0], "A1")
        self.assertEqual(rows[0][-1], "yes")

    def test_a_missing_core_is_a_refusal_not_a_crash(self):
        out = project_plan.schedule(project_plan.normalise(record()), None)
        self.assertFalse(out["ok"])
        self.assertIn("not attached", out["error"])


class GateTest(unittest.TestCase):
    def test_an_incomplete_record_blocks_export_with_the_named_gap(self):
        from bp.product import paper
        data = record()
        data["wbs"][1]["owner"] = ""
        state = {"profile": "project_plan", "plan": {"fields": [], "blocks": []},
                 "answers": {"inputs": {}}, "project": data}
        missing = paper.missing(state)
        self.assertTrue(any("1.1 has no owner" in item for item in missing), missing)


class TableTest(unittest.TestCase):
    def test_a_table_is_a_grid_figure(self):
        figure = project_plan.table("WBS", ["ID", "Name"], [["1", "Design"]])
        self.assertEqual(figure["kind"], "table")
        grid = figure["grids"][0]["rows"]
        self.assertEqual(grid[0][0]["label"], "ID")
        self.assertEqual(grid[1][1]["bullets"], ["Design"])


if __name__ == "__main__":
    unittest.main()
