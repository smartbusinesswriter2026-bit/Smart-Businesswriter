import urllib.request
import json

try:
    r = urllib.request.urlopen('http://127.0.0.1:7700/indexes/pages/stats', timeout=5)
    data = json.loads(r.read().decode('utf-8'))
    print("Documents in index:", data.get("numberOfDocuments"))
    print("Is indexing:", data.get("isIndexing"))
except Exception as e:
    print('Error:', type(e).__name__, str(e))
