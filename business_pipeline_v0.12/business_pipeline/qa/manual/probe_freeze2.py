import sys
sys.path.insert(0, "src")
sys.path.insert(0, "tests")
import product_statements_fixture as fixture
from bp.product import verify

fresh = fixture.record()
print("record plan_hash:", fresh.get("plan_hash"))
recomputed = verify.freeze(dict(fresh))
print("recomputed plan_hash:", recomputed.get("plan_hash"))
# Does freeze mutate the input?
print("input plan_hash after freeze:", fresh.get("plan_hash"))
# Try freezing again
r2 = verify.freeze(dict(fresh))
print("second freeze:", r2.get("plan_hash"))
# Compare body hash excluding plan_hash
import json, hashlib
body = {k: v for k, v in fresh.items() if k != "plan_hash"}
raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
print("manual hash:", "sha256:" + hashlib.sha256(raw.encode()).hexdigest()[:16])
print("fresh has plan_hash key:", "plan_hash" in fresh)
print("fresh plan_hash type:", type(fresh.get("plan_hash")))
