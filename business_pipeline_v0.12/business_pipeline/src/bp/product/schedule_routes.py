"""The schedule route: labelled figures in, a named schedule out, no model involved.

A schedule problem states its figures and names its output:

    "Data: Direct materials used 50,000; direct labour 40,000; ... Required: create a cost
     of goods manufactured schedule and an income statement."

There is no transaction to post and no ambiguity to resolve, so asking a model to read it
is both slower and less reliable than reading the labels.  This module does exactly two
things: it maps each label to a figure (a table, one row per label), and it renders the
rows `bp.schedule_math` computed into text.

Detection is deliberately strict — a request word *and* every required figure.  A trial
balance that happens to say "prepare the cash flow statement" must keep going to the
ledger route, and does: it carries Dr/Cr markers and none of the schedule's inputs.

Adding a schedule is one entry in `SCHEMAS` plus one function in `bp.schedule_math`.
"""
import re
from decimal import Decimal, InvalidOperation

_SCHEMAS_SEED = {
    # ------------------------------------------------------------------ COGM
    "cogm": {
        "request": r"cost of goods manufactured|schedule of cost of goods",
        "required": ("direct_materials", "direct_labour", "manufacturing_overhead",
                     "beginning_wip", "ending_wip"),
        "figures": (
            ("direct_materials", r"direct materials?(?:\s+used)?", 1),
            ("direct_labour", r"direct labou?r", 1),
            ("manufacturing_overhead", r"(?:manufacturing|factory|production) overhead", 1),
            ("beginning_wip", r"beginning (?:work in process|wip|work-in-process)", 1),
            ("ending_wip", r"ending (?:work in process|wip|work-in-process)", 1),
            ("beginning_finished_goods",
             r"beginning (?:finished goods|finished goods inventory)", 1),
            ("ending_finished_goods", r"ending (?:finished goods|finished goods inventory)", 1),
            ("sales", r"\bsales\b|\brevenue\b|\bnet sales\b", 1),
            ("selling_and_admin",
             r"selling (?:and|&) admin\w*|selling,? general|sg&a|operating expenses", 1),
        ),
    },
    # ---------------------------------------------------- cash flows, indirect
    "cash_flow_indirect": {
        "request": r"cash ?flows?|statement of cash",
        "require_all": ("net_income",),
        "require_any": ("depreciation", "accounts_receivable", "inventory",
                        "accounts_payable", "capital_expenditure", "proceeds_from_sale"),
        "figures": (
            ("net_income", r"net income", 1),
            ("depreciation", r"depreciation(?!\s+expense)", 1),
            ("gain_on_sale", r"gain on (?:the )?(?:sale|disposal)", 1),
            ("loss_on_sale", r"loss on (?:the )?(?:sale|disposal)", 1),
            ("accounts_receivable", r"increase in (?:accounts? receivables?|receivables|a/?r)\b", 1),
            ("accounts_receivable", r"decrease in (?:accounts? receivables?|receivables|a/?r)\b", -1),
            ("inventory", r"increase in (?:inventor(?:y|ies)|stock)\b", 1),
            ("inventory", r"decrease in (?:inventor(?:y|ies)|stock)\b", -1),
            ("prepaid_expenses", r"increase in prepaid\w*", 1),
            ("prepaid_expenses", r"decrease in prepaid\w*", -1),
            ("accounts_payable", r"increase in (?:accounts? payables?|payables|a/?p)\b", 1),
            ("accounts_payable", r"decrease in (?:accounts? payables?|payables|a/?p)\b", -1),
            ("accrued_liabilities", r"increase in (?:accrued|accruals?)\b", 1),
            ("accrued_liabilities", r"decrease in (?:accrued|accruals?)\b", -1),
            ("capital_expenditure",
             r"purchase(?:s)? of (?:equipment|property|plant|ppe|machinery|land|buildings?|"
             r"vehicles?|fixed assets)", 1),
            ("proceeds_from_sale", r"proceeds from (?:the )?(?:sale|disposal)", 1),
            ("shares_issued",
             r"(?:issue|issued|issuance)(?:\s+of)?\s+(?:common\s+|ordinary\s+|share\s+)?(?:stock|shares)", 1),
            ("dividends_paid", r"dividends?[^;\n]{0,30}?(?:paid|declared)", 1),
            ("beginning_cash", r"beginning cash|cash at (?:the )?beginning|opening cash", 1),
        ),
    },
    # ------------------------------------------------ statement of equity
    "equity_statement": {
        "request": r"(?:changes?\s+in|statement\s+of)\s+(?:[a-z']+\s+){0,2}equity|"
                   r"statement of (?:owners?'?|stockholders?'?|shareholders?'?)\s*equity",
        "require_all": ("net_income",),
        "require_any": ("beginning_common_stock", "beginning_retained_earnings"),
        "figures": (
            ("beginning_common_stock",
             r"beginning (?:common|ordinary|share|preferred) (?:stock|capital)", 1),
            ("beginning_retained_earnings", r"beginning retained earnings", 1),
            ("common_stock_issued",
             r"(?:common|ordinary|share|preferred) (?:stock|capital) (?:issued|issue)", 1),
            ("net_income", r"net income", 1),
            ("dividends", r"dividends?", 1),
            ("other_comprehensive_income", r"other comprehensive income", 1),
        ),
    },
    # --------------------------------------------------- bank reconciliation
    "bank_reconciliation": {
        "request": r"bank reconciliation|reconcil\w* (?:the )?(?:bank|cash)",
        "require_all": ("bank_statement_balance", "book_cash_balance"),
        "figures": (
            ("bank_statement_balance",
             r"bank statement balance|balance per bank|bank balance|balance per the bank", 1),
            ("book_cash_balance",
             r"book cash balance|balance per books?|book balance|cash balance per books?|"
             r"balance per the books?", 1),
            ("deposits_in_transit", r"deposits? in transit", 1),
            ("outstanding_checks", r"outstanding checks?", 1),
            ("bank_service_charge", r"(?:bank )?service charge", 1),
            ("nsf_check", r"nsf(?:\s+customer)?\s+check|nsf", 1),
            ("note_collected", r"note collected(?:\s+by (?:the )?bank)?", 1),
            ("interest_earned", r"interest earned", 1),
            ("book_error", r"book error|error in (?:the )?(?:books|cash)", 1),
        ),
    },
}

