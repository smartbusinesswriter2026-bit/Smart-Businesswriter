with open('D:/SMART BUSINESSWRITER/business_pipeline_v0.12/business_pipeline/src/bp/server.py', 'r') as f:
    content = f.read()

old = '"accounts": {"objective": "Prepare the management accounts for the period", "method": "management_accounts", "currency": "USD",\n                 "inputs": {"spec": accounts.EXAMPLE_SPEC}},'

new = '"accounts": {"objective": "Prepare the management accounts for the period", "method": "management_accounts", "currency": "USD",\n                 "inputs": {"spec": {"period": {"start": "", "end": ""}, "currency": "USD", "framework": "IFRS", "places": 2, "chart": [], "prior_closing": {}, "opening": [], "entries": [], "schedules": []}}},'

if old in content:
    content = content.replace(old, new)
    with open('D:/SMART BUSINESSWRITER/business_pipeline_v0.12/business_pipeline/src/bp/server.py', 'w') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Old string not found')
    idx = content.find('accounts.EXAMPLE_SPEC')
    if idx >= 0:
        print('Found at:', idx)
        print(repr(content[idx-100:idx+100]))