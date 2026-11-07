src = open("src/bp/product/income_statement.py", encoding="utf-8").read()

# Fix: first detect has_inventory_data, then treat "cogs" (purchases) as purchases when inventory data present
old = '''    beginning_inventory = Decimal("0")
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
        cogs = beginning_inventory + purchases - purchase_returns + freight_in - ending_inventory'''

new = '''    beginning_inventory = Decimal("0")
    purchases = Decimal("0")
    purchase_returns = Decimal("0")
    freight_in = Decimal("0")
    ending_inventory = Decimal("0")

    # First pass: detect if inventory data is present
    has_inventory_data = any(l.kind in ("beginning_inventory", "purchase_returns",
                                       "freight_in", "ending_inventory") for l in lines)

    for line in lines:
        if line.kind == "revenue":
            revenue += line.amount
        elif line.kind == "contra_revenue":
            contra_revenue += line.amount
        elif line.kind == "cogs":
            if has_inventory_data:
                # "purchases" classified as cogs; treat as purchases component
                purchases += line.amount
            else:
                cogs += line.amount
        elif line.kind == "operating_expense":
            operating_expenses += line.amount
        elif line.kind == "non_operating_revenue":
            non_operating_revenue += line.amount
        elif line.kind == "non_operating_expense":
            non_operating_expense += line.amount
        elif line.kind == "beginning_inventory":
            beginning_inventory += line.amount
        elif line.kind == "purchases":
            purchases += line.amount
        elif line.kind == "purchase_returns":
            purchase_returns += line.amount
        elif line.kind == "freight_in":
            freight_in += line.amount
        elif line.kind == "ending_inventory":
            ending_inventory += line.amount

    # If inventory data is present, compute COGS from it
    if has_inventory_data:
        cogs = beginning_inventory + purchases - purchase_returns + freight_in - ending_inventory'''
assert old in src
src = src.replace(old, new, 1)
open("src/bp/product/income_statement.py", "w", encoding="utf-8").write(src)
print("patched")
