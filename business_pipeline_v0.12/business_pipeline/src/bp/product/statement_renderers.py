"""Statement-structure renderers for advanced accounting topics.

Each renderer takes a data dict and produces a formatted text table.
These are RENDERERS (presentation only) — all figures come from the stored record.
"""
from decimal import Decimal as D


def _money(v, places=2):
    try:
        return f"{float(v):,.{places}f}"
    except (ValueError, TypeError):
        return str(v)


def consolidation_worksheet(data):
    """5-column P&L worksheet: P | S | Dr | Cr | Consolidated."""
    lines = ["CONSOLIDATION WORKSHEET (P&L)", ""]
    lines.append(f"{'Line':<30}{'P':>12}{'S':>12}{'Dr':>12}{'Cr':>12}{'Consol':>12}")
    lines.append("-" * 90)
    for row in data.get("rows", []):
        name = row.get("name", "")
        p = _money(row.get("p", 0))
        s = _money(row.get("s", 0))
        dr = _money(row.get("dr", 0))
        cr = _money(row.get("cr", 0))
        consol = _money(row.get("consol", 0))
        lines.append(f"{name:<30}{p:>12}{s:>12}{dr:>12}{cr:>12}{consol:>12}")
    dr_total = sum(r.get("dr", 0) for r in data.get("rows", []))
    cr_total = sum(r.get("cr", 0) for r in data.get("rows", []))
    lines.append("-" * 90)
    lines.append(f"{'Dr total = Cr total':<30}{'':>12}{'':>12}{_money(dr_total):>12}{_money(cr_total):>12}{'':>12}")
    if data.get("nci") is not None:
        lines.append(f"NCI share: {_money(data['nci'])}")
    if data.get("attributable_to_parent") is not None:
        lines.append(f"Attributable to parent: {_money(data['attributable_to_parent'])}")
    return "\n".join(lines)


def oci_statement(data):
    """OCI statement with pre-tax / tax / net-of-tax / recyclable columns."""
    lines = ["STATEMENT OF OTHER COMPREHENSIVE INCOME", ""]
    lines.append(f"{'Component':<35}{'Pre-tax':>12}{'Tax':>12}{'Net':>12}{'Recyclable':>12}")
    lines.append("-" * 83)
    recyclable_total = 0
    nonrecyclable_total = 0
    for row in data.get("components", []):
        name = row.get("name", "")
        pre = _money(row.get("pre_tax", 0))
        tax = _money(row.get("tax", 0))
        net = _money(row.get("net", 0))
        rec = "Y" if row.get("recyclable", False) else "N"
        lines.append(f"{name:<35}{pre:>12}{tax:>12}{net:>12}{rec:>12}")
        if row.get("recyclable"):
            recyclable_total += row.get("net", 0)
        else:
            nonrecyclable_total += row.get("net", 0)
    lines.append("-" * 83)
    lines.append(f"{'Total OCI':<35}{_money(data.get('total_pre_tax',0)):>12}{_money(data.get('total_tax',0)):>12}{_money(data.get('total_net',0)):>12}")
    lines.append(f"{'  Recyclable subtotal':<35}{'':>12}{'':>12}{_money(recyclable_total):>12}")
    lines.append(f"{'  Non-recyclable subtotal':<35}{'':>12}{'':>12}{_money(nonrecyclable_total):>12}")
    return "\n".join(lines)


