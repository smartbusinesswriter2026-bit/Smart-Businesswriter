"""Independent recomputation of the DCF mid-year and end-year valuations.

This is the evidence for defect D-FIN-01.  It computes both conventions by hand
(plain float arithmetic, its own loop) and compares them with the frozen
method's output and with the method's own declared self-check.  It recomputes
nothing from `bp.methods` except for the comparison.

Usage:  PYTHONPATH=src python qa/probe_dcf_midyear.py
"""
import sys

sys.path.insert(0, "src")

from bp import server  # noqa: E402
from bp.methods import LIBRARY, validate_inputs  # noqa: E402

CFS = [100000.0, 120000.0, 140000.0, 155000.0]
R = 0.10
G = 0.02


def ev_end(cfs, r, g):
    """Enterprise value with every cash flow discounted from the end of its period."""
    pv = sum(cf / (1.0 + r) ** t for t, cf in enumerate(cfs, 1))
    tv = cfs[-1] * (1.0 + g) / (r - g)
    return pv + tv / (1.0 + r) ** len(cfs), pv, tv / (1.0 + r) ** len(cfs)


def ev_mid(cfs, r, g):
    """The same, with every cash flow discounted from the middle of its period."""
    pv = sum(cf / (1.0 + r) ** (t - 0.5) for t, cf in enumerate(cfs, 1))
    tv = cfs[-1] * (1.0 + g) / (r - g)
    n = len(cfs)
    return pv + tv / (1.0 + r) ** (n - 0.5), pv, tv / (1.0 + r) ** (n - 0.5)


def main():
    m = LIBRARY["dcf_valuation"]
    end_inputs = {"cashflows": [str(c) for c in CFS], "discount_rate": str(R),
                  "terminal_growth": str(G), "timing": "end"}
    mid_inputs = dict(end_inputs, timing="mid")

    print("== independent recomputation (plain float, hand loop) ==")
    end_ev, end_pv, end_pvt = ev_end(CFS, R, G)
    mid_ev, mid_pv, mid_pvt = ev_mid(CFS, R, G)
    print("end-of-year : EV=%0.2f  (explicit PV=%0.2f + terminal PV=%0.2f)" % (end_ev, end_pv, end_pvt))
    print("mid-year    : EV=%0.2f  (explicit PV=%0.2f + terminal PV=%0.2f)" % (mid_ev, mid_pv, mid_pvt))
    print("mid > end   : %s   (mid/end = %0.6f)" % (mid_ev > end_ev, mid_ev / end_ev))

    print("")
    print("== the frozen method on the same two input sets ==")
    for label, inp in (("end", end_inputs), ("mid", mid_inputs)):
        print("  validate_inputs(%s) -> %s" % (label, validate_inputs(m, inp) or "no errors"))
        out = m.impl(dict(inp))
        print("  impl(%s).enterprise_value = %s" % (label, out["enterprise_value"]))
    print("  method mid/year ratio     = %s"
          % (m.impl(dict(mid_inputs))["enterprise_value"] / m.impl(dict(end_inputs))["enterprise_value"]))

    print("")
    print("== the method's own declared checks, on each input set ==")
    for label, inp in (("end", end_inputs), ("mid", mid_inputs)):
        checks = m.tests(dict(inp), m.impl)
        failing = [name for name, ok in checks if not ok]
        print("  on %-3s inputs: %d checks, failing=%s" % (label, len(checks), failing or "none"))

    print("")
    print("== what the product does with the dcfmid preset ==")
    print("  server.PRESETS['dcfmid']['inputs']['timing'] = %r"
          % server.PRESETS["dcfmid"]["inputs"].get("timing"))
    from bp.orchestrator import Pipeline  # noqa: E402
    delivery = Pipeline().run(dict(server.PRESETS["dcfmid"]), confirm_spec=lambda spec: True)
    print("  status = %r" % delivery.status)
    print("  reason = %r" % delivery.blocked_reason)


if __name__ == "__main__":
    main()
