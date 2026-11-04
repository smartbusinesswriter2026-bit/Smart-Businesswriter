"""Smoke test: read a problem's words with a live model, then post the result through the plan layer.

This is the end-to-end proof of the split the owner's tips describe:

    text -> model (structure only) -> validator (grounding) -> ledger -> statements -> identities

It is a **smoke test, not a test suite**: it spends a real model call and needs a key. The scripted
provider in `tests/test_statement_plan.py` is the version that runs in CI.

Run from the repository root:

    $env:DEEPSEEK_API_KEY = "..."        # or another OpenAI-compatible key
    python qa/manual/extract-smoke.py

It sends only the synthetic problem text below - no user data. A key is read from the environment by
`bp.llm` and is never printed.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))

from bp import statement_extract as sx
from bp import statement_plan as sp
from bp.llm import DeepSeekProvider, LLMConfig, Models

# A synthetic problem: no dates on three of the four clauses, so the period-end fallback is exercised.
TEXT = ("The owner started the business with 20,000 cash. "
        "Paid 3,000 cash for a 12-month insurance policy on 1 February. "
        "Sales of 9,500 were made for cash. "
        "Paid rent of 1,200 and salaries of 2,400, both in cash.")

CHART_RAW = [
    {"code": "1000", "name": "Cash", "type": "asset", "line": "Cash", "section": "current", "role": "cash"},
    {"code": "1300", "name": "Prepaid insurance", "type": "asset", "line": "Prepayments", "section": "current"},
    {"code": "3000", "name": "Capital", "type": "equity", "line": "Capital", "role": "capital"},
    {"code": "4000", "name": "Sales", "type": "income", "line": "Revenue"},
    {"code": "5000", "name": "Rent", "type": "expense", "line": "Operating expenses"},
    {"code": "6000", "name": "Salaries", "type": "expense", "line": "Operating expenses"},
]

PLAN = {
    "period": {"start": "2026-01-01", "end": "2026-12-31"},
    "currency": "USD", "framework": "local", "places": 2,
    "chart": [sp.account("1000", "Cash", "asset", "Cash", "current", "cash"),
              sp.account("1300", "Prepaid insurance", "asset", "Prepayments", "current"),
              sp.account("3000", "Capital", "equity", "Capital", role="capital"),
              sp.account("3100", "Retained earnings", "equity", "Retained earnings", role="retained_earnings"),
              sp.account("4000", "Sales", "income", "Revenue"),
              sp.account("5000", "Rent", "expense", "Operating expenses"),
              sp.account("6000", "Salaries", "expense", "Operating expenses")],
    "policy": {"explicitly_stated": []},
    "prior_closing": {}, "opening": [], "adjustments": [], "schedules": [],
}


def main():
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("no DEEPSEEK_API_KEY in the environment; nothing was sent")
        return 2
    models = Models(DeepSeekProvider("deepseek-chat"), config=LLMConfig(enabled=True, max_output_tokens=1200))
    try:
        out = sx.extract(TEXT, CHART_RAW, models, consent=True, places=2,
                         period=PLAN["period"], default_date=PLAN["period"]["end"])
    except sx.ExtractionError as error:
        print("the model's reading was refused (this is the guard working):", str(error)[:400])
        return 0
    print("entries:", len(out["entries"]), "| adjustments:", len(out["adjustments"]),
          "| unplaceable:", len(out["unplaceable"]))
    for e in out["entries"]:
        print(" ", e["date"], "|", e["description"][:60], "|",
              [(l.get("account"), l.get("debit") or l.get("credit")) for l in e["lines"]])
    if out["adjustments"]:
        for a in out["adjustments"]:
            print("  adjustment:", a["id"], a["function"], a.get("params"))
    result = sp.build({**PLAN, "entries": out["entries"], "adjustments": out["adjustments"],
                       "policy": out["policy"] or {}})
    print("net income:", result["net_income"], "| assets:", result["total_assets"])
    print("articulation:", [(n, ok) for n, ok, _ in result["articulation"]])
    print("assumptions:", [a["assumption"] for a in result["assumptions"]["assumed"]])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
