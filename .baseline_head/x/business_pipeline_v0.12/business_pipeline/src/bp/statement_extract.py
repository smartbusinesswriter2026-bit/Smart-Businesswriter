"""The one model-touching step: read a problem's words into balanced journal lines, and nothing else.

Tip 1 puts the whole boundary in one sentence: *"Translate each transaction into debits and credits.
This is the only step that needs language understanding."* Tip 2 makes it enforceable: the model
returns schema-shaped data, a validator proves it, and every later stage is code.

So this module does three things and no arithmetic:

1. states the contract the model must satisfy (`CONTRACT`, `system_prompt`, `user_prompt`);
2. parses the model's JSON and refuses anything off-contract (`parse`, `validate`);
3. proves every figure it proposes is **already in the source text** (`_grounded`). An amount the
   text does not contain is never accepted, because the adjustment stage - not the model - is what
   derives new figures. That single rule is what keeps "no invented numbers" true even when a model
   is in the loop.

A caller supplies a `bp.llm.Models`; tests supply `bp.llm.MockProvider`. No key is read here.
"""
import json
import re
from decimal import Decimal as D, InvalidOperation

from . import ledger

CONTRACT_VERSION = "statement-extract/2"

SYSTEM = """You read an accounting problem and return journal entries plus adjustment specs as JSON. You do not calculate.

Rules, all of them absolute:
- Return ONLY a JSON object with keys "entries", "adjustments", "policy", "unplaceable", "assumptions". No prose, no code fences.
- "entries": one entry per transaction or adjustment the text states explicitly. Every entry balances: the sum of debits equals the sum of credits. Use ONLY account codes from the chart. If nothing fits, put the text in "unplaceable".
- "adjustments": only when you can extract the PARAMETERS for a registered function (below). Never compute the amount; never emit an adjustment whose parameters you cannot find in the text. If the text states a finished figure ("depreciation 12,000"), book it as an entry, not an adjustment.
- "policy": only what the text states (tax rate, depreciation convention, inventory system). Omit a key rather than guess it.
- Amounts must be numbers that appear in the text exactly as stated. Never sum, prorate, depreciate, accrue, compute tax or derive a figure. A combined total is a derived figure and will be rejected.
- Do not produce totals, balances or statements.
- "date" is YYYY-MM-DD. If the text states no date, use the accounting period's end date and say so in "assumptions".
- "source_text" is the exact sentence or clause the entry or adjustment came from.
- "kind" is "original" for a transaction the text states, "adjustment" for an adjusting entry the text states explicitly. Do not infer adjustments.
- List every assumption in "assumptions"; an empty list is the common answer.

REGISTERED ADJUSTMENT FUNCTIONS (use only these, by exact name):
- straight_line_depreciation: params {cost, residual (default 0), life_years, convention in {full_year, half_year, pro_rata}, months_in_service (required only for pro_rata)}. Amount = (cost - residual) / life_years, prorated by the convention.
- reducing_balance_depreciation: params {cost, residual (default 0), life_years, rate (optional; defaults to 2/life_years), accumulated (default 0), convention in {full_year, half_year, pro_rata}, months_in_service (required only for pro_rata)}. Amount = (cost - accumulated - residual) * rate, prorated by the convention. Never goes below zero.
- units_of_production_depreciation: params {cost, residual (default 0), units_this_period, total_estimated_units}. Amount = (cost - residual) * units_this_period / total_estimated_units.
- prepaid_amortization: params {payment, months_expired, total_months (default 12)}. Amount = payment * months_expired / total_months.
- periodic_cogs: params {beginning_inventory (default 0), purchases, ending_inventory}. Amount = beginning + purchases - ending.
- bad_debt_expense: params {receivables, rate, prior_allowance (default 0)}. Amount = receivables * rate - prior_allowance, clamped at zero. The rate is the percentage of receivables estimated uncollectible.
- tax_on_pretax: params {} (the rate comes from policy.tax_rate). Amount = pre-tax income * rate; a loss earns no tax.
- tax_benefit_on_loss: params {pretax_income, rate (optional; defaults to policy.tax_rate)}. Amount = -pretax * rate when pretax < 0, otherwise zero. Only emit when the text states a loss carryback or carryforward policy.
Each adjustment needs "debit" and "credit" account codes from the chart, distinct.
"""

