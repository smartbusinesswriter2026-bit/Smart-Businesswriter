# Economics for students

This guide explains what the Economics shelf is for, what level it assumes, and
how to read the tools added across builds 0.77 to 0.80. It is written for
**senior high school ABM and first-year undergraduate** students for the micro
and macro core, and for **intermediate undergraduate** students for welfare,
international, development and behavioural economics. Advanced econometrics
remains a separate, parked lane.

The tools calculate only what you declare. They do not estimate demand curves,
fetch GDP or CPI data, or decide a policy question for you.

## Conventions

The tools use the same conventions throughout:

- **Demand:** `Qd = a - bP`, with `b > 0`.
- **Supply:** `Qs = c + dP`, with `d > 0`.
- If your textbook writes `P = a - bQ`, rearrange it to `Q = a - bP` before
  entering the numbers.
- **Elasticity:** the arc (midpoint) formula between two observations.
- **Tax:** a fixed amount per unit, levied on sellers; a tax on buyers at the
  same rate has the same economic incidence.
- **Price control:** a ceiling binds only below equilibrium; a floor binds only
  above it. The short side of the market determines quantity traded.
- **Concentration:** HHI uses percentage shares, so it runs from 0 to 10,000.
- **Costs:** `TC = fixed + linear x Q + quadratic x Q squared`; `MC` is the
  derivative, `AC = TC / Q`.
- **National income:** GDP is the expenditure approach `C + I + G + X - M`;
  GNP adds net factor income; NNP subtracts depreciation.
- **Inflation:** the percentage change in the CPI; the real interest rate uses
  the exact Fisher relation, with nominal minus inflation shown as an
  approximation.
- **Labour:** the unemployment rate divides by the labour force; participation
  and employment ratios divide by the working-age population.
- **Money:** the simple multiplier is `1 / reserve ratio`; the extended
  multiplier adds a currency drain.
- **Fiscal:** the government multiplier is `1 / (1 - MPC(1 - t))`.
- **Debt:** the debt ratio is debt over GDP; its change uses the
  interest-growth-primary identity.

## Worked examples

### 1. Market equilibrium

`Qd = 100 - 2P`, `Qs = 20 + 2P`.

Set `100 - 2P = 20 + 2P`, so `80 = 4P` and `P* = 20`. Then
`Q* = 100 - 2(20) = 60`.

- Demand choke price: `100 / 2 = 50`.
- Supply floor price: `-20 / 2 = -10`.
- Consumer surplus: `1/2 x (50 - 20) x 60 = 900`.
- Producer surplus: `1/2 x (20 - (-10)) x 60 = 900`.
- Total surplus: `1,800`.

**Common mistake:** entering the inverse form `P = 50 - 0.5Q` as if it were
`Q = 50 - 0.5P`. The slopes are reciprocals, not the same number.

### 2. Price elasticity of demand

Price falls from 10 to 8; quantity rises from 100 to 140.

- Percentage change in quantity: `40 / 120 = 33.33%`.
- Percentage change in price: `-2 / 9 = -22.22%`.
- Arc elasticity: `33.33 / -22.22 = -1.5`.
- Absolute value: `1.5`, so demand is **elastic**.
- Revenue: `10 x 100 = 1,000` before; `8 x 140 = 1,120` after; a rise of 120.

**Common mistake:** saying demand is inelastic because the elasticity is
negative. Compare the **absolute value** with 1.

### 3. Tax incidence

Same curves; a per-unit tax of 6 on sellers.

- Buyers pay `Pc = 23`; sellers keep `Ps = 17`; the wedge is 6.
- Quantity traded falls from 60 to 54.
- Consumer burden: `23 - 20 = 3`; producer burden: `20 - 17 = 3`.
- Tax revenue: `6 x 54 = 324`.
- Deadweight loss: `1/2 x 6 x (60 - 54) = 18`.

**Common mistake:** assuming the side that hands the tax to the government bears
the burden. The slopes decide the split.

### 4. Price ceiling

Same curves; a ceiling at 15.

- Quantity demanded: `100 - 2(15) = 70`.
- Quantity supplied: `20 + 2(15) = 50`.
- Shortage: 20; quantity traded: 50.
- Deadweight loss: `1/2 x (60 - 50) x (25 - 15) = 50`.

A floor at 25 gives a surplus of 20 and the same deadweight loss.

**Common mistake:** treating a ceiling above equilibrium as binding. It is not.

### 5. Market concentration

