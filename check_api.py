import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    print("Page length:", len(data))
    
    # Look for API endpoints
    endpoints = re.findall(r'["\']([^"\']*(?:api|search|academic)[^"\']*)["\']', data, re.IGNORECASE)
    for ep in endpoints[:40]:
        print(ep)
except Exception as e:
    print('Error:', type(e).__name__, str(e))
