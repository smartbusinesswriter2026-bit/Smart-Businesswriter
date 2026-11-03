"""Generic statement plan: policy -> chart -> journal -> adjustment DAG -> the frozen ledger -> articulation gate.

This module is the layer the two owner tips describe, expressed once and generically. It adds nothing
to the ledger kernel and nothing to `accounts.build`; it compiles a plan into the declarative
engagement spec those already accept, computes only the adjustments the plan declares, and then
re-checks the result against the identities the tips name.

Division of labour (the whole point of the tips):

  * a model may read language and propose **structured** journal lines (see `statement_extract`);
  * this module validates those lines, never invents one, and never does arithmetic on a model's say-so;
  * every total comes from `bp.ledger` through `bp.accounts.build`.

Nothing here knows any worked example. A plan carries its own chart, policy, entries and adjustment
specs; the same code builds a different engagement by being given different data.
"""
from decimal import Decimal as D, ROUND_HALF_UP, ROUND_HALF_EVEN, InvalidOperation

from . import accounts, ledger


class PlanError(ValueError):
    """A plan that cannot be built, or a built engagement that failed an articulation check."""


# ---------------------------------------------------------------------------
# Policy registry and the assumptions manifest (tip 1, "handle ambiguity explicitly")
# ---------------------------------------------------------------------------

#: Every policy value the pipeline can default. A default is never silent: `manifest()` names each
#: one the problem text did not state, so a reader can see what the build assumed.
POLICY_DEFAULTS = {
    "depreciation.method": "straight_line",
    "depreciation.convention": "pro_rata",
    "inventory_system": "periodic",
    "rounding": "half_up",
}

#: Why each default exists, printed beside it in the manifest.
POLICY_REASONS = {
    "depreciation.method": "only straight-line is implemented; a reducing-balance policy must be declared",
    "depreciation.convention": "the text did not say whether a part-year asset is depreciated in full, pro rata or at half rate",
    "inventory_system": "the text did not say whether inventory is kept periodically or perpetually",
    "rounding": "the text did not declare a rounding rule",
}

ROUNDING = {"half_up": ROUND_HALF_UP, "half_even": ROUND_HALF_EVEN}
CONVENTIONS = ("full_year", "pro_rata", "half_year")
INVENTORY_SYSTEMS = ("periodic", "perpetual")


def money(x, places=2, rounding="half_up"):
    """Quantise to the engagement's precision. Every computed amount passes through here once."""
    if isinstance(x, bool) or isinstance(x, float):
        raise PlanError("amounts are Decimals or strings, never binary floats")
    try:
        d = D(str(x))
    except (InvalidOperation, ValueError):
        raise PlanError(f"not a number: {x!r}")
    if not d.is_finite():
        raise PlanError(f"not a finite number: {x!r}")
    return d.quantize(D(1).scaleb(-places), rounding=ROUNDING[rounding])


def _flatten(prefix, value):
    out = {}
    for k, v in value.items():
        name = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(_flatten(name, v))
        else:
            out[name] = v
    return out


def manifest(policy):
    """What the build decided, split into what the text stated and what it assumed.

    `explicitly_stated` is a list of dotted policy names (e.g. ``depreciation.convention``). Anything
    in `POLICY_DEFAULTS` that is not in that list appears in `assumed`: it is visible, never silent.
    A value the plan supplies without listing it as stated is reported the same way - supplying a
    number is not the same as the problem stating it.
    """
    policy = policy or {}
    stated = list(policy.get("explicitly_stated") or [])
    flat = _flatten("", policy)
    assumed = []
    for name, default in POLICY_DEFAULTS.items():
        if name in stated:
            continue
        assumed.append({"assumption": name, "value": flat.get(name, default),
                        "reason": POLICY_REASONS[name]})
    return {"stated": stated, "assumed": assumed}


