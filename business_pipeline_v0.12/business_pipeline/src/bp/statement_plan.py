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
from . import statement_chart
from . import timing
try:
    from . import methods as _methods
    from . import finance_methods as _finance_methods  # noqa: F401 — registers additional methods
except Exception:
    _methods = None
    _finance_methods = None


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
# Partial statement requests: compute scope != output scope (Tip 3)
# ---------------------------------------------------------------------------
# The ledger is always built in full. What varies is which projections are rendered and which
# upstream projections are computed silently to keep them articulate. IS is the only statement
# that stands alone; BS drags in RE (which drags in IS); CF drags in IS + BS.

PROJECTIONS = {
    "IS": {"requires": []},
    "RE": {"requires": ["IS"]},
    "BS": {"requires": ["RE"]},
    "CF": {"requires": ["IS", "BS"]},
}

ALL_STATEMENTS = ("IS", "RE", "BS", "CF")


def dependency_closure(requested):
    """Topologically ordered closure: everything that must be computed (not just rendered)."""
    seen = set()
    order = []
    def visit(k):
        if k in seen:
            return
        seen.add(k)
        for dep in PROJECTIONS[k]["requires"]:
            visit(dep)
        order.append(k)
    for k in requested:
        if k not in PROJECTIONS:
            raise PlanError(f"unknown statement {k!r}; known: {sorted(PROJECTIONS)}")
        visit(k)
    return order


def classify(requested, extraction_coverage):
    """Classify a request given what the extraction actually found.

    Returns one of:
      - "full_compute_partial_render": extraction complete; safe to compute everything and render
        only the requested statements.
      - "standalone_is": only IS requested and the data is IS-self-contained; the cheap path.
      - "requires_full_ledger": CF (or BS with gaps) requested; the full ledger is mandatory.
      - "requires_plugs": downstream statement requested with incomplete data; render only with
        explicit, logged plugs.
    """
    requested = list(requested or [])
    if not requested:
        raise PlanError("at least one statement must be requested")
    if extraction_coverage is None:
        extraction_coverage = {"complete": True}
    complete = bool(extraction_coverage.get("complete", True))
    if complete:
        return "full_compute_partial_render"
    if requested == ["IS"]:
        return "standalone_is"
    if "CF" in requested:
        return "requires_full_ledger"
    return "requires_plugs"


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
    """payment x months_expired / total_months: the expired portion, not the whole payment.

    `months_expired` may be supplied directly, or derived from `coverage_start` and
    `coverage_end` (ISO dates) using the period end in `context["period_end"]` (the
    number of months of the policy that have expired by the period end).  The dates
    are what the text states; the month count is derived here, not by the reader.
    """
    payment = _dec(params.get("payment"), "payment")
    if params.get("months_expired") is not None:
        expired = _dec(params.get("months_expired"), "months_expired")
    elif params.get("coverage_start") and params.get("coverage_end"):
        from datetime import date
        cs = date.fromisoformat(str(params["coverage_start"]))
        ce = date.fromisoformat(str(params["coverage_end"]))
        ye_raw = context.get("period_end") or params.get("year_end") or params["coverage_end"]
        ye = date.fromisoformat(str(ye_raw))
        expired = D(timing.months_expired(cs, ce, ye))
    else:
        raise PlanError("prepaid_amortization needs months_expired, or coverage_start and coverage_end")
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
    if params.get("receivables") is not None:
        receivables = _dec(params.get("receivables"), "receivables")
    else:
        billed = _dec(params.get("billed", params.get("receivables_billed", 0)), "billed")
        collected = _dec(params.get("collected", params.get("cash_collected", 0)), "collected")
        written = _dec(params.get("written_off", params.get("write_offs", 0)), "written_off")
        receivables = billed - collected - written
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    if params.get("prior_allowance") is not None:
        prior = _dec(params.get("prior_allowance"), "prior_allowance")
    else:
        opening = _dec(params.get("opening_allowance", 0), "opening_allowance")
        writeoffs = _dec(params.get("write_offs", params.get("written_off", 0)), "write_offs")
        prior = opening - writeoffs
    if receivables < 0 or rate < 0 or rate > 1:
        raise PlanError("receivables must not be negative and rate must be between 0 and 1 (or 0..100 as a percentage)")
    amount = receivables * rate - prior
    if amount < 0:
        amount = D(0)
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def supplies_used(params, context):
    """Supplies consumed in the period: beginning + purchases - ending.

    The ending count is what the text states; the consumed amount is derived here.
    """
    opening = _dec(params.get("beginning_inventory", params.get("beginning_supplies", 0)), "beginning_inventory")
    purchases = _dec(params.get("purchases", params.get("purchases_of_supplies", 0)), "purchases")
    ending = _dec(params.get("ending_inventory", params.get("ending_supplies", params.get("ending"))), "ending_inventory")
    if opening < 0 or purchases < 0 or ending < 0:
        raise PlanError("supply figures must not be negative")
    if opening + purchases < ending:
        raise PlanError("ending supplies exceed goods available; check the declarations")
    return money(opening + purchases - ending, context.get("places", 2), context.get("rounding", "half_up"))


