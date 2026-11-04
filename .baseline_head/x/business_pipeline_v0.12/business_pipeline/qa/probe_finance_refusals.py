"""Record exactly how the finance refusals behave, so the tests assert the real reason.

Usage:  PYTHONPATH=src python qa/probe_finance_refusals.py [out.txt]
"""
import sys

sys.path.insert(0, "src")

from bp import methods  # noqa: E402
from bp.orchestrator import Delivery, Pipeline  # noqa: E402

CASES = [
    ("E-fin-009 unknown input", "npv",
     {"rate": "0.10", "cashflows": ["-1000", "400", "400"], "bogus": "1"}),
    ("E-fin-010 survey weights", "npv",
     {"rate": "0.10", "cashflows": ["-1000", "400", "400"], "weights": ["1", "2", "3"]}),
    ("E-fin-012 no sign change", "irr", {"cashflows": ["100", "200", "300"]}),
    ("E-fin-012 two sign changes", "irr", {"cashflows": ["-100", "250", "-160"]}),
    ("E-fin-013 unrecovered outlay", "discounted_payback",
     {"cashflows": ["-1000", "10", "10"], "rate": "0.10"}),
    ("E-fin-014 price equals variable", "breakeven",
     {"fixed": "1000", "price": "10", "variable": "10"}),
    ("E-fin-015 growth above rate", "dcf_valuation",
     {"cashflows": ["100", "110"], "discount_rate": "0.05", "terminal_growth": "0.06"}),
    ("E-fin-015 bad timing", "dcf_valuation",
     {"cashflows": ["100", "110"], "discount_rate": "0.10", "timing": "start"}),
]


def main():
    lines = []
    emit = lines.append
    for label, method_id, inputs in CASES:
        emit("=" * 70)
        emit(label + "  (%s)" % method_id)
        m = methods.LIBRARY[method_id]
        emit("  validate_inputs: %s" % (methods.validate_inputs(m, inputs) or "no errors"))
        try:
            emit("  profile: %s" % (list(m.profile(dict(inputs))) or "no issues"))
        except Exception as error:  # noqa: BLE001
            emit("  profile raised: %s: %s" % (type(error).__name__, error))
        try:
            m.impl(dict(inputs))
            emit("  impl: DID NOT RAISE")
        except Exception as error:  # noqa: BLE001
            emit("  impl raised: %s: %s" % (type(error).__name__, error))
        delivery = Pipeline().start({"objective": "probe", "method": method_id,
                                     "currency": "USD", "inputs": inputs})
        if isinstance(delivery, Delivery):
            emit("  pipeline: %s / %s" % (delivery.status, delivery.blocked_reason))
        else:
            emit("  pipeline: confirmed-stage spec returned (NOT refused)")
    text = "\n".join(lines) + "\n"
    if len(sys.argv) > 1:
        open(sys.argv[1], "w", encoding="utf-8").write(text)
        print("wrote %s" % sys.argv[1])
    else:
        print(text)


if __name__ == "__main__":
    main()
