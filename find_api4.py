import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Look for any fetch or axios calls with URLs
    # Pattern: fetch("url") or axios.get("url")
    patterns = [
        r'(?:fetch|axios\.(?:get|post|put|delete|request))\s*\(\s*["\']([^"\']+)["\']',
        r'fetch\s*\(\s*`([^`]+)`',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, data)
        for m in sorted(set(matches))[:50]:
            print("CALL:", m)
    
    # Also look for any URL patterns starting with /api/
    api_urls = re.findall(r'["\'](/api/[^"\']*)["\']', data, re.IGNORECASE)
    for u in sorted(set(api_urls))[:50]:
        print("API:", u)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
