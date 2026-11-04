import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import unittest
import bp.registry as registry
import bp.product.subjects as subjects
import bp.product.framework_profiles as fp
import bp.templates as templates
import json

class WorksheetRegistrationTests(unittest.TestCase):
    def test_worksheets_valid_template(self):
        for wid, info in subjects.WORKSHEETS.items():
            self.assertIn(info["template"], templates.TEMPLATES)
            # template existence in TEMPLATES? registry uses TEMPLATES; check templates module has it
    def test_worksheets_catalogue_ids_exist(self):
        data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "src", "bp", "data", "registry_v0_2.json")))
        ids = {r["id"] for r in data["records"]}
        for wid, info in subjects.WORKSHEETS.items():
            self.assertIn(info["catalogue_id"], ids)
    def test_new_catalogue_records_exist(self):
        data = json.load(open(os.path.join(os.path.dirname(__file__), "..", "src", "bp", "data", "registry_v0_2.json")))
        ids = {r["id"] for r in data["records"]}
        for cid in ("CHG-15", "STR-19"):
            self.assertIn(cid, ids)
    def test_eight_profiles_exist(self):
        for key in ("bmc", "lean_canvas", "value_proposition_canvas", "project_charter", "wbs", "risk_register", "stakeholder_plan", "lessons_learned"):
            prof = fp.profile_for(key)
            self.assertIsNotNone(prof)
            self.assertIn("unit", prof)
            self.assertIn("voice", prof)
            self.assertIn("notes", prof)
    def test_subject_worksheets_valid(self):
        for d in subjects.SUBJECT_DEFS:
            for wid in (d.get("worksheets") or []):
                self.assertIn(wid, subjects.WORKSHEETS)
    def test_catalogue_consistent(self):
        for cid, row in subjects.CATALOGUE.items():
            if row.get("form") == "worksheet":
                self.assertIn(cid, subjects.WORKSHEETS)
    def test_no_invented_content_spot(self):
        for tid, meta in templates.CANVAS_META.items():
            for field in ("intended_use", "unsupported_use"):
                self.assertNotIn("example data", meta.get(field, "").lower())

if __name__ == "__main__":
    unittest.main()