def validate_policy(policy):
    policy = policy or {}
    errs = []
    if not isinstance(policy, dict):
        return ["policy must be an object"]
    dep = policy.get("depreciation")
    if dep is not None:
        if not isinstance(dep, dict):
            errs.append("policy.depreciation must be an object")
        else:
            if dep.get("method", "straight_line") != "straight_line":
                errs.append("policy.depreciation.method must be 'straight_line' (the only method implemented)")
            if dep.get("convention", "pro_rata") not in CONVENTIONS:
                errs.append(f"policy.depreciation.convention must be one of {list(CONVENTIONS)}")
    if policy.get("inventory_system", "periodic") not in INVENTORY_SYSTEMS:
        errs.append(f"policy.inventory_system must be one of {list(INVENTORY_SYSTEMS)}")
    if policy.get("rounding", "half_up") not in ROUNDING:
        errs.append(f"policy.rounding must be one of {sorted(ROUNDING)}")
    rate = policy.get("tax_rate")
    if rate is not None:
        try:
            r = D(str(rate))
            if not (D(0) <= r <= D(1)):
                errs.append("policy.tax_rate must be between 0 and 1")
        except (InvalidOperation, ValueError):
            errs.append("policy.tax_rate must be a number between 0 and 1")
    if not isinstance(policy.get("explicitly_stated", []), list):
        errs.append("policy.explicitly_stated must be a list of dotted policy names")
    return errs


# ---------------------------------------------------------------------------
# Chart and journal validation (tip 1, "a strict journal entry schema")
# ---------------------------------------------------------------------------

def account(code, name, type, line, section="", role="", activity="", contra=False):
    """One chart account, validated by the ledger's own `Account` rather than by a copy of its rules."""
    a = ledger.Account(code=str(code), name=name, type=type, line=line, section=section,
                       role=role, activity=activity, contra=contra)
    return {"code": a.code, "name": a.name, "type": a.type, "line": a.line, "section": a.section,
            "role": a.role, "activity": a.activity, "contra": a.contra}


def validate_chart(chart):
    errs = []
    if not isinstance(chart, list) or not chart:
        return ["chart must be a non-empty list of accounts"]
    codes = set()
    for i, row in enumerate(chart):
        try:
            a = ledger.Account(**row)
        except (TypeError, ledger.ChartError) as ex:
            errs.append(f"chart[{i}]: {ex}")
            continue
        if a.code in codes:
            errs.append(f"chart[{i}]: duplicate account code {a.code}")
        codes.add(a.code)
    if not any(r.get("role") == "retained_earnings" and r.get("type") == "equity" for r in chart):
        errs.append("the chart needs one equity account with role 'retained_earnings'")
    if not any(r.get("role") == "cash" for r in chart):
        errs.append("the chart needs at least one account with role 'cash'")
    return errs


def validate_entries(entries, chart, places=2):
    """Validate journal lines with the ledger's own constructor: balance, sides, accounts, precision.

    A model-proposed entry is validated here before it reaches the journal, so an unbalanced or
    unknown-account entry can never be posted.
    """
    codes = {r["code"] for r in chart}
    errs = []
    if not isinstance(entries, list):
        return ["entries must be a list"]
    for i, e in enumerate(entries):
        tag = f"entries[{i}]"
        if not isinstance(e, dict):
            errs.append(f"{tag} must be an object")
            continue
        if not ledger.DATE.fullmatch(str(e.get("date", ""))):
            errs.append(f"{tag} date must be YYYY-MM-DD")
        lines = e.get("lines")
        if not isinstance(lines, list) or len(lines) < 2:
            errs.append(f"{tag} needs at least two lines")
            continue
        before = len(errs)
        for j, line in enumerate(lines):
            if not isinstance(line, dict):
                errs.append(f"{tag}.lines[{j}] must be an object")
                continue
            if ("debit" in line) == ("credit" in line):
                errs.append(f"{tag}.lines[{j}] needs exactly one of debit or credit")
            if line.get("account") not in codes:
                errs.append(f"{tag}.lines[{j}] uses unknown account {line.get('account')!r}")
        if len(errs) == before:
            try:
                ledger.Entry.make(str(e["date"]), str(e.get("description", "")), lines, places)
            except ledger.LedgerError as ex:
                errs.append(f"{tag}: {ex}")
    return errs


