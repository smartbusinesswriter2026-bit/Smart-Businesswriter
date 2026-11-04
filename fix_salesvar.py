with open('D:/SMART BUSINESSWRITER/business_pipeline_v0.12/business_pipeline/src/bp/server.py', 'r') as f:
    content = f.read()

old = '"salesvar": {"objective": "Why did revenue move against the budget?", "method": "sales_variances", "currency": "PHP", "period": "annual",\n                 "inputs": {"products": [\n                     {"name": "X", "budget_units": "100", "budget_price": "10", "actual_units": "120", "actual_price": "11"},\n                     {"name": "Y", "budget_units": "100", "budget_price": "20", "actual_units": "80", "actual_price": "18"}]}},'

new = '"salesvar": {"objective": "Why did revenue move against the budget?", "method": "sales_variances", "currency": "PHP", "period": "annual",\n                 "inputs": {"products": []}},'

if old in content:
    content = content.replace(old, new)
    with open('D:/SMART BUSINESSWRITER/business_pipeline_v0.12/business_pipeline/src/bp/server.py', 'w') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Old string not found')
    idx = content.find('salesvar')
    if idx >= 0:
        print('Found at:', idx)
        print(repr(content[idx:idx+300]))