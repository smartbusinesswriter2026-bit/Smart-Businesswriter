"""Statement projection layer: render IS/RE/BS/CF from a trial balance + account metadata.

This is the declarative line-spec renderer the tips and the MiniMax brief describe: the
trial balance is the single source, account metadata decides where each balance lands, and
presentation_sign is the only place that flips a sign (G1).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List

from . import audit, money, signs


def _bal(tb, code):
    return Decimal(str(tb.balance(code))) if hasattr(tb, "balance") else Decimal(str(tb.get(code, 0)))


def project_is(tb, accounts: Dict[str, Any]) -> List[dict]:
    lines = []
    revenue = Decimal(0)
    expenses = Decimal(0)
    for code, m in sorted(accounts.items()):
        if m.get("statement") != "IS":
            continue
        raw = _bal(tb, code)
        val = signs.SignConvention.for_statement(m, raw)
        entry = {"label": m.get("name", code), "account": code, "amount": money.q(val),
                 "kind": "revenue" if m.get("type") == "income" else "expense"}
        lines.append(entry)
        if m.get("type") == "income":
            revenue += val
        else:
            expenses += val
    ni = revenue - expenses
    lines.append({"label": "Net income", "account": None, "amount": money.q(ni), "kind": "total"})
    return lines


def project_re(opening_re: Decimal, net_income: Decimal, dividends: Decimal) -> List[dict]:
    closing = opening_re + net_income - dividends
    return [
        {"label": "Opening retained earnings", "amount": money.q(opening_re), "kind": "line"},
        {"label": "Net income", "amount": money.q(net_income), "kind": "line"},
        {"label": "Dividends", "amount": money.q(-dividends), "kind": "line"},
        {"label": "Closing retained earnings", "amount": money.q(closing), "kind": "total"},
    ]


def project_bs(tb, accounts: Dict[str, Any]) -> List[dict]:
    lines = []
    assets = Decimal(0)
    liab = Decimal(0)
    equity = Decimal(0)
    for code, m in sorted(accounts.items()):
        if m.get("statement") != "BS":
            continue
        raw = _bal(tb, code)
        val = signs.SignConvention.for_statement(m, raw)
        lines.append({"label": m.get("name", code), "account": code,
                      "amount": money.q(val), "kind": m.get("type", "asset")})
        t = m.get("type")
        if t == "asset":
            assets += val
        elif t == "liability":
            liab += val
        elif t == "equity":
            equity += val
    lines.append({"label": "Total assets", "amount": money.q(assets), "kind": "total"})
    lines.append({"label": "Total liabilities", "amount": money.q(liab), "kind": "total"})
    lines.append({"label": "Total equity", "amount": money.q(equity), "kind": "total"})
    lines.append({"label": "Total liabilities and equity", "amount": money.q(liab + equity), "kind": "total"})
    return lines


def explain_is(lines: List[dict]) -> List:
    out = []
    for l in lines:
        out.append(audit.explain(l["label"], l["amount"], kind=l.get("kind", "line"),
                                account=l.get("account")))
    return out


def project_cf(tb_begin, tb_end, accounts: Dict[str, Any], net_income: Decimal) -> List[dict]:
    # indirect method: NI + noncash addbacks + working capital changes
    cfo = net_income
    for code, m in accounts.items():
        if m.get("cf_bucket") == "operating_noncash":
            raw_end = _bal(tb_end, code)
            raw_begin = _bal(tb_begin, code)
            cfo += (raw_end - raw_begin)
        elif m.get("cf_bucket") == "operating_working_capital":
            raw_end = _bal(tb_end, code)
            raw_begin = _bal(tb_begin, code)
            cfo += -(raw_end - raw_begin)
    cfi = Decimal(0)
    cff = Decimal(0)
    for code, m in accounts.items():
        bucket = m.get("cf_bucket")
        if bucket == "investing":
            cfi += _bal(tb_end, code) - _bal(tb_begin, code)
        elif bucket == "financing":
            cff += _bal(tb_end, code) - _bal(tb_begin, code)
    net_change = cfo + cfi + cff
    return [
        {"label": "Net income", "amount": money.q(net_income), "kind": "line"},
        {"label": "CFO", "amount": money.q(cfo), "kind": "total"},
        {"label": "CFI", "amount": money.q(cfi), "kind": "total"},
        {"label": "CFF", "amount": money.q(cff), "kind": "total"},
        {"label": "Net change in cash", "amount": money.q(net_change), "kind": "total"},
    ]
