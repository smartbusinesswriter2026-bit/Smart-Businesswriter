| # | Tool | Method | Tier | Headline metric / unit | Claim ceiling | Required inputs | Preset |
|---|---|---|---|---|---|---|---|
| E-ent-011 | `marketsize` | `market_sizing` | T1 | serviceable_obtainable_market / currency | descriptive | `target_population`, `annual_spend_per_customer`, `serviceable_share`, `obtainable_share` | `marketsize` |
| E-ent-012 | `forecast` | `trend_forecast` | T1 | forecast_1 / @unit | predictive | `values` | `forecast` |
| E-ent-013 | `demandcurve` | `demand_curve` | T1 | slope / ratio | associational | `prices`, `quantities` | `demandcurve` |
| E-ent-014 | `purchaseintent` | `purchase_intent` | T1 | intent_rate / rate | descriptive | `definitely`, `probably`, `maybe`, `never` | `purchaseintent` |
| E-ent-015 | `funnel` | `sales_funnel` | T1 | overall_conversion / rate | descriptive | `stages` | `funnel` |
| E-ent-016 | `cohort` | `cohort_retention` | T1 | average_retention / rate | descriptive | `cohort_sizes`, `retained` | `cohort` |
| E-ent-017 | `concentration` | `market_concentration` | T1 | hhi / ratio | descriptive | `firm_revenues` | `concentration` |
| E-ent-018 | `elasticity` | `elasticity` | T1 | price_elasticity / ratio | descriptive | `quantity_1`, `price_1`, `quantity_2`, `price_2` | `elasticity` |
| E-ent-019 | `descriptive` | `descriptive_stats` | T1 | mean / from_request | descriptive | `values` | `descriptive` |
| E-ent-020 | `chi_square` | `chi_square` | T1 | cramers_v / ratio | associational | `table` | `chi_square` |
| E-ent-021 | `power` | `power_analysis` | T1 | power / probability | descriptive | `design`, `effect`, `n1`, `sd1` | `power` |
| E-ent-022 | `pricing` | `pricing_decision` | T1 | cost_plus_price / currency | descriptive | `unit_cost`, `expected_units`, `markup_rate` | `pricing` |
| E-ent-023 | `breakeven` | `breakeven` | T1 | breakeven_units / units | descriptive | `fixed`, `price`, `variable` | `breakeven` |
| E-ent-024 | `multibreakeven` | `multi_product_breakeven` | T1 | breakeven_total_units / units | descriptive | `fixed_costs`, `products` | `multibreakeven` |
| E-ent-025 | `unitecon` | `unit_economics` | T1 | unit_margin / currency | descriptive | `price`, `variable_cost`, `acquisition_cost` | `unitecon` |
| E-ent-026 | `costcurves` | `cost_curves` | T1 | average_cost / currency | descriptive | `fixed_cost`, `linear_cost`, `quadratic_cost`, `quantity` | `costcurves` |
| E-ent-027 | `marketpower` | `market_power` | T1 | lerner_index / ratio | descriptive | `price`, `marginal_cost` | `marketpower` |
| E-ent-028 | `capacity` | `capacity_analysis` | T1 | max_output / units | descriptive | `resources` | `capacity` |
| E-ent-029 | `inventory` | `inventory_policy` | T1 | economic_order_quantity / units | descriptive | `annual_demand`, `order_cost`, `holding_cost_per_unit`, `lead_time_days` | `inventory` |
| E-ent-030 | `frommarket` | `sales_from_market` | T1 | target_revenue / currency | descriptive | `market_size`, `target_share`, `price` | `frommarket` |
| E-ent-031 | `proforma` | `proforma_statements` | T1 | total_net_income / currency | descriptive | `revenue`, `gross_margin_rate`, `operating_costs`, `depreciation` | `proforma` |
| E-ent-032 | `sensitivity` | `sensitivity_table` | T1 | base_profit / currency | descriptive | `base_price`, `base_units`, `base_variable_cost`, `base_fixed_cost`, `price_changes`, `volume_changes` | `sensitivity` |
| E-ent-033 | `ratios` | `ratio_analysis` | T1 | n_computed / count | descriptive | *(none required)* | `ratios` |
| E-ent-034 | `depreciation` | `depreciation_schedule` | T1 | total_depreciation / currency | descriptive | `cost`, `life` | `depreciation` |
| E-ent-035 | `salesprojection` | `sales_projection` | T1 | total_profit / currency | descriptive | `start_units`, `price`, `unit_variable_cost`, `fixed_cost_per_period` | `salesprojection` |
| E-ent-036 | `startupcapital` | `startup_capital` | T1 | amount_to_raise / currency | descriptive | `start_up_costs`, `working_capital` | `startupcapital` |
| E-ent-037 | `cashrunway` | `cash_runway` | T1 | runway_months / units | descriptive | `opening_cash`, `monthly_net_cash_flow` | `cashrunway` |
| E-ent-038 | `roi` | `return_on_investment` | T1 | roi / rate | descriptive | `total_investment`, `net_gain` | `roi` |
| E-ent-039 | `tax` | `tax_declared` | T1 | total_tax_charge / currency | descriptive | `taxable_income`, `income_tax_rate` | `tax` |
| E-ent-040 | `npv` | `npv` | T1 | npv / from_request | descriptive | `rate`, `cashflows` | `npv` |
| E-ent-041 | `irr` | `irr` | T1 | irr / rate | descriptive | `cashflows` | `irr` |
| E-ent-042 | `dpayback` | `discounted_payback` | T1 | discounted_payback / periods | descriptive | `cashflows` | `dpayback` |
| E-ent-043 | `projectmetrics` | `project_metrics` | T1 | npv / currency | descriptive | `cashflows`, `rate` | `projectmetrics` |
| E-ent-044 | `scenario` | `scenario_analysis` | T1 | npv_base / currency | descriptive | `cashflows`, `discount_rate`, `rate_low`, `rate_high` | `scenario` |
| E-ent-045 | `trendanalysis` | `trend_analysis` | T1 | revenue_cagr / rate | descriptive | `years`, `revenue`, `cost_of_sales`, `operating_expenses`, `net_income` | `trendanalysis` |
| E-ent-046 | `workingcapital` | `working_capital` | T1 | cash_conversion_cycle / days | descriptive | `revenue`, `cost_of_sales`, `inventory`, `receivables`, `payables`, `annual_demand`, `order_cost`, `holding_cost_per_unit`, `discount_percent`, `credit_terms_days`, `discount_days` | `workingcapital` |
| E-ent-047 | `captable` | `cap_table_round` | T1 | investor_pct / rate | descriptive | `pre_money_valuation`, `investment`, `founders_shares` | `captable` |
| E-ent-048 | `loan` | `loan_amortization` | T1 | payment / currency | descriptive | `principal`, `annual_rate`, `years` | `loan` |
| E-ent-049 | `dcf` | `dcf_valuation` | T2 | enterprise_value / currency | descriptive | `cashflows`, `discount_rate` | `dcf` |
| E-ent-050 | `multiples` | `multiples_valuation` | T2 | implied_equity_value / currency | descriptive | `metric`, `subject_value` | `multiples` |
| E-ent-051 | `equitybridge` | `equity_bridge` | T2 | equity_value / currency | descriptive | `enterprise_value` | `equitybridge` |
| E-ent-052 | `currency` | `currency_convert` | T1 | amount / currency | descriptive | `amount`, `from_currency`, `to_currency`, `rate` | `currency` |
| E-ent-053 | `sroi` | `sroi` | T2 | sroi_ratio / ratio | descriptive | `investment`, `benefits` | `sroi` |
| E-ent-054 | `cba` | `cost_benefit` | T2 | net_present_value / currency | descriptive | `costs`, `benefits` | `cba` |
| E-ent-055 | `costeffectiveness` | `cost_effectiveness` | T2 | n_options / count | descriptive | `options` | `cea` |
| E-ent-056 | `case_decision` | `case_decision` (template) | T2 | n/a (per alternative) | descriptive | declared in the template | `case_decision` |