# ---------------------------------------------------------------------------
# Adjustment DAG (tip 2, "plugs are first-class nodes, not free-text adjustments")
# ---------------------------------------------------------------------------

class Node:
    """One adjustment computation. `params` values may be literals or `{"$ref": "<node id>"}`."""

    __slots__ = ("id", "function", "params", "depends_on")

    def __init__(self, id, function, params=None, depends_on=()):
        self.id = str(id)
        self.function = str(function)
        self.params = params or {}
        self.depends_on = tuple(depends_on)


def _refs(value):
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            return [str(value["$ref"])]
        out = []
        for v in value.values():
            out += _refs(v)
        return out
    if isinstance(value, list):
        out = []
        for v in value:
            out += _refs(v)
        return out
    return []


def toposort(nodes):
    """Deterministic topological order (ties broken by node id), refusing a cycle or an unknown ref."""
    by_id = {n.id: n for n in nodes}
    if len(by_id) != len(nodes):
        raise PlanError("duplicate adjustment node id")
    for n in nodes:
        for ref in _refs(n.params) + list(n.depends_on):
            if ref not in by_id:
                raise PlanError(f"adjustment {n.id!r} depends on unknown node {ref!r}")
    deps = {n.id: set(list(n.depends_on) + _refs(n.params)) for n in nodes}
    order, done = [], set()
    while len(order) < len(nodes):
        ready = sorted(nid for nid, ds in deps.items() if nid not in done and ds <= done)
        if not ready:
            raise PlanError("adjustment graph has a cycle: " + ", ".join(sorted(set(deps) - done)))
        for nid in ready:
            order.append(nid)
            done.add(nid)
    return order


