"""Throwaway probe 3: worksheet ids, catalogue ids, target catalogue slots."""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from bp.product import subjects

W = subjects.WORKSHEETS
C = subjects.CATALOGUE

print("worksheet ids:", sorted(W.keys()))
print()
k0 = sorted(W.keys())[0]
print("=== WORKSHEETS[%r] full ===" % k0)
print(json.dumps(W[k0], indent=2, default=str))

print()
print("=== catalogue ids ===")
for cid in sorted(C.keys()):
    r = C[cid]
    print("  %-8s | %-52s | type=%-4s | form=%-13s | tpl=%-32s | %s" % (
        cid, r.get("name"), r.get("type"), r.get("form"), r.get("template"), r.get("status_short")))

print()
print("=== catalogue entries for the 8 target registry ids ===")
for cid in ["STR-15", "STR-16", "STR-17", "PM-05", "PM-09", "PM-06", "PM-15", "PM-16"]:
    print("\n--", cid, "present:", cid in C)
    if cid in C:
        print(json.dumps(C[cid], indent=2, default=str))
