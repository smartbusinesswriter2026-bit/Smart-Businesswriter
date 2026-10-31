import json, urllib.request
with urllib.request.urlopen("http://127.0.0.1:8777/api/methods") as r:
    methods = json.loads(r.read().decode())
print("methods:", len(methods))
for m in methods:
    schema = m.get("input_schema") or {}
    kinds = sorted({(v.get("type"), k) for k, v in schema.items()})
    mappable = [k for k, v in schema.items() if v.get("type") in ("value_list", "code_map", "code_list", "column_map")]
    if mappable:
        print("%-24s mappable=%s" % (m["method_id"], mappable))
