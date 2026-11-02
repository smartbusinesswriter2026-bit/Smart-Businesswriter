# Economics shelf — acceptance manual

**Session:** 2 of 11 · **Subject:** `economics` · **Branch:** `corpus/merge-v1`
**Baseline commit:** `ab0be0d` · **Build:** 1.56 (`docs/CHANGELOG.md`)
**Written:** 2026-11-02 · **Author:** computation lane, for the product owner.

This is the manual the repository did not have. Every row cites the source of truth it was
taken from. Nothing here is an opinion about how the shelf *ought* to behave: where the code and
the documentation disagree, both are recorded and the row is marked `DISPUTED` (§10).

**How the tables are built.** Sections 1, 2, 5, 6, 7, 8, 9 and 10 are written by hand. The
tables in §3 (59 tools) and §4 (records, glossary, tiles) are **generated** from the live
registries by `python qa/build_econ_manual.py`: `bp.product.subjects.detail("economics")` for the
catalogue surface, `bp.methods.LIBRARY` for the method contract, and one real run of every preset
for the output names and their units (`qa/baseline/econ_tools_report.json`). A row therefore
cannot drift from the code — re-running the builder rebuilds it.

**Source-of-truth ranks** (work order §5): (1) `bp.methods.LIBRARY` + golden fixtures;
(2) `docs/sources/…Catalogue_v0_2.md`; (3) `CONDUCTOR_MANUAL.md` §4/§8 and
`VALIDATION_HARNESS.md` §5; (4) `framework_profiles.PROFILES`; (5) `subjects.detail()`;
(6) `docs/ECONOMICS_STUDENT_GUIDE.md`; (7) existing tests.

## 1. Who it serves

`docs/CURRICULUM_MAP.md`, row *Economics* (rank 5-adjacent):

| Course | Level |
|---|---|
| Applied Economics | senior high school ABM |
| Microeconomics, Macroeconomics | UG1–2 |
| Welfare, international, behavioural economics | UG3+ |

`docs/ECONOMICS_STUDENT_GUIDE.md` (rank 6) states the same assumption: the guide is written for
*senior high school ABM and first-year undergraduate* students for the micro and macro core, and
for *intermediate undergraduate* students for welfare, international, development and behavioural
economics; advanced econometrics is called a "separate, parked lane".

Ten disciplines are declared on the catalogue surface
(`subjects.detail("economics")["disciplines"]`): microeconomics, macroeconomics, welfare and public
economics, international economics, development economics, behavioural economics, industrial
organization, labour economics, public/nonprofit and impact evaluation, program and impact
evaluation.

The assignments it must survive (`CURRICULUM_MAP.md`, *Topics covered*): demand and supply,
elasticity, tax, price control, costs, market power, national income, money, fiscal, welfare,
trade, game theory, econometrics.

## 2. Scope and non-goals — promises, not bugs

The shelf declares three things it does **not** do (`detail("economics")["does_not"]`):

- It does not retrieve GDP, CPI, market or household data; you declare every input.
- It does not estimate a demand curve, a model or a causal effect from raw data.
- It does not make a policy recommendation or prove that one policy is better.

The student guide adds the arithmetic boundary: *"The tools calculate only what you declare."*
The catalogue names this shelf's gaps (`CURRICULUM_MAP.md`): advanced time series (VAR,
cointegration), the diagram renderer, retrieved macro data. The guide's *Not covered yet* and
*Never covered by arithmetic alone* sections name the rest.

These are **not** defects and are not tested as features:

| Not built | Declared by |
|---|---|
| VAR, cointegration, unit-root tests | `CURRICULUM_MAP.md` named gaps; `PARKED_QUEUE.md` item 7 |
| Economics catalogue section, diagram renderer | `ECONOMICS_STUDENT_GUIDE.md` "Not covered yet" |
| Retrieved GDP / CPI / market data | `does_not[0]`; `CONDUCTOR_MANUAL.md` retrieval limits |
| IS-LM and AD-AS diagrams, game trees, economic history | `ECONOMICS_STUDENT_GUIDE.md` "Never covered by arithmetic alone" |
| Imputation, complex-design inference | `PARKED_QUEUE.md` "Also waiting" |

## 3. Compute tools — one row per tool

Sources: *claims*, *refuses*, *checks*, *ceiling* and *inputs* are rank 1
(`bp.methods.LIBRARY`); *formula* and *level* are rank 5
(`subjects.detail("economics")["tools"]`); *outputs* and their units come from the
method's own `typing()` hook, read from a real run of the preset. `L` marks a list
input, `R` a record list; `opt` marks an optional input. A percentage is a fraction of
one (0.06 = 6%), never the number 6. Each row's acceptance ID is its test in §9.

### 001. Market equilibrium — `equilibrium`

- **Acceptance:** E-eco-001
- **Method / preset:** `demand_supply_equilibrium` / `equilibrium` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Equilibrium price and quantity for declared linear demand and supply curves (Qd = a - bP, Qs = c + dP), with consumer and producer surplus.
- **Refuses:** Estimating the curves from data; non-linear demand or supply; shifts, dynamics or expectations; taxes, externalities or market power; causal claims.
- **Formula (student note):** Qd = a - bP and Qs = c + dP; set Qd = Qs to find P*, then Q* = a - bP*.
- **Inputs:** `demand_intercept`, `demand_slope`, `supply_intercept`, `supply_slope`
- **Outputs (method typing):** equilibrium_price (currency/2), equilibrium_quantity (units/2), demand_choke_price (currency/2), supply_floor_price (currency/2), consumer_surplus (currency/2), producer_surplus (currency/2), total_surplus (currency/2)
- **Checks:** second_implementation_agrees, quantity_demanded_equals_quantity_supplied, consumer_surplus_is_the_triangle, producer_surplus_is_the_triangle, total_surplus_is_consumer_plus_producer
- **Assumptions:** Demand slopes down and supply slopes up, both linearly.; All else equal: no shifts, taxes, externalities or market power.; The curves are the owner's declared functions, not estimated from data.

### 002. Price elasticity of demand — `elasticity`

- **Acceptance:** E-eco-002
- **Method / preset:** `elasticity` / `elasticity` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Arc (midpoint) price elasticity of demand between two declared price-quantity observations, with the revenue change and an elastic/inelastic classification.
- **Refuses:** Point elasticity at a single price without a demand function; income or cross-price elasticity; estimating elasticity from a regression; causal claims.
- **Formula (student note):** E = (% change in Q) / (% change in P), using the midpoint (arc) formula.
- **Inputs:** `price_1`, `price_2`, `quantity_1`, `quantity_2`
- **Outputs (method typing):** price_elasticity (ratio/4), absolute_elasticity (ratio/4), pct_change_quantity (rate/4), pct_change_price (rate/4), total_revenue_1 (currency/2), total_revenue_2 (currency/2), revenue_change (currency/2), elastic (count/0), unit_elastic (count/0)
- **Checks:** second_implementation_agrees, arc_elasticity_equals_percentage_changes, swapping_the_observations_leaves_the_arc_elasticity_unchanged, revenue_change_equals_new_revenue_minus_old, elastic_flag_matches_the_magnitude
- **Assumptions:** The two observations lie on the same demand curve.; All else equal: no income, substitute price or taste change between the observations.; The arc formula is the agreed convention for a discrete change.

### 003. Tax incidence and deadweight loss — `taxincidence`

- **Acceptance:** E-eco-003
- **Method / preset:** `tax_incidence` / `taxincidence` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Economic incidence of a declared per-unit tax in a linear partial-equilibrium market: consumer and producer prices, the burden split, tax revenue and deadweight loss.
- **Refuses:** Estimating the curves; ad valorem taxes; a tax in a non-linear or general-equilibrium model; the statutory incidence; distributional or dynamic effects.
- **Formula (student note):** Consumer price Pc and producer price Ps satisfy Pc - Ps = t; the burden split follows the slopes.
- **Inputs:** `demand_intercept`, `demand_slope`, `supply_intercept`, `supply_slope`, `tax_per_unit`
- **Outputs (method typing):** equilibrium_price_no_tax (currency/2), equilibrium_quantity_no_tax (units/2), tax_per_unit (currency/2), consumer_price (currency/2), producer_price (currency/2), quantity_traded (units/2), consumer_incidence (currency/2), producer_incidence (currency/2), consumer_share (ratio/4), producer_share (ratio/4), tax_revenue (currency/2), deadweight_loss (currency/2)
- **Checks:** second_implementation_agrees, consumer_and_producer_incidence_sum_to_the_tax, consumer_share_equals_d_over_b_plus_d, tax_revenue_equals_tax_times_quantity_traded, deadweight_loss_is_the_triangle
- **Assumptions:** Linear demand and supply, all else equal.; The tax is a fixed amount per unit, not a percentage of price.; The market is competitive and partial equilibrium.

### 004. Price ceilings and floors — `pricecontrol`

- **Acceptance:** E-eco-004
- **Method / preset:** `price_control` / `pricecontrol` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** units / **descriptive**
- **Claims:** The effect of a declared price ceiling or floor on a linear competitive market: quantity traded, shortage or surplus, and deadweight loss.
- **Refuses:** Estimating the curves; rationing, queues or black markets; quality changes; dynamic or general-equilibrium effects; a control that is not a single fixed price.
- **Formula (student note):** At the control price, compare quantity demanded with quantity supplied; the short side determines quantity traded.
- **Inputs:** `control_price`, `control_type`, `demand_intercept`, `demand_slope`, `supply_intercept`, `supply_slope`
- **Outputs (method typing):** equilibrium_price (currency/2), equilibrium_quantity (units/2), control_price (currency/2), binding (count/0), quantity_demanded_at_control (units/2), quantity_supplied_at_control (units/2), quantity_traded (units/2), quantity_gap (units/2), shortage (units/2), surplus (units/2), deadweight_loss (currency/2)
- **Checks:** second_implementation_agrees, a_non_binding_control_leaves_the_market_unchanged, a_binding_ceiling_creates_a_shortage, a_binding_floor_creates_a_surplus, deadweight_loss_is_the_triangle
- **Assumptions:** Linear demand and supply, all else equal.; The control is a single fixed price that is enforced.; The market is competitive and partial equilibrium.

### 005. Market concentration (HHI) — `concentration`

- **Acceptance:** E-eco-005
- **Method / preset:** `market_concentration` / `concentration` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Market concentration from declared firm revenues: Herfindahl-Hirschman index (0-10,000), CR1, CR4 and the equivalent number of equal-sized firms.
- **Refuses:** Defining the market; estimating revenues; import competition or geographic markets; merger simulation; applying a threshold as a legal conclusion.
- **Formula (student note):** HHI = sum of squared percentage market shares; CR4 = sum of the four largest shares.
- **Inputs:** `firm_revenues`L
- **Outputs (method typing):** n_firms (count/0), total_revenue (currency/2), hhi (ratio/0), cr1 (ratio/2), cr4 (ratio/2), effective_n (ratio/2)
- **Checks:** second_implementation_agrees, hhi_equals_the_sum_of_squared_shares, cr4_is_the_sum_of_the_four_largest_shares, shares_sum_to_one_hundred, effective_n_times_hhi_equals_ten_thousand
- **Assumptions:** The declared revenues cover the relevant market.; Each firm's revenue is its market sales, not total corporate revenue across other markets.; The market boundary is the owner's judgement.

### 006. Cost curves — `costcurves`

- **Acceptance:** E-eco-006
- **Method / preset:** `cost_curves` / `costcurves` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Average cost, average variable cost, average fixed cost and marginal cost at a declared quantity for the quadratic cost function TC = fixed + linear x Q + quadratic x Q squared, with optional price, revenue, profit and a shutdown flag.
- **Refuses:** Estimating the cost function; step costs, learning curves or capacity limits; economies of scope; a full cost-curve schedule.
- **Formula (student note):** TC = FC + bQ + cQ^2; AC = TC / Q; MC = b + 2cQ.
- **Inputs:** `fixed_cost`, `linear_cost`, `price` opt, `quadratic_cost`, `quantity`
- **Outputs (method typing):** total_cost (currency/2), fixed_cost (currency/2), variable_cost (currency/2), average_cost (currency/2), average_variable_cost (currency/2), average_fixed_cost (currency/2), marginal_cost (currency/2), quantity (units/2), price (currency/2), total_revenue (currency/2), profit (currency/2), shutdown (count/0)
- **Checks:** second_implementation_agrees, marginal_cost_is_the_derivative_of_total_cost, average_cost_equals_total_cost_over_quantity, average_cost_equals_average_fixed_plus_average_variable, average_variable_cost_excludes_fixed_cost
- **Assumptions:** The declared quadratic cost function describes the relevant range.; Fixed cost does not change with quantity.; The quantity is positive.

### 007. Profit maximisation — `profitmax`

- **Acceptance:** E-eco-007
- **Method / preset:** `profit_maximization` / `profitmax` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Profit-maximising quantity and price for a firm facing linear demand P = a - bQ and quadratic cost TC = fixed + linear x Q + quadratic x Q squared, with revenue, cost, profit, markup and the Lerner index.
- **Refuses:** Estimating demand or cost; multi-product firms; price discrimination; entry, dynamics or strategic interaction; a competitive market price taken as given.
- **Formula (student note):** Set MR = MC: a - 2bQ = c + 2dQ, then P = a - bQ.
- **Inputs:** `demand_intercept`, `demand_slope`, `fixed_cost`, `linear_cost`, `quadratic_cost`
- **Outputs (method typing):** profit_maximizing_quantity (units/2), profit_maximizing_price (currency/2), total_revenue (currency/2), total_cost (currency/2), profit (currency/2), marginal_cost_at_optimum (currency/2), markup (currency/2), lerner_index (ratio/4)
- **Checks:** second_implementation_agrees, marginal_revenue_equals_marginal_cost, profit_equals_revenue_minus_cost, lerner_index_equals_markup_over_price, profit_falls_away_from_the_optimum
- **Assumptions:** The firm faces the declared linear demand curve.; The cost function is quadratic and non-decreasing.; The firm is a single-price monopolist or monopoly-like seller.

### 008. Markup and Lerner index — `marketpower`

- **Acceptance:** E-eco-008
- **Method / preset:** `market_power` / `marketpower` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Markup and Lerner index from a declared price and marginal cost, with the implied demand elasticity under the single-price monopoly model.
- **Refuses:** Estimating marginal cost; proving market power or consumer harm; a dynamic or strategic game; a multi-product firm; a regulated price.
- **Formula (student note):** Lerner index = (P - MC) / P; markup = P - MC; implied elasticity = 1 / Lerner.
- **Inputs:** `marginal_cost`, `price`
- **Outputs (method typing):** price (currency/2), marginal_cost (currency/2), markup (currency/2), lerner_index (ratio/4), implied_demand_elasticity (ratio/4)
- **Checks:** second_implementation_agrees, lerner_index_equals_markup_over_price, markup_equals_price_minus_marginal_cost, price_equals_marginal_cost_gives_zero_lerner, a_higher_price_raises_the_lerner_index
- **Assumptions:** The declared marginal cost is the relevant marginal cost.; The firm sets a single price.; The price and cost are from the same period and product.

### 009. Price discrimination — `pricediscrimination`

- **Acceptance:** E-eco-009
- **Method / preset:** `price_discrimination` / `pricediscrimination` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Third-degree price discrimination across two separated linear markets with constant marginal cost: quantities, prices and profit.
- **Refuses:** Estimating demand; arbitrage or market separation; first- or second-degree discrimination; menu costs, capacity or welfare comparison with a single price.
- **Formula (student note):** Set marginal revenue equal to marginal cost separately in each market.
- **Inputs:** `demand_intercept_1`, `demand_intercept_2`, `demand_slope_1`, `demand_slope_2`, `marginal_cost`
- **Outputs (method typing):** quantity_1 (units/2), price_1 (currency/2), quantity_2 (units/2), price_2 (currency/2), revenue_1 (currency/2), revenue_2 (currency/2), total_revenue (currency/2), total_profit (currency/2)
- **Checks:** second_implementation_agrees, marginal_revenue_equals_marginal_cost_in_market_one, marginal_revenue_equals_marginal_cost_in_market_two, total_revenue_is_the_sum_of_market_revenues, a_higher_marginal_cost_lowers_both_quantities
- **Assumptions:** The two markets are separable and resale is impossible.; Demand is linear and marginal cost is constant.; The firm can set a different price in each market.

### 010. Cournot duopoly — `cournot`

- **Acceptance:** E-eco-010
- **Method / preset:** `cournot_duopoly` / `cournot` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Two-firm Cournot equilibrium with linear demand and constant marginal costs: quantities, price and profits.
- **Refuses:** Estimating demand or costs; more than two firms; capacity, product differentiation, repeated interaction or collusion; a firm priced out of the market.
- **Formula (student note):** q1 = (a - 2c1 + c2) / (3b); q2 = (a - 2c2 + c1) / (3b); P = a - b(q1 + q2).
- **Inputs:** `demand_intercept`, `demand_slope`, `marginal_cost_1`, `marginal_cost_2`
- **Outputs (method typing):** quantity_1 (units/2), quantity_2 (units/2), total_output (units/2), price (currency/2), profit_1 (currency/2), profit_2 (currency/2), total_profit (currency/2)
- **Checks:** second_implementation_agrees, firm_one_is_on_its_best_response, firm_two_is_on_its_best_response, symmetric_costs_give_equal_quantities, a_higher_own_cost_lowers_own_quantity
- **Assumptions:** Two firms, homogeneous products and linear demand.; Constant marginal costs.; Simultaneous quantity choice and no collusion.

### 011. Nash equilibrium (2x2) — `nash`

- **Acceptance:** E-eco-011
- **Method / preset:** `nash_equilibrium` / `nash` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** count / **descriptive**
- **Claims:** Pure-strategy Nash equilibria of a declared 2x2 game, with a flag for each cell and the number of equilibria.
- **Refuses:** Mixed strategies; games larger than 2x2; sequential or repeated games; coalitional games; selecting among multiple equilibria.
- **Formula (student note):** A cell is a Nash equilibrium when neither player can gain by switching strategy alone.
- **Inputs:** `column_payoffs`L, `row_payoffs`L
- **Outputs (method typing):** nash_11 (count/0), nash_12 (count/0), nash_21 (count/0), nash_22 (count/0), nash_count (count/0)
- **Checks:** second_implementation_agrees, nash_count_equals_the_number_of_flags, prisoners_dilemma_has_one_nash, coordination_game_has_two_nash, matching_pennies_has_no_pure_nash
- **Assumptions:** The payoffs are the players' utilities and are comparable only within each player.; The game is one-shot and simultaneous.; Each player knows the payoff matrix.

### 012. Panel fixed effects — `panel`

- **Acceptance:** E-eco-012
- **Method / preset:** `panel_regression` / `panel` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** Balanced-panel fixed-effects (within) slope and intercept for one regressor, with within R-squared and degrees of freedom.
- **Refuses:** Unbalanced panels; time-invariant regressors; dynamic panels with lagged outcomes; clustered or robust standard errors; causal claims.
- **Formula (student note):** Within slope = sum of within-entity (x - entity mean x)(y - entity mean y) / sum of within-entity (x - entity mean x)^2.
- **Inputs:** `data`R
- **Outputs (method typing):** slope (ratio/4), intercept (ratio/4), within_r2 (ratio/4), n_obs (count/0), n_entities (count/0), n_periods (count/0), df (count/0)
- **Checks:** second_implementation_agrees, slope_equals_within_covariance_over_variance, adding_a_constant_to_y_leaves_the_slope_unchanged, adding_a_constant_to_x_leaves_the_slope_unchanged, within_residuals_sum_to_zero
- **Assumptions:** The panel is balanced and the entity effect is additive.; The slope is common across entities.; No time-varying omitted variable is correlated with x.

### 013. Instrumental variables — `iv`

- **Acceptance:** E-eco-013
- **Method / preset:** `instrumental_variables` / `iv` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** Just-identified instrumental-variables slope and intercept with one endogenous regressor and one excluded instrument, plus the first-stage and OLS slopes for comparison.
- **Refuses:** Over-identified models; weak instruments; controls; robust or clustered inference; testing the exclusion restriction; causal claims without a defended design.
- **Formula (student note):** Just-identified IV slope = cov(z, y) / cov(z, x); first stage = cov(z, x) / var(z).
- **Inputs:** `x`L, `y`L, `z`L
- **Outputs (method typing):** iv_slope (ratio/4), iv_intercept (ratio/4), first_stage_slope (ratio/4), ols_slope (ratio/4), n (count/0)
- **Checks:** second_implementation_agrees, iv_slope_is_the_covariance_ratio, first_stage_slope_is_the_instrument_on_the_regressor, scaling_the_instrument_leaves_the_iv_slope_unchanged, adding_a_constant_to_y_shifts_the_intercept_not_the_slope
- **Assumptions:** The instrument is relevant and satisfies the exclusion restriction.; The relationship is linear with a constant effect.; Observations are independent.

### 014. Regression discontinuity — `rdd`

- **Acceptance:** E-eco-014
- **Method / preset:** `regression_discontinuity` / `rdd` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** Sharp regression-discontinuity estimate from a local linear fit on each side of a declared cutoff and bandwidth.
- **Refuses:** Fuzzy designs; manipulation of the running variable; optimal bandwidth selection; covariates; bias-corrected or robust inference; causal claims without a defended design.
- **Formula (student note):** RDD estimate = right-side intercept at the cutoff - left-side intercept at the cutoff.
- **Inputs:** `bandwidth`, `cutoff`, `data`R
- **Outputs (method typing):** estimate (ratio/4), left_intercept (ratio/4), right_intercept (ratio/4), left_slope (ratio/4), right_slope (ratio/4), n_left (count/0), n_right (count/0)
- **Checks:** second_implementation_agrees, estimate_is_the_right_intercept_minus_the_left_intercept, shifting_the_outcome_leaves_the_estimate_unchanged, the_bandwidth_excludes_observations_outside_it, a_positive_jump_at_the_cutoff_gives_a_positive_estimate
- **Assumptions:** Treatment is determined by the running variable crossing the cutoff.; No manipulation of the running variable.; No other discontinuity at the cutoff.

### 015. Probit model — `probit`

- **Acceptance:** E-eco-015
- **Method / preset:** `probit` / `probit` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** Binary probit with one predictor: latent-index coefficients, log likelihood, McFadden pseudo R-squared and the marginal effect at the mean.
- **Refuses:** Multiple predictors, interactions, robust or clustered inference, separation, causal claims, or predicted probabilities outside the observed support.
- **Formula (student note):** P(y = 1) = Phi(intercept + slope x x); the marginal effect at the mean is phi(intercept + slope x mean x) x slope.
- **Inputs:** `x`L, `y`L
- **Outputs (method typing):** intercept (ratio/4), slope (ratio/4), log_likelihood (ratio/4), pseudo_r2 (ratio/4), marginal_effect_at_mean (ratio/4)
- **Checks:** second_implementation_agrees, score_equations_are_near_zero, predicted_probabilities_are_between_zero_and_one, scaling_the_predictor_rescales_the_slope, shifting_the_predictor_moves_the_intercept_not_the_slope
- **Assumptions:** The outcome is binary and observations are independent.; The latent index is linear in the predictor.; No separation or near-separation.

### 016. GDP and national income — `nationalincome`

- **Acceptance:** E-eco-016
- **Method / preset:** `national_income` / `nationalincome` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** GDP by the expenditure approach, plus GNP, NNP, net exports, optional GDP per capita and optional real GDP from a declared deflator.
- **Refuses:** Retrieving national-accounts data; the income or production approach; double-counting checks; chain-linked or base-year rebasing; informal or underground activity.
- **Formula (student note):** GDP = C + I + G + X - M; GNP = GDP + net factor income; NNP = GNP - depreciation.
- **Inputs:** `consumption`, `depreciation` opt, `exports`, `gdp_deflator` opt, `government_spending`, `imports`, `investment`, `net_factor_income` opt, `population` opt
- **Outputs (method typing):** gdp (currency/2), gnp (currency/2), nnp (currency/2), net_exports (currency/2), consumption (currency/2), investment (currency/2), government_spending (currency/2), exports (currency/2), imports (currency/2), net_factor_income (currency/2), depreciation (currency/2), population (count/0), gdp_per_capita (currency/2), gdp_deflator (ratio/2), real_gdp (currency/2)
- **Checks:** second_implementation_agrees, gdp_equals_expenditure_components, gnp_equals_gdp_plus_net_factor_income, nnp_equals_gnp_minus_depreciation, net_exports_equals_exports_minus_imports
- **Assumptions:** The components are one period's declared values in one currency.; Imports are already included in the other components and are subtracted once.; The deflator, if used, is an index with a base of 100.

### 017. Growth rate and CAGR — `growth`

- **Acceptance:** E-eco-017
- **Method / preset:** `growth_rate` / `growth` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** rate / **descriptive**
- **Claims:** Total growth, compound annual growth rate and the rule-of-72 doubling time between two declared values, with optional per-capita growth.
- **Refuses:** Forecasting future growth; fitting a trend; inflation adjustment; a growth-accounting decomposition into capital, labour and productivity.
- **Formula (student note):** CAGR = (end / start)^(1 / periods) - 1; doubling time is about 72 / (CAGR x 100).
- **Inputs:** `end_value`, `periods`, `population_end` opt, `population_start` opt, `start_value`
- **Outputs (method typing):** start_value (currency/2), end_value (currency/2), periods (count/0), total_growth (rate/4), cagr (rate/4), doubling_time_years (periods/2)
- **Checks:** second_implementation_agrees, cagr_compounds_to_the_end_value, total_growth_is_end_over_start_minus_one, doubling_time_times_cagr_is_approximately_72_percent, a_higher_end_value_raises_cagr
- **Assumptions:** The two values are measured on the same basis and currency.; The periods are equal in length.; No inflation adjustment is made unless the values are already real.

### 018. Inflation and real interest — `inflation`

- **Acceptance:** E-eco-018
- **Method / preset:** `inflation_cpi` / `inflation` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** rate / **descriptive**
- **Claims:** Inflation from two CPI values, the exact and approximate real interest rate, and optional real wage growth.
- **Refuses:** Retrieving CPI data; choosing or rebasing the basket; core versus headline inflation; expectations; a household-specific cost-of-living index.
- **Formula (student note):** Inflation = (CPI end - CPI start) / CPI start; real interest = (1 + nominal) / (1 + inflation) - 1.
- **Inputs:** `cpi_end`, `cpi_start`, `nominal_interest_rate` opt, `wage_end` opt, `wage_start` opt
- **Outputs (method typing):** cpi_start (ratio/2), cpi_end (ratio/2), inflation_rate (rate/4), nominal_interest_rate (rate/4), real_interest_rate (rate/4), real_interest_approximation (rate/4), nominal_wage_growth (rate/4), real_wage_growth (rate/4)
- **Checks:** second_implementation_agrees, inflation_is_the_cpi_percentage_change, fisher_identity_holds, approximation_gap_is_the_declared_identity, a_higher_cpi_end_raises_inflation
- **Assumptions:** The two CPI values use the same basket and base.; The nominal rate and the CPI cover the same period.; Wages, if used, are nominal values for the same period.

### 019. Unemployment and participation — `unemployment`

- **Acceptance:** E-eco-019
- **Method / preset:** `unemployment_rate` / `unemployment` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** rate / **descriptive**
- **Claims:** Unemployment rate, labour-force participation rate and employment-population ratio from declared labour-force, employment and working-age population counts.
- **Refuses:** Retrieving labour-market data; defining who is in the labour force; underemployment, discouragement or informal work; seasonal adjustment.
- **Formula (student note):** Unemployment rate = unemployed / labour force; LFPR = labour force / working-age population.
- **Inputs:** `employed`, `labour_force`, `working_age_population`
- **Outputs (method typing):** labour_force (count/0), employed (count/0), unemployed (count/0), unemployment_rate (rate/4), labour_force_participation_rate (rate/4), employment_population_ratio (rate/4)
- **Checks:** second_implementation_agrees, unemployed_equals_labour_force_minus_employed, unemployment_rate_equals_unemployed_over_labour_force, participation_rate_equals_labour_force_over_working_age_population, employment_population_ratio_equals_employed_over_working_age_population
- **Assumptions:** The three counts cover the same population and period.; The labour force does not exceed the working-age population.; The employed are a subset of the labour force.

### 020. Money multiplier — `moneymultiplier`

- **Acceptance:** E-eco-020
- **Method / preset:** `money_multiplier` / `moneymultiplier` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Simple and currency-adjusted money multipliers from the monetary base, reserve ratio and optional currency drain, with the implied money supply.
- **Refuses:** Retrieving monetary aggregates; excess reserves, bank capital or liquidity constraints; central-bank reaction functions; a full money-market model.
- **Formula (student note):** Simple multiplier = 1 / reserve ratio; extended = (1 + currency drain) / (reserve ratio + currency drain).
- **Inputs:** `currency_drain_ratio` opt, `monetary_base`, `reserve_ratio`
- **Outputs (method typing):** monetary_base (currency/2), reserve_ratio (ratio/4), currency_drain_ratio (ratio/4), simple_money_multiplier (ratio/4), extended_money_multiplier (ratio/4), money_supply_simple (currency/2), money_supply_extended (currency/2)
- **Checks:** second_implementation_agrees, simple_multiplier_is_one_over_the_reserve_ratio, extended_multiplier_is_the_currency_adjusted_formula, money_supply_is_the_base_times_the_multiplier, a_higher_reserve_ratio_lowers_the_simple_multiplier
- **Assumptions:** The reserve ratio is binding and constant.; Banks lend all available funds above reserves.; The currency drain is a constant fraction of deposits.

### 021. Fiscal multipliers — `fiscal`

- **Acceptance:** E-eco-021
- **Method / preset:** `fiscal_multiplier` / `fiscal` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Government-spending, tax and balanced-budget multipliers from a declared marginal propensity to consume and proportional tax rate, with the output change from declared fiscal changes.
- **Refuses:** Estimating the mpc or tax rate; crowding out, confidence, supply-side effects, lags, open-economy leakages or a full macro model.
- **Formula (student note):** Government multiplier = 1 / (1 - MPC(1 - t)); tax multiplier = -MPC / (1 - MPC(1 - t)).
- **Inputs:** `government_spending_change` opt, `mpc`, `tax_change` opt, `tax_rate` opt
- **Outputs (method typing):** mpc (ratio/4), tax_rate (ratio/4), government_spending_multiplier (ratio/4), tax_multiplier (ratio/4), balanced_budget_multiplier (ratio/4), government_spending_change (currency/2), tax_change (currency/2), output_change (currency/2)
- **Checks:** second_implementation_agrees, government_multiplier_is_one_over_one_minus_mpc_times_one_minus_tax, tax_multiplier_is_negative_mpc_times_the_government_multiplier, balanced_budget_multiplier_is_one_minus_mpc_times_the_government_multiplier, a_higher_mpc_raises_the_government_multiplier
- **Assumptions:** The mpc and tax rate are constant over the relevant range.; Prices and interest rates do not respond.; There is spare capacity.

### 022. Budget balance and debt — `budgetdebt`

- **Acceptance:** E-eco-022
- **Method / preset:** `budget_debt` / `budgetdebt` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** rate / **descriptive**
- **Claims:** Overall and primary budget balances, the debt-to-GDP ratio, the interest rate and the standard debt-ratio change from declared budget aggregates.
- **Refuses:** Forecasting debt; contingent liabilities, off-budget items, currency composition or maturity structure; a full debt-sustainability model; choosing a fiscal rule.
- **Formula (student note):** Overall balance = revenue - spending - interest; debt ratio = debt / GDP.
- **Inputs:** `debt_stock`, `government_revenue`, `government_spending`, `inflation_rate` opt, `interest_payments`, `nominal_gdp`, `nominal_growth_rate`
- **Outputs (method typing):** government_revenue (currency/2), primary_spending (currency/2), interest_payments (currency/2), total_spending (currency/2), overall_balance (currency/2), primary_balance (currency/2), debt_stock (currency/2), nominal_gdp (currency/2), debt_to_gdp (rate/4), interest_rate (rate/4), primary_balance_to_gdp (rate/4), debt_ratio_change (rate/4), real_interest_rate (rate/4)
- **Checks:** second_implementation_agrees, overall_balance_equals_revenue_minus_total_spending, primary_balance_equals_overall_balance_plus_interest, debt_ratio_equals_debt_over_gdp, debt_ratio_change_follows_the_interest_growth_primary_identity
- **Assumptions:** The aggregates are one period's declared values in one currency.; The debt stock is at the start of the period.; The interest rate is interest paid divided by the debt stock.

### 023. Output gap and Okun's law — `okun`

- **Acceptance:** E-eco-023
- **Method / preset:** `output_gap_okun` / `okun` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** rate / **descriptive**
- **Claims:** Output gap from actual and potential GDP, with the predicted unemployment change from a declared Okun coefficient.
- **Refuses:** Estimating potential output; estimating the Okun coefficient; a structural model of the labour market; a forecast.
- **Formula (student note):** Output gap = (actual GDP - potential GDP) / potential GDP; unemployment change = -Okun coefficient x gap.
- **Inputs:** `actual_gdp`, `current_unemployment_rate` opt, `okun_coefficient` opt, `potential_gdp`
- **Outputs (method typing):** output_gap (rate/4), predicted_unemployment_change_pp (rate/4), predicted_unemployment_rate (rate/4), okun_coefficient (ratio/4)
- **Checks:** second_implementation_agrees, output_gap_is_actual_over_potential_minus_one, zero_gap_gives_zero_unemployment_change, a_positive_gap_lowers_the_predicted_unemployment_rate, a_higher_okun_coefficient_raises_the_magnitude
- **Assumptions:** Actual and potential GDP are on the same price and currency basis.; The Okun relation is linear over the relevant range.; The coefficient is the owner's declared value.

### 024. Externalities and Pigouvian tax — `externality`

- **Acceptance:** E-eco-024
- **Method / preset:** `externality_pigouvian` / `externality` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Market and social optimum under a declared per-unit external cost, with the Pigouvian tax and deadweight loss.
- **Refuses:** Estimating external damages; valuing non-monetary effects; abatement technology; tax interaction; general-equilibrium or distributional effects.
- **Formula (student note):** Social optimum: demand = private supply + marginal external cost; Pigouvian tax = marginal external cost; DWL = 1/2 x tax x (market quantity - social quantity).
- **Inputs:** `demand_intercept`, `demand_slope`, `marginal_external_cost`, `supply_intercept`, `supply_slope`
- **Outputs (method typing):** market_price (currency/2), market_quantity (units/2), social_consumer_price (currency/2), social_producer_price (currency/2), social_quantity (units/2), external_cost (currency/2), pigouvian_tax (currency/2), deadweight_loss (currency/2)
- **Checks:** second_implementation_agrees, market_quantity_uses_the_private_curves, social_quantity_equates_demand_to_private_supply_plus_external_cost, pigouvian_tax_equals_the_marginal_external_cost, a_higher_external_cost_lowers_the_social_quantity
- **Assumptions:** Linear private demand and supply; a constant per-unit external cost.; The external cost is known and additively separable.; Partial equilibrium with no other distortions.

### 025. Public goods — `publicgood`

- **Acceptance:** E-eco-025
- **Method / preset:** `public_good` / `publicgood` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** units / **descriptive**
- **Claims:** Efficient provision of a public good from two declared linear marginal-benefit schedules and one marginal-cost schedule, with total and net benefit.
- **Refuses:** Estimating benefits; free-riding games; contribution mechanisms; crowding out; distributional weights; more than two individuals.
- **Formula (student note):** Sum the marginal benefits vertically; set social marginal benefit equal to marginal cost.
- **Inputs:** `mb1_intercept`, `mb1_slope`, `mb2_intercept`, `mb2_slope`, `mc_intercept`, `mc_slope`
- **Outputs (method typing):** efficient_quantity (units/2), social_marginal_benefit (currency/2), marginal_cost (currency/2), total_benefit (currency/2), total_cost (currency/2), net_benefit (currency/2)
- **Checks:** second_implementation_agrees, samuelson_condition_holds, total_benefit_is_the_area_under_social_marginal_benefit, total_cost_is_the_area_under_marginal_cost, a_higher_marginal_cost_lowers_the_efficient_quantity
- **Assumptions:** Two individuals with declared linear marginal benefits.; The good is non-rival and non-excludable.; Marginal cost is linear and positive.

### 026. Social welfare functions — `socialwelfare`

- **Acceptance:** E-eco-026
- **Method / preset:** `social_welfare` / `socialwelfare` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Utilitarian, Rawlsian and Nash social welfare from declared incomes, with the selected welfare function.
- **Refuses:** Estimating individual utility; interpersonal comparisons beyond income; equivalence scales; non-income dimensions; a policy recommendation.
- **Formula (student note):** Utilitarian = sum of incomes; Rawlsian = minimum income; Nash = geometric mean.
- **Inputs:** `incomes`L, `welfare_function`
- **Outputs (method typing):** n (count/0), mean_income (currency/2), min_income (currency/2), max_income (currency/2), utilitarian_welfare (currency/2), rawlsian_welfare (currency/2), nash_welfare (currency/2), social_welfare (currency/2)
- **Checks:** welfare_measures_agree_with_their_definitions, utilitarian_is_the_sum_of_incomes, rawlsian_is_the_minimum_income, nash_is_the_geometric_mean, a_transfer_from_the_richest_to_the_poorest_does_not_lower_nash_welfare
- **Assumptions:** Incomes are positive and comparable across the people listed.; Income is a sufficient proxy for the welfare argument.; The selected function is the intended ethical criterion.

### 027. Gini coefficient — `gini`

- **Acceptance:** E-eco-027
- **Method / preset:** `gini_coefficient` / `gini` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Gini coefficient, mean, minimum and maximum from declared incomes, with the poorest and richest shares.
- **Refuses:** Estimating incomes; equivalence scales; taxes and transfers; in-kind income; decomposing inequality by source or group; a policy verdict.
- **Formula (student note):** Gini = (2 x sum of rank-weighted incomes - (n + 1) x total income) / (n x total income).
- **Inputs:** `incomes`L
- **Outputs (method typing):** n (count/0), mean_income (currency/2), min_income (currency/2), max_income (currency/2), gini (ratio/4), poorest_share (ratio/4), richest_share (ratio/4)
- **Checks:** second_implementation_agrees, equal_incomes_give_zero_gini, gini_is_bounded_between_zero_and_one, scaling_all_incomes_leaves_gini_unchanged, reordering_the_incomes_leaves_gini_unchanged
- **Assumptions:** Incomes are non-negative and cover the intended population.; Each income belongs to one person or household.; No equivalence scale is applied.

### 028. Poverty measures — `poverty`

- **Acceptance:** E-eco-028
- **Method / preset:** `poverty_measures` / `poverty` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** rate / **descriptive**
- **Claims:** Headcount ratio, poverty gap, squared gap and total shortfall from declared incomes and a declared poverty line.
- **Refuses:** Choosing a poverty line; estimating incomes; multidimensional poverty; transient versus chronic poverty; equivalence scales; a policy verdict.
- **Formula (student note):** Headcount = share below the line; poverty gap = average normalised shortfall over the population.
- **Inputs:** `incomes`L, `poverty_line`
- **Outputs (method typing):** n (count/0), poor_count (count/0), headcount_ratio (rate/4), poverty_gap (rate/4), squared_gap (rate/4), total_gap (currency/2)
- **Checks:** second_implementation_agrees, headcount_is_the_share_below_the_line, poverty_gap_is_the_average_normalised_shortfall, squared_gap_is_the_average_squared_shortfall, a_higher_poverty_line_raises_the_headcount
- **Assumptions:** Incomes are non-negative and cover the intended population.; The poverty line is fixed and comparable across the observations.; No equivalence scale is applied.

### 029. Tax progressivity — `taxprogressivity`

- **Acceptance:** E-eco-029
- **Method / preset:** `tax_progressivity` / `taxprogressivity` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Average tax rate and a simple top-quartile progressivity gap from declared incomes and taxes.
- **Refuses:** Estimating taxes; a full Kakwani or Reynolds-Smolensky index; deductions, exemptions or behavioural responses; a policy verdict.
- **Formula (student note):** Progressivity gap = top-quartile tax share - top-quartile income share.
- **Inputs:** `incomes`L, `taxes`L
- **Outputs (method typing):** average_tax_rate (rate/4), top_income_share (rate/4), top_tax_share (rate/4), progressivity_gap (rate/4), n (count/0)
- **Checks:** second_implementation_agrees, average_tax_rate_equals_total_tax_over_total_income, top_income_share_equals_top_income_over_total_income, top_tax_share_equals_top_tax_over_total_tax, a_proportional_tax_gives_zero_progressivity_gap
- **Assumptions:** Incomes are positive and taxes are non-negative.; The two lists cover the same people and period.; The top quartile is the intended comparison group.

### 030. Optimal pollution — `optimalpollution`

- **Acceptance:** E-eco-030
- **Method / preset:** `optimal_pollution` / `optimalpollution` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** units / **descriptive**
- **Claims:** Optimal emissions and pollution tax where declared linear marginal damage equals declared linear marginal abatement cost.
- **Refuses:** Estimating damage or abatement costs; non-linear or threshold damage; multiple pollutants; technological change; a policy verdict.
- **Formula (student note):** Set marginal damage equal to marginal abatement cost; the pollution tax equals marginal damage at the optimum.
- **Inputs:** `marginal_abatement_intercept`, `marginal_abatement_slope`, `marginal_damage_intercept`, `marginal_damage_slope`
- **Outputs (method typing):** optimal_emissions (units/2), marginal_damage (currency/2), marginal_abatement_cost (currency/2), pollution_tax (currency/2), total_damage (currency/2), total_abatement_cost (currency/2)
- **Checks:** second_implementation_agrees, marginal_damage_equals_marginal_abatement_cost, pollution_tax_equals_marginal_damage, total_damage_is_the_area_under_marginal_damage, a_higher_damage_intercept_lowers_optimal_emissions
- **Assumptions:** Linear marginal damage and marginal abatement cost.; One pollutant and one period.; The curves are the owner's declared functions.

### 031. Comparative advantage — `comparative`

- **Acceptance:** E-eco-031
- **Method / preset:** `comparative_advantage` / `comparative` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Ricardian comparative advantage from two countries' declared unit labour requirements in two goods, with opportunity costs and specialisation flags.
- **Refuses:** Estimating productivity; more than two countries or goods; transport costs, tariffs, demand differences, increasing returns or strategic trade policy.
- **Formula (student note):** Opportunity cost of good one = hours per unit of good one / hours per unit of good two.
- **Inputs:** `countries`R
- **Outputs (method typing):** oc_a_good1 (ratio/4), oc_a_good2 (ratio/4), oc_b_good1 (ratio/4), oc_b_good2 (ratio/4), a_has_advantage_good1 (count/0), b_has_advantage_good1 (count/0), a_has_advantage_good2 (count/0), b_has_advantage_good2 (count/0)
- **Checks:** second_implementation_agrees, opportunity_costs_are_reciprocals, exactly_one_country_has_advantage_in_each_good, scaling_a_countrys_hours_leaves_its_opportunity_cost_unchanged, absolute_advantage_does_not_determine_comparative_advantage
- **Assumptions:** Unit labour requirements are constant and the only input.; Two countries and two goods.; Labour is mobile within a country and immobile between countries.

### 032. Tariff welfare — `tariff`

- **Acceptance:** E-eco-032
- **Method / preset:** `tariff_welfare` / `tariff` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Small-country tariff on a linear market: domestic price, imports, tariff revenue and the production and consumption deadweight losses.
- **Refuses:** Large-country terms-of-trade effects; retaliation; quotas; transport costs; general-equilibrium or dynamic effects.
- **Formula (student note):** Domestic price = world price + tariff; imports = quantity demanded - quantity supplied.
- **Inputs:** `demand_intercept`, `demand_slope`, `supply_intercept`, `supply_slope`, `tariff_per_unit`, `world_price`
- **Outputs (method typing):** domestic_price (currency/2), quantity_demanded (units/2), quantity_supplied (units/2), imports (units/2), imports_free_trade (units/2), tariff_revenue (currency/2), production_dwloss (currency/2), consumption_dwloss (currency/2), total_dwloss (currency/2)
- **Checks:** second_implementation_agrees, domestic_price_is_world_price_plus_tariff, imports_equal_domestic_demand_minus_supply, tariff_revenue_equals_tariff_times_imports, a_higher_tariff_lowers_imports
- **Assumptions:** Linear domestic demand and supply.; The country is a price-taker in world markets.; The tariff is a per-unit amount and is fully enforced.

### 033. Purchasing-power parity — `ppp`

- **Acceptance:** E-eco-033
- **Method / preset:** `exchange_rate_ppp` / `ppp` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Absolute and relative purchasing-power parity from declared price levels and a nominal exchange rate, with the real rate, misalignment and expected depreciation.
- **Refuses:** Retrieving price levels or exchange rates; choosing a basket; non-tradables, transport costs, tariffs or a full equilibrium model.
- **Formula (student note):** PPP rate = domestic price / foreign price; real exchange rate = nominal x foreign price / domestic price.
- **Inputs:** `domestic_inflation` opt, `foreign_inflation` opt, `nominal_rate`, `price_domestic`, `price_foreign`
- **Outputs (method typing):** ppp_rate (ratio/4), real_exchange_rate (ratio/4), misalignment (rate/4), expected_nominal_rate (ratio/4), expected_depreciation (rate/4)
- **Checks:** second_implementation_agrees, ppp_rate_is_the_domestic_price_over_the_foreign_price, real_exchange_rate_is_nominal_over_ppp, nominal_rate_equal_to_ppp_gives_zero_misalignment, a_higher_domestic_price_raises_the_ppp_rate
- **Assumptions:** The two price levels cover comparable baskets.; The nominal rate is domestic per foreign.; Relative PPP uses one period and the declared inflation rates.

### 034. Interest-rate parity — `irp`

- **Acceptance:** E-eco-034
- **Method / preset:** `interest_rate_parity` / `irp` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Covered interest parity: the implied forward rate and forward premium from a spot rate, two interest rates and a declared horizon, with an optional declared forward and real rates.
- **Refuses:** Retrieving rates; uncovered parity as a forecast; transaction costs, capital controls, credit or basis risk; a full exchange-rate model.
- **Formula (student note):** Forward = spot x [(1 + domestic rate) / (1 + foreign rate)]^T.
- **Inputs:** `domestic_inflation` opt, `domestic_rate`, `foreign_inflation` opt, `foreign_rate`, `forward_rate` opt, `spot_rate`, `time_to_maturity`
- **Outputs (method typing):** implied_forward (currency/4), forward_premium (rate/4), forward_rate (currency/4), cip_gap (rate/4), real_domestic_rate (rate/4), real_foreign_rate (rate/4)
- **Checks:** second_implementation_agrees, covered_interest_parity_holds, forward_premium_is_the_interest_differential, a_higher_domestic_rate_raises_the_implied_forward, a_higher_foreign_rate_lowers_the_implied_forward
- **Assumptions:** The spot rate is domestic per foreign.; The two interest rates apply to the same horizon.; Capital is mobile and there are no controls or transaction costs.

### 035. Balance of payments — `bop`

- **Acceptance:** E-eco-035
- **Method / preset:** `balance_of_payments` / `bop` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Balance-of-payments identity from declared current, capital and financial account balances, with an optional errors term and current-account-to-GDP ratio.
- **Refuses:** Retrieving balance-of-payments data; choosing a sign convention; reserve valuation effects; debt-service or sustainability analysis.
- **Formula (student note):** Current account + capital account + financial account + errors and omissions = 0.
- **Inputs:** `capital_account`, `current_account`, `errors_and_omissions` opt, `financial_account`, `gdp` opt
- **Outputs (method typing):** current_account (currency/2), capital_account (currency/2), financial_account (currency/2), errors_and_omissions (currency/2), net_balance (currency/2), balanced (count/0), current_account_to_gdp (rate/4)
- **Checks:** second_implementation_agrees, net_balance_is_the_sum_of_the_accounts, a_balanced_position_is_flagged, a_current_account_deficit_needs_an_offsetting_surplus, the_current_account_ratio_uses_gdp
- **Assumptions:** The three account balances use one sign convention and one period.; Errors and omissions are declared or zero.; GDP, if used, is on the same basis.

### 036. Human Development Index — `hdi`

- **Acceptance:** E-eco-036
- **Method / preset:** `hdi` / `hdi` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Human Development Index from declared life expectancy, expected and mean years of schooling and GNI per capita, using the UNDP goalposts.
- **Refuses:** Retrieving HDI data; choosing goalposts; inequality-adjusted HDI; multidimensional poverty; a policy verdict.
- **Formula (student note):** HDI = geometric mean of the life, education and income indices.
- **Inputs:** `expected_years_schooling`, `gni_per_capita`, `life_expectancy`, `mean_years_schooling`
- **Outputs (method typing):** life_index (ratio/4), education_index (ratio/4), income_index (ratio/4), hdi (ratio/4)
- **Checks:** second_implementation_agrees, dimension_indices_are_bounded, hdi_is_the_geometric_mean_of_the_indices, a_higher_life_expectancy_raises_the_life_index, the_goalposts_give_an_hdi_of_one
- **Assumptions:** The four inputs are on the UNDP definitions and comparable basis.; The goalposts are the declared UNDP values.; GNI per capita is in purchasing-power terms.

### 037. Expected utility — `expectedutility`

- **Acceptance:** E-eco-037
- **Method / preset:** `expected_utility` / `expectedutility` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Expected value, expected utility, certainty equivalent and risk premium for a declared gamble under risk neutrality or CRRA utility.
- **Refuses:** Estimating utilities or risk aversion; non-expected-utility models; ambiguity; reference dependence (use prospect_theory); a normative recommendation.
- **Formula (student note):** EV = sum of probability x outcome; EU = sum of probability x utility; the certainty equivalent is the certain amount with the same utility.
- **Inputs:** `outcomes`L, `probabilities`L, `risk_aversion` opt, `utility_function` opt
- **Outputs (method typing):** expected_value (currency/2), expected_utility (currency/2), certainty_equivalent (currency/2), risk_premium (currency/2), risk_aversion (ratio/4)
- **Checks:** second_implementation_agrees, expected_value_is_the_probability_weighted_outcome, risk_neutral_certainty_equivalent_equals_expected_value, a_risky_gamble_has_a_positive_risk_premium_under_crra, a_higher_risk_aversion_lowers_the_certainty_equivalent
- **Assumptions:** Probabilities are known and sum to one.; Outcomes are positive final wealth levels.; The utility function and risk aversion are the owner's declared values.

### 038. Prospect theory — `prospect`

- **Acceptance:** E-eco-038
- **Method / preset:** `prospect_theory` / `prospect` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Kahneman-Tversky-style prospect value from declared outcomes, probabilities and a reference point, with loss aversion, curvature and probability weighting.
- **Refuses:** Estimating the parameters; a normative recommendation; ambiguity, framing or reference-point selection; cumulative prospect theory with rank dependence.
- **Formula (student note):** v(gain) = gain^alpha; v(loss) = -loss aversion x loss^beta; probabilities are weighted.
- **Inputs:** `gain_curvature` opt, `loss_aversion` opt, `loss_curvature` opt, `outcomes`L, `probabilities`L, `probability_weighting` opt, `reference_point`
- **Outputs (method typing):** prospect_value (currency/2), expected_value (currency/2), loss_aversion (ratio/4), gain_curvature (ratio/4), loss_curvature (ratio/4), probability_weighting (ratio/4)
- **Checks:** second_implementation_agrees, a_reference_outcome_has_zero_prospect_value, a_loss_hurts_more_than_an_equal_gain, a_higher_loss_aversion_lowers_a_mixed_prospect, gains_and_losses_are_curved_separately
- **Assumptions:** Outcomes are evaluated relative to the declared reference point.; Probabilities are known and sum to one.; The parameters are the owner's declared values.

### 039. Real wage and labour market — `labour`

- **Acceptance:** E-eco-039
- **Method / preset:** `labour_market` / `labour` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Real wage, wage share of productivity and optional labour-market tightness from declared nominal wage, CPI, productivity and vacancy/unemployment figures.
- **Refuses:** Estimating wages or productivity; hours, composition, taxes, benefits or bargaining; a full labour-market model.
- **Formula (student note):** Real wage = nominal wage / (CPI / 100); wage share = real wage / labour productivity.
- **Inputs:** `cpi`, `labour_productivity`, `nominal_wage`, `unemployment_rate` opt, `vacancies` opt
- **Outputs (method typing):** nominal_wage (currency/2), cpi (ratio/2), labour_productivity (ratio/2), real_wage (currency/2), wage_share_of_productivity (currency/2), vacancies (currency/2), unemployment_rate (rate/4), labour_market_tightness (currency/2)
- **Checks:** second_implementation_agrees, real_wage_is_nominal_wage_over_the_price_index, wage_share_is_real_wage_over_productivity, a_higher_cpi_lowers_the_real_wage, a_higher_productivity_lowers_the_wage_share
- **Assumptions:** The nominal wage, CPI and productivity cover the same period and population.; The CPI is an index with a base of 100.; Productivity is output per worker.

### 040. Difference-in-differences — `did`

- **Acceptance:** E-eco-040
- **Method / preset:** `difference_in_differences` / `did` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** currency / **associational**
- **Claims:** Two-group, two-period difference-in-differences from four declared means.
- **Refuses:** Testing parallel trends; covariates, clustering, weights, repeated cross-sections, staggered adoption or a causal claim without the design.
- **Formula (student note):** DiD = (treated post - treated pre) - (control post - control pre).
- **Inputs:** `control_post`, `control_pre`, `treated_post`, `treated_pre`
- **Outputs (method typing):** treated_change (currency/2), control_change (currency/2), did_estimate (currency/2)
- **Checks:** second_implementation_agrees, treated_change_is_post_minus_pre, control_change_is_post_minus_pre, did_is_the_difference_of_the_two_changes, parallel_trends_give_a_zero_estimate
- **Assumptions:** The four means are comparable and measured the same way.; The control group would have followed the treated group's trend absent treatment.; No confounding shocks differ between the groups.

### 041. Trend forecast — `forecast`