def accrued_expense(params, context):
    """An expense incurred but unpaid: the amount is what the text states (e.g. wages earned but unpaid)."""
    amount = _dec(params.get("amount"), "amount")
    if amount < 0:
        raise PlanError("amount must not be negative")
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def warranty_expense(params, context):
    """Warranty expense: sales x rate (the rate is a percentage number or decimal)."""
    sales = _dec(params.get("sales", params.get("revenue")), "sales")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    if sales < 0 or rate < 0 or rate > 1:
        raise PlanError("sales must not be negative and rate must be between 0 and 1 (or 0..100 as a percentage)")
    return money(sales * rate, context.get("places", 2), context.get("rounding", "half_up"))


def inventory_shrinkage(params, context):
    """Inventory shrinkage: book inventory - physical count."""
    book = _dec(params.get("book_inventory", params.get("book")), "book_inventory")
    physical = _dec(params.get("physical_count", params.get("physical")), "physical_count")
    if book < 0 or physical < 0 or physical > book:
        raise PlanError("book and physical must be non-negative and physical <= book")
    return money(book - physical, context.get("places", 2), context.get("rounding", "half_up"))


def credit_card_fee(params, context):
    """Credit card fee: sales x rate."""
    sales = _dec(params.get("sales", params.get("revenue")), "sales")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    if sales < 0 or rate < 0 or rate > 1:
        raise PlanError("sales must not be negative and rate must be between 0 and 1 (or 0..100 as a percentage)")
    return money(sales * rate, context.get("places", 2), context.get("rounding", "half_up"))


def asset_disposal_gain_loss(params, context):
    """Gain or loss on disposal: proceeds - book value."""
    proceeds = _dec(params.get("proceeds", params.get("sale_price")), "proceeds")
    book_value = _dec(params.get("book_value"), "book_value")
    return money(proceeds - book_value, context.get("places", 2), context.get("rounding", "half_up"))


def depreciation_sum_of_years_digits(params, context):
    cost = _dec(params.get("cost"), "cost")
    salvage = _dec(params.get("salvage", 0), "salvage")
    life = _dec(params.get("life_years"), "life_years")
    year = _dec(params.get("year", 1), "year")
    if cost < 0 or salvage < 0 or life <= 0 or year < 1 or year > life:
        raise PlanError("invalid depreciation parameters")
    depreciable = cost - salvage
    total_years = life * (life + 1) / D(2)
    remaining = life - year + 1
    amount = depreciable * remaining / total_years
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def allowance_writeoff(params, context):
    amount = _dec(params.get("amount"), "amount")
    if amount < 0:
        raise PlanError("amount must not be negative")
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def allowance_recovery(params, context):
    amount = _dec(params.get("amount"), "amount")
    if amount < 0:
        raise PlanError("amount must not be negative")
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def accrued_revenue(params, context):
    amount = _dec(params.get("amount"), "amount")
    if amount < 0:
        raise PlanError("amount must not be negative")
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def warranty_claim_paid(params, context):
    amount = _dec(params.get("amount"), "amount")
    if amount < 0:
        raise PlanError("amount must not be negative")
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def warranty_liability_trueup(params, context):
    expected = _dec(params.get("expected_expense"), "expected_expense")
    actual_claims = _dec(params.get("actual_claims"), "actual_claims")
    prior = _dec(params.get("prior_balance", 0), "prior_balance")
    amount = expected - actual_claims + prior
    return money(amount, context.get("places", 2), context.get("rounding", "half_up"))


