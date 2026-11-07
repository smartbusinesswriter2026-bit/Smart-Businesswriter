import re

# === 1. Add inventory component kinds to _classify_account ===
src = open("src/bp/product/income_statement.py", encoding="utf-8").read()

# Add after the COGS classification
old_cogs = '    # COGS\n    if re.search(r"^(purchases?|cost of (sales|goods sold)|cogs)$", a):\n        return ("cogs", "Cost of Goods Sold")\n'
new_cogs = ('    # COGS\n'
            '    if re.search(r"^(purchases?|cost of (sales|goods sold)|cogs)$", a):\n'
            '        return ("cogs", "Cost of Goods Sold")\n'
            '    # Inventory components for COGS computation\n'
            '    if re.search(r"^(beginning inventory|opening inventory|beginning stock)$", a):\n'
            '        return ("beginning_inventory", "Beginning Inventory")\n'
            '    if re.search(r"^(purchase returns?|returns? outwards|purchase returns and allowances)$", a):\n'
            '        return ("purchase_returns", "Purchase Returns")\n'
            '    if re.search(r"^(freight[- ]?in|carriage inwards?|freight on purchases)$", a):\n'
            '        return ("freight_in", "Freight-In")\n'
            '    if re.search(r"^(ending inventory|closing inventory|ending stock)$", a):\n'
            '        return ("ending_inventory", "Ending Inventory")\n')
assert old_cogs in src
src = src.replace(old_cogs, new_cogs, 1)

# === 2. Modify compute_income_statement to compute COGS from inventory data ===
old_compute = '''    revenue = Decimal("0")
    contra_revenue = Decimal("0")
    cogs = Decimal("0")
    operating_expenses = Decimal("0")
    non_operating_revenue = Decimal("0")
    non_operating_expense = Decimal("0")

    for line in lines:
        if line.kind == "revenue":
            revenue += line.amount
        elif line.kind == "contra_revenue":
            contra_revenue += line.amount
        elif line.kind == "cogs":
            cogs += line.amount
        elif line.kind == "operating_expense":
            operating_expenses += line.amount
        elif line.kind == "non_operating_revenue":
            non_operating_revenue += line.amount
        elif line.kind == "non_operating_expense":
            non_operating_expense += line.amount

    net_sales = revenue - contra_revenue
    gross_profit = net_sales - cogs'''

new_compute = '''    revenue = Decimal("0")
    contra_revenue = Decimal("0")
    cogs = Decimal("0")
    operating_expenses = Decimal("0")
    non_operating_revenue = Decimal("0")
    non_operating_expense = Decimal("0")
    beginning_inventory = Decimal("0")
    purchases = Decimal("0")
    purchase_returns = Decimal("0")
    freight_in = Decimal("0")
    ending_inventory = Decimal("0")
    has_inventory_data = False

    for line in lines:
        if line.kind == "revenue":
            revenue += line.amount
        elif line.kind == "contra_revenue":
            contra_revenue += line.amount
        elif line.kind == "cogs":
            cogs += line.amount
        elif line.kind == "operating_expense":
            operating_expenses += line.amount
        elif line.kind == "non_operating_revenue":
            non_operating_revenue += line.amount
        elif line.kind == "non_operating_expense":
            non_operating_expense += line.amount
        elif line.kind == "beginning_inventory":
            beginning_inventory += line.amount
            has_inventory_data = True
        elif line.kind == "purchases":
            purchases += line.amount
            has_inventory_data = True
        elif line.kind == "purchase_returns":
            purchase_returns += line.amount
            has_inventory_data = True
        elif line.kind == "freight_in":
            freight_in += line.amount
            has_inventory_data = True
        elif line.kind == "ending_inventory":
            ending_inventory += line.amount
            has_inventory_data = True

    # If inventory data is present, compute COGS from it
    if has_inventory_data:
        cogs = beginning_inventory + purchases - purchase_returns + freight_in - ending_inventory

    net_sales = revenue - contra_revenue
    gross_profit = net_sales - cogs'''
assert old_compute in src
src = src.replace(old_compute, new_compute, 1)

# === 3. Add gross_margin_percent to IncomeStatementResult ===
old_field = "    net_income: Decimal\n    lines: List[Dict[str, Any]]  # rendered lines for pre"
new_field = "    net_income: Decimal\n    gross_margin_percent: Decimal  # gross profit / net sales\n    lines: List[Dict[str, Any]]  # rendered lines for pre"
assert old_field in src
src = src.replace(old_field, new_field, 1)

# Update the constructor call
old_ctor = "    net_income=net_income,\n    lines=rendered,"
new_ctor = "    net_income=net_income,\n    gross_margin_percent=(gross_profit / net_sales * 100) if net_sales else Decimal(\"0\"),\n    lines=rendered,"
assert old_ctor in src
src = src.replace(old_ctor, new_ctor, 1)

# === 4. Update render to show gross margin % ===
old_render = '    out.append(f"Gross Profit                                              {result.gross_profit:>12,.2f}")\n    out.append("")'
new_render = ('    out.append(f"Gross Profit                                              {result.gross_profit:>12,.2f}")\n'
              '    out.append(f"Gross Margin %                                            {result.gross_margin_percent:>12.2f}%")\n'
              '    out.append("")')
assert old_render in src
src = src.replace(old_render, new_render, 1)

open("src/bp/product/income_statement.py", "w", encoding="utf-8").write(src)
print("patched income_statement.py")