- **Acceptance:** E-eco-041
- **Method / preset:** `trend_forecast` / `forecast` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** from_request / **predictive**
- **Claims:** Project a linear trend in a single time series forward for a user-chosen horizon, with prediction intervals and a disclosed out-of-sample error on the recent past.
- **Refuses:** Seasonal, cyclical or structural-break series; causal claims; multi-series or driver-based models; long horizons; policy simulations.
- **Formula (student note):** Fit y = a + bt to the series; the forecast extends the line and carries a prediction interval.
- **Inputs:** `confidence_level` opt, `horizon` opt, `missing_codes`L opt, `values`L
- **Outputs (method typing):** intercept (@unit/3), slope (@unit/3), r_squared (ratio/3), residual_se (@unit/3), p_slope (probability/4), n_fitted (count/0), n_excluded (count/0), horizon (count/0), confidence_level (rate/2), forecast_1 (@unit/3), ci_lower_1 (@unit/3), ci_upper_1 (@unit/3), forecast_2 (@unit/3), ci_lower_2 (@unit/3), ci_upper_2 (@unit/3), forecast_3 (@unit/3), ci_lower_3 (@unit/3), ci_upper_3 (@unit/3), mae_holdout (@unit/3), coverage_holdout (rate/2), n_holdout (count/0)
- **Checks:** second_implementation_agrees, out_of_sample_check_agrees, shift_moves_intercept_and_forecasts_not_slope, positive_scale_equivariance, bounded_and_consistent
- **Assumptions:** Observations are in time order with one value per period.; The trend is linear in time.; Errors around the trend are independent and roughly normal.

### 042. Currency conversion — `currency`

- **Acceptance:** E-eco-042
- **Method / preset:** `currency_convert` / `currency` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Convert an amount from one ISO 4217 currency to another at a rate the owner declares, recording the rate, its provenance, any source and date.
- **Refuses:** Retrieving or verifying exchange rates; interpolation, forward rates or triangulation; translating a set of statements; multi-currency consolidation; tax or fee conversion.
- **Formula (student note):** Converted amount = amount x rate, with the rate's provenance recorded.
- **Inputs:** `amount`, `from_currency`, `rate`, `rate_date` opt, `rate_provenance` opt, `rate_source` opt, `to_currency`
- **Outputs (method typing):** amount (currency/2), amount_from (currency/2), rate (ratio/6), _appendix (currency/2)
- **Checks:** second_implementation_agrees, round_trip_at_the_inverse_rate_returns_the_original, zero_amount_converts_to_zero, negative_amount_converts_with_the_same_magnitude, scaling_the_amount_scales_the_result
- **Assumptions:** The rate is the owner's declaration and describes the instant it is intended for.; Both currencies are ISO 4217 codes present in the declared table.

### 043. Pricing rules — `pricing`

- **Acceptance:** E-eco-043
- **Method / preset:** `pricing_decision` / `pricing` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Cost-plus, target-margin, break-even and target-return prices from declared unit cost, fixed cost, volume and rate inputs.
- **Refuses:** Researching willingness to pay or competitor prices; estimating a demand response; psychological pricing; discounts and promotions; tax.
- **Formula (student note):** Cost-plus price = unit cost x (1 + markup); margin price = unit cost / (1 - margin); break-even price = total cost / expected units.
- **Inputs:** `expected_units`, `fixed_cost` opt, `markup_rate`, `target_margin_rate` opt, `target_profit` opt, `unit_cost`
- **Outputs (method typing):** unit_cost (currency/2), fixed_cost (currency/2), expected_units (units/2), markup_rate (rate/4), total_cost (currency/2), cost_plus_price (currency/2), gross_margin_at_cost_plus (ratio/4), break_even_price (currency/2), target_margin_rate (rate/4), margin_price (currency/2), target_profit (currency/2), target_return_price (currency/2)
- **Checks:** second_implementation_agrees, cost_plus_price_is_unit_cost_times_one_plus_markup, break_even_price_covers_the_total_cost, margin_price_recovers_the_declared_margin, target_return_price_covers_cost_and_declared_profit
- **Assumptions:** Unit cost and fixed cost are constant over the declared range.; The expected volume is the owner's declared figure.

### 044. Demand line and revenue-max price — `demandcurve`

- **Acceptance:** E-eco-044
- **Method / preset:** `demand_curve` / `demandcurve` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** A straight line fitted to declared price-quantity observations, with the slope, R-squared, elasticity at the mean price and, when the slope is negative, the revenue-maximising price on the fitted line.
- **Refuses:** Identifying demand; causal claims; omitting variables, simultaneity or measurement error; non-linear demand; market data retrieval; pricing recommendations.
- **Formula (student note):** q = a + b p, fitted by least squares; elasticity at the mean = b x (mean price / mean quantity).
- **Inputs:** `prices`L, `quantities`L
- **Outputs (method typing):** intercept (ratio/4), slope (ratio/4), r_squared (ratio/4), mean_price (currency/2), mean_quantity (units/2), elasticity_at_mean (ratio/4), revenue_max_price (currency/2), revenue_max_quantity (units/2), revenue_max_revenue (currency/2)
- **Checks:** second_implementation_agrees, slope_is_the_covariance_over_the_variance, fitted_line_passes_through_the_means, r_squared_is_bounded_and_matches_the_residuals, revenue_maximising_price_sets_marginal_revenue_to_zero
- **Assumptions:** The pairs are comparable observations of the same market in the same period basis.; The relationship is approximately linear within the observed range.

### 045. Cost-benefit analysis — `cba`

- **Acceptance:** E-eco-045
- **Method / preset:** `cost_benefit` / `cba` · **tier** T2 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Discounted cost-benefit appraisal: present values of declared costs and benefits, the net present value and the benefit-cost ratio.
- **Refuses:** Monetising non-monetised effects; choosing the discount rate; tax, financing or risk adjustment; probability distributions or Monte Carlo; distributive weighting.
- **Formula (student note):** NPV = PV(benefits) - PV(costs); BCR = PV(benefits) / PV(costs).
- **Inputs:** `benefits`L, `costs`L, `discount_rate` opt
- **Outputs (method typing):** pv_costs (currency/2), pv_benefits (currency/2), net_present_value (currency/2), n_periods (count/0), discount_rate (rate/2), benefit_cost_ratio (ratio/3)
- **Checks:** second_implementation_agrees, net_value_is_present_value_of_benefits_minus_costs, zero_discount_rate_gives_undiscounted_sums, scaling_the_benefits_scales_the_benefit_side, a_higher_discount_rate_lowers_the_present_value
- **Assumptions:** Costs and benefits are the owner's declared values on one basis.; The declared rate is the appropriate social or financial discount rate.

### 046. Cost-effectiveness analysis — `cea`

- **Acceptance:** E-eco-046
- **Method / preset:** `cost_effectiveness` / `cea` · **tier** T2 · **level** intermediate
- **Row unit / claim ceiling:** count / **descriptive**
- **Claims:** Cost-effectiveness analysis against a declared comparator: incremental cost per unit of effect (ICER) for each other option, with dominance flags.
- **Refuses:** Comparing different outcome scales; weighting or aggregating several effects; probabilistic sensitivity analysis; deciding a willingness-to-pay threshold.
- **Formula (student note):** ICER = (cost of option - cost of comparator) / (effect of option - effect of comparator).
- **Inputs:** `options`R
- **Outputs (method typing):** comparator_cost (@unit/2), comparator_effect (@unit/2), n_options (count/0), icer_intensive (currency/2), delta_cost_intensive (currency/2), delta_effect_intensive (@unit/3), dominant_intensive (count/0)
- **Checks:** second_implementation_agrees, icer_is_incremental_cost_over_incremental_effect, comparator_is_the_first_option, cheaper_and_more_effective_is_flagged_dominant, adding_a_third_option_adds_one_ratio_per_option
- **Assumptions:** Costs and effects are declared on one basis and one outcome scale.; The first option is the intended comparator.

### 047. Social return on investment — `sroi`

- **Acceptance:** E-eco-047
- **Method / preset:** `sroi` / `sroi` · **tier** T2 · **level** intermediate
- **Row unit / claim ceiling:** ratio / **descriptive**
- **Claims:** Social return on investment: present value of declared social benefits divided by the declared investment.
- **Refuses:** Estimating or verifying social benefits; additionality, deadweight, attribution or displacement adjustments; assurance; comparing across different outcome scales.
- **Formula (student note):** SROI = PV(social benefits) / investment.
- **Inputs:** `benefits`L, `discount_rate` opt, `investment`
- **Outputs (method typing):** pv_benefits (currency/2), investment (currency/2), sroi_ratio (ratio/3), net_value (currency/2), n_periods (count/0), discount_rate (rate/2)
- **Checks:** second_implementation_agrees, ratio_is_present_value_over_investment, net_value_is_benefits_minus_investment, doubling_the_investment_halves_the_ratio, zero_discount_rate_gives_undiscounted_benefits
- **Assumptions:** Benefits are declared values on one basis.; The investment is a declared amount and the rate is the owner's choice.

### 048. Net present value — `npv`

- **Acceptance:** E-eco-048
- **Method / preset:** `npv` / `npv` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Value a stream of cash flows at a user-supplied discount rate.
- **Refuses:** Choosing the discount rate; ranking mutually exclusive projects of unequal scale or life; unequal period lengths.
- **Formula (student note):** NPV = sum of CF_t / (1 + r)^t, with the first cash flow at t = 0 and undiscounted.
- **Inputs:** `cashflows`L, `rate`
- **Outputs (method typing):** _none_
- **Checks:** second_implementation_agrees, boundary_zero_rate_equals_sum, t0_cash_flow_shifts_npv_one_for_one
- **Assumptions:** Cash flows are certain given the inputs.

### 049. DCF valuation (year-end) — `dcf`

- **Acceptance:** E-eco-049
- **Method / preset:** `dcf_valuation` / `dcf` · **tier** T2 · **level** intermediate
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Discount a declared stream of free cash flows at a declared rate and declared timing (end-of-period, or an explicit mid-year convention), with an optional Gordon-growth terminal value, to an enterprise value.
- **Refuses:** Forecasting the cash flows; choosing the discount rate or growth (declare them, or use wacc and your own inputs); tax computation; real-option or scenario valuation; equity value claims beyond the separate equity_bridge method.
- **Formula (student note):** EV = sum of FCF_t / (1 + r)^t + TV / (1 + r)^n; TV = FCF_n(1 + g) / (r - g).
- **Inputs:** `cashflows`L, `discount_rate`, `terminal_growth` opt, `timing` opt
- **Outputs (method typing):** pv_explicit (currency/2), pv_terminal (currency/2), terminal_value (currency/2), enterprise_value (currency/2), terminal_share (ratio/3), n_periods (count/0), discount_rate (rate/2), terminal_growth (rate/2)
- **Checks:** second_implementation_agrees, value_scales_with_the_cash_flows, a_higher_discount_rate_lowers_the_value, terminal_value_is_gordon_growth_on_the_last_flow, without_terminal_growth_there_is_no_terminal_value, mid_year_convention_raises_the_value
- **Assumptions:** The cash flows and the discount rate are the owner's declared inputs.; The terminal growth rate persists forever and stays below the discount rate.; Under a mid-year convention every flow is assumed to arrive mid-period.

### 050. Break-even point — `breakeven`

- **Acceptance:** E-eco-050
- **Method / preset:** `breakeven` / `breakeven` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** units / **descriptive**
- **Claims:** Units needed to cover fixed cost at a constant unit contribution, with the break-even revenue, contribution margin, margin of safety and target-profit volume when those inputs are declared.
- **Refuses:** Multi-product mix; step-fixed costs; non-linear price or cost; a demand response to the price; tax; financing cost.
- **Formula (student note):** Break-even quantity = fixed cost / (price - variable cost per unit); break-even revenue = quantity x price; margin of safety = expected units - break-even units.
- **Inputs:** `expected_units` opt, `fixed`, `price`, `target_profit` opt, `variable`
- **Outputs (method typing):** breakeven_units (units/2), contribution_margin (currency/2), contribution_margin_ratio (ratio/4), breakeven_revenue (currency/2)
- **Checks:** profit_at_breakeven_is_zero, contribution_margin_is_price_minus_variable, breakeven_revenue_is_units_times_price, margin_of_safety_is_expected_units_minus_breakeven, target_profit_raises_the_required_units
- **Assumptions:** Linear cost and revenue.; The expected volume is the owner's declared input, not a forecast.

### 051. Multi-product break-even — `multibreakeven`

- **Acceptance:** E-eco-051
- **Method / preset:** `multi_product_breakeven` / `multibreakeven` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** units / **descriptive**
- **Claims:** Break-even in units and revenue for a fixed product mix: the mix-weighted contribution margin and the per-product break-even quantities.
- **Refuses:** A changing mix, step costs, capacity limits, price-volume relationships or tax; forecasting which mix will actually occur.
- **Formula (student note):** Weighted contribution = sum(mix weight x unit contribution); break-even units = fixed cost / weighted contribution.
- **Inputs:** `fixed_costs`, `products`R
- **Outputs (method typing):** weighted_contribution (ratio/4), breakeven_total_units (units/2), breakeven_revenue (currency/2), fixed_costs (currency/2), total_mix_units (units/2), units_coffee (units/2), units_cake (units/2)
- **Checks:** second_implementation_agrees, weighted_contribution_is_the_mix_weighted_margin, profit_at_break_even_is_zero, scaling_fixed_costs_scales_break_even_units, per_product_units_sum_to_the_total
- **Assumptions:** Each product's price and variable cost are constant.; The declared mix is the mix that will be sold.; Fixed costs do not change with volume.

### 052. Unit economics — `unitecon`

- **Acceptance:** E-eco-052
- **Method / preset:** `unit_economics` / `unitecon` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** currency / **descriptive**
- **Claims:** Unit contribution margin, payback of the acquisition cost and (when a churn rate is declared) a period-value LTV and LTV/CAC.
- **Refuses:** Estimating churn, retention curves or customer lifetime modelling; discounting LTV to present value; tax, financing or cross-sell; segment-level CAC.
- **Formula (student note):** Contribution margin = price - variable cost; LTV = margin / churn; CAC payback = acquisition cost / margin.
- **Inputs:** `acquisition_cost`, `churn_rate` opt, `price`, `variable_cost`
- **Outputs (method typing):** unit_margin (currency/2), margin_pct (rate/4), payback_periods (ratio/3), price (currency/2), variable_cost (currency/2), acquisition_cost (currency/2), churn_rate (rate/4), ltv (currency/2), ltv_cac (ratio/3)
- **Checks:** second_implementation_agrees, margin_is_price_minus_variable_cost, payback_is_acquisition_cost_over_margin, raising_price_raises_margin_by_the_same_amount, lower_churn_raises_ltv
- **Assumptions:** Prices, costs and churn are the owner's declared inputs.; The unit margin is earned each period until churn.