def _resolve(value, env):
    if isinstance(value, dict):
        if set(value) == {"$ref"}:
            ref = str(value["$ref"])
            if ref not in env:
                raise PlanError(f"adjustment refers to {ref!r} before it is computed")
            return env[ref]
        return {k: _resolve(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve(v, env) for v in value]
    return value


def evaluate(nodes, context=None):
    """Evaluate every node once, in dependency order, returning {node id: Decimal}."""
    context = context or {}
    env = {}
    for nid in toposort(nodes):
        node = next(n for n in nodes if n.id == nid)
        fn = FUNCTIONS.get(node.function)
        if fn is None:
            raise PlanError(f"unknown adjustment function {node.function!r}; known: {sorted(FUNCTIONS)}")
        env[nid] = fn(_resolve(node.params, env), context)
    return env


def _dec(x, what):
    if isinstance(x, bool) or isinstance(x, float):
        raise PlanError(f"{what} must be a Decimal, string or integer, never a binary float")
    try:
        d = D(str(x))
    except (InvalidOperation, ValueError):
        raise PlanError(f"{what} is not a number: {x!r}")
    if not d.is_finite():
        raise PlanError(f"{what} is not finite")
    return d


def straight_line_depreciation(params, context):
    """(cost - residual) / life_years, prorated by the declared convention.

    The convention is a policy, not a default hidden in the arithmetic: `full_year` charges a whole
    year in the year of acquisition, `half_year` a half, and `pro_rata` requires `months_in_service`.
    """
    cost = _dec(params.get("cost"), "cost")
    residual = _dec(params.get("residual", 0), "residual")
    life = _dec(params.get("life_years"), "life_years")
    if cost < 0 or residual < 0 or life <= 0:
        raise PlanError("cost and residual must not be negative, and life_years must be positive")
    if residual > cost:
        raise PlanError("residual cannot exceed cost")
    convention = params.get("convention") or context.get("policy", {}).get("depreciation", {}).get("convention", "pro_rata")
    if convention not in CONVENTIONS:
        raise PlanError(f"depreciation convention must be one of {list(CONVENTIONS)}")
    if convention == "full_year":
        months = D(12)
    elif convention == "half_year":
        months = D(6)
    else:
        months = _dec(params.get("months_in_service", 0), "months_in_service")
        if months <= 0:
            raise PlanError("the pro_rata convention needs months_in_service (1-12) for the asset")
        if months > 12:
            raise PlanError("months_in_service cannot exceed 12; a longer period is more than one year")
    return money((cost - residual) / life * months / D(12), context.get("places", 2), context.get("rounding", "half_up"))


def prepaid_amortization(params, context):
    """payment x months_expired / total_months: the expired portion, not the whole payment."""
    payment = _dec(params.get("payment"), "payment")
    expired = _dec(params.get("months_expired"), "months_expired")
    total = _dec(params.get("total_months", 12), "total_months")
    if payment < 0 or total <= 0 or expired < 0 or expired > total:
        raise PlanError("payment must not be negative and 0 <= months_expired <= total_months")
    return money(payment * expired / total, context.get("places", 2), context.get("rounding", "half_up"))


def periodic_cogs(params, context):
    """beginning inventory + purchases - ending inventory (a periodic system's closing figure)."""
    opening = _dec(params.get("beginning_inventory", 0), "beginning_inventory")
    purchases = _dec(params.get("purchases", 0), "purchases")
    ending = _dec(params.get("ending_inventory"), "ending_inventory")
    if opening < 0 or purchases < 0 or ending < 0:
        raise PlanError("inventory figures must not be negative")
    if opening + purchases < ending:
        raise PlanError("ending inventory exceeds goods available for sale; check the declarations")
    return money(opening + purchases - ending, context.get("places", 2), context.get("rounding", "half_up"))


def tax_on_pretax(params, context):
    """pre-tax income x rate. A loss is not taxed and no tax benefit is invented."""
    pretax = _dec(params.get("pretax_income", context.get("pretax_income", 0)), "pretax_income")
    rate = _dec(params.get("rate", context.get("policy", {}).get("tax_rate")), "tax rate")
    if rate < 0 or rate > 1:
        raise PlanError("tax rate must be between 0 and 1")
    if pretax <= 0:
        return D(0)
    return money(pretax * rate, context.get("places", 2), context.get("rounding", "half_up"))


def reducing_balance_depreciation(params, context):
    """Declining-balance depreciation: (cost - accumulated) x rate, prorated by convention.

    `rate` is the declared annual rate (e.g. 0.20 for 20%). When it is omitted the double-declining
    rate 2 / life_years is used, which is the common default and is itself a declared convention.
    `accumulated` is the depreciation already taken in earlier periods (0 for the first year).
    """
    cost = _dec(params.get("cost"), "cost")
    residual = _dec(params.get("residual", 0), "residual")
    life = _dec(params.get("life_years"), "life_years")
    accumulated = _dec(params.get("accumulated", 0), "accumulated")
    if cost < 0 or residual < 0 or life <= 0 or accumulated < 0:
        raise PlanError("cost, residual and accumulated must not be negative, and life_years must be positive")
    if residual > cost:
        raise PlanError("residual cannot exceed cost")
    if accumulated > cost - residual:
        raise PlanError("accumulated depreciation cannot exceed cost less residual")
    if params.get("rate") is None:
        rate = D(2) / life
    else:
        rate = _dec(params["rate"], "rate")
        if rate < 0 or rate > 1:
            raise PlanError("rate must be between 0 and 1")
    convention = params.get("convention") or context.get("policy", {}).get("depreciation", {}).get("convention", "full_year")
    if convention not in CONVENTIONS:
        raise PlanError(f"depreciation convention must be one of {list(CONVENTIONS)}")
    if convention == "full_year":
        months = D(12)
    elif convention == "half_year":
        months = D(6)
    else:
        months = _dec(params.get("months_in_service", 0), "months_in_service")
        if months <= 0 or months > 12:
            raise PlanError("the pro_rata convention needs months_in_service from 1 to 12")
    amount = (cost - accumulated - residual) * rate * months / D(12)
    if amount < 0:
        amount = D(0)
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def units_of_production_depreciation(params, context):
    """(cost - residual) x (units_this_period / total_estimated_units)."""
    cost = _dec(params.get("cost"), "cost")
    residual = _dec(params.get("residual", 0), "residual")
    units = _dec(params.get("units_this_period"), "units_this_period")
    total = _dec(params.get("total_estimated_units"), "total_estimated_units")
    if cost < 0 or residual < 0 or units < 0 or total <= 0:
        raise PlanError("cost and residual must not be negative, units must not be negative, total_estimated_units must be positive")
    if residual > cost:
        raise PlanError("residual cannot exceed cost")
    if units > total:
        raise PlanError("units_this_period cannot exceed total_estimated_units")
    return money((cost - residual) * units / total, context.get("places", 2), context.get("rounding", "half_up"))


def bad_debt_expense(params, context):
    """Bad debt expense under the percentage-of-receivables method.

    expense = receivables x rate - prior_allowance. A negative result (a recovery) is reported as
    zero here; a recovery needs its own entry direction and is not modelled in this increment.
    """
    receivables = _dec(params.get("receivables"), "receivables")
    rate = _dec(params.get("rate"), "rate")
    prior = _dec(params.get("prior_allowance", 0), "prior_allowance")
    if receivables < 0 or rate < 0 or rate > 1 or prior < 0:
        raise PlanError("receivables and prior_allowance must not be negative, and rate must be between 0 and 1")
    amount = receivables * rate - prior
    if amount < 0:
        amount = D(0)
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def tax_benefit_on_loss(params, context):
    """A tax benefit (deferred tax asset) arising from a tax loss.

    benefit = -pretax_income x rate, when pretax_income < 0; otherwise zero. A loss is not a tax
    benefit unless the jurisdiction allows a carryback or carryforward; this function computes the
    arithmetic only and never invents a policy. The policy (carryback vs carryforward, years) is an
    owner decision and must be stated in the problem text.
    """
    pretax = _dec(params.get("pretax_income", context.get("pretax_income", 0)), "pretax_income")
    rate = _dec(params.get("rate", context.get("policy", {}).get("tax_rate")), "tax rate")
    if rate < 0 or rate > 1:
        raise PlanError("tax rate must be between 0 and 1")
    if pretax >= 0:
        return D(0)
    return money(-pretax * rate, context.get("places", 2), context.get("rounding", "half_up"))


FUNCTIONS = {
    "straight_line_depreciation": straight_line_depreciation,
    "reducing_balance_depreciation": reducing_balance_depreciation,
    "units_of_production_depreciation": units_of_production_depreciation,
    "prepaid_amortization": prepaid_amortization,
    "periodic_cogs": periodic_cogs,
    "bad_debt_expense": bad_debt_expense,
    "tax_on_pretax": tax_on_pretax,
    "tax_benefit_on_loss": tax_benefit_on_loss,
}


def resolve_adjustments(adjustments, policy, period_end, pretax_income=None, places=2):
    """Turn each declared adjustment into one balanced journal entry, computed by a registered function.

    Each adjustment names the function, its params and the two accounts it moves:
    ``{"id", "function", "params", "debit", "credit", "date"?, "description"?}``. The amount is
    computed here; the accounts are declared by the plan. A zero amount posts nothing and is
    reported, because a zero-value entry is not evidence that the adjustment happened.
    """
    context = {"policy": policy or {}, "pretax_income": pretax_income, "places": places,
               "rounding": (policy or {}).get("rounding", "half_up")}
    entries, skipped = [], []
    for spec in adjustments:
        node = Node(spec["id"], spec["function"], spec.get("params") or {})
        amount = evaluate([node], context)[node.id]
        if amount == 0:
            skipped.append({"adjustment": node.id, "function": node.function,
                            "reason": "the function computed zero, so no entry was posted"})
            continue
        entries.append({
            "date": spec.get("date") or period_end,
            "description": spec.get("description") or node.id,
            "lines": [{"account": spec["debit"], "debit": str(amount)},
                      {"account": spec["credit"], "credit": str(amount)}],
        })
    return entries, skipped


DEFAULT_CHART = [
    {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "section": "current", "role": "cash"},
    {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Trade receivables", "section": "current"},
    {"code": "1200", "name": "Inventory", "type": "asset", "line": "Inventory", "section": "current"},
    {"code": "1300", "name": "Prepayments", "type": "asset", "line": "Prepayments", "section": "current"},
    {"code": "1500", "name": "Property, plant and equipment", "type": "asset", "line": "Property, plant and equipment", "section": "non_current"},
    {"code": "1510", "name": "Accumulated depreciation", "type": "asset", "line": "Property, plant and equipment", "section": "non_current", "contra": True},
    {"code": "2000", "name": "Trade payables", "type": "liability", "line": "Trade payables", "section": "current"},
    {"code": "2100", "name": "Borrowings", "type": "liability", "line": "Borrowings", "section": "non_current"},
    {"code": "2200", "name": "Accruals", "type": "liability", "line": "Accruals", "section": "current"},
    {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "role": "capital"},
    {"code": "3100", "name": "Retained earnings", "type": "equity", "line": "Retained earnings", "role": "retained_earnings"},
    {"code": "4000", "name": "Revenue", "type": "income", "line": "Revenue"},
    {"code": "5000", "name": "Cost of sales", "type": "expense", "line": "Cost of sales"},
    {"code": "6000", "name": "Operating expenses", "type": "expense", "line": "Operating expenses"},
    {"code": "7000", "name": "Finance costs", "type": "expense", "line": "Finance costs"},
    {"code": "8000", "name": "Tax", "type": "expense", "line": "Tax"},
]

_PLAN_KEYS = ("period", "currency", "framework", "chart")


def _spec(plan, extra_entries):
    """The declarative engagement spec `accounts.build` accepts, with the compiled entries appended."""
    entries = list(plan.get("entries") or []) + list(extra_entries)
    spec = {"period": plan["period"], "currency": plan["currency"], "framework": plan["framework"],
            "places": plan.get("places", 2), "chart": plan["chart"],
            "prior_closing": plan.get("prior_closing") or {},
            "opening": plan.get("opening") or [], "entries": entries,
            "schedules": plan.get("schedules") or []}
    if plan.get("reconciliation") is not None:
        spec["reconciliation"] = plan["reconciliation"]
    if plan.get("policy_changes") is not None:
        spec["policy_changes"] = plan["policy_changes"]
    return spec


def validate_plan(plan):
    """Every reason the plan cannot build, in the order a reader would fix them."""
    if not isinstance(plan, dict):
        return ["the plan must be an object"]
    errs = [f"{k} is required" for k in _PLAN_KEYS if not plan.get(k)]
    if errs:
        return errs
    errs += validate_policy(plan.get("policy"))
    errs += validate_chart(plan.get("chart") or [])
    chart = plan.get("chart") or []
    codes = {r.get("code") for r in chart}
    errs += validate_entries(plan.get("entries") or [], chart, plan.get("places", 2))
    adjustments = plan.get("adjustments") or []
    if not isinstance(adjustments, list):
        errs.append("adjustments must be a list")
        adjustments = []
    placements = plan.get("period") or {}
    for i, a in enumerate(adjustments):
        tag = f"adjustments[{i}]"
        if not isinstance(a, dict):
            errs.append(f"{tag} must be an object")
            continue
        if a.get("function") not in FUNCTIONS:
            errs.append(f"{tag}: unknown function {a.get('function')!r}; known: {sorted(FUNCTIONS)}")
        if a.get("debit") not in codes:
            errs.append(f"{tag}: debit account {a.get('debit')!r} is not in the chart")
        if a.get("credit") not in codes:
            errs.append(f"{tag}: credit account {a.get('credit')!r} is not in the chart")
        if a.get("debit") and a.get("debit") == a.get("credit"):
            errs.append(f"{tag}: debit and credit are the same account, so the entry would do nothing")
        if a.get("date") is not None and not ledger.DATE.fullmatch(str(a["date"])):
            errs.append(f"{tag}: date must be YYYY-MM-DD")
        elif a.get("date") and placements.get("start") and not (placements["start"] <= a["date"] <= placements.get("end", "9999-12-31")):
            errs.append(f"{tag}: date is outside the period")
    tax = [a for a in adjustments if isinstance(a, dict) and a.get("function") == "tax_on_pretax"]
    if tax and (plan.get("policy") or {}).get("tax_rate") is None:
        errs.append("a tax adjustment needs policy.tax_rate; the rate is never assumed")
    try:
        accounts.validate_spec(_spec(plan, []))
    except (KeyError, TypeError) as ex:
        errs.append(f"the plan cannot be assembled: {ex}")
    return errs


def build(plan):
    """Build the engagement and gate it on the articulation identities.

    Returns the `accounts.build` result plus `articulation`, `assumptions`, `pretax_income` and
    `skipped_adjustments`. Raises `PlanError` when the plan is invalid or a check fails; a statement
    that does not tie is never returned as though it did.
    """
    errs = validate_plan(plan)
    if errs:
        raise PlanError("; ".join(errs))

    policy = plan.get("policy") or {}
    places = plan.get("places", 2)
    end = plan["period"]["end"]
    adjustments = plan.get("adjustments") or []
    non_tax = [a for a in adjustments if a["function"] != "tax_on_pretax"]
    tax = [a for a in adjustments if a["function"] == "tax_on_pretax"]

    extra, skipped = resolve_adjustments(non_tax, policy, end, places=places)
    first = accounts.build(_spec(plan, extra))
    pretax = D(first["net_income"])

    result = first
    final_spec = _spec(plan, extra)
    if tax:
        tax_entries, tax_skipped = resolve_adjustments(tax, policy, end, pretax_income=pretax, places=places)
        skipped += tax_skipped
        final_spec = _spec(plan, extra + tax_entries)
        result = accounts.build(final_spec)

    checks = articulation(result, plan)
    failed = [(n, d) for n, ok, d in checks if not ok]
    if failed:
        raise PlanError("the statements do not tie: " + "; ".join(f"{n} ({d})" for n, d in failed))

    return {**result, "articulation": checks, "assumptions": manifest(policy),
            "pretax_income": pretax, "skipped_adjustments": skipped, "spec": final_spec}


def articulation(result, plan):
    """The three identities the tips call non-negotiable, computed from the built record.

    Assets = liabilities + equity; the cash-flow statement's movement equals the change in cash on
    the balance sheet; and receipts minus payments equals ending cash. The last is the strongest
    because it compares cash computed two ways: from the cash transactions and from the accrual
    statements.
    """
    ap = result["_appendix"]
    st, cf = ap["statements"], ap["cash_flow"]
    assets = D(str(st["total_assets"]))
    liab = D(str(st["total_liabilities"]))
    equity = D(str(st["equity_with_current_earnings"]))
    checks = [("assets_equal_liabilities_plus_equity", assets == liab + equity,
               f"assets {assets}, liabilities + equity {liab + equity}")]

    cash_codes = [r["code"] for r in plan["chart"] if r.get("role") == "cash"]
    prior = plan.get("prior_closing") or {}
    opening = sum((D(str(prior.get(c, 0))) for c in cash_codes), D(0))
    closing = sum((D(str(ap["closing_balances"].get(c, 0))) for c in cash_codes), D(0))
    net = D(str(cf["net_direct"]))
    checks.append(("cash_flow_equals_balance_sheet_cash", net == closing - opening,
                   f"statement {net}, closing cash {closing} less opening {opening} = {closing - opening}"))

    receipts = payments = D(0)
    for entry in ap["journal"]:
        if entry.get("opening"):
            continue
        for line in entry["lines"]:
            if line["account"] in cash_codes:
                receipts += D(str(line["debit"]))
                payments += D(str(line["credit"]))
    ending = opening + receipts - payments
    checks.append(("receipts_minus_payments_equals_ending_cash", ending == closing,
                   f"receipts {receipts} less payments {payments} plus opening {opening} = {ending}, closing cash {closing}"))
    return checks
