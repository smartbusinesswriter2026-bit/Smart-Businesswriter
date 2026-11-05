import json, sys
sys.path.insert(0, "src")
sys.path.insert(0, "tests")
import product_statements_fixture as fixture

fresh = fixture.record()
rt = json.loads(json.dumps(fresh))
stored = fixture.load()
print("fresh == stored:", fresh == stored)
print("rt == fresh:", rt == fresh)
print("rt == stored:", rt == stored)
# find diff between rt and stored
def first_diff(a, b, path=""):
    if type(a) != type(b):
        return path, type(a).__name__, type(b).__name__
    if isinstance(a, dict):
        for k in list(a) + [k for k in b if k not in a]:
            if k not in a: return path+"."+k, "<missing>", repr(b[k])[:60]
            if k not in b: return path+"."+k, repr(a[k])[:60], "<missing>"
            r = first_diff(a[k], b[k], path+"."+k)
            if r: return r
        return None
    if isinstance(a, list):
        if len(a) != len(b): return path, "len "+str(len(a)), "len "+str(len(b))
        for i,(x,y) in enumerate(zip(a,b)):
            r = first_diff(x, y, path+"["+str(i)+"]")
            if r: return r
        return None
    if a != b:
        return path, repr(a)[:60], repr(b)[:60]
    return None
print("first diff rt vs stored:", first_diff(rt, stored))
