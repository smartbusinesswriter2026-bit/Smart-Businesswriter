## guidance

Start with the level you are working at. Intro tools cover the first principles: demand and supply, elasticity, tax incidence, price controls and market concentration. Intermediate tools cover welfare, policy, international trade and behavioural questions. Advanced tools are econometrics and game theory; use them only when you have the data and the design. Every curve, rate and income is one you declare.

## start_steps

- A market question: Market equilibrium, then Elasticity, Tax incidence or Price ceilings and floors.
- A national or policy question: GDP and national income, Inflation and real interest, Unemployment and participation, then the money or fiscal multiplier.
- A welfare or inequality question: Externalities and Pigouvian tax, Public goods, Social welfare, Gini coefficient and Poverty measures.
- An international question: Comparative advantage, Tariff welfare, Purchasing-power parity and Interest-rate parity.
- An evidence question: use the Advanced econometrics tools only when the data and design are declared.

## does_not

- It does not retrieve GDP, CPI, market or household data; you declare every input.
- It does not estimate a demand curve, a model or a causal effect from raw data.
- It does not make a policy recommendation or prove that one policy is better.

## disciplines

- microeconomics
- macroeconomics
- welfare and public economics
- international economics
- development economics
- behavioural economics
- industrial organization
- labour economics
- public, nonprofit and impact evaluation
- program and impact evaluation

## discipline_labels

- microeconomics
- macroeconomics
- welfare and public economics
- international economics
- development economics
- behavioural economics
- industrial organization
- labour economics
- public, nonprofit and impact evaluation
- program and impact evaluation

## tiles

| key | label | what | need | worksheets | tools |
|---|---|---|---|---|---|
| `market_basics` | Market basics | Equilibrium price and quantity, price elasticity, tax incidence, price controls and market concentration. | The demand and supply curves, or two price-quantity observations for elasticity. | - | 5 |
| `firm_behaviour` | Firm behaviour | Cost curves, profit maximisation, markup and Lerner index, price discrimination, Cournot and Nash equilibrium. | A cost function and demand curve, or a price and marginal cost for markup. | - | 6 |
| `macroeconomics` | Macroeconomics | GDP and national income, growth and CAGR, inflation and real interest, unemployment, money and fiscal multipliers, budget and debt, Okun's law. | The expenditure components for GDP, two values and periods for growth, two CPI values for inflation. | - | 8 |
| `welfare_policy` | Welfare and policy | Externalities and Pigouvian tax, public goods, social welfare functions, Gini coefficient, poverty measures, tax progressivity, optimal pollution. | Incomes for inequality and poverty, benefit schedules for public goods, damage and abatement for externalities. | - | 7 |
| `international` | International economics | Comparative advantage, tariff welfare, purchasing-power parity, interest-rate parity, balance of payments, Human Development Index. | Unit labour requirements for comparative advantage, a tariff rate, two interest rates for interest-rate parity. | - | 6 |
| `behavioural_evidence` | Behavioural and evidence | Expected utility, prospect theory, labour market, difference-in-differences, instrumental variables, panel regression, regression discontinuity, probit. | A gamble for prospect theory, four means for difference-in-differences, an instrument and endogenous variable for IV. | - | 8 |
| `impact_evaluation` | Impact evaluation | Trend forecast and currency conversion. | Your own series for the trend forecast, and an amount plus a declared rate for currency conversion. | - | 2 |
| `quantitative_core` | Quantitative core | Pricing and demand, cost-benefit and cost-effectiveness, discounting, social return on investment, difference-in-differences, break-even, multi-product break-even, unit economics, descriptive statistics, Pearson correlation, linear regression, Welch t-test, one-way ANOVA, chi-square, power analysis. | Price, variable and fixed cost for pricing and break-even; costs and benefits per period for cost-benefit; options with cost and effect for cost-effectiveness; investment and benefits for SROI; two-period group means for difference-in-differences; observations for statistics; two groups for t-test; three groups for ANOVA. | - | 17 |

## records

| id | name | type | form | template | linked methods | status |
|---|---|---|---|---|---|---|
| `QNT-FIN-07` | Pricing and demand | Q | computed | - | pricing_decision, elasticity | Computed |
| `QNT-EVL-01` | Cost–benefit and cost-effectiveness calculations | Q | computed | - | cost_benefit, cost_effectiveness | Computed |
| `QNT-EVL-02` | Discounting of costs and benefits, sensitivity to valuation assumptions | Q | computed | - | npv, dcf_valuation | Computed |
| `QNT-EVL-03` | Difference-in-differences and other impact-estimation methods when assumptions and data support them | Q | computed | - | difference_in_differences | Computed |
| `QNT-EVL-05` | SROI-type estimates only with transparent attribution, deadweight, displacement, drop-off and monetization assumptions | Q | computed | - | sroi | Computed |

**QNT-FIN-07 Pricing and demand** — partial: cost-plus, target-margin, break-even and target-return prices are implemented, together with arc price elasticity between two observations; estimating a demand curve or willingness to pay is not implemented

**QNT-EVL-01 Cost–benefit and cost-effectiveness calculations** — partial: discounted cost-benefit (net present value and benefit-cost ratio) and cost-effectiveness (cost per unit of effect, incremental ratios and dominance) are implemented; non-market valuation, distributional weights and unmonetised effects are not implemented

**QNT-EVL-02 Discounting of costs and benefits, sensitivity to valuation assumptions** — partial: discounting of declared costs and benefits at a declared rate, with low/high-rate sensitivity, is implemented; a probabilistic sensitivity analysis over every valuation assumption is not implemented

**QNT-EVL-03 Difference-in-differences and other impact-estimation methods when assumptions and data support them** — partial: a two-group, two-period difference-in-differences estimate with its standard error is implemented; parallel trends cannot be proven from the data, and staggered adoption, covariates and clustering are not implemented

**QNT-EVL-05 SROI-type estimates only with transparent attribution, deadweight, displacement, drop-off and monetization assumptions** — partial: a social return on investment ratio from declared benefits, investment and attribution inputs is implemented; deadweight, displacement and drop-off must be declared, and the result is assumption-sensitive

## glossary (25 terms)

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

## worksheets

_0 worksheets on this shelf._

## theories

_0 theories on this shelf._