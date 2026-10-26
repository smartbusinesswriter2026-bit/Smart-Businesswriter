"""Minimal JSON API + static shell (stdlib only; FastAPI can replace this later behind the same routes)."""
import json, os, re, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from decimal import Decimal
from .session import SessionManager
from urllib.parse import urlparse, parse_qs
import uuid
from . import methods, registry, templates, assist, llm, literature, accounts, ingest, currency
from .product import api as product_api, ops as product_ops
from .sandbox import SubprocessSandbox

ASSIST_RUNS = {}
M = SessionManager(assist_runs=ASSIST_RUNS)
MODELS = None            # llm.Models or None (model assistance off)
SANDBOX_ENABLED = True   # set by serve(); reported by /api/health
LITERATURE_SOURCES = {"crossref": literature.CrossrefSource(), "openalex": literature.OpenAlexSource()}
LITERATURE_AUTO = ("crossref", "openalex")   # declared priority order (B-064): Crossref first, OpenAlex fallback
LITERATURE_LABELS = {"crossref": "Crossref", "openalex": "OpenAlex", "auto": "Auto (Crossref, then OpenAlex)"}
LITERATURE_CALLS = 0
LITERATURE_CAP = 100     # per server run; the public APIs are free, but this stops a runaway loop
LITERATURE_LOG = os.environ.get("BP_RETRIEVAL_LOG") or "retrieval_log.jsonl"   # durable retrieval audit; "" disables it
LITERATURE_NOTICE = ("The title and DOI you enter are sent to the selected public bibliographic API (Crossref or OpenAlex) "
                     "to look the reference up. No case text is sent. A citation is marked verified only when the DOI resolves "
                     "and the title matches exactly. Every resolved retrieval is recorded in the local retrieval log (source, "
                     "UTC time, SHA-256 of the response bytes) so a citation can be re-checked later.")
