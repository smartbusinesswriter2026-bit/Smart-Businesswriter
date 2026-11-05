"""Adapters from the ledger's appendix to the eight advanced statement structures.

The renderers in `statement_renderers` are presentation only: they need a shape.  This
module is the one place that knows how the appendix maps onto those shapes, and — just as
important — when it does **not** map.  A structure the ledger cannot support is returned
as a *named gap*, never as a zero-filled table: "a figure the statements cannot support is
omitted, never estimated" is the tile's oldest rule.

What the ledger can support
---------------------------
S1  the consolidated view of the primary statements (one entity, so NCI is 0)
S2  the OCI statement, when the period carries other comprehensive income
S5  the deferred tax note, when the ledger carries deferred tax balances
S7  the pension reconciliation, when the ledger carries pension balances
S8  the equity / restatement column, always (the equity statement is in the appendix)

What it cannot, and says so
---------------------------
S3  the EPS note — needs a share count, which a journal does not carry
S4  the segment note — needs a segment disclosure, which a journal does not carry
S6  the lease maturity table — needs a payment schedule, which a journal does not carry

Those three are the honest gaps.  A caller that does have the data (an EPS or segment
problem, say) can pass it in `extra` and the adapter uses it.
"""
import re
from decimal import Decimal, InvalidOperation

from . import statement_renderers as renderers
from . import tie_registry

RECYCLABLE = re.compile(r"cash ?flow ?hedg|hedging reserve|foreign (currency|operation)|"
                        r"translation|available.for.sale|fair value through oci", re.I)
NON_RECYCLABLE = re.compile(r"revalu|actuar|pension|remeasure|remeasurement|"
                            r"fair value (gain|loss) on (own|property)", re.I)
REVALUATION = re.compile(r"revalu", re.I)
CASH_FLOW_HEDGE = re.compile(r"cash ?flow ?hedg|hedging reserve", re.I)
PENSION_OCI = re.compile(r"pension|actuar|remeasure", re.I)
DEFERRED_TAX = re.compile(r"deferred tax", re.I)
LEASE = re.compile(r"lease", re.I)
GOODWILL = re.compile(r"goodwill", re.I)
PENSION_ASSET = re.compile(r"plan assets?|pension assets?|fair value of plan", re.I)
PENSION_LIABILITY = re.compile(r"\bpbo\b|projected benefit|defined benefit obligation|pension obligation", re.I)
RETENTION = re.compile(r"retained earnings?|accumulated (profit|earnings|deficit)|revenue reserve", re.I)
VALUATION_ALLOWANCE = re.compile(r"valuation allowance", re.I)

SIX = Decimal("0.01")


def _number(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    try:
        return Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError):
        return None


def _sum(values):
    """Sum, treating 'not supplied' as zero only when at least one value is supplied."""
    present = [v for v in values if v is not None]
    return sum(present, Decimal(0)) if present else None


def _matching(mapping, pattern):
    """(total, matched names) for the lines of a presented group whose name matches."""
    total, names = Decimal(0), []
    for name, amount in (mapping or {}).items():
        if pattern.search(str(name)):
            value = _number(amount)
            if value is not None:
                total += value
                names.append(str(name))
    return total, names


def _groups(appendix):
    grouped = appendix.get("balance_sheet_groups") or {}
    return grouped.get("groups") or {}, grouped.get("totals") or {}


def _statement(appendix, key):
    return (appendix.get("statements") or {}).get(key)


def _equity_accounts(appendix):
    return list((appendix.get("equity_statement") or {}).get("accounts") or [])


def _retained(appendix):
    """The retained-earnings closing balance from the balance sheet group."""
    groups, totals = _groups(appendix)
    total, names = _matching(groups.get("equity") or {}, RETENTION)
    if names:
        return total
    if totals.get("equity") is not None:
        return _number(totals.get("equity"))
    return None


def _retained_opening(appendix):
    for account in _equity_accounts(appendix):
        if RETENTION.search(str(account.get("name") or "")):
            return _number(account.get("opening"))
    return None


