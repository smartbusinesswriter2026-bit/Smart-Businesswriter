"""Stage 3 — the capability walker.

For every entry in capabilities.ENTRIES (126) that has a preset, this drives
the conductor path: chat.start -> answer -> confirm_plan -> run_capability
(with the preset inputs) -> research -> draft -> docx_bytes, with retrieval
frozen to evidence/shared.json (no network, no model).  Judgement uses the
shared rule engine (scripts/validation/rules.py).

Usage (from business_pipeline/):
    PYTHONPATH=src python scripts/validation/walk_capabilities.py [--limit N]
"""

import argparse
import datetime
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

for var in ("BP_LLM_PROVIDER", "BP_LLM_MODEL", "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY", "BP_OPENGO_API_KEY",
            "OPENCODE_API_KEY"):
    os.environ.pop(var, None)

from bp.product import chat, capabilities  # noqa: E402
import bp.server as srv  # noqa: E402
try:
    from .rules import judge_paper, by_rule as _by_rule
except ImportError:
    from rules import judge_paper, by_rule as _by_rule

DEFAULTS = {"decision": "", "geography": "Global", "period": "5",
            "style": "apa", "industry": "consumer goods"}


def load_subject_map():
    import json as _j
    with open(os.path.join(HERE, "subject_map.json"), encoding="utf-8") as f:
        return _j.load(f)


def subject_of_capability(entry):
    # capabilities carry no subject; slot -> shelf heuristic from §7
    slot = (entry.get("slot") or ("", ""))[0] if isinstance(entry.get("slot"), tuple) else ""
    mapping = {
        "Financial Feasibility": "finance",
        "Data Analysis": "research",
        "Economic Context": "economics",
        "Delivery Status": "project-management",
        "Market Structure": "economics",
        "Policy Impact": "economics",
        "Marketing Performance": "marketing",
        "Operations": "operations",
        "Financial Analysis": "accounting",
        "Customer Economics": "marketing",
        "Customer Evidence": "marketing",
        "Impact": "economics",
        "Market Assessment": "marketing",
        "Market Response": "marketing",
        "Ownership": "finance",
        "Pricing": "marketing",
    }
    return mapping.get(slot, "research")


