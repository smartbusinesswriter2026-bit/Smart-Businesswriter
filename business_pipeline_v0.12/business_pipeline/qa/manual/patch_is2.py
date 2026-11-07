src = open("src/bp/product/income_statement.py", encoding="utf-8").read()

# Fix the constructor call pattern
old_ctor = "    net_income=net_income,\n    lines=rendered,"
new_ctor = "    net_income=net_income,\n    gross_margin_percent=(gross_profit / net_sales * 100) if net_sales else Decimal(\"0\"),\n    lines=rendered,"
assert old_ctor in src, "ctor not found"
src = src.replace(old_ctor, new_ctor, 1)

# Fix render pattern
old_render = '    out.append(f"Gross Profit                                              {result.gross_profit:>12,.2f}")\n    out.append("")'
new_render = ('    out.append(f"Gross Profit                                              {result.gross_profit:>12,.2f}")\n'
              '    out.append(f"Gross Margin %                                            {result.gross_margin_percent:>12.2f}%")\n'
              '    out.append("")')
assert old_render in src, "render not found"
src = src.replace(old_render, new_render, 1)

open("src/bp/product/income_statement.py", "w", encoding="utf-8").write(src)
print("patched")
PYEOF
python qa/manual/patch_is2.py 2>&1 | Select-Object -Last 5