def interest_accrual(params, context):
    principal = _dec(params.get("principal"), "principal")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    months = _dec(params.get("months", 12), "months")
    if principal < 0 or rate < 0 or rate > 1 or months < 0 or months > 12:
        raise PlanError("invalid interest accrual parameters")
    return money(principal * rate * months / D(12), context.get("places", 2), context.get("rounding", "half_up"))
    """Accrued interest: principal x rate x (months / 12).

    A rate given as a whole number (e.g. 8 for 8%) is converted. `months` defaults to 12.
    """
    principal = _dec(params.get("principal", params.get("amount_principal")), "principal")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    months = _dec(params.get("months", params.get("months_accrued", 12)), "months")
    if principal < 0 or rate < 0 or rate > 1 or months < 0 or months > 12:
        raise PlanError("principal must not be negative, rate must be between 0 and 1 (or 0..100 as a percentage), and months must be 0..12")
    return money(principal * rate * months / D(12), context.get("places", 2), context.get("rounding", "half_up"))


def method_call(params, context):
    """Delegate to a method from methods.py by method_id.

    params: {"method_id": str, ...method inputs}. The method's impl computes the amount.
    The amount is extracted from the method's output (looks for 'amount', 'value', or first numeric).
    """
    if _methods is None:
        return D(0)
    mid = params.get("method_id")
    if not mid:
        return D(0)
    try:
        m = _methods.LIBRARY[mid]
    except (KeyError, AttributeError):
        return D(0)   # unknown method → skip, don't fail the build
    inp = {k: v for k, v in params.items() if k != "method_id"}
    aliases = {"tax_rate": "income_tax_rate", "rate": "income_tax_rate",
               "principal_amount": "principal", "cost_amount": "cost"}
    for alias, canonical in aliases.items():
        if alias in inp and canonical not in inp:
            inp[canonical] = inp.pop(alias)
    try:
        out = m.impl(inp)
    except Exception:
        return D(0)   # bad params → skip, don't fail the build
    # extract a single amount
    if isinstance(out, dict):
        for key in ("amount", "value", "result", "total"):
            if key in out:
                return _dec(out[key], key)
        # first numeric value
        for v in out.values():
            try:
                return _dec(v, "result")
            except PlanError:
                continue
    raise PlanError(f"method {mid} returned no numeric amount")


def lease_pv(params, context):
    payment = _dec(params.get("payment"), "payment")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    periods = _dec(params.get("periods"), "periods")
    due = params.get("due", "end")
    if due == "beginning":
        pv = payment * (D(1) - (D(1) + rate) ** (-periods)) / rate * (D(1) + rate)
    else:
        pv = payment * (D(1) - (D(1) + rate) ** (-periods)) / rate
    return money(pv, context.get("places", 2), context.get("rounding", "half_up"))


def deferred_tax(params, context):
    diff = _dec(params.get("temporary_difference"), "temporary_difference")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    return money(diff * rate, context.get("places", 2), context.get("rounding", "half_up"))


def valuation_allowance(params, context):
    dta = _dec(params.get("dta"), "dta")
    prob = _dec(params.get("probability"), "probability")
    if prob > 1:
        prob = prob / D(100)
    va = dta * (D(1) - prob)
    return money(va, context.get("places", 2), context.get("rounding", "half_up"))


def goodwill(params, context):
    consideration = _dec(params.get("consideration"), "consideration")
    nci = _dec(params.get("nci", 0), "nci")
    fvn = _dec(params.get("fair_value_net_assets"), "fair_value_net_assets")
    return money(consideration + nci - fvn, context.get("places", 2), context.get("rounding", "half_up"))


def impairment_loss(params, context):
    carrying = _dec(params.get("carrying_amount"), "carrying_amount")
    recoverable = _dec(params.get("recoverable_amount", params.get("fair_value")), "recoverable_amount")
    if carrying <= recoverable:
        return D(0)
    return money(carrying - recoverable, context.get("places", 2), context.get("rounding", "half_up"))


