import sys, json, os, copy, unittest
sys.path.insert(0, "src")
from bp import registry as R, catalogue_import as CI
from bp.methods import LIBRARY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT = os.path.join(ROOT, "docs", "sources", "Business_Frameworks_and_Quantitative_Methods_Catalogue_v0_2.md")
FIX = json.load(open(os.path.join(ROOT, "tests", "fixtures", "framework_requests.json")))["cases"]

class Import(unittest.TestCase):
    @unittest.skipUnless(os.path.exists(CAT), "catalogue not in docs/sources")
    def test_shipped_registry_equals_fresh_import(self):
        fresh = CI.import_catalogue(CAT); shipped = json.load(open(R.DATA, encoding="utf-8"))
        self.assertEqual(json.loads(json.dumps(fresh, ensure_ascii=False)), shipped)
    @unittest.skipUnless(os.path.exists(CAT), "catalogue not in docs/sources")
    def test_every_catalogue_row_is_present_and_nothing_is_dropped(self):
        import re
        ids = [re.match(r"\|\s*([A-Z]{2,5}-\d+)", l).group(1) for l in open(CAT, encoding="utf-8") if re.match(r"\|\s*[A-Z]{2,5}-\d+\s*\|", l)]
        self.assertEqual(len(ids), 91)
        for i in ids: self.assertEqual(R.get(i)["id"] in ids or i in R.get(i)["also_listed_as"], True, i)
    def test_counts_and_types(self):
        recs = R.load()["records"]; from collections import Counter; c = Counter(r["type"] for r in recs)
        self.assertEqual((len(recs), c["F"], c["M"], c["Q"], c["T"]), (140, 61, 22, 50, 7))
    def test_duplicates_merged_with_both_ids_kept(self):
        self.assertEqual(R.get("IMP-01")["id"], "CHG-07"); self.assertEqual(R.get("IMP-02")["id"], "CHG-08"); self.assertIn("IMP-01", R.get("CHG-07")["also_listed_as"])
        self.assertEqual(len({r["id"] for r in R.load()["records"]}), 140)
    def test_composite_types_split_into_primary_and_secondary(self):
        self.assertEqual((R.get("RSK-09")["type"], R.get("RSK-09")["secondary_types"]), ("F", ["Q"])); self.assertEqual((R.get("MKT-08")["type"], R.get("MKT-08")["secondary_types"]), ("Q", ["M"]))
        self.assertIn("reference", R.get("PM-11")["type_note"])
    def test_nothing_invented_about_evidence(self):
        for r in R.load()["records"]: self.assertEqual((r["evidence_status"], r["pipeline_status"], r["limitations"], r["licensing_review"]), ("unreviewed", "catalogued", [], "not_reviewed"), r["id"])
    def test_standards_flagged_for_edition_and_permission_checks(self):
        for i in ("RSK-01", "OPS-01", "PM-06", "PM-11", "PM-12"): self.assertTrue(R.get(i)["verify_edition_and_permissions"], i)
        self.assertFalse(R.get("STR-01")["verify_edition_and_permissions"])
    def test_validation_passes_and_catches_defects(self):
        self.assertEqual(R.validate(), [])
        bad = copy.deepcopy(R.load()); bad["records"][0]["type"] = "X"; bad["records"][1]["id"] = bad["records"][2]["id"]; bad["records"][3]["evidence_status"] = "great"; bad["records"][4]["pipeline_status"] = "shipped"
        bad["records"][5]["name"] = ""; q = next(r for r in bad["records"] if r["type"] == "Q"); q["linked_methods"] = [{"method_id": "nope", "coverage": "partial", "note": ""}]
        errs = " | ".join(R.validate(bad)); 
        for frag in ("bad type", "duplicate id", "bad evidence_status", "bad pipeline_status", "missing name", "missing method nope"): self.assertIn(frag, errs)
        th = next(r for r in bad["records"] if r["type"] == "T"); th["linked_methods"] = [{"method_id": "npv", "coverage": "partial", "note": ""}]; self.assertIn("cannot link", " | ".join(R.validate(bad)))
    def test_method_links_resolve_to_real_tested_methods_and_state_coverage(self):
        linked = [r for r in R.load()["records"] if r["linked_methods"]]; self.assertGreaterEqual(len(linked), 5)
        for r in linked:
            for l in r["linked_methods"]: self.assertIn(l["method_id"], LIBRARY); self.assertEqual(l["coverage"], "partial"); self.assertTrue(l["note"])
        self.assertTrue(R.get("QNT-STA-03")["implementation_status"].startswith("partial")); self.assertEqual(R.get("QNT-OPS-01")["implementation_status"], "not implemented")
    def test_registry_is_versioned_and_hashed(self):
        reg = R.load(); self.assertEqual(reg["registry_version"], "0.1.0"); self.assertEqual(reg["source"]["catalogue_version"], "0.2"); self.assertEqual(len(reg["hash"]), 64); self.assertEqual(reg["hash"], R.load()["hash"])

