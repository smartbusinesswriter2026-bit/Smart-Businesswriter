p = "src/bp/product/statements.py"
text = open(p, encoding="utf-8").read()
old = '''    # Classify accounts into income statement vs balance sheet
    is_lines = [l for l in lines if l.kind in ("revenue", "contra_revenue", "cogs",
                                               "operating_expense",
                                               "non_operating_revenue", "non_operating_expense")]
    bs_lines = [l for l in lines if l.kind in ("current_asset", "non_current_asset",
                                                "current_liability", "non_current_liability")]

    # If we have income statement accounts, compute IS
    if is_lines:'''
new = '''    # Classify accounts into income statement vs balance sheet
    is_lines = [l for l in lines if l.kind in ("revenue", "contra_revenue", "cogs",
                                               "operating_expense",
                                               "non_operating_revenue", "non_operating_expense")]
    bs_lines = [l for l in lines if l.kind in ("current_asset", "non_current_asset",
                                                "current_liability", "non_current_liability")]

    # A problem with BOTH income-statement and balance-sheet accounts is a trial balance,
    # not a "given balances" problem.  Let the trial-balance route (read_deterministic)
    # handle it — it renders IS + RE + BS and carries the ratios.
    if is_lines and bs_lines:
        return None

    # If we have income statement accounts, compute IS
    if is_lines:'''
assert old in text
text = text.replace(old, new, 1)
open(p, "w", encoding="utf-8").write(text)
print("patched")