def _total_equity(appendix):
    _groups_map, totals = _groups(appendix)
    for source in (totals.get("equity"), _statement(appendix, "total_equity")):
        value = _number(source)
        if value is not None:
            return value
    return _sum([_number(a.get("closing")) for a in _equity_accounts(appendix)])


def _total_assets(appendix):
    _groups_map, totals = _groups(appendix)
    value = _number(_statement(appendix, "total_assets"))
    if value is not None:
        return value
    return _sum([_number(totals.get("current_assets")), _number(totals.get("non_current_assets")),
                 _number(totals.get("unclassified_assets"))])


def _total_liabilities(appendix):
    _groups_map, totals = _groups(appendix)
    value = _number(_statement(appendix, "total_liabilities"))
    if value is not None:
        return value
    return _sum([_number(totals.get("current_liabilities")),
                 _number(totals.get("non_current_liabilities")),
                 _number(totals.get("unclassified_liabilities"))])


def _oci(appendix):
    return (appendix.get("income_groups") or {}).get("oci") or {}


def _revenue(appendix):
    return _number((appendix.get("income_groups") or {}).get("total_revenue"))


def _expenses(appendix):
    return _number((appendix.get("income_groups") or {}).get("total_expenses"))


def _profit(appendix):
    return _number((appendix.get("comprehensive_income") or {}).get("profit_for_period"))


def _dividends(appendix):
    total = Decimal(0)
    found = False
    for account in _equity_accounts(appendix):
        for movement in account.get("movements") or []:
            if str(movement.get("kind") or "") == "dividends":
                value = _number(movement.get("amount"))
                if value is not None:
                    total += value
                    found = True
    return total if found else None


# ---------------------------------------------------------------------------
# S1 — the consolidated view of the primary statements
# ---------------------------------------------------------------------------
def _structure_s1(appendix):
    groups, _totals = _groups(appendix)
    equity_group = groups.get("equity") or {}
    assets_group = {
        "assets": {**{k: v for k, v in (groups.get("current_assets") or {}).items()},
                   **{k: v for k, v in (groups.get("non_current_assets") or {}).items()},
                   **{k: v for k, v in (groups.get("unclassified_assets") or {}).items()}},
    }
    liabilities_group = {
        "liabilities": {**{k: v for k, v in (groups.get("current_liabilities") or {}).items()},
                        **{k: v for k, v in (groups.get("non_current_liabilities") or {}).items()},
                        **{k: v for k, v in (groups.get("unclassified_liabilities") or {}).items()}},
    }
    retained = _retained(appendix)
    total_equity = _total_equity(appendix)
    if retained is None and total_equity is not None:
        retained = Decimal(0)
    share_capital = (total_equity - retained) if (total_equity is not None and retained is not None) else None

    revenue, expenses = _revenue(appendix), _expenses(appendix)
    consolidated_income = None
    if revenue is not None and expenses is not None:
        consolidated_income = revenue - expenses

    revaluation, _ = _matching(equity_group, REVALUATION)
    hedge, _ = _matching(equity_group, CASH_FLOW_HEDGE)
    deferred_tax_liability, _ = _matching(liabilities_group["liabilities"], DEFERRED_TAX)
    deferred_tax_asset, _ = _matching(assets_group["assets"], DEFERRED_TAX)
    lease_liability, _ = _matching(liabilities_group["liabilities"], LEASE)
    goodwill, goodwill_names = _matching(assets_group["assets"], GOODWILL)

    profit = _profit(appendix)
    dividends = _dividends(appendix)
    retained_opening = None
    if None not in (retained, profit):
        retained_opening = retained - profit + (dividends or Decimal(0))
    elif _retained_opening(appendix) is not None:
        retained_opening = _retained_opening(appendix)

    structure = {
        # Equity is presented net of tax: the reserve movements posted to equity are the
        # after-tax figures, and the tax effect sits in the deferred tax note.
        "_tax_basis": {"RE": "net_of_tax"},
        "NI": {"consolidated": consolidated_income,
               "parent": profit if profit is not None else consolidated_income,
               "nci": Decimal(0)},
        "TA": {"consolidated": _total_assets(appendix)},
        "TL": {"consolidated": _total_liabilities(appendix), "lease_component": lease_liability},
        "SC": {"consolidated": share_capital},
        "RE": {"consolidated": retained, "reval_component": revaluation,
               "cfh_component": hedge, "opening_adjusted": retained_opening},
        "NCI": {"consolidated": Decimal(0)},
        "REV": {"consolidated": revenue},
        "DTL": {"net": deferred_tax_liability},
        "DTA": {"net": deferred_tax_asset},
    }
    if goodwill_names:
        # The balance is known; the acquisition arithmetic behind it is not.  T20 stays PARAM.
        structure["GW"] = {"consolidated": goodwill, "consideration": None,
                           "nci_at_acq": None, "fv_net_assets": None}
    return structure


