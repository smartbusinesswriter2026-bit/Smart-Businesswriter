"""Contract tests for the Home chat orchestration layer.

These tests pin the paper contract, the paper-family registry, the plan IR and
the audit/repair loop. They are structural: they do not run the pipeline and
they do not compute any business number.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import audit, paper_contract, paper_families


class PaperFamilyRegistryTest(unittest.TestCase):
    def test_every_family_has_the_required_fields(self):
        for family in paper_families.families():
            for field in ("id", "label", "genre", "evidence_policy", "computation_policy", "chart_policy", "examples"):
                self.assertIn(field, family)

    def test_every_archetype_has_the_required_fields(self):
        for archetype in paper_families.archetypes():
            for field in ("id", "family", "label", "purpose", "required_sections",
                          "required_blocks", "length_bands", "citation_styles",
                          "rubric_families", "completeness", "status"):
                self.assertIn(field, archetype)

    def test_every_archetype_family_exists(self):
        for archetype in paper_families.archetypes():
            self.assertTrue(paper_families.is_family(archetype["family"]))

    def test_ready_archetypes_are_a_subset(self):
        ready = paper_families.ready_archetypes()
        self.assertTrue(ready)
        for archetype in ready:
            self.assertEqual(archetype["status"], "ready")

    def test_unknown_archetype_is_refused(self):
        self.assertTrue(paper_families.validate_archetype("does_not_exist"))

    def test_unknown_family_is_refused(self):
        self.assertTrue(paper_families.validate_family("does_not_exist"))

    def test_unknown_length_band_is_refused(self):
        self.assertTrue(paper_families.validate_length_band("huge"))

    def test_unknown_citation_style_is_refused(self):
        self.assertTrue(paper_families.validate_citation_style("chicago"))

    def test_analytical_report_has_a_completeness_contract(self):
        self.assertTrue(paper_families.completeness_for("analytical_report"))

    def test_archetypes_for_family_filters(self):
        found = paper_families.archetypes_for_family("analytical_report")
        self.assertTrue(found)
        for archetype in found:
            self.assertEqual(archetype["family"], "analytical_report")


class PaperContractTest(unittest.TestCase):
    def test_make_contract_fills_archetype_defaults(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report")
        self.assertEqual(contract["archetype"], "analytical_report")
        self.assertEqual(contract["family"], "analytical_report")
        self.assertEqual(contract["length"], "mid")
        self.assertEqual(contract["style"], "apa")
        self.assertTrue(contract["required_sections"])
        self.assertTrue(contract["deliverables"])
        self.assertEqual(contract["constraints"], paper_contract.IMMUTABLE_CONSTRAINTS)

    def test_validate_contract_accepts_a_valid_contract(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest", approved=True, approved_at="2026-01-01T00:00:00Z")
        # recompute hash after approval fields are set by freeze
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        self.assertEqual(paper_contract.validate_contract(frozen), [])

    def test_validate_contract_refuses_unknown_archetype(self):
        contract = paper_contract.make_contract("analyse a company", "nope")
        problems = paper_contract.validate_contract(contract)
        self.assertTrue(problems)

    def test_validate_contract_refuses_bad_length(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", length="huge")
        problems = paper_contract.validate_contract(contract)
        self.assertTrue(any("length band" in p for p in problems))

    def test_validate_contract_refuses_bad_style(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", style="chicago")
        problems = paper_contract.validate_contract(contract)
        self.assertTrue(any("citation style" in p for p in problems))

    def test_freeze_contract_requires_validity(self):
        contract = paper_contract.make_contract("analyse a company", "nope")
        with self.assertRaises(ValueError):
            paper_contract.freeze_contract(contract)

    def test_freeze_contract_sets_approved_and_hash(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        self.assertTrue(frozen["approved"])
        self.assertEqual(frozen["approved_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(frozen["hash"], paper_contract.contract_hash(frozen))
        self.assertEqual(paper_contract.validate_contract(frozen), [])

    def test_is_approved_checks_hash(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        self.assertTrue(paper_contract.is_approved(frozen))
        frozen["thesis"]["text"] = "tampered"
        self.assertFalse(paper_contract.is_approved(frozen))

    def test_immutable_constraints_cannot_change(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report")
        contract["constraints"] = {"no_invented_evidence": False}
        problems = paper_contract.validate_contract(contract)
        self.assertTrue(any("constraints" in p for p in problems))

    def test_approved_contract_needs_thesis_and_decision(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", approved=True, approved_at="2026-01-01T00:00:00Z")
        problems = paper_contract.validate_contract(contract)
        self.assertTrue(any("thesis" in p for p in problems))
        self.assertTrue(any("decision" in p for p in problems))


class AuditTest(unittest.TestCase):
    def test_audit_passes_a_clean_paper(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["x" * 700]), ("Context", ["c"]), ("Analysis", ["a"]), ("Synthesis", ["s"]), ("Recommendation", ["r"]), ("Limitations", ["l"]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        report = audit.audit(frozen, plan={"blocks": [{"id": "b1", "kind": "framework", "contribution": "sets context"}]}, draft=draft)
        self.assertTrue(report["passed"])
        self.assertEqual(report["blocking_count"], 0)

    def test_audit_blocks_unapproved_contract(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report")
        report = audit.audit(contract, draft={"sections": [("Introduction", ["x" * 700]), ("Conclusion", ["done"]), ("References", ["a"]) ] })
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "contract_not_approved" for f in report["findings"]))

    def test_audit_blocks_missing_section(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["x" * 700])]}
        report = audit.audit(frozen, draft=draft)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "missing_section" for f in report["findings"]))

    def test_audit_blocks_template_text(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["(your analysis)"]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        report = audit.audit(frozen, draft=draft)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "template_text" for f in report["findings"]))

    def test_audit_blocks_unresolved_claim(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["x" * 700]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        evidence = {"claims": [{"id": "c1", "type": "external", "source_ids": []}]}
        report = audit.audit(frozen, evidence=evidence, draft=draft)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "unresolved_claim" for f in report["findings"]))

    def test_audit_blocks_unresolved_number(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["x" * 700]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        evidence = {"numbers": [{"id": "n1"}]}
        report = audit.audit(frozen, evidence=evidence, draft=draft)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "unresolved_number" for f in report["findings"]))

    def test_audit_blocks_unresolved_chart(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["x" * 700]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        evidence = {"charts": [{"id": "ch1"}]}
        report = audit.audit(frozen, evidence=evidence, draft=draft)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "unresolved_chart" for f in report["findings"]))

    def test_audit_blocks_forbidden_term(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["The PSE index rose"]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        report = audit.audit(frozen, draft=draft, forbidden_terms=["PSE"])
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "forbidden_term" for f in report["findings"]))

    def test_audit_requires_synthesis_for_multiple_analysis_blocks(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        draft = {"sections": [("Introduction", ["x" * 700]), ("Conclusion", ["done"]), ("References", ["a"]) ] }
        plan = {"blocks": [{"id": "b1", "kind": "framework", "contribution": "x"}, {"id": "b2", "kind": "computation", "contribution": "y"}]}
        report = audit.audit(frozen, plan=plan, draft=draft)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "missing_synthesis" for f in report["findings"]))

    def test_repair_suggestions_are_targeted(self):
        report = {"findings": [{"code": "missing_section", "message": "missing required section: X"},
                               {"code": "template_text", "message": "template text found: (your analysis)"}]}
        actions = audit.repair_suggestions(report)
        self.assertEqual(len(actions), 2)
        self.assertTrue(any("missing section" in a for a in actions))

    def test_is_clean(self):
        self.assertTrue(audit.is_clean({"findings": []}))
        self.assertFalse(audit.is_clean({"findings": [{"severity": "blocking", "code": "x"}]}))

    def test_production_check_passes_a_valid_plan(self):
        contract = paper_contract.make_contract("analyse a company", "analytical_report", thesis="The firm is profitable.", decision="Invest")
        frozen = paper_contract.freeze_contract(contract, approved_at="2026-01-01T00:00:00Z")
        plan = {"blocks": [{"id": "b1", "kind": "framework", "ref": "pestel", "role": "analysis", "contribution": "x"}],
                "section_order": ["Introduction", "PESTEL", "Conclusion", "References"]}
        report = audit.production_check(frozen, plan)
        self.assertTrue(report["passed"])

    def test_production_check_blocks_a_cycle(self):
        plan = {"blocks": [{"id": "b1", "kind": "framework", "ref": "pestel", "role": "analysis", "contribution": "x"}],
                "dependencies": [["b1", "b1"]]}
        report = audit.production_check({}, plan)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "dependency_cycle" for f in report["findings"]))

    def test_production_check_blocks_a_chart_without_artifact(self):
        plan = {"blocks": [{"id": "c1", "kind": "chart", "ref": "bar", "role": "visual", "contribution": "x", "spec": {"format": "bp-chart/1", "kind": "bar", "title": "t"}}]}
        report = audit.production_check({}, plan)
        self.assertFalse(report["passed"])
        self.assertTrue(any(f["code"] == "chart_no_artifact" for f in report["findings"]))


if __name__ == "__main__":
    unittest.main()