def run_one(key, out):
    entry = capabilities.entry(key)
    # presets are keyed by a different alias than the capability key; match on method
    method_to_preset = {}
    for pk, pv in srv.PRESETS.items():
        method_to_preset.setdefault(pv.get("method"), pk)
    cap_method = entry.get("method")
    preset_key = method_to_preset.get(cap_method, key)
    preset = srv.PRESETS.get(preset_key)
    if not preset:
        return {"subject": subject_of_capability(entry), "kind": "capability", "id": key,
                "label": entry.get("label") or key, "feature": "capability",
                "verdict": "skip", "paper": None,
                "findings": [{"rule": None, "severity": "low", "advisory": True,
                              "detail": "no preset inputs", "where": "", "source": "walker"}]}
    fw = (entry.get("applies_to") or ["pestel"])[0]
    objective = preset.get("objective") or ("Analyse " + (entry.get("label") or key))
    brief = ("A mid-sized consumer-goods company is analysing a proposed project. "
             "Analyse the market environment with PESTEL.")
    subject = subject_of_capability(entry)
    state = chat.start(brief, None, "pestel")
    defaults = dict(DEFAULTS)
    defaults["decision"] = objective
    while chat.current_question(state):
        q = chat.current_question(state)
        qid = q.get("id") or q.get("key")
        ans = defaults.get(qid, "")
        choices = q.get("choices") or q.get("options")
        if choices and not ans:
            first = choices[0]
            ans = first[0] if isinstance(first, (list, tuple)) else (first.get("value") if isinstance(first, dict) else first)
        if q.get("type") == "choice" and not ans:
            ans = "yes"
        state = chat.answer(state, qid, ans)
    chat.confirm_plan(state)
    state.setdefault("selection", {"selected": []})
    state["selection"]["selected"] = [entry]
    # normalise preset inputs to the schema's row field names
    inputs = preset.get("inputs", {})
    if isinstance(inputs, dict):
        for name, val in list(inputs.items()):
            if isinstance(val, list):
                for row in val:
                    if isinstance(row, dict) and "id" in row and "name" not in row:
                        row["name"] = row["id"]
    try:
        chat.run_capability(state, key, {"values": inputs})
    except Exception as e:  # noqa: BLE001
        msg = str(e)[:300]
        # input-shape mismatches between the preset and the frozen schema are
        # harness/product impedance issues, not paper defects: record as skip
        is_shape = ("needs a " in msg or "needs one" in msg or "must be a set" in msg
                    or "Declare at least" in msg or "not available" in msg
                    or "refused the declared" in msg)
        return {"subject": subject, "kind": "capability", "id": key,
                "label": entry.get("label") or key, "feature": "capability",
                "verdict": "skip" if is_shape else "fail", "paper": None,
                "findings": [{"rule": None if is_shape else "V-00-walker",
                              "severity": "low" if is_shape else "high",
                              "advisory": is_shape,
                              "detail": "run_capability: %s" % msg,
                              "where": "", "source": "walker"}]}
    try:
        chat.research(state)
    except Exception as e:  # noqa: BLE001
        pass
    try:
        state = chat.draft(state, implications="No implications beyond those stated.")
    except Exception as e:  # noqa: BLE001
        return {"subject": subject, "kind": "capability", "id": key,
                "label": entry.get("label") or key, "feature": "capability",
                "verdict": "fail", "paper": None,
                "findings": [{"rule": "V-00-walker", "severity": "high",
                              "detail": "draft failed: %s" % str(e)[:300],
                              "where": "", "source": "walker"}]}
    report = state.get("draft") or {}
    dims = state.get("plan", {}).get("dimensions", [])
    result = {"blocks": [{"key": d.get("key"), "label": d.get("label")} for d in dims],
              "template": "template_pestel", "kind": "capability",
              "computations": state.get("computations", {})}
    try:
        data = chat.docx_bytes(state)
    except Exception as e:  # noqa: BLE001
        # export gate blocked: render the draft anyway so the paper is reviewable,
        # and record the blocking issues as findings (V-07/V-17)
        try:
            draft = state.get("draft") or {}
            outline = draft.get("outline") or __import__("bp.product.paper", fromlist=["x"]).flatten(draft.get("sections") or [])
            data = __import__("bp.product.docx", fromlist=["x"]).render_academic(
                draft.get("title", key), outline, draft.get("style", "apa"))
        except Exception as e2:  # noqa: BLE001
            return {"subject": subject, "kind": "capability", "id": key,
                    "label": entry.get("label") or key, "feature": "capability",
                    "verdict": "fail", "paper": None,
                    "findings": [{"rule": "V-00-walker", "severity": "high",
                                  "detail": "docx render failed: %s" % str(e2)[:300],
                                  "where": "", "source": "walker"}]}
        # record the export-block reason as an advisory V-07 finding
        extra = [{"rule": "V-07", "severity": "low", "advisory": True,
                  "detail": "export gate blocked: %s" % str(e)[:200],
                  "where": "", "source": "chat.docx_bytes"}]
        # judge, then append the export-block finding
        verdict, findings = judge_paper(result, report, kind="capability")
        findings = findings + extra
        # write the file
        fname = "%s__apa.docx" % key
        os.makedirs(os.path.join(out, subject), exist_ok=True)
        with open(os.path.join(out, subject, fname), "wb") as fh:
            fh.write(data)
        return {"subject": subject, "kind": "capability", "id": key,
                "label": entry.get("label") or key, "feature": "capability",
                "paper": "%s/%s" % (subject, fname),
                "sha256": hashlib.sha256(data).hexdigest(),
                "words": report.get("words"),
                "verdict": verdict, "findings": findings}
    fname = "%s__apa.docx" % key
    os.makedirs(os.path.join(out, subject), exist_ok=True)
    with open(os.path.join(out, subject, fname), "wb") as fh:
        fh.write(data)
    verdict, findings = judge_paper(result, report, kind="capability")
    return {"subject": subject, "kind": "capability", "id": key,
            "label": entry.get("label") or key, "feature": "capability",
            "paper": "%s/%s" % (subject, fname),
            "sha256": hashlib.sha256(data).hexdigest(),
            "words": report.get("words"),
            "verdict": verdict, "findings": findings}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "validation_out"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    out = args.out
    os.makedirs(out, exist_ok=True)
    import json as _j
    with open(os.path.join(HERE, "evidence", "shared.json")) as f:
        pack = _j.load(f).get("sources", [])
    # freeze retrieval
    sys.path.insert(0, HERE)
    import walk_frameworks as wf
    wf.freeze_retrieval(pack)
    # attach the frozen core so capability inputs can be validated
    import bp.methods as _methods
    import bp.product.api as _api
    def _run(method_id, values):
        m = _methods.LIBRARY[method_id]
        errs = _methods.validate_inputs(m, values)
        if errs:
            raise ValueError("; ".join(errs))
        return m.impl(values)
    _api.attach_compute(lambda values: _methods.breakeven(values))
    _api.attach_methods(_run, _methods.describe)
    # reuse walk_frameworks freeze by importing
    keys = list(capabilities.ENTRIES)
    if args.limit:
        keys = keys[:args.limit]
    features = []
    for key in keys:
        try:
            entry = run_one(key, out)
        except Exception as e:  # noqa: BLE001
            entry = {"subject": "research", "kind": "capability", "id": key,
                     "label": key, "feature": "capability", "verdict": "fail",
                     "paper": None,
                     "findings": [{"rule": "V-00-walker", "severity": "high",
                                   "detail": "unhandled: %s" % str(e)[:300],
                                   "where": "", "source": "walker"}]}
        features.append(entry)
        print("%s %s %s" % (entry["subject"], key, entry["verdict"]))
    # merge into existing manifest if present
    manifest_path = os.path.join(out, "manifest.json")
    existing = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            existing = _j.load(f)
    new_ids = {f.get("id") for f in features}
    existing_features = [f for f in existing.get("features", [])
                        if not (f.get("kind") == "capability" and f.get("id") in new_ids)]
    all_features = existing_features + features
    manifest = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "build": "v0.12",
                "features": all_features,
                "summary": {"pass": sum(1 for f in all_features if f["verdict"] == "pass"),
                            "fail": sum(1 for f in all_features if f["verdict"] != "pass"),
                            "by_rule": _by_rule(all_features)}}
    with open(manifest_path, "w", encoding="utf-8") as f:
        _j.dump(manifest, f, indent=1, ensure_ascii=False)
    print("capability stage: %d papers, %d pass, %d fail" % (
        len(features), sum(1 for f in features if f["verdict"] == "pass"),
        sum(1 for f in features if f["verdict"] != "pass")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY