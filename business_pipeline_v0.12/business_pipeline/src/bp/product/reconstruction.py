"""Reconstruction engine (Tip 5 Type 2): solve for a missing figure from a stated relation.

A reconstruction problem gives some figures and asks for one that is missing.  The rule is
the owner's: **write the formula, substitute the knowns, solve, cross-check with a second
relation.**  This module does exactly that and nothing else:

- a **relation** is a formula with named variables and a stated identity;
- the engine solves the relation for the one unknown it is asked for;
- every solved value carries the relation it came from, so the record can show the working;
- if no relation can solve the target with the stated knowns, the engine names what is missing
  rather than inventing a figure.

Two relation shapes are supported:

- **linear** (additive): ``a = b + c - d``.  Any variable can be solved for by moving terms.
- **ratio** (multiplicative): ``ratio = numerator / denominator``.  The ratio, the numerator or
  the denominator can be solved for.

The engine is deterministic, uses ``Decimal`` only, and returns ``None`` for a target no relation
can reach with the knowns supplied.  It never fills a gap.
"""

from __future__ import annotations

import re

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Callable, Dict, List, Optional


ZERO = Decimal("0")


@dataclass
class LinearRelation:
    """An additive identity: ``terms`` is ``variable -> coefficient`` with the target's coefficient 1.

    The relation is stated as ``sum(coeff * var) = 0``.  Solving for ``target`` gives
    ``target = -sum(other_coeff * other_var) / target_coeff``.
    """
    id: str
    label: str
    formula: str
    terms: Dict[str, Decimal]

    def solve(self, knowns: Dict[str, Decimal]) -> Optional[Dict[str, Decimal]]:
        """Solve for every variable whose coefficient is non-zero, given the others.

        Returns a dict of solved values (usually one) or None when a coefficient is zero or
        a needed known is missing.
        """
        out: Dict[str, Decimal] = {}
        for target, coeff in self.terms.items():
            if coeff == 0:
                continue
            total = ZERO
            ok = True
            for var, c in self.terms.items():
                if var == target:
                    continue
                if var not in knowns:
                    ok = False
                    break
                total += c * knowns[var]
            if ok:
                out[target] = -total / coeff
        return out


@dataclass
class RatioRelation:
    """A multiplicative identity: ``ratio = numerator / denominator`` where each side is a sum."""
    id: str
    label: str
    formula: str
    ratio: str
    numerator: List[str]
    denominator: List[str]

    def solve(self, knowns: Dict[str, Decimal]) -> Optional[Dict[str, Decimal]]:
        out: Dict[str, Decimal] = {}
        # Solve for the ratio when both sides are fully known.
        if all(v in knowns for v in self.numerator) and all(v in knowns for v in self.denominator):
            num = sum((knowns[v] for v in self.numerator), ZERO)
            den = sum((knowns[v] for v in self.denominator), ZERO)
            if den != 0:
                out[self.ratio] = num / den
        # Solve for one numerator variable: var = ratio * den - (other numerator vars)
        if self.ratio in knowns and all(v in knowns for v in self.denominator):
            den = sum((knowns[v] for v in self.denominator), ZERO)
            for var in self.numerator:
                if var in knowns:
                    continue
                others = [v for v in self.numerator if v != var]
                if all(v in knowns for v in others):
                    out[var] = knowns[self.ratio] * den - sum((knowns[v] for v in others), ZERO)
        # Solve for one denominator variable: var = numerator / ratio - (other denominator vars)
        if self.ratio in knowns and all(v in knowns for v in self.numerator):
            num = sum((knowns[v] for v in self.numerator), ZERO)
            if knowns[self.ratio] != 0:
                for var in self.denominator:
                    if var in knowns:
                        continue
                    others = [v for v in self.denominator if v != var]
                    if all(v in knowns for v in others):
                        out[var] = num / knowns[self.ratio] - sum((knowns[v] for v in others), ZERO)
        return out


def _c(v):
    return Decimal(str(v))


#: The relations from Tip 5 Type 2 and the computation document (Section A/B).
RELATIONS: List = [
    LinearRelation(
        id="net_sales", label="Net Sales", formula="Net Sales = Gross Sales - Returns - Discounts - Allowances",
        terms={"net_sales": _c(1), "gross_sales": _c(-1), "sales_returns": _c(1),
               "sales_discounts": _c(1), "sales_allowances": _c(1)},
    ),
    LinearRelation(
        id="net_purchases", label="Net Purchases", formula="Net Purchases = Purchases + Freight-In - Returns - Discounts",
        terms={"net_purchases": _c(1), "purchases": _c(-1), "freight_in": _c(-1),
               "purchase_returns": _c(1), "purchase_discounts": _c(1)},
    ),
    LinearRelation(
        id="cogs", label="Cost of Goods Sold (merchandising)",
        formula="COGS = Beginning Inventory + Net Purchases - Ending Inventory",
        terms={"cogs": _c(1), "beginning_inventory": _c(-1), "net_purchases": _c(-1),
               "ending_inventory": _c(1)},
    ),
    LinearRelation(
        id="cogs_simple", label="Cost of Goods Sold (beginning + purchases - ending)",
        formula="COGS = Beginning Inventory + Purchases - Ending Inventory",
        terms={"cogs": _c(1), "beginning_inventory": _c(-1), "purchases": _c(-1),
               "ending_inventory": _c(1)},
    ),
    LinearRelation(
        id="gross_profit", label="Gross Profit", formula="Gross Profit = Net Sales - COGS",
        terms={"gross_profit": _c(1), "net_sales": _c(-1), "cogs": _c(1)},
    ),
    LinearRelation(
        id="net_income", label="Net Income", formula="Net Income = Revenue - Expenses",
        terms={"net_income": _c(1), "revenue": _c(-1), "expenses": _c(1)},
    ),
    LinearRelation(
        id="accounting_equation", label="Accounting Equation", formula="Assets = Liabilities + Equity",
        terms={"assets": _c(1), "liabilities": _c(-1), "equity": _c(-1)},
    ),
    LinearRelation(
        id="ending_re", label="Ending Retained Earnings",
        formula="Ending RE = Beginning RE + Net Income - Dividends",
        terms={"ending_re": _c(1), "beginning_re": _c(-1), "net_income": _c(-1), "dividends": _c(1)},
    ),
    LinearRelation(
        id="working_capital", label="Working Capital", formula="Working Capital = Current Assets - Current Liabilities",
        terms={"working_capital": _c(1), "current_assets": _c(-1), "current_liabilities": _c(1)},
    ),
    LinearRelation(
        id="cfo_direct", label="Cash Flow from Operations (direct)",
        formula="CFO = Cash Receipts - Cash Payments",
        terms={"cfo": _c(1), "cash_receipts": _c(-1), "cash_payments": _c(1)},
    ),
    LinearRelation(
        id="cfo_indirect", label="Cash Flow from Operations (indirect)",
        formula="CFO = Net Income + Non-cash Items - Increase in Net Working Capital",
        terms={"cfo": _c(1), "net_income": _c(-1), "non_cash_items": _c(-1), "nwc_increase": _c(1)},
    ),
    LinearRelation(
        id="net_income_margin", label="Net Income from margin and sales",
        formula="Net Income = Net Profit Margin x Net Sales (linearised as Net Income - Margin*Sales = 0)",
        terms={"net_income": _c(1), "margin_times_sales": _c(-1)},
    ),
    # Ratio relations
    RatioRelation(
        id="current_ratio", label="Current Ratio", formula="Current Ratio = Current Assets / Current Liabilities",
        ratio="current_ratio", numerator=["current_assets"], denominator=["current_liabilities"],
    ),
    RatioRelation(
        id="debt_to_equity", label="Debt-to-Equity", formula="D/E = Total Liabilities / Total Equity",
        ratio="debt_to_equity", numerator=["total_liabilities"], denominator=["total_equity"],
    ),
    RatioRelation(
        id="roa", label="Return on Assets", formula="ROA = Net Income / Average Total Assets",
        ratio="roa", numerator=["net_income"], denominator=["average_total_assets"],
    ),
    RatioRelation(
        id="roe", label="Return on Equity", formula="ROE = Net Income / Average Equity",
        ratio="roe", numerator=["net_income"], denominator=["average_equity"],
    ),
    RatioRelation(
        id="gross_margin", label="Gross Profit Margin", formula="Gross Margin = Gross Profit / Net Sales",
        ratio="gross_margin", numerator=["gross_profit"], denominator=["net_sales"],
    ),
    RatioRelation(
        id="net_margin", label="Net Profit Margin", formula="Net Margin = Net Income / Net Sales",
        ratio="net_margin", numerator=["net_income"], denominator=["net_sales"],
    ),
    RatioRelation(
        id="inventory_turnover", label="Inventory Turnover", formula="Inventory Turnover = COGS / Average Inventory",
        ratio="inventory_turnover", numerator=["cogs"], denominator=["average_inventory"],
    ),
    RatioRelation(
        id="asset_turnover", label="Total Asset Turnover", formula="Asset Turnover = Net Sales / Average Total Assets",
        ratio="asset_turnover", numerator=["net_sales"], denominator=["average_total_assets"],
    ),
    RatioRelation(
        id="times_interest", label="Times Interest Earned", formula="TIE = EBIT / Interest Expense",
        ratio="times_interest_earned", numerator=["ebit"], denominator=["interest_expense"],
    ),
    RatioRelation(
        id="book_value_share", label="Book Value per Share",
        formula="BVPS = (Total Equity - Preferred Equity) / Common Shares",
        ratio="book_value_per_share", numerator=["total_equity", "preferred_equity"],
        denominator=["common_shares"],
    ),
    RatioRelation(
        id="quick_ratio", label="Quick (Acid-Test) Ratio",
        formula="Quick Ratio = (Cash + Receivables) / Current Liabilities",
        ratio="quick_ratio", numerator=["cash_and_equivalents", "net_accounts_receivable"],
        denominator=["current_liabilities"],
    ),
    RatioRelation(
        id="cash_ratio", label="Cash Ratio",
        formula="Cash Ratio = Cash / Current Liabilities",
        ratio="cash_ratio", numerator=["cash_and_equivalents"],
        denominator=["current_liabilities"],
    ),
    RatioRelation(
        id="debt_ratio", label="Debt Ratio",
        formula="Debt Ratio = Total Liabilities / Total Assets",
        ratio="debt_ratio", numerator=["total_liabilities"], denominator=["total_assets"],
    ),
    RatioRelation(
        id="equity_ratio", label="Equity Ratio",
        formula="Equity Ratio = Total Equity / Total Assets",
        ratio="equity_ratio", numerator=["total_equity"], denominator=["total_assets"],
    ),
    RatioRelation(
        id="return_on_common_equity", label="Return on Common Equity",
        formula="ROCE = (Net Income - Preferred Dividends) / Average Common Equity",
        ratio="return_on_common_equity",
        numerator=["net_income", "preference_dividends"], denominator=["average_common_equity"],
    ),
]


