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
- "adjustments": emit an adjustment when you can identify the PARAMETERS for a registered function (below). You may derive parameters from the text (e.g. months_expired from coverage dates, receivables from billed/collected/written-off). The engine computes the amount; you never compute it. If the text states a finished figure ("depreciation 12,000"), book it as an entry, not an adjustment. If the text states an income tax rate, you must emit a tax_on_pretax adjustment.
- "policy": only what the text states (tax rate, depreciation convention, inventory system). Omit a key rather than guess it.
- You may propose derived figures (sums, prorations, accruals, tax, month counts) as long as they follow from the text. The engine computes and verifies them; a proposal that does not tie is refused. Declare the derived figure and the inputs it came from in "assumptions".
- Amounts should be traceable to the text or to a clear derivation from stated figures. Nothing is rejected for being derived; the gates decide.
- Do not produce totals, balances or statements.
- "date" is YYYY-MM-DD. If the text states no date, use the accounting period's end date and say so in "assumptions".
- "source_text" is the exact sentence or clause the entry or adjustment came from.
- "kind" is "original" for a transaction the text states, "adjustment" for an adjusting entry the text states explicitly. Do not infer adjustments.
- List every assumption in "assumptions"; an empty list is the common answer.

REGISTERED ADJUSTMENT FUNCTIONS (use only these, by exact name):
- straight_line_depreciation: params {cost, residual (default 0), life_years, convention in {full_year, half_year, pro_rata}, months_in_service (required only for pro_rata)}. Amount = (cost - residual) / life_years, prorated by the convention.
- reducing_balance_depreciation: params {cost, residual (default 0), life_years, rate (optional; defaults to 2/life_years), accumulated (default 0), convention in {full_year, half_year, pro_rata}, months_in_service (required only for pro_rata)}. Amount = (cost - accumulated - residual) * rate, prorated by the convention. Never goes below zero.
- units_of_production_depreciation: params {cost, residual (default 0), units_this_period, total_estimated_units}. Amount = (cost - residual) * units_this_period / total_estimated_units.
- prepaid_amortization: params {payment, months_expired, total_months (default 12)} OR {payment, coverage_start, coverage_end, total_months (default 12)}. Amount = payment * months_expired / total_months. months_expired is the number of months of the policy that have expired by the period end; give it directly only if the text states it, otherwise give coverage_start and coverage_end (ISO dates) and it is derived.
- periodic_cogs: params {beginning_inventory (default 0), purchases, ending_inventory}. Amount = beginning + purchases - ending.
- supplies_used: params {beginning_inventory (default 0), purchases, ending_inventory}. Amount = beginning + purchases - ending.
- accrued_expense: params {amount}. Amount = the stated amount (e.g. wages earned but unpaid).
- warranty_expense: params {sales, rate}. Amount = sales * rate. rate is the percentage number the text states (e.g. 4 for 4%).
- depreciation_sum_of_years_digits: params {cost, salvage, life_years, year}. Sum-of-years-digits depreciation.
- allowance_writeoff: params {amount}. Write off a receivable against the allowance.
- allowance_recovery: params {amount}. Recover a previously written-off receivable.
- accrued_revenue: params {amount}. Revenue earned but not yet billed.
- warranty_claim_paid: params {amount}. Cash paid for warranty claims.
- warranty_liability_trueup: params {expected_expense, actual_claims, prior_balance}. True up warranty liability.
- interest_accrual_days: use interest_accrual with months converted to days/30.
- interest_accrual: params {principal, rate, months (default 12)}. Amount = principal * rate * months / 12. rate is the percentage number the text states (e.g. 8 for 8%).
- lease_pv: params {payment, rate, periods, due ("beginning" or "end")}. PV of lease payments.
- deferred_tax: params {temporary_difference, rate}. Deferred tax from temporary differences.
- valuation_allowance: params {dta, probability}. Valuation allowance on deferred tax assets.
- goodwill: params {consideration, nci, fair_value_net_assets}. Goodwill computation.
- impairment_loss: params {carrying_amount, recoverable_amount (or fair_value)}. Impairment loss.
- pension_expense: params {service_cost, interest_cost, expected_return, prior_service_cost_amort, net_actuarial_loss_amort}. Net pension expense.
- equity_method_income: params {share_of_net_income, basis_difference_amortization}. Equity method income.
- segment_threshold: params {total_revenue}. 10% threshold for segment reporting.
- stock_based_comp: params {fair_value, shares, vesting_years, forfeiture_rate}. Annual stock-based comp expense.
- diluted_eps_incremental: params {conversion_shares}. Incremental shares from convertibles.
- revenue_allocation: params {transaction_price, ssp, total_ssp}. Allocate revenue by SSP.
- unrealized_profit_elimination: params {intercompany_sale_amount, gross_margin, remaining_inventory_fraction}. Unrealized profit.
- remeasurement_gain_loss: params {net_assets_current_rate, net_assets_historical_rate}. FX remeasurement.
- eps_weighted_shares: params {periods: [{shares, months}], split_factor}. Weighted average shares.
- method_call: params {method_id, ...method inputs}. Delegates to the computation library (methods.py, 142 methods). The engine computes; you declare which method and its inputs. Use this ONLY for computations not covered by the functions above. Do NOT use method_call for depreciation or tax — use straight_line_depreciation and tax_on_pretax. method_id must be a valid id from the catalogue below; invalid ids are skipped.
- bad_debt_expense: params {billed, collected, written_off, rate, opening_allowance (default 0)}. Amount = (billed - collected - written_off) * rate - (opening_allowance - written_off), clamped at zero. rate is the percentage number the text states (e.g. 3 for 3%). Never compute receivables or the allowance balance; supply the stated components. (receivables and prior_allowance may be given instead when the text states them directly.)
- tax_on_pretax: params {} (the rate comes from policy.tax_rate). Amount = pre-tax income * rate; a loss earns no tax. policy.tax_rate is the rate as a decimal (e.g. 0.21 for 21%); the text's percentage (e.g. 21%) is converted. If the text states an income tax rate, you MUST emit a tax_on_pretax adjustment.
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


