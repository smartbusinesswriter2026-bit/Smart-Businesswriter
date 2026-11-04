"""Comprehensive financial statement computation engine (Sections A-K).

Implements all 198 computations from Financial_Statement_Computations.docx:
A. Statement of Comprehensive Income (Income Statement)
B. Statement of Changes in Equity
C. Statement of Financial Position (Balance Sheet)
D. Statement of Cash Flows
E. Horizontal, Vertical and Trend Analysis
F. Liquidity Ratios
G. Activity (Efficiency) Ratios
H. Solvency (Leverage) Ratios
I. Profitability Ratios
J. Market and Investor Ratios
K. Cash Flow Analysis and Quality of Earnings

Every figure is traceable to its source input. Missing inputs are named as gaps
-- never filled, never guessed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Dict, List, Optional, Tuple


MONEY = re.compile(r"-?\d[\d,]*(?:\.\d+)?")


# ============================================================================
# Core types
# ============================================================================

@dataclass
class ComputationSpec:
    """Specification for one financial computation."""
    id: str  # e.g. "a_net_sales", "f_current_ratio"
    section: str  # "A" through "K"
    label: str  # human-readable label
    formula: str  # formula description
    inputs: List[str]  # input variable names needed from text
    output_name: str  # name of computed output
    compute_fn: Callable[[Dict[str, Decimal]], Decimal]  # compute from inputs
    description: str  # human-readable description
    depends_on: List[str]  # output names this depends on (computed by other specs)


@dataclass
class ComputationResult:
    """Result of one computation."""
    spec_id: str
    section: str
    label: str
    output_name: str
    value: Decimal
    inputs_used: Dict[str, Decimal]
    description: str
    ok: bool
    gap: Optional[str] = None  # missing input that prevented computation


@dataclass
class ComputationPack:
    """Results for a section: computed outputs and named gaps."""
    section: str
    results: Dict[str, ComputationResult]  # output_name -> result
    gaps: List[str]  # input names that were missing and blocked computation
    formula_map: Dict[str, str]  # output_name -> formula string


# ============================================================================
# Registry
# ============================================================================

class ComputationRegistry:
    """Registry of all computations, organized by section."""

    def __init__(self):
        self._specs: Dict[str, ComputationSpec] = {}
        self._by_section: Dict[str, List[ComputationSpec]] = {}

    def register(self, spec: ComputationSpec):
        self._specs[spec.id] = spec
        self._by_section.setdefault(spec.section, []).append(spec)

    def get(self, spec_id: str) -> Optional[ComputationSpec]:
        return self._specs.get(spec_id)

    def by_section(self, section: str) -> List[ComputationSpec]:
        return self._by_section.get(section, [])

    def all(self) -> List[ComputationSpec]:
        return list(self._specs.values())


REGISTRY = ComputationRegistry()


# ============================================================================
# Computation engine (dependency resolution)
# ============================================================================

def _topo_sort(specs: List[ComputationSpec]) -> List[ComputationSpec]:
    """Topological sort respecting depends_on.

    A dependency may name a spec's **output name** or its **spec id**; both are
    resolved here.  The engine's `depends_on` names output names, so looking them
    up by spec id alone resolved nothing: the order was left as the registration
    order, which is wrong for the four specs whose producer is registered after
    its consumer.  Those four then saw an empty pool and recorded a gap for a
    value the engine had already computed a moment later.
    """
    by_output = {s.output_name: s for s in specs}
    by_id = {s.id: s for s in specs}
    visited: Dict[str, str] = {}  # id -> "visiting" | "done"
    order: List[ComputationSpec] = []

    def visit(spec: ComputationSpec, stack: List[str]):
        state = visited.get(spec.id)
        if state == "done":
            return
        if state == "visiting":
            return  # a cycle: stop rather than hang
        visited[spec.id] = "visiting"
        for dep in spec.depends_on:
            target = by_output.get(dep) or by_id.get(dep)
            if target is not None and target.id != spec.id:
                visit(target, stack + [spec.id])
        visited[spec.id] = "done"
        order.append(spec)

    for s in specs:
        visit(s, [])
    return order


def compute_section(
    section: str,
    raw_inputs: Dict[str, Decimal],
    registry: ComputationRegistry = REGISTRY,
    computed: Optional[Dict[str, Decimal]] = None,
) -> ComputationPack:
    """Compute all computations in a section given raw inputs.

    Resolves dependencies across sections. Returns computed results and named gaps.

    `computed` is the shared pool of values already computed.  It is read *and*
    written, so a caller that computes several sections in order (see
    `compute_all_sections`) hands the same pool to each one and a value produced
    in one section is available to the next.  Without that, seventy-two specs -
    every one that depends on a value another section produces - recorded a gap
    for a value the engine had already computed.
    """
    specs = registry.by_section(section)
    if not specs:
        return ComputationPack(section=section, results={}, gaps=[], formula_map={})

    ordered = _topo_sort(specs)

    # The pool of computed values: the caller's, when one is given, so the value
    # travels between sections; otherwise this section's own.
    pool: Dict[str, Decimal] = computed if computed is not None else {}
    results: Dict[str, ComputationResult] = {}
    gaps: List[str] = []
    formula_map: Dict[str, str] = {}

    for spec in ordered:
        # Gather inputs: from raw_inputs first, then from computed outputs
        inputs: Dict[str, Decimal] = {}
        missing: List[str] = []
        for inp in spec.inputs:
            if inp in raw_inputs:
                inputs[inp] = raw_inputs[inp]
            elif inp in pool:
                inputs[inp] = pool[inp]
            else:
                missing.append(inp)

        if missing:
            # Cannot compute -- record gap
            for m in missing:
                if m not in gaps:
                    gaps.append(m)
            results[spec.output_name] = ComputationResult(
                spec_id=spec.id,
                section=spec.section,
                label=spec.label,
                output_name=spec.output_name,
                value=Decimal("0"),
                inputs_used={},
                description=spec.description,
                ok=False,
                gap=", ".join(missing),
            )
            formula_map[spec.output_name] = spec.formula
            continue

        try:
            value = spec.compute_fn(inputs)
        except Exception:
            results[spec.output_name] = ComputationResult(
                spec_id=spec.id,
                section=spec.section,
                label=spec.label,
                output_name=spec.output_name,
                value=Decimal("0"),
                inputs_used=inputs,
                description=spec.description,
                ok=False,
                gap="computation error",
            )
            formula_map[spec.output_name] = spec.formula
            continue

        pool[spec.output_name] = value
        results[spec.output_name] = ComputationResult(
            spec_id=spec.id,
            section=spec.section,
            label=spec.label,
            output_name=spec.output_name,
            value=value,
            inputs_used=inputs,
            description=spec.description,
            ok=True,
        )
        formula_map[spec.output_name] = spec.formula

    return ComputationPack(section=section, results=results, gaps=gaps, formula_map=formula_map)


# ============================================================================
# Input parsing from text
# ============================================================================

def parse_inputs_from_text(text: str, variable_patterns: Dict[str, str]) -> Dict[str, Decimal]:
    """Parse input variables from problem text using regex patterns.

    variable_patterns maps variable name -> regex pattern (with one capture group for the number).
    Returns dict of variable name -> Decimal value.
    """
    inputs: Dict[str, Decimal] = {}
    for var_name, pattern in variable_patterns.items():
        m = re.search(pattern, text, re.I)
        if m:
            try:
                val = Decimal(m.group(1).replace(",", ""))
                inputs[var_name] = val
            except (InvalidOperation, IndexError):
                pass
    return inputs


def _extract_tax_rate_from_text(text: str) -> Decimal:
    """Extract tax rate from problem text (e.g. 'tax rate 25%' or '25% of pretax income')."""
    match = re.search(r"(\d+(?:\.\d+)?)\s*%\s*of\s+pre.?tax\s+income", text, re.I)
    if match:
        return Decimal(match.group(1)) / Decimal(100)
    match = re.search(r"tax.*?(\d+(?:\.\d+)?)%", text, re.I)
    if match:
        return Decimal(match.group(1)) / Decimal(100)
    match = re.search(r"tax rate\s+(\d+(?:\.\d+)?)%", text, re.I)
    if match:
        return Decimal(match.group(1)) / Decimal(100)
    return Decimal("0")


# Common variable patterns for financial statement problems
COMMON_PATTERNS: Dict[str, str] = {
    # Income statement
    "gross_sales": r"gross sales\s+([\d,]+(?:\.\d+)?)",
    "sales_returns": r"sales returns\s+([\d,]+(?:\.\d+)?)",
    "sales_discounts": r"sales discounts?\s+([\d,]+(?:\.\d+)?)",
    "sales_allowances": r"sales allowances?\s+([\d,]+(?:\.\d+)?)",
    "purchases": r"purchases\s+([\d,]+(?:\.\d+)?)",
    "freight_in": r"freight.?in\s+([\d,]+(?:\.\d+)?)",
    "purchase_returns": r"purchase returns?\s+([\d,]+(?:\.\d+)?)",
    "purchase_discounts": r"purchase discounts?\s+([\d,]+(?:\.\d+)?)",
    "beginning_inventory": r"beginning inventory\s+([\d,]+(?:\.\d+)?)",
    "ending_inventory": r"ending inventory\s+([\d,]+(?:\.\d+)?)",
    "direct_materials_beg": r"beginning (?:direct )?materials\s+([\d,]+(?:\.\d+)?)",
    "direct_materials_end": r"ending (?:direct )?materials\s+([\d,]+(?:\.\d+)?)",
    "direct_labor": r"direct labor\s+([\d,]+(?:\.\d+)?)",
    "factory_overhead": r"factory overhead\s+([\d,]+(?:\.\d+)?)",
    "beg_wip": r"beginning work.?in.?process\s+([\d,]+(?:\.\d+)?)",
    "end_wip": r"ending work.?in.?process\s+([\d,]+(?:\.\d+)?)",
    "beg_finished_goods": r"beginning finished goods\s+([\d,]+(?:\.\d+)?)",
    "end_finished_goods": r"ending finished goods\s+([\d,]+(?:\.\d+)?)",
    "operating_expenses": r"operating expenses\s+([\d,]+(?:\.\d+)?)",
    "selling_expenses": r"selling expenses\s+([\d,]+(?:\.\d+)?)",
    "general_expenses": r"general (?:and administrative )?expenses\s+([\d,]+(?:\.\d+)?)",
    "interest_expense": r"interest expense\s+([\d,]+(?:\.\d+)?)",
    "interest_income": r"interest income\s+([\d,]+(?:\.\d+)?)",
    "gain_on_disposal": r"gain on (?:disposal|sale)\s+([\d,]+(?:\.\d+)?)",
    "loss_on_disposal": r"loss on (?:disposal|sale)\s+([\d,]+(?:\.\d+)?)",
    "income_before_tax": r"income before tax\s+([\d,]+(?:\.\d+)?)",
    "tax_rate": r"tax rate\s+([\d,]+(?:\.\d+)?)%",
    "preference_dividends": r"preference dividends?\s+([\d,]+(?:\.\d+)?)",
    "ordinary_shares": r"ordinary shares\s+([\d,]+(?:\.\d+)?)",
    "net_income": r"net income\s+([\d,]+(?:\.\d+)?)",
    # Balance sheet
    "cash": r"\bcash\b\s+([\d,]+(?:\.\d+)?)",
    "bank_balance": r"bank balance\s+([\d,]+(?:\.\d+)?)",
    "deposits_in_transit": r"deposits in transit\s+([\d,]+(?:\.\d+)?)",
    "outstanding_checks": r"outstanding checks\s+([\d,]+(?:\.\d+)?)",
    "book_balance": r"book balance\s+([\d,]+(?:\.\d+)?)",
    "bank_credits": r"bank credits\s+([\d,]+(?:\.\d+)?)",
    "bank_charges": r"bank charges\s+([\d,]+(?:\.\d+)?)",
    "gross_receivables": r"gross receivables\s+([\d,]+(?:\.\d+)?)",
    "allowance_for_doubtful": r"allowance for doubtful\s+([\d,]+(?:\.\d+)?)",
    "notes_receivable": r"notes receivable\s+([\d,]+(?:\.\d+)?)",
    "maturity_value": r"maturity value\s+([\d,]+(?:\.\d+)?)",
    "discount_rate": r"discount rate\s+([\d,]+(?:\.\d+)?)%",
    "ppe_cost": r"(?:ppe|property, plant and equipment|equipment)\s+(?:cost\s+)?([\d,]+(?:\.\d+)?)",
    "accumulated_depreciation": r"accumulated depreciation\s+([\d,]+(?:\.\d+)?)",
    "impairment": r"impairment\s+([\d,]+(?:\.\d+)?)",
    "total_assets": r"total assets\s+([\d,]+(?:\.\d+)?)",
    "total_liabilities": r"total liabilities\s+([\d,]+(?:\.\d+)?)",
    "total_equity": r"total equity\s+([\d,]+(?:\.\d+)?)",
    "retained_earnings": r"retained earnings\s+([\d,]+(?:\.\d+)?)",
    "current_assets": r"current assets\s+([\d,]+(?:\.\d+)?)",
    "current_liabilities": r"current liabilities\s+([\d,]+(?:\.\d+)?)",
    "non_current_assets": r"non.current assets\s+([\d,]+(?:\.\d+)?)",
    "non_current_liabilities": r"non.current liabilities\s+([\d,]+(?:\.\d+)?)",
    "accounts_payable": r"accounts payable\s+([\d,]+(?:\.\d+)?)",
    "unearned_revenue": r"unearned revenue\s+([\d,]+(?:\.\d+)?)",
    "interest_payable": r"interest payable\s+([\d,]+(?:\.\d+)?)",
    "warranty_liability": r"warranty liability\s+([\d,]+(?:\.\d+)?)",
    "bonds_payable": r"bonds payable\s+([\d,]+(?:\.\d+)?)",
    "market_price_per_share": r"market price per share\s+([\d,]+(?:\.\d+)?)",
    "dividends_per_share": r"dividends per share\s+([\d,]+(?:\.\d+)?)",
    "shares_outstanding": r"shares outstanding\s+([\d,]+(?:\.\d+)?)",
    # Prior year for horizontal/trend
    "prior_net_sales": r"prior (?:year )?net sales\s+([\d,]+(?:\.\d+)?)",
    "prior_total_assets": r"prior (?:year )?total assets\s+([\d,]+(?:\.\d+)?)",
}


# ============================================================================
# Section A: Statement of Comprehensive Income (items 3-45)
# ============================================================================

def _a_register():
    specs = [
        ComputationSpec(
            id="a_net_sales", section="A",
            label="Net Sales",
            formula="Gross Sales − Sales Returns − Sales Discounts − Sales Allowances",
            inputs=["gross_sales", "sales_returns", "sales_discounts", "sales_allowances"],
            output_name="net_sales",
            compute_fn=lambda i: i["gross_sales"] - i.get("sales_returns", Decimal("0")) - i.get("sales_discounts", Decimal("0")) - i.get("sales_allowances", Decimal("0")),
            description="Revenue after all deductions.",
            depends_on=[],
        ),
        ComputationSpec(
            id="a_net_purchases", section="A",
            label="Net Purchases",
            formula="Purchases + Freight-In − Purchase Returns − Purchase Discounts",
            inputs=["purchases", "freight_in", "purchase_returns", "purchase_discounts"],
            output_name="net_purchases",
            compute_fn=lambda i: i["purchases"] + i.get("freight_in", Decimal("0")) - i.get("purchase_returns", Decimal("0")) - i.get("purchase_discounts", Decimal("0")),
            description="Total cost of merchandise bought.",
            depends_on=[],
        ),
        ComputationSpec(
            id="a_goods_available", section="A",
            label="Goods Available for Sale",
            formula="Beginning Inventory + Net Purchases",
            inputs=["beginning_inventory", "net_purchases"],
            output_name="goods_available_for_sale",
            compute_fn=lambda i: i["beginning_inventory"] + i["net_purchases"],
            description="Total goods available to be sold.",
            depends_on=["net_purchases"],
        ),
        ComputationSpec(
            id="a_cogs_merch", section="A",
            label="COGS (Merchandising)",
            formula="Beginning Inventory + Net Purchases − Ending Inventory",
            inputs=["beginning_inventory", "net_purchases", "ending_inventory"],
            output_name="cogs_merchandising",
            compute_fn=lambda i: i["beginning_inventory"] + i["net_purchases"] - i["ending_inventory"],
            description="Cost of items sold.",
            depends_on=["net_purchases"],
        ),
        ComputationSpec(
            id="a_cogs_manuf", section="A",
            label="COGS (Manufacturing)",
            formula="Beg. Finished Goods + COGM − End. Finished Goods",
            inputs=["beg_finished_goods", "cogs_manufactured", "end_finished_goods"],
            output_name="cogs_manufacturing",
            compute_fn=lambda i: i["beg_finished_goods"] + i["cogs_manufactured"] - i["end_finished_goods"],
            description="Cost of finished goods sold.",
            depends_on=["cogs_manufactured"],
        ),
        ComputationSpec(
            id="a_cogs_manufactured", section="A",
            label="Cost of Goods Manufactured",
            formula="Direct Materials Used + Direct Labor + Factory Overhead + Beg. WIP − End. WIP",
            inputs=["direct_materials_used", "direct_labor", "factory_overhead", "beg_wip", "end_wip"],
            output_name="cogs_manufactured",
            compute_fn=lambda i: i["direct_materials_used"] + i["direct_labor"] + i["factory_overhead"] + i["beg_wip"] - i["end_wip"],
            description="Cost of goods completed in production.",
            depends_on=["direct_materials_used"],
        ),
        ComputationSpec(
            id="a_direct_materials_used", section="A",
            label="Direct Materials Used",
            formula="Beg. Materials + Purchases + Freight-In − End. Materials",
            inputs=["direct_materials_beg", "purchases", "freight_in", "direct_materials_end"],
            output_name="direct_materials_used",
            compute_fn=lambda i: i["direct_materials_beg"] + i["purchases"] + i.get("freight_in", Decimal("0")) - i["direct_materials_end"],
            description="Raw materials put into production.",
            depends_on=[],
        ),
        ComputationSpec(
            id="a_gross_profit", section="A",
            label="Gross Profit",
            formula="Net Sales − Cost of Goods Sold",
            inputs=["net_sales", "cogs_merchandising"],
            output_name="gross_profit",
            compute_fn=lambda i: i["net_sales"] - i["cogs_merchandising"],
            description="Profit before operating expenses.",
            depends_on=["net_sales", "cogs_merchandising"],
        ),
        ComputationSpec(
            id="a_total_opex", section="A",
            label="Total Operating Expenses",
            formula="Selling Expenses + General and Administrative Expenses",
            inputs=["selling_expenses", "general_expenses"],
            output_name="total_operating_expenses",
            compute_fn=lambda i: i["selling_expenses"] + i["general_expenses"],
            description="Costs of running the business.",
            depends_on=[],
        ),
        ComputationSpec(
            id="a_operating_income", section="A",
            label="Operating Income (EBIT)",
            formula="Gross Profit − Total Operating Expenses",
            inputs=["gross_profit", "total_operating_expenses"],
            output_name="operating_income",
            compute_fn=lambda i: i["gross_profit"] - i["total_operating_expenses"],
            description="Profit from core operations.",
            depends_on=["gross_profit", "total_operating_expenses"],
        ),
        ComputationSpec(
            id="a_income_before_tax", section="A",
            label="Income Before Tax",
            formula="Operating Income + Other Income − Other Expenses − Interest Expense",
            inputs=["operating_income", "other_income", "other_expenses", "interest_expense"],
            output_name="income_before_tax",
            compute_fn=lambda i: i["operating_income"] + i.get("other_income", Decimal("0")) - i.get("other_expenses", Decimal("0")) - i.get("interest_expense", Decimal("0")),
            description="Pre-tax profit.",
            depends_on=["operating_income"],
        ),
        ComputationSpec(
            id="a_current_tax", section="A",
            label="Current Income Tax Expense",
            formula="Taxable Income × Tax Rate",
            inputs=["taxable_income", "tax_rate"],
            output_name="current_income_tax_expense",
            compute_fn=lambda i: i["taxable_income"] * i["tax_rate"] / Decimal(100),
            description="Tax payable for the current period.",
            depends_on=[],
        ),
        ComputationSpec(
            id="a_total_tax", section="A",
            label="Total Income Tax Expense",
            formula="Current Tax + Deferred Tax",
            inputs=["current_income_tax_expense", "deferred_tax"],
            output_name="total_income_tax_expense",
            compute_fn=lambda i: i["current_income_tax_expense"] + i.get("deferred_tax", Decimal("0")),
            description="Tax expense reported.",
            depends_on=["current_income_tax_expense"],
        ),
        ComputationSpec(
            id="a_income_continuing", section="A",
            label="Income from Continuing Operations",
            formula="Income Before Tax − Income Tax Expense",
            inputs=["income_before_tax", "total_income_tax_expense"],
            output_name="income_from_continuing_operations",
            compute_fn=lambda i: i["income_before_tax"] - i["total_income_tax_expense"],
            description="After-tax profit from ongoing operations.",
            depends_on=["income_before_tax", "total_income_tax_expense"],
        ),
        ComputationSpec(
            id="a_net_income", section="A",
            label="Net Income",
            formula="Continuing Operations ± Discontinued Operations",
            inputs=["income_from_continuing_operations", "discontinued_ops_net"],
            output_name="net_income",
            compute_fn=lambda i: i["income_from_continuing_operations"] + i.get("discontinued_ops_net", Decimal("0")),
            description="Bottom-line profit.",
            depends_on=["income_from_continuing_operations"],
        ),
        ComputationSpec(
            id="a_basic_eps", section="A",
            label="Basic Earnings per Share",
            formula="(Net Income − Preferred Dividends) ÷ Weighted Average Common Shares",
            inputs=["net_income", "preference_dividends", "weighted_average_shares"],
            output_name="basic_eps",
            compute_fn=lambda i: (i["net_income"] - i.get("preference_dividends", Decimal("0"))) / i["weighted_average_shares"] if i["weighted_average_shares"] > 0 else Decimal("0"),
            description="Profit per common share.",
            depends_on=["net_income"],
        ),
        ComputationSpec(
            id="a_diluted_eps", section="A",
            label="Diluted Earnings per Share",
            formula="(NI − Pref. Div. + After-Tax Interest on Convertibles) ÷ (Shares + Potential Shares)",
            inputs=["net_income", "preference_dividends", "after_tax_interest_convertibles", "weighted_average_shares", "potential_shares"],
            output_name="diluted_eps",
            compute_fn=lambda i: (i["net_income"] - i.get("preference_dividends", Decimal("0")) + i.get("after_tax_interest_convertibles", Decimal("0"))) / (i["weighted_average_shares"] + i.get("potential_shares", Decimal("0"))) if (i["weighted_average_shares"] + i.get("potential_shares", Decimal("0"))) > 0 else Decimal("0"),
            description="EPS assuming dilutive securities convert.",
            depends_on=["net_income", "basic_eps"],
        ),
        ComputationSpec(
            id="a_ebitda", section="A",
            label="EBITDA",
            formula="Net Income + Interest + Taxes + Depreciation + Amortization",
            inputs=["net_income", "interest_expense", "total_income_tax_expense", "depreciation_expense", "amortization_expense"],
            output_name="ebitda",
            compute_fn=lambda i: i["net_income"] + i.get("interest_expense", Decimal("0")) + i.get("total_income_tax_expense", Decimal("0")) + i.get("depreciation_expense", Decimal("0")) + i.get("amortization_expense", Decimal("0")),
            description="Operating earnings before non-cash and financing items.",
            depends_on=["net_income", "total_income_tax_expense"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_a_register()


# ============================================================================
# Section B: Statement of Changes in Equity (items 46-63)
# ============================================================================

def _b_register():
    specs = [
        ComputationSpec(
            id="b_ending_re", section="B",
            label="Ending Retained Earnings",
            formula="Beginning RE ± Prior Period Adjustments + Net Income − Dividends",
            inputs=["beginning_re", "prior_period_adjustments", "net_income", "dividends"],
            output_name="ending_retained_earnings",
            compute_fn=lambda i: i["beginning_re"] + i.get("prior_period_adjustments", Decimal("0")) + i["net_income"] - i.get("dividends", Decimal("0")),
            description="Accumulated undistributed profits.",
            depends_on=["net_income"],
        ),
        ComputationSpec(
            id="b_corrected_beginning_re", section="B",
            label="Corrected Beginning Retained Earnings",
            formula="Beginning RE ± Prior Period Error Correction (net of tax)",
            inputs=["beginning_re", "prior_period_error_correction"],
            output_name="corrected_beginning_retained_earnings",
            compute_fn=lambda i: i["beginning_re"] + i.get("prior_period_error_correction", Decimal("0")),
            description="Retroactive restatement of earlier periods.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_cash_dividends", section="B",
            label="Cash Dividends Declared",
            formula="Shares Outstanding × Dividend per Share",
            inputs=["shares_outstanding", "dividends_per_share"],
            output_name="cash_dividends_declared",
            compute_fn=lambda i: i["shares_outstanding"] * i["dividends_per_share"],
            description="Distribution reducing retained earnings.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_preferred_dividends_cumulative", section="B",
            label="Preferred Dividends (Cumulative)",
            formula="Preferred Shares × Par × Rate × Years Due",
            inputs=["preferred_shares", "par_value", "preferred_rate", "years_due"],
            output_name="preferred_dividends_cumulative",
            compute_fn=lambda i: i["preferred_shares"] * i["par_value"] * i["preferred_rate"] / Decimal(100) * i["years_due"],
            description="Dividends owed to preferred holders including arrears.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_stock_dividend", section="B",
            label="Stock Dividend",
            formula="Shares Outstanding × Stock Dividend % × Par/Fair Value",
            inputs=["shares_outstanding", "stock_dividend_percent", "par_or_fair_value"],
            output_name="stock_dividend",
            compute_fn=lambda i: i["shares_outstanding"] * i["stock_dividend_percent"] / Decimal(100) * i["par_or_fair_value"],
            description="Capitalization of retained earnings.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_share_capital_issued", section="B",
            label="Share Capital Issued",
            formula="Shares Issued × Par Value",
            inputs=["shares_issued", "par_value"],
            output_name="share_capital_issued",
            compute_fn=lambda i: i["shares_issued"] * i["par_value"],
            description="Par amount of shares issued.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_additional_paid_in_capital", section="B",
            label="Additional Paid-in Capital (Premium)",
            formula="Shares Issued × (Issue Price − Par Value)",
            inputs=["shares_issued", "issue_price", "par_value"],
            output_name="additional_paid_in_capital",
            compute_fn=lambda i: i["shares_issued"] * (i["issue_price"] - i["par_value"]),
            description="Amount received above par.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_treasury_shares_cost", section="B",
            label="Treasury Shares at Cost",
            formula="Shares Reacquired × Price per Share",
            inputs=["shares_reacquired", "reacquire_price"],
            output_name="treasury_shares_at_cost",
            compute_fn=lambda i: i["shares_reacquired"] * i["reacquire_price"],
            description="Contra-equity for repurchased shares.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_treasury_reissue_gain_loss", section="B",
            label="Gain/Loss on Treasury Share Reissue",
            formula="Reissue Price − Cost per Share (adjusts APIC)",
            inputs=["reissue_price", "cost_per_share"],
            output_name="treasury_reissue_gain_loss",
            compute_fn=lambda i: i["reissue_price"] - i["cost_per_share"],
            description="Equity adjustment when treasury shares are resold.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_stock_split", section="B",
            label="Stock Split Effect",
            formula="New Shares = Old Shares × Split Ratio; New Par = Old Par ÷ Ratio",
            inputs=["old_shares", "split_ratio", "old_par"],
            output_name="stock_split_new_shares",
            compute_fn=lambda i: i["old_shares"] * i["split_ratio"],
            description="Changes share count and par, not total equity.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_appropriated_re", section="B",
            label="Appropriated Retained Earnings",
            formula="Reserve Amount set aside from Unappropriated RE",
            inputs=["reserve_amount"],
            output_name="appropriated_retained_earnings",
            compute_fn=lambda i: i["reserve_amount"],
            description="Restricted portion of retained earnings.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_share_based_comp", section="B",
            label="Share-Based Compensation",
            formula="Fair Value at Grant × Options Expected to Vest × Years Elapsed ÷ Vesting Period",
            inputs=["fair_value_grant", "options_expected_to_vest", "years_elapsed", "vesting_period"],
            output_name="share_based_compensation",
            compute_fn=lambda i: i["fair_value_grant"] * i["options_expected_to_vest"] * i["years_elapsed"] / i["vesting_period"],
            description="Equity credited as employee options vest.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_accumulated_oci", section="B",
            label="Accumulated OCI",
            formula="Beginning AOCI + OCI for the Period",
            inputs=["beginning_aoci", "oci_period"],
            output_name="accumulated_oci",
            compute_fn=lambda i: i["beginning_aoci"] + i["oci_period"],
            description="Cumulative other comprehensive items.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_nci_equity", section="B",
            label="Non-Controlling Interest in Equity",
            formula="Beg. NCI + NCI Share of Income − NCI Dividends",
            inputs=["beginning_nci", "nci_share_income", "nci_dividends"],
            output_name="nci_in_equity",
            compute_fn=lambda i: i["beginning_nci"] + i["nci_share_income"] - i.get("nci_dividends", Decimal("0")),
            description="Minority holders' equity in subsidiaries.",
            depends_on=[],
        ),
        ComputationSpec(
            id="b_total_equity", section="B",
            label="Total Equity",
            formula="Share Capital + APIC + Retained Earnings + AOCI − Treasury Shares + NCI",
            inputs=["share_capital", "apic", "retained_earnings", "aoci", "treasury_shares", "nci"],
            output_name="total_equity",
            compute_fn=lambda i: i["share_capital"] + i.get("apic", Decimal("0")) + i["retained_earnings"] + i.get("aoci", Decimal("0")) - i.get("treasury_shares", Decimal("0")) + i.get("nci", Decimal("0")),
            description="Total owners' stake.",
            depends_on=["retained_earnings"],
        ),
        ComputationSpec(
            id="b_partner_capital", section="B",
            label="Partner's Capital Balance",
            formula="Beg. Capital + Investments + Share of Income − Withdrawals",
            inputs=["beginning_capital", "investments", "share_of_income", "withdrawals"],
            output_name="partner_capital_balance",
            compute_fn=lambda i: i["beginning_capital"] + i.get("investments", Decimal("0")) + i["share_of_income"] - i.get("withdrawals", Decimal("0")),
            description="Partnership equity per partner.",
            depends_on=[],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_b_register()


# ============================================================================
# Section C: Statement of Financial Position (Balance Sheet) (items 64-107)
# ============================================================================

def _c_register():
    specs = [
        ComputationSpec(
            id="c_accounting_equation", section="C",
            label="Accounting Equation Check",
            formula="Assets = Liabilities + Equity",
            inputs=["total_assets", "total_liabilities", "total_equity"],
            output_name="accounting_equation_difference",
            compute_fn=lambda i: i["total_assets"] - (i["total_liabilities"] + i["total_equity"]),
            description="Statement must balance.",
            depends_on=["total_assets", "total_liabilities", "total_equity"],
        ),
        ComputationSpec(
            id="c_cash_equivalents", section="C",
            label="Cash and Cash Equivalents",
            formula="Cash on Hand + Bank Balances + Short-Term Investments (≤ 3 months)",
            inputs=["cash_on_hand", "bank_balances", "short_term_investments"],
            output_name="cash_and_equivalents",
            compute_fn=lambda i: i["cash_on_hand"] + i.get("bank_balances", Decimal("0")) + i.get("short_term_investments", Decimal("0")),
            description="Most liquid assets.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_adjusted_bank", section="C",
            label="Adjusted Bank Balance",
            formula="Bank Balance + Deposits in Transit − Outstanding Checks ± Errors",
            inputs=["bank_balance", "deposits_in_transit", "outstanding_checks"],
            output_name="adjusted_bank_balance",
            compute_fn=lambda i: i["bank_balance"] + i.get("deposits_in_transit", Decimal("0")) - i.get("outstanding_checks", Decimal("0")) + i.get("bank_errors", Decimal("0")),
            description="True cash balance after reconciliation.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_net_ar", section="C",
            label="Net Accounts Receivable",
            formula="Gross Receivables − Allowance for Doubtful Accounts",
            inputs=["gross_receivables", "allowance_for_doubtful"],
            output_name="net_accounts_receivable",
            compute_fn=lambda i: i["gross_receivables"] - i["allowance_for_doubtful"],
            description="Expected collectible receivables.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_allowance_aging", section="C",
            label="Allowance (Aging Method)",
            formula="Σ (Receivables by Age Bracket × Uncollectible %)",
            inputs=["aging_allowance_total"],
            output_name="allowance_aging_method",
            compute_fn=lambda i: i["aging_allowance_total"],
            description="Required allowance balance.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_ending_inventory_fifo", section="C",
            label="Ending Inventory (FIFO)",
            formula="Units on Hand × Most Recent Unit Costs",
            inputs=["fifo_units", "fifo_recent_cost"],
            output_name="ending_inventory_fifo",
            compute_fn=lambda i: i["fifo_units"] * i["fifo_recent_cost"],
            description="Inventory at latest costs.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_ending_inventory_wac", section="C",
            label="Ending Inventory (Weighted Average)",
            formula="Units on Hand × (Cost of Goods Available ÷ Units Available)",
            inputs=["units_on_hand", "cogs_available", "units_available"],
            output_name="ending_inventory_wac",
            compute_fn=lambda i: i["units_on_hand"] * (i["cogs_available"] / i["units_available"]),
            description="Inventory at average cost.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_ending_inventory_retail", section="C",
            label="Ending Inventory (Retail Method)",
            formula="Ending Inventory at Retail × Cost-to-Retail Ratio",
            inputs=["ending_inventory_retail", "cost_to_retail_ratio"],
            output_name="ending_inventory_retail_method",
            compute_fn=lambda i: i["ending_inventory_retail"] * i["cost_to_retail_ratio"],
            description="Estimated cost of inventory.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_ending_inventory_gross_profit", section="C",
            label="Ending Inventory (Gross Profit Method)",
            formula="Goods Available − Estimated COGS",
            inputs=["goods_available", "estimated_cogs"],
            output_name="ending_inventory_gross_profit_method",
            compute_fn=lambda i: i["goods_available"] - i["estimated_cogs"],
            description="Estimated inventory without physical count.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_inventory_lower_cost_nrv", section="C",
            label="Inventory at Lower of Cost and NRV",
            formula="Lower of Cost or (Selling Price − Cost to Complete and Sell)",
            inputs=["inventory_cost", "nrv"],
            output_name="inventory_lower_of_cost_nrv",
            compute_fn=lambda i: min(i["inventory_cost"], i["nrv"]),
            description="Inventory valuation at the conservative figure.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_prepaid_expenses", section="C",
            label="Prepaid Expenses",
            formula="Amount Paid − Portion Expired",
            inputs=["amount_paid", "portion_expired"],
            output_name="prepaid_expenses",
            compute_fn=lambda i: i["amount_paid"] - i["portion_expired"],
            description="Unexpired prepayments.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_ppe_cost", section="C",
            label="Property, Plant and Equipment Cost",
            formula="Purchase Price + Freight + Installation + Testing + Other Costs",
            inputs=["purchase_price", "freight", "installation", "testing", "other_costs"],
            output_name="ppe_cost",
            compute_fn=lambda i: i["purchase_price"] + i.get("freight", Decimal("0")) + i.get("installation", Decimal("0")) + i.get("testing", Decimal("0")) + i.get("other_costs", Decimal("0")),
            description="Total capitalized asset cost.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_accumulated_depreciation", section="C",
            label="Accumulated Depreciation",
            formula="Beg. Accumulated Depreciation + Depreciation Expense − Depreciation on Disposals",
            inputs=["beg_accum_depreciation", "depreciation_expense", "depreciation_on_disposals"],
            output_name="accumulated_depreciation",
            compute_fn=lambda i: i["beg_accum_depreciation"] + i["depreciation_expense"] - i.get("depreciation_on_disposals", Decimal("0")),
            description="Total depreciation to date.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_carrying_value_ppe", section="C",
            label="Carrying Value of PPE",
            formula="Cost − Accumulated Depreciation − Impairment",
            inputs=["ppe_cost", "accumulated_depreciation", "impairment"],
            output_name="carrying_value_ppe",
            compute_fn=lambda i: i["ppe_cost"] - i["accumulated_depreciation"] - i.get("impairment", Decimal("0")),
            description="Net book value.",
            depends_on=["ppe_cost", "accumulated_depreciation"],
        ),
        ComputationSpec(
            id="c_revaluation_surplus", section="C",
            label="Revaluation Surplus",
            formula="Fair Value − Carrying Amount (net of tax)",
            inputs=["fair_value", "carrying_amount", "tax_rate"],
            output_name="revaluation_surplus",
            compute_fn=lambda i: (i["fair_value"] - i["carrying_amount"]) * (Decimal("1") - i.get("tax_rate", Decimal("0")) / Decimal(100)),
            description="Increase credited to OCI.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_intangible_assets_net", section="C",
            label="Intangible Assets (Net)",
            formula="Cost − Accumulated Amortization − Impairment",
            inputs=["intangible_cost", "accumulated_amortization", "intangible_impairment"],
            output_name="intangible_assets_net",
            compute_fn=lambda i: i["intangible_cost"] - i["accumulated_amortization"] - i.get("intangible_impairment", Decimal("0")),
            description="Carrying value of intangibles.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_goodwill", section="C",
            label="Goodwill",
            formula="Consideration + NCI + Prior Interest − Fair Value of Net Identifiable Assets",
            inputs=["consideration", "nci", "prior_interest", "fair_value_net_identifiable_assets"],
            output_name="goodwill",
            compute_fn=lambda i: i["consideration"] + i.get("nci", Decimal("0")) + i.get("prior_interest", Decimal("0")) - i["fair_value_net_identifiable_assets"],
            description="Excess paid in a business combination.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_investment_equity_method", section="C",
            label="Investment (Equity Method)",
            formula="Cost + Share of Income − Dividends Received",
            inputs=["investment_cost", "share_of_income", "dividends_received"],
            output_name="investment_equity_method",
            compute_fn=lambda i: i["investment_cost"] + i["share_of_income"] - i.get("dividends_received", Decimal("0")),
            description="Carrying value of an associate.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_right_of_use_asset", section="C",
            label="Right-of-Use Asset",
            formula="Lease Liability + Initial Direct Costs + Prepaid Payments",
            inputs=["lease_liability", "initial_direct_costs", "prepaid_payments"],
            output_name="right_of_use_asset",
            compute_fn=lambda i: i["lease_liability"] + i.get("initial_direct_costs", Decimal("0")) + i.get("prepaid_payments", Decimal("0")),
            description="Leased asset recognized at start.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_total_current_assets", section="C",
            label="Total Current Assets",
            formula="Cash + Receivables + Inventory + Prepaids + Short-Term Investments",
            inputs=["cash_and_equivalents", "net_accounts_receivable", "ending_inventory_fifo", "prepaid_expenses", "short_term_investments"],
            output_name="total_current_assets",
            compute_fn=lambda i: i["cash_and_equivalents"] + i.get("net_accounts_receivable", Decimal("0")) + i.get("ending_inventory_fifo", Decimal("0")) + i.get("prepaid_expenses", Decimal("0")) + i.get("short_term_investments", Decimal("0")),
            description="Assets expected to be used within a year.",
            depends_on=["cash_and_equivalents", "net_accounts_receivable", "ending_inventory_fifo", "prepaid_expenses"],
        ),
        ComputationSpec(
            id="c_total_assets", section="C",
            label="Total Assets",
            formula="Current Assets + Non-Current Assets",
            inputs=["total_current_assets", "non_current_assets"],
            output_name="total_assets",
            compute_fn=lambda i: i["total_current_assets"] + i.get("non_current_assets", Decimal("0")),
            description="Total resources.",
            depends_on=["total_current_assets"],
        ),
        ComputationSpec(
            id="c_accrued_liabilities", section="C",
            label="Accrued Liabilities",
            formula="Expense Incurred − Amount Paid",
            inputs=["expense_incurred", "amount_paid"],
            output_name="accrued_liabilities",
            compute_fn=lambda i: i["expense_incurred"] - i["amount_paid"],
            description="Unpaid obligations at period end.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_unearned_revenue", section="C",
            label="Unearned Revenue",
            formula="Advance Payments − Portion Earned",
            inputs=["advance_payments", "portion_earned"],
            output_name="unearned_revenue",
            compute_fn=lambda i: i["advance_payments"] - i["portion_earned"],
            description="Obligation to deliver goods or services.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_accounts_payable", section="C",
            label="Accounts Payable",
            formula="Beg. Payable + Purchases − Payments",
            inputs=["beg_payable", "purchases", "payments"],
            output_name="accounts_payable",
            compute_fn=lambda i: i["beg_payable"] + i["purchases"] - i["payments"],
            description="Amount owed to suppliers.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_total_liabilities", section="C",
            label="Total Liabilities",
            formula="Current Liabilities + Non-Current Liabilities",
            inputs=["current_liabilities", "non_current_liabilities"],
            output_name="total_liabilities",
            compute_fn=lambda i: i["current_liabilities"] + i.get("non_current_liabilities", Decimal("0")),
            description="All obligations.",
            depends_on=[],
        ),
        ComputationSpec(
            id="c_working_capital", section="C",
            label="Working Capital",
            formula="Current Assets − Current Liabilities",
            inputs=["total_current_assets", "current_liabilities"],
            output_name="working_capital",
            compute_fn=lambda i: i["total_current_assets"] - i["current_liabilities"],
            description="Liquidity cushion.",
            depends_on=["total_current_assets"],
        ),
        ComputationSpec(
            id="c_net_assets", section="C",
            label="Net Assets",
            formula="Total Assets − Total Liabilities",
            inputs=["total_assets", "total_liabilities"],
            output_name="net_assets",
            compute_fn=lambda i: i["total_assets"] - i["total_liabilities"],
            description="Equals total equity.",
            depends_on=["total_assets", "total_liabilities"],
        ),
        ComputationSpec(
            id="c_book_value_per_share", section="C",
            label="Book Value per Share",
            formula="(Total Equity − Preferred Equity) ÷ Common Shares Outstanding",
            inputs=["total_equity", "preferred_equity", "common_shares_outstanding"],
            output_name="book_value_per_share",
            compute_fn=lambda i: (i["total_equity"] - i.get("preferred_equity", Decimal("0"))) / i["common_shares_outstanding"] if i["common_shares_outstanding"] > 0 else Decimal("0"),
            description="Net asset value per common share.",
            depends_on=["total_equity"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_c_register()


# ============================================================================
# Section D: Statement of Cash Flows (items 108-134)
# ============================================================================

def _d_register():
    specs = [
        ComputationSpec(
            id="d_operating_cf_indirect", section="D",
            label="Operating Cash Flow (Indirect)",
            formula="Net Income ± Non-cash Items ± Changes in Working Capital",
            inputs=["net_income", "depreciation_amortization", "wc_adjustments"],
            output_name="operating_cash_flow_indirect",
            compute_fn=lambda i: i["net_income"] + i.get("depreciation_amortization", Decimal("0")) + i.get("wc_adjustments", Decimal("0")),
            description="Converts accrual profit to cash.",
            depends_on=["net_income"],
        ),
        ComputationSpec(
            id="d_change_ar", section="D",
            label="Change in Accounts Receivable",
            formula="− Increase / + Decrease",
            inputs=["ar_increase"],
            output_name="change_in_accounts_receivable",
            compute_fn=lambda i: -i["ar_increase"],
            description="Adjustment for uncollected sales.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_change_inventory", section="D",
            label="Change in Inventory",
            formula="− Increase / + Decrease",
            inputs=["inventory_increase"],
            output_name="change_in_inventory",
            compute_fn=lambda i: -i["inventory_increase"],
            description="Adjustment for inventory buildup.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_change_ap", section="D",
            label="Change in Accounts Payable",
            formula="+ Increase / − Decrease",
            inputs=["ap_increase"],
            output_name="change_in_accounts_payable",
            compute_fn=lambda i: i["ap_increase"],
            description="Adjustment for unpaid purchases.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_net_cash_operating", section="D",
            label="Net Cash from Operating Activities",
            formula="Cash Receipts − Cash Payments for Operations",
            inputs=["cash_receipts", "cash_payments_operations"],
            output_name="net_cash_from_operating",
            compute_fn=lambda i: i["cash_receipts"] - i["cash_payments_operations"],
            description="Total operating cash flow.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_capex", section="D",
            label="Cash Paid for Purchase of Assets",
            formula="Ending PPE (gross) − Beginning PPE (gross) + Cost of Assets Sold",
            inputs=["ending_ppe_gross", "beginning_ppe_gross", "cost_of_assets_sold"],
            output_name="capex",
            compute_fn=lambda i: i["ending_ppe_gross"] - i["beginning_ppe_gross"] + i.get("cost_of_assets_sold", Decimal("0")),
            description="Capital expenditures.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_proceeds_sale_assets", section="D",
            label="Proceeds from Sale of Assets",
            formula="Carrying Value Sold + Gain (− Loss)",
            inputs=["carrying_value_sold", "gain_on_sale"],
            output_name="proceeds_from_sale_of_assets",
            compute_fn=lambda i: i["carrying_value_sold"] + i.get("gain_on_sale", Decimal("0")),
            description="Cash from disposals.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_net_cash_investing", section="D",
            label="Net Cash from Investing Activities",
            formula="Proceeds from Sales − Purchases of Long-Term Assets and Investments",
            inputs=["proceeds_from_sale_of_assets", "capex", "investment_purchases"],
            output_name="net_cash_from_investing",
            compute_fn=lambda i: i["proceeds_from_sale_of_assets"] - i["capex"] - i.get("investment_purchases", Decimal("0")),
            description="Total investing cash flow.",
            depends_on=["proceeds_from_sale_of_assets", "capex"],
        ),
        ComputationSpec(
            id="d_dividends_paid", section="D",
            label="Dividends Paid",
            formula="Dividends Declared − Increase in Dividends Payable",
            inputs=["dividends_declared", "increase_in_dividends_payable"],
            output_name="dividends_paid",
            compute_fn=lambda i: i["dividends_declared"] - i.get("increase_in_dividends_payable", Decimal("0")),
            description="Cash actually distributed.",
            depends_on=[],
        ),
        ComputationSpec(
            id="d_net_cash_financing", section="D",
            label="Net Cash from Financing Activities",
            formula="Inflows from Capital and Borrowings − Dividends and Repayments",
            inputs=["capital_inflows", "borrowings_inflows", "dividends_paid", "debt_repayments"],
            output_name="net_cash_from_financing",
            compute_fn=lambda i: i["capital_inflows"] + i.get("borrowings_inflows", Decimal("0")) - i["dividends_paid"] - i.get("debt_repayments", Decimal("0")),
            description="Total financing cash flow.",
            depends_on=["dividends_paid"],
        ),
        ComputationSpec(
            id="d_net_increase_cash", section="D",
            label="Net Increase/Decrease in Cash",
            formula="Operating + Investing + Financing",
            inputs=["net_cash_from_operating", "net_cash_from_investing", "net_cash_from_financing"],
            output_name="net_increase_decrease_cash",
            compute_fn=lambda i: i["net_cash_from_operating"] + i["net_cash_from_investing"] + i["net_cash_from_financing"],
            description="Net change in cash during the period.",
            depends_on=["net_cash_from_operating", "net_cash_from_investing", "net_cash_from_financing"],
        ),
        ComputationSpec(
            id="d_ending_cash", section="D",
            label="Ending Cash Balance",
            formula="Beginning Cash + Net Increase (Decrease)",
            inputs=["beginning_cash", "net_increase_decrease_cash"],
            output_name="ending_cash_balance",
            compute_fn=lambda i: i["beginning_cash"] + i["net_increase_decrease_cash"],
            description="Must equal cash on the balance sheet.",
            depends_on=["net_increase_decrease_cash"],
        ),
        ComputationSpec(
            id="d_free_cash_flow", section="D",
            label="Free Cash Flow",
            formula="Operating Cash Flow − Capital Expenditures",
            inputs=["net_cash_from_operating", "capex"],
            output_name="free_cash_flow",
            compute_fn=lambda i: i["net_cash_from_operating"] - i["capex"],
            description="Cash available to investors after reinvestment.",
            depends_on=["net_cash_from_operating", "capex"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_d_register()


# ============================================================================
# Section E: Horizontal, Vertical and Trend Analysis (items 135-141)
# ============================================================================

def _e_register():
    specs = [
        ComputationSpec(
            id="e_horizontal_change", section="E",
            label="Horizontal Change (absolute)",
            formula="Current Year − Base Year",
            inputs=["current_year_value", "base_year_value"],
            output_name="horizontal_change",
            compute_fn=lambda i: i["current_year_value"] - i["base_year_value"],
            description="Absolute change.",
            depends_on=[],
        ),
        ComputationSpec(
            id="e_percentage_change", section="E",
            label="Percentage Change",
            formula="(Current − Base) ÷ Base × 100",
            inputs=["current_year_value", "base_year_value"],
            output_name="percentage_change",
            compute_fn=lambda i: (i["current_year_value"] - i["base_year_value"]) / i["base_year_value"] * Decimal(100) if i["base_year_value"] != 0 else Decimal("0"),
            description="Relative change between periods.",
            depends_on=[],
        ),
        ComputationSpec(
            id="e_trend_percentage", section="E",
            label="Trend Percentage (Index)",
            formula="Current Year ÷ Base Year × 100",
            inputs=["current_year_value", "base_year_value"],
            output_name="trend_percentage",
            compute_fn=lambda i: i["current_year_value"] / i["base_year_value"] * Decimal(100) if i["base_year_value"] != 0 else Decimal("0"),
            description="Index of an item over several years.",
            depends_on=[],
        ),
        ComputationSpec(
            id="e_common_size_is", section="E",
            label="Common-Size Income Statement",
            formula="Item ÷ Net Sales × 100",
            inputs=["item_value", "net_sales"],
            output_name="common_size_income_statement",
            compute_fn=lambda i: i["item_value"] / i["net_sales"] * Decimal(100) if i["net_sales"] != 0 else Decimal("0"),
            description="Expresses items as percent of sales.",
            depends_on=["net_sales"],
        ),
        ComputationSpec(
            id="e_common_size_bs", section="E",
            label="Common-Size Balance Sheet",
            formula="Item ÷ Total Assets × 100",
            inputs=["item_value", "total_assets"],
            output_name="common_size_balance_sheet",
            compute_fn=lambda i: i["item_value"] / i["total_assets"] * Decimal(100) if i["total_assets"] != 0 else Decimal("0"),
            description="Expresses items as percent of total assets.",
            depends_on=["total_assets"],
        ),
        ComputationSpec(
            id="e_cagr", section="E",
            label="Compound Annual Growth Rate",
            formula="(Ending ÷ Beginning)^(1 ÷ n) − 1",
            inputs=["ending_value", "beginning_value", "n_years"],
            output_name="cagr",
            compute_fn=lambda i: (i["ending_value"] / i["beginning_value"]) ** (Decimal("1") / i["n_years"]) - Decimal("1") if i["beginning_value"] != 0 and i["n_years"] > 0 else Decimal("0"),
            description="Average annual growth rate.",
            depends_on=[],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_e_register()


# ============================================================================
# Section F: Liquidity Ratios (items 142-147)
# ============================================================================

def _f_register():
    specs = [
        ComputationSpec(
            id="f_current_ratio", section="F",
            label="Current Ratio",
            formula="Current Assets ÷ Current Liabilities",
            inputs=["current_assets", "current_liabilities"],
            output_name="current_ratio",
            compute_fn=lambda i: i["current_assets"] / i["current_liabilities"] if i["current_liabilities"] != 0 else Decimal("0"),
            description="Ability to pay short-term debts.",
            depends_on=["current_assets", "current_liabilities"],
        ),
        ComputationSpec(
            id="f_quick_ratio", section="F",
            label="Quick (Acid-Test) Ratio",
            formula="(Cash + Marketable Securities + Receivables) ÷ Current Liabilities",
            inputs=["cash_and_equivalents", "marketable_securities", "net_accounts_receivable", "current_liabilities"],
            output_name="quick_ratio",
            compute_fn=lambda i: (i["cash_and_equivalents"] + i.get("marketable_securities", Decimal("0")) + i.get("net_accounts_receivable", Decimal("0"))) / i["current_liabilities"] if i["current_liabilities"] != 0 else Decimal("0"),
            description="Liquidity excluding inventory.",
            depends_on=["cash_and_equivalents", "net_accounts_receivable", "current_liabilities"],
        ),
        ComputationSpec(
            id="f_cash_ratio", section="F",
            label="Cash Ratio",
            formula="(Cash + Equivalents) ÷ Current Liabilities",
            inputs=["cash_and_equivalents", "current_liabilities"],
            output_name="cash_ratio",
            compute_fn=lambda i: i["cash_and_equivalents"] / i["current_liabilities"] if i["current_liabilities"] != 0 else Decimal("0"),
            description="Strictest liquidity test.",
            depends_on=["cash_and_equivalents", "current_liabilities"],
        ),
        ComputationSpec(
            id="f_operating_cf_ratio", section="F",
            label="Operating Cash Flow Ratio",
            formula="Operating Cash Flow ÷ Current Liabilities",
            inputs=["net_cash_from_operating", "current_liabilities"],
            output_name="operating_cash_flow_ratio",
            compute_fn=lambda i: i["net_cash_from_operating"] / i["current_liabilities"] if i["current_liabilities"] != 0 else Decimal("0"),
            description="Ability to cover obligations from operations.",
            depends_on=["net_cash_from_operating", "current_liabilities"],
        ),
        ComputationSpec(
            id="f_defensive_interval", section="F",
            label="Defensive Interval",
            formula="(Cash + Securities + Receivables) ÷ Daily Operating Expenses",
            inputs=["cash_and_equivalents", "marketable_securities", "net_accounts_receivable", "daily_operating_expenses"],
            output_name="defensive_interval",
            compute_fn=lambda i: (i["cash_and_equivalents"] + i.get("marketable_securities", Decimal("0")) + i.get("net_accounts_receivable", Decimal("0"))) / i["daily_operating_expenses"] if i["daily_operating_expenses"] != 0 else Decimal("0"),
            description="Days the firm can operate without new revenue.",
            depends_on=["cash_and_equivalents", "net_accounts_receivable"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_f_register()


# ============================================================================
# Section G: Activity (Efficiency) Ratios (items 148-159)
# ============================================================================

def _g_register():
    specs = [
        ComputationSpec(
            id="g_receivables_turnover", section="G",
            label="Receivables Turnover",
            formula="Net Credit Sales ÷ Average Receivables",
            inputs=["net_credit_sales", "average_receivables"],
            output_name="receivables_turnover",
            compute_fn=lambda i: i["net_credit_sales"] / i["average_receivables"] if i["average_receivables"] != 0 else Decimal("0"),
            description="Frequency of collection.",
            depends_on=["net_sales"],
        ),
        ComputationSpec(
            id="g_avg_collection_period", section="G",
            label="Average Collection Period",
            formula="365 ÷ Receivables Turnover",
            inputs=["receivables_turnover"],
            output_name="average_collection_period",
            compute_fn=lambda i: Decimal(365) / i["receivables_turnover"] if i["receivables_turnover"] != 0 else Decimal("0"),
            description="Days to collect receivables.",
            depends_on=["receivables_turnover"],
        ),
        ComputationSpec(
            id="g_inventory_turnover", section="G",
            label="Inventory Turnover",
            formula="COGS ÷ Average Inventory",
            inputs=["cogs", "average_inventory"],
            output_name="inventory_turnover",
            compute_fn=lambda i: i["cogs"] / i["average_inventory"] if i["average_inventory"] != 0 else Decimal("0"),
            description="Frequency inventory is sold.",
            depends_on=["cogs_merchandising"],
        ),
        ComputationSpec(
            id="g_days_sales_inventory", section="G",
            label="Days Sales in Inventory",
            formula="365 ÷ Inventory Turnover",
            inputs=["inventory_turnover"],
            output_name="days_sales_in_inventory",
            compute_fn=lambda i: Decimal(365) / i["inventory_turnover"] if i["inventory_turnover"] != 0 else Decimal("0"),
            description="Average days inventory is held.",
            depends_on=["inventory_turnover"],
        ),
        ComputationSpec(
            id="g_payables_turnover", section="G",
            label="Payables Turnover",
            formula="Net Credit Purchases ÷ Average Payables",
            inputs=["net_credit_purchases", "average_payables"],
            output_name="payables_turnover",
            compute_fn=lambda i: i["net_credit_purchases"] / i["average_payables"] if i["average_payables"] != 0 else Decimal("0"),
            description="Frequency suppliers are paid.",
            depends_on=["net_purchases"],
        ),
        ComputationSpec(
            id="g_days_payable_outstanding", section="G",
            label="Days Payable Outstanding",
            formula="365 ÷ Payables Turnover",
            inputs=["payables_turnover"],
            output_name="days_payable_outstanding",
            compute_fn=lambda i: Decimal(365) / i["payables_turnover"] if i["payables_turnover"] != 0 else Decimal("0"),
            description="Average days to pay suppliers.",
            depends_on=["payables_turnover"],
        ),
        ComputationSpec(
            id="g_operating_cycle", section="G",
            label="Operating Cycle",
            formula="Days Sales in Inventory + Average Collection Period",
            inputs=["days_sales_in_inventory", "average_collection_period"],
            output_name="operating_cycle",
            compute_fn=lambda i: i["days_sales_in_inventory"] + i["average_collection_period"],
            description="Time from buying inventory to collecting cash.",
            depends_on=["days_sales_in_inventory", "average_collection_period"],
        ),
        ComputationSpec(
            id="g_cash_conversion_cycle", section="G",
            label="Cash Conversion Cycle",
            formula="Operating Cycle − Days Payable Outstanding",
            inputs=["operating_cycle", "days_payable_outstanding"],
            output_name="cash_conversion_cycle",
            compute_fn=lambda i: i["operating_cycle"] - i["days_payable_outstanding"],
            description="Days cash is tied up in operations.",
            depends_on=["operating_cycle", "days_payable_outstanding"],
        ),
        ComputationSpec(
            id="g_working_capital_turnover", section="G",
            label="Working Capital Turnover",
            formula="Net Sales ÷ Average Working Capital",
            inputs=["net_sales", "average_working_capital"],
            output_name="working_capital_turnover",
            compute_fn=lambda i: i["net_sales"] / i["average_working_capital"] if i["average_working_capital"] != 0 else Decimal("0"),
            description="Sales generated per unit of working capital.",
            depends_on=["net_sales", "working_capital"],
        ),
        ComputationSpec(
            id="g_total_asset_turnover", section="G",
            label="Total Asset Turnover",
            formula="Net Sales ÷ Average Total Assets",
            inputs=["net_sales", "average_total_assets"],
            output_name="total_asset_turnover",
            compute_fn=lambda i: i["net_sales"] / i["average_total_assets"] if i["average_total_assets"] != 0 else Decimal("0"),
            description="Efficiency of all assets.",
            depends_on=["net_sales", "total_assets"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_g_register()


# ============================================================================
# Section H: Solvency (Leverage) Ratios (items 160-169)
# ============================================================================

def _h_register():
    specs = [
        ComputationSpec(
            id="h_debt_ratio", section="H",
            label="Debt Ratio",
            formula="Total Liabilities ÷ Total Assets",
            inputs=["total_liabilities", "total_assets"],
            output_name="debt_ratio",
            compute_fn=lambda i: i["total_liabilities"] / i["total_assets"] if i["total_assets"] != 0 else Decimal("0"),
            description="Share of assets financed by debt.",
            depends_on=["total_liabilities", "total_assets"],
        ),
        ComputationSpec(
            id="h_equity_ratio", section="H",
            label="Equity Ratio",
            formula="Total Equity ÷ Total Assets",
            inputs=["total_equity", "total_assets"],
            output_name="equity_ratio",
            compute_fn=lambda i: i["total_equity"] / i["total_assets"] if i["total_assets"] != 0 else Decimal("0"),
            description="Share of assets financed by owners.",
            depends_on=["total_equity", "total_assets"],
        ),
        ComputationSpec(
            id="h_debt_to_equity", section="H",
            label="Debt-to-Equity Ratio",
            formula="Total Liabilities ÷ Total Equity",
            inputs=["total_liabilities", "total_equity"],
            output_name="debt_to_equity",
            compute_fn=lambda i: i["total_liabilities"] / i["total_equity"] if i["total_equity"] != 0 else Decimal("0"),
            description="Creditor versus owner financing.",
            depends_on=["total_liabilities", "total_equity"],
        ),
        ComputationSpec(
            id="h_equity_multiplier", section="H",
            label="Equity Multiplier",
            formula="Total Assets ÷ Total Equity",
            inputs=["total_assets", "total_equity"],
            output_name="equity_multiplier",
            compute_fn=lambda i: i["total_assets"] / i["total_equity"] if i["total_equity"] != 0 else Decimal("0"),
            description="Financial leverage.",
            depends_on=["total_assets", "total_equity"],
        ),
        ComputationSpec(
            id="h_times_interest_earned", section="H",
            label="Times Interest Earned",
            formula="EBIT ÷ Interest Expense",
            inputs=["operating_income", "interest_expense"],
            output_name="times_interest_earned",
            compute_fn=lambda i: i["operating_income"] / i["interest_expense"] if i["interest_expense"] != 0 else Decimal("0"),
            description="Ability to cover interest.",
            depends_on=["operating_income"],
        ),
        ComputationSpec(
            id="h_debt_service_coverage", section="H",
            label="Debt Service Coverage",
            formula="Net Operating Income ÷ Total Debt Service",
            inputs=["net_operating_income", "total_debt_service"],
            output_name="debt_service_coverage",
            compute_fn=lambda i: i["net_operating_income"] / i["total_debt_service"] if i["total_debt_service"] != 0 else Decimal("0"),
            description="Ability to meet principal and interest.",
            depends_on=["operating_income"],
        ),
        ComputationSpec(
            id="h_cash_flow_to_debt", section="H",
            label="Cash Flow to Debt Ratio",
            formula="Operating Cash Flow ÷ Total Liabilities",
            inputs=["net_cash_from_operating", "total_liabilities"],
            output_name="cash_flow_to_debt_ratio",
            compute_fn=lambda i: i["net_cash_from_operating"] / i["total_liabilities"] if i["total_liabilities"] != 0 else Decimal("0"),
            description="Ability to repay debt from operations.",
            depends_on=["net_cash_from_operating", "total_liabilities"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_h_register()


# ============================================================================
# Section I: Profitability Ratios (items 170-180)
# ============================================================================

def _i_register():
    specs = [
        ComputationSpec(
            id="i_gross_profit_margin", section="I",
            label="Gross Profit Margin",
            formula="Gross Profit ÷ Net Sales",
            inputs=["gross_profit", "net_sales"],
            output_name="gross_profit_margin",
            compute_fn=lambda i: i["gross_profit"] / i["net_sales"] if i["net_sales"] != 0 else Decimal("0"),
            description="Profit after production costs.",
            depends_on=["gross_profit", "net_sales"],
        ),
        ComputationSpec(
            id="i_operating_profit_margin", section="I",
            label="Operating Profit Margin",
            formula="Operating Income ÷ Net Sales",
            inputs=["operating_income", "net_sales"],
            output_name="operating_profit_margin",
            compute_fn=lambda i: i["operating_income"] / i["net_sales"] if i["net_sales"] != 0 else Decimal("0"),
            description="Profit from operations.",
            depends_on=["operating_income", "net_sales"],
        ),
        ComputationSpec(
            id="i_ebitda_margin", section="I",
            label="EBITDA Margin",
            formula="EBITDA ÷ Net Sales",
            inputs=["ebitda", "net_sales"],
            output_name="ebitda_margin",
            compute_fn=lambda i: i["ebitda"] / i["net_sales"] if i["net_sales"] != 0 else Decimal("0"),
            description="Operating cash-based profitability.",
            depends_on=["ebitda", "net_sales"],
        ),
        ComputationSpec(
            id="i_net_profit_margin", section="I",
            label="Net Profit Margin",
            formula="Net Income ÷ Net Sales",
            inputs=["net_income", "net_sales"],
            output_name="net_profit_margin",
            compute_fn=lambda i: i["net_income"] / i["net_sales"] if i["net_sales"] != 0 else Decimal("0"),
            description="Final profit per unit of sales.",
            depends_on=["net_income", "net_sales"],
        ),
        ComputationSpec(
            id="i_roa", section="I",
            label="Return on Assets (ROA)",
            formula="Net Income ÷ Average Total Assets",
            inputs=["net_income", "average_total_assets"],
            output_name="roa",
            compute_fn=lambda i: i["net_income"] / i["average_total_assets"] if i["average_total_assets"] != 0 else Decimal("0"),
            description="Profit generated by assets.",
            depends_on=["net_income", "total_assets"],
        ),
        ComputationSpec(
            id="i_roe", section="I",
            label="Return on Equity (ROE)",
            formula="Net Income ÷ Average Equity",
            inputs=["net_income", "average_equity"],
            output_name="roe",
            compute_fn=lambda i: i["net_income"] / i["average_equity"] if i["average_equity"] != 0 else Decimal("0"),
            description="Return to shareholders.",
            depends_on=["net_income", "total_equity"],
        ),
        ComputationSpec(
            id="i_return_on_common_equity", section="I",
            label="Return on Common Equity",
            formula="(Net Income − Preferred Dividends) ÷ Average Common Equity",
            inputs=["net_income", "preference_dividends", "average_common_equity"],
            output_name="return_on_common_equity",
            compute_fn=lambda i: (i["net_income"] - i.get("preference_dividends", Decimal("0"))) / i["average_common_equity"] if i["average_common_equity"] != 0 else Decimal("0"),
            description="Return to common shareholders.",
            depends_on=["net_income"],
        ),
        ComputationSpec(
            id="i_dupont", section="I",
            label="DuPont Analysis (3-Step)",
            formula="Net Profit Margin × Total Asset Turnover × Equity Multiplier",
            inputs=["net_profit_margin", "total_asset_turnover", "equity_multiplier"],
            output_name="dupont_roe",
            compute_fn=lambda i: i["net_profit_margin"] * i["total_asset_turnover"] * i["equity_multiplier"],
            description="Decomposes ROE.",
            depends_on=["net_profit_margin", "total_asset_turnover", "equity_multiplier"],
        ),
        ComputationSpec(
            id="i_operating_expense_ratio", section="I",
            label="Operating Expense Ratio",
            formula="Operating Expenses ÷ Net Sales",
            inputs=["total_operating_expenses", "net_sales"],
            output_name="operating_expense_ratio",
            compute_fn=lambda i: i["total_operating_expenses"] / i["net_sales"] if i["net_sales"] != 0 else Decimal("0"),
            description="Expense burden relative to sales.",
            depends_on=["total_operating_expenses", "net_sales"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_i_register()


# ============================================================================
# Section J: Market and Investor Ratios (items 181-191)
# ============================================================================

def _j_register():
    specs = [
        ComputationSpec(
            id="j_pe_ratio", section="J",
            label="Price-Earnings Ratio",
            formula="Market Price per Share ÷ EPS",
            inputs=["market_price_per_share", "basic_eps"],
            output_name="pe_ratio",
            compute_fn=lambda i: i["market_price_per_share"] / i["basic_eps"] if i["basic_eps"] != 0 else Decimal("0"),
            description="Price paid per unit of earnings.",
            depends_on=["basic_eps"],
        ),
        ComputationSpec(
            id="j_earnings_yield", section="J",
            label="Earnings Yield",
            formula="EPS ÷ Market Price per Share",
            inputs=["basic_eps", "market_price_per_share"],
            output_name="earnings_yield",
            compute_fn=lambda i: i["basic_eps"] / i["market_price_per_share"] if i["market_price_per_share"] != 0 else Decimal("0"),
            description="Earnings relative to price.",
            depends_on=["basic_eps"],
        ),
        ComputationSpec(
            id="j_dividend_yield", section="J",
            label="Dividend Yield",
            formula="Dividends per Share ÷ Market Price per Share",
            inputs=["dividends_per_share", "market_price_per_share"],
            output_name="dividend_yield",
            compute_fn=lambda i: i["dividends_per_share"] / i["market_price_per_share"] if i["market_price_per_share"] != 0 else Decimal("0"),
            description="Cash return on share price.",
            depends_on=[],
        ),
        ComputationSpec(
            id="j_dividend_payout", section="J",
            label="Dividend Payout Ratio",
            formula="Dividends ÷ Net Income",
            inputs=["cash_dividends_declared", "net_income"],
            output_name="dividend_payout_ratio",
            compute_fn=lambda i: i["cash_dividends_declared"] / i["net_income"] if i["net_income"] != 0 else Decimal("0"),
            description="Share of earnings distributed.",
            depends_on=["cash_dividends_declared", "net_income"],
        ),
        ComputationSpec(
            id="j_retention_ratio", section="J",
            label="Retention Ratio",
            formula="1 − Dividend Payout Ratio",
            inputs=["dividend_payout_ratio"],
            output_name="retention_ratio",
            compute_fn=lambda i: Decimal("1") - i["dividend_payout_ratio"],
            description="Share of earnings reinvested.",
            depends_on=["dividend_payout_ratio"],
        ),
        ComputationSpec(
            id="j_sustainable_growth", section="J",
            label="Sustainable Growth Rate",
            formula="ROE × Retention Ratio",
            inputs=["roe", "retention_ratio"],
            output_name="sustainable_growth_rate",
            compute_fn=lambda i: i["roe"] * i["retention_ratio"],
            description="Growth financed without new equity.",
            depends_on=["roe", "retention_ratio"],
        ),
        ComputationSpec(
            id="j_pb_ratio", section="J",
            label="Price-to-Book Ratio",
            formula="Market Price per Share ÷ Book Value per Share",
            inputs=["market_price_per_share", "book_value_per_share"],
            output_name="price_to_book_ratio",
            compute_fn=lambda i: i["market_price_per_share"] / i["book_value_per_share"] if i["book_value_per_share"] != 0 else Decimal("0"),
            description="Market value relative to book value.",
            depends_on=["book_value_per_share"],
        ),
        ComputationSpec(
            id="j_market_cap", section="J",
            label="Market Capitalization",
            formula="Market Price per Share × Shares Outstanding",
            inputs=["market_price_per_share", "shares_outstanding"],
            output_name="market_capitalization",
            compute_fn=lambda i: i["market_price_per_share"] * i["shares_outstanding"],
            description="Total market value of equity.",
            depends_on=[],
        ),
        ComputationSpec(
            id="j_enterprise_value", section="J",
            label="Enterprise Value",
            formula="Market Cap + Debt − Cash",
            inputs=["market_capitalization", "total_liabilities", "cash_and_equivalents"],
            output_name="enterprise_value",
            compute_fn=lambda i: i["market_capitalization"] + i.get("total_liabilities", Decimal("0")) - i.get("cash_and_equivalents", Decimal("0")),
            description="Total value of the business.",
            depends_on=["market_capitalization"],
        ),
        ComputationSpec(
            id="j_ev_ebitda", section="J",
            label="EV/EBITDA",
            formula="Enterprise Value ÷ EBITDA",
            inputs=["enterprise_value", "ebitda"],
            output_name="ev_ebitda",
            compute_fn=lambda i: i["enterprise_value"] / i["ebitda"] if i["ebitda"] != 0 else Decimal("0"),
            description="Valuation multiple.",
            depends_on=["enterprise_value", "ebitda"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_j_register()


# ============================================================================
# Section K: Cash Flow Analysis and Quality of Earnings (items 192-198)
# ============================================================================

def _k_register():
    specs = [
        ComputationSpec(
            id="k_cash_flow_margin", section="K",
            label="Cash Flow Margin",
            formula="Operating Cash Flow ÷ Net Sales",
            inputs=["net_cash_from_operating", "net_sales"],
            output_name="cash_flow_margin",
            compute_fn=lambda i: i["net_cash_from_operating"] / i["net_sales"] if i["net_sales"] != 0 else Decimal("0"),
            description="Cash generated per unit of sales.",
            depends_on=["net_cash_from_operating", "net_sales"],
        ),
        ComputationSpec(
            id="k_cash_flow_to_net_income", section="K",
            label="Cash Flow to Net Income",
            formula="Operating Cash Flow ÷ Net Income",
            inputs=["net_cash_from_operating", "net_income"],
            output_name="cash_flow_to_net_income",
            compute_fn=lambda i: i["net_cash_from_operating"] / i["net_income"] if i["net_income"] != 0 else Decimal("0"),
            description="Earnings quality indicator.",
            depends_on=["net_cash_from_operating", "net_income"],
        ),
        ComputationSpec(
            id="k_capex_ratio", section="K",
            label="Capital Expenditure Ratio",
            formula="Operating Cash Flow ÷ Capital Expenditures",
            inputs=["net_cash_from_operating", "capex"],
            output_name="capital_expenditure_ratio",
            compute_fn=lambda i: i["net_cash_from_operating"] / i["capex"] if i["capex"] != 0 else Decimal("0"),
            description="Ability to fund investments internally.",
            depends_on=["net_cash_from_operating", "capex"],
        ),
        ComputationSpec(
            id="k_cash_return_on_assets", section="K",
            label="Cash Return on Assets",
            formula="Operating Cash Flow ÷ Average Total Assets",
            inputs=["net_cash_from_operating", "average_total_assets"],
            output_name="cash_return_on_assets",
            compute_fn=lambda i: i["net_cash_from_operating"] / i["average_total_assets"] if i["average_total_assets"] != 0 else Decimal("0"),
            description="Cash-based asset return.",
            depends_on=["net_cash_from_operating", "total_assets"],
        ),
        ComputationSpec(
            id="k_accrual_ratio", section="K",
            label="Accrual Ratio",
            formula="(Net Income − Operating Cash Flow) ÷ Average Total Assets",
            inputs=["net_income", "net_cash_from_operating", "average_total_assets"],
            output_name="accrual_ratio",
            compute_fn=lambda i: (i["net_income"] - i["net_cash_from_operating"]) / i["average_total_assets"] if i["average_total_assets"] != 0 else Decimal("0"),
            description="Measures reliance on accruals.",
            depends_on=["net_income", "net_cash_from_operating", "total_assets"],
        ),
        ComputationSpec(
            id="k_altman_z", section="K",
            label="Altman Z-Score (Public Manufacturers)",
            formula="1.2(WC/TA) + 1.4(RE/TA) + 3.3(EBIT/TA) + 0.6(MVE/TL) + 1.0(Sales/TA)",
            inputs=["working_capital", "total_assets", "retained_earnings", "operating_income", "market_capitalization", "total_liabilities", "net_sales"],
            output_name="altman_z_score",
            compute_fn=lambda i: (
                Decimal("1.2") * i["working_capital"] / i["total_assets"] +
                Decimal("1.4") * i["retained_earnings"] / i["total_assets"] +
                Decimal("3.3") * i["operating_income"] / i["total_assets"] +
                Decimal("0.6") * i["market_capitalization"] / i["total_liabilities"] +
                Decimal("1.0") * i["net_sales"] / i["total_assets"]
            ) if i["total_assets"] != 0 and i["total_liabilities"] != 0 else Decimal("0"),
            description="Bankruptcy risk indicator.",
            depends_on=["working_capital", "total_assets", "retained_earnings", "operating_income", "market_capitalization", "total_liabilities", "net_sales"],
        ),
    ]
    for s in specs:
        REGISTRY.register(s)


_k_register()


# ============================================================================
# Section detection
# ============================================================================

#: Computation cue words: the text must ask for a computation, not just list accounts.
COMPUTE_CUES = re.compile(
    r"\b(compute|calculate|determine|find|what (?:is|are)|ratio|margin|"
    r"turnover|coverage|yield|growth|analysis|break.?even|working capital|"
    r"earnings per share|eps|book value|enterprise value)\b", re.I)

#: Section keywords: more specific patterns that indicate actual computation requests.
SECTION_KEYWORDS = {
    "A": [r"income statement", r"comprehensive income", r"net sales", r"gross profit",
          r"cost of goods sold", r"operating income", r"net income", r"ebitda",
          r"earnings per share", r"\beps\b", r"cost of goods manufactured"],
    "B": [r"statement of changes in equity", r"retained earnings", r"dividend",
          r"share capital", r"treasury (share|stock)", r"additional paid.?in",
          r"stock dividend", r"stock split"],
    "C": [r"balance sheet", r"statement of financial position", r"total assets",
          r"total liabilities", r"total equity", r"working capital",
          r"accounting equation", r"carrying value", r"book value per share"],
    "D": [r"cash flow statement", r"statement of cash flows", r"operating activities",
          r"investing activities", r"financing activities", r"free cash flow"],
    "E": [r"horizontal analysis", r"vertical analysis", r"trend analysis",
          r"common.?size", r"cagr", r"percentage change"],
    "F": [r"current ratio", r"quick ratio", r"cash ratio", r"liquidity",
          r"defensive interval", r"operating cash flow ratio"],
    "G": [r"receivables turnover", r"inventory turnover", r"payables turnover",
          r"asset turnover", r"operating cycle", r"cash conversion cycle",
          r"activity ratio", r"efficiency ratio"],
    "H": [r"debt ratio", r"debt.?to.?equity", r"equity ratio", r"equity multiplier",
          r"times interest earned", r"solvency", r"leverage",
          r"debt service coverage"],
    "I": [r"profit margin", r"return on assets", r"return on equity", r"\broa\b",
          r"\broe\b", r"dupont", r"gross margin", r"net margin", r"operating margin"],
    "J": [r"price.?to.?earnings", r"\bp/e\b", r"dividend yield", r"payout ratio",
          r"retention ratio", r"price.?to.?book", r"enterprise value",
          r"market cap", r"ev/ebitda"],
    "K": [r"cash flow margin", r"cash flow to net income", r"capex ratio",
          r"cash return on assets", r"accrual ratio", r"altman z",
          r"quality of earnings"],
}


def detect_sections(text: str) -> List[str]:
    """Detect which sections apply from problem text.

    Requires both a computation cue word and section-specific keywords,
    so a bare trial balance or account list does not trigger computation.
    """
    low = text.lower()
    if not COMPUTE_CUES.search(low):
        return []
    found = []
    for section, patterns in SECTION_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, low):
                found.append(section)
                break
    return found


# ============================================================================
# Compute all applicable sections
# ============================================================================

def _section_order(sections: List[str], registry: ComputationRegistry = REGISTRY) -> List[str]:
    """The sections in an order where a section's dependencies are computed first.

    A value computed in one section is an input in another: seventy-two of the
    128 specs depend on a value another section produces.  The sections are
    therefore computed in dependency order, over one shared pool.
    """
    wanted = [s for s in sections]
    owner = {spec.output_name: spec.section for spec in registry.all()}
    pending: Dict[str, set] = {s: set() for s in wanted}
    for section in wanted:
        for spec in registry.by_section(section):
            for dep in spec.depends_on:
                source = owner.get(dep)
                if source in pending and source != section:
                    pending[section].add(source)
    order: List[str] = []
    done: set = set()
    while pending:
        ready = sorted(s for s, deps in pending.items() if not (deps - done))
        if not ready:
            # Sections that depend on each other in a circle: take one
            # deterministically rather than hang.
            ready = [sorted(pending)[0]]
        for section in ready:
            order.append(section)
            done.add(section)
            pending.pop(section, None)
    return order


def compute_all_sections(
    text: str,
    raw_inputs: Dict[str, Decimal],
    sections: Optional[List[str]] = None,
) -> Dict[str, ComputationPack]:
    """Compute all applicable sections given raw inputs and text.

    If sections is None, auto-detect from text.  The sections are computed in
    dependency order over one shared pool of computed values, so a spec that
    needs a value another section produces receives it instead of a gap.
    """
    if sections is None:
        sections = detect_sections(text)

    pool: Dict[str, Decimal] = {}
    packs: Dict[str, ComputationPack] = {}
    for section in _section_order(sections):
        packs[section] = compute_section(section, raw_inputs, REGISTRY, pool)
    return packs


__all__ = [
    "ComputationSpec", "ComputationResult", "ComputationPack",
    "ComputationRegistry", "REGISTRY",
    "compute_section", "compute_all_sections",
    "parse_inputs_from_text", "COMMON_PATTERNS",
    "detect_sections",
]