def eps_note(data):
    """EPS note with allocation + sequencing tables."""
    lines = ["EARNINGS PER SHARE NOTE", ""]
    lines.append("Table 1: Earnings allocation")
    lines.append(f"{'Security':<25}{'Δ Numerator':>14}{'Δ Denominator':>16}{'Incremental EPS':>16}{'Include?':>10}")
    lines.append("-" * 81)
    for row in data.get("securities", []):
        name = row.get("name", "")
        num = _money(row.get("delta_num", 0))
        den = _money(row.get("delta_den", 0))
        inc = _money(row.get("incremental_eps", 0))
        inc_flag = "Yes" if row.get("include", False) else "No"
        lines.append(f"{name:<25}{num:>14}{den:>16}{inc:>16}{inc_flag:>10}")
    lines.append("-" * 81)
    if data.get("basic_eps") is not None:
        lines.append(f"Basic EPS: {_money(data['basic_eps'])}")
    if data.get("diluted_eps") is not None:
        lines.append(f"Diluted EPS: {_money(data['diluted_eps'])}")
    return "\n".join(lines)


def segment_note(data):
    """Segment note with segment table + reconciliation."""
    lines = ["SEGMENT REPORTING NOTE", ""]
    lines.append("Table 1: Reportable segments")
    headers = ["Segment", "Ext. rev", "Inter-seg", "Total rev", "Profit", "Assets"]
    lines.append(f"{'Segment':<12}{'Ext.rev':>12}{'Inter-seg':>12}{'Total':>12}{'Profit':>12}{'Assets':>12}")
    lines.append("-" * 72)
    for row in data.get("segments", []):
        name = row.get("name", "")
        ext = _money(row.get("external_revenue", 0))
        inter = _money(row.get("intersegment_revenue", 0))
        total = _money(row.get("total_revenue", 0))
        profit = _money(row.get("profit", 0))
        assets = _money(row.get("assets", 0))
        lines.append(f"{name:<12}{ext:>12}{inter:>12}{total:>12}{profit:>12}{assets:>12}")
    lines.append("-" * 72)
    # reconciliation
    lines.append("")
    lines.append("Table 2: Reconciliation to consolidated")
    lines.append(f"{'Item':<30}{'Segments':>12}{'Eliminations':>14}{'Unallocated':>12}{'Consolidated':>14}")
    lines.append("-" * 82)
    for row in data.get("reconciliation", []):
        name = row.get("name", "")
        seg = _money(row.get("segments", 0))
        elim = _money(row.get("eliminations", 0))
        unalloc = _money(row.get("unallocated", 0))
        consol = _money(row.get("consolidated", 0))
        lines.append(f"{name:<30}{seg:>12}{elim:>14}{unalloc:>12}{consol:>14}")
    return "\n".join(lines)


def deferred_tax_note(data):
    """Deferred tax note with rollforward by temporary difference."""
    lines = ["DEFERRED TAX NOTE", ""]
    headers = ["Difference", "Opening", "P&L", "OCI", "Equity", "Acq.", "Closing"]
    lines.append(f"{'Difference':<20}{'Opening':>12}{'P&L':>12}{'OCI':>12}{'Equity':>12}{'Acq.':>12}{'Closing':>12}")
    lines.append("-" * 92)
    for row in data.get("differences", []):
        name = row.get("name", "")
        op = _money(row.get("opening", 0))
        pl = _money(row.get("pl", 0))
        oci = _money(row.get("oci", 0))
        eq = _money(row.get("equity", 0))
        acq = _money(row.get("acquisition", 0))
        cl = _money(row.get("closing", 0))
        lines.append(f"{name:<20}{op:>12}{pl:>12}{oci:>12}{eq:>12}{acq:>12}{cl:>12}")
    lines.append("-" * 92)
    lines.append(f"{'Total DTL':<20}{_money(data.get('total_dtl',0)):>12}")
    lines.append(f"{'Total DTA':<20}{_money(data.get('total_dta',0)):>12}")
    lines.append(f"{'Net':<20}{_money(data.get('net',0)):>12}")
    return "\n".join(lines)


