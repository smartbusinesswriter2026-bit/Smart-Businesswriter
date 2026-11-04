"""Quantify what the financial-computations engine can actually compute from text today."""
import os
import sys

ROOT = r"D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
sys.path.insert(0, os.path.join(ROOT, "src"))

from bp.product import financial_computations as fc  # noqa: E402

specs = fc.REGISTRY.all()
outputs = {s.output_name for s in specs}
patterns = set(fc.COMMON_PATTERNS)
raw_inputs = set(patterns)

all_inputs = set()
for s in specs:
    all_inputs.update(s.inputs)

from_text = all_inputs & raw_inputs
from_other = all_inputs & outputs
unreachable = all_inputs - from_text - from_other

print("specs:", len(specs))
print("distinct input names across all specs:", len(all_inputs))
print("  satisfiable from text patterns :", len(from_text))
print("  satisfiable from another spec  :", len(from_other))
print("  UNREACHABLE (always a gap)      :", len(unreachable))
print()
print("unreachable input names:")
for name in sorted(unreachable):
    users = sorted(s.id for s in specs if name in s.inputs)
    print("   %-34s used by %d spec(s): %s" % (name, len(users), ", ".join(users[:4])))
print()

# how many specs have every input reachable?
fully = [s for s in specs if all(i in from_text or i in outputs for i in s.inputs)]
partly = [s for s in specs if s not in fully and any(i in from_text or i in outputs for i in s.inputs)]
never = [s for s in specs if not any(i in from_text or i in outputs for i in s.inputs)]
print("specs whose every input is reachable :", len(fully))
print("specs with some input reachable       :", len(partly))
print("specs with NO input reachable         :", len(never))
print()
print("the 'pse' hit, field by field:")
for spec in fc.REGISTRY.all():
    if "pse" in spec.label.lower():
        print("  label:", repr(spec.label))
    if "pse" in spec.description.lower():
        print("  description:", repr(spec.description))
    if "pse" in spec.formula.lower():
        print("  formula:", repr(spec.formula))
    if "pse" in spec.id.lower():
        print("  id:", repr(spec.id))
    if "pse" in spec.output_name.lower():
        print("  output_name:", repr(spec.output_name))
