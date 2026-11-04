import sys, unittest
sys.path.insert(0, "src")
from bp.methods import LIBRARY
from bp import server
from bp.product import subjects


class MethodContractAudit(unittest.TestCase):
    """Every method must carry the full contract a backend caller relies on."""

    def test_every_method_declares_a_complete_contract(self):
        for method_id, method in LIBRARY.items():
            self.assertTrue(method.intended_use, method_id)
            self.assertTrue(method.unsupported_use, method_id)
            self.assertTrue(method.assumptions, method_id)
            self.assertTrue(method.limitations, method_id)
            self.assertTrue(method.test_names, method_id)
            self.assertEqual(len(method.test_names), len(set(method.test_names)), method_id)
            self.assertTrue(method.metric, method_id)
            self.assertTrue(method.unit, method_id)
            self.assertIn(method.tier, ("T1", "T2", "T3", "T4"), method_id)
            self.assertIn(method.claim_ceiling, ("descriptive", "associational", "predictive"), method_id)
            self.assertTrue(method.input_schema, method_id)
            for key, spec in method.input_schema.items():
                self.assertIn("type", spec, (method_id, key))
                self.assertTrue(spec.get("desc"), (method_id, key))

    def test_every_preset_that_names_a_method_points_at_the_library(self):
        from bp import templates
        allowed = set(LIBRARY) | set(templates.TEMPLATES)
        for key, preset in server.PRESETS.items():
            if key == "unsupported":
                continue  # the deliberate negative preset
            if "method" in preset:
                self.assertIn(preset["method"], allowed, key)

    def test_every_subject_tool_is_a_known_calculator_tool(self):
        union = {tool["key"] for tool in subjects.compute_tools()}
        for definition in subjects.SUBJECT_DEFS:
            for key in definition["tools"]:
                self.assertIn(key, union, definition["id"])


if __name__ == "__main__":
    unittest.main()