@dataclass
class ReconstructionResult:
    """One solved figure, with the relation it came from and the knowns used."""
    target: str
    value: Decimal
    relation_id: str
    relation_label: str
    formula: str
    knowns: Dict[str, Decimal]
    cross_check: Optional[Dict[str, object]] = None  # second relation that agrees, if one exists


def solve_for(target: str, knowns: Dict[str, Decimal],
              relations: Optional[List] = None) -> Optional[ReconstructionResult]:
    """Solve one variable from the stated relations.

    Returns the first relation that can solve ``target``, or None when no relation can.
    The result carries the relation and the knowns so the record can show the working.
    """
    for rel in (relations or RELATIONS):
        solved = rel.solve(knowns)
        if solved and target in solved:
            val = solved[target]
            if not val.is_finite():
                continue
            return ReconstructionResult(
                target=target, value=val, relation_id=rel.id,
                relation_label=rel.label, formula=rel.formula, knowns=dict(knowns),
            )
    return None


def solve_all(knowns: Dict[str, Decimal], relations: Optional[List] = None) -> Dict[str, ReconstructionResult]:
    """Solve every variable any relation can reach from the knowns, chaining solved values.

    The engine iterates: a value solved by one relation is added to the knowns, so a later
    relation that depends on it can run.  It stops when an iteration adds nothing.  Later
    relations do not overwrite an earlier solved value.
    """
    out: Dict[str, ReconstructionResult] = {}
    env = dict(knowns)
    for _ in range(10):  # bounded; the relation graph is acyclic in practice
        progress = False
        for rel in (relations or RELATIONS):
            solved = rel.solve(env)
            if not solved:
                continue
            for target, val in solved.items():
                if target in out:
                    continue
                if not val.is_finite():
                    continue
                out[target] = ReconstructionResult(
                    target=target, value=val, relation_id=rel.id,
                    relation_label=rel.label, formula=rel.formula, knowns=dict(knowns),
                )
                env[target] = val
                progress = True
        if not progress:
            break
    return out


