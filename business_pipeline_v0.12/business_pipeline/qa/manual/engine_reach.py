"""How much of the 128-spec computation engine can actually be fed?

Every spec declares the input names it needs. A spec is reachable only if
something can supply those names: a text the engine can parse, or the output
of another spec. This measures the numbers the manual quotes - distinct input
names, how many a text can supply, how many another spec's output can supply,
and how many nothing supplies - so the claim is a measurement and not a claim.

    python qa/manual/engine_reach.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, ROOT)

from bp.product import financial_computations as fc  # noqa: E402

REG = fc.REGISTRY
SPECS = REG.all()

inputs = set()
for spec in SPECS:
    inputs.update(spec.inputs)

outputs = set()
for spec in SPECS:
    if spec.output_name:
        outputs.add(spec.output_name)
    outputs.add(spec.id)

patterns = getattr(fc, "COMMON_PATTERNS", {}) or {}
text_supplied = set(patterns)
if isinstance(patterns, dict):
    for key, value in patterns.items():
        if isinstance(value, dict):
            text_supplied.update(value.keys())

by_text = sorted(inputs & text_supplied)
by_output = sorted(inputs & outputs - text_supplied)
by_nothing = sorted(inputs - text_supplied - outputs)

print("specs                        : %d" % len(SPECS))
print("distinct input names         : %d" % len(inputs))
print("supplied by a text           : %d" % len(by_text))
print("supplied by another spec     : %d" % len(by_output))
print("supplied by nothing at all   : %d" % len(by_nothing))
print("")

reachable = 0
unreachable = []
no_input_at_all = []
for spec in SPECS:
    need = set(spec.inputs)
    missing = need - text_supplied - outputs
    if not missing:
        reachable += 1
    else:
        unreachable.append((spec.id, sorted(missing)))
        if not (need & (text_supplied | outputs)):
            no_input_at_all.append(spec.id)

print("specs whose inputs are all supplied : %d of %d" % (reachable, len(SPECS)))
print("specs with at least one gap          : %d" % len(unreachable))
print("specs with NO input supplied at all  : %d" % len(no_input_at_all))
print("  ->", ", ".join(no_input_at_all[:12]))
print("")
print("names supplied by BOTH a text and a spec output: %d"
      % len(text_supplied & outputs & inputs))
for spec_id, gaps in unreachable[:15]:
    print("   %-34s %s" % (spec_id, ", ".join(gaps[:4])))
if len(unreachable) > 15:
    print("   ... and %d more" % (len(unreachable) - 15))