CONTRACT = {
    "format": CONTRACT_VERSION,
    "type": "object",
    "required": ["entries"],
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["date", "description", "lines", "source_text", "kind"],
                "properties": {
                    "date": {"type": "string", "format": "date"},
                    "description": {"type": "string"},
                    "kind": {"enum": ["original", "adjustment"]},
                    "source_text": {"type": "string"},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                    "lines": {
                        "type": "array",
                        "minItems": 2,
                        "items": {
                            "type": "object",
                            "required": ["account"],
                            "properties": {
                                "account": {"type": "string"},
                                "debit": {"type": "number", "minimum": 0},
                                "credit": {"type": "number", "minimum": 0},
                            },
                        },
                    },
                },
            },
        },
        "adjustments": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "function", "debit", "credit", "source_text"],
                "properties": {
                    "id": {"type": "string"},
                    "function": {"type": "string"},
                    "debit": {"type": "string"},
                    "credit": {"type": "string"},
                    "params": {"type": "object"},
                    "date": {"type": "string", "format": "date"},
                    "description": {"type": "string"},
                    "source_text": {"type": "string"},
                    "assumptions": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "policy": {
            "type": "object",
            "properties": {
                "tax_rate": {"type": "number", "minimum": 0, "maximum": 1},
                "depreciation": {
                    "type": "object",
                    "properties": {
                        "method": {"enum": ["straight_line"]},
                        "convention": {"enum": ["full_year", "half_year", "pro_rata"]},
                    },
                },
                "inventory_system": {"enum": ["periodic", "perpetual"]},
                "explicitly_stated": {"type": "array", "items": {"type": "string"}},
            },
        },
        "unplaceable": {"type": "array", "items": {"type": "string"}},
        "assumptions": {"type": "array", "items": {"type": "string"}},
    },
}


class ExtractionError(ValueError):
    """The model's answer was off-contract, ungrounded, or could not be posted."""


def system_prompt():
    return SYSTEM


def user_prompt(text, chart, period=None):
    """The chart is given as data so the model can only choose existing codes."""
    codes = [{"code": r["code"], "name": r["name"], "type": r["type"], "line": r["line"]} for r in chart]
    head = "CHART OF ACCOUNTS\n" + json.dumps(codes, indent=1)
    if period:
        head += ("\n\nACCOUNTING PERIOD\n" + json.dumps(period) +
                 "\nIf the text states no date for a transaction, use the period end date and say so in assumptions.")
    return (head + "\n\nPROBLEM TEXT\n" + str(text) + "\n\nReturn the JSON object now.")


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def _tokens(text):
    """Every number the text actually contains, as Decimals (commas stripped)."""
    out = set()
    for m in _NUMBER.findall(str(text)):
        try:
            out.add(D(m.replace(",", "")))
        except InvalidOperation:
            continue
    return out


def _numbers_in(value):
    """Every number buried in a params object, for the grounding check."""
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, str):
        try:
            return [D(value)]
        except (InvalidOperation, ValueError):
            return []
    if isinstance(value, dict):
        out = []
        for v in value.values():
            out += _numbers_in(v)
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            out += _numbers_in(v)
        return out
    return []


def _entry_shape(e):
    """Accept both the `lines` shape and the `{debit, credit, amount}` shorthand a model may emit."""
    if isinstance(e, dict) and "lines" not in e and "debit" in e and "credit" in e and "amount" in e:
        e = dict(e)
        e["lines"] = [{"account": e["debit"], "debit": e["amount"]},
                      {"account": e["credit"], "credit": e["amount"]}]
    return e


_PARAM_DEFAULTS = {
    "straight_line_depreciation": {"residual": 0},
    "prepaid_amortization": {"total_months": 12},
    "periodic_cogs": {"beginning_inventory": 0},
    "tax_on_pretax": {},
}