WEB = os.path.join(os.path.dirname(__file__), "..", "..", "web")
MAXBODY = 100_000
INGEST_MAXBODY = 7_500_000   # base64 of the 5 MB ingestion limit, plus JSON overhead
PRESETS = {
    "npv": {"objective": "Should we invest in this project?", "method": "npv", "currency": "USD", "period": "annual",
           "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}, "sensitivity": {"rate": ["0.05", "0.25"]}},
    "irr": {"objective": "What rate of return does the project earn?", "method": "irr", "period": "annual",
            "inputs": {"cashflows": ["-1000", "400", "400", "400", "400"]}},
    "dpayback": {"objective": "How long until the discounted cash flows repay the investment?", "method": "discounted_payback", "currency": "USD", "period": "annual",
                 "inputs": {"cashflows": ["-1000", "400", "400", "400", "400"], "rate": "0.10"}},
    "breakeven": {"objective": "How many units must we sell to break even?", "method": "breakeven", "period": "annual",
                  "inputs": {"fixed": "1000", "price": "20", "variable": "10"}},
    "descriptive": {"objective": "Describe the exam scores", "method": "descriptive_stats", "unit": "points",
                    "inputs": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"]}},
    "pearson": {"objective": "Is study time associated with exam score?", "method": "pearson",
                "inputs": {"x": ["1", "2", "3", "4", "5", "6", "7", "8"], "y": ["52", "55", "61", "58", "70", "72", "69", "80"], "missing_codes": []}},
    "ols": {"objective": "How are study hours and sleep associated with exam score?", "method": "ols",
            "inputs": {"y": ["52", "55", "61", "58", "70", "72", "69", "80", "66", "74"],
                       "predictors": {"study_hours": ["1", "2", "3", "4", "5", "6", "7", "8", "4", "6"], "sleep_hours": ["6", "7", "5", "8", "6", "7", "8", "6", "7", "7"]}, "missing_codes": []}},
    "welch": {"objective": "Do the two teaching methods differ in exam scores?", "method": "welch_t", "unit": "points",
              "inputs": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"]}, "missing_codes": []}},
    "anova": {"objective": "Do the three teaching formats differ in exam scores?", "method": "anova", "unit": "points",
              "inputs": {"groups": {"lecture": ["62", "70", "68", "75", "66", "71", "64", "73"], "workshop": ["72", "78", "74", "85", "80", "77", "69", "83", "79"], "online": ["60", "63", "58", "66", "61", "65", "60"]}, "missing_codes": []}},
    "chi_square": {"objective": "Is the outcome category associated with the treatment group?", "method": "chi_square",
                   "inputs": {"table": [[45, 30, 25], [20, 40, 40], [10, 20, 70]]}},
    "forecast": {"objective": "Forecast the next three periods", "method": "trend_forecast", "unit": "units",
                 "inputs": {"values": ["10", "12", "11", "14", "13", "16", "15", "18", "17", "20", "19", "22"], "missing_codes": [], "horizon": "3"}},
    "ratios": {"objective": "Compute the key ratios from our financial statements", "method": "ratio_analysis", "period": "annual",
               "inputs": {"current_assets": "5000", "current_liabilities": "2000", "cash": "800", "inventory": "1200", "receivables": "1500",
                          "payables": "900", "total_assets": "12000", "total_liabilities": "7000", "equity": "5000", "revenue": "20000",
                          "cost_of_sales": "12000", "operating_profit": "3000", "net_income": "1800", "interest_expense": "400"}},
    "paired": {"objective": "Did the scores change after the intervention?", "method": "paired_t", "unit": "points", "period": "cross_section",
               "inputs": {"pairs": {"before": ["10", "12", "11", "9", "13"], "after": ["12", "13", "12", "10", "14"]}}},
    "onesample": {"objective": "Is the mean different from the target?", "method": "one_sample_t", "unit": "points", "period": "cross_section",
                  "inputs": {"values": ["72", "85", "90", "68", "99", "77", "81"], "missing_codes": ["99"], "mu0": "75"}},
    "wacc": {"objective": "What is our weighted average cost of capital?", "method": "wacc", "period": "annual",
             "inputs": {"equity_value": "800000", "debt_value": "200000", "cost_of_equity": "0.12", "cost_of_debt_after_tax": "0.05"}},
    "dcf": {"objective": "Value the project from its free cash flows", "method": "dcf_valuation", "currency": "USD", "period": "annual",
            "inputs": {"cashflows": ["100000", "120000", "140000", "155000"], "discount_rate": "0.10", "terminal_growth": "0.02"}},
    "dcfmid": {"objective": "Value the project with mid-year cash flows", "method": "dcf_valuation", "currency": "USD", "period": "annual",
               "inputs": {"cashflows": ["100000", "120000", "140000", "155000"], "discount_rate": "0.10", "terminal_growth": "0.02", "timing": "mid"}},
    "equitybridge": {"objective": "What is the equity value after net debt and other claims?", "method": "equity_bridge", "currency": "USD", "period": "annual",
                     "inputs": {"enterprise_value": "1750939.14", "debt": "300000", "cash": "150000", "minority_interest": "20000",
                                "preferred_equity": "10000", "shares_outstanding": "100000"}},
    "currency": {"objective": "Convert a USD amount to EUR at a declared rate", "method": "currency_convert", "currency": "EUR", "period": "cross_section",
                 "inputs": {"amount": "1000", "from_currency": "USD", "to_currency": "EUR", "rate": "0.92", "rate_provenance": "user", "rate_date": "2026-10-20"}},
    "logit": {"objective": "What predicts the binary outcome?", "method": "logistic_regression", "period": "cross_section",
              "inputs": {"y": ["0", "0", "0", "1", "0", "1", "1", "1", "1", "1", "1", "1", "0", "1", "1", "0", "1", "0", "0", "1", "0", "0", "0", "1", "1", "0", "0", "1", "1", "0", "1", "1", "1", "1", "0", "1", "1", "1", "1", "0"], "predictors": {"size": ["-1.72", "-0.26", "-0.74", "-0.01", "0.2", "-0.72", "-0.74", "-0.28", "-0.8", "1.32", "0.48", "1.3", "-1.0", "-0.02", "0.62", "0.8", "3.11", "-0.84", "-0.01", "0.17", "-0.15", "0.42", "-0.17", "-0.96", "0.79", "-0.95", "-1.79", "-0.16", "0.26", "0.47", "2.23", "0.64", "0.92", "0.22", "0.89", "-0.08", "2.05", "1.76", "0.01", "0.15"], "group": ["0", "0", "0", "0", "1", "0", "0", "0", "1", "1", "1", "0", "0", "1", "1", "0", "1", "0", "0", "1", "0", "0", "1", "1", "0", "0", "0", "0", "1", "0", "0", "0", "0", "0", "1", "1", "1", "0", "1", "1"]}}},
    "alpha": {"objective": "Are the survey items internally consistent?", "method": "reliability_alpha", "unit": "points", "period": "cross_section",
              "inputs": {"items": {"one": ["4", "5", "3", "4", "5", "2", "4", "3"], "two": ["4", "4", "3", "5", "4", "3", "4", "2"], "three": ["3", "4", "2", "4", "5", "3", "4", "3"], "four": ["4", "5", "3", "4", "4", "2", "3", "3"]}}},
    "cba": {"objective": "Appraise the programme costs against its benefits", "method": "cost_benefit", "currency": "USD", "period": "annual",
            "inputs": {"costs": ["50000", "10000", "10000"], "benefits": ["20000", "30000", "40000"], "discount_rate": "0.05"}},
    "cea": {"objective": "Which option gives more effect per unit of cost?", "method": "cost_effectiveness", "currency": "USD", "period": "annual",
            "inputs": {"options": [{"name": "basic", "cost": "10000", "effect": "40"}, {"name": "intensive", "cost": "18000", "effect": "60"}]}},
    "sroi": {"objective": "What is the social return on the investment?", "method": "sroi", "currency": "USD", "period": "annual",
             "inputs": {"investment": "60000", "benefits": ["20000", "25000", "30000"], "discount_rate": "0.04"}},
    "unitecon": {"objective": "What does a customer cost and return?", "method": "unit_economics", "currency": "USD", "period": "annual",
                 "inputs": {"price": "49", "variable_cost": "12", "acquisition_cost": "80", "churn_rate": "0.04"}},
    "multibreakeven": {"objective": "How many units must the product mix sell to break even?", "method": "multi_product_breakeven", "currency": "USD", "period": "annual",
                       "inputs": {"fixed_costs": "6000", "products": [{"name": "coffee", "price": "5", "variable_cost": "2", "mix_units": "3"}, {"name": "cake", "price": "6", "variable_cost": "3", "mix_units": "1"}]}},
    "factorial": {"objective": "Do the two factors and their interaction matter?", "method": "two_way_anova", "unit": "points", "period": "cross_section",
                  "inputs": {"data": [{"response": "1", "factor_a": "low", "factor_b": "x"}, {"response": "3", "factor_a": "low", "factor_b": "x"}, {"response": "5", "factor_a": "low", "factor_b": "y"}, {"response": "7", "factor_a": "low", "factor_b": "y"}, {"response": "3", "factor_a": "high", "factor_b": "x"}, {"response": "5", "factor_a": "high", "factor_b": "x"}, {"response": "7", "factor_a": "high", "factor_b": "y"}, {"response": "9", "factor_a": "high", "factor_b": "y"}]}},
    "posthoc": {"objective": "Which groups differ from which?", "method": "posthoc_pairwise", "unit": "points", "period": "cross_section",
                "inputs": {"groups": {"a": ["10", "12", "11", "13"], "b": ["14", "15", "16", "14"], "c": ["18", "17", "19", "20"]}, "adjust": "holm", "alpha": "0.05"}},
    "multicomp": {"objective": "Correct a declared family of hypothesis tests", "method": "multiple_comparison", "period": "cross_section",
                  "inputs": {"p_values": ["0.01", "0.04", "0.03", "0.005"], "method": "holm", "alpha": "0.05"}},
    "power": {"objective": "Size a study to detect a stated effect", "method": "power_analysis", "unit": "points", "period": "cross_section",
              "inputs": {"design": "two_sample", "effect": "5", "n1": "30", "n2": "40", "sd1": "10", "sd2": "12", "alpha": "0.05", "tails": "two_sided", "target_power": "0.8"}},
    "missing": {"objective": "How much could the missing values move the mean?", "method": "missing_data_bounds", "unit": "points", "period": "cross_section",
                "inputs": {"values": ["10", "12", "", "14", "99", "16"], "missing_codes": ["99"], "mechanism": "unknown"}},
    "weighted": {"objective": "Summarize the survey scores with the design weights", "method": "weighted_summary", "unit": "points", "period": "cross_section",
                 "inputs": {"values": ["1", "2", "3", "4"], "weights": ["1", "1", "1", "3"], "weight_kind": "reliability"}},
    "accounts": {"objective": "Prepare the management accounts for the period", "method": "management_accounts", "currency": "USD",
                 "inputs": {"spec": accounts.EXAMPLE_SPEC}},
    "case": {"objective": "A regional bakery is losing customers to a new supermarket chain. Analyze the competition in our industry and compare strategic options.", "context": "Single owner, three shops"},
    "swot": templates.EXAMPLES["template_swot"], "five_forces": templates.EXAMPLES["template_five_forces"], "case_decision": templates.EXAMPLES["case_decision"],
    "unsupported": {"objective": "Value this startup", "method": "monte_carlo_valuation", "inputs": {"x": "1"}},
}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(b)
        started = getattr(self, "_started", None)
        if started is not None:
            product_ops.log_request(self.command, self.path, code,
                                    (time.monotonic() - started) * 1000.0)   # method/path/status/ms only: no body
    def _body(self, maxb=None):
        n = int(self.headers.get("Content-Length") or 0)
        if n > (maxb or MAXBODY): raise ValueError("body too large")
        return json.loads(self.rfile.read(n) or b"{}", parse_float=Decimal)
    def do_GET(self):
        self._started = time.monotonic()
        try:
            if self.path == "/api/health":
                return self._send(200, product_ops.health({"sandbox": "on" if SANDBOX_ENABLED else "off (development)",
                                                          "model_assistance": bool(MODELS)}))
            if self.path == "/": 
                with open(os.path.join(WEB, "index.html"), "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/api/presets": return self._send(200, PRESETS)
            if self.path.startswith(product_api.CASE_ROUTE): return self._send(*product_api.handle("GET", self.path))
            u = urlparse(self.path); qs = parse_qs(u.query)
            if u.path == "/api/frameworks":
                q = (qs.get("q") or [""])[0]; ty = (qs.get("type") or [None])[0]
                if ty and ty not in registry.TYPE_LABEL: return self._send(400, {"error": "type must be F, M, Q or T"})
                return self._send(200, {"registry": {"version": registry.load()["registry_version"], "hash": registry.load()["hash"]}, "results": registry.search(q, ty, min(int((qs.get("limit") or [10])[0]), 25))})
            fm = re.fullmatch(r"/api/frameworks/([A-Za-z0-9\-]+)", u.path)
            if fm: return self._send(200, registry.brief(registry.get(fm[1])))
            if u.path == "/api/assist/config":
                if not MODELS: return self._send(200, {"enabled": False, "reason": "No model provider is configured on this server. Set BP_LLM_PROVIDER and BP_LLM_MODEL (and the provider's API key) and restart."})
                c = MODELS.config; return self._send(200, {"enabled": c.enabled, "provider": MODELS.builder.name, "builder_model": MODELS.builder.model, "reviewer_model": MODELS.reviewer.model, "same_model": MODELS.same_model,
                                                          "limits": {"max_calls_total": c.max_calls_total, "calls_used": MODELS.calls, "max_input_chars": c.max_input_chars}, "privacy_notice": c.privacy_notice, "prompt_version": assist.PROMPT_VERSION})
            if u.path == "/api/currencies":
                return self._send(200, {"currencies": currency.catalog(), "note": "ISO 4217 codes and their minor units (decimal places). No exchange rates are provided: a conversion needs a declared rate (B-069)."})
            if u.path == "/api/literature/sources":
                names = ["auto"] + [k for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] + [k for k in LITERATURE_SOURCES if k not in LITERATURE_AUTO]
                return self._send(200, {"sources": [{"name": n, "label": LITERATURE_LABELS.get(n, n)} for n in names], "notice": LITERATURE_NOTICE,
                                        "citation_styles": list(literature.CITATION_STYLES), "citation_notices": dict(literature.CITATION_NOTICES),
                                        "priority": [k for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] or list(LITERATURE_SOURCES), "log_enabled": bool(LITERATURE_LOG)})
            if u.path == "/api/literature/drift":
                if not LITERATURE_LOG: return self._send(200, {"enabled": False, "checked": 0, "result": [], "notice": "The retrieval log is disabled on this server."})
                try: n = max(1, min(int((qs.get("limit") or [10])[0]), 25))
                except ValueError: return self._send(400, {"error": "limit must be an integer"})
                srcs = [LITERATURE_SOURCES[k] for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] or list(LITERATURE_SOURCES.values())
                try: rep = literature.drift_check(LITERATURE_LOG, n, srcs)
                except literature.SourceError as e: return self._send(502, {"error": str(e)})
                return self._send(200, rep)
            if u.path == "/api/literature/log":
                if not LITERATURE_LOG: return self._send(200, {"enabled": False, "entries": [], "notice": "The retrieval log is disabled on this server."})
                try: n = max(1, min(int((qs.get("limit") or [20])[0]), 100))
                except ValueError: return self._send(400, {"error": "limit must be an integer"})
                try: entries = literature.read_log(LITERATURE_LOG, n)
                except literature.SourceError as e: return self._send(502, {"error": str(e)})
                return self._send(200, {"enabled": True, "format": literature.LOG_FORMAT, "entries": entries,
                                        "notice": "Local append-only retrieval log: source, UTC time, response SHA-256. Entries are not evidence that the metadata is correct."})
            if u.path == "/api/templates": return self._send(200, [templates.describe(k) for k in templates.TEMPLATES])
            tm = re.fullmatch(r"/api/templates/(\w+)", u.path)
            if tm:
                if tm[1] not in templates.TEMPLATES: return self._send(404, {"error": "unknown template"})
                return self._send(200, templates.describe(tm[1]))
            if self.path == "/api/methods": return self._send(200, methods.list_methods())
            m = re.fullmatch(r"/api/sessions/(\w+)", self.path)
            if m: return self._send(200, M.get(m[1]).to_dict())
            self._send(404, {"error": "not found"})
        except KeyError as e: self._send(404, {"error": "unknown session" if "registry" not in str(e) else str(e).strip("'\"")})
    def do_POST(self):
        self._started = time.monotonic()
        try:
            if self.path.startswith(product_api.CASE_ROUTE):
                n = int(self.headers.get("Content-Length") or 0)
                if n > MAXBODY: raise ValueError("body too large")
                return self._send(*product_api.handle("POST", self.path, json.loads(self.rfile.read(n) or b"{}")))
            if self.path == "/api/sessions": return self._send(201, M.create(self._body()).to_dict())
            if self.path == "/api/assist": return self._assist(self._body())
            if self.path == "/api/ingest": return self._ingest(self._body(INGEST_MAXBODY))
            if self.path == "/api/literature/verify": return self._literature(self._body())
            m = re.fullmatch(r"/api/sessions/(\w+)/(confirm|reject)", self.path)
            if m:
                body = self._body(); s = M.get(m[1])
                if not isinstance(body, dict): raise ValueError("body must be an object")
                s.confirm(m[2] == "confirm", body.get("frameworks")); return self._send(200, s.to_dict())
            self._send(404, {"error": "not found"})
        except KeyError: self._send(404, {"error": "unknown session"})
        except (ValueError, TypeError) as e: self._send(400, {"error": str(e)})
    def do_DELETE(self):
        self._started = time.monotonic()
        try:
            if self.path.startswith(product_api.CASE_ROUTE): return self._send(*product_api.handle("DELETE", self.path))
            self._send(404, {"error": "not found"})
        except (ValueError, TypeError) as e: self._send(400, {"error": str(e)})
    def _assist(self, b):
        if not isinstance(b, dict): raise ValueError("body must be an object")
        if not MODELS or not MODELS.config.enabled: return self._send(503, {"error": "model assistance is not configured on this server"})
        task, consent = b.get("task"), b.get("consent") is True
        try:
            if task == "facts": res = assist.extract_facts(MODELS, b.get("case_text"), consent, b.get("pii_acknowledged") is True)
            elif task == "alternatives": res = assist.propose_alternatives(MODELS, b.get("facts"), b.get("objective"), consent)
            elif task == "critique":
                if not isinstance(b.get("facts"), list) or not isinstance(b.get("alternatives"), list): raise assist.AssistError("facts and alternatives are required")
                if not all(isinstance(x, dict) and isinstance(x.get("id"), str) and isinstance(x.get("text", x.get("name", "")), str) for x in b["facts"] + b["alternatives"]): raise assist.AssistError("each fact and alternative needs an id")
                res = assist.critique(models=MODELS, facts=b["facts"], alternatives=b["alternatives"], consent=consent)
            else: raise ValueError("task must be facts, alternatives or critique")
        except llm.ConsentRequired as e: return self._send(400, {"error": str(e)})
        except llm.BudgetExceeded as e: return self._send(429, {"error": str(e)})
        except llm.ProviderError as e: return self._send(502, {"error": str(e)})
        except assist.AssistError as e: return self._send(422, {"error": str(e), "rejected": e.rejected})
        rid = uuid.uuid4().hex[:12]; run = {**res["run"], "run_id": rid, "accepted_by_code": len(res.get("proposals", res.get("items", []))), "rejected_by_code": len(res["rejected"])}
        ASSIST_RUNS[rid] = run; res["run"] = run; return self._send(200, res)
    def _literature(self, b):
        global LITERATURE_CALLS
        if not isinstance(b, dict): raise ValueError("body must be an object")
        title, doi, name = b.get("title"), b.get("doi"), b.get("source") or "auto"
        if not isinstance(title, str) or not title.strip(): raise ValueError("title is required")
        if not isinstance(name, str) or (name != "auto" and name not in LITERATURE_SOURCES):
            raise ValueError("source must be 'auto' or one of: " + ", ".join(sorted(LITERATURE_SOURCES)))
        style = b.get("cite")
        if style is not None and (not isinstance(style, str) or style not in literature.CITATION_STYLES):
            raise ValueError("cite must be one of: " + ", ".join(literature.CITATION_STYLES))
        if LITERATURE_CALLS >= LITERATURE_CAP: return self._send(429, {"error": "literature verification call cap reached for this server run"})
        LITERATURE_CALLS += 1
        try:
            if name == "auto":
                srcs = [LITERATURE_SOURCES[k] for k in LITERATURE_AUTO if k in LITERATURE_SOURCES] or list(LITERATURE_SOURCES.values())
                ref = literature.verify_reference(title, doi, sources=srcs, log=LITERATURE_LOG or None)
            else:
                ref = literature.verify_reference(title, doi, LITERATURE_SOURCES[name], log=LITERATURE_LOG or None)
        except literature.SourceError as e:
            return self._send(502, {"error": str(e)})
        body = {"reference": {"title": ref.title, "doi": ref.doi, "authors": list(ref.authors), "year": ref.year,
                              "container": ref.container, "volume": ref.volume, "issue": ref.issue, "pages": ref.pages,
                              "reference_type": ref.reference_type, "resolved_title": ref.resolved_title, "status": ref.status, "source": ref.source,
                              "retrieved_at": ref.retrieved_at, "response_hash": ref.response_hash},
                "notice": LITERATURE_NOTICE}
        if style: body["citation"] = literature.format_citation(ref, style)
        return self._send(200, body)
    def log_message(self, *a): pass

    def _ingest(self, b):
        try:
            table = ingest.decode_request(b)
            body = {"table": table}
            if isinstance(b, dict) and b.get("map") is not None:
                mp = b["map"]
                if not isinstance(mp, dict) or "method" not in mp or "columns" not in mp: raise ingest.IngestError("map needs {method, columns}")
                body["mapped_request"] = ingest.to_method_inputs(table, mp["method"], mp["columns"])
        except ingest.IngestError as e: return self._send(422, {"error": str(e)})
        return self._send(200, body)

def serve(port=8000, host="127.0.0.1", sandbox=True, models=None):
    global M, MODELS, SANDBOX_ENABLED
    M = SessionManager(SubprocessSandbox() if sandbox else None, ASSIST_RUNS); MODELS = models if models is not None else llm.from_env()
    SANDBOX_ENABLED = bool(sandbox)
    print(f"Workbench on http://{host}:{port} (sandbox {'ON' if sandbox else 'OFF: development only'}; model assistance {'ON: ' + MODELS.builder.name + ' ' + MODELS.builder.model if MODELS else 'OFF'}; literature ON: {', '.join(LITERATURE_SOURCES)})")
    print("Health: /api/health | cases: /api/cases | request log: " + (str(product_ops.request_log_path()) if product_ops.request_log_path() else "disabled"))
    ThreadingHTTPServer((host, port), H).serve_forever()

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    serve(int(args[0]) if args else 8000, sandbox="--no-sandbox" not in sys.argv)
