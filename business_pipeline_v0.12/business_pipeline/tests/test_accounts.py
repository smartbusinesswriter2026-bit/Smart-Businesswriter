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

if __name__ == "__main__": unittest.main()