def _numbers_grounded(params, function, tokens, source_tokens):
    """Every number in params must be stated, unless it is a declared default for that function."""
    defaults = _PARAM_DEFAULTS.get(function, {})
    for n in _numbers_in(params):
        if n in (D(str(v)) for v in defaults.values() if isinstance(v, (int, float, str))):
            continue
        if not (_grounded(n, tokens) or _grounded(n, source_tokens)):
            return n
    return None


def _grounded(amount, tokens):
    try:
        return D(str(amount)) in tokens
    except (InvalidOperation, ValueError):
        return False


def _account(line):
    """The chart code a line names. `account` is the schema key; `code` is accepted as its alias."""
    return line.get("account") or line.get("code")


def _sides(line):
    """Normalise a schema-shaped line: a zero on the other side is the schema's own default.

    Tip 2's journal line carries both `debit` and `credit` with 0 for the unused side. That is
    accepted here and reduced to one side; a line with two non-zero sides, or two zeroes, is refused.
    """
    try:
        dr = D(str(line.get("debit", 0) or 0))
        cr = D(str(line.get("credit", 0) or 0))
    except (InvalidOperation, ValueError):
        raise ExtractionError("a debit or credit is not a number")
    if not (dr.is_finite() and cr.is_finite()):
        raise ExtractionError("a debit or credit is not a finite number")
    if dr < 0 or cr < 0:
        raise ExtractionError("a debit or credit cannot be negative")
    if dr and cr:
        raise ExtractionError("a line cannot carry both a debit and a credit")
    if not dr and not cr:
        raise ExtractionError("a line must carry a debit or a credit")
    out = {"account": _account(line)}
    if dr:
        out["debit"] = str(dr)
    else:
        out["credit"] = str(cr)
    return out


def parse(text):
    """The model's text as a JSON object, refusing anything that is not one."""
    raw = _FENCE.sub("", str(text or "").strip())
    if not raw:
        raise ExtractionError("the model returned nothing")
    try:
        data = json.loads(raw)
    except ValueError:
        raise ExtractionError("the model did not return JSON")
    if not isinstance(data, dict):
        raise ExtractionError("the model returned JSON but not an object")
    if not isinstance(data.get("entries"), list):
        raise ExtractionError('the model must return {"entries": [...]}')
    return data