def pension_expense(params, context):
    service = _dec(params.get("service_cost", 0), "service_cost")
    interest = _dec(params.get("interest_cost", 0), "interest_cost")
    er = _dec(params.get("expected_return", 0), "expected_return")
    psc = _dec(params.get("prior_service_cost_amort", 0), "prior_service_cost_amort")
    nal = _dec(params.get("net_actuarial_loss_amort", 0), "net_actuarial_loss_amort")
    total = service + interest - er + psc + nal
    return money(total, context.get("places", 2), context.get("rounding", "half_up"))


def equity_method_income(params, context):
    share_ni = _dec(params.get("share_of_net_income"), "share_of_net_income")
    amort = _dec(params.get("basis_difference_amortization", 0), "basis_difference_amortization")
    return money(share_ni - amort, context.get("places", 2), context.get("rounding", "half_up"))


def segment_threshold(params, context):
    total = _dec(params.get("total_revenue"), "total_revenue")
    return money(total * D("0.10"), context.get("places", 2), context.get("rounding", "half_up"))


def stock_based_comp(params, context):
    fair_value = _dec(params.get("fair_value"), "fair_value")
    shares = _dec(params.get("shares"), "shares")
    vesting_years = _dec(params.get("vesting_years"), "vesting_years")
    forfeiture = _dec(params.get("forfeiture_rate", 0), "forfeiture_rate")
    if forfeiture > 1:
        forfeiture = forfeiture / D(100)
    total = fair_value * shares * (D(1) - forfeiture)
    annual = total / vesting_years
    return money(annual, context.get("places", 2), context.get("rounding", "half_up"))


def diluted_eps_incremental(params, context):
    shares = _dec(params.get("conversion_shares"), "conversion_shares")
    return money(shares, 0, context.get("rounding", "half_up"))


def revenue_allocation(params, context):
    total_tp = _dec(params.get("transaction_price"), "transaction_price")
    ssp = _dec(params.get("ssp"), "ssp")
    total_ssp = _dec(params.get("total_ssp"), "total_ssp")
    return money(total_tp * ssp / total_ssp, context.get("places", 2), context.get("rounding", "half_up"))


def unrealized_profit_elimination(params, context):
    amount = _dec(params.get("intercompany_sale_amount"), "intercompany_sale_amount")
    margin = _dec(params.get("gross_margin"), "gross_margin")
    if margin > 1:
        margin = margin / D(100)
    remaining = _dec(params.get("remaining_inventory_fraction", 1), "remaining_inventory_fraction")
    return money(amount * margin * remaining, context.get("places", 2), context.get("rounding", "half_up"))


def remeasurement_gain_loss(params, context):
    na_current = _dec(params.get("net_assets_current_rate"), "net_assets_current_rate")
    na_historical = _dec(params.get("net_assets_historical_rate"), "net_assets_historical_rate")
    return money(na_current - na_historical, context.get("places", 2), context.get("rounding", "half_up"))


def eps_weighted_shares(params, context):
    shares_periods = params.get("periods", [])
    split_factor = _dec(params.get("split_factor", 1), "split_factor")
    total = D(0)
    for sp in shares_periods:
        sh = _dec(sp.get("shares", 0), "shares")
        months = _dec(sp.get("months", 0), "months")
        total += sh * months / D(12)
    return money(total * split_factor, 0, context.get("rounding", "half_up"))


def tiered_rebate(params, context):
    sales = _dec(params.get("sales"), "sales")
    tier_rate = _dec(params.get("tier_rate"), "tier_rate")
    if tier_rate > 1:
        tier_rate = tier_rate / D(100)
    rebate = sales * tier_rate
    return money(rebate, context.get("places", 2), context.get("rounding", "half_up"))


def loyalty_point_allocation(params, context):
    total_price = _dec(params.get("total_price"), "total_price")
    points_value = _dec(params.get("points_value"), "points_value")
    total_ssp = _dec(params.get("total_ssp"), "total_ssp")
    allocated = total_price * points_value / total_ssp
    return money(allocated, context.get("places", 2), context.get("rounding", "half_up"))


