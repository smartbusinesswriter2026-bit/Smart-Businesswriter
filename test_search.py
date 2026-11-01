import urllib.request
import json

# Test search in Meilisearch
body = json.dumps({"q": "five forces", "limit": 5}).encode('utf-8')
req = urllib.request.Request('http://127.0.0.1:7700/indexes/pages/search',
    data=body, headers={'Content-Type': 'application/json'}, method='POST')

try:
    response = urllib.request.urlopen(req, timeout=10)
    data = json.loads(response.read().decode('utf-8'))
    print("Found", len(data.get("hits", [])), "hits")
    for hit in data.get("hits", [])[:3]:
        print("  -", hit.get("title"), "| page", hit.get("pdf_page"), "|", hit.get("doc_id"))
except Exception as e:
    print('Error:', type(e).__name__, str(e))