from .product.statements import StatementError as _StatementError

class ExtractionError(_StatementError):
    """The model's answer was off-contract, ungrounded, or could not be posted."""


def system_prompt():
    return SYSTEM


def user_prompt(text, chart, period=None, examples=None):
    """The chart is given as data so the model can only choose existing codes."""
    codes = [{"code": r["code"], "name": r["name"], "type": r["type"], "line": r["line"]} for r in chart]
    head = "CHART OF ACCOUNTS\n" + json.dumps(codes, indent=1)
    if period:
        head += ("\n\nACCOUNTING PERIOD\n" + json.dumps(period) +
                 "\nIf the text states no date for a transaction, use the period end date and say so in assumptions.")
    # computation library catalogue (methods.py) — the model may reference any method_id
    try:
        from . import methods as _m
        ids = [m["method_id"] for m in _m.list_methods()]
        head += ("\n\nCOMPUTATION LIBRARY (methods.py) — " + str(len(ids)) + " methods. You may reference any "
                 "method_id via the method_call adjustment function; the engine computes it deterministically. "
                 "Method IDs: " + ", ".join(ids))
    except Exception:
        pass
    # few-shot examples from the learning library
    if examples:
        head += "\n\nEXAMPLES (previously solved problems — follow this pattern):\n"
        for i, ex in enumerate(examples, 1):
            head += f"\n--- Example {i} ---\nPROBLEM: {ex.get('text', '')[:500]}\n"
            if ex.get("entries"):
                head += "ENTRIES: " + json.dumps(ex["entries"])[:800] + "\n"
            if ex.get("adjustments"):
                head += "ADJUSTMENTS: " + json.dumps(ex["adjustments"])[:800] + "\n"
    # account classification table (from corpus)
    try:
        import os as _os
        cls_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                 "product", "data", "account_classification.json")
        cls = json.load(open(cls_path, encoding="utf-8"))
        # build a compact type->accounts map
        by_type = {}
        for name, info in cls.get("classification", {}).items():
            t = info.get("type", "")
            by_type.setdefault(t, []).append(name)
        lines = []
        for t in sorted(by_type):
            lines.append(f"{t}: {', '.join(sorted(by_type[t])[:15])}")
        head += "\n\nACCOUNT CLASSIFICATION (from accounting textbooks):\n" + "\n".join(lines)
    except Exception:
        pass
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
    "supplies_used": {"beginning_inventory": 0},
    "interest_accrual": {"months": 12},
    "warranty_expense": {},
    "depreciation_sum_of_years_digits": {},
    "allowance_writeoff": {},
    "allowance_recovery": {},
    "accrued_revenue": {},
    "warranty_claim_paid": {},
    "warranty_liability_trueup": {},
    "lease_pv": {},
    "deferred_tax": {},
    "valuation_allowance": {},
    "goodwill": {},
    "impairment_loss": {},
    "pension_expense": {},
    "equity_method_income": {},
    "segment_threshold": {},
    "stock_based_comp": {},
    "diluted_eps_incremental": {},
    "revenue_allocation": {},
    "unrealized_profit_elimination": {},
    "remeasurement_gain_loss": {},
    "eps_weighted_shares": {},
    "tiered_rebate": {},
    "loyalty_point_allocation": {},
    "financing_arrangement": {},
    "standard_cost_variance": {},
    "lifo_liquidation": {},
    "aro_capitalization": {},
    "weighted_avg_borrowing_rate": {},
    "grant_clawback": {},
    "inflate_then_discount": {},
    "eir_solving": {},
    "off_market_leaseback": {},
    "terp_bonus_factor": {},
    "method_call": {},
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