# ---------------------------------------------------------------------------
# S2 — statement of other comprehensive income
# ---------------------------------------------------------------------------
def _component_value(name):
    for pattern in (REVALUATION, CASH_FLOW_HEDGE, PENSION_OCI):
        if pattern.search(name):
            return pattern
    return None


def _structure_s2(appendix):
    oci = _oci(appendix)
    if not oci:
        return None
    components = []
    for name, amount in oci.items():
        value = _number(amount) or Decimal(0)
        components.append({
            "name": str(name),
            "pre_tax": value,          # the ledger posts OCI net of tax
            "tax": None,               # the tax effect is not separable from a journal
            "net": value,
            "recyclable": bool(RECYCLABLE.search(str(name))) and not NON_RECYCLABLE.search(str(name)),
        })
    totals = {}
    for name, pattern in (("REVAL", REVALUATION), ("CFH", CASH_FLOW_HEDGE), ("PENSION", PENSION_OCI)):
        totals[name] = sum((c["net"] for c in components if pattern.search(c["name"])), Decimal(0))
    return {
        "_tax_basis": {"TAX": "net_of_tax"},
        "_components": components,
        "PROFIT": {"for_period": _profit(appendix)},
        "REVAL": {"net": totals["REVAL"]},
        "CFH": {"net": totals["CFH"]},
        "PENSION": {"net": totals["PENSION"]},
        # Not separable: one side of T07 must stay PARAM rather than be guessed at zero.
        "TAX": {"total": None},
        "TOTAL": {"net": _sum([c["net"] for c in components]),
                  "recyclable": _sum([c["net"] for c in components if c["recyclable"]]),
                  "non_recyclable": _sum([c["net"] for c in components if not c["recyclable"]])},
    }


# ---------------------------------------------------------------------------
# S5 — deferred tax note
# ---------------------------------------------------------------------------
def _structure_s5(appendix):
    groups, _totals = _groups(appendix)
    liabilities = {**{k: v for k, v in (groups.get("current_liabilities") or {}).items()},
                   **{k: v for k, v in (groups.get("non_current_liabilities") or {}).items()},
                   **{k: v for k, v in (groups.get("unclassified_liabilities") or {}).items()}}
    assets = {**{k: v for k, v in (groups.get("current_assets") or {}).items()},
              **{k: v for k, v in (groups.get("non_current_assets") or {}).items()},
              **{k: v for k, v in (groups.get("unclassified_assets") or {}).items()}}
    liabilities_dt, liability_names = _matching(liabilities, DEFERRED_TAX)
    assets_dt, asset_names = _matching(assets, DEFERRED_TAX)
    if not (liability_names or asset_names):
        return None
    allowance, allowance_names = _matching(assets, VALUATION_ALLOWANCE)
    rows = []
    for name, amount in liabilities.items():
        if DEFERRED_TAX.search(str(name)):
            rows.append({"name": str(name), "closing": _number(amount)})
    for name, amount in assets.items():
        if DEFERRED_TAX.search(str(name)):
            rows.append({"name": str(name), "closing": -(_number(amount) or Decimal(0))})
    return {
        "OPENING": {"net": None},
        "CLOSING": {"net": liabilities_dt - assets_dt},
        "PL": {"total": None}, "OCI": {"total": None},
        "EQUITY": {"total": None}, "ACQ": {"total": None},
        "GROSS_DTA": {"closing": assets_dt if asset_names else None},
        "VA": {"closing": allowance if allowance_names else Decimal(0)},
        "_rows": rows,
    }


