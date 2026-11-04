"""Print the declared input schema of each method as compact one-line rows.

Usage:  PYTHONPATH=src python qa/probe_schema.py management_accounts trial_balance_check ...
"""
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402


def describe(spec):
    kind = spec.get("type")
    bits = [kind]
    if spec.get("required", True):
        bits.append("required")
    else:
        bits.append("optional")
    for key in ("min_items", "min_columns", "values", "max_chars", "min_rows", "min_cols"):
        if key in spec:
            value = spec[key]
            if isinstance(value, list) and len(value) > 6:
                value = value[:6] + ["..."]
            bits.append("%s=%s" % (key, value))
    return " ".join(str(bit) for bit in bits)


def main(argv):
    for method_id in argv[1:]:
        method = methods.LIBRARY[method_id]
        print("## %s  tier=%s metric=%s unit=%s ceiling=%s period=%s"
              % (method_id, method.tier, method.metric, method.unit, method.claim_ceiling,
                 method.default_period))
        for name in sorted(method.input_schema):
            spec = method.input_schema[name]
            print("   %-32s %-46s %s" % (name, describe(spec), spec.get("desc", "")))


if __name__ == "__main__":
    main(sys.argv)
