import sys
sys.path.insert(0, "src")
sys.path.insert(0, "tests")
import product_statements_fixture as fixture
from bp.product import verify
import json, hashlib

fresh = fixture.record()
print("record plan_hash:", fresh.get("plan_hash"))

# freeze it
frozen = verify.freeze(dict(fresh))
print("freeze plan_hash:", frozen.get("plan_hash"))

# hash the body manually
body = {k: v for k, v in fresh.items() if k != "plan_hash"}
raw = json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)
manual = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
print("manual hash     :", manual)

# Are there non-deterministic values? Check repr of each top-level value's json
for k in sorted(fresh.keys()):
    if k == "plan_hash":
        continue
    r1 = json.dumps(fresh[k], sort_keys=True, separators=(",", ":"), default=str)
    r2 = json.dumps(fresh[k], sort_keys=True, separators=(",", ":"), default=str)
    if r1 != r2:
        print("NON-DETERMINISTIC:", k)
print("done")
