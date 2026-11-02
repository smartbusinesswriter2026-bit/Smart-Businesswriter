"""Work Plan record, stage states derived from recorded events, JSON-safe serialization (Stage 1 contracts)."""
import json, uuid, threading
from dataclasses import asdict, is_dataclass
from .orchestrator import Pipeline, Delivery, Pause, STAGES
from .spec import ProblemSpec
from .methods import LIBRARY
from . import registry as REG, templates as TPL

# Charter 6/9 states, plus one declared extension: awaiting_user (a mandatory checkpoint is open).
STATES = ["planned", "running", "passed", "failed", "blocked", "not_run", "awaiting_user"]
_PASS = {"done", "frozen", "selected", "pass", "artifact", "delivered", "no_method"}

def stage_states(events: list[dict], finished: bool) -> dict:
    """Status comes only from recorded events, never from an agent's self-report."""
    out = {}
    for st in STAGES:
        ev = [e for e in events if e["stage"] == st]
        if not ev: out[st] = "not_run" if finished else "planned"; continue
        last = ev[-1]["status"]
        out[st] = ("awaiting_user" if last == "awaiting_confirmation" else "blocked" if last == "blocked"
                   else "failed" if last in ("fail", "error") else "not_run" if last == "skipped"
                   else "passed" if last in _PASS else "running")
    return out

def work_plan(request: dict, spec: ProblemSpec | None) -> dict:
    m = LIBRARY.get(request.get("method")); t = TPL.TEMPLATES.get(request.get("method"))
    plan = {
        "objective": request.get("objective"),
        "task_family": ("Descriptive statistics" if m.category == "descriptive statistics" else "Correlation analysis" if m.category == "correlation" else "Regression analysis" if m.category == "regression" else "Group comparison" if m.category == "group comparison" else "Quantitative business analysis") if m else ("Framework guidance (no computed answer)" if request.get("method") in (None, "", "framework_only") else "Unsupported method (framework-only response)"),
        "method": request.get("method"), "tier": m.tier if m else "T4",
        "tier_label": ("custom analysis (T2); expert review pending" if m and m.tier == "T2" and m.review_status == "pending_named_reviewer" else "standard method; expert review pending" if m and m.review_status == "pending_named_reviewer" else "standard method") if m else "framework only",
        "stages": list(STAGES),
        "planned_checks": list(m.test_names) if m else [],
        "inputs": spec.inputs if spec else {}, "assumptions": request.get("assumptions", []),
        "ambiguities": request.get("ambiguities", []) + [dict(d) for d in (m.defaults if m else ())],
        "method_version": m.version if m else None, "review_status": m.review_status if m else None,
        "intended_use": m.intended_use if m else "", "unsupported_use": m.unsupported_use if m else "",
        "limitations": list(m.limitations) if m else [],
        "assumption_checks": list(m.assumption_check_names) if m else [], "fallbacks": dict(m.fallbacks) if m else {},
        "thresholds": spec.thresholds if spec else {},
        "sensitivity": request.get("sensitivity", {}),
        "expected_outputs": ["report (numbers by reference)", "provenance appendix", "run log"] if m else ["framework-only guidance; no computed answer"],
        "confirmation_required": "Confirm the Problem Spec before anything is computed.",
    }
    if t:
        plan.update({"task_family": "Framework template: " + t["name"], "tier": t.get("tier", "T4"), "tier_label": ("custom analysis (T2); expert review pending" if t.get("tier") == "T2" else "framework template (structure only; no computed answer)"),
                     "planned_checks": list(t["test_names"]), "ambiguities": request.get("ambiguities", []) + [dict(d) for d in t["defaults"]], "method_version": t["version"],
                     "review_status": "pending_named_reviewer" if t.get("tier") == "T2" else "not applicable (nothing is computed)", "sensitivity": ({"rate": request.get("inputs", {}).get("rate_range")} if t.get("sensitivity") else {}), "intended_use": t["intended_use"], "unsupported_use": t["unsupported_use"], "limitations": list(t["limitations"]),
                     "expected_outputs": (["comparison report (numbers by reference)", "crossover rates across your range", "verbatim facts and alternatives", "provenance appendix", "run log"] if t.get("tier") == "T2" else ["framework structure built only from your evidence", "audit flags and gaps", "verbatim evidence listing", "provenance appendix", "run log"]),
                     "input_help": t["input_help"], "template_registry_ids": t["registry_ids"]})
    return plan

