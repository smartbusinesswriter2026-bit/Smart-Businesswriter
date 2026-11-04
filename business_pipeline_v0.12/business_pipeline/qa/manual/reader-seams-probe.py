"""A measurement of the reader's seams: the state before the fix and the state after it.

Seven questions, each answered by running the real reader against the real text:

1. does a narrative that opens "on 1 January 2025" get a one-day period?
2. does a fiscal year whose start and end are both stated read as two periods?
3. does a transaction date ("On 2 January ... 30,000") read as a comparative?
4. do Salaries and Rent collide on one statement line?
5. does a stated sales figure survive the prose around it?
6. does a partition the text states ("of which 55,000 was cash") survive grounding?
7. does the chart that carries the deterministic path cover the codes its own detectors post to?

Run:  python qa/manual/reader-seams-probe.py
"""
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp import methods  # noqa: E402
from bp import statement_chart  # noqa: E402
from bp import statement_detect as sd  # noqa: E402
from bp import statement_extract as se  # noqa: E402
from bp.product import statements  # noqa: E402

#: The chart the deterministic transaction path carries.  It used to be written out
#: here, and it drifted: the detectors post to codes this list did not carry, and
#: the seam read as open when the tile had already moved to one chart.
DETERMINISTIC_CHART_CODES = {a["code"] for a in statement_chart.CHART}


def attach():
    """The frozen core, attached exactly as `bp.server` attaches it."""
    statements.attach_core(
        solve=lambda spec: methods.LIBRARY["management_accounts"].impl({"spec": spec}),
        diagnose=lambda rows, places: methods.LIBRARY["trial_balance_check"].impl(
            {"journal": None, "trial_balance": rows, "places": places}),
        ratio_analysis=lambda figures: methods.LIBRARY["ratio_analysis"].impl(figures),
        dupont=lambda inputs: methods.LIBRARY["dupont_analysis"].impl(inputs))


def line(label, value):
    print("  " + label.ljust(50) + str(value))


def show_problem(text, label):
    print()
    print("=" * 100)
    print(label)
    print("-" * 100)
    print(text.strip()[:400])
    print("-" * 100)


def seam_1_period_collapses():
    text = ("On 1 January 2025 the owner invested 50,000 cash in the business. "
            "The business bought a delivery van for 30,000 cash on 2 January 2025.")
    show_problem(text, "SEAM 1 — a narrative that opens with a transaction date")
    period, source, quote = statements.period_of(text)
    line("period", period)
    line("source", source)
    line("is a one-day period", period["start"] == period["end"])


def seam_2_one_year_reads_as_two_periods():
    text = ("The following trial balance was extracted at 31 December 2025 for the year "
            "1 January 2025 to 31 December 2025.\nCash 5,000\nCapital 5,000")
    show_problem(text, "SEAM 2 — one fiscal year, both ends stated")
    line("periods_in", sorted(statements.periods_in(text)))
    line("counted as two periods", len(statements.periods_in(text)) > 1)


def seam_3_transaction_date_reads_as_comparative():
    text = ("On 2 January 2025 the business purchased a delivery van for 30,000 cash.\n"
            "Depreciation of 5,000 was charged on the van.")
    show_problem(text, "SEAM 3 — a month-day date on a transaction line")
    line("column_lines", statements.column_lines(text))
    line("counted as a comparative", bool(statements.column_lines(text)))


def seam_4_two_operating_expenses_collide():
    text = ("The following trial balance was extracted at 31 December 2026.\n"
            "Cash 20,000\nSales 20,000\nSalaries 8,000\nRent 4,000\nCapital 12,000")
    show_problem(text, "SEAM 4 — Salaries and Rent on one trial balance")
    record = statements.solve(text)
    line("solved", record.get("solved"))
    line("refusal", record.get("refusal"))
    if record.get("spec"):
        line("chart lines", [(a["code"], a["name"], a["line"]) for a in record["spec"]["chart"]])
    if record.get("statements"):
        line("income statement", (record["statements"].get("income_statement") or "").replace("\n", " | "))


def seam_5_prose_rewrites_the_account():
    text = "Compute the net income for Alder Trading for 2025.\nSales 70,000\nCost of sales 60,000"
    show_problem(text, "SEAM 5 — a stated sales figure beside prose")
    rows, _skipped = statements.parse_rows(text)
    line("rows read", [(r["label"], r["written"], r["placed"]["placement"]["line"]) for r in rows])
    line("a prose line became a row", any("net income" in r["label"] for r in rows))


def seam_6_stated_partition():
    text = "The business made sales of 90,000, of which 55,000 was cash and the balance on credit."
    show_problem(text, "SEAM 6 — a partition the text states")
    tokens = se._tokens(text)
    line("tokens in the text", sorted(tokens))
    line("35,000 grounded", se._grounded(35000, tokens))
    payload = {"entries": [{"date": "2025-01-01", "description": "credit sales", "kind": "original",
                            "source_text": "the balance on credit",
                            "lines": [{"account": "4000", "debit": 35000},
                                      {"account": "1100", "credit": 35000}]}]}
    chart = [{"code": "4000", "name": "Revenue", "type": "income", "line": "Revenue"},
             {"code": "1100", "name": "Trade receivables", "type": "asset", "line": "Trade receivables"}]
    line("validator says", se.validate(payload, text, chart, 2, default_date="2025-01-01"))


def seam_7_detector_codes_have_no_home():
    show_problem("Sales returns of 2,000 and a warranty provision of 5,000.",
                 "SEAM 7 — a detector code the chart does not carry")
    slots = {"amount": 1, "cost": 1, "life": 5, "life_years": 5, "asset_account": "1500", "rate": 1,
             "months_expired": 1, "total_months": 12, "beginning_inventory": 0, "purchases": 1,
             "ending_inventory": 0, "receivables": 1, "prior_allowance": 0, "tax_rate": 0.25,
             "pretax_income": 1, "units_this_period": 1, "total_estimated_units": 1, "residual": 0,
             "accumulated": 0}
    codes = set()
    for _detector_id, template in sd.TEMPLATES.items():
        try:
            posted = template(dict(slots))
        except Exception:
            continue
        for account, _side, _amount in posted:
            codes.add(account)
    line("codes the templates post to", sorted(codes))
    line("posted to but not carried", sorted(codes - DETERMINISTIC_CHART_CODES))
    try:
        record = statements.solve("The owner started the business. Sales returns of 2,000.")
        line("solved", record.get("solved"))
        line("refusal", record.get("refusal"))
    except Exception as error:
        line("refused", str(error)[:160])


def main():
    print("READER SEAMS PROBE")
    attach()
    seam_1_period_collapses()
    seam_2_one_year_reads_as_two_periods()
    seam_3_transaction_date_reads_as_comparative()
    seam_4_two_operating_expenses_collide()
    seam_5_prose_rewrites_the_account()
    seam_6_stated_partition()
    seam_7_detector_codes_have_no_home()


if __name__ == "__main__":
    main()
