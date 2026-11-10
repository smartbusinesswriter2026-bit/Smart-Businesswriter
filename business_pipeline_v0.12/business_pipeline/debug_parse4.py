import os, sys, time
os.environ['BP_LLM_PROVIDER'] = 'opencode'
os.environ['BP_LLM_MODEL'] = 'beam-free'
os.environ['BP_OPENGO_API_KEY'] = os.environ['OPENCODE_GO_API_KEY']
sys.path.insert(0, 'src')
from bp import llm
import json

models = llm.from_env()

diff_instructions = {
    "expert": "Make problems expert-level stress tests: contradictory data, multiple periods, unusual account placements, tricky adjustments, boundary values, and scenarios designed to break the pipeline. Include malformed inputs, ambiguous wording, and edge cases.",
}
diff_note = diff_instructions["expert"]

system = (
    "You are a test-problem generator for a business analysis pipeline. "
    "Given an instruction and a count, create that many distinct test problems "
    "that exercise the pipeline. Each problem should be a realistic business "
    "analysis question or scenario. " + diff_note + " "
    "Vary the format: some as word problems, some as trial balances, some as journal entries, "
    "some as narrative instructions. "
    "Return ONLY a JSON object: {\"problems\": [\"problem 1\", \"problem 2\", ...]}. "
    "No markdown, no extra text."
)
user = json.dumps({"instruction": "Generate complex accounting problems involving depreciation, journal entries, and financial statements", "count": 3, "difficulty": "expert"}, ensure_ascii=False)

for attempt in range(3):
    try:
        result = models.call('builder', 'chat_heal', 'v1', system, user, consent=True)
        raw = result[0] if isinstance(result, tuple) else str(result)
        print(f'Attempt {attempt+1}: OK, length={len(raw)}')
        # Try parsing
        try:
            data = json.loads(raw.strip().strip('`').strip())
            print(f'  Parsed OK, problems: {len(data.get("problems", []))}')
            break
        except Exception as e:
            print(f'  Parse error: {e}')
            print(f'  First 100: {repr(raw[:100])}')
    except Exception as e:
        print(f'Attempt {attempt+1}: ERROR: {str(e)[:100]}')
        time.sleep(2)