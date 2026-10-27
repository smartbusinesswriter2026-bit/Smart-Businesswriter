"""Deterministic orchestrator: code fixes stage order and whether verification runs (P4, section 4)."""
import re, uuid, inspect, datetime
from dataclasses import dataclass, field
from decimal import Decimal as D, InvalidOperation
from .quantity import Quantity
from .artifacts import Artifact, ArtifactStore, sha, env_hash
from .spec import ProblemSpec
from .methods import LIBRARY, validate_inputs, DataError, decision_flip
from .sandbox import SandboxError
from . import envpin, registry, templates, currency as currencies
from .claims import license_check

STAGES = ["intake", "formalization", "method_selection", "test_planning", "execution",
          "verification", "sensitivity", "drafting", "draft_audit", "delivery"]
YEAR = re.compile(r"\b(19|20)\d{2}\b")
TOKEN = re.compile(r"\{\{ref:(\w+):(\w+):(\w+)\}\}")
TXT = re.compile(r"\{\{txt:([A-Za-z0-9_]{1,20})\}\}")
SYNTHETIC_NOTE = "Note: these results are computed from synthetic data and must not be read as observations."

# ---------- cross-cutting honesty layer (manual 9B.3; B-057) ----------
# These notices do not change any number. They make the limits that the 9B.3 upgrades would otherwise
# fix visible in every delivery, so a result cannot be read as more than it is: missing data are removed
# listwise without an established mechanism, multiple hypotheses are not corrected, no power calculation
# is reported, and weights/clusters/repeated measures are not supported.
_DATA_INPUT_TYPES = ("value_list", "column_map", "count_table")

def _honesty(m, inp):
    """Return ({field: disclosure sentence or None}, [sentences to append to the report])."""
    types = {s.get("type") for s in m.input_schema.values()}
    inferential = m.claim_ceiling in ("associational", "predictive") or bool(m.assumption_checks)
    missing = ("Missing values (blank entries and declared missing codes) are excluded listwise before the computation; "
               "the missing-data mechanism (MCAR, MAR or MNAR) was not established, so the results assume the excluded values are not systematically different.") if types.intersection(_DATA_INPUT_TYPES) and m.name not in ("multiple_comparison", "missing_data_bounds") else None
    if m.name == "multiple_comparison":
        multiple = "The declared correction is applied to the family you supplied; the method does not decide whether that family is the right one, and it does not model dependence between the tests."
    elif m.name in ("ols", "ols_robust"):
        k = len(inp.get("predictors") or {})
        multiple = (f"No multiple-comparison correction is applied automatically: {k} coefficient hypotheses are tested at the same time, so the family-wise chance of a small p-value is higher than the per-test level; read individual coefficient p-values as a family, not in isolation. A declared correction can be computed with the multiple_comparison method (Holm or Bonferroni)."
                    if k > 1 else "One coefficient hypothesis is tested, so no multiple-comparison correction is needed.")
    elif m.name in ("anova", "kruskal_wallis"):
        multiple = "One omnibus hypothesis is tested and no post-hoc pairwise comparisons are made, so no multiple-comparison correction is applied."
    elif inferential:
        multiple = "One hypothesis is tested, so no multiple-comparison correction is applied."
    else:
        multiple = None
    power = ("No power or minimum-detectable-effect calculation is reported; the confidence interval shows the precision the sample actually achieved."
             if inferential else None)
    weights = ("Weights are applied to the summary only; no standard error, interval or test is computed because that needs a declared complex design (stratification, clustering, replicate weights)."
               if m.name == "weighted_summary" else
               ("Survey weights, clustered observations and repeated measures are not supported; every observation is treated as independent."
                if inferential else None))
    out = {"missing_data": missing, "multiple_comparisons": multiple, "power": power, "weights_and_clusters": weights}
    return out, [v for v in out.values() if v]


@dataclass
class Delivery:
    status: str                 # delivered | blocked
    tier: str
    report: str = ""
    blocked_reason: str = ""
    appendix: dict = field(default_factory=dict)

@dataclass
class Pause:
    """A mandatory checkpoint that is open: the pipeline waits for a user decision before continuing."""
    mapping: dict

def _code_hash(impl):
    try: return sha(inspect.getsource(impl))
    except (OSError, TypeError): return sha(getattr(impl, "__name__", "impl"))