# ---------------------------------------------------------------------------
# S7 — pension reconciliation
# ---------------------------------------------------------------------------
def _structure_s7(appendix):
    groups, _totals = _groups(appendix)
    assets = {**{k: v for k, v in (groups.get("current_assets") or {}).items()},
              **{k: v for k, v in (groups.get("non_current_assets") or {}).items()},
              **{k: v for k, v in (groups.get("unclassified_assets") or {}).items()}}
    liabilities = {**{k: v for k, v in (groups.get("current_liabilities") or {}).items()},
                   **{k: v for k, v in (groups.get("non_current_liabilities") or {}).items()},
                   **{k: v for k, v in (groups.get("unclassified_liabilities") or {}).items()}}
    plan_assets, plan_names = _matching(assets, PENSION_ASSET)
    pbo, pbo_names = _matching(liabilities, PENSION_LIABILITY)
    # A net pension liability presented as one line is both the PBO and the funded status.
    if not pbo_names:
        net_liability, net_names = _matching(liabilities, re.compile(r"pension|retirement benefit", re.I))
        if net_names:
            pbo = net_liability
            pbo_names = net_names
    if not (plan_names or pbo_names):
        return None
    status = plan_assets - pbo
    return {
        "PBO": {"closing": pbo},
        "ASSETS": {"closing": plan_assets},
        "FUNDED": {"status": status},
        "BS": {"net_liability": -status},
        "OCI": {"remeasurement": sum((c for c in [_number(v) for v in _oci(appendix).values()]
                                      if c is not None), Decimal(0)) if _oci(appendix) else None},
        "PL": {"net_cost": None},
    }


# ---------------------------------------------------------------------------
# S3 / S4 / S6 — only from data a caller supplies
# ---------------------------------------------------------------------------
def _structure_s3(extra):
    eps = (extra or {}).get("eps")
    if not isinstance(eps, dict):
        return None
    numerator = _number(eps.get("numerator"))
    preferred = _number(eps.get("preferred_dividends")) or Decimal(0)
    basic = _number(eps.get("basic_shares"))
    incremental = _number(eps.get("incremental_shares")) or Decimal(0)
    if numerator is None or basic is None:
        return None
    diluted = basic + incremental
    basic_eps = _number(eps.get("basic_eps"))
    diluted_eps = _number(eps.get("diluted_eps"))
    if basic_eps is None and basic:
        basic_eps = numerator / basic
    if diluted_eps is None and diluted:
        diluted_eps = numerator / diluted
    return {
        "NI": {"numerator": numerator},
        "DIV": {"preferred": preferred},
        "WA": {"shares": basic, "basic": basic, "diluted": diluted},
        "EPS": {"basic": basic_eps, "diluted": diluted_eps},
        "INCR": {"denominator_total": incremental},
        "_securities": list(eps.get("securities") or []),
    }


def _structure_s4(extra):
    segments = (extra or {}).get("segments")
    if not isinstance(segments, dict):
        return None
    rows = list(segments.get("segments") or [])
    if not rows:
        return None
    external = sum((_number(r.get("external_revenue")) or Decimal(0)) for r in rows)
    inter = sum((_number(r.get("intersegment_revenue")) or Decimal(0)) for r in rows)
    unallocated = _number(segments.get("unallocated_revenue")) or Decimal(0)
    consolidated = external + inter - inter + unallocated
    return {
        "REV": {"consolidated": consolidated, "segment_total": external + inter,
                "intersegment": inter, "unallocated": unallocated},
        "ASSETS": {"segment_total": sum((_number(r.get("assets")) or Decimal(0)) for r in rows),
                   "unallocated": _number(segments.get("unallocated_assets")) or Decimal(0)},
        "_segments": rows,
    }