class Search(unittest.TestCase):
    def test_name_alias_and_type_filter(self):
        self.assertEqual(R.search("five forces")[0]["id"], "STR-01"); self.assertEqual(R.search("MCDA")[0]["id"], "RSK-09")
        self.assertTrue(all(x["type"] == "T" for x in R.search("motivation", type="T"))); self.assertEqual(R.search(""), []); self.assertEqual(R.search("zzzz qqqq"), [])
    def test_search_is_deterministic(self): self.assertEqual(R.search("customer"), R.search("customer"))

class Recommend(unittest.TestCase):
    def test_tuning_set(self):
        res = R.evaluate([c for c in FIX if c["split"] == "tuning"]); bad = [x for x in res if not x["passed"]]; self.assertEqual(bad, [])
    def test_held_out_set(self):
        res = R.evaluate([c for c in FIX if c["split"] == "held_out"]); bad = [x for x in res if not x["passed"]]; self.assertEqual(bad, [])
    def test_every_suggestion_explains_itself(self):
        for c in FIX:
            r = R.recommend(c["text"])
            for k in ("frameworks", "quantitative", "theories", "named"):
                for x in r[k]:
                    self.assertTrue(x["why"]); self.assertEqual(x["evidence_status"], "unreviewed"); self.assertIn("evidence_needs", x)
                    if k != "named": self.assertTrue(x["matched_terms"] and x["status"] == "suggested")
    def test_minimum_sufficient_set_and_caps(self):
        pol = R.POLICY
        for c in FIX:
            r = R.recommend(c["text"]); self.assertLessEqual(len(r["frameworks"]), pol["max_framework_suggestions"]); self.assertLessEqual(len(r["quantitative"]), pol["max_quant_suggestions"]); self.assertLessEqual(len(r["theories"]), pol["max_theory_suggestions"])
    def test_theories_are_never_offered_as_framework_templates(self):
        for c in FIX:
            r = R.recommend(c["text"]); self.assertTrue(all(x["type"] in ("F", "M") for x in r["frameworks"])); self.assertTrue(all(x["type"] == "Q" for x in r["quantitative"])); self.assertTrue(all(x["type"] == "T" for x in r["theories"]))
        t = R.recommend("Explain Maslow's hierarchy of needs and Herzberg for our staff motivation"); self.assertTrue(any(x["id"] == "THE-02" for x in t["named"] + t["theories"]))
    def test_no_fit_says_so_instead_of_forcing_a_framework(self):
        r = R.recommend("Write a poem about the sea."); self.assertIsNotNone(r["none_reason"]); self.assertEqual((r["frameworks"], r["quantitative"], r["named"]), ([], [], []))
    def test_named_by_user_is_honoured_with_a_fit_note(self):
        r = R.recommend("Use the BCG matrix."); self.assertEqual([x["id"] for x in r["named"]], ["STR-10"]); self.assertIn("nothing else in it clearly points", r["named"][0]["why"])
        r2 = R.recommend("We should use SWOT because we need to weigh internal strengths and weaknesses against external opportunities and threats."); self.assertEqual(r2["named"][0]["why"], "Named in your request.")
    def test_deterministic_and_reports_policy_and_registry(self):
        a = R.recommend(FIX[0]["text"]); b = R.recommend(FIX[0]["text"]); self.assertEqual(a, b); self.assertEqual(a["policy"]["status"], "PROVISIONAL"); self.assertEqual(a["registry"]["hash"], R.load()["hash"])
    def test_fixtures_are_marked_unreviewed_by_experts(self):
        meta = json.load(open(os.path.join(ROOT, "tests", "fixtures", "framework_requests.json"))); self.assertEqual(meta["expert_review"], "pending")

class FrameworkOnly(unittest.TestCase):
    def test_report_says_no_computed_answer_and_lists_evidence_needs(self):
        sel = R.selection_records(["STR-01", "THE-02", "QNT-FIN-01"]); t = R.framework_only_report(sel, "x")
        self.assertTrue(t.startswith("No computed answer is given")); self.assertIn("Evidence and data needed", t); self.assertIn("not as a template", t); self.assertIn("available: npv", t)
        self.assertIn("No framework was selected", R.framework_only_report([], "x"))
    def test_unknown_id_rejected(self):
        with self.assertRaises(KeyError): R.selection_records(["STR-01", "NOPE-99"])
if __name__ == "__main__": unittest.main()
