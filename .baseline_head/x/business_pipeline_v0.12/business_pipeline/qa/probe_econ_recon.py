"""Reconnaissance probe for the economics QA session (read-only).

Writes `qa/baseline/econ_recon.json` and prints a short summary.

Checks, all of them mechanical:
  * every economics tool's `method` resolves in `bp.methods.LIBRARY`
  * every economics tool's `preset` exists in `bp.server.PRESETS` and launches that method
  * the method contract is complete for every tool (source of truth rank 1)
  * `related` tool ids and record `linked_methods` resolve
  * duplicate top-level definitions in `src/bp/**` (the shadowing bug class)
  * student notes: level / formula / steps / common mistakes / need

Usage:  python qa/probe_econ_recon.py
"""
import ast
import json
import pathlib
import sys

sys.path.insert(0, "src")

from bp import methods, server                     # noqa: E402
from bp.product import subjects, framework_profiles  # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent
CONTRACT_FIELDS = ("intended_use", "unsupported_use", "assumptions", "limitations",
                   "test_names", "metric", "unit", "tier", "claim_ceiling")
VALID_TIERS = {"T1", "T2", "T3", "T4"}
VALID_CEILINGS = {"descriptive", "associational", "predictive"}


def duplicates_in(path):
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    seen = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            seen.setdefault(node.name, []).append(node.lineno)
    return {name: lines for name, lines in seen.items() if len(lines) > 1}


def main():
    detail = subjects.detail("economics")
    tools = detail["tools"]
    tool_keys = {tool["key"] for tool in tools}

    report = {"counts": {}, "findings": [], "tools": [], "records": [], "method_gaps": []}

    def note(kind, detail_text, **extra):
        row = {"kind": kind, "detail": detail_text}
        row.update(extra)
        report["findings"].append(row)

    report["counts"] = {
        "tools": len(tools),
        "worksheets": len(detail["worksheets"]),
        "records": len(detail["records"]),
        "theories": len(detail["theories"]),
        "glossary": len(detail["glossary"]),
        "tiles": len(detail["tiles"]),
        "start_steps": len(detail["start_steps"]),
        "does_not": len(detail["does_not"]),
        "methods_in_library": len(methods.LIBRARY),
        "presets": len(server.PRESETS),
    }


    # ---- per tool -----------------------------------------------------------
    for tool in tools:
        row = {
            "key": tool["key"],
            "label": tool["label"],
            "method": tool["method"],
            "preset": tool["preset"],
            "group": tool.get("group"),
            "level": tool.get("level"),
            "diagram": tool.get("diagram"),
            "has_formula": bool(tool.get("formula")),
            "n_steps": len(tool.get("steps") or []),
            "n_mistakes": len(tool.get("common_mistakes") or []),
            "need": tool.get("need"),
            "related": tool.get("related") or [],
        }
        method = methods.LIBRARY.get(tool["method"])
        if method is None:
            note("TOOL_METHOD_MISSING", "tool %s -> unknown method %s"
                 % (tool["key"], tool["method"]), tool=tool["key"])
            row["method_resolved"] = False
            report["tools"].append(row)
            continue
        row["method_resolved"] = True
        row["tier"] = method.tier
        row["metric"] = method.metric
        row["unit"] = method.unit
        row["claim_ceiling"] = method.claim_ceiling
        row["category"] = getattr(method, "category", None)
        row["inputs"] = sorted((method.input_schema or {}).keys())
        row["n_tests"] = len(method.test_names or ())

        gaps = [field for field in CONTRACT_FIELDS
                if not getattr(method, field, None)]
        if gaps:
            note("CONTRACT_INCOMPLETE", "%s (%s) missing %s"
                 % (tool["method"], tool["key"], ",".join(gaps)), tool=tool["key"])
            report["method_gaps"].append({"method": tool["method"], "missing": gaps})
        if method.tier not in VALID_TIERS:
            note("BAD_TIER", "%s tier=%r" % (tool["method"], method.tier))
        if method.claim_ceiling not in VALID_CEILINGS:
            note("BAD_CEILING", "%s ceiling=%r" % (tool["method"], method.claim_ceiling))
        schema = method.input_schema or {}
        bad_fields = [name for name, spec in schema.items()
                      if not isinstance(spec, dict) or "type" not in spec or "desc" not in spec]
        if bad_fields:
            note("SCHEMA_FIELD_INCOMPLETE", "%s: %s" % (tool["method"], ",".join(bad_fields)),
                 tool=tool["key"])

        # preset wiring
        preset = server.PRESETS.get(tool["preset"])
        if preset is None:
            note("PRESET_MISSING", "tool %s preset %r not in PRESETS"
                 % (tool["key"], tool["preset"]), tool=tool["key"])
        else:
            preset_method = preset.get("method") if isinstance(preset, dict) else getattr(
                preset, "method", None)
            if preset_method != tool["method"]:
                note("PRESET_METHOD_MISMATCH", "tool %s preset %r launches %r not %r"
                     % (tool["key"], tool["preset"], preset_method, tool["method"]),
                     tool=tool["key"])

        # student notes
        if not tool.get("formula"):
            note("NO_FORMULA", "tool %s has no formula note" % tool["key"], tool=tool["key"])
        if not (tool.get("steps") or []):
            note("NO_STEPS", "tool %s has no steps" % tool["key"], tool=tool["key"])
        if not (tool.get("common_mistakes") or []):
            note("NO_MISTAKES", "tool %s has no common mistakes" % tool["key"],
                 tool=tool["key"])
        if tool.get("need") is None:
            note("NO_NEED", "tool %s declares no 'need' text" % tool["key"], tool=tool["key"])
        for related in tool.get("related") or []:
            if related not in tool_keys:
                note("RELATED_UNRESOLVED", "tool %s related id %r is not an economics tool"
                     % (tool["key"], related), tool=tool["key"])

        report["tools"].append(row)


    # ---- records ------------------------------------------------------------
    for record in detail["records"]:
        row = {
            "id": record.get("id"),
            "name": record.get("name"),
            "form": record.get("form"),
            "template": record.get("template"),
            "linked_methods": record.get("linked_methods") or [],
            "status_note": record.get("status_note"),
        }
        for mid in row["linked_methods"]:
            if mid not in methods.LIBRARY:
                note("RECORD_METHOD_MISSING", "record %s links unknown method %r"
                     % (row["id"], mid))
        if row["template"] and row["template"] not in framework_profiles.PROFILES:
            note("RECORD_TEMPLATE_MISSING", "record %s names template %r"
                 % (row["id"], row["template"]))
        report["records"].append(row)

    # ---- duplicate definitions across the package ---------------------------
    dups = {}
    for path in sorted((APP / "src" / "bp").rglob("*.py")):
        found = duplicates_in(path)
        if found:
            dups[str(path.relative_to(APP))] = found
    report["duplicate_definitions"] = dups
    for path, found in dups.items():
        for name, lines in found.items():
            note("DUPLICATE_DEFINITION", "%s: %s at lines %s" % (path, name, lines))

    (APP / "qa" / "baseline" / "econ_recon.json").write_text(
        json.dumps(report, indent=1, default=str), encoding="utf-8")

    print("counts:", json.dumps(report["counts"]))
    print("findings:", len(report["findings"]))
    kinds = {}
    for finding in report["findings"]:
        kinds[finding["kind"]] = kinds.get(finding["kind"], 0) + 1
    for kind in sorted(kinds):
        print("  %-28s %d" % (kind, kinds[kind]))


if __name__ == "__main__":
    main()
