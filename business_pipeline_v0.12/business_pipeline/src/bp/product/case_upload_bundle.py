"""Upload a {topic, problems: [...]} bundle as one case per problem."""

import json

from . import case_store
from . import paper_batch

MAX_UPLOAD = 25 * 1024 * 1024


def _dry_run(tile, inputs):
    from . import case_upload as _cu
    return _cu._dry_run(tile, inputs)


_INPUT_MAP = {
    "breakeven": {
        "selling_price": "price",
        "variable_cost_per_unit": "variable",
        "fixed_costs": "fixed",
        "actual_units": "expected_units",
        "target_profit": "target_profit",
    },
}

_OUTPUT_MAP = {
    "breakeven": {
        "contribution_per_unit": "contribution_margin",
        "break_even_units": "breakeven_units",
        "break_even_revenue": "breakeven_revenue",
        "margin_of_safety_units": "margin_of_safety_units",
        "margin_of_safety_ratio_pct": "margin_of_safety_ratio",
        "target_profit_units": "target_profit_units",
    },
}

_PERCENT_OUTPUTS = {"margin_of_safety_ratio_pct"}

#: The bundle's own topic decides the tile.  A file is about one topic, and the
#: upload form's tile is only the fallback when the bundle does not name one.
_TOPIC_TILES = {
    "break-even": "breakeven",
    "breakeven": "breakeven",
    "multi-product break-even": "multibreakeven",
    "depreciation": "depreciation",
    "financial statement ratios": "ratios",
    "ratios": "ratios",
    "dupont": "dupont",
    "common-size and trend": "trendanalysis",
    "trend": "trendanalysis",
    "standard costing": "scv",
    "standard-cost variances": "scv",
    "activity-based costing": "abc",
    "sales price, mix and volume variances": "salesvar",
    "sales variances": "salesvar",
    "working capital": "workingcapital",
    "loan amortisation": "loan",
    "loan amortization": "loan",
    "projected statements": "proforma",
    "price and volume sensitivity": "sensitivity",
    "sensitivity": "sensitivity",
    "sales and profit projection": "salesprojection",
    "sales from market share": "frommarket",
    "tax on declared rates": "tax",
    "tax": "tax",
    "checking a trial balance": "tbcheck",
    "trial balance": "tbcheck",
    "bookkeeping engagement": "accounts",
    "management accounts": "accounts",
}


def _tile_for_topic(topic, fallback):
    key = " ".join(str(topic or "").lower().replace("&", "and").split())
    if not key:
        return fallback
    if key in _TOPIC_TILES:
        return _TOPIC_TILES[key]
    # a whole word only: "multibreakeven" must not match "breakeven"
    import re as _re
    for needle in sorted(_TOPIC_TILES, key=len, reverse=True):
        if _re.search(r"(?<![a-z])" + _re.escape(needle) + r"(?![a-z])", key):
            return _TOPIC_TILES[needle]
    return fallback


def _map_inputs(tile_key, data):
    data = data if isinstance(data, dict) else {}
    if tile_key == "breakeven":
        out = {}
        if "selling_price" in data:
            out["price"] = data["selling_price"]
        if "variable_cost_per_unit" in data:
            out["variable"] = data["variable_cost_per_unit"]
        if "variable_cost_pct" in data and "selling_price" in data:
            try:
                out["variable"] = str(round(float(data["selling_price"]) * float(data["variable_cost_pct"]) / 100.0, 6))
            except (TypeError, ValueError):
                pass
        if "fixed_costs" in data:
            out["fixed"] = data["fixed_costs"]
        if "actual_units" in data:
            out["expected_units"] = data["actual_units"]
        if "target_profit" in data:
            out["target_profit"] = data["target_profit"]
        return out
    return {str(k): v for k, v in data.items()}


def _map_outputs(tile_key, answer):
    answer = answer if isinstance(answer, dict) else {}
    if tile_key == "breakeven":
        out = {}
        for src, dst in _OUTPUT_MAP["breakeven"].items():
            if src in answer:
                value = answer[src]
                if src in _PERCENT_OUTPUTS and isinstance(value, (int, float)):
                    value = value / 100.0
                out[dst] = value
        return out
    return {str(k): v for k, v in answer.items()}