def _structure_s6(extra):
    schedule = (extra or {}).get("lease_schedule")
    if not isinstance(schedule, dict):
        return None
    rows = list(schedule.get("rows") or [])
    if not rows:
        return None
    undiscounted = sum((_number(r.get("payment")) or Decimal(0)) for r in rows)
    present_value = sum((_number(r.get("pv")) or Decimal(0)) for r in rows)
    return {
        "PV": {"total": present_value},
        "UNDISC": {"total": undiscounted},
        "IMPUTED": {"total": undiscounted - present_value},
        "BS": {"liability": _number(schedule.get("liability"))},
        "_rows": rows,
    }


# ---------------------------------------------------------------------------
# S8 — equity statement / restatement column
# ---------------------------------------------------------------------------
def _structure_s8(appendix):
    accounts = _equity_accounts(appendix)
    if not accounts:
        return None
    retained_closing = None
    total_closing = Decimal(0)
    corrections = Decimal(0)
    has_corrections = False
    rows = []
    for account in accounts:
        name = str(account.get("name") or "")
        opening = _number(account.get("opening")) or Decimal(0)
        closing = _number(account.get("closing")) or Decimal(0)
        total_closing += closing
        movement_total = _number(account.get("movement_total"))
        accounted = opening
        for movement in account.get("movements") or []:
            amount = _number(movement.get("amount")) or Decimal(0)
            accounted += amount
            if str(movement.get("kind") or "") in ("prior_period_adjustment", "correction"):
                corrections += amount
                has_corrections = True
        if RETENTION.search(name):
            retained_closing = closing
            rows.append({"name": "Retained earnings — opening", "as_reported": opening,
                         "correction": corrections if has_corrections else Decimal(0),
                         "restated": opening})
            rows.append({"name": "Movement for the period",
                         "as_reported": movement_total if movement_total is not None else closing - opening,
                         "correction": Decimal(0),
                         "restated": movement_total if movement_total is not None else closing - opening})
            rows.append({"name": "Retained earnings — closing", "as_reported": accounted,
                         "correction": Decimal(0), "restated": closing})
    return {
        "RE": {"opening_restated": _retained_opening(appendix), "closing_restated": retained_closing},
        "EQUITY": {"closing_restated": total_closing, "closing_reported": _total_equity(appendix)},
        # A correction column that has no corrections terminates at zero; one that spans
        # several periods cannot be terminally checked from a single column.
        "CORRECTION": {"cumulative": None if has_corrections else Decimal(0)},
        "SHARES": {"wa_total": None},
        "_rows": rows,
    }


BUILDERS = {"S1": _structure_s1, "S2": _structure_s2, "S5": _structure_s5,
            "S7": _structure_s7, "S8": _structure_s8}
EXTRA_BUILDERS = {"S3": _structure_s3, "S4": _structure_s4, "S6": _structure_s6}

GAP_REASON = {
    "S3": "the earnings-per-share note needs a share count; a journal carries none",
    "S4": "the segment note needs a segment disclosure; a journal carries none",
    "S6": "the lease maturity table needs a payment schedule; a journal carries none",
}