### 053. Descriptive statistics — `descriptive`

- **Acceptance:** E-eco-053
- **Method / preset:** `descriptive_stats` / `descriptive` · **tier** T1 · **level** intro
- **Row unit / claim ceiling:** from_request / **descriptive**
- **Claims:** Summarize one numeric variable in a dataset (n, missing, mean, median, range, sample SD).
- **Refuses:** Inference (intervals, tests, effect sizes), weighted or clustered survey data, grouped summaries, quartiles.
- **Formula (student note):** Mean = sum of values / count; standard deviation measures typical distance from the mean.
- **Inputs:** `missing_codes`L opt, `values`L
- **Outputs (method typing):** _none_
- **Checks:** second_implementation_agrees, shift_moves_location_not_spread, scale_scales_spread, permutation_invariant, missing_entries_excluded_not_valued, order_statistics_bounded
- **Assumptions:** Observations are numeric and the listed codes fully identify missing values.

### 054. Pearson correlation — `pearson`

- **Acceptance:** E-eco-054
- **Method / preset:** `pearson` / `pearson` · **tier** T1 · **level** intermediate
- **Row unit / claim ceiling:** correlation / **associational**
- **Claims:** Linear association between two numeric variables in a sample, with interval, p-value and effect size.
- **Refuses:** Causal claims; non-linear relationships; clustered, weighted or repeated-measures data; more than two variables.
- **Formula (student note):** r = covariance(x, y) / (standard deviation of x x standard deviation of y).
- **Inputs:** `alpha` opt, `confidence_level` opt, `missing_codes`L opt, `x`L, `y`L
- **Outputs (method typing):** _none_
- **Checks:** second_implementation_agrees, invariant_to_positive_linear_transform, negating_y_flips_sign_keeps_p, symmetric_in_x_and_y, bounded_and_consistent, missing_pairs_excluded_not_valued
- **Assumptions:** Pairs are independent observations.; Relationship is approximately linear.; Approximate normality, screened by skewness and kurtosis only.

### 055. Linear regression — `ols`

- **Acceptance:** E-eco-055
- **Method / preset:** `ols` / `ols` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** Linear association of one numeric outcome with up to five numeric predictors, with intervals, p-values and effect sizes.
- **Refuses:** Causal claims; categorical predictors; interactions; non-linear fits; clustered, weighted or time-series data; prediction beyond the observed range.
- **Formula (student note):** y = intercept + coefficient x x + error; the coefficients minimise the sum of squared errors.
- **Inputs:** `alpha` opt, `confidence_level` opt, `missing_codes`L opt, `predictors`R, `y`L
- **Outputs (method typing):** r_squared (ratio/3), adj_r_squared (ratio/3), f_squared (ratio/3), f_stat (ratio/3), p_f (probability/4), residual_se (coefficient/3), n (count/0), n_excluded (count/0), k (count/0), df_residual (count/0), confidence_level (rate/2), alpha (rate/2), coef_intercept (coefficient/3), se_intercept (coefficient/3), p_intercept (probability/4), ci_lower_intercept (coefficient/3), ci_upper_intercept (coefficient/3), coef_study_hours (coefficient/3), se_study_hours (coefficient/3), p_study_hours (probability/4), ci_lower_study_hours (coefficient/3), ci_upper_study_hours (coefficient/3), std_beta_study_hours (ratio/3), coef_sleep_hours (coefficient/3), se_sleep_hours (coefficient/3), p_sleep_hours (probability/4), ci_lower_sleep_hours (coefficient/3), ci_upper_sleep_hours (coefficient/3), std_beta_sleep_hours (ratio/3)
- **Checks:** second_implementation_agrees, shift_changes_intercept_only, scaling_rescales_coefficients_not_significance, row_order_invariant, incomplete_rows_excluded_not_valued, bounded_and_consistent, cross_check_partial_regression_and_pearson
- **Assumptions:** Observations are independent.; The outcome is approximately linear in the predictors.; Residual variance is constant (screened) or robust errors are used.

### 056. Welch two-sample t-test — `welch`

- **Acceptance:** E-eco-056
- **Method / preset:** `welch_t` / `welch` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** from_request / **associational**
- **Claims:** Compare the means of two independent groups on a numeric outcome, with interval, p-value and standardized effect size.
- **Refuses:** Paired or repeated measures; more than two groups; causal claims; clustered data; proportions or counts.
- **Formula (student note):** t = (mean A - mean B) / standard error of the difference, without assuming equal variances.
- **Inputs:** `alpha` opt, `confidence_level` opt, `groups`R, `missing_codes`L opt
- **Outputs (method typing):** diff (@unit/3), se_diff (@unit/3), ci_lower (@unit/3), ci_upper (@unit/3), t_stat (ratio/3), df (ratio/3), p_value (probability/4), hedges_g (ratio/3), g_ci_lower (ratio/3), g_ci_upper (ratio/3), n_lecture (count/0), mean_lecture (@unit/3), sd_lecture (@unit/3), n_workshop (count/0), mean_workshop (@unit/3), sd_workshop (@unit/3), n_excluded (count/0), confidence_level (rate/2), alpha (rate/2)
- **Checks:** second_implementation_agrees, shift_leaves_difference_inference_unchanged, positive_scale_equivariance, swapping_groups_negates_difference_keeps_p, row_order_invariant, missing_entries_excluded_not_valued, bounded_and_consistent
- **Assumptions:** Observations are independent within and between groups.; Group means are approximately normal (screened by skewness and kurtosis only).

### 057. One-way ANOVA — `anova`