class Pipeline:
    def __init__(self, amendment_budget: int = 3, sandbox=None):
        self.N = amendment_budget; self.sb = sandbox     # sandbox=None runs in-process (development and unit tests)
        self.events: list[dict] = []   # the UI reflects these records, not agent self-reports
        self.store = ArtifactStore()
        self.mapping = None

    def log(self, stage, status, **detail): self.events.append({"stage": stage, "status": status, **detail})

    def start(self, request: dict):
        """Stages 1-2 up to the user checkpoint. Returns a draft ProblemSpec, or a blocked Delivery."""
        request = {**request, "method": request.get("method") or "framework_only", "inputs": request.get("inputs") or {}}
        self.request = request
        inp = request["inputs"]; m = LIBRARY.get(request["method"])
        issues = []; t = templates.TEMPLATES.get(request["method"])
        if t: issues = templates.validate(request["method"], inp)
        elif m:
            issues = validate_inputs(m, inp)            # schema first: actionable errors, no defaults substituted
            if request.get("currency"):
                try: currencies.minor_units(request["currency"])
                except currencies.CurrencyError as e: issues.append(str(e))
            if not issues:
                try: issues = m.profile(inp)
                except (InvalidOperation, KeyError, TypeError, ValueError, ZeroDivisionError) as e:
                    issues = [f"malformed or missing input: {e!r}"]
        self.log("intake", "done", anomalies=issues)
        if issues: return self._block("intake", f"profiling anomalies: {issues}", "T4")
        th = {**(m.default_thresholds if m else {}), **request.get("thresholds", {})}
        fb = dict(m.fallbacks) if m else {}
        claims = [{"id": "c1", "text": "result", "type": m.claim_ceiling if m else "descriptive"}]
        if m and m.decision: claims.append({"id": "c2", "text": "decision", "type": "prescriptive"})
        spec = ProblemSpec(
            objective=request["objective"], method=request["method"], claims=claims,
            inputs={k: {"value": str(v), "provenance": request.get("provenance", {}).get(k, "user")} for k, v in inp.items()},
            assumptions=request.get("assumptions", []), sensitivity=({"rate": inp.get("rate_range")} if t and t.get("sensitivity") and isinstance(inp, dict) else request.get("sensitivity", {})), thresholds=th,
            ambiguity_register=request.get("ambiguities", []) + [dict(d) for d in (t["defaults"] if t else m.defaults if m else ())],
            decision_context=request.get("decision_context", {}),
            checks=list(t["test_names"]) if t else (list(m.test_names) + list(m.assumption_check_names) + [t for f in fb.values() for t in LIBRARY[f].test_names]) if m else [],
            data_manifest=request.get("data_manifest", []), user_values=request.get("user_values", []),
            framework=request.get("framework"), fallbacks=fb)
        self.spec = spec
        self.log("formalization", "awaiting_confirmation")
        return spec

    def run(self, request: dict, confirm_spec, builder=None, template: str | None = None) -> Delivery:
        """Convenience path: runs to completion, confirming both mandatory checkpoints (the spec and, where the method
        declares one, the account mapping). Use start/resume to honour the checkpoints interactively."""
        r = self.start(request)
        if isinstance(r, Delivery): return r
        return self.resume(bool(confirm_spec(r)), builder, template, mapping_confirmed=True)

    def reject_mapping(self):
        """The owner rejected the account mapping at the second mandatory checkpoint: nothing is posted."""
        m = LIBRARY.get(self.request["method"])
        return self._block("formalization", "user did not confirm the account mapping", m.tier if m else "T4")

    def resume(self, confirmed: bool, builder=None, template: str | None = None, mapping_confirmed: bool = False) -> "Delivery | Pause":
        request, spec = self.request, self.spec
        inp = request["inputs"]; m = LIBRARY.get(request["method"])
        if not confirmed: return self._block("formalization", "user did not confirm spec", "T4")
        if not spec.hash: spec.freeze(); self.log("formalization", "frozen", spec_hash=spec.hash)

        if request["method"] in templates.TEMPLATES: return self._template_resume(spec, request)
        # 3 Method selection: escalation by missing method, never by "difficulty"
        if not m:
            self.log("method_selection", "no_method", tier="T4")
            sel = [registry.get(x["id"]) for x in spec.frameworks_selected]
            return Delivery("delivered", "T4", report=registry.framework_only_report(sel, spec.objective),
                            appendix={"spec_hash": spec.hash, "tier": "T4", "frameworks_selected": spec.frameworks_selected, "registry": spec.registry,
                                      "note": "Framework-only response: nothing was computed. Frameworks are suggestions recorded in the frozen spec; the catalogue marks every item as unreviewed."})
        period = request.get("period", m.default_period); entity = request.get("entity", "entity"); cur = request.get("currency")
        tier = m.tier; self.log("method_selection", "selected", method=m.name, version=m.version, tier=tier, review_status=m.review_status)

        # 3b Second mandatory checkpoint (manual 9.3): the account mapping must be confirmed before anything is posted
        if m.mapping:
            try: mp = m.mapping(inp)
            except (ValueError, TypeError) as e: return self._block("formalization", f"account mapping problem: {e}", tier)
            bad = [n for n, ok, _ in mp["checks"] if not ok]
            if bad: return self._block("formalization", "account mapping checks failed: " + ", ".join(bad), tier)
            self.mapping = mp
            if not mapping_confirmed:
                self.log("formalization", "awaiting_confirmation", checkpoint="account_mapping", rows=mp["rows"], checks=[[n, bool(ok), d] for n, ok, d in mp["checks"]])
                return Pause(mp)
            self.log("formalization", "frozen", checkpoint="account_mapping_confirmed", spec_hash=spec.hash)

        # 4 Test planning: names frozen before execution
        planned = tuple(m.test_names) or tuple(n for n, _ in m.tests(inp, m.impl))
        plan_hash = sha(planned); self.log("test_planning", "frozen", tests=planned, plan_hash=plan_hash)

        # 6a Pre-declared assumption checks; a failure triggers the pre-declared fallback as a logged amendment (9B.3)
        used_fallback = None
        if m.assumption_checks:
            try: res = self.sb.assumptions(m.name, inp, spec.thresholds)[0] if self.sb else m.assumption_checks(inp, spec.thresholds)
            except DataError as e: return self._block("verification", f"data problem: {e}", "T4")
            except SandboxError as e: return self._block("verification", f"sandbox failure: {e}", "T4")
            self.log("verification", "assumptions", results=[(n, ok, d) for n, ok, d in res])
            bad = [(n, d) for n, ok, d in res if not ok]
            if bad:
                nofb = [(n, d) for n, d in bad if n not in spec.fallbacks]
                if nofb: return self._block("verification", "assumption check failed with no pre-declared fallback: " + "; ".join(f"{n} ({d})" for n, d in nofb), tier)
                fbid = spec.fallbacks[bad[0][0]]
                self.log("amendment", "logged", kind="fallback", check=bad[0][0], from_method=m.name, to_method=fbid, detail=bad[0][1])
                used_fallback = {"check": bad[0][0], "from": m.name, "to": fbid, "detail": bad[0][1]}
                m = LIBRARY[fbid]; planned = tuple(m.test_names); tier = m.tier
                self.log("test_planning", "frozen", tests=planned, plan_hash=sha(planned), fallback_of=used_fallback["from"])

        # 5/6 Execution + verification with amendment control
        impl, amendments, meta = m.impl, 0, None
        if self.sb:
            if builder is not None: raise ValueError("builder patching is not supported with the sandbox (vetted T1 methods only)")
            try: results, outputs, meta = self.sb.verify_execute(m.name, inp)
            except DataError as e: return self._block("verification", f"data problem: {e}", "T4")
            except SandboxError as e: return self._block("execution", f"sandbox failure: {e}", "T4")
            failed = [n for n, ok in results if not ok]
            self.log("verification", "pass" if not failed else "fail", failed=failed, amendments=0, sandboxed=True)
            if failed: return self._block("verification", f"checks failed: {failed}; escalate to human/lower tier", "T4")
        else:
            while True:
                try: results = m.tests(inp, impl)
                except DataError as e: return self._block("verification", f"data problem: {e}", "T4")
                except Exception as e: results = [("execution_error", False)]; self.log("execution", "error", error=repr(e))
                failed = [n for n, ok in results if not ok]
                self.log("verification", "pass" if not failed else "fail", failed=failed, amendments=amendments)
                if not failed: break
                if builder is None or amendments >= self.N:
                    return self._block("verification", f"checks failed after {amendments} amendment(s): {failed}; escalate to human/lower tier", "T4")
                patched = builder(impl, failed)          # builder may patch code only; tests, thresholds, verifier untouched
                amendments += 1
                self.log("amendment", "logged", n=amendments, failing=failed)
                impl = patched
        if tuple(n for n, _ in results) != planned:
            return self._block("verification", "test set differs from frozen plan", "T4")
        if not self.sb: raw = impl(inp); outputs = raw if isinstance(raw, dict) else {m.metric: raw}
        extra = (meta or {}).get("appendix_extra")          # structured, non-numeric results some methods attach
        if isinstance(outputs, dict):
            outputs = dict(outputs); extra = outputs.pop("_appendix", extra); outputs.pop("_checks", None)
        base_unit = request.get("unit", "value") if m.unit == "from_request" else m.unit
        fp = meta["fingerprint"] if meta else envpin.fingerprint()
        run_id, env, code_h, created = uuid.uuid4().hex[:12], (meta["env_hash"] if meta else envpin.env_hash(fp)), (meta["code_hash"] if meta else _code_hash(impl)), datetime.datetime.now(datetime.timezone.utc).isoformat()
        ids = []
        for metric, val in outputs.items():
            if m.typing: mu, prec = m.typing(metric)
            else: mu, prec = ("count" if metric in ("n", "n_missing") else m.output_units.get(metric, base_unit)), m.output_precision.get(metric, request.get("precision", 2))
            if mu == "count": prec = 0
            if mu == "currency" and "precision" not in request and cur:
                try: prec = currencies.minor_units(cur)
                except currencies.CurrencyError: pass
            cur_here = cur if mu == "@unit" else None
            if mu == "@unit": mu = base_unit
            q = Quantity(val, unit=mu, currency=cur_here if cur_here else None if mu in ("count", "units", "correlation", "probability", "rate", "coefficient", "ratio", "days") else cur,
                         period=period, precision=prec)
            aid = "result" if len(outputs) == 1 else metric
            self.store.put(Artifact(aid, q, (metric, period, entity, "base"), spec.hash, code_h, sha(inp),
                                    f"{m.name}(inputs).{metric}", "tier:" + tier, env, m.version, run_id, created)); ids.append(aid)
        self.log("execution", "artifact", ids=ids, code_hash=code_h, run_id=run_id)
        primary = outputs[m.metric]

        # 7 Sensitivity: decision-flip over pre-declared range
        flip = None
        if m.decision and "rate" in spec.sensitivity:
            lo, hi = (D(str(x)) for x in spec.sensitivity["rate"])
            try: flip = self.sb.flip(m.name, inp, lo, hi) if self.sb else decision_flip(m, impl, inp, lo, hi)
            except SandboxError as e: return self._block("sensitivity", f"sandbox failure: {e}", tier)
            if flip is not None:
                self.store.put(Artifact("flip_rate", Quantity(flip, unit="rate", period=period),
                                        ("flip_rate", period, entity, "base"), spec.hash, "bisect", sha(inp), "bisection on decision", "deterministic", env, m.version, run_id, created))
            self.log("sensitivity", "done", flips=flip is not None)
        else: self.log("sensitivity", "skipped", reason="no pre-declared range or no decision rule")

        # 8 Drafting: template writes tokens, never digits; renderer fills numbers
        decision = m.decision(primary) if m.decision else None
        template = template or (m.template(outputs, period, spec.thresholds) if m.template else self._default_template(m, decision, flip is not None, period))
        self.log("drafting", "done")

        # 9 Draft audit: raw digits rejected, tokens resolved against labels, claim wording licensed
        if re.search(r"\d", YEAR.sub("", TOKEN.sub("", template))): return self._block("draft_audit", "raw numeric literal in draft", tier)
        try: rendered = TOKEN.sub(lambda t: self.store.resolve(*t.groups()).value.display(), template)
        except Exception as e: return self._block("draft_audit", f"reference failure: {e!r}", tier)
        for s in filter(None, (x.strip() for x in re.split(r"(?<=[.!?])\s+", template))):
            probs = license_check(s, "prescriptive" if re.search(r"\bshould\b|\brecommend", s, re.I) else m.claim_ceiling)
            if probs: return self._block("draft_audit", f"claim licensing: {probs}", tier)
        notes = list(m.caveats(outputs, spec.thresholds)) if m.caveats else []
        honesty, honesty_notes = _honesty(m, inp)
        notes.extend(honesty_notes)
        if any(v.get("provenance") == "synthetic" for v in spec.inputs.values()): notes.append(SYNTHETIC_NOTE)
        if used_fallback:
            notes.insert(0, f"Because the pre-declared {used_fallback['check'].replace('_', ' ')} failed, the analysis switched from {used_fallback['from']} to the pre-declared fallback, {used_fallback['to']}. This switch is logged as an amendment.")
        if notes: rendered += " " + " ".join(notes)
        self.log("draft_audit", "pass")

        # 10 Delivery (fail closed handled by early returns above)
        appendix = {"spec_hash": spec.hash, "tier": tier, "method": {"id": m.name, "version": m.version, "category": m.category, "review_status": m.review_status},
                    "run_id": run_id, "env_hash": env, "fallback_used": used_fallback, "thresholds": spec.thresholds, "frameworks_selected": spec.frameworks_selected, "registry": spec.registry,
                    "frameworks_note": "Selected frameworks are recorded in the frozen spec; framework templates are not implemented, so they did not change the computation.", "code_hash": code_h, "sandbox": meta["policy"] if meta else "in-process (development mode; no isolation)", "environment": fp, "tests": [n for n, _ in results], "amendments": amendments,
                    "assumptions": spec.assumptions + list(m.assumptions), "ambiguities": spec.ambiguity_register, "limitations": list(m.limitations),
                    "artifacts": [(a.id, a.labels, a.derivation) for a in self.store.all()]}
        if extra is not None:
            # the key is part of the existing delivery shape for every method that had an appendix;
            # only the new check gets its own, so nothing already consumed moves
            appendix["detail" if m.name == "trial_balance_check" else "accounts"] = extra
        appendix["honesty"] = honesty   # 9B.3 disclosure layer: what was NOT corrected, powered, weighted or established
        flip_s = str(flip) if flip is not None else None
        appendix["reperform"] = {"format": "bp-reperform/1", "method": {"id": m.name, "version": m.version}, "inputs": inp, "sensitivity": spec.sensitivity,
                                 "outputs": {k: str(v) for k, v in outputs.items()}, "flip": flip_s, "env_hash": env, "fingerprint": fp, "spec_hash": spec.hash,
                                 "outputs_hash": sha({k: str(v) for k, v in outputs.items()}),
                                 # the rendered appendix is what a reader actually sees; hashing it makes
                                 # "re-runnable" mean the document, not only the scalar set
                                 "statements_hash": sha(extra) if extra is not None else None}
        self.log("delivery", "delivered")
        return Delivery("delivered", tier, rendered, appendix=appendix)

    def _template_resume(self, spec, request):
        """Framework templates (tier T4): structure the user's own evidence, verify it, render. Nothing is computed or invented."""
        kind, inp = request["method"], request["inputs"]; t = templates.TEMPLATES[kind]; tier = t.get("tier", "T4"); entity = request.get("entity", "entity")
        self.log("method_selection", "selected", method=kind, version=t["version"], tier=tier, review_status=("pending_named_reviewer" if tier == "T2" else "not applicable (nothing is computed)"))
        names = tuple(t["test_names"]); self.log("test_planning", "frozen", tests=names, plan_hash=sha(names))
        try: out, meta = self.sb.template(kind, inp) if self.sb else (templates.run_template(kind, inp), None)
        except DataError as e: return self._block("verification", f"data problem: {e}", tier)
        except SandboxError as e: return self._block("execution", f"sandbox failure: {e}", tier)
        results = [(n, ok) for n, ok in out["results"]]; failed = [n for n, ok in results if not ok]
        self.log("verification", "pass" if not failed else "fail", failed=failed, amendments=0, sandboxed=bool(self.sb))
        if failed: return self._block("verification", f"checks failed: {failed}; escalate to human review", tier)
        if tuple(n for n, _ in results) != names: return self._block("verification", "test set differs from frozen plan", tier)
        fp = meta["fingerprint"] if meta else envpin.fingerprint(); env = meta["env_hash"] if meta else envpin.env_hash(fp)
        code_h = meta["code_hash"] if meta else _code_hash(t["build"]); run_id = uuid.uuid4().hex[:12]; created = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for ar in out["artifacts"]:
            u = ar["unit"]; q = Quantity(ar["value"], unit=u, currency=ar.get("currency") if u == "currency" else None, period=templates.PERIOD, precision=ar.get("precision", 2))
            self.store.put(Artifact(ar["id"], q, (ar["metric"], templates.PERIOD, entity, "base"), spec.hash, code_h, sha(inp), f"{kind}.{ar['id']}", "tier:" + tier, env, t["version"], run_id, created))
        self.log("execution", "artifact", ids=[ar["id"] for ar in out["artifacts"]], code_hash=code_h, run_id=run_id)
        if t.get("sensitivity"): self.log("sensitivity", "done", range=spec.sensitivity)
        else: self.log("sensitivity", "skipped", reason="framework template: nothing computed")
        self.log("drafting", "done")
        narrative = out["narrative"]
        if re.search(r"\d", YEAR.sub("", TXT.sub("", TOKEN.sub("", narrative)))): return self._block("draft_audit", "raw numeric literal in the template narrative", tier)
        for sn in filter(None, (x.strip() for x in re.split(r"(?<=[.!?])\s+", narrative))):
            probs = license_check(sn, "descriptive")
            if probs: return self._block("draft_audit", f"claim licensing: {probs}", tier)
        try: rendered = TOKEN.sub(lambda m_: self.store.resolve(*m_.groups()).value.display(), narrative)
        except Exception as e: return self._block("draft_audit", f"reference failure: {e!r}", tier)
        refs = out.get("text_refs", {})
        if any(i not in refs for i in TXT.findall(rendered)): return self._block("draft_audit", "text reference to an unknown item", tier)
        rendered = TXT.sub(lambda m_: refs[m_.group(1)], rendered)      # user-supplied names are inserted after the audit and are not re-scanned
        self.log("draft_audit", "pass")
        report = rendered + "\n\n" + out["listing"]       # the listing is the user's own evidence, reproduced verbatim after the audit
        appendix = {"spec_hash": spec.hash, "tier": tier, "template": {"id": kind, "version": t["version"], "registry_ids": t["registry_ids"], "review_status": "pending_named_reviewer" if tier == "T2" else "not applicable (nothing is computed)"}, "run_id": run_id, "env_hash": env, "code_hash": code_h,
                    "sandbox": meta["policy"] if meta else "in-process (development mode; no isolation)", "environment": fp, "tests": [n for n, _ in results], "analysis": out["analysis"],
                    "ambiguities": spec.ambiguity_register, "limitations": list(t["limitations"]), "frameworks_selected": spec.frameworks_selected, "registry": spec.registry,
                    "note": ("Custom analysis (T2, expert review pending): net present value computed from the cash flows you supplied; a preference appears only under your own decision rule; no fact, alternative or weight was added." if tier == "T2"
                             else "Framework template: the structure is built only from the evidence you supplied. Nothing was computed, ranked or scored, and no fact was added."),
                    "reperform": {"format": "bp-reperform/1", "template": True, "method": {"id": kind, "version": t["version"]}, "inputs": inp, "analysis_hash": sha(out["analysis"]),
                                  "outputs": {ar["id"]: ar["value"] for ar in out["artifacts"]}, "env_hash": env, "fingerprint": fp, "spec_hash": spec.hash}}
        self.log("delivery", "delivered")
        return Delivery("delivered", tier, report, appendix=appendix)

    def _default_template(self, m, decision, has_flip, period):
        t = f"Under the stated assumptions, the {m.metric.replace('_', ' ')} is {{{{ref:result:{m.metric}:{period}}}}}. "
        if decision is not None:
            t += ("The result is positive, so the investment clears the hurdle under these inputs. " if decision
                  else "The result is not positive, so the investment does not clear the hurdle under these inputs. ")
        if has_flip:
            t += "The decision changes at a discount rate of {{ref:flip_rate:flip_rate:%s}}, which is user-supplied range sensitivity. " % period
        return t.strip()

    def _block(self, stage, reason, tier):
        self.log(stage, "blocked", reason=reason)
        return Delivery("blocked", tier, blocked_reason=reason, appendix={"events": self.events})
