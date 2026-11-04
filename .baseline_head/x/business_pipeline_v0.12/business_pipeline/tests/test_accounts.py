import sys, os, copy, unittest
from decimal import Decimal as D
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))
from bp import accounts, ledger
from bp.orchestrator import Pipeline

yes = lambda s: True
SPEC = {
    "period": {"start": "2026-01-01", "end": "2026-12-31"}, "currency": "USD", "framework": "local", "places": 2,
    "chart": [{"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "role": "cash"},
              {"code": "1500", "name": "Equipment", "type": "asset", "line": "Equipment"},
              {"code": "1510", "name": "Accumulated depreciation", "type": "asset", "line": "Equipment", "contra": True},
              {"code": "2000", "name": "Loan", "type": "liability", "line": "Loans"},
              {"code": "3000", "name": "Owner capital", "type": "equity", "line": "Capital", "role": "capital"},
              {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
              {"code": "3200", "name": "Dividends", "type": "equity", "line": "Dividends", "role": "dividends"},
              {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
              {"code": "5000", "name": "Rent", "type": "expense", "line": "Rent"},
              {"code": "5100", "name": "Depreciation", "type": "expense", "line": "Depreciation"}],
    "prior_closing": {"1000": "5000", "1500": "1200", "3000": "6200"},
    "opening": [{"lines": [{"account": "1000", "debit": "5000"}, {"account": "1500", "debit": "1200"}, {"account": "3000", "credit": "6200"}]}],
    "entries": [{"date": "2026-01-15", "description": "sale", "lines": [{"account": "1000", "debit": "2000"}, {"account": "4000", "credit": "2000"}]},
                {"date": "2026-03-31", "description": "rent", "lines": [{"account": "5000", "debit": "500"}, {"account": "1000", "credit": "500"}]},
                {"date": "2026-06-30", "description": "dividend", "lines": [{"account": "3200", "debit": "300"}, {"account": "1000", "credit": "300"}]}],
    "schedules": [{"kind": "depreciation", "cost": "1200", "residual": "0", "life": 12, "start": "2026-01", "dep_account": "5100", "accum_account": "1510"}],
}
def req(spec=SPEC, **kw):
    r = {"objective": "Prepare the management accounts.", "method": "management_accounts", "currency": "USD", "inputs": {"spec": spec}}; r.update(kw); return r

class Build(unittest.TestCase):
    def test_hand_checked_engagement(self):
        out = accounts.build(SPEC)
        self.assertEqual((out["net_income"], out["total_assets"], out["total_liabilities"], out["total_equity"]), (D(300), D(6200), D(0), D(6200)))
        self.assertEqual((out["retained_earnings_closing"], out["cash_net"]), (D(0), D(1200)))
        self.assertEqual((out["n_entries"], out["checks_passed"], out["checks_total"], out["checks_na"], out["n_flags"]), (D(19), D(9), D(11), D(2), D(0)))
        self.assertTrue(all(ok for _, ok, _ in out["_checks"]))
        self.assertNotIn("reconciliation", out["_appendix"])
        ap = out["_appendix"]; self.assertEqual(ap["statements"]["income"], {}); self.assertEqual(ap["statements"]["expenses"], {})   # closed
        self.assertIn("closing: income to retained earnings", ap["export"]); self.assertEqual(ap["closing_balances"]["3100"], "0.00")
        self.assertEqual(ap["framework"], "local")
    def test_deterministic(self):
        a, b = accounts.build(SPEC), accounts.build(SPEC)
        self.assertEqual(a["_appendix"]["export"], b["_appendix"]["export"]); self.assertEqual({k: str(v) for k, v in a.items() if k not in ("_appendix", "_checks")}, {k: str(v) for k, v in b.items() if k not in ("_appendix", "_checks")})
    def test_prior_closing_mismatch_fails_the_check(self):
        bad = copy.deepcopy(SPEC); bad["prior_closing"]["1000"] = "5001"
        out = accounts.build(bad); checks = {n: (ok, d) for n, ok, d in out["_checks"]}
        self.assertFalse(checks["opening_balances_equal_prior_closing"][0]); self.assertEqual(out["checks_passed"], D(8))

class RatioSelection(unittest.TestCase):
    """B-203: the ratio inputs are selected from figures the core computed, never summed by a caller."""
    def classified(self, drop_section=None):
        s = copy.deepcopy(SPEC)
        s["chart"][0]["section"] = "current"          # Cash
        s["chart"][1]["section"] = "non_current"      # Equipment
        s["chart"][2]["section"] = "non_current"      # Accumulated depreciation
        if drop_section is not None: s["chart"][drop_section].pop("section")
        return s
    def test_the_grouping_published_is_the_cores_own(self):
        ap = accounts.build(SPEC)["_appendix"]
        self.assertEqual(ap["balance_sheet_groups"]["totals"]["equity"], ap["statements"]["equity_with_current_earnings"])
        self.assertEqual(ap["ratio_figures"]["total_assets"], ap["statements"]["total_assets"])
        self.assertEqual(D(ap["ratio_figures"]["cash"]), D(6200))
        self.assertEqual(D(ap["ratio_figures"]["revenue"]), D(2000))
        self.assertEqual(D(ap["ratio_figures"]["net_income"]), D(300))
    def test_every_published_figure_is_an_input_the_ratio_method_declares(self):
        from bp import methods
        figs = accounts.build(self.classified())["_appendix"]["ratio_figures"]
        self.assertTrue(set(figs) <= set(methods.LIBRARY["ratio_analysis"].input_schema), sorted(set(figs) - set(methods.LIBRARY["ratio_analysis"].input_schema)))
        self.assertEqual(methods.validate_inputs(methods.LIBRARY["ratio_analysis"], figs), [])
        self.assertEqual(methods.LIBRARY["ratio_analysis"].impl(figs)["n_computed"], D(6))
    def test_a_fully_classified_balance_sheet_publishes_the_current_totals(self):
        ap = accounts.build(self.classified())["_appendix"]
        self.assertEqual(D(ap["ratio_figures"]["current_assets"]), D(6200))
        self.assertEqual(D(ap["ratio_figures"]["current_liabilities"]), D(0))
    def test_a_line_left_unclassified_omits_the_total_rather_than_understating_it(self):
        ap = accounts.build(self.classified(drop_section=2))["_appendix"]
        self.assertNotIn("current_assets", ap["ratio_figures"])
        # both accounts share the statement line "Equipment", so the line is what is unclassified
        self.assertEqual(ap["balance_sheet_groups"]["groups"]["unclassified_assets"], {"Equipment": "-1200.00"})
    def test_an_unclassified_chart_publishes_no_current_total_at_all(self):
        figs = accounts.build(SPEC)["_appendix"]["ratio_figures"]
        self.assertNotIn("current_assets", figs)
        self.assertNotIn("current_liabilities", figs)
        from bp import methods
        reasons = {r["ratio"]: r["reason"] for r in methods.LIBRARY["ratio_analysis"].impl(figs)["_appendix"]["not_computed"]}
        self.assertIn("current_assets", reasons["current_ratio"])
    def test_a_figure_the_statements_cannot_support_is_named_not_estimated(self):
        from bp import methods
        figs = accounts.build(SPEC)["_appendix"]["ratio_figures"]
        self.assertNotIn("receivables", figs); self.assertNotIn("inventory", figs)
        reasons = {r["ratio"]: r["reason"] for r in methods.LIBRARY["ratio_analysis"].impl(figs)["_appendix"]["not_computed"]}
        self.assertIn("receivables", reasons["receivables_days"])
        self.assertIn("inventory", reasons["inventory_days"])
    def test_no_gap_names_a_ratio_the_registry_can_already_compute(self):
        from bp import methods
        overlap = {r[0] for r in methods._RATIOS} & {g["ratio"] for g in accounts.RATIO_GAPS}
        self.assertEqual(sorted(overlap), [], "a ratio listed as a gap is in fact computed by the registry")
        for gap in accounts.RATIO_GAPS:
            self.assertTrue(gap["needs"], gap); self.assertTrue(gap["why"], gap)
    def test_the_selection_is_deterministic(self):
        a, b = accounts.build(self.classified()), accounts.build(self.classified())
        self.assertEqual(a["_appendix"]["ratio_figures"], b["_appendix"]["ratio_figures"])
        self.assertEqual(a["_appendix"]["balance_sheet_groups"], b["_appendix"]["balance_sheet_groups"])


class Validation(unittest.TestCase):
    def errs(self, mut):
        s = copy.deepcopy(SPEC); mut(s); return " ".join(accounts.validate_spec(s))
    def test_traps(self):
        self.assertIn("reporting framework", self.errs(lambda s: s.pop("framework")))
        self.assertIn("start <= end", self.errs(lambda s: s["period"].update(start="2027-01-01")))
        self.assertIn("does not balance", self.errs(lambda s: s["entries"][0]["lines"][1].update(credit="1999")))
        self.assertIn("unknown account", self.errs(lambda s: s["entries"][0]["lines"][0].update(account="9999")))
        self.assertIn("binary float", self.errs(lambda s: s["entries"][0]["lines"][0].update(debit=10.0)))
        self.assertIn("retained earnings account", self.errs(lambda s: s["chart"].pop(5)))
        self.assertIn("cost must be positive", self.errs(lambda s: s["schedules"][0].update(cost="0")))
        self.assertIn("prior_closing must be", self.errs(lambda s: s.update(prior_closing=[])))
        self.assertIn("duplicate account code", self.errs(lambda s: s["chart"].append({"code": "1000", "name": "Cash2", "type": "asset", "line": "Cash"})))
    def test_entry_outside_the_period_blocks(self):
        bad = copy.deepcopy(SPEC); bad["entries"].append({"date": "2027-01-05", "description": "late", "lines": [{"account": "1000", "debit": "10"}, {"account": "4000", "credit": "10"}]})
        errs = accounts.validate_spec(bad); self.assertEqual(errs, [])            # schema-level validation passes
        d = Pipeline().run(req(bad), yes); self.assertEqual(d.status, "blocked"); self.assertIn("outside the period", d.blocked_reason)

class PipelineFlow(unittest.TestCase):
    def test_end_to_end_delivery(self):
        p = Pipeline(); d = p.run(req(SPEC), yes)
        self.assertEqual(d.status, "delivered", d.blocked_reason); self.assertEqual(d.tier, "T2")
        for frag in ("posts 19 entries", "Net income is USD 300.00", "total assets are USD 6,200.00", "equity of USD 6,200.00",
                     "Closing retained earnings are USD 0.00", "net change in cash of USD 1,200.00",
                     "9 of 11 checks passed (2 not applicable), with 0 item(s) flagged", "not GAAP or IFRS", "expert review pending", "reconciliation supplied"): self.assertIn(frag, d.report)
        self.assertNotIn("{{", d.report)
        ap = d.appendix["accounts"]; self.assertIn("closing: income to retained earnings", ap["export"]); self.assertEqual(ap["checks"][0][1], True)
        se = ap["statements_export"]
        for k in ("trial_balance", "income_statement", "balance_sheet", "cash_flow", "notes", "combined"): self.assertIn(k, se)
        self.assertIn("Net income", se["income_statement"]); self.assertIn("TRIAL BALANCE", se["trial_balance"]); self.assertIn("TOTAL" if False else "Total assets", se["balance_sheet"])
        self.assertEqual(d.appendix["method"]["review_status"], "pending_named_reviewer")
        a = {x.id: x for x in p.store.all()}; self.assertEqual((a["net_income"].value.unit, a["net_income"].value.currency), ("currency", "USD")); self.assertEqual(a["checks_passed"].value.unit, "count")
    def test_bad_spec_blocks_with_reason(self):
        bad = copy.deepcopy(SPEC); bad.pop("framework")
        d = Pipeline().run(req(bad), yes); self.assertEqual(d.status, "blocked"); self.assertIn("reporting framework", d.blocked_reason)
    def test_prior_closing_mismatch_blocks_at_verification(self):
        bad = copy.deepcopy(SPEC); bad["prior_closing"]["1000"] = "5001"
        d = Pipeline().run(req(bad), yes); self.assertEqual(d.status, "blocked"); self.assertIn("opening_balances_equal_prior_closing", d.blocked_reason)
    def test_plan_shows_t2(self):
        from bp.session import SessionManager
        s = SessionManager().create(req()); self.assertEqual(s.plan["task_family"], "Quantitative business analysis"); self.assertEqual(s.plan["tier"], "T2"); self.assertIn("custom analysis (T2)", s.plan["tier_label"])
        self.assertEqual(len(s.plan["planned_checks"]), 11)
    def test_sandbox_path_matches_in_process(self):
        from bp.sandbox import SubprocessSandbox
        d1 = Pipeline().run(req(SPEC), yes); d2 = Pipeline(sandbox=SubprocessSandbox(timeout=60)).run(req(SPEC), yes)
        self.assertEqual((d1.status, d2.status), ("delivered", "delivered")); self.assertEqual(d1.report, d2.report)
        self.assertEqual(d1.appendix["accounts"]["export"], d2.appendix["accounts"]["export"]); self.assertIsInstance(d2.appendix["sandbox"], dict)
    def test_example_spec_builds_with_reconciliation(self):
        out = accounts.build(accounts.EXAMPLE_SPEC); self.assertTrue(all(ok for _, ok, _ in out["_checks"]))
        self.assertEqual(accounts.validate_spec(accounts.EXAMPLE_SPEC), [])
        self.assertEqual((out["checks_passed"], out["checks_total"], out["checks_na"], out["n_entries"]), (D(11), D(11), D(0), D(6)))
        rp = out["_appendix"]["reconciliation"]; self.assertEqual((rp["difference"], rp["receipts_in_transit"], rp["unrecorded_payments"]), ("0", "150", "25"))
        self.assertEqual(out["_appendix"]["statements"]["equity"]["Capital"], "5000"); self.assertEqual(out["total_assets"], D(6650))
    def test_reconciliation_block_is_validated(self):
        bad = copy.deepcopy(SPEC); bad["reconciliation"] = {"account": "9999", "statement": {"opening_balance": "1", "closing_balance": "1", "lines": []}}
        self.assertIn("not in the chart", " ".join(accounts.validate_spec(bad)))
        bad["reconciliation"] = {"account": "1000", "statement": {"opening_balance": "1", "closing_balance": "1", "lines": [{"amount": "1", "direction": "up"}]}}
        self.assertIn("direction", " ".join(accounts.validate_spec(bad)))
class MappingCheckpoint(unittest.TestCase):
    def test_mapping_table_and_checks(self):
        mp = accounts.account_mapping(SPEC)
        self.assertEqual(len(mp["rows"]), 10); self.assertEqual((mp["rows"][0]["code"], mp["rows"][0]["role"]), ("1000", "cash"))
        self.assertEqual([c[0] for c in mp["checks"]], ["every_account_maps_to_a_statement_line", "at_least_one_cash_account", "exactly_one_retained_earnings_account"])
        self.assertTrue(all(ok for _, ok, _ in mp["checks"]))
        self.assertEqual(mp["framework"], "local")
    def test_mapping_checks_catch_problems(self):
        bad = copy.deepcopy(SPEC); bad["chart"][0]["line"] = ""
        self.assertFalse({n: ok for n, ok, _ in accounts.account_mapping(bad)["checks"]}["every_account_maps_to_a_statement_line"])
        bad = copy.deepcopy(SPEC); bad["chart"].append({"code": "3110", "name": "Retained earnings 2", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"})
        self.assertFalse({n: ok for n, ok, _ in accounts.account_mapping(bad)["checks"]}["exactly_one_retained_earnings_account"])
        bad = copy.deepcopy(SPEC)
        for a in bad["chart"]:
            if a["code"] == "1000": a.pop("role")
        self.assertFalse({n: ok for n, ok, _ in accounts.account_mapping(bad)["checks"]}["at_least_one_cash_account"])
    def test_session_pauses_for_the_mapping_and_resumes(self):
        from bp.session import SessionManager
        s = SessionManager().create(req(SPEC))
        self.assertEqual(s.status, "awaiting_confirmation")
        s.confirm(True)
        self.assertEqual(s.status, "awaiting_mapping_confirmation")
        d = s.to_dict(); self.assertEqual(len(d["account_mapping"]["rows"]), 10); self.assertIsNone(d["delivery"])
        self.assertEqual(d["stage_states"]["formalization"], "awaiting_user"); self.assertEqual(d["stage_states"]["execution"], "planned")
        events = [e for e in d["events"] if e.get("checkpoint") == "account_mapping"]
        self.assertEqual(len(events), 1); self.assertEqual(events[0]["status"], "awaiting_confirmation")
        s.confirm(True)
        self.assertEqual(s.status, "delivered"); d = s.to_dict()
        self.assertEqual(d["stage_states"]["formalization"], "passed"); self.assertIn("9 of 11 checks passed (2 not applicable)", d["delivery"]["report"])
        with self.assertRaises(ValueError): s.confirm(True)
    def test_rejecting_the_mapping_blocks(self):
        from bp.session import SessionManager
        s = SessionManager().create(req(SPEC)); s.confirm(True); s.confirm(False)
        self.assertEqual(s.status, "blocked"); self.assertIn("account mapping", s.to_dict()["delivery"]["blocked_reason"])
    def test_non_mapping_method_keeps_a_single_checkpoint(self):
        from bp.orchestrator import Pipeline
        d = Pipeline().run({"objective": "x", "method": "npv", "currency": "USD", "inputs": {"rate": "0.10", "cashflows": ["-1000", "400"]}}, yes)
        self.assertEqual(d.status, "delivered")

class PolicyChanges(unittest.TestCase):
    def test_declared_change_is_applied_prospectively_and_disclosed(self):
        spec = copy.deepcopy(SPEC)
        spec["policy_changes"] = [{"date": "2026-07-01", "kind": "useful_life_revision", "schedule": 0, "life": 10,
                                   "description": "useful life revised from 12 to 10 periods", "treatment": "prospective"}]
        self.assertEqual(accounts.validate_spec(spec), [])
        out = accounts.build(spec)
        self.assertEqual(out["n_entries"], D(17))          # 1 opening + 3 entries + 10 depreciation + 3 closing
        self.assertTrue(all(ok for _, ok, _ in out["_checks"]))
        notes = out["_appendix"]["policy_changes"]; self.assertEqual(len(notes), 1)
        self.assertEqual((notes[0]["treatment"], notes[0]["applied_prospectively"]), ("prospective", True))
        self.assertEqual(out["_appendix"]["export"].count("depreciation"), 10)   # total unchanged, spread over fewer periods (post-closing statements carry no expense lines)
        self.assertIn("Any declared policy change is listed in the appendix", Pipeline().run(req(spec), yes).report)
    def test_disclosure_only_change_has_no_computation_effect(self):
        spec = copy.deepcopy(SPEC)
        spec["policy_changes"] = [{"date": "2026-02-01", "kind": "disclosure", "description": "reclassification of rent", "treatment": "prospective"}]
        self.assertEqual(accounts.validate_spec(spec), []); out = accounts.build(spec)
        self.assertEqual(out["n_entries"], D(19)); self.assertFalse(out["_appendix"]["policy_changes"][0]["applied_prospectively"])
    def test_validation_traps(self):
        cases = (
            (lambda s: s.update(policy_changes=[{"date": "2027-01-01", "kind": "disclosure", "description": "x", "treatment": "prospective"}]), "outside the period"),
            (lambda s: s.update(policy_changes=[{"kind": "disclosure", "description": "x", "treatment": "prospective"}]), "date must be"),
            (lambda s: s.update(policy_changes=[{"date": "2026-02-01", "kind": "disclosure", "treatment": "prospective"}]), "description is required"),
            (lambda s: s.update(policy_changes=[{"date": "2026-02-01", "kind": "other", "description": "x", "treatment": "prospective"}]), "kind must be"),
            (lambda s: s.update(policy_changes=[{"date": "2026-07-01", "kind": "useful_life_revision", "schedule": 3, "life": 10, "description": "x", "treatment": "prospective"}]), "schedule must be"),
            (lambda s: s.update(policy_changes=[{"date": "2026-02-01", "kind": "disclosure", "description": "x", "treatment": "retrospective"}]), "retrospective"),
        )
        for mut, frag in cases:
            s = copy.deepcopy(SPEC); mut(s); self.assertIn(frag, " ".join(accounts.validate_spec(s)), frag)
    def test_impossible_change_blocks_the_pipeline(self):
        spec = copy.deepcopy(SPEC)
        spec["policy_changes"] = [{"date": "2026-07-01", "kind": "useful_life_revision", "schedule": 0, "life": 6,
                                   "description": "x", "treatment": "prospective"}]
        d = Pipeline().run(req(spec), yes); self.assertEqual(d.status, "blocked"); self.assertIn("policy change", d.blocked_reason)

if __name__ == "__main__": unittest.main()