Firm revenues: 40, 25, 15, 10, 10 (total 100).

- Shares: 40%, 25%, 15%, 10%, 10%.
- HHI: `40^2 + 25^2 + 15^2 + 10^2 + 10^2 = 2,650`.
- CR4: `40 + 25 + 15 + 10 = 90%`.
- Equivalent number of equal-sized firms: `10,000 / 2,650 = 3.77`.

**Common mistake:** entering fractions (0.40) when the HHI expects percentages.
Fractions give an HHI between 0 and 1.

## Practice set

1. `Qd = 120 - 3P`, `Qs = 2P - 10`. Find `P*`, `Q*`, consumer surplus and
   producer surplus.
2. Price rises from 20 to 24; quantity falls from 50 to 40. Find the arc
   elasticity and classify it.
3. Using the curves in question 1, impose a per-unit tax of 5. Find `Pc`, `Ps`,
   quantity traded, the burden split and deadweight loss.
4. Using the curves in question 1, impose a ceiling of 20. Find the shortage,
   quantity traded and deadweight loss.
5. Firm revenues are 50, 20, 15, 10, 5. Find the HHI, CR4 and the equivalent
   number of firms.

### Answer key

1. `P* = 26`, `Q* = 42`; consumer surplus `294`, producer surplus `441`.
2. `%dQ = -10/45 = -22.22%`, `%dP = 4/22 = 18.18%`,
   `E = -1.22` (elastic).
3. `Pc = 28`, `Ps = 23`, `Qt = 36`, consumer burden `2`, producer burden `3`,
   revenue `180`, deadweight loss `15`.
4. `Qd = 60`, `Qs = 30`, shortage `30`, quantity traded `30`,
   deadweight loss `60`.
5. Shares `50, 20, 15, 10, 5`; HHI `3,250`; CR4 `95%`; effective firms `3.08`.

## Macro and firm worked examples

### 6. Cost curves

`TC = 1,000 + 10Q + 0.5Q squared`, at `Q = 20`.

- `TC = 1,000 + 200 + 200 = 1,400`.
- `AC = 1,400 / 20 = 70`; `AVC = 400 / 20 = 20`; `AFC = 1,000 / 20 = 50`.
- `MC = 10 + 2(0.5)(20) = 30`.
- At a price of 40, revenue is 800 and profit is -600. Price is above AVC, so
  the firm operates in the short run even though it makes a loss.

**Common mistake:** shutting down whenever profit is negative. The shutdown
test compares price with **average variable cost**, not with average cost.

### 7. Profit maximisation

`P = 100 - 2Q`, `TC = 100 + 10Q + 0.5Q squared`.

- `MR = 100 - 4Q`; `MC = 10 + Q`.
- Set `100 - 4Q = 10 + Q`, so `Q = 18` and `P = 64`.
- Revenue 1,152; cost 442; profit 710.
- `MC` at the optimum is 28; markup 36; Lerner `36 / 64 = 0.5625`.

**Common mistake:** setting `P = MC`. That is the competitive outcome; a firm
with market power sets `MR = MC`.

### 8. GDP and national income

`C = 600`, `I = 150`, `G = 200`, `X = 120`, `M = 170`.

- `GDP = 600 + 150 + 200 + 120 - 170 = 900`.
- Net factor income 20 gives `GNP = 920`; depreciation 50 gives `NNP = 870`.
- Deflator 120 gives real GDP `900 / 1.2 = 750`.
- Population 100 gives GDP per capita 9.

**Common mistake:** adding imports instead of subtracting them.

### 9. Growth and inflation

100 grows to 200 over 10 periods.

- Total growth 100%; CAGR `(200/100)^(1/10) - 1 = 7.18%`.
- Rule of 72: `72 / 7.18 = 10.03` periods to double.

CPI 100 to 105 is 5% inflation. A nominal interest rate of 8% gives an exact
real rate of `1.08 / 1.05 - 1 = 2.86%`; nominal minus inflation is 3%, an
approximation. Wages 100 to 104 grow 4% nominal, so real wages fall by about
0.95%.

**Common mistake:** subtracting the two CPI values and calling the difference
the inflation rate.

### 10. Unemployment and money

Labour force 1,000; employed 920; working-age population 1,500.

- Unemployed 80; unemployment rate 8%.
- Participation rate `1,000 / 1,500 = 66.67%`; employment ratio
  `920 / 1,500 = 61.33%`.

Monetary base 100; reserve ratio 10%; currency drain 5%.