def _skip_reason(tile_key, problem):
    problem = problem if isinstance(problem, dict) else {}
    if tile_key == "breakeven":
        data = problem.get("data") or {}
        if "year_1_price" in data or "product_a_price" in data:
            return ("multi-period or multi-product problem: one case holds one period and one product; "
                    "split it into separate cases")
    return None


def upload_bundle(subject, tile_key, filename, raw):
    """Parse a {topic, problems: [...]} bundle and store one case per problem."""
    if not isinstance(raw, (bytes, bytearray)) or not raw:
        raise ValueError("the uploaded file is empty")
    if len(raw) > MAX_UPLOAD:
        raise ValueError("the file is over the 5 MB upload limit")
    from . import case_upload as _cu
    try:
        document = json.loads(bytes(raw).decode("utf-8"))
    except Exception as error:
        raise ValueError("the JSON is not readable: " + str(error)[:160])
    if not isinstance(document, dict) or not isinstance(document.get("problems"), list):
        raise ValueError("this is not a problem bundle: it needs a 'problems' list")
    problems = document["problems"]
    if not problems:
        raise ValueError("the bundle contains no problems")
    # The bundle's own topic names the tile; the form's selection is only a fallback.
    resolved = _tile_for_topic(document.get("topic"), tile_key)
    try:
        subject_info, _group, tile = paper_batch._find_tile(subject, resolved)
    except (KeyError, ValueError):
        subject_info, _group, tile = paper_batch._find_tile(subject, tile_key)
        resolved = tile_key
    tile_key = resolved

    stored, skipped, errors = [], [], []
    for index, problem in enumerate(problems, start=1):
        problem = problem if isinstance(problem, dict) else {}
        pid = problem.get("id") or index
        reason = _skip_reason(tile_key, problem)
        if reason:
            skipped.append((pid, reason))
            continue
        reject = bool(problem.get("reject"))
        inputs = _map_inputs(tile_key, problem.get("data"))
        instruction = str(problem.get("problem") or problem.get("instruction") or "").strip()
        if not instruction:
            skipped.append((pid, "the problem has no text"))
            continue

        if reject:
            expected = {"status": "error"}
            recorded = None
            try:
                recorded = _cu._dry_run(tile, inputs) if inputs else None
            except ValueError:
                recorded = None
            if recorded is not None:
                expected = {"status": "ok", "result": case_store._recorded(recorded),
                            "contains": [tile.get("label") or tile_key, "What you declared", "How the figures were checked"],
                            "contract": {"sections": ["Result", "Inputs and results",
                                                      "How the figures were checked"]},
                            "xlsx_sheets": ["Summary", "Inputs", "Results", "Record"]}
        else:
            try:
                recorded = _cu._dry_run(tile, inputs)
            except ValueError as error:
                skipped.append((pid, "the engine refused it: " + str(error)[:120]))
                continue
            mapped = _map_outputs(tile_key, problem.get("answer"))
            recorded_map = case_store._recorded(recorded) or {}
            for key, value in recorded_map.items():
                mapped.setdefault(key, value)
            # A percentage given to two decimals (33.33) cannot be compared to the
            # engine's full-precision decimal (0.333333...) at the runner's tolerance,
            # so an answer that is right to the stated precision is kept as the
            # engine's value and noted; an answer that is wrong by more than that
            # stays as given and the case fails loudly.
            percent_destinations = {"margin_of_safety_ratio"}
            for key in list(mapped):
                if key in percent_destinations and key in recorded_map:
                    try:
                        if abs(float(mapped[key]) - float(recorded_map[key])) < 1e-3:
                            mapped[key] = recorded_map[key]
                    except (TypeError, ValueError):
                        pass
            expected = {"status": "ok", "result": mapped,
                        "contains": [tile.get("label") or tile_key, "What you declared", "How the figures were checked"],
                        "contract": {"sections": ["Result", "Inputs and results",
                                                  "How the figures were checked"]},
                        "xlsx_sheets": ["Summary", "Inputs", "Results", "Record"]}

        try:
            payload = _cu._store(subject, tile_key, filename, instruction, inputs or {}, recorded, expected)
            stored.append(payload["id"])
        except Exception as error:
            errors.append((pid, str(error)[:160]))

    return {"stored": stored, "skipped": skipped, "errors": errors,
            "total": len(problems), "tile": tile_key}
