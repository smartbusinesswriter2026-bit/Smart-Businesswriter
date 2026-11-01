import urllib.request
import re

try:
    r = urllib.request.urlopen('http://localhost:4001/academic-sources.html', timeout=5)
    data = r.read().decode('utf-8')
    
    # Find all script src URLs
    scripts = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', data, re.IGNORECASE)
    for s in scripts:
        print("SCRIPT:", s)
        
except Exception as e:
    print('Error:', type(e).__name__, str(e))
