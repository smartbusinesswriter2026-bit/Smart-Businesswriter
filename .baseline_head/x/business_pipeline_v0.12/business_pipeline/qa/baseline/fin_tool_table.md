| Tool | Method | Tier | Metric / unit | Claim ceiling | Required inputs | Optional inputs | Preset |
|---|---|---|---|---|---|---|---|
| `tvm` | `time_value` | T1 | future_value / currency | descriptive | `present_value`, `rate`, `periods` | `payment`, `compounding`, `timing` | `tvm` |
| `loan` | `loan_amortization` | T1 | payment / currency | descriptive | `principal`, `annual_rate`, `years` | `payments_per_year` | `loan` |
| `dupont` | `dupont_analysis` | T1 | return_on_equity / ratio | descriptive | `revenue`, `net_income`, `total_assets`, `equity` | `cost_of_sales`, `ebit`, `pretax_income`, `tax_expense`, `prior_revenue`, `prior_net_income`, `prior_total_assets`, `prior_equity` | `dupont` |
| `trendanalysis` | `trend_analysis` | T1 | revenue_cagr / rate | descriptive | `years`, `revenue`, `cost_of_sales`, `operating_expenses`, `net_income` | `total_assets`, `equity` | `trendanalysis` |
| `workingcapital` | `working_capital` | T1 | cash_conversion_cycle / days | descriptive | `revenue`, `cost_of_sales`, `inventory`, `receivables`, `payables`, `annual_demand`, `order_cost`, `holding_cost_per_unit`, `discount_percent`, `credit_terms_days`, `discount_days` | `days`, `daily_demand`, `lead_time_days`, `safety_stock` | `workingcapital` |
| `ratios` | `ratio_analysis` | T1 | n_computed / count | descriptive | — | `current_assets`, `current_liabilities`, `cash`, `inventory`, `receivables`, `payables`, `total_assets`, `total_liabilities`, `equity`, `revenue`, `cost_of_sales`, `operating_profit`, `net_income`, `interest_expense` | `ratios` |
| `breakeven` | `breakeven` | T1 | breakeven_units / units | descriptive | `fixed`, `price`, `variable` | `expected_units`, `target_profit` | `breakeven` |
| `multibreakeven` | `multi_product_breakeven` | T1 | breakeven_total_units / units | descriptive | `fixed_costs`, `products` | — | `multibreakeven` |
| `unitecon` | `unit_economics` | T1 | unit_margin / currency | descriptive | `price`, `variable_cost`, `acquisition_cost` | `churn_rate` | `unitecon` |
| `forecast` | `trend_forecast` | T1 | forecast_1 / from_request | predictive | `values` | `horizon`, `missing_codes`, `confidence_level` | `forecast` |
| `descriptive` | `descriptive_stats` | T1 | mean / from_request | descriptive | `values` | `missing_codes` | `descriptive` |
| `npv` | `npv` | T1 | npv / currency | descriptive | `rate`, `cashflows` | — | `npv` |
| `irr` | `irr` | T1 | irr / rate | descriptive | `cashflows` | — | `irr` |
| `dpayback` | `discounted_payback` | T1 | discounted_payback / periods | descriptive | `cashflows` | `rate` | `dpayback` |
| `projectmetrics` | `project_metrics` | T1 | npv / currency | descriptive | `cashflows`, `rate` | `finance_rate` | `projectmetrics` |
| `wacc` | `wacc` | T1 | wacc / rate | descriptive | `equity_value`, `debt_value`, `cost_of_equity`, `cost_of_debt_after_tax` | — | `wacc` |
| `capm` | `capm` | T1 | cost_of_equity / rate | descriptive | `risk_free_rate`, `market_return` | `beta`, `returns_asset`, `returns_market`, `debt_to_equity`, `tax_rate` | `capm` |
| `leverage` | `leverage_analysis` | T1 | eps / currency | descriptive | `ebit`, `interest_expense`, `tax_rate`, `debt`, `equity`, `shares_outstanding` | `working_capital`, `retained_earnings`, `total_assets`, `total_liabilities`, `sales`, `market_value_equity`, `alternative_interest_expense`, `alternative_shares_outstanding` | `leverage` |
| `scenario` | `scenario_analysis` | T1 | npv_base / currency | descriptive | `cashflows`, `discount_rate`, `rate_low`, `rate_high` | — | `scenario` |
| `case_decision` | `case_decision` (T2 template) | T2 | n/a | descriptive | `facts`, `alternatives` | — | `case_decision` |
| `dcf` | `dcf_valuation` | T2 | enterprise_value / currency | descriptive | `cashflows`, `discount_rate` | `terminal_growth`, `timing` | `dcf` |
| `dcfmid` | `dcf_valuation` | T2 | enterprise_value / currency | descriptive | `cashflows`, `discount_rate` | `terminal_growth`, `timing` | `dcfmid` |
| `equitybridge` | `equity_bridge` | T2 | equity_value / currency | descriptive | `enterprise_value` | `debt`, `cash`, `minority_interest`, `preferred_equity`, `shares_outstanding` | `equitybridge` |
| `multiples` | `multiples_valuation` | T2 | implied_equity_value / currency | descriptive | `metric`, `subject_value` | `comparables`, `peer_multiple`, `net_debt`, `shares_outstanding` | `multiples` |
| `portfolioval` | `portfolio_valuation` | T1 | nav / currency | descriptive | `holdings` | `cash` | `portfolioval` |
| `portfolioperf` | `portfolio_performance` | T1 | twr / ratio | descriptive | `periods` | `benchmark_start`, `benchmark_end` | `portfolioperf` |
| `bond` | `bond_analysis` | T1 | price / currency | descriptive | `face_value`, `coupon_rate`, `years_to_maturity` | `yield_to_maturity`, `price`, `payments_per_year` | `bond` |
| `portfolio` | `portfolio_analysis` | T1 | portfolio_return / rate | descriptive | `returns_a`, `returns_b`, `weight_a`, `risk_free_rate`, `returns_market` | — | `portfolio` |
| `pearson` | `pearson` | T1 | r / correlation | associational | `x`, `y` | `missing_codes`, `confidence_level`, `alpha` | `pearson` |
| `ols` | `ols` | T1 | r_squared / ratio | associational | `y`, `predictors` | `missing_codes`, `confidence_level`, `alpha` | `ols` |
| `ols_robust` | `ols_robust` | T1 | r_squared / ratio | associational | `y`, `predictors` | `missing_codes`, `confidence_level`, `alpha` | `*(none)*` |
| `risk` | `risk_metrics` | T1 | historical_var / rate | descriptive | `returns` | `confidence`, `portfolio_value`, `horizon_days`, `stress_return` | `risk` |
| `options` | `option_pricing` | T2 | option_price / currency | descriptive | `option_type`, `spot_price`, `strike_price`, `volatility`, `risk_free_rate`, `time_to_maturity` | `dividend_yield`, `steps` | `options` |
| `fx` | `fx_parity` | T1 | ppp_expected_spot / value | descriptive | `spot_rate`, `domestic_rate`, `foreign_rate`, `domestic_inflation`, `foreign_inflation`, `time_to_maturity` | `forward_rate`, `exposure_amount`, `hedge_forward`, `expected_spot` | `fx` |
| `currency` | `currency_convert` | T1 | amount / currency | descriptive | `amount`, `from_currency`, `to_currency`, `rate` | `rate_provenance`, `rate_source`, `rate_date` | `currency` |
