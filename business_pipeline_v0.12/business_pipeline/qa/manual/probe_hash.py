import json, hashlib, sys
sys.path.insert(0, "src")
sys.path.insert(0, "tests")
import product_statements_fixture as fixture

stored = fixture.load()
frozen_copy = dict(stored)
frozen_copy.pop("plan_hash", None)
raw = json.dumps(frozen_copy, sort_keys=True, separators=(",", ":"), default=str)
computed = "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
print("stored plan_hash :", stored.get("plan_hash"))
print("recomputed hash  :", computed)
print("equal:", computed == stored.get("plan_hash"))
# Is there a non-serializable object?
for k, v in stored.items():
    try:
        json.dumps(v, default=str)
    except Exception as e:
        print("NON-SERIALIZABLE:", k, type(v), e)
print("done")
