import sys, os, json, tempfile, unittest
sys.path.insert(0, "src")
from bp import evaluate
from bp.llm import MockProvider, Models, ProviderError
import bp.assist as assist

CASE = {"id": "demo", "case_text": "The shop faces a new competitor.\nThe owner has cash reserves.", "objective": "What should the shop do?",
        "gold_facts": ["The shop faces a new competitor.", "The owner has cash reserves."],
        "gold_alternatives": ["expand", "cater"], "gold_critique": [{"category": "missing_information", "target": "case"}]}

def script(system, user):
    if "extract facts" in system:
        body = user.split("<case>", 1)[1].rsplit("</case>", 1)[0]
        return json.dumps({"facts": [{"quote": ln.strip()} for ln in body.strip().splitlines() if ln.strip()]})
    if "propose between" in system:
        return json.dumps({"alternatives": [{"name": "Expand seating", "description": "expand the shop", "supports": ["F1"]},
                                            {"name": "Cater to offices", "description": "cater lunches", "supports": ["F2"]}]})
    return json.dumps({"critique": [{"category": "missing_information", "target": "case", "text": "No competitor detail"}]})

class Scores(unittest.TestCase):
    def test_fact_scores(self):
        p = [{"text": CASE["gold_facts"][0]}]
        self.assertEqual(evaluate.score_facts(p, CASE["gold_facts"])["f1"], 0.6667)
        self.assertEqual(evaluate.score_facts([{"text": q} for q in CASE["gold_facts"]], CASE["gold_facts"])["f1"], 1.0)
        self.assertEqual(evaluate.score_facts([], CASE["gold_facts"]), {"precision": 0.0, "recall": 0.0, "f1": 0.0, "matched": 0, "proposed": 0, "gold": 2})
    def test_alternative_and_critique_coverage(self):
        alts = [{"name": "Expand seating", "description": "expand the shop"}, {"name": "Cater", "description": "cater lunches"}]
        self.assertEqual(evaluate.score_alternatives(alts, ["expand", "cater"])["coverage"], 1.0)
        self.assertEqual(evaluate.score_alternatives(alts, ["expand", "price"])["coverage"], 0.5)
        self.assertEqual(evaluate.score_critique([{"category": "missing_information", "target": "case"}], CASE["gold_critique"])["coverage"], 1.0)

class Harness(unittest.TestCase):
    def test_perfect_scripted_run(self):
        row = evaluate.run_case(Models(MockProvider(script)), CASE)
        self.assertEqual(row["facts"]["f1"], 1.0); self.assertEqual(row["alternatives"]["coverage"], 1.0); self.assertEqual(row["critique"]["coverage"], 1.0)
        out = evaluate.evaluate(Models(MockProvider(script)), [CASE]); self.assertEqual((out["summary"]["cases"], out["summary"]["facts_mean_f1"]), (1, 1.0))
    def test_invalid_model_output_is_reported_not_raised(self):
        row = evaluate.run_case(Models(MockProvider(lambda s, u: "not json")), CASE)
        self.assertIn("error", row["facts"]); self.assertIn("skipped", row["alternatives"]); self.assertIn("skipped", row["critique"])
    def test_provider_error_is_reported_not_raised(self):
        row = evaluate.run_case(Models(MockProvider(lambda s, u: ProviderError("provider returned HTTP 500"))), CASE)
        self.assertIn("error", row["facts"])
    def test_load_cases_fixture_and_validation(self):
        path = os.path.join("tests", "fixtures", "eval_cases.json"); cases = evaluate.load_cases(path)
        self.assertEqual([c["id"] for c in cases], ["bakery-competition", "software-pricing"])
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f: json.dump([{"id": "x"}], f); bad = f.name
        try:
            with self.assertRaises(ValueError): evaluate.load_cases(bad)
        finally: os.unlink(bad)
if __name__ == "__main__": unittest.main()
