import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Find the full fetch/axios call for /api/sources/search
    # Look for the pattern around it
    idx = data.find('/api/sources/search')
    if idx >= 0:
        # Print surrounding context
        start = max(0, idx - 500)
        end = min(len(data), idx + 1000)
        print(data[start:end])
        print("=" * 80)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
