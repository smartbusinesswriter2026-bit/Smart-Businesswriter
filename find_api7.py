import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Find BACKEND definition
    for pattern in [r'BACKEND\s*=\s*["\']([^"\']+)["\']', r'_asBackend\s*=\s*["\']([^"\']+)["\']', r'const\s+BACKEND\s*=\s*["\']([^"\']+)["\']', r'let\s+BACKEND\s*=\s*["\']([^"\']+)["\']', r'var\s+BACKEND\s*=\s*["\']([^"\']+)["\']']:
        m = re.search(pattern, data)
        if m:
            print("BACKEND:", m.group(1))
            break
    
    # Also look for any localhost or 127.0.0.1 URLs
    localhost_urls = re.findall(r'["\']([^"\']*(?:localhost|127\.0\.0\.1|0\.0\.0\.0)[^"\']*)["\']', data, re.IGNORECASE)
    for u in sorted(set(localhost_urls))[:20]:
        print("LOCALHOST:", u)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
