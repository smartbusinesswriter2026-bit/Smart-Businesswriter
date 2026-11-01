import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Look for API endpoints specifically
    endpoints = re.findall(r'["\'](/[^"\']*(?:api|search|academic|query|source)[^"\']*)["\']', data, re.IGNORECASE)
    for ep in sorted(set(endpoints))[:50]:
        print("ENDPOINT:", ep)
    
    # Look for fetch/axios calls with full URLs
    fetch_calls = re.findall(r'(?:fetch|axios\.(?:get|post|request)|XMLHttpRequest)\s*\(\s*["\']([^"\']+)["\']', data, re.IGNORECASE)
    for fc in sorted(set(fetch_calls))[:30]:
        print("CALL:", fc)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
