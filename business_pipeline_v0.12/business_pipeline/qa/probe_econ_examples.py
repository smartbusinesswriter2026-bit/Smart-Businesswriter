"""Recompute every reproduced worked example in `docs/ECONOMICS_STUDENT_GUIDE.md`.

The expected values below are hand arithmetic taken from the guide (source of truth
rank 6, cross-checked against the contract's own formula). They are NOT produced by
the method: this is the independent second route required by the acceptance suite.

Usage:  python qa/probe_econ_examples.py
Writes: qa/baseline/econ_examples.txt
"""
import pathlib
import sys

sys.path.insert(0, "src")

from bp.methods import LIBRARY  # noqa: E402

APP = pathlib.Path(__file__).resolve().parent.parent
EQ = {"demand_intercept": "100", "demand_slope": "2",
      "supply_intercept": "20", "supply_slope": "2"}

# (id, method, inputs, {output_key: hand-computed expected})
EXAMPLES = [
    ("guide-1-equilibrium", "demand_supply_equilibrium", EQ,
     {"equilibrium_price": "20", "equilibrium_quantity": "60",
      "consumer_surplus": "900", "producer_surplus": "900",
      "total_surplus": "1800"}),
    ("guide-2-elasticity", "elasticity",
     {"price_1": "10", "quantity_1": "100", "price_2": "8", "quantity_2": "140"},
     {"elasticity": "-1.5", "revenue_change": "120"}),
    ("guide-3-tax", "tax_incidence", {**EQ, "tax_per_unit": "6"},
     {"consumer_price": "23", "producer_price": "17", "quantity": "54",
      "tax_revenue": "324", "deadweight_loss": "18"}),
    ("guide-4-ceiling", "price_control",
     {**EQ, "control_type": "ceiling", "control_price": "15"},
     {"quantity_demanded": "70", "quantity_supplied": "50", "shortage": "20",
      "quantity_traded": "50", "deadweight_loss": "50"}),
    ("guide-4-floor", "price_control",
     {**EQ, "control_type": "floor", "control_price": "25"},
     {"surplus": "20", "quantity_traded": "50", "deadweight_loss": "50"}),
    ("guide-5-concentration", "market_concentration",
     {"firm_revenues": ["40", "25", "15", "10", "10"]},
     {"hhi": "2650", "cr4": "90"}),
    ("guide-6-costs", "cost_curves",
     {"fixed_cost": "1000", "linear_cost": "10", "quadratic_cost": "0.5",
      "quantity": "20", "price": "40"},
     {"total_cost": "1400", "average_cost": "70", "average_variable_cost": "20",
      "average_fixed_cost": "50", "marginal_cost": "30",
      "revenue": "800", "profit": "-600"}),
    ("guide-7-profitmax", "profit_maximization",
     {"demand_intercept": "100", "demand_slope": "2", "fixed_cost": "100",
      "linear_cost": "10", "quadratic_cost": "0.5"},
     {"quantity": "18", "price": "64", "profit": "710"}),
    ("guide-8-national-income", "national_income",
     {"consumption": "600", "investment": "150", "government_spending": "200",
      "exports": "120", "imports": "170", "net_factor_income": "20",
      "depreciation": "50", "gdp_deflator": "120", "population": "100"},
     {"gdp": "900", "gnp": "920", "nnp": "870", "real_gdp": "750",
      "gdp_per_capita": "9"}),
    ("guide-9-growth", "growth_rate",
     {"start_value": "100", "end_value": "200", "periods": "10"},
     {"total_growth_rate": "1"}),
    ("guide-9-growth-practice", "growth_rate",
     {"start_value": "50", "end_value": "80", "periods": "6"},
     {"total_growth_rate": "0.6"}),
    ("guide-10-inflation", "inflation_cpi",
     {"cpi_start": "120", "cpi_end": "126", "nominal_interest_rate": "0.07",
      "wage_start": "200", "wage_end": "210"},
     {"inflation_rate": "0.05"}),
    ("guide-11-unemployment", "unemployment_rate",
     {"labour_force": "500", "employed": "450",
      "working_age_population": "800"},
     {"unemployment_rate": "0.1", "participation_rate": "0.625",
      "employment_ratio": "0.5625"}),
    ("guide-12-money", "money_multiplier",
     {"monetary_base": "200", "reserve_ratio": "0.2", "currency_drain_ratio": "0"},
     {"multiplier": "5", "money_supply": "1000"}),
    ("guide-13-fiscal", "fiscal_multiplier",
     {"mpc": "0.75", "tax_rate": "0.2", "government_spending_change": "80"},
     {"multiplier": "2.5", "output_change": "200"}),
    ("guide-14-budget", "budget_debt",
     {"government_revenue": "300", "government_spending": "330",
      "interest_payments": "20", "debt_stock": "800", "nominal_gdp": "1600",
      "nominal_growth_rate": "0.04"},
     {"overall_balance": "-50", "primary_balance": "-30", "debt_ratio": "0.5"}),
    ("guide-15-gini", "gini_coefficient",
     {"incomes": ["10", "20", "30", "40"]},
     {"gini": "0.25", "mean_income": "25"}),
    ("guide-16-poverty", "poverty_measures",
     {"incomes": ["10", "20", "30", "40"], "poverty_line": "25"},
     {"headcount_ratio": "0.5", "average_poverty_gap": "0.2"}),
    ("guide-17-externality", "externality_pigouvian",
     {**EQ, "marginal_external_cost": "4"},
     {"social_quantity": "56", "pigouvian_tax": "4",
      "deadweight_loss": "8"}),
    ("guide-19-tariff", "tariff_welfare",
     {**EQ, "world_price": "10", "tariff_per_unit": "5"},
     {"domestic_price": "15", "tariff_revenue": "100"}),
    ("guide-20-ppp", "exchange_rate_ppp",
     {"price_domestic": "5000", "price_foreign": "100", "nominal_rate": "55",
      "domestic_inflation": "0", "foreign_inflation": "0"},
     {"ppp_rate": "50", "real_exchange_rate": "1.1"}),
    ("guide-21-irp", "interest_rate_parity",
     {"spot_rate": "50", "domestic_rate": "0.06", "foreign_rate": "0.04",
      "time_to_maturity": "1", "domestic_inflation": "0",
      "foreign_inflation": "0"},
     {"forward_rate": "50.961538"}),
    ("guide-24-cournot", "cournot_duopoly",
     {"demand_intercept": "100", "demand_slope": "2",
      "marginal_cost_1": "10", "marginal_cost_2": "20"},
     {"quantity_1": "16.6667", "quantity_2": "11.6667",
      "price": "43.3333"}),
]