def validate(payload, source_text, chart, places=2, default_date=None, period=None):
    """Every reason the proposed journal cannot be posted, gathered in one pass.

    Checks, in the order a reader would fix them: shape, account membership, the ledger's own balance
    rule, and finally grounding - the amount must be in the source text. `unplaceable` lines are
    passed through as reported gaps, never as invented accounts.

    `default_date` is the period end: a problem that states no date ("paid rent of 1,200") is the
    normal case, not an error, and the extraction is dated to the period end rather than refused.
    `period` (optional) additionally refuses a date outside the accounting period.
    """
    errs = []
    if not isinstance(payload, dict):
        return ["the extraction must be an object"]
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return ["entries must be a list"]
    codes = {r["code"] for r in chart}
    tokens = _tokens(source_text)
    for i, e in enumerate(entries):
        tag = f"entries[{i}]"
        e = _entry_shape(e)
        if not isinstance(e, dict):
            errs.append(f"{tag} must be an object")
            continue
        date = e.get("date") or default_date
        if not ledger.DATE.fullmatch(str(date or "")):
            errs.append(f"{tag} needs a date as YYYY-MM-DD (the text states none and no default_date was supplied)")
        elif period and not (str(period.get("start", "0000-01-01")) <= str(date) <= str(period.get("end", "9999-12-31"))):
            errs.append(f"{tag} date {date} is outside the accounting period")
        if e.get("kind") not in ("original", "adjustment"):
            errs.append(f"{tag} kind must be 'original' or 'adjustment'")
        if not str(e.get("source_text", "")).strip():
            errs.append(f"{tag} needs the source_text it came from")
        lines = e.get("lines")
        if not isinstance(lines, list) or len(lines) < 2:
            errs.append(f"{tag} needs at least two lines")
            continue
        before = len(errs)
        clean = []
        for j, line in enumerate(lines):
            ltag = f"{tag}.lines[{j}]"
            if not isinstance(line, dict):
                errs.append(f"{ltag} must be an object")
                continue
            if _account(line) not in codes:
                errs.append(f"{ltag} uses account {_account(line)!r}, which is not in the chart")
                continue
            try:
                norm = _sides(line)
            except ExtractionError as ex:
                errs.append(f"{ltag} {ex}")
                continue
            amount = norm.get("debit", norm.get("credit"))
            if not _grounded(amount, tokens):
                errs.append(f"{ltag} amount {amount!r} does not appear in the problem text; "
                            f"a model may not introduce a figure (derived amounts belong to the adjustment stage)")
                continue
            clean.append(norm)
        if len(clean) == len(lines) and len(errs) == before:
            try:
                ledger.Entry.make(str(date), str(e.get("description") or e.get("source_text")),
                                  clean, places)
            except ledger.LedgerError as ex:
                errs.append(f"{tag}: {ex}")

    # Adjustments: only registered functions, grounded parameters, distinct accounts.
    adjustments = payload.get("adjustments")
    if adjustments is None:
        adjustments = []
    if not isinstance(adjustments, list):
        errs.append("adjustments must be a list")
        adjustments = []
    from . import statement_plan as _sp
    for i, a in enumerate(adjustments):
        tag = f"adjustments[{i}]"
        if not isinstance(a, dict):
            errs.append(f"{tag} must be an object")
            continue
        if a.get("function") not in _sp.FUNCTIONS:
            errs.append(f"{tag}: unknown function {a.get('function')!r}; known: {sorted(_sp.FUNCTIONS)}")
        if a.get("debit") not in codes or a.get("credit") not in codes:
            errs.append(f"{tag}: debit and credit must be chart codes")
        elif a.get("debit") == a.get("credit"):
            errs.append(f"{tag}: debit and credit are the same account")
        if not str(a.get("source_text", "")).strip():
            errs.append(f"{tag} needs the source_text it came from")
        params = a.get("params", {})
        if not isinstance(params, dict):
            errs.append(f"{tag}.params must be an object")
            params = {}
        # every number in params must appear in the source text (or the problem text), unless it is
        # a declared default for that function
        for n in _numbers_in(params):
            if not (_grounded(n, tokens) or _grounded(n, _tokens(a.get("source_text", "")))):
                # allow declared defaults
                defaults = _PARAM_DEFAULTS.get(a.get("function"), {})
                if n in (D(str(v)) for v in defaults.values() if isinstance(v, (int, float, str))):
                    continue
                errs.append(f"{tag}.params contains {n!r}, which does not appear in the source text; "
                            f"the model may not introduce a figure")
        # convention, if supplied, must be admissible
        dep = params.get("depreciation") if isinstance(params.get("depreciation"), dict) else None
        conv = params.get("convention") or (dep.get("convention") if dep else None)
        if conv is not None and conv not in _sp.CONVENTIONS:
            errs.append(f"{tag}.params.convention must be one of {list(_sp.CONVENTIONS)}")
        inv = params.get("inventory_system")
        if inv is not None and inv not in _sp.INVENTORY_SYSTEMS:
            errs.append(f"{tag}.params.inventory_system must be one of {list(_sp.INVENTORY_SYSTEMS)}")
        if a.get("date") is not None and not ledger.DATE.fullmatch(str(a["date"])):
            errs.append(f"{tag}.date must be YYYY-MM-DD")
        elif a.get("date") and period and not (str(period.get("start", "0000-01-01")) <= str(a["date"]) <= str(period.get("end", "9999-12-31"))):
            errs.append(f"{tag}.date is outside the accounting period")

    # Policy: only stated values, validated.
    policy = payload.get("policy")
    if policy is not None:
        if not isinstance(policy, dict):
            errs.append("policy must be an object")
        else:
            if policy.get("tax_rate") is not None:
                try:
                    r = D(str(policy["tax_rate"]))
                    if not (D(0) <= r <= D(1)):
                        errs.append("policy.tax_rate must be between 0 and 1")
                except (InvalidOperation, ValueError):
                    errs.append("policy.tax_rate must be a number between 0 and 1")
            dep = policy.get("depreciation")
            if dep is not None:
                if not isinstance(dep, dict):
                    errs.append("policy.depreciation must be an object")
                else:
                    if dep.get("method") not in (None, "straight_line"):
                        errs.append("policy.depreciation.method must be 'straight_line'")
                    if dep.get("convention") is not None and dep["convention"] not in _sp.CONVENTIONS:
                        errs.append(f"policy.depreciation.convention must be one of {list(_sp.CONVENTIONS)}")
            if policy.get("inventory_system") is not None and policy["inventory_system"] not in _sp.INVENTORY_SYSTEMS:
                errs.append(f"policy.inventory_system must be one of {list(_sp.INVENTORY_SYSTEMS)}")
    return errs


