import urllib.request
req = urllib.request.Request('http://127.0.0.1:8000/')
with urllib.request.urlopen(req) as response:
    html = response.read().decode('utf-8', errors='replace')
    count = html.count('id="tileclose"')
    print(f'tileclose element count: {count}')
    if count >= 1:
        print('PASS: tileclose element found')
    else:
        print('FAIL: tileclose element NOT found')
    if 'tilefoot' in html:
        print('PASS: tilefoot class found')
    else:
        print('FAIL: tilefoot class NOT found')