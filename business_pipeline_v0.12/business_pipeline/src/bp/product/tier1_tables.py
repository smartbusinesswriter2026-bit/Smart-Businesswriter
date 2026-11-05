"""Tier-1 data tables: the mutable knowledge the self-healing loop improves.

Lazy-loaded to avoid circular imports with statements.py and schedules.py.
Seeds from code constants only when the JSON file is absent (at runtime, not import time).
"""
import json
import os

_STORE_DIR = os.environ.get("BP_STATEMENT_LIBRARY_DIR") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "statement_library")
_TABLES_PATH = os.path.join(_STORE_DIR, "tier1_tables.json")

_rules_cache = None
_schemas_cache = None


def _seed_rules():
    try:
        from . import statements as S
        return [list(r) for r in S._RULES_SEED]
    except Exception:
        return None


def _seed_schemas():
    try:
        from . import schedule_routes as SCH
        out = {}
        for kind, schema in SCH._SCHEMAS_SEED.items():
            out[kind] = {
                "request": schema["request"],
                "required": list(schema.get("required", ())),
                "require_all": list(schema.get("require_all", ())),
                "require_any": list(schema.get("require_any", ())) if schema.get("require_any") else [],
                "figures": [[k, p, s] for k, p, s in schema.get("figures", ())],
            }
        return out
    except Exception:
        return None


def _load():
    global _rules_cache, _schemas_cache
    if _rules_cache is not None:
        return _rules_cache, _schemas_cache
    rules, schemas = None, None
    if os.path.exists(_TABLES_PATH):
        try:
            with open(_TABLES_PATH, encoding="utf-8") as f:
                data = json.load(f)
            rules = data.get("rules")
            schemas = data.get("schemas")
        except Exception:
            pass
    if rules is None:
        rules = _seed_rules()
        schemas = _seed_schemas()
        if rules is not None and schemas is not None:
            _save(rules, schemas, version=1)
    # Convert types
    if rules is not None:
        rules = [tuple(r) for r in rules]
    converted_schemas = None
    if schemas is not None:
        converted_schemas = {}
        for kind, schema in (schemas or {}).items():
            converted_schemas[kind] = {
                "request": schema["request"],
                "required": tuple(schema.get("required", [])),
                "require_all": tuple(schema.get("require_all", [])),
                "require_any": tuple(schema.get("require_any", [])),
                "figures": [tuple(f) for f in schema.get("figures", [])],
            }
    _rules_cache = rules
    _schemas_cache = converted_schemas
    return _rules_cache, _schemas_cache


def _save(rules, schemas, version=None):
    os.makedirs(_STORE_DIR, exist_ok=True)
    data = {"version": version or 1,
            "rules": [list(r) for r in rules],
            "schemas": {k: {"request": v["request"],
                            "required": list(v.get("required", ())),
                            "require_all": list(v.get("require_all", ())),
                            "require_any": list(v.get("require_any", ())) if v.get("require_any") else [],
                            "figures": [[kk, p, ss] for kk, p, ss in v.get("figures", ())]}
                       for k, v in schemas.items()}}
    with open(_TABLES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_rules():
    rules, _ = _load()
    return rules if rules is not None else None


def get_schemas():
    _, schemas = _load()
    return schemas if schemas is not None else None


def append_rule(rule_tuple):
    """Append a new rule to RULES (self-healing loop). Versioned, reversible."""
    rules, schemas = _load()
    if rules is None:
        rules = _seed_rules() or []
    rules = list(rules) + [rule_tuple]
    if schemas is None:
        schemas = _seed_schemas() or {}
    _save(rules, schemas)
    # Update cache
    global _rules_cache, _schemas_cache
    _rules_cache = [tuple(r) for r in rules]
    _schemas_cache = None
    _load()  # reload to convert types


def append_schema(kind, schema_dict):
    """Append a new schema to SCHEMAS (self-healing loop)."""
    rules, schemas = _load()
    if rules is None:
        rules = _seed_rules() or []
    if schemas is None:
        schemas = _seed_schemas() or {}
    schemas[kind] = schema_dict
    _save(rules, schemas)
    global _rules_cache, _schemas_cache
    _rules_cache = None
    _schemas_cache = None
    _load()


def reload():
    """Reload tables from disk."""
    global _rules_cache, _schemas_cache
    _rules_cache = None
    _schemas_cache = None
    return _load()
