import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Look for API endpoints
    endpoints = re.findall(r'["\']([^"\']*(?:api|search|academic|fetch)[^"\']*)["\']', data, re.IGNORECASE)
    for ep in endpoints[:50]:
        print(ep)
    
    # Look for fetch/axios calls
    fetch_calls = re.findall(r'(?:fetch|axios\.|XMLHttpRequest|\.get\(|\.post\()\(["\']([^"\']+)["\']', data, re.IGNORECASE)
    for fc in fetch_calls[:30]:
        print("FETCH:", fc)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
