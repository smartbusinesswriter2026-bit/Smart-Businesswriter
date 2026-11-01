import urllib.request
try:
    r = urllib.request.urlopen('http://127.0.0.1:7700/health', timeout=5)
    print(r.read().decode())
except Exception as e:
    print('Error:', type(e).__name__, str(e))
