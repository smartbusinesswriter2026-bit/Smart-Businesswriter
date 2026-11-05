import sys
sys.path.insert(0, "src")
sys.path.insert(0, "tests")
import product_statements_fixture as fixture
fresh = fixture.record()
print("problem_type:", fresh.get("problem_type"))
print("reading_source:", fresh.get("reading_source"))
print("plan_hash:", fresh.get("plan_hash"))
# which route? check _record? no. Print reading.why
print("why:", (fresh.get("reading") or {}).get("why", "")[:100])