def lease_maturity_table(data):
    """Lease maturity table reconciling undiscounted to liability."""
    lines = ["LEASE MATURITY TABLE", ""]
    lines.append(f"{'Year':<8}{'Payment':>14}{'Factor':>12}{'PV':>14}")
    lines.append("-" * 48)
    for row in data.get("rows", []):
        yr = row.get("year", "")
        pay = _money(row.get("payment", 0))
        factor = _money(row.get("factor", 0), 6)
        pv = _money(row.get("pv", 0))
        lines.append(f"{str(yr):<8}{pay:>14}{factor:>12}{pv:>14}")
    lines.append("-" * 48)
    lines.append(f"{'Total undiscounted':<8}{_money(data.get('total_undiscounted',0)):>14}")
    lines.append(f"{'Less imputed interest':<8}{_money(data.get('imputed_interest',0)):>14}")
    lines.append(f"{'Lease liability':<8}{_money(data.get('liability',0)):>14}")
    return "\n".join(lines)


def pension_reconciliation(data):
    """Pension reconciliation: PBO + plan assets + funded status."""
    lines = ["PENSION RECONCILIATION", ""]
    lines.append("PBO rollforward:")
    for row in data.get("pbo", []):
        lines.append(f"  {row.get('label',''):<30} {_money(row.get('amount',0)):>12}")
    lines.append("")
    lines.append("Plan assets rollforward:")
    for row in data.get("plan_assets", []):
        lines.append(f"  {row.get('label',''):<30} {_money(row.get('amount',0)):>12}")
    lines.append("")
    lines.append("Funded status:")
    lines.append(f"  Plan assets: {_money(data.get('plan_assets_total',0)):>12}")
    lines.append(f"  PBO: {_money(data.get('pbo_total',0)):>12}")
    lines.append(f"  Net liability: {_money(data.get('funded_status',0)):>12}")
    return "\n".join(lines)


def restatement_column(data):
    """Restatement column: as reported | correction | restated."""
    lines = ["RESTATEMENT", ""]
    headers = data.get("headers", ["Line", "As reported", "Correction", "Restated"])
    lines.append(f"{headers[0]:<25}{headers[1]:>14}{headers[2]:>14}{headers[3]:>14}")
    lines.append("-" * 67)
    for row in data.get("rows", []):
        name = row.get("name", "")
        ar = _money(row.get("as_reported", 0))
        corr = _money(row.get("correction", 0))
        rest = _money(row.get("restated", 0))
        lines.append(f"{name:<25}{ar:>14}{corr:>14}{rest:>14}")
    return "\n".join(lines)


def oci_statement(data):
    return oci_statement_render(data)


def oci_statement_render(data):
    """Alias for oci_statement."""
    lines = ["STATEMENT OF OTHER COMPREHENSIVE INCOME", ""]
    lines.append(f"{'Component':<35}{'Pre-tax':>12}{'Tax':>12}{'Net':>12}{'Recyclable':>12}")
    lines.append("-" * 83)
    for row in data.get("components", []):
        name = row.get("name", "")
        pre = _money(row.get("pre_tax", 0))
        tax = _money(row.get("tax", 0))
        net = _money(row.get("net", 0))
        rec = "Y" if row.get("recyclable", False) else "N"
        lines.append(f"{name:<35}{pre:>12}{tax:>12}{net:>12}{rec:>12}")
    lines.append("-" * 83)
    lines.append(f"{'Total OCI':<35}{_money(data.get('total_pre_tax',0)):>12}{_money(data.get('total_tax',0)):>12}{_money(data.get('total_net',0)):>12}")
    return "\n".join(lines)


RENDERERS = {
    "consolidation_worksheet": consolidation_worksheet,
    "oci_statement": oci_statement,
    "eps_note": eps_note,
    "segment_note": segment_note,
    "deferred_tax_note": deferred_tax_note,
    "lease_maturity_table": lease_maturity_table,
    "pension_reconciliation": pension_reconciliation,
    "restatement_column": restatement_column,
}


def render(name, data):
    """Render a named structure. Returns text."""
    fn = RENDERERS.get(name)
    if fn is None:
        return f"[Unknown renderer: {name}]"
    return fn(data)
