import urllib.request
import json

# Test the academic sources API
url = 'http://localhost:4001/api/sources/search'
payload = json.dumps({"topic": "five forces competitive advantage", "maxResults": 5}).encode('utf-8')
req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')

try:
    response = urllib.request.urlopen(req, timeout=30)
    print("Status:", response.status)
    result = response.read().decode('utf-8')
    print("Response length:", len(result))
    print(result[:3000])
except Exception as e:
    print('Error:', type(e).__name__, str(e))