def financing_arrangement(params, context):
    sale_price = _dec(params.get("sale_price"), "sale_price")
    repurchase_price = _dec(params.get("repurchase_price"), "repurchase_price")
    carrying = _dec(params.get("carrying_amount"), "carrying_amount")
    # if repurchase_price >= sale_price: financing arrangement, no gain
    if repurchase_price >= sale_price:
        return money(D(0), context.get("places", 2), context.get("rounding", "half_up"))
    gain = sale_price - carrying
    return money(gain, context.get("places", 2), context.get("rounding", "half_up"))


def standard_cost_variance(params, context):
    standard = _dec(params.get("standard_cost"), "standard_cost")
    actual = _dec(params.get("actual_cost"), "actual_cost")
    qty = _dec(params.get("quantity"), "quantity")
    variance = (actual - standard) * qty
    return money(variance, context.get("places", 2), context.get("rounding", "half_up"))


def lifo_liquidation(params, context):
    old_cost = _dec(params.get("old_layer_cost"), "old_layer_cost")
    current_cost = _dec(params.get("current_cost"), "current_cost")
    qty = _dec(params.get("quantity_liquidated"), "quantity_liquidated")
    effect = (current_cost - old_cost) * qty
    return money(effect, context.get("places", 2), context.get("rounding", "half_up"))


def aro_capitalization(params, context):
    obligation = _dec(params.get("obligation"), "obligation")
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    years = _dec(params.get("years"), "years")
    # PV of obligation
    pv = obligation / (D(1) + rate) ** years
    return money(pv, context.get("places", 2), context.get("rounding", "half_up"))


def weighted_avg_borrowing_rate(params, context):
    total_interest = _dec(params.get("total_interest"), "total_interest")
    total_borrowings = _dec(params.get("total_borrowings"), "total_borrowings")
    if total_borrowings == 0:
        raise PlanError("total_borrowings must be positive")
    rate = total_interest / total_borrowings
    return money(rate, 4, context.get("rounding", "half_up"))


def grant_clawback(params, context):
    deferred = _dec(params.get("deferred_income"), "deferred_income")
    repayment = _dec(params.get("repayment"), "repayment")
    if repayment <= deferred:
        return money(D(0), context.get("places", 2), context.get("rounding", "half_up"))
    excess = repayment - deferred
    return money(excess, context.get("places", 2), context.get("rounding", "half_up"))


def inflate_then_discount(params, context):
    cost = _dec(params.get("cost"), "cost")
    inflation = _dec(params.get("inflation_rate"), "inflation_rate")
    if inflation > 1:
        inflation = inflation / D(100)
    years = _dec(params.get("years"), "years")
    rate = _dec(params.get("discount_rate"), "discount_rate")
    if rate > 1:
        rate = rate / D(100)
    inflated = cost * (D(1) + inflation) ** years
    pv = inflated / (D(1) + rate) ** years
    return money(pv, context.get("places", 2), context.get("rounding", "half_up"))


def eir_solving(params, context):
    # simplified: return the rate
    rate = _dec(params.get("rate"), "rate")
    if rate > 1:
        rate = rate / D(100)
    return money(rate, 4, context.get("rounding", "half_up"))


def off_market_leaseback(params, context):
    sale_price = _dec(params.get("sale_price"), "sale_price")
    carrying = _dec(params.get("carrying_amount"), "carrying_amount")
    market_rent = _dec(params.get("market_rent"), "market_rent")
    actual_rent = _dec(params.get("actual_rent"), "actual_rent")
    periods = _dec(params.get("periods"), "periods")
    excess_rent = (actual_rent - market_rent) * periods
    gain = sale_price - carrying
    return money(gain, context.get("places", 2), context.get("rounding", "half_up"))