def close(observed, expected):
    try:
        return abs(float(observed) - float(expected)) <= 1e-4 * max(1.0, abs(float(expected)))
    except (TypeError, ValueError):
        return False



def main():
    lines = []
    missing_keys = []
    mismatches = []
    for example_id, method_id, inputs, expected in EXAMPLES:
        method = LIBRARY[method_id]
        try:
            out = method.impl(inputs)
        except Exception as error:                        # noqa: BLE001
            lines.append("%-26s RAISED   %s: %s" % (example_id, type(error).__name__, error))
            mismatches.append((example_id, "raise", str(error)))
            continue
        absent = [key for key in expected if key not in out]
        if absent:
            missing_keys.append((example_id, method_id, absent))
        bad = [(key, expected[key], out.get(key)) for key in expected
               if key in out and not close(out[key], expected[key])]
        status = "OK" if not bad and not absent else "MISMATCH"
        lines.append("%-26s %-8s %s" % (example_id, status, method_id))
        if absent:
            lines.append("    missing output keys: %s (have: %s)"
                         % (absent, sorted(out)))
        for key, want, got in bad:
            lines.append("    %-24s expected %-14s got %s" % (key, want, got))
            mismatches.append((example_id, key, (want, str(got))))
        if status == "OK":
            lines.append("    outputs: %s" % {k: str(v) for k, v in sorted(out.items())})

    lines.append("")
    lines.append("SUMMARY: %d examples, %d mismatched, %d with missing keys"
                 % (len(EXAMPLES), len(mismatches), len(missing_keys)))
    text = "\n".join(lines)
    (APP / "qa" / "baseline" / "econ_examples.txt").write_text(text, encoding="utf-8")
    print(text[-2500:])


if __name__ == "__main__":
    main()
