"""The statement verifier: code, not opinion (product layer).

Every reading — from the deterministic parser or from a model — passes through here before the core
is called.  Six checks, each of which can fail:

1. **provenance** — every chart account and every figure carries the exact text it came from, and
   that text is an exact substring of the instruction (the same rule `verify.verify_reading` uses,
   so the two verifiers cannot disagree);
2. **filing** — every figure normalises through `verify.normalise_number`, and the case currency is
   the one this product uses;
3. **chart** — valid types, a statement line on every account, no duplicate code or name, exactly one
   retained-earnings role, and a section on every asset and liability (the section decides the
   cash-flow classification, so an empty one is a silent misclassification);
4. **balance** — every journal entry balances: debits equal credits.  That is a check on a declared
   reading, not a figure anyone reports;
5. **articulation** — when the core result is supplied: every applicable core check passed, and the
   closing equity in the statement of changes in equity equals the balance sheet's equity;
6. **completeness** — when the core refused, the reading says what is missing.

Nothing here computes a business result; the totals come from the core.
"""

from decimal import Decimal, InvalidOperation

from . import verify

FORMAT = "bp-statements-verify/1"
PROBLEM_TYPES = ("trial_balance", "transactions", "adjustments", "incomplete_records")
TYPES = ("asset", "liability", "equity", "income", "expense", "oci")
CURRENCY = "USD"

#: The core's own checks that make a statement set articulate.  A failure in any of them is a
#: refusal, never a silent correction.
ARTICULATION = ("trial_balance_debits_equal_credits", "assets_equal_liabilities_plus_equity",
                "net_income_agrees_across_routes", "cash_flow_agrees_across_routes",
                "statement_lines_foot_to_totals", "journal_hash_chain_intact")


def _amount(text):
    try:
        return Decimal(str(text).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def verify_reading(reading, instruction, currency=None, result=None, refusal=None):
    """Return the problems with one reading; empty means it is approved."""
    problems = []

    def problem(check, detail):
        problems.append({"check": check, "detail": detail})

    if not isinstance(reading, dict):
        return [{"check": "shape", "detail": "a reading must be an object"}]
    source = str(instruction or "")

    if reading.get("problem_type") not in PROBLEM_TYPES:
        problem("type", "problem_type must be one of " + ", ".join(PROBLEM_TYPES))

    wanted = str(reading.get("currency") or currency or CURRENCY).upper()
    if wanted != CURRENCY:
        problem("currency", "this product answers in " + CURRENCY + " only; the reading declares " + wanted)

    for account in reading.get("chart") or []:
        if not isinstance(account, dict) or account.get("synthesised"):
            continue
        quote = str(account.get("quote") or "")
        if not quote:
            problem("provenance", "the account '" + str(account.get("name")) + "' carries no quote")
        elif quote not in source:
            problem("provenance", "the quote for '" + str(account.get("name")) + "' is not in the "
                                  "instruction: " + quote[:60])

    for figure in reading.get("figures") or []:
        if not isinstance(figure, dict) or figure.get("derived"):
            continue
        quote = str(figure.get("quote") or "")
        if not quote:
            problem("provenance", "a figure (" + str(figure.get("written")) + ") carries no quote")
        elif quote not in source:
            problem("provenance", "the figure quote is not in the instruction: " + quote[:60])
        try:
            verify.normalise_number(figure.get("written"), figure.get("kind") or "amount", wanted)
        except verify.VerifyError as error:
            problem("filing", "a figure does not normalise: " + str(error))

    codes, names, retained = set(), set(), 0
    for account in reading.get("chart") or []:
        if not isinstance(account, dict):
            problem("chart", "a chart entry is not an object")
            continue
        code, name = str(account.get("code") or ""), str(account.get("name") or "")
        if account.get("type") not in TYPES:
            problem("chart", code + ": type must be one of " + ", ".join(TYPES))
        if not str(account.get("line") or "").strip():
            problem("chart", code + ": every account needs a statement line")
        if not code:
            problem("chart", "an account has no code")
        if code in codes:
            problem("chart", "duplicate account code " + code)
        if name and name.lower() in names:
            problem("chart", "duplicate account name " + name)
        codes.add(code)
        names.add(name.lower())
        if account.get("type") == "equity" and account.get("role") == "retained_earnings":
            retained += 1
        if account.get("type") in ("asset", "liability") and not account.get("section"):
            problem("chart", code + " (" + name + "): every asset and liability needs a section, "
                                    "because the section decides the cash-flow classification")
    if retained != 1:
        problem("chart", "the chart needs exactly one retained-earnings account, found " + str(retained))

    for entry in reading.get("journal") or []:
        if not isinstance(entry, dict) or entry.get("aggregate"):
            continue
        debits, credits = Decimal(0), Decimal(0)
        for line in entry.get("lines") or []:
            amount = _amount(line.get("debit") if "debit" in line else line.get("credit"))
            if amount is None:
                problem("balance", "an entry line carries no readable amount")
                continue
            if "debit" in line:
                debits += amount
            else:
                credits += amount
        if debits != credits:
            problem("balance", "the entry '" + str(entry.get("description")) + "' does not balance: "
                               "debits " + str(debits) + ", credits " + str(credits))

    if result is not None:
        checks = {name: ok for name, ok, _detail in (result.get("_checks") or [])}
        for name in ARTICULATION:
            if name in checks and not checks[name]:
                problem("articulation", "the core's own check failed: " + name)
        appendix = result.get("_appendix") or {}
        closing = (appendix.get("equity_statement") or {}).get("total_closing")
        equity = (appendix.get("statements") or {}).get("equity_with_current_earnings")
        if closing is not None and equity is not None and str(closing) != str(equity):
            problem("articulation", "the statement of changes in equity closes at " + str(closing)
                                    + " but the balance sheet reports " + str(equity))

    if refusal is not None and not (reading.get("missing") or []):
        problem("completeness", "the accounts do not build, so the reading must say what is missing")
    return problems

