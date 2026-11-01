import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Search for BACKEND assignments more broadly
    for pattern in [
        r'BACKEND\s*=\s*([^,;]+)',
        r'_asBackend\s*=\s*([^,;]+)',
        r'backend\s*=\s*["\']([^"\']+)["\']',
        r'apiBase\s*=\s*["\']([^"\']+)["\']',
        r'apiUrl\s*=\s*["\']([^"\']+)["\']',
    ]:
        m = re.search(pattern, data, re.IGNORECASE)
        if m:
            print("MATCH:", pattern, "->", m.group(1))
    
    # Look for window.location usage
    loc_patterns = re.findall(r'window\.location[^;;]{0,100}', data)
    for lp in sorted(set(loc_patterns))[:20]:
        print("LOC:", lp)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