def cross_check(target: str, knowns: Dict[str, Decimal],
                relations: Optional[List] = None) -> Optional[Dict[str, object]]:
    """Find a second relation that reaches the same target and agrees.

    Tip 5 Type 2 says "cross-check with a second relation".  This returns that second relation
    and whether its value matches the first, or None when no second relation exists.
    """
    primary = None
    for rel in (relations or RELATIONS):
        solved = rel.solve(knowns)
        if solved and target in solved:
            if primary is None:
                primary = (rel, solved[target])
                continue
            if rel.id == primary[0].id:
                continue
            return {"relation_id": rel.id, "relation_label": rel.label,
                    "value": solved[target], "agrees": solved[target] == primary[1]}
    return None


#: Variable aliases a student may write, mapped to the canonical variable name.
ALIASES = {
    "sales": "net_sales",
    "net sales": "net_sales",
    "gross sales": "gross_sales",
    "cost of goods sold": "cogs",
    "cost of sales": "cogs",
    "cost of sales": "cogs",
    "beg inventory": "beginning_inventory",
    "beginning inventory": "beginning_inventory",
    "opening inventory": "beginning_inventory",
    "end inventory": "ending_inventory",
    "ending inventory": "ending_inventory",
    "closing inventory": "ending_inventory",
    "purchases": "purchases",
    "gross profit": "gross_profit",
    "net income": "net_income",
    "net profit": "net_income",
    "revenue": "revenue",
    "expenses": "expenses",
    "total assets": "assets",
    "total liabilities": "liabilities",
    "total equity": "equity",
    "assets": "assets",
    "liabilities": "liabilities",
    "equity": "equity",
    "capital": "equity",
    "beginning retained earnings": "beginning_re",
    "ending retained earnings": "ending_re",
    "dividends": "dividends",
    "current assets": "current_assets",
    "current liabilities": "current_liabilities",
    "working capital": "working_capital",
    "cash receipts": "cash_receipts",
    "cash payments": "cash_payments",
    "net working capital increase": "nwc_increase",
}


def canonical(name: str) -> str:
    """The canonical variable name for a label a student wrote."""
    key = " ".join(str(name or "").strip().lower().split())
    return ALIASES.get(key, key.replace(" ", "_"))


#: Cues that a problem asks for a missing figure, not a fresh set of statements.
RECONSTRUCTION_CUES = re.compile(
    r"\b(?:find|compute|calculate|determine|derive|solve\s+for|what\s+is|what\s+was|how\s+much\s+(?:is|was|are))\b"
    r"|\bmissing\b|\bbalancing\s+figure\b|\bincomplete\s+records\b"
    r"|\bif\s+the\s+(?:capital|purchases|cogs|cost\s+of\s+goods\s+sold|ending\s+inventory|net\s+income|revenue|assets|liabilities|equity)\b",
    re.I)


def detect_reconstruction_problem(text: str) -> bool:
    """True when the text asks for a missing figure that a relation can solve."""
    if not RECONSTRUCTION_CUES.search(text or ""):
        return False
    low = str(text or "").lower()
    # It must name a variable the relation set knows, or say "missing"/"balancing figure".
    if re.search(r"\bmissing\b|\bbalancing\s+figure\b", low):
        return True
    return any(re.search(r"\b" + re.escape(v) + r"\b", low)
               for v in ("capital", "purchases", "cogs", "cost of goods sold",
                         "ending inventory", "beginning inventory", "net income",
                         "revenue", "assets", "liabilities", "equity", "gross profit",
                         "working capital", "current assets", "current liabilities"))


__all__ = [
    "LinearRelation", "RatioRelation", "ReconstructionResult",
    "RELATIONS", "solve_for", "solve_all", "cross_check", "canonical", "ALIASES",
    "detect_reconstruction_problem", "RECONSTRUCTION_CUES",
]
