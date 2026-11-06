"""Stage 4 — the compute-tool walker.

For every compute tool declared on a subject shelf (subjects.compute_tools(),
148 of them) this drives the real session path: SessionManager.create with
the tool's preset objective/inputs -> confirm -> deliverables.write_export
(working papers, xlsx), with no model and no network.  Records pass/skip/fail
in validation_out/manifest.json under kind="compute".

Usage (from business_pipeline/):
    PYTHONPATH=src python scripts/validation/walk_compute.py [--limit N]
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

from bp.product import subjects  # noqa: E402
import bp.server as srv  # noqa: E402
from bp.session import SessionManager  # noqa: E402
from bp.product import deliverables as D  # noqa: E402

# map tool key -> subject
KEY2SUBJ = {}
for sid in ["accounting", "finance", "economics", "management", "project-management",
            "entrepreneurship", "operations", "supply-chain", "marketing", "people", "research"]:
    for t in subjects.detail(sid)["tools"]:
        KEY2SUBJ[t["key"]] = sid


def run_one(tool, out):
    key = tool["key"]
    subject = KEY2SUBJ.get(key, "research")
    preset_key = tool.get("preset") or key
    preset = srv.PRESETS.get(preset_key)
    if not preset:
        return {"subject": subject, "kind": "compute", "id": key,
                "label": tool.get("label") or key, "feature": "compute",
                "verdict": "skip", "paper": None,
                "findings": [{"rule": None, "severity": "low", "advisory": True,
                              "detail": "no preset inputs", "where": "", "source": "walker"}]}
    sm = SessionManager()
    req = {"objective": preset.get("objective") or tool.get("label") or key,
           "inputs": preset.get("inputs") or {}}
    try:
        sess = sm.create(req)
        sess.confirm(True)
    except Exception as e:  # noqa: BLE001
        return {"subject": subject, "kind": "compute", "id": key,
                "label": tool.get("label") or key, "feature": "compute",
                "verdict": "fail", "paper": None,
                "findings": [{"rule": "V-00-walker", "severity": "high",
                              "detail": "session failed: %s" % str(e)[:300],
                              "where": "", "source": "walker"}]}
    if sess.delivery is None or sess.delivery.status != "delivered":
        reason = getattr(sess.delivery, "blocked_reason", None) if sess.delivery else "no delivery"
        return {"subject": subject, "kind": "compute", "id": key,
                "label": tool.get("label") or key, "feature": "compute",
                "verdict": "skip", "paper": None,
                "findings": [{"rule": None, "severity": "low", "advisory": True,
                              "detail": "session not delivered: %s" % str(reason)[:200],
                              "where": "", "source": "walker"}]}
    bundle = {"title": tool.get("label") or key, "id": sess.id,
              "delivery": {"report": sess.delivery.report, "appendix": sess.delivery.appendix}}
    os.makedirs(os.path.join(out, subject), exist_ok=True)
    dest = os.path.join(out, subject, "%s.xlsx" % key)
    try:
        D.write_export(bundle, "workpapers", "xlsx", dest)
    except Exception as e:  # noqa: BLE001
        return {"subject": subject, "kind": "compute", "id": key,
                "label": tool.get("label") or key, "feature": "compute",
                "verdict": "fail", "paper": None,
                "findings": [{"rule": "V-00-walker", "severity": "high",
                              "detail": "write_export failed: %s" % str(e)[:300],
                              "where": "", "source": "walker"}]}
    return {"subject": subject, "kind": "compute", "id": key,
            "label": tool.get("label") or key, "feature": "compute",
            "paper": "%s/%s.xlsx" % (subject, key),
            "sha256": hashlib.sha256(open(dest, "rb").read()).hexdigest(),
            "verdict": "pass", "findings": []}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "validation_out"))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    out = args.out
    os.makedirs(out, exist_ok=True)
    tools = subjects.compute_tools()
    if args.limit:
        tools = tools[:args.limit]
    features = []
    for tool in tools:
        try:
            entry = run_one(tool, out)
        except Exception as e:  # noqa: BLE001
            entry = {"subject": "research", "kind": "compute", "id": tool["key"],
                     "label": tool.get("label") or tool["key"], "feature": "compute",
                     "verdict": "fail", "paper": None,
                     "findings": [{"rule": "V-00-walker", "severity": "high",
                                   "detail": "unhandled: %s" % str(e)[:300],
                                   "where": "", "source": "walker"}]}
        features.append(entry)
        print("%s %s %s" % (entry["subject"], tool["key"], entry["verdict"]))
    manifest_path = os.path.join(out, "manifest.json")
    existing = {}
    if os.path.isfile(manifest_path):
        with open(manifest_path, encoding="utf-8") as f:
            existing = json.load(f)
    new_ids = {f.get("id") for f in features}
    existing_features = [f for f in existing.get("features", [])
                        if not (f.get("kind") == "compute" and f.get("id") in new_ids)]
    all_features = existing_features + features
    manifest = {"generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "build": "v0.12",
                "features": all_features,
                "summary": {"pass": sum(1 for f in all_features if f["verdict"] == "pass"),
                            "fail": sum(1 for f in all_features if f["verdict"] not in ("pass", "skip")),
                            "skip": sum(1 for f in all_features if f["verdict"] == "skip"),
                            "by_rule": {}}}
    # by_rule
    counts = {}
    for f in all_features:
        for x in f.get("findings", []):
            if x.get("rule"):
                counts[x["rule"]] = counts.get(x["rule"], 0) + 1
    manifest["summary"]["by_rule"] = counts
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    print("compute stage: %d tools, %d pass, %d fail, %d skip" % (
        len(features), sum(1 for f in features if f["verdict"] == "pass"),
        sum(1 for f in features if f["verdict"] == "fail"),
        sum(1 for f in features if f["verdict"] == "skip")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY