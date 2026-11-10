"""The method catalogue: one generated record per frozen method.

This is the single source of truth for *which computations exist* and *how they
are typed*.  It is generated from ``bp.methods.LIBRARY`` (which, after the
finance additions are registered at import, holds every callable method) plus
the layers that surface a method:

- ``capabilities.ENTRIES``  -- the paper-conductor blocks (a curated subset);
- ``subjects.TOOL_INFO``     -- the shelf-tool descriptors;
- ``web/calculator.json``    -- the calculator's shelf list;
- ``data/calc_inputs_v0_1.json`` -- input metadata (cross-check only).

Nothing here computes a number and nothing here invents a method.  It only
names what the core already exposes, so the product can stop drifting from the
core by hand-maintained counts.
"""

import json
from collections import defaultdict
from pathlib import Path

from . import capabilities, subjects
from .. import methods

FORMAT = "bp-method-catalogue/1"
VERSION = 1

#: A method may be a paper block, a shelf tool, a service, an internal helper,
#: or deprecated.  Every method must carry exactly one.
STATUSES = ("paper", "tile", "service", "internal", "deprecated")

#: Methods that are a service behind the statements/workbench lane, not a plain
#: data-table computation.  Their ``engagement_spec`` input is not a table.
SERVICE_METHODS = frozenset({"management_accounts", "trial_balance_check"})

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]
_CALCULATOR = _REPO / "web" / "calculator.json"
_REGISTRY = _HERE.parents[1] / "data" / "registry_v0_2.json"
_CALC_INPUTS = _HERE.parent / "data" / "calc_inputs_v0_1.json"
_CATALOGUE = _HERE.parent / "data" / "method_catalogue_v1.json"

_CACHE = None


def _committed():
    """The committed catalogue, loaded once.  The product reads this so a runtime
    caller does not need to import the frozen core to see a method's schema."""
    global _CACHE
    if _CACHE is None:
        _CACHE = load(_CATALOGUE)
    return _CACHE


def schema_for(method):
    """The declared input schema of one method, from the committed catalogue."""
    for row in _committed().get("methods") or []:
        if row.get("method") == method:
            return dict(row.get("schema") or {})
    return {}


def status_for(method):
    """The catalogue status of one method, or "" when it is not a library method."""
    for row in _committed().get("methods") or []:
        if row.get("method") == method:
            return row.get("status") or ""
    return ""


def _label(key):
    return " ".join(word.capitalize() for word in key.split("_"))


def _calculator_tools():
    """method -> set of subject ids, and method -> first label, from calculator.json."""
    subjects_by_method = defaultdict(set)
    labels = {}
    data = json.loads(_CALCULATOR.read_text(encoding="utf-8"))
    for group in data.get("groups") or []:
        for tool in group.get("tools") or []:
            method = tool.get("method")
            if not method:
                continue
            subjects_by_method[method].add(group.get("id"))
            labels.setdefault(method, tool.get("label") or _label(method))
    return subjects_by_method, labels


def _framework_count():
    data = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    return len(data.get("records") or [])


def _statement_spec_count():
    from . import financial_computations
    return len(financial_computations.REGISTRY.all())


def _data_shapes(schema):
    """The data shapes a schema can accept, from its own input types only."""
    shapes = set()
    for spec in (schema or {}).values():
        kind = (spec or {}).get("type")
        if kind in ("value_list", "decimal_list", "code_list", "column_map"):
            shapes.add("column")
        elif kind == "count_table":
            shapes.add("count_table")
        elif kind == "value_matrix":
            shapes.add("matrix")
        elif kind == "records":
            shapes.add("records")
        elif kind == "rows":
            shapes.add("rows")
        elif kind in ("object", "engagement_spec"):
            shapes.add("structured")
        elif kind:
            shapes.add("cell")
    return sorted(shapes)


def build():
    """One compact record per frozen method, in stable key order."""
    library = methods.LIBRARY
    capability_methods = {row["method"] for row in capabilities.ENTRIES.values()}
    tool_subjects, tool_labels = _calculator_tools()
    tool_info_methods = {row.get("method") for row in subjects.TOOL_INFO.values()
                         if row.get("method")}
    for key, row in subjects.TOOL_INFO.items():
        method = row.get("method")
        if method and method not in tool_labels:
            tool_labels[method] = row.get("label") or _label(method)

    surfaced = tool_info_methods | set(tool_subjects)

    methods_out = []
    for key in sorted(library):
        described = methods.describe(key)
        schema = described.get("input_schema") or {}
        status = ("paper" if key in capability_methods
                  else "service" if key in SERVICE_METHODS
                  else "tile")
        reviewed = key in capability_methods or key in surfaced
        methods_out.append({
            "key": key,
            "method": key,
            "label": tool_labels.get(key) or _label(key),
            "tier": described.get("tier") or "",
            "category": described.get("category") or "",
            "status": status,
            "paper": key in capability_methods,
            "review": "" if reviewed else "proposed",
            "subjects": sorted(tool_subjects.get(key) or []),
            "schema": schema,
            "data_shapes": _data_shapes(schema),
        })

    calc_inputs_methods = set(json.loads(_CALC_INPUTS.read_text(encoding="utf-8"))["methods"])

    source = {
        "library": len(library),
        "capability_entries": len(capabilities.ENTRIES),
        "capability_methods": len(capability_methods),
        "tool_info_entries": len(subjects.TOOL_INFO),
        "tool_info_methods": len(tool_info_methods),
        "calculator_items": sum(len(group.get("tools") or [])
                                for group in json.loads(_CALCULATOR.read_text(encoding="utf-8"))["groups"]),
        "calculator_methods": len(tool_subjects),
        "calc_inputs_methods": len(calc_inputs_methods),
        "statement_specs": _statement_spec_count(),
        "frameworks": _framework_count(),
    }

    # Services/templates that live beside the method library, not inside it.
    non_method = [
        {"key": "business_plan", "kind": "service"},
        {"key": "case_decision", "kind": "template"},
    ]

    return {
        "format": FORMAT,
        "version": VERSION,
        "source": source,
        "non_method": non_method,
        "methods": methods_out,
    }


def write(path):
    """Write the catalogue as JSON, deterministically."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