def _plain(o):
    if is_dataclass(o) and not isinstance(o, type): return {k: _plain(v) for k, v in asdict(o).items()}
    if isinstance(o, dict): return {str(k): _plain(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_plain(v) for v in o]
    return o if isinstance(o, (str, int, bool, type(None))) else str(o)

class Session:
    def __init__(self, request: dict, sandbox=None, assist_runs=None):
        self.id = uuid.uuid4().hex[:12]; self.request = request; self.assist = self._runs(request, assist_runs or {}); self.p = Pipeline(sandbox=sandbox); self.delivery = None
        self.pause = None; self.spec_confirmed = False
        r = self.p.start(request)
        if isinstance(r, Delivery): self.delivery, self.spec = r, None
        else: self.spec = r
        self.plan = work_plan(request, self.spec)
        self.suggestions = REG.recommend((request.get("objective") or "") + " " + (request.get("context") or ""))
        self.plan["framework_suggestions"] = self.suggestions

    @property
    def status(self):
        if self.delivery: return self.delivery.status
        return "awaiting_mapping_confirmation" if self.pause else "awaiting_confirmation"

    @staticmethod
    def _runs(request, known):
        ids = request.get("assist_runs", [])
        if not isinstance(ids, list) or len(ids) > 10 or not all(isinstance(i, str) for i in ids): raise ValueError("assist_runs must be a list of at most 10 run ids")
        out = []
        for i in dict.fromkeys(ids):
            if i not in known: raise ValueError(f"unknown assist run id {i}")
            out.append(known[i])
        return out

    def _selection(self, ids):
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids): raise ValueError("frameworks must be a list of registry ids")
        if len(ids) > REG.POLICY["max_selected"]: raise ValueError(f"select at most {REG.POLICY['max_selected']} items (minimum sufficient set)")
        try: recs = REG.selection_records(ids)
        except KeyError as e: raise ValueError(str(e).strip("'\""))
        sug = {x["id"]: "suggested" for k in ("frameworks", "quantitative", "theories") for x in self.suggestions[k]}; sug.update({x["id"]: "named_by_user" for x in self.suggestions["named"]})
        out = [{"id": r["id"], "name": r["name"], "type": r["type"], "source": sug.get(r["id"], "added_by_user"), "role": "supporting_theory" if r["type"] == "T" else "selected"} for r in recs]
        t = TPL.TEMPLATES.get(self.request.get("method"))
        if t:       # requesting a template is itself an explicit selection of its framework
            for rid in reversed(t["registry_ids"]):
                if rid not in {x["id"] for x in out}: r = REG.get(rid); out.insert(0, {"id": r["id"], "name": r["name"], "type": r["type"], "source": "requested_template", "role": "selected"})
        return out

    def confirm(self, confirmed: bool = True, frameworks=None):
        if self.delivery: raise ValueError("session already finished")
        if self.pause:       # second mandatory checkpoint: the account mapping must be confirmed before anything is posted
            r = self.p.resume(True, mapping_confirmed=True) if confirmed else self.p.reject_mapping()
            self.delivery, self.pause = r, None
            return self._attach_assist()
        if confirmed:       # nothing is applied unless the user selected it; selection is frozen with the spec
            self.p.spec.frameworks_selected = self._selection(frameworks or []); self.p.spec.registry = self.suggestions["registry"]
            self.p.spec.model_assistance = [{k: r[k] for k in ("run_id", "task", "provider", "model", "template_version", "prompt_sha256", "output_sha256")} for r in self.assist]
            self.spec_confirmed = True
        r = self.p.resume(confirmed)
        if isinstance(r, Pause): self.pause = r
        else: self.delivery = r
        self._attach_assist()

    def _attach_assist(self):
        if self.delivery is not None and self.delivery.status == "delivered" and self.assist:
            ev = (self.request.get("inputs") or {}).get("facts", []); n = sum(1 for f in ev if isinstance(f, dict) and str(f.get("source", "")).startswith("case text (model-extracted"))
            self.delivery.appendix["model_assistance"] = {"runs": self.p.spec.model_assistance, "facts_marked_model_extracted": n,
                "statement": "Model proposals were validated by code and used only if you confirmed them. The model produced no numbers; every number in this result comes from your inputs or from computation."}

    def to_dict(self):
        mp = self.pause.mapping if self.pause else (self.p.mapping if getattr(self.p, "mapping", None) else None)
        return _plain({"id": self.id, "status": self.status, "work_plan": self.plan,
                       "account_mapping": mp,
                       "spec": {**self.spec.content(), "hash": self.spec.hash} if self.spec else None,
                       "stage_states": stage_states(self.p.events, self.delivery is not None),
                       "events": self.p.events, "delivery": self.delivery})

class SessionManager:
    def __init__(self, sandbox=None, assist_runs=None): self._s, self._lock, self.sandbox, self.assist_runs = {}, threading.Lock(), sandbox, (assist_runs if assist_runs is not None else {})
    def create(self, request):
        if not isinstance(request, dict) or not str(request.get("objective", "")).strip(): raise ValueError("missing field: objective")
        if not isinstance(request.get("inputs", {}), dict): raise ValueError("inputs must be an object")
        s = Session(request, self.sandbox, self.assist_runs)
        with self._lock: self._s[s.id] = s
        return s
    def get(self, id):
        with self._lock: return self._s[id]
