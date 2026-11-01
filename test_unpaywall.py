import urllib.request
import json

# Test Unpaywall API with a DOI
doi = "10.61132/greeninflation.v2i1.204"
url = "https://api.unpaywall.org/v2/%s?email=test@example.com" % doi

try:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req, timeout=30)
    data = json.loads(response.read().decode('utf-8'))
    print("Best OA location:", data.get("best_oa_location"))
    print("OA status:", data.get("oa_status"))
except Exception as e:
    print('Error:', type(e).__name__, str(e))