- Simple multiplier `1 / 0.10 = 10`; money supply 1,000.
- Extended multiplier `(1.05) / (0.15) = 7`; money supply 700.

**Common mistake:** dividing the unemployed by the working-age population, or
forgetting the currency drain.

### 11. Fiscal policy and debt

MPC 0.8; tax rate 25%.

- Government multiplier `1 / (1 - 0.8(0.75)) = 2.5`.
- Tax multiplier `-0.8 / 0.4 = -2`; balanced-budget multiplier `0.2 / 0.4 = 0.5`.
- A 100 rise in government spending raises output by 250 in this model.

Revenue 500; primary spending 520; interest 30.

- Total spending 550; overall balance -50; primary balance -20.
- Debt 1,000 and GDP 2,000 give a 50% debt ratio.
- Interest rate 3%, growth 5%, primary balance -1% of GDP:
  `(3% - 5%) x 50% - (-1%) = 0`, so the debt ratio is stable.

**Common mistake:** including interest in primary spending and then adding it
again, or confusing the overall balance with the primary balance.

## Macro practice set

1. `TC = 500 + 8Q + 0.25Q squared`, at `Q = 20`. Find TC, AC, AVC, AFC and MC.
2. `P = 80 - Q`, `TC = 50 + 10Q + 0.5Q squared`. Find the profit-maximising
   quantity, price and profit.
3. `C = 400`, `I = 100`, `G = 150`, `X = 80`, `M = 90`. Find GDP and net exports.
4. A value grows from 50 to 80 over 6 years. Find total growth and CAGR.
5. CPI 120 to 126; nominal interest 7%; wages 200 to 210. Find inflation, the
   real interest rate and real wage growth.
6. Labour force 500; employed 450; working-age population 800. Find the
   unemployment rate, participation rate and employment ratio.
7. Monetary base 200; reserve ratio 20%; no currency drain. Find the simple
   multiplier and the money supply.
8. MPC 0.75; tax rate 20%; government spending rises by 80. Find the government
   multiplier and the output change.
9. Revenue 300; primary spending 330; interest 20; debt 800; GDP 1,600; nominal
   growth 4%. Find the overall balance, primary balance and debt ratio.

### Macro answer key

1. `TC = 500 + 160 + 100 = 760`; `AC = 38`; `AVC = 13`; `AFC = 25`;
   `MC = 8 + 2(0.25)(20) = 18`.
2. `MR = 80 - 2Q`; `MC = 10 + Q`; `Q = 23.33`; `P = 56.67`;
   `profit = 1,322.22 - (50 + 233.33 + 272.22) = 766.67`.
3. `GDP = 400 + 100 + 150 + 80 - 90 = 640`; net exports `-10`.
4. Total growth 60%; CAGR `(80/50)^(1/6) - 1 = 8.15%`.
5. Inflation 5%; real interest `1.07 / 1.05 - 1 = 1.90%`; nominal wage growth
   5%, real wage growth `1.05 / 1.05 - 1 = 0`.
6. Unemployed 50; unemployment rate 10%; participation 62.5%; employment ratio
   56.25%.
7. Simple multiplier `1 / 0.20 = 5`; money supply `200 x 5 = 1,000`.
8. Government multiplier `1 / (1 - 0.75(0.80)) = 2.5`; output change `80 x 2.5
   = 200`.
9. Overall balance `300 - 330 - 20 = -50`; primary balance `-30`; debt ratio
   `800 / 1,600 = 50%`.

## Welfare, international and behavioural examples

### 12. Inequality, poverty and externalities

Incomes 10, 20, 30, 40.

- Gini `0.25`; mean 25.
- With a poverty line of 25: headcount 50%, average poverty gap 20%.
- A per-unit external cost of 4 on the equilibrium example moves the social quantity
  from 60 to 56; the Pigouvian tax is 4 and the deadweight loss is 8.

**Common mistake:** averaging the poverty gap only over the poor, or treating the
Gini as a full picture of where inequality lies.

### 13. Comparative advantage and a tariff

Country A needs 2 hours for good one and 1 hour for good two; country B needs 5 and 3.

- Opportunity cost of good one: A `2`, B `1.67`; B has comparative advantage in
  good one, A in good two.
- A is absolutely better at both goods, which is exactly why absolute advantage
  does not determine the pattern of trade.

World price 10; tariff 5 on the equilibrium curves.

