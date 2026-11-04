"""Probe the new financial-computations engine for three suspected defects.

1. Cross-section dependencies: a value computed in section C should be available
   to a section F spec that depends on it.
2. Input patterns whose first capture group is not the number.
3. The global-product rule: no Philippine place/currency name in a user-visible label.
"""
import os
import sys

ROOT = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import financial_computations as fc  # noqa: E402

print("=" * 72)
print("1. cross-section dependency")
print("=" * 72)
# Section C produces cash_and_equivalents; section F's quick ratio needs it.
raw = {
    "current_assets": fc.Decimal("50000"),
    "current_liabilities": fc.Decimal("20000"),
    "cash": fc.Decimal("15000"),
    "net_accounts_receivable": fc.Decimal("8000"),
    "inventory": fc.Decimal("12000"),
}
packs = fc.compute_all_sections("current ratio and quick ratio", raw, ["C", "F"])
for section in ("C", "F"):
    pack = packs.get(section)
    if not pack:
        continue
    for name in ("cash_and_equivalents", "net_accounts_receivable",
                 "current_ratio", "quick_ratio", "cash_ratio"):
        r = pack.results.get(name)
        if r is None:
            continue
        print("  %-26s ok=%-5s value=%-12s gap=%s" % (name, r.ok, r.value, r.gap or "-"))
print("  section F gaps:", packs["F"].gaps)

print()
print("=" * 72)
print("2. input patterns whose group(1) is not the number")
print("=" * 72)
text = ("Equipment cost 45,000. Property, plant and equipment 45,000. "
        "Cash 15,000. Total assets 90,000. Total liabilities 30,000. Total equity 60,000.")
parsed = fc.parse_inputs_from_text(text, fc.COMMON_PATTERNS)
for key in ("ppe_cost", "cash", "total_assets", "total_liabilities", "total_equity"):
    print("  %-20s -> %s" % (key, parsed.get(key, "NOT PARSED")))
bad = []
for name, pattern in fc.COMMON_PATTERNS.items():
    import re
    m = re.search(pattern, "Test 1,234.56 value here", re.I)
    if m:
        try:
            fc.Decimal(m.group(1).replace(",", ""))
        except Exception:
            bad.append((name, pattern, m.group(1)))
print("  patterns whose first group is not numeric:", len(bad))
for name, pattern, got in bad:
    print("     %-28s group(1)=%r  pattern=%s" % (name, got, pattern))

print()
print("=" * 72)
print("3. global-product labels")
print("=" * 72)
forbidden = ("peso", "php", "philippin", "manila", "pse", "psei")
hits = []
for spec in fc.REGISTRY.all():
    blob = " ".join([spec.id, spec.label, spec.output_name, spec.formula, spec.description]).lower()
    for word in forbidden:
        if word in blob:
            hits.append((spec.id, spec.label, word))
print("  offending specs:", len(hits))
for hit in hits:
    print("     ", hit)
