"""Generate the schedule golden fixture with an independent numeric route.

The method library uses `Decimal`. This generator uses exact `fractions.Fraction`, applies the declared
rounding rule (half-even) at the declared places, and compares. Two different numeric models agreeing is
the point; re-running the same Decimal code would prove nothing - so this file deliberately **does not
import** `bp.schedules`.

Run from `business_pipeline/`:

    python tests/fixtures/generate_schedule_golden.py

Written by this script, never edited by hand.
"""

import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))


def half_even(fr, places):
    """Round an exact Fraction to `places` decimals, half to even - the declared ledger rule."""
    sign = -1 if fr < 0 else 1
    fr = abs(fr)
    scale = 10 ** places
    scaled = fr * scale
    whole, rem = divmod(scaled.numerator, scaled.denominator)
    twice = rem * 2
    if twice > scaled.denominator or (twice == scaled.denominator and whole % 2 == 1):
        whole += 1
    return Fraction(sign * whole, scale)


def as_str(fr, places):
    """The exact decimal string of a Fraction whose denominator divides 10**places."""
    scale = 10 ** places
    scaled = fr * scale
    if scaled.denominator != 1:
        raise AssertionError("value is not exact at %d places: %r" % (places, fr))
    n = scaled.numerator
    sign = "-" if n < 0 else ""
    whole, frac = divmod(abs(n), scale)
    if places == 0:
        return sign + str(whole)
    return "%s%d.%0*d" % (sign, whole, places, frac)


def spend(pool, parts, places):
    """Split an exact pool into `parts` rounded shares, the last absorbing the remainder."""
    if parts == 1:
        return [pool]
    each = half_even(pool / parts, places)
    out, used = [], Fraction(0)
    for _ in range(parts - 1):
        out.append(each)
        used += each
    out.append(pool - used)
    return out


def straight_line(cost, residual, life, places):
    return spend(Fraction(cost) - Fraction(residual), life, places)


def reducing_balance(cost, residual, life, rate, places):
    carrying, out = Fraction(cost), []
    for period in range(1, life + 1):
        if period == life:
            amount = carrying - Fraction(residual)
        else:
            amount = half_even(carrying * Fraction(rate), places)
            if carrying - amount < Fraction(residual):
                amount = carrying - Fraction(residual)
        out.append(amount)
        carrying -= amount
    return out


def units_of_production(cost, residual, total_units, units, places):
    depreciable = Fraction(cost) - Fraction(residual)
    last = max(i for i, u in enumerate(units) if u > 0)
    out, charged = [], Fraction(0)
    for i, u in enumerate(units):
        amount = ((depreciable - charged) if i == last
                  else half_even(depreciable * Fraction(u) / Fraction(total_units), places))
        out.append(amount)
        charged += amount
    return out


CASES = []
DEP_DEFAULTS = {"start": "2026-01", "dep_account": "5100", "accum_account": "1100"}


def case(name, kind, spec, expected, places=2):
    CASES.append({"name": name, "kind": kind, "spec": spec,
                  "expected": [as_str(x, places) for x in expected]})


case("straight_line_even", "depreciation",
     dict(DEP_DEFAULTS, cost="10000", residual="1000", life=4, places=2),
     straight_line(10000, 1000, 4, 2))

case("straight_line_rounding", "depreciation",
     dict(DEP_DEFAULTS, cost="1000", residual="0", life=3, places=2),
     straight_line(1000, 0, 3, 2))

case("reducing_balance_40pct", "depreciation",
     dict(DEP_DEFAULTS, cost="10000", residual="1000", life=4, rate="0.4", places=2, method="reducing_balance"),
     reducing_balance(10000, 1000, 4, Fraction(4, 10), 2))

case("units_of_production", "depreciation",
     dict(DEP_DEFAULTS, cost="10000", residual="1000", total_units="1000", units_per_period=[100, 400, 500],
          places=2, method="units_of_production"),
     units_of_production(10000, 1000, 1000, [100, 400, 500], 2))

case("prepayment_three", "prepayment",
     {"total": "1000", "periods": 3, "places": 2, "start": "2026-01", "date": "2026-01-05",
      "prepaid_account": "1300", "expense_account": "5000", "cash_account": "1000"},
     spend(Fraction(1000), 3, 2))

case("deferred_income_four", "deferred_income",
     {"total": "900", "periods": 4, "places": 2, "start": "2026-01", "date": "2026-01-10",
      "cash_account": "1000", "deferred_account": "2100", "revenue_account": "4000"},
     spend(Fraction(900), 4, 2))


def main():
    fixture = {
        "note": "Schedule arithmetic generated with exact fractions, rounding half-even at the declared "
                "places and letting the final period absorb the remainder. The library under test uses "
                "Decimal; this uses Fraction, so agreement is evidence rather than tautology.",
        "generator": "tests/fixtures/generate_schedule_golden.py",
        "numeric_route": "fractions.Fraction",
        "python": sys.version.split()[0],
        "rounding": "ROUND_HALF_EVEN at the declared places; final period absorbs the remainder",
        "cases": CASES,
    }
    out = os.path.join(HERE, "schedule_golden.json")
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(fixture, fh, indent=1)
        fh.write("\n")
    print("wrote %d cases to %s" % (len(CASES), out))
    for c in CASES:
        print("  %-26s %s" % (c["name"], c["expected"]))


if __name__ == "__main__":
    main()
