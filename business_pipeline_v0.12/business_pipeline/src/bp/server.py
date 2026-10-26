"""Minimal JSON API + static shell (stdlib only; FastAPI can replace this later behind the same routes)."""
import json, os, re, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from decimal import Decimal
from .session import SessionManager
from urllib.parse import urlparse, parse_qs
import uuid
from . import methods, registry, templates, assist, llm, literature
from .sandbox import SubprocessSandbox

ASSIST_RUNS = {}
M = SessionManager(assist_runs=ASSIST_RUNS)
MODELS = None            # llm.Models or None (model assistance off)
LITERATURE_SOURCES = {"crossref": literature.CrossrefSource(), "openalex": literature.OpenAlexSource()}
LITERATURE_LABELS = {"crossref": "Crossref", "openalex": "OpenAlex"}
LITERATURE_CALLS = 0
LITERATURE_CAP = 100     # per server run; the public APIs are free, but this stops a runaway loop
LITERATURE_NOTICE = ("The title and DOI you enter are sent to the selected public bibliographic API (Crossref or OpenAlex) "
                     "to look the reference up. No case text is sent. A citation is marked verified only when the DOI resolves "
                     "and the title matches exactly.")
WEB = os.path.join(os.path.dirname(__file__), "..", "..", "web")
MAXBODY = 100_000
PRESETS = {
    "npv": {"objective": "Should we invest in this project?", "method": "npv", "currency": "USD", "period": "annual",
           "inputs": {"rate": "0.10", "cashflows": ["-1000", "400", "400", "400"]}, "sensitivity": {"rate": ["0.05", "0.25"]}},
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
    "case": {"objective": "A regional bakery is losing customers to a new supermarket chain. Analyze the competition in our industry and compare strategic options.", "context": "Single owner, three shops"},
    "swot": templates.EXAMPLES["template_swot"], "five_forces": templates.EXAMPLES["template_five_forces"], "case_decision": templates.EXAMPLES["case_decision"],
    "unsupported": {"objective": "Value this startup", "method": "monte_carlo_valuation", "inputs": {"x": "1"}},
}

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(b)
    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        if n > MAXBODY: raise ValueError("body too large")
        return json.loads(self.rfile.read(n) or b"{}", parse_float=Decimal)
    def do_GET(self):
        try:
            if self.path == "/": 
                with open(os.path.join(WEB, "index.html"), "rb") as f: return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/api/presets": return self._send(200, PRESETS)
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
            if u.path == "/api/literature/sources":
                return self._send(200, {"sources": [{"name": k, "label": LITERATURE_LABELS.get(k, k)} for k in LITERATURE_SOURCES], "notice": LITERATURE_NOTICE})
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
        try:
            if self.path == "/api/sessions": return self._send(201, M.create(self._body()).to_dict())
            if self.path == "/api/assist": return self._assist(self._body())
            if self.path == "/api/literature/verify": return self._literature(self._body())
            m = re.fullmatch(r"/api/sessions/(\w+)/(confirm|reject)", self.path)
            if m:
                body = self._body(); s = M.get(m[1])
                if not isinstance(body, dict): raise ValueError("body must be an object")
                s.confirm(m[2] == "confirm", body.get("frameworks")); return self._send(200, s.to_dict())
            self._send(404, {"error": "not found"})
        except KeyError: self._send(404, {"error": "unknown session"})
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
        title, doi, name = b.get("title"), b.get("doi"), b.get("source") or "crossref"
        if not isinstance(title, str) or not title.strip(): raise ValueError("title is required")
        if not isinstance(name, str) or name not in LITERATURE_SOURCES: raise ValueError("source must be one of: " + ", ".join(sorted(LITERATURE_SOURCES)))
        if LITERATURE_CALLS >= LITERATURE_CAP: return self._send(429, {"error": "literature verification call cap reached for this server run"})
        LITERATURE_CALLS += 1
        try:
            ref = literature.verify_reference(title, doi, LITERATURE_SOURCES[name])
        except literature.SourceError as e:
            return self._send(502, {"error": str(e)})
        return self._send(200, {"reference": {"title": ref.title, "doi": ref.doi, "authors": list(ref.authors), "year": ref.year,
                                             "container": ref.container, "resolved_title": ref.resolved_title, "status": ref.status, "source": ref.source},
                                 "notice": LITERATURE_NOTICE})
    def log_message(self, *a): pass

def serve(port=8000, host="127.0.0.1", sandbox=True, models=None):
    global M, MODELS
    M = SessionManager(SubprocessSandbox() if sandbox else None, ASSIST_RUNS); MODELS = models if models is not None else llm.from_env()
    print(f"Workbench on http://{host}:{port} (sandbox {'ON' if sandbox else 'OFF: development only'}; model assistance {'ON: ' + MODELS.builder.name + ' ' + MODELS.builder.model if MODELS else 'OFF'}; literature ON: {', '.join(LITERATURE_SOURCES)})"); ThreadingHTTPServer((host, port), H).serve_forever()

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    serve(int(args[0]) if args else 8000, sandbox="--no-sandbox" not in sys.argv)