- **Acceptance:** E-eco-057
- **Method / preset:** `anova` / `anova` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** from_request / **associational**
- **Claims:** Compare the means of three or more independent groups with an omnibus F test, an eta-squared effect size and per-group summaries.
- **Refuses:** Repeated measures; two-way or factorial designs; post-hoc pairwise tests; causal claims; fewer than three groups.
- **Formula (student note):** F = between-group variance / within-group variance.
- **Inputs:** `alpha` opt, `groups`R, `missing_codes`L opt
- **Outputs (method typing):** f_stat (ratio/3), df_between (count/0), df_within (count/0), p_value (probability/4), eta_squared (ratio/3), n_groups (count/0), n_total (count/0), n_excluded (count/0), grand_mean (@unit/3), alpha (rate/2), n_lecture (count/0), mean_lecture (@unit/3), sd_lecture (@unit/3), n_workshop (count/0), mean_workshop (@unit/3), sd_workshop (@unit/3), n_online (count/0), mean_online (@unit/3), sd_online (@unit/3)
- **Checks:** second_implementation_agrees, within_group_permutation_invariant, group_relabeling_invariant, equal_shift_leaves_F_and_effect_unchanged, positive_scale_equivariance, missing_entries_excluded_not_valued, bounded_and_consistent
- **Assumptions:** Observations are independent within and between groups.; Group distributions are approximately normal (screened by skewness and kurtosis only).; Group variances are approximately equal (screened by Levene's test).

### 058. Chi-square association — `chi_square`

- **Acceptance:** E-eco-058
- **Method / preset:** `chi_square` / `chi_square` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** ratio / **associational**
- **Claims:** Test whether two categorical variables are independent from a table of observed counts, with a Cramer's V effect size.
- **Refuses:** Goodness of fit; ordered categories; repeated or paired counts; causal claims; tables with small expected counts (blocks).
- **Formula (student note):** Chi-square = sum of (observed - expected)^2 / expected.
- **Inputs:** `alpha` opt, `table`R
- **Outputs (method typing):** chi_squared (ratio/3), df (count/0), p_value (probability/4), cramers_v (ratio/3), n_total (count/0), n_cells (count/0), min_expected_count (count/0), alpha (rate/2)
- **Checks:** second_implementation_agrees, row_order_invariant, transpose_invariant, uniform_scaling_scales_chi2_keeps_V, independence_gives_zero_chi2, bounded_and_consistent
- **Assumptions:** Observations are independent and each is counted in exactly one cell.; Expected counts are large enough (screened; at least 5).

### 059. Power and sample size — `power`

- **Acceptance:** E-eco-059
- **Method / preset:** `power_analysis` / `power` · **tier** T1 · **level** advanced
- **Row unit / claim ceiling:** probability / **descriptive**
- **Claims:** Plan a two-sample or one-sample comparison of means: the power for a stated effect, and the minimum detectable effect at a declared target power, under the normal approximation.
- **Refuses:** Exact power under the noncentral t distribution; proportions or counts; cluster, weighted or repeated-measures designs; multiplicity; treating a high power as a guarantee of significance.
- **Formula (student note):** Power depends on the effect size, alpha, sample size and variability.
- **Inputs:** `alpha` opt, `design`, `effect`, `n1`, `n2` opt, `sd1`, `sd2` opt, `tails` opt, `target_power` opt
- **Outputs (method typing):** power (probability/4), mde (@unit/2), se (@unit/2), ncp (ratio/3), z_alpha (ratio/3), alpha (probability/4), target_power (probability/4), n1 (count/0), n2 (count/0), _appendix (ratio/3), _checks (ratio/3)
- **Checks:** second_implementation_agrees, power_at_zero_effect_equals_alpha, power_increases_with_effect_size, power_increases_with_sample_size, mde_decreases_with_sample_size
- **Assumptions:** Observations are independent within and between groups.; The standard deviations supplied are the planning values and are positive.; A single test at the declared alpha, with the declared number of tails.

## 4. Worksheets and framework profiles

**None.** `subjects.detail("economics")["worksheets"]` is empty (0), every tile's
`worksheets` list is empty, and no economics record names a `template`. The shelf is
arithmetic only; `does_not` says so and the student guide repeats it. This is a declared
scope statement (`CURRICULUM_MAP.md` places this shelf's coverage entirely in tools), not
a missing feature, and no E-row promises a paper from this shelf.

## 5. Records, theories and glossary

### 5.1 Catalogue records (5)

| id | name | type | form | template | linked methods | declared status |
|---|---|---|---|---|---|---|
| `QNT-FIN-07` | Pricing and demand | Q | computed | — | `pricing_decision`, `elasticity` | Computed |
| `QNT-EVL-01` | Cost–benefit and cost-effectiveness calculations | Q | computed | — | `cost_benefit`, `cost_effectiveness` | Computed |
| `QNT-EVL-02` | Discounting of costs and benefits, sensitivity to valuation assumptions | Q | computed | — | `npv`, `dcf_valuation` | Computed |
| `QNT-EVL-03` | Difference-in-differences and other impact-estimation methods when assumptions and data support them | Q | computed | — | `difference_in_differences` | Computed |
| `QNT-EVL-05` | SROI-type estimates only with transparent attribution, deadweight, displacement, drop-off and monetization assumptions | Q | computed | — | `sroi` | Computed |

Every record is read-only catalogue material: `template` is `None` for all five and each
links only methods that exist. A record naming a worksheet the engine does not have, or a
method absent from `LIBRARY`, is a defect (E-eco-070).

- **QNT-FIN-07 Pricing and demand** — partial: cost-plus, target-margin, break-even and target-return prices are implemented, together with arc price elasticity between two observations; estimating a demand curve or willingness to pay is not implemented
- **QNT-EVL-01 Cost–benefit and cost-effectiveness calculations** — partial: discounted cost-benefit (net present value and benefit-cost ratio) and cost-effectiveness (cost per unit of effect, incremental ratios and dominance) are implemented; non-market valuation, distributional weights and unmonetised effects are not implemented
- **QNT-EVL-02 Discounting of costs and benefits, sensitivity to valuation assumptions** — partial: discounting of declared costs and benefits at a declared rate, with low/high-rate sensitivity, is implemented; a probabilistic sensitivity analysis over every valuation assumption is not implemented
- **QNT-EVL-03 Difference-in-differences and other impact-estimation methods when assumptions and data support them** — partial: a two-group, two-period difference-in-differences estimate with its standard error is implemented; parallel trends cannot be proven from the data, and staggered adoption, covariates and clustering are not implemented
- **QNT-EVL-05 SROI-type estimates only with transparent attribution, deadweight, displacement, drop-off and monetization assumptions** — partial: a social return on investment ratio from declared benefits, investment and attribution inputs is implemented; deadweight, displacement and drop-off must be declared, and the result is assumption-sensitive

### 5.2 Theories (0)

None on this shelf; the reading lenses live on Research & statistics.

### 5.3 Glossary (25 terms)

| term | definition |
|---|---|
| P* | The equilibrium price, where quantity demanded equals quantity supplied. |
| Q* | The equilibrium quantity traded at P*. |
| CS | Consumer surplus: the area below the demand curve and above the price. |
| PS | Producer surplus: the area above the supply curve and below the price. |
| DWL | Deadweight loss: the surplus lost when the quantity traded is not the efficient quantity. |
| E | Price elasticity of demand: the percentage change in quantity divided by the percentage change in price. |
| Pc / Ps | The consumer price and the producer price when a tax drives a wedge between them. |
| HHI | Herfindahl-Hirschman index: the sum of squared percentage market shares, from 0 to 10,000. |
| CR4 | The combined market share of the four largest firms. |
| GDP | Gross domestic product: the market value of final goods and services produced inside a country in a period. |
| GNP / NNP | Gross national product adds net factor income from abroad; net national product subtracts depreciation. |
| CPI | Consumer price index: the cost of a fixed basket relative to a base period, usually scaled to 100. |
| CAGR | Compound annual growth rate: the constant yearly rate that turns the start value into the end value. |
| LFPR | Labour-force participation rate: the labour force divided by the working-age population. |
| MPC | Marginal propensity to consume: the fraction of an extra unit of income spent on consumption. |
| Debt-to-GDP | The debt stock divided by nominal GDP; the standard scale for comparing debt across economies. |
| Pigouvian tax | A tax equal to the marginal external cost at the social optimum. |
| Gini coefficient | An inequality index between zero (perfect equality) and one (one person has all income). |
| HDI | Human Development Index: the geometric mean of life, education and income indices. |
| PPP | Purchasing-power parity: the exchange rate that equalises the cost of a basket across countries. |
| IRP | Interest-rate parity: the forward rate implied by the two countries' interest rates. |
| BoP | Balance of payments: the current, capital and financial accounts, which add to zero. |
| DiD | Difference-in-differences: the treated change minus the control change. |
| Nash equilibrium | A cell where neither player can gain by switching strategy alone. |
| Cournot | Quantity competition in which each firm best-responds to the other's output. |

### 5.4 Tiles (8)

| key | label | tools | worksheets |
|---|---|---|---|
| `market_basics` | Market basics | 5 | — |
| `firm_behaviour` | Firm behaviour | 6 | — |
| `macroeconomics` | Macroeconomics | 8 | — |
| `welfare_policy` | Welfare and policy | 7 | — |
| `international` | International economics | 6 | — |
| `behavioural_evidence` | Behavioural and evidence | 8 | — |
| `impact_evaluation` | Impact evaluation | 2 | — |
| `quantitative_core` | Quantitative core | 17 | — |

The tile-level `need` text tells the student what to gather for the whole group. The
per-tool `need` is present for only 7 of 59 tools (`TOOL_NEEDS` carries `npv`, `forecast`,
`descriptive`, `pearson`, `ols`, `chi_square`, `power`); the other 52 tool cards render
without a *what you need* line — ledgered `G-eco-01` and tested as a fallback, never
faked (E-eco-080).

## 6. Student guidance

Source of truth rank 5 (`subjects.detail("economics")`) and rank 6 (the guide).

**Shelf guidance** (rendered at the top of the page):

> Start with the level you are working at. Intro tools cover the first principles: demand and
> supply, elasticity, tax incidence, price controls and market concentration. Intermediate tools
> cover welfare, policy, international trade and behavioural questions. Advanced tools are
> econometrics and game theory; use them only when you have the data and the design. Every curve,
> rate and income is one you declare.

**Start steps (5)** — the "where do I begin" list:

1. A market question: Market equilibrium, then Elasticity, Tax incidence or Price ceilings and floors.
2. A national or policy question: GDP and national income, Inflation and real interest, Unemployment and participation, then the money or fiscal multiplier.
3. A welfare or inequality question: Externalities and Pigouvian tax, Public goods, Social welfare, Gini coefficient and Poverty measures.
4. An international question: Comparative advantage, Tariff welfare, Purchasing-power parity and Interest-rate parity.
5. An evidence question: use the Advanced econometrics tools only when the data and design are declared.

**Does-not list (3)** — see §2.

**Per tool** the catalogue promises five things, each tested in §8 (E-eco-068): a `level`, a
`formula`, ≥3 `steps`, ≥3 `common_mistakes`, and a `related` list that resolves (E-eco-069).
The sixth promise, the per-tool `need` line, is only partly delivered — ledgered `G-eco-01`.

**Conventions the guide pins**, each with a test:

| Convention (guide) | Test |
|---|---|
| Demand `Qd = a - bP`, supply `Qs = c + dP`, both slopes positive | E-eco-001 |
| Elasticity is the arc (midpoint) formula and is symmetric in the two observations | E-eco-077 |
| A per-unit tax splits by the slopes, not by who hands it over | E-eco-003 |
| A ceiling binds only below equilibrium, a floor only above; the short side trades | E-eco-078 |
| HHI uses percentage shares (0–10,000); CR4 is the four largest shares | E-eco-079 |
| `TC = fixed + linear·Q + quadratic·Q²`; `MC` is the derivative, `AC = TC/Q` | E-eco-006 |
| GDP is `C + I + G + X − M`; GNP adds net factor income; NNP subtracts depreciation | E-eco-008 |
| Inflation is the CPI percentage change; the real rate uses the exact Fisher relation | E-eco-076 |
| Unemployment divides by the labour force; participation and employment ratios by the working-age population | E-eco-075 |
| Simple money multiplier `1 / reserve ratio`; fiscal multiplier `1 / (1 − MPC(1 − t))` | E-eco-012, E-eco-013 |
| Debt ratio is debt over GDP; its change uses the interest-growth-primary identity | E-eco-014 |

## 7. Surface routing

The shelf is one page: `GET /api/cases/subjects/economics` returns the catalogue surface
(`subjects.detail("economics")`), and the served page renders it.

| Surface | What it opens | Served by |
|---|---|---|
| Eight tiles (`market_basics`, `firm_behaviour`, `macroeconomics`, `welfare_policy`, `international`, `behavioural_evidence`, `impact_evaluation`, `quantitative_core`) | the tools of that group | `web/index.html` tile rail, from `ECONOMICS_TILES` |
| A tool tile | its calculator form, built from the method's `input_schema` | `activate(<preset>)` — never `show(...)` |
| The `related` line under a tool | a plain text list of related tool ids (not hyperlinks) | page template; 151 ids, all resolving (E-eco-069) |
| Run a tool | `POST /api/sessions {objective, method, inputs}` → `POST /api/sessions/{id}/confirm {}` → `GET /api/sessions/{id}` | `bp.server` preset path |
| A result | the delivery report + appendix (checks) + the declared formats | `deliverables.write_export` |
| The glossary | the 25 declared terms | page glossary panel |

No worksheet, drafting form, framework paper or catalogue-record page is served from this shelf,
because none exists (§4, §5.1). The `related` line is text, not navigation — asserted as such
rather than assumed to be a link.


**This shelf has no worksheets, no framework profiles and no theories** — `worksheets: 0`,
`theories: 0` on the catalogue surface, and no record on the shelf names a `template`. Work
order §4 (worksheets/framework profiles) therefore has no row to fill for economics, and §10 of
this document records that as a deliberate scope statement, not an omission.


## 8. Expected behaviour — `E-eco-nnn`

Atomic and testable, one line each. The **test** column names the enforcing test in
`tests/test_subject_economics_acceptance.py`; `—` means no test exists, and then the row must be
`BLOCKED` or `GAP` (§9) with a ledger id. `§3` points at the tool's own row.

### 8.1 One row per compute tool (59)

Each row means, in one test: the preset launches that method, the preset's own inputs pass
validation, the pipeline reaches `delivered`, every check the method declares passes, two runs are
identical, and the outputs carry the units listed in §3.

| id | statement | source | test | status |
|---|---|---|---|---|
| E-eco-001 | `equilibrium` runs from preset `equilibrium`; P*, Q*, CS, PS and total surplus are 20, 60, 900, 900, 1800 on the guide's curves | rank 1 + guide §1 | `test_E_eco_001__equilibrium_runs_from_its_preset` | PASS |
| E-eco-002 | `elasticity` runs from its preset and returns the arc elasticity −1.5 with a revenue rise of 120 | rank 1 + guide §2 | `test_E_eco_002__elasticity_runs_from_its_preset` | PASS |
| E-eco-003 | `taxincidence` runs from its preset; Pc 23, Ps 17, Qt 54, revenue 324, DWL 18 | rank 1 + guide §3 | `test_E_eco_003__taxincidence_runs_from_its_preset` | PASS |
| E-eco-004 | `pricecontrol` runs from its preset; a ceiling at 15 gives shortage 20, Q traded 50, DWL 50 | rank 1 + guide §4 | `test_E_eco_004__pricecontrol_runs_from_its_preset` | PASS |
| E-eco-005 | `concentration` runs from its preset; HHI 2,650, CR4 90, effective firms 10,000/HHI | rank 1 + guide §5 | `test_E_eco_005__concentration_runs_from_its_preset` | PASS |
| E-eco-006 | `costcurves` runs from its preset; TC 1,400, AC 70, AVC 20, AFC 50, MC 30 at Q=20 | rank 1 + guide §6 | `test_E_eco_006__costcurves_runs_from_its_preset` | PASS |
| E-eco-007 | `profitmax` runs from its preset; MR=MC at Q 18, P 64, profit 710, Lerner 0.5625 | rank 1 + guide §7 | `test_E_eco_007__profitmax_runs_from_its_preset` | PASS |
| E-eco-008 | `marketpower` runs from its preset and reports markup and the Lerner index | rank 1 | `test_E_eco_008__marketpower_runs_from_its_preset` | PASS |
| E-eco-009 | `pricediscrimination` runs from its preset; MR=MC in each of two separable markets | rank 1 | `test_E_eco_009__pricediscrimination_runs_from_its_preset` | PASS |
| E-eco-010 | `cournot` runs from its preset; q 16.67/11.67, P 43.33, profits 555.56/272.22 | rank 1 + guide §16 | `test_E_eco_010__cournot_runs_from_its_preset` | PASS |
| E-eco-011 | `nash` runs from its preset and flags every pure-strategy equilibrium | rank 1 | `test_E_eco_011__nash_runs_from_its_preset` | PASS |
| E-eco-012 | `panel` runs from its preset; the within slope is the within covariance over variance | rank 1 + guide §17 | `test_E_eco_012__panel_runs_from_its_preset` | PASS |
| E-eco-013 | `iv` runs from its preset; the IV slope is the covariance ratio, OLS reported beside it | rank 1 + guide §17 | `test_E_eco_013__iv_runs_from_its_preset` | PASS |
| E-eco-014 | `rdd` runs from its preset; the estimate is the right minus the left intercept | rank 1 + guide §17 | `test_E_eco_014__rdd_runs_from_its_preset` | PASS |
| E-eco-015 | `probit` runs from its preset with a latent slope and a marginal effect at the mean | rank 1 + guide §17 | `test_E_eco_015__probit_runs_from_its_preset` | PASS |
| E-eco-016 | `nationalincome` runs from its preset; GDP 900, GNP 920, NNP 870, real 750, per capita 9 | rank 1 + guide §8 | `test_E_eco_016__nationalincome_runs_from_its_preset` | PASS |
| E-eco-017 | `growth` runs from its preset; 100→200 over 10 periods is 100% total and a 7.18% CAGR | rank 1 + guide §9 | `test_E_eco_017__growth_runs_from_its_preset` | PASS |
| E-eco-018 | `inflation` runs from its preset; CPI 120→126 is 5% and the real rate 1.90% | rank 1 + guide §9 | `test_E_eco_018__inflation_runs_from_its_preset` | PASS |
| E-eco-019 | `unemployment` runs from its preset; 10% unemployment, 62.5% participation, 56.25% employment ratio | rank 1 + guide §11 | `test_E_eco_019__unemployment_runs_from_its_preset` | PASS |
| E-eco-021 | `fiscal` runs from its preset; the multiplier is 2.5 and the output change 200 | rank 1 + guide §13 | `test_E_eco_021__fiscal_runs_from_its_preset` | PASS |
| E-eco-022 | `budgetdebt` runs from its preset; overall −50, primary −30, debt ratio 50% | rank 1 + guide §14 | `test_E_eco_022__budgetdebt_runs_from_its_preset` | PASS |
| E-eco-023 | `okun` runs from its preset and links the output gap to the unemployment gap by the declared coefficient | rank 1 | `test_E_eco_023__okun_runs_from_its_preset` | PASS |
| E-eco-024 | `externality` runs from its preset; social quantity 56, Pigouvian tax 4, DWL 8 | rank 1 + guide §12 | `test_E_eco_024__externality_runs_from_its_preset` | PASS |
| E-eco-025 | `publicgood` runs from its preset and satisfies the Samuelson condition on the declared schedules | rank 1 | `test_E_eco_025__publicgood_runs_from_its_preset` | PASS |
| E-eco-026 | `socialwelfare` runs from its preset; utilitarian = sum, Rawlsian = min, Nash = geometric mean | rank 1 | `test_E_eco_026__socialwelfare_runs_from_its_preset` | PASS |
| E-eco-027 | `gini` runs from its preset; incomes 10/20/30/40 give a Gini of 0.25 and a mean of 25 | rank 1 + guide §12 | `test_E_eco_027__gini_runs_from_its_preset` | PASS |
| E-eco-028 | `poverty` runs from its preset; a line at 25 gives a 50% headcount and a 20% average gap | rank 1 + guide §12 | `test_E_eco_028__poverty_runs_from_its_preset` | PASS |
| E-eco-029 | `taxprogressivity` runs from its preset and reports progressivity from declared incomes and taxes | rank 1 | `test_E_eco_029__taxprogressivity_runs_from_its_preset` | PASS |
| E-eco-030 | `optimalpollution` runs from its preset; marginal abatement equals marginal damage at the optimum | rank 1 | `test_E_eco_030__optimalpollution_runs_from_its_preset` | PASS |
| E-eco-031 | `comparative` runs from its preset; opportunity costs 2 and 1.67 make B the good-one specialist | rank 1 + guide §13 | `test_E_eco_031__comparative_runs_from_its_preset` | PASS |
| E-eco-032 | `tariff` runs from its preset; domestic price 15, imports 40→20, revenue 100, total DWL 50 | rank 1 + guide §13 | `test_E_eco_032__tariff_runs_from_its_preset` | PASS |
| E-eco-033 | `ppp` runs from its preset; PPP 50 and a real rate of 1.1 (10% above PPP) | rank 1 + guide §14 | `test_E_eco_033__ppp_runs_from_its_preset` | PASS |
| E-eco-034 | `irp` runs from its preset; spot 50 at 6%/4% over one year gives an implied forward of 50.9615 | rank 1 + guide §14 | `test_E_eco_034__irp_runs_from_its_preset` | PASS |
| E-eco-035 | `bop` runs from its preset and checks that the declared accounts add up, not that the data are right | rank 1 | `test_E_eco_035__bop_runs_from_its_preset` | PASS |
| E-eco-036 | `hdi` runs from its preset and reports the three sub-indices and their geometric mean | rank 1 | `test_E_eco_036__hdi_runs_from_its_preset` | PASS |
| E-eco-037 | `expectedutility` runs from its preset; a 50/50 gamble of 50/150 at CRRA 2 gives EV 100, EU −0.01333, CE 75, RP 25 | rank 1 + guide §15 | `test_E_eco_037__expectedutility_runs_from_its_preset` | PASS |
| E-eco-038 | `prospect` runs from its preset and values the same gamble around −19.54 at the default parameters | rank 1 + guide §15 | `test_E_eco_038__prospect_runs_from_its_preset` | PASS |
| E-eco-039 | `labour` runs from its preset and deflates the declared nominal wage by the declared CPI | rank 1 + guide §Conventions | `test_E_eco_039__labour_runs_from_its_preset` | PASS |
| E-eco-040 | `did` runs from its preset; the estimate is (treated post − pre) − (control post − pre) | rank 1 | `test_E_eco_040__did_runs_from_its_preset` | PASS |
| E-eco-041 | `forecast` runs from its preset; the confidence level and horizon are declared and reported | rank 1 | `test_E_eco_041__forecast_runs_from_its_preset` | PASS |
| E-eco-042 | `currency` runs from its preset; 1,000 USD at 0.92 is 920 EUR and the appendix records the declared provenance | rank 1 | `test_E_eco_042__currency_runs_from_its_preset` | PASS |
| E-eco-043 | `pricing` runs from its preset; cost-plus, target-margin, target-return and break-even prices are reported | rank 1 | `test_E_eco_043__pricing_runs_from_its_preset` | PASS |
| E-eco-044 | `demandcurve` runs from its preset and fits the declared price-quantity observations | rank 1 | `test_E_eco_044__demandcurve_runs_from_its_preset` | PASS |
| E-eco-045 | `cba` runs from its preset; NPV = PV(benefits) − PV(costs) and BCR = benefits / costs | rank 1 | `test_E_eco_045__cba_runs_from_its_preset` | PASS |
| E-eco-046 | `cea` runs from its preset; each ratio is against the first-listed comparator and a dominant option gets a flag, not a ratio | rank 1 | `test_E_eco_046__cea_runs_from_its_preset` | PASS |
| E-eco-047 | `sroi` runs from its preset; the ratio is the discounted benefit over the declared investment | rank 1 | `test_E_eco_047__sroi_runs_from_its_preset` | PASS |
| E-eco-048 | `npv` runs from its preset and discounts each declared cash flow at the declared rate | rank 1 | `test_E_eco_048__npv_runs_from_its_preset` | PASS |
| E-eco-049 | `dcf` runs from its preset with the declared terminal growth and timing convention | rank 1 | `test_E_eco_049__dcf_runs_from_its_preset` | PASS |
| E-eco-050 | `breakeven` runs from its preset; volume is (fixed + target profit) / (price − variable) | rank 1 | `test_E_eco_050__breakeven_runs_from_its_preset` | PASS |
| E-eco-051 | `multibreakeven` runs from its preset and uses the declared product mix | rank 1 | `test_E_eco_051__multibreakeven_runs_from_its_preset` | PASS |
| E-eco-052 | `unitecon` runs from its preset; unit margin, LTV, LTV/CAC and payback are reported | rank 1 | `test_E_eco_052__unitecon_runs_from_its_preset` | PASS |
| E-eco-053 | `descriptive` runs from its preset and excludes declared missing codes listwise, saying so | rank 1 | `test_E_eco_053__descriptive_runs_from_its_preset` | PASS |
| E-eco-054 | `pearson` runs from its preset with n, r, r², a confidence interval and its claim ceiling | rank 1 | `test_E_eco_054__pearson_runs_from_its_preset` | PASS |
| E-eco-055 | `ols` runs from its preset with the declared predictors and reports coefficients with a coefficient unit | rank 1 | `test_E_eco_055__ols_runs_from_its_preset` | PASS |
| E-eco-056 | `welch` runs from its preset and compares two declared groups | rank 1 | `test_E_eco_056__welch_runs_from_its_preset` | PASS |
| E-eco-057 | `anova` runs from its preset over three or more declared groups | rank 1 | `test_E_eco_057__anova_runs_from_its_preset` | PASS |
| E-eco-058 | `chi_square` runs from its preset on a declared two-way table of counts | rank 1 | `test_E_eco_058__chi_square_runs_from_its_preset` | PASS |
| E-eco-059 | `power` runs from its preset with a declared design, effect, alpha and target power | rank 1 | `test_E_eco_059__power_runs_from_its_preset` | PASS |

### 8.2 Cross-cutting behaviour

| id | statement | source | test | status |
|---|---|---|---|---|
| E-eco-060 | A delivered economics report contains no raw multi-digit Decimal and no scientific notation: every figure prints at its declared precision | manual §4.1; session-1 D-ACC-01/04 class | `test_E_eco_060__no_report_prints_a_raw_decimal_or_scientific_notation` | PASS |
| E-eco-061 | No delivered economics report carries an unresolved template token (`{{ref:`, `@unit`) | manual §4.1 | `test_E_eco_061__no_report_carries_an_unresolved_template_token` | PASS |
| E-eco-062 | Identical inputs produce an identical row, and the row is JSON-round-trip stable | determinism (manual §7) | `test_E_eco_062__computations_are_deterministic_and_json_stable` | PASS |
| E-eco-063 | Each method's `tests()` returns exactly its declared `test_names`, in order, all true on valid input | rank 1 | `test_E_eco_063__every_method_reports_its_declared_checks_and_they_pass` | PASS |
| E-eco-064 | Every economics method declares a complete contract: non-empty intended use, unsupported use, assumptions, limitations, ≥3 checks, metric, unit, a valid tier and a valid claim ceiling | rank 1 (`Method`) | `test_E_eco_064__every_method_contract_is_complete` | PASS |
| E-eco-065 | Every tool's preset exists and launches that tool's method; the tool set and the preset set agree | rank 1 + `server.PRESETS` | `test_E_eco_065__every_preset_launches_the_method_it_claims` | PASS |
| E-eco-066 | No method is claimed by two economics tools, and no tool carries an empty key, label, formula or group | rank 5 | `test_E_eco_066__the_catalogue_has_no_duplicate_or_empty_tool_row` | PASS |
| E-eco-067 | Every tool declares a level in {intro, intermediate, advanced}; the split is 23 / 23 / 13 as `scripts/econ_shelf.py --check` prints | rank 5 + shelf audit | `test_E_eco_067__levels_are_declared_and_split_23_23_13` | PASS |
| E-eco-068 | Every tool carries a formula, ≥3 steps and ≥3 common mistakes | rank 5 | `test_E_eco_068__every_tool_carries_formula_steps_and_mistakes` | PASS |
| E-eco-069 | Every `related` id resolves to a built tool on some shelf; the page renders them as text, not links | rank 5 + `web/index.html` | `test_E_eco_069__every_related_id_resolves_to_a_built_tool` | PASS |
| E-eco-070 | The five catalogue records link only methods that exist and name no worksheet template | `test_catalogue_truth` class | `test_E_eco_070__records_link_only_built_methods` | PASS |
| E-eco-071 | The glossary carries 25 terms, each with a non-empty definition, and no term repeats | rank 5 | `test_E_eco_071__the_glossary_is_complete_and_has_no_duplicates` | PASS |
| E-eco-072 | The eight tiles partition the 59 tools exactly: every tool appears once and its `group` names its tile | rank 5 | `test_E_eco_072__the_tiles_partition_the_tool_set` | PASS |
| E-eco-073 | The shelf declares five start steps and three does-not statements, all non-empty | rank 5 | `test_E_eco_073__start_steps_and_does_not_are_declared` | PASS |
| E-eco-074 | Every worked example reproduced from the student guide matches the guide's own figure | rank 6 | `test_E_eco_074__the_student_guide_examples_reproduce` | PASS |
| E-eco-075 | The unemployment rate divides by the labour force; participation and the employment ratio divide by the working-age population | guide §Conventions | `test_E_eco_075__labour_ratios_use_the_declared_denominators` | PASS |
| E-eco-076 | The real interest rate uses the exact Fisher relation and also reports the nominal-minus-inflation approximation | guide §Conventions | `test_E_eco_076__the_real_rate_is_the_fisher_relation` | PASS |
| E-eco-077 | Arc elasticity is unchanged when the two observations are swapped | rank 1 check list | `test_E_eco_077__arc_elasticity_is_symmetric` | PASS |
| E-eco-078 | A ceiling binds only below equilibrium and a floor only above; the short side sets quantity traded | guide §Conventions | `test_E_eco_078__a_non_binding_control_changes_nothing` | PASS |
| E-eco-079 | HHI uses percentage shares and runs from 0 to 10,000; CR4 sums the four largest shares | guide §Conventions | `test_E_eco_079__hhi_uses_percentage_shares` | PASS |
| E-eco-080 | A tool with no `need` text still renders through the documented fallback, and the absence is ledgered `G-eco-01` rather than invented | session-1 precedent D-ACC-10 | `test_E_eco_080__a_missing_need_line_falls_back_and_is_ledgered` | PASS |
| E-eco-081 | `labour_market` types `wage_share_of_productivity` and `labour_market_tightness` as a ratio and `vacancies` as a count, never as currency | guide §Conventions; rank 1 `typing()` | `test_E_eco_081__a_share_and_a_count_are_not_typed_as_money` | PASS (B-190) |
| E-eco-082 | Labour-market tightness is vacancies per unemployed person, with the denominator declared, not vacancies divided by the unemployment *rate* | `OPEN_ISSUES.md` 11b; standard definition | — | **BLOCKED** D-ECO-02 |
| E-eco-083 | A currency conversion never labels the source amount with the target currency, and points at the appendix for both amounts and both codes | `POST /api/sessions` deliverable; rank 1 template | `test_E_eco_083__the_conversion_never_mislabels_the_source_amount` | PASS (B-190) |
| E-eco-084 | `docs/CURRICULUM_MAP.md` states this shelf's true tool count (59), not a stale 55 | docs-sync rule; measured catalogue | `test_E_eco_084__the_curriculum_map_states_the_true_tool_count` | PASS |



| E-eco-020 | `moneymultiplier` runs from its preset; the simple multiplier is 1/0.20 = 5 | rank 1 + guide §12 | `test_E_eco_020__moneymultiplier_runs_from_its_preset` | PASS |


## 9. Traceability — the session scoreboard

| Status | Rows | Meaning |
|---|---:|---|
| PASS | 83 | enforced by a test in `tests/test_subject_economics_acceptance.py` |
| BLOCKED | 1 | E-eco-082 — needs an owner modelling decision on the tightness denominator (D-ECO-02) |
| DISPUTED | 0 | the code and the docs agree everywhere else |

84 rows in total. E-eco-081 and E-eco-083 were BLOCKED and are now PASS under the owner-approved
unfreeze **B-190** (two fixes in `src/bp/methods.py`, each with its trap test). One PASS row
(E-eco-080) also records a **GAP**: `G-eco-01`, the 52 tool cards with no per-tool `need` line, is
not built — the test asserts the documented fallback, not the missing feature.



Reconciliation against the catalogue (`GET /api/cases/subjects/economics`): **59 tools → 59 rows
(E-eco-001…059)**, **0 worksheets → 0 rows**, **5 records → 1 row (E-eco-070) + §5.1 detail**,
**0 theories → 0 rows**, **25 glossary terms → 1 row (E-eco-071)**, **8 tiles → 1 row
(E-eco-072)**, **3 does-not + 5 start steps → 1 row (E-eco-073)**, plus 25 cross-cutting rows.

**Existing tests that already covered this shelf** (re-run, never weakened):
`test_economics.py`, `test_economics_remaining.py`, `test_macroeconomics.py`,
`test_appraisal.py`, `test_power.py`, `test_market_panels.py`, `test_method_contracts.py`,
`test_catalogue_truth.py`, `test_honesty.py`, `test_frozen_contract.py`. At the baseline commit
all pass; no economics-shelf test appears in the 79-item failure list.

## 10. Known gaps, disputes and blocked items

| Ref | Item | Declared / decided by | Ledger |
|---|---|---|---|
| `G-eco-01` | 52 of 59 tool cards have no per-tool *what you need* line; the tile-level `need` covers the group | measured against `TOOL_NEEDS`; session-1 precedent | D-ECO-04 (GAP) |
| `G-eco-02` | No worksheets, frameworks or theories on this shelf | `CURRICULUM_MAP.md`; `does_not` | D-ECO-05 (GAP) |
| `G-eco-03` | VAR, cointegration, unit-root tests not built | `PARKED_QUEUE.md` item 7 | D-ECO-06 (GAP) |
| `G-eco-04` | The diagram renderer and the economics catalogue section are not built | `ECONOMICS_STUDENT_GUIDE.md` "Not covered yet" | D-ECO-07 (GAP) |
| `D-ECO-01` | `labour_market` types a share and a tightness ratio as currency | frozen core (B-079) | BLOCKED — needs owner unfreeze |
| `D-ECO-02` | Tightness divides by the unemployment *rate*, not the unemployed count | `OPEN_ISSUES.md` 11b; frozen core | BLOCKED — needs owner unfreeze |
| `D-ECO-03` | `currency_convert`'s template labels the source amount with the target currency | frozen core template | BLOCKED — needs owner unfreeze |
| `D-ECO-08` | `docs/CURRICULUM_MAP.md` said 55 tools; the catalogue has 59 | docs drift | **FIXED** in this session |

A declared gap is not a bug and is not converted into an expectation. The three `BLOCKED` rows are
reproduced with numbers in `qa/QA_DEFECTS.md` and are deliberately **not** encoded as failing
tests: a red suite would hide the next real regression.
