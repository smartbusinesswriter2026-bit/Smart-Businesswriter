import os, sys, time
os.environ['BP_LLM_PROVIDER'] = 'opencode'
os.environ['BP_LLM_MODEL'] = 'beam-free'
os.environ['BP_OPENGO_API_KEY'] = os.environ['OPENCODE_GO_API_KEY']
sys.path.insert(0, 'src')
from bp import llm
models = llm.from_env()
system = (
    "You are a test-problem generator. "
    "Return ONLY a JSON object: {\"problems\": [\"problem 1\", \"problem 2\"]}. "
    "No markdown, no extra text."
)
user = "Generate 2 complex accounting problems about depreciation."
for attempt in range(5):
    try:
        result = models.call('builder', 'chat_heal', 'v1', system, user, consent=True)
        raw = result[0] if isinstance(result, tuple) else str(result)
        print(f'Attempt {attempt+1}: OK, length={len(raw)}')
        print('First 100:', repr(raw[:100]))
        break
    except Exception as e:
        print(f'Attempt {attempt+1}: ERROR: {str(e)[:100]}')
        time.sleep(2)