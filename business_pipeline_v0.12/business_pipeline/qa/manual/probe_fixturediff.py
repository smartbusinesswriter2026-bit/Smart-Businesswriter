import json, sys
sys.path.insert(0, "src")
sys.path.insert(0, "tests")
import product_statements_fixture as fixture

stored = fixture.load()
fresh = fixture.record()

def first_diff(a, b, path=""):
    if type(a) != type(b):
        return path, type(a).__name__, type(b).__name__
    if isinstance(a, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a:
                return path + "." + k, "<missing>", repr(b[k])[:80]
            if k not in b:
                return path + "." + k, repr(a[k])[:80], "<missing>"
            r = first_diff(a[k], b[k], path + "." + k)
            if r: return r
        return None
    if isinstance(a, list):
        if len(a) != len(b):
            return path, "len " + str(len(a)), "len " + str(len(b))
        for i,(x,y) in enumerate(zip(a,b)):
            r = first_diff(x, y, path + "[" + str(i) + "]")
            if r: return r
        return None
    if a != b:
        return path, repr(a)[:80], repr(b)[:80]
    return None

r = first_diff(stored, fresh)
print("first diff:", r)
print("stored plan_hash:", stored.get("plan_hash"))
print("fresh  plan_hash:", fresh.get("plan_hash"))
print("stored keys:", sorted(stored.keys()))
print("fresh  keys:", sorted(fresh.keys()))
