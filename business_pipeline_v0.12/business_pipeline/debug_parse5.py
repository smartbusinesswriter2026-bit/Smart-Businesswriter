import os, sys, json, urllib.request
os.environ['BP_OPENGO_API_KEY'] = os.environ['OPENCODE_GO_API_KEY']
api_key = os.environ['OPENCODE_GO_API_KEY']
url = "https://opencode.ai/inference/go/openai/v1/chat/completions"

system = (
    "You are a test-problem generator for a business analysis pipeline. "
    "Given an instruction and a count, create that many distinct test problems "
    "that exercise the pipeline. Each problem should be a realistic business "
    "analysis question or scenario. "
    "Make problems expert-level stress tests: contradictory data, multiple periods, unusual account placements, tricky adjustments, boundary values, and scenarios designed to break the pipeline. Include malformed inputs, ambiguous wording, and edge cases. "
    "Vary the format: some as word problems, some as trial balances, some as journal entries, "
    "some as narrative instructions. "
    "Return ONLY a JSON object: {\"problems\": [\"problem 1\", \"problem 2\", ...]}. "
    "No markdown, no extra text."
)
user = json.dumps({"instruction": "Generate complex accounting problems involving depreciation, journal entries, and financial statements", "count": 3, "difficulty": "expert"}, ensure_ascii=False)

payload = {
    "model": "beam-free",
    "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ],
    "temperature": 0.7,
    "max_tokens": 4000
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        "Authorization": "Bearer " + api_key,
        "Content-Type": "application/json",
        "User-Agent": "smart-business-writer/1.0"
    }
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print("SUCCESS")
        print("choices:", len(data.get('choices', [])))
        if data.get('choices'):
            content = data['choices'][0].get('message', {}).get('content', '')
            print("content length:", len(content))
            print("first 200:", content[:200])
except Exception as e:
    print("ERROR:", str(e)[:300])