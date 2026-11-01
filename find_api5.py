import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Look for BACKEND variable definition
    backend_match = re.search(r'_asBackend\s*=\s*["\']([^"\']+)["\']', data)
    if backend_match:
        print("BACKEND:", backend_match.group(1))
    
    backend_match2 = re.search(r'BACKEND\s*=\s*["\']([^"\']+)["\']', data)
    if backend_match2:
        print("BACKEND2:", backend_match2.group(1))
    
    # Look for how the search is called - look for sources/search context
    search_context = re.findall(r'/api/sources/search[^"\']*', data)
    for s in sorted(set(search_context))[:20]:
        print("SEARCH_URL:", s)
    
    # Look for function definitions around search
    search_fn = re.findall(r'function\s+(\w*search\w*)\s*\(', data, re.IGNORECASE)
    for f in sorted(set(search_func))[:20]:
        print("FUNC:", f)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