- Domestic price 15; imports fall from 40 to 20.
- Tariff revenue 100; production and consumption deadweight loss 25 each, total 50.

**Common mistake:** reading absolute hours as comparative advantage.

### 14. PPP and interest parity

Domestic price 5,000; foreign price 100; nominal rate 55 domestic per foreign.

- PPP rate 50; real exchange rate `55 x 100 / 5,000 = 1.1`, so the nominal rate is
  10% above PPP.
- Spot 50; domestic 6%; foreign 4%; one year: forward `50 x 1.06 / 1.04 = 50.96`.

**Common mistake:** inverting the exchange-rate quotation, or using simple interest
when the method compounds.

### 15. Expected utility and prospect theory

A 50/50 gamble between 50 and 150; CRRA risk aversion 2.

- Expected value 100; expected utility -0.01333; certainty equivalent 75; risk
  premium 25.
- Prospect theory around a reference point of 100 values the same 50/50 gain/loss
  at about -19.54 with the default loss aversion and weighting.

**Common mistake:** treating expected value as expected utility, or treating
prospect theory as a normative recommendation.

### 16. Cournot and Nash

`P = 100 - 2Q`, costs 10 and 20.

- Cournot quantities 16.67 and 11.67; price 43.33; profits 555.56 and 272.22.
- In the prisoner's dilemma payoff matrix, the dominant-strategy cell is the unique
  pure Nash equilibrium.

**Common mistake:** looking for the highest joint payoff instead of a cell where
neither player can gain by switching alone.

### 17. Advanced econometrics: panel, IV, RDD and probit

- **Panel fixed effects:** the balanced three-entity example gives a within slope of `2`, with within
  R-squared `1` in the constructed data.
- **Instrumental variables:** the example gives an IV slope of `1.46`, a first-stage slope of `0.905`
  and an OLS slope of `1.408`; the difference is the point of the exercise.
- **Regression discontinuity:** a local-linear fit with a jump from a left intercept of `3` to a right
  intercept of `9` gives an estimate of `6`.
- **Probit:** the example slope is about `0.092` on the latent scale, with a marginal effect at the mean of
  about `0.037`.

**Common mistake:** treating a relevant instrument as a valid one, treating an RDD bandwidth as arbitrary, or
reading a probit coefficient as a constant probability effect.

## What this shelf does and does not cover

**Covered now:** equilibrium, elasticity, tax incidence, price controls, market
concentration, cost curves, profit maximisation, market power, price
discrimination, Cournot competition and 2x2 Nash equilibrium; GDP and national
income, growth, inflation and real interest, unemployment and participation,
money and fiscal multipliers, budget balances, debt and Okun's law; externalities,
public goods, social welfare, Gini, poverty, tax progressivity and optimal
pollution; comparative advantage, tariffs, PPP, interest parity, the balance of
payments and the HDI; expected utility, prospect theory and the labour market;
difference-in-differences; plus cost-benefit and cost-effectiveness appraisal,
SROI, forecasting, currency conversion, break-even, unit economics and the core
statistics used in economics.

**Not covered yet:** VAR, cointegration and the remaining time-series estimators,
the economics catalogue section and the diagram renderer. Those remain labelled
gaps rather than faked calculations. The student guide is not yet
teacher-reviewed.

**Never covered by arithmetic alone:** IS-LM and AD-AS diagrams, game theory
trees, consumer-choice diagrams, schools of economic thought and economic
history. These belong in worksheets and catalogue records, not in a calculator.

## Bringing your own material

The calculator box is not the only way in. At the top of the session you can
attach, and each attachment becomes something specific:

- **An instruction** — your assignment brief pasted or attached, then read back
  by *Use as the instruction*. It is marked `unverified: true`: the system shows
  you what it thinks the brief asks, and you confirm it before anything runs.
- **A dataset** — attached with `role: dataset`. Its columns then map onto a
  method's inputs and the mapped values are recorded as **sourced**, with an
  `input_provenance` entry and a data manifest, rather than as figures you typed.
- **Your sources** — a `.bib`, `.ris` or `.csv` file attached as `kind: sources`.
  A declared source is recorded as your declaration (B-182); it is **not**
  evidence that this system retrieved or verified it.
- **A rubric** — attached and read by `rubric.py`, which is read-only and asks
  you to confirm what it read (`confirm_required`). It never awards a mark.

None of this changes the rule above: the tools still calculate only what is
declared, and nothing is estimated, fetched or filled in for you. Attachments
are a faster way to declare, not a substitute for declaring.

