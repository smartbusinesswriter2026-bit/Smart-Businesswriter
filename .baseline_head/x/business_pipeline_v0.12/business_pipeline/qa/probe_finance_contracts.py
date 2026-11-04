"""Dump the frozen contract behind every finance tool, for the QA manual.

Read-only probe.  For each tool on the finance shelf it prints the tile's
student-facing promise (formula, level, steps, common mistakes), the
`bp.methods.Method` contract (tier, metric, unit, claim ceiling, schema,
refusals), the preset that launches it, whether that preset's default inputs
pass `validate_inputs`, whether the method delivers on those inputs and whether
every declared self-test passes.

Nothing is written except the file named on the command line.

Usage:  PYTHONPATH=src python qa/probe_finance_contracts.py [out.json]
"""
import json
import sys
import traceback

sys.path.insert(0, "src")

from bp import server  # noqa: E402
from bp.methods import LIBRARY, validate_inputs  # noqa: E402
from bp.product import subjects  # noqa: E402


def presets_for(method):
    """Every preset id whose declared method is `method`, with its default inputs."""
    out = []
    for preset_id, request in server.PRESETS.items():
        if request.get("method") == method:
            out.append({"preset": preset_id, "currency": request.get("currency"),
                        "period": request.get("period"),
                        "objective": request.get("objective"),
                        "inputs": request.get("inputs")})
    return out


def describe_method(method_id):
    m = LIBRARY.get(method_id)
    if m is None:
        return {"in_library": False}
    schema = []
    for name, spec in (m.input_schema or {}).items():
        schema.append({"name": name, "type": spec.get("type"),
                       "required": spec.get("required", True),
                       "desc": spec.get("desc"),
                       "choices": spec.get("choices"),
                       "items": spec.get("items")})
    return {
        "in_library": True,
        "name": m.name, "tier": m.tier, "metric": m.metric, "unit": m.unit,
        "claim_ceiling": m.claim_ceiling, "version": m.version,
        "status": m.status, "category": m.category,
        "test_names": list(m.test_names or ()),
        "intended_use": m.intended_use, "unsupported_use": m.unsupported_use,
        "assumptions": list(m.assumptions or ()),
        "limitations": list(m.limitations or ()),
        "defaults": list(m.defaults or ()),
        "output_units": dict(m.output_units or {}),
        "output_precision": dict(m.output_precision or {}),
        "has_typing": m.typing is not None,
        "has_profile": m.profile is not None,
        "has_mapping": m.mapping is not None,
        "assumption_check_names": list(m.assumption_check_names or ()),
        "mapping_check_names": list(m.mapping_check_names or ()),
        "schema": schema,
    }


def run_method(method_id, inputs):
    """Run the method and its own contract checks on one input set."""
    m = LIBRARY[method_id]
    result = {"input_errors": validate_inputs(m, inputs), "output": None,
              "output_keys": [], "checks": [], "checks_all_ok": None,
              "profile_issues": None, "error": None}
    if result["input_errors"]:
        return result
    try:
        out = m.impl(dict(inputs))
    except Exception as exc:  # noqa: BLE001 - a probe records what happened
        result["error"] = "%s: %s" % (type(exc).__name__, exc)
        return result
    if isinstance(out, dict):
        result["output"] = {k: (str(v) if not isinstance(v, (int, float, str, bool, type(None)))
                                else v) for k, v in out.items()}
        result["output_keys"] = sorted(out.keys())
    else:
        result["output"] = str(out)
    try:
        checks = m.tests(dict(inputs), m.impl) if m.tests else []
        result["checks"] = [(str(name), bool(ok)) for name, ok in checks]
        result["checks_all_ok"] = all(bool(ok) for _, ok in result["checks"])
    except Exception as exc:  # noqa: BLE001
        result["error"] = "tests() raised %s: %s" % (type(exc).__name__, exc)
    try:
        if m.profile:
            result["profile_issues"] = list(m.profile(dict(inputs)))
    except Exception as exc:  # noqa: BLE001
        result["profile_issues"] = ["profile() raised %s: %s" % (type(exc).__name__, exc)]
    return result


def main(argv):
    detail = subjects.detail("finance")
    rows = []
    for tool in detail.get("tools") or []:
        method_id = tool["method"]
        rows.append({"tool": tool["key"], "preset": tool.get("preset"), "method": method_id,
                     "group": tool.get("group"), "level": tool.get("level"),
                     "label": tool.get("label"), "what": tool.get("what"),
                     "need": tool.get("need"), "formula": tool.get("formula"),
                     "period": tool.get("period"), "diagram": tool.get("diagram"),
                     "steps": len(tool.get("steps") or []),
                     "common_mistakes": len(tool.get("common_mistakes") or []),
                     "related": tool.get("related"),
                     "contract": describe_method(method_id)})

    # Presets that launch these methods, and whether their defaults work.
    for row in rows:
        launches = presets_for(row["method"])
        row["presets"] = [{"preset": p["preset"], "currency": p["currency"],
                           "period": p["period"], "objective": p["objective"]}
                          for p in launches]
        row["preset_matches_tool"] = (row["preset"] in [p["preset"] for p in launches]
                                      if row["preset"] else None)
        run = next((p for p in launches if p["preset"] == row["preset"]),
                   launches[0] if launches else None)
        if run and row["contract"]["in_library"]:
            row["run_on_preset_defaults"] = run_method(row["method"], run["inputs"])
            row["run_on_preset_defaults"]["preset_used"] = run["preset"]
        else:
            row["run_on_preset_defaults"] = {"note": "no preset launches this method"}

    shelf_methods = {row["method"] for row in rows}
    orphan_presets = sorted(pid for pid, req in server.PRESETS.items()
                            if req.get("method") not in LIBRARY)
    text = json.dumps({"tool_count": len(rows), "rows": rows,
                       "presets_with_unknown_method": orphan_presets,
                       "shelf_methods": sorted(shelf_methods)},
                      indent=1, default=str)
    if len(argv) > 1:
        with open(argv[1], "w", encoding="utf-8") as handle:
            handle.write(text)
        print("wrote %s" % argv[1])
    else:
        print(text)


if __name__ == "__main__":
    try:
        main(sys.argv)
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(1)