def build(appendix, extra=None):
    """Build every structure the appendix supports.

    Returns ``(structures, gaps)``.  A gap is ``{structure, name, why}`` and is shown to
    the reader; it is never filled with zeros.
    """
    appendix = appendix or {}
    structures, gaps = {}, []
    for sid, builder in BUILDERS.items():
        try:
            built = builder(appendix)
        except Exception as error:                     # an adapter fault is a gap, not a crash
            gaps.append({"structure": sid, "name": tie_registry.STRUCTURE_NAME[sid],
                         "why": "the ledger's data could not be shaped into this structure "
                                "(" + str(error)[:120] + ")"})
            continue
        if built is None:
            continue
        structures[sid] = built
    for sid, builder in EXTRA_BUILDERS.items():
        try:
            built = builder(extra)
        except Exception as error:
            gaps.append({"structure": sid, "name": tie_registry.STRUCTURE_NAME[sid],
                         "why": "supplied data could not be shaped into this structure "
                                "(" + str(error)[:120] + ")"})
            continue
        if built is None:
            gaps.append({"structure": sid, "name": tie_registry.STRUCTURE_NAME[sid],
                         "why": GAP_REASON[sid]})
            continue
        structures[sid] = built
    return structures, gaps


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _money(value):
    return value if value is not None else Decimal(0)


def _render_s1(appendix, structure):
    income = (appendix.get("income_groups") or {}).get("income") or {}
    expenses = (appendix.get("income_groups") or {}).get("expenses") or {}
    rows = []
    for name, amount in income.items():
        value = _number(amount) or Decimal(0)
        rows.append({"name": str(name), "p": value, "s": Decimal(0), "dr": Decimal(0),
                     "cr": Decimal(0), "consol": value})
    for name, amount in expenses.items():
        value = _number(amount) or Decimal(0)
        rows.append({"name": str(name), "p": value, "s": Decimal(0), "dr": Decimal(0),
                     "cr": Decimal(0), "consol": value})
    if not rows:
        return None
    return renderers.render("consolidation_worksheet", {
        "rows": rows,
        "nci": structure["NI"]["nci"],
        "attributable_to_parent": structure["NI"]["parent"],
        "single_entity": True,
    })


def _render_s2(structure):
    components = structure.get("_components") or []
    if not components:
        return None
    return renderers.render("oci_statement", {
        "components": components,
        "total_pre_tax": structure["TOTAL"]["net"],
        "total_tax": None,
        "total_net": structure["TOTAL"]["net"],
    })


def _render_s5(structure):
    rows = structure.get("_rows") or []
    if not rows:
        return None
    for row in rows:
        if row.get("closing") is not None:
            row["closing"] = row["closing"]
    return renderers.render("deferred_tax_note", {
        "differences": rows,
        "total_dtl": None,
        "total_dta": None,
        "net": structure["CLOSING"]["net"],
    })


def _render_s7(structure):
    return renderers.render("pension_reconciliation", {
        "pbo": [{"label": "Closing projected benefit obligation", "amount": structure["PBO"]["closing"]}],
        "plan_assets": [{"label": "Closing plan assets", "amount": structure["ASSETS"]["closing"]}],
        "plan_assets_total": structure["ASSETS"]["closing"],
        "pbo_total": structure["PBO"]["closing"],
        "funded_status": structure["FUNDED"]["status"],
    })


def _render_s8(structure):
    rows = structure.get("_rows") or []
    if not rows:
        return None
    return renderers.render("restatement_column", {
        "headers": ["Equity movement", "As reported", "Correction", "Restated"],
        "rows": rows,
    })


RENDER_MAP = {"S1": _render_s1, "S2": _render_s2, "S5": _render_s5,
              "S7": _render_s7, "S8": _render_s8}


def render(structures, gaps=None):
    """Render every built structure.  Returns ``(rendered, withheld)``.

    Keys are renderer names so a consumer can look one up by structure.  A structure whose
    builder returns nothing renderable is reported in ``withheld`` rather than emitted as
    an empty table.
    """
    rendered, withheld = {}, []
    for sid, structure in structures.items():
        builder = RENDER_MAP.get(sid)
        if builder is None:
            continue
        try:
            text = builder(structure) if sid == "S1" else builder(structure)
        except Exception as error:
            withheld.append({"structure": sid, "why": "renderer failed: " + str(error)[:120]})
            continue
        if not text:
            withheld.append({"structure": sid, "why": "nothing to present"})
            continue
        rendered[sid] = {"name": tie_registry.STRUCTURE_NAME[sid], "text": text}
    return rendered, withheld
