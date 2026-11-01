import urllib.request

# Test if DOI URL directly serves a PDF
doi_url = "https://doi.org/10.61132/greeninflation.v2i1.204"

try:
    req = urllib.request.Request(doi_url, headers={'User-Agent': 'Mozilla/5.0'})
    response = urllib.request.urlopen(req, timeout=30)
    print("Status:", response.status)
    print("Content-Type:", response.headers.get('Content-Type'))
    print("Final URL:", response.geturl())
    # Read first 100 bytes to check if it's PDF
    first_bytes = response.read(100)
    print("First bytes:", first_bytes[:20])
except Exception as e:
    print('Error:', type(e).__name__, str(e))
