import os, sys, traceback
sys.path.insert(0, "src")

from bp.product import statements as S

COGM = ("Data: Direct materials used 50,000; direct labor 40,000; manufacturing overhead 30,000; "
        "beginning WIP 10,000; ending WIP 12,000; beginning finished goods 15,000; ending finished goods 18,000; "
        "sales 200,000; selling and administrative expenses 35,000.\n"
        "Required: Create a cost of goods manufactured schedule and an income statement.")

CFS = ("Data: Net income 50,000; depreciation 10,000; gain on sale of equipment 3,000; increase in AR 8,000; "
       "decrease in inventory 5,000; increase in AP 4,000; purchase of equipment 25,000; proceeds from sale of "
       "equipment 7,000; issue common stock 20,000; dividends paid 12,000; beginning cash 15,000.\n"
       "Required: Create a statement of cash flows using the indirect method.")

for label, text in (("COGM", COGM), ("CFS", CFS)):
    print("=" * 70)
    print(label)
    print("=" * 70)
    for name, fn in (
        ("detect_income_statement", S.detect_income_statement),
        ("detect_ratio_analysis", S.detect_ratio_analysis),
        ("detect_given_balances", S.detect_given_balances),
        ("detect_eps", S.detect_eps),
    ):
        try:
            print("  ", name, "->", bool(fn(text)))
        except Exception as e:
            print("  ", name, "ERROR", e)
    try:
        print("   classify ->", S.classify(text)[0])
    except Exception as e:
        print("   classify ERROR", e)
    try:
        rows, skipped = S.parse_rows(S._split_semicolon_accounts(text))
        print("   parse_rows ->", len(rows), "rows,", len(skipped), "skipped")
        for r in rows:
            print("       ", r["label"], "=", r["written"], "| line:", r["placed"]["placement"]["line"])
        for s in skipped:
            print("        SKIP:", s[:70])
    except Exception as e:
        print("   parse_rows ERROR", e)
    try:
        print("   sections ->", S.fc.detect_sections(text))
    except Exception as e:
        print("   sections ERROR", e)
    print()