#: A trial balance marks its side on the line: "Cash 10,000 Dr".  Such a text is never a
#: schedule, whatever it asks for at the end.
_SCHEMAS_SEED["asset_disposal"] = {
    "request": r"depreciation .* sold|sold .* depreciation|disposal|gain.?loss on (?:sale|disposal)|"
               r"depreciation.*residual|residual.*depreciation",
    "require_all": ("cost", "residual_value", "useful_life", "years_elapsed", "sale_price"),
    "figures": (
        ("cost", r"equipment cost|cost of (?:the )?(?:asset|equipment)|asset cost|\bcost\b", 1),
        ("residual_value", r"residual value|salvage value", 1),
        ("useful_life", r"useful life", 1),
        ("years_elapsed", r"year\s*(\d+)", 1),
        ("sale_price",
         r"sold .* for|proceeds from (?:the )?(?:sale|disposal)|sale price|selling price", 1),
    ),
}

_SCHEMAS_SEED["ratio_computation"] = {
    "request": r"current ratio|quick ratio|debt ratio|gross margin|net margin|return on assets|"
               r"return on equity|asset turnover|receivables turnover|days sales outstanding",
    "require_all": ("current_assets", "current_liabilities", "total_assets", "total_liabilities",
                     "equity", "sales", "net_income", "accounts_receivable"),
    "figures": (
        ("current_assets", r"current assets", 1),
        ("inventory", r"inventory", 1),
        ("current_liabilities", r"current liabilities", 1),
        ("total_assets", r"total assets", 1),
        ("total_liabilities", r"total liabilities", 1),
        ("equity", r"\bequity\b", 1),
        ("sales", r"\bsales\b", 1),
        ("cogs", r"cogs|cost of goods sold", 1),
        ("net_income", r"net income", 1),
        ("accounts_receivable", r"accounts receivable", 1),
    ),
}

from . import tier1_tables as _t1
SCHEMAS = _t1.get_schemas() or _SCHEMAS_SEED

TRIAL_BALANCE_MARK = re.compile(r"\d[\d,]*(?:\.\d+)?\s*(?:Dr|Cr)\.?(?=\s|$|[;,.])", re.I)

NUMBER = r"(\d[\d,]*(?:\.\d+)?)"