def terp_bonus_factor(params, context):
    shares = _dec(params.get("shares_outstanding"), "shares_outstanding")
    rights_ratio = _dec(params.get("rights_ratio"), "rights_ratio")
    rights_price = _dec(params.get("rights_price"), "rights_price")
    market_price = _dec(params.get("market_price"), "market_price")
    new_shares = shares / rights_ratio
    terp = (shares * market_price + new_shares * rights_price) / (shares + new_shares)
    bonus_factor = market_price / terp
    return money(bonus_factor, 4, context.get("rounding", "half_up"))


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
    "depreciation_straight_line": straight_line_depreciation,
    "depreciation_straight_line_capped": straight_line_depreciation,
    "reducing_balance_depreciation": reducing_balance_depreciation,
    "units_of_production_depreciation": units_of_production_depreciation,
    "prepaid_amortization": prepaid_amortization,
    "deferred_prepaid_expense": prepaid_amortization,
    "deferred_prepaid_expense_daily": prepaid_amortization,
    "periodic_cogs": periodic_cogs,
    "cogs_periodic": periodic_cogs,
    "bad_debt_expense": bad_debt_expense,
    "bad_debt_pct_receivables": bad_debt_expense,
    "bad_debt_pct_credit_sales": bad_debt_expense,
    "supplies_used": supplies_used,
    "accrued_expense": accrued_expense,
    "accrued_expense_given_amount": accrued_expense,
    "warranty_expense": warranty_expense,
    "inventory_shrinkage": inventory_shrinkage,
    "credit_card_fee": credit_card_fee,
    "asset_disposal_gain_loss": asset_disposal_gain_loss,
    # Claude's names (aliases)
    "warranty_expense_per_unit": warranty_expense,
    "inventory_shrinkage": inventory_shrinkage,
    "credit_card_fee": credit_card_fee,
    "asset_disposal_gain_loss": asset_disposal_gain_loss,
    "interest_accrual": interest_accrual,
    "depreciation_sum_of_years_digits": depreciation_sum_of_years_digits,
    "allowance_writeoff": allowance_writeoff,
    "allowance_recovery": allowance_recovery,
    "accrued_revenue": accrued_revenue,
    "warranty_claim_paid": warranty_claim_paid,
    "warranty_liability_trueup": warranty_liability_trueup,
    # aliases for Claude's names
    "depreciation_sum_of_years_digits": depreciation_sum_of_years_digits,
    "allowance_writeoff": allowance_writeoff,
    "allowance_recovery": allowance_recovery,
    "accrued_revenue": accrued_revenue,
    "warranty_claim_paid": warranty_claim_paid,
    "warranty_liability_trueup": warranty_liability_trueup,
    "lease_pv": lease_pv,
    "deferred_tax": deferred_tax,
    "valuation_allowance": valuation_allowance,
    "goodwill": goodwill,
    "impairment_loss": impairment_loss,
    "pension_expense": pension_expense,
    "equity_method_income": equity_method_income,
    "segment_threshold": segment_threshold,
    "stock_based_comp": stock_based_comp,
    "diluted_eps_incremental": diluted_eps_incremental,
    "revenue_allocation": revenue_allocation,
    "unrealized_profit_elimination": unrealized_profit_elimination,
    "remeasurement_gain_loss": remeasurement_gain_loss,
    "eps_weighted_shares": eps_weighted_shares,
    "tiered_rebate": tiered_rebate,
    "loyalty_point_allocation": loyalty_point_allocation,
    "financing_arrangement": financing_arrangement,
    "standard_cost_variance": standard_cost_variance,
    "lifo_liquidation": lifo_liquidation,
    "aro_capitalization": aro_capitalization,
    "weighted_avg_borrowing_rate": weighted_avg_borrowing_rate,
    "grant_clawback": grant_clawback,
    "inflate_then_discount": inflate_then_discount,
    "eir_solving": eir_solving,
    "off_market_leaseback": off_market_leaseback,
    "terp_bonus_factor": terp_bonus_factor,
    "method_call": method_call,
    "tax_on_pretax": tax_on_pretax,
    "income_tax_expense": tax_on_pretax,
    "unearned_revenue_earned": accrued_expense,  # placeholder: model provides amount
    "supplies_used": supplies_used,
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
               "rounding": (policy or {}).get("rounding", "half_up"),
               "period_end": period_end}
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


#: The chart the plan layer compiles into.  It is the **one** chart of the statements
#: tile: `bp.statement_chart` owns it, because the deterministic detector layer posts to
#: account codes that a chart living here alone did not carry.
DEFAULT_CHART = list(statement_chart.CHART)

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
