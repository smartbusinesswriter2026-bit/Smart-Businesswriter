import urllib.request
import json

# Test the local API with a single keyword
url = 'http://localhost:4001/api/sources/search'
payload = json.dumps({"topic": "five forces competitive advantage", "maxResults": 3}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')

try:
    response = urllib.request.urlopen(req, timeout=15)
    result = json.loads(response.read().decode('utf-8'))
    print("Status: OK")
    print("Sources found:", len(result.get("sources", [])))
    for s in result.get("sources", [])[:3]:
        print("  -", s.get("title"), "|", s.get("doi"), "|", s.get("url"))
except Exception as e:
    print('Error:', type(e).__name__, str(e))