def _decimal(text):
    try:
        return Decimal(str(text).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _figure(text, patterns):
    """The amount written after any of these labels, times its sign, or None.

    A label and its amount are not always adjacent.  The bridge between them is at most a few
    words of ordinary text, so a label with no amount of its own cannot borrow the next line's
    number.

    A pattern may carry its own capture group when the figure is part of the label rather than
    written after it (for example \"Year 3\").  In that case the captured group is used.
    """
    for pattern, sign in patterns:
        if "(" in pattern:
            match = re.search(pattern, text, re.I)
            if match and match.lastindex:
                value = _decimal(match.group(match.lastindex))
                if value is not None:
                    return sign * value
        match = re.search(r"(?:" + pattern + r")[^0-9;\n]{0,32}" + NUMBER, text, re.I)
        if match:
            value = _decimal(match.group(1))
            if value is not None:
                return sign * value
    return None


def _has(text, pattern):
    return re.search(pattern, text, re.I) is not None


def detect(text):
    """The schedule kind this instruction declares, or None."""
    text = str(text or "")
    if re.search(r"\btrial balance\b", text, re.I):
        # A trial balance is a ledger problem: it has accounts and sides, not labelled
        # schedules.  One exception is never reached here (bank reconciliations do not say
        # "trial balance"), but the guard keeps the rule in one place.
        return None
    for kind, schema in SCHEMAS.items():
        if not _has(text, schema["request"]):
            continue
        if TRIAL_BALANCE_MARK.search(text):
            # A trial balance goes to the ledger route: it has side markers and no schedule.
            continue
        figures = read_figures(kind, text)
        if not _enough(schema, figures):
            continue
        return kind
    return None


def _enough(schema, figures):
    for key in schema.get("required", ()):
        if figures.get(key) is None:
            return False
    for key in schema.get("require_all", ()):
        if figures.get(key) is None:
            return False
    wanted = schema.get("require_any")
    if wanted and all(figures.get(key) is None for key in wanted):
        return False
    return True


def read_figures(kind, text):
    """Every figure the schema for `kind` names, in the order the labels appear.

    A key is present only when the text states it.  An optional figure the problem never mentions
    is *absent*, not zero and not None: the arithmetic supplies the zero, and the tier refuses to
    demand a figure the student did not give.
    """
    schema = SCHEMAS.get(kind) or {}
    text = str(text or "")
    figures = {}
    for key, pattern, sign in schema.get("figures", ()):
        if figures.get(key) is not None:
            continue
        value = _figure(text, ((pattern, sign),))
        if value is not None:
            figures[key] = value
    return figures


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def _amount(value, negative=False):
    if value is None:
        return ""
    text = "{:,.2f}".format(abs(value))
    return "(" + text + ")" if (value < 0 or negative) else text


def _render_rows(rows, label_width=52, amount_width=16):
    lines = []
    for row in rows:
        if row.get("amount") is None and not row.get("heading"):
            lines.append("")
            continue
        if row.get("heading"):
            lines.append(row["label"])
            continue
        if row.get("rule"):
            lines.append("-" * (label_width + amount_width))
        indent = "  " * int(row.get("indent") or 0)
        label = indent + str(row.get("label") or "")
        lines.append("{:<{w}}{:>{a}}".format(label[:label_width], _amount(row.get("amount")),
                                             w=label_width, a=amount_width))
    return lines


def _render_columns(rows, columns, label_width=40, column_width=18):
    header = "{:<{w}}".format("", w=label_width)
    for name in columns:
        header += "{:>{c}}".format(name[:column_width - 2], c=column_width)
    lines = [header, "-" * (label_width + column_width * len(columns))]
    for row in rows:
        if row.get("rule"):
            lines.append("-" * (label_width + column_width * len(columns)))
        line = "{:<{w}}".format(str(row.get("label") or "")[:label_width], w=label_width)
        for value in row.get("columns") or []:
            line += "{:>{c}}".format(_amount(value), c=column_width)
        lines.append(line)
    return lines


def _render_entries(entries):
    if not entries:
        return []
    lines = ["", "ADJUSTING JOURNAL ENTRIES"]
    for entry in entries:
        lines.append("")
        lines.append("  " + str(entry.get("description") or "entry"))
        debit_account, debit_amount = entry["debit"]
        credit_account, credit_amount = entry["credit"]
        lines.append("    Dr {:<44}{:>14}".format(debit_account, _amount(debit_amount)))
        lines.append("       Cr {:<41}{:>14}".format(credit_account, _amount(credit_amount)))
    return lines


def render(result):
    """Render a computed schedule into the sections the record carries."""
    sections = []
    for section in result.get("sections") or []:
        rows = section.get("rows") or []
        if section.get("columns"):
            body = _render_columns(rows, section["columns"])
        else:
            body = _render_rows(rows)
        sections.append({"title": section["title"],
                         "text": "\n".join([section["title"], ""] + body)})
    entries = _render_entries(result.get("entries") or [])
    if entries:
        sections.append({"title": "ADJUSTING JOURNAL ENTRIES", "text": "\n".join(entries)})
    return sections


def run(kind, text, compute):
    """Read the figures, compute, render.  Raises `ScheduleError` when a figure is missing."""
    figures = read_figures(kind, text)
    schema = SCHEMAS.get(kind) or {}
    for key in schema.get("required", ()) + schema.get("require_all", ()):
        if figures.get(key) is None:
            raise ScheduleError("the schedule needs '" + key.replace("_", " ") +
                                "', and the problem does not state it")
    result = compute(kind, figures)
    sections = render(result)
    return {"kind": kind, "figures": figures,
            "computed": result.get("figures") or {},
            "result": result, "sections": sections,
            "checks": result.get("checks") or [],
            "title": (result.get("sections") or [{}])[0].get("title", kind)}


class ScheduleError(ValueError):
    """A stated figure is missing or unusable."""
