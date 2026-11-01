import urllib.request
req = urllib.request.Request('http://127.0.0.1:8000/#/new')
with urllib.request.urlopen(req) as response:
    html = response.read().decode('utf-8', errors='replace')
    count = html.count('id="tileclose"')
    print(f'tileclose element count on /#/new: {count}')
    if 'tilefoot' in html:
        print('PASS: tilefoot class found on /#/new')
    else:
        print('INFO: tilefoot NOT on /#/new (may be loaded dynamically)')