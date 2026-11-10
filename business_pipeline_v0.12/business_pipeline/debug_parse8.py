import os, json, urllib.request
os.environ['BP_OPENGO_API_KEY'] = os.environ['OPENCODE_GO_API_KEY']
api_key = os.environ['OPENCODE_GO_API_KEY']
url = "https://opencode.ai/inference/go/openai/v1/chat/completions"

system = 'You are a test-problem generator. Return ONLY a JSON object: {"problems": ["p1", "p2", "p3"]}. No markdown.'
user = 'Generate 3 complex accounting problems about depreciation.'

payload = {
    "model": "beam-free",
    "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ],
    "max_tokens": 2000
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "User-Agent": "smart-business-writer/1.0",
        "x-opencode-session": "bp-prose"
    }
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        open('debug_response.txt', 'w', encoding='utf-8').write(json.dumps(data, indent=2)[:2000])
        print("OK")
except Exception as e:
    open('debug_response.txt', 'w', encoding='utf-8').write(str(e)[:500])
    print("ERROR:", str(e)[:100])