import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Look for search-related endpoints
    endpoints = re.findall(r'["\']([^"\']*(?:search|search_academic|research|query|sources)[^"\']*)["\']', data, re.IGNORECASE)
    for ep in sorted(set(endpoints))[:50]:
        print("ENDPOINT:", ep)
    
    # Look for fetch calls with full URLs
    fetch_calls = re.findall(r'(?:fetch|axios\.\w+)\s*\(\s*["\']([^"\']+)["\']', data, re.IGNORECASE)
    for fc in sorted(set(fetch_calls))[:50]:
        print("CALL:", fc)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