def to_entries(payload, default_date=None):
    """The proposed entries in the shape `bp.accounts` accepts (already validated by `validate`)."""
    out = []
    for e in payload.get("entries") or []:
        e = _entry_shape(e)
        out.append({"date": e.get("date") or default_date,
                    "description": e.get("description") or e.get("source_text"),
                    "lines": [_sides(line) for line in e["lines"]],
                    "source_text": e["source_text"], "kind": e.get("kind", "original")})
    return out


def to_adjustments(payload):
    """The proposed adjustments in the shape `statement_plan` accepts."""
    out = []
    for i, a in enumerate(payload.get("adjustments") or []):
        item = {"id": a.get("id") or (a.get("function", "adj") + "_" + str(i)),
                "function": a["function"],
                "debit": a["debit"], "credit": a["credit"],
                "params": a.get("params") or {},
                "source_text": a.get("source_text", "")}
        if a.get("date"):
            item["date"] = a["date"]
        if a.get("description"):
            item["description"] = a["description"]
        out.append(item)
    return out


def to_policy(payload):
    """The policy the model stated, or None when it stated nothing."""
    p = payload.get("policy")
    if not isinstance(p, dict) or not p:
        return None
    # mark as stated what the model actually supplied
    stated = []
    if "tax_rate" in p:
        stated.append("tax_rate")
    dep = p.get("depreciation") or {}
    if "convention" in dep:
        stated.append("depreciation.convention")
    if "inventory_system" in p:
        stated.append("inventory_system")
    p = dict(p)
    # accept the flat shape a model may emit
    if "depreciation_convention" in p:
        p.setdefault("depreciation", {})["convention"] = p.pop("depreciation_convention")
    if "tax_rate" in p and p["tax_rate"] is not None:
        p["tax_rate"] = str(p["tax_rate"])
    p.setdefault("explicitly_stated", stated)
    return p


def extract(text, chart, models, consent=False, places=2, period=None, default_date=None):
    """Ask a model for the journal, then refuse it unless it is schema-shaped and grounded.

    Returns ``{"entries", "adjustments", "policy", "record", "unplaceable"}``. Raises
    `ExtractionError` on any contract breach; the caller never sees a partially accepted journal.
    """
    if models is None:
        raise ExtractionError("no model is configured, so only structured input can be read")
    raw, record = models.call("builder", "statement_extract", CONTRACT_VERSION,
                              system_prompt(), user_prompt(text, chart, period), consent)
    payload = parse(raw)
    errs = validate(payload, text, chart, places, default_date=default_date, period=period)
    if errs:
        raise ExtractionError("; ".join(errs))
    return {"entries": to_entries(payload, default_date=default_date),
            "adjustments": to_adjustments(payload),
            "policy": to_policy(payload),
            "record": record,
            "unplaceable": list(payload.get("unplaceable") or [])}