#: Words that say two numbers in a clause are parts of one whole.
_PARTITION = re.compile(r"\b(of which|the balance|balance of|remaining|the rest|less|net of|"
                         r"split into|part of|deducted from|after deducting)\b", re.I)


def _clauses(text):
    """The clauses of the text: each sentence, and each comma-part inside it."""
    out = []
    for sentence in re.split(r"[.;\n]", str(text or "")):
        sentence = sentence.strip()
        if not sentence:
            continue
        out.append(sentence)
        for part in re.split(r",|;", sentence):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def _partition_grounded(amount, text, source_text):
    """True when the text proves the amount by partition: a stated whole less a stated part.

    The proof is arithmetic the code does, not a figure the model asserts.  Both operands
    must be stated in the same clause, the clause must say the two numbers are parts of
    one whole ("of which 55,000 was cash"), and the subtraction must come to the amount
    exactly.  Nothing else is accepted: a sum of two unrelated figures, or a difference
    the text never frames as a partition, stays ungrounded.
    """
    try:
        target = D(str(amount))
    except (InvalidOperation, ValueError):
        return False
    wanted = str(source_text or "").strip()
    for clause in _clauses(text):
        if wanted and wanted not in clause:
            continue
        if not _PARTITION.search(clause):
            continue
        numbers = []
        for match in _NUMBER.finditer(clause):
            try:
                numbers.append(D(match.group(0).replace(",", "")))
            except InvalidOperation:
                continue
        for whole in numbers:
            for part in numbers:
                if whole == part:
                    continue
                if whole - part == target:
                    return True
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
            # Grounding lifted: the model may propose derived figures. The gates verify.
            # Semantic account check: verify chart account types match the
            # classification table from the corpus (catches chart misconfigurations).
            try:
                import os as _os
                cls_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))),
                                         "product", "data", "account_classification.json")
                cls = json.load(open(cls_path, encoding="utf-8"))
                cmap = cls.get("code_map", {})
                # build code -> expected type from classification
                code_type = {}
                for name, info in cls.get("classification", {}).items():
                    cm = cmap.get(name, {})
                    code = cm.get("code")
                    if code and code not in code_type:
                        code_type[code] = info.get("type")
                # check this account
                expected = code_type.get(acct)
                if expected is not None and acct_type is not None and expected != acct_type:
                    errs.append(f"{ltag}: account {acct} is typed '{acct_type}' in the chart "
                                f"but classified as '{expected}' in the corpus")
            except Exception:
                pass
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
        # Grounding lifted: the model may propose derived figures. The gates verify.
        # prepaid_amortization: months_expired may be derived from stated coverage dates
        if a.get("function") == "prepaid_amortization" and isinstance(params, dict):
            if params.get("months_expired") is None and not (params.get("coverage_start") and params.get("coverage_end")):
                errs.append(f"{tag}: prepaid_amortization needs months_expired, or coverage_start and coverage_end")
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
    # few-shot examples from the learning library
    examples = None
    try:
        from .product import statement_library as _slib
        examples = _slib.few_shot(text, n=2)
    except Exception:
        examples = None
    raw, record = models.call("builder", "statement_extract", CONTRACT_VERSION,
                              system_prompt(), user_prompt(text, chart, period, examples=examples), consent)
    payload = parse(raw)
    errs = validate(payload, text, chart, places, default_date=default_date, period=period)
    if errs:
        raise ExtractionError("; ".join(errs))
    # If the text states a tax rate but the model omitted the tax adjustment, add it:
    # the rate is already in policy and the amount is derived by the adjustment stage.
    policy = to_policy(payload) or {}
    adjustments = to_adjustments(payload)
    has_tax = any(isinstance(a, dict) and a.get("function") == "tax_on_pretax" for a in adjustments)
    text_has_tax = bool(__import__("re").search(r"tax\s*rate|income\s*tax", str(text or ""), __import__("re").I))
    if (not has_tax) and policy.get("tax_rate") is not None and text_has_tax:
        tax_expense_code = None
        tax_payable_code = None
        for row in (chart or []):
            name = str(row.get("name", "")).lower()
            if row.get("type") == "expense" and "tax" in name and tax_expense_code is None:
                tax_expense_code = row.get("code")
            if row.get("type") == "liability" and "tax" in name and tax_payable_code is None:
                tax_payable_code = row.get("code")
        if tax_expense_code and tax_payable_code and tax_expense_code != tax_payable_code:
            adjustments.append({"id": "tax_on_pretax_0", "function": "tax_on_pretax",
                               "debit": tax_expense_code, "credit": tax_payable_code,
                               "params": {}, "date": (period or {}).get("end") or default_date,
                               "source_text": "Income tax rate: " + str(payload.get("policy", {}).get("tax_rate"))})
    return {"entries": to_entries(payload, default_date=default_date),
            "adjustments": adjustments,
            "policy": policy,
            "record": record,
            "unplaceable": list(payload.get("unplaceable") or [])}