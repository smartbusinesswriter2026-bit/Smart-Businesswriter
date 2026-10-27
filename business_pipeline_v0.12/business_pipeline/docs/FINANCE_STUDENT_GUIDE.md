# Finance for students

This guide explains what the Finance shelf is for, what level it assumes, and how to read the
fourteen tools added in build 0.76. It is written for **senior high school ABM, first-year
undergraduate and intermediate financial-management** students. Every number below is produced
by the method named, from the preset inputs, and can be reproduced in the app.

The tools calculate only what you declare. They do not fetch share prices, bond quotes,
exchange rates or peer multiples, and they do not decide an investment question for you.

## Reading the page

The shelf is arranged in the order a course usually teaches it: **Foundations**, **Corporate
finance**, **Valuation**, **Investments**, **Risk & derivatives**, **International**. Each tile
carries a level (intro, intermediate, advanced), a period convention (`annual`, `per period`,
`per observation`, `spot rate`, `point in time`) and an expandable study note with the formula, the
steps and the mistakes that most often cost marks. The glossary at the foot of the page defines the
terms used on it.

If an answer produces a rate above 100%, the report adds a warning: rates are entered as decimals,
so 6% is `0.06`, not `6`. The warning does not block the run, because a declared rate above 100%
can be genuine.

## Conventions used throughout

- **Rates are decimals**, not percentages: enter `0.06` for 6%, not `6`.
- A **nominal annual rate** is divided by the compounding or payment frequency inside the method;
  the **effective annual rate** is reported separately. Do not enter a monthly rate as if it were annual.
- **Time-value and project cash flows are end-of-period**, with the first cash flow at `t = 0`
  (normally the negative outlay). The mid-year convention exists only in `dcf_valuation`.
- **Returns** in `portfolio_analysis` and `risk_metrics` are per period, as decimals. A mean,
  standard deviation, Sharpe ratio or VaR is therefore *per that period*, not annual, unless you
  supplied annual returns.
- **Enterprise versus equity:** EV/EBITDA and EV/Sales are enterprise multiples; P/E and P/B are
  equity multiples. `multiples_valuation` bridges through net debt in the right direction for each.
- **FX quotes** are domestic currency per one unit of foreign currency.
- **Tax is never computed.** Where a method needs an after-tax figure, you supply it, or you supply
  the tax rate and the method applies it exactly as declared.

## Choosing a tool

| Question you are answering | Tool |
|---|---|
| What will savings and regular deposits be worth? | `time_value` |
| What is the monthly payment and total interest on a loan? | `loan_amortization` |
| What is this bond worth, or what yield does this price imply? | `bond_analysis` |
| What cost of equity does CAPM imply, and what is the relevered beta? | `capm` |
| Where does the return on equity come from? | `dupont_analysis` |
| What value do comparable companies imply? | `multiples_valuation` |
| How long is cash tied up, and how much should we order? | `working_capital` |
| What return and risk does this two-asset portfolio have? | `portfolio_analysis` |
| Which project ranks better on PI, MIRR, payback or EAA? | `project_metrics` |
| What is this option worth, and how sensitive is it? | `option_pricing` |
| How much could this portfolio lose at a stated confidence? | `risk_metrics` |
| What forward rate and expected spot do the parities imply? | `fx_parity` |
| What do EPS, leverage and the Altman Z-score look like? | `leverage_analysis` |
| How much does the decision swing with the discount rate? | `scenario_analysis` |

## Worked examples

### 1. Time value of money

A lump sum of 100,000 today plus 12,000 deposited at the end of each year for five years, at a
nominal 6% compounded quarterly (`present_value 100000`, `payment 12000`, `rate 0.06`,
`periods 5`, `compounding quarterly`, `timing end`).

- Periodic rate: `0.06 / 4 = 0.015`; periods: `5 x 4 = 20`.
- Future value: **412,169.51**.
- Present value of the twenty deposits: **206,023.67**.
- Effective annual rate: `(1.015)^4 - 1 = 6.1364%`.

**Common mistake:** treating 6% as a quarterly rate. That multiplies the answer by roughly
`(1.06/1.015)^20`.

### 2. Loan amortization

200,000 borrowed at 9% a year for five years, monthly payments (`principal 200000`,
`annual_rate 0.09`, `years 5`, `payments_per_year 12`).

- Monthly rate: `0.09 / 12 = 0.0075`; payments: 60.
- Level payment: **4,151.67**.
- Total paid: **249,100.26**; total interest: **49,100.26**.
- First payment: 1,500.00 interest and 2,651.67 principal.

**Common mistake:** multiplying the monthly payment by 60 and calling the difference "interest
charged this year". It is the interest over the whole term.

### 3. Bond price, yield and duration

A 10-year 8% bond, face value 1,000, semiannual coupons, yield to maturity 6%.

- Coupon per half-year: `1,000 x 0.08 / 2 = 40`; 20 payments.
- Price: **1,148.77** (a premium, because the coupon exceeds the yield).
- Macaulay duration: **7.2863 years**; modified duration: **7.0740**.
- Convexity: **63.92**; DV01: **0.8126** per 1,000 face.

If you supply the price instead of the yield, the method solves the yield. Feeding the computed
price back returns 6.0000%, which is the check.

**Common mistakes:** dividing the annual coupon by the annual yield instead of the periodic
coupon by the periodic yield; reading duration as maturity; forgetting that a premium bond's
price falls towards par as maturity approaches.

### 4. CAPM and Hamada relevering

Risk-free 4%, market return 10%, beta 1.2, debt-to-equity 0.6, tax 30%.

- Market risk premium: `0.10 - 0.04 = 0.06`.
- Cost of equity: `0.04 + 1.2 x 0.06 = 11.2%`.
- Unlevered beta: `1.2 / (1 + 0.7 x 0.6) = 0.8451`.
- Relevered beta returns 1.2, the round-trip check.

**Common mistakes:** using the debt-to-*value* ratio where the formula expects debt-to-*equity*;
relevering with a pre-tax rather than `(1 - tax)` shield; comparing a levered beta with an
unlevered comparable's cost of equity.

### 5. DuPont analysis

Revenue 20,000, net income 1,800, total assets 12,000, equity 5,000 (and EBIT 3,000, pre-tax
income 2,400, tax 600 for the five-step form).

- Net margin 9.0%; asset turnover 1.6667; equity multiplier 2.4.
- ROE: `0.09 x 1.6667 x 2.4 = 36.0%`, matching `1,800 / 5,000`.
- Five-step: tax burden 0.75 x interest burden 0.8 x operating margin 0.15 x turnover 1.6667 x
  multiplier 2.4 = **36.0%**.
- Against the declared comparison period (revenue 18,000, net income 1,500, assets 11,000,
  equity 4,700), revenue grew **11.11%**, net income **20.0%**, and prior ROE was **31.91%**, so ROE
  rose by **4.09 percentage points**.

**Common mistake:** concluding that a high ROE means good operations. A high multiplier can carry
ROE while margin and turnover are weak; the three components are the point of the decomposition.
A second common mistake is comparing a 12-month period with a nine-month prior period and calling
the difference growth.

### 6. Comparable multiples

EBITDA 500,000; peers at 8x, 10x and 12x; net debt 300,000; 100,000 shares.

- Mean and median multiple: 10x.
- Implied enterprise value: **5,000,000**.
- Implied equity value: `5,000,000 - 300,000 = 4,700,000`.
- Per share: **47.00**.

**Common mistakes:** applying a P/E to EBITDA; forgetting to subtract net debt from an enterprise
multiple; averaging a peer set that includes a loss-making outlier without saying so.

### 7. Working capital and inventory

Revenue 20,000, cost of sales 12,000, inventory 1,200, receivables 1,500, payables 900; annual
demand 5,000 units, order cost 50, holding cost 4 per unit a year; 2/10 net 30; lead time 7 days;
safety stock 100.

- DSO 27.375 days; DIO 36.5 days; DPO 27.375 days.
- Cash conversion cycle: **36.5 days**.
- EOQ: **353.55 units**; reorder point: `13.6986 x 7 + 100 = 195.89 units`.
- Cost of forgoing the discount: **37.24% a year**.

**Common mistakes:** using revenue for DIO and DPO (use cost of sales); treating the cash
conversion cycle as a profitability measure (it is a liquidity measure); forgetting that the EOQ
minimises order plus holding cost, not purchase cost.

### 8. Portfolio return, risk and performance

Six paired period returns, 60% in asset A and 40% in B, risk-free 2% per period, with a market
series.

- Portfolio return: **1.70%** per period.
- Portfolio standard deviation: **1.4014%**.
- Correlation: **0.8303**; beta against the market series: **0.9375**.
- Sharpe: **-0.2141**; Treynor: **-0.0032**; Jensen's alpha: **+0.6375%**.

**Common mistakes:** mixing monthly and annual returns; using the risk-free *annual* rate with
monthly returns; reading a negative Sharpe as "the portfolio lost money" (it means the return is
below the risk-free rate for that period).

### 9. Project ranking metrics

Outlay 1,000, then 400 a year for four years, at 10% (finance rate 8%).

- NPV: **267.95**; profitability index: **1.2679**.
- MIRR: **15.87%**; IRR: **21.86%**; payback: **2.5 years**.
- Equivalent annual annuity: **84.53** a year.

**Common mistakes:** ranking two projects by IRR when their scales differ; reading payback as a
return; forgetting that MIRR depends on the declared reinvestment rate while NPV does not.

### 10. Option pricing

A European call, spot 100, strike 100, volatility 25%, risk-free 5%, one year.

- Black-Scholes price: **12.34**; binomial cross-check at 200 steps: **12.32**.
- Delta **0.6274**, gamma **0.01514**, vega **37.84**, theta **-7.25**, rho **50.40**.
- Intrinsic value 0; time value 12.34; put-call parity gap 0.

**Common mistakes:** entering volatility as 25 instead of 0.25; assuming this prices an American
put (it does not); treating delta as the probability of exercise (it is a hedge ratio).

### 11. Value at risk

Ten period returns, 95% confidence, a 1,000,000 portfolio, a declared stress return of -5%.

- Mean 0.15%, standard deviation 1.7803%.
- Historical VaR: **2.55%** (25,500); historical expected shortfall: **3.00%**.
- Parametric VaR at 95% is 0 here because the positive mean offsets the normal quantile; that is
  a result, not a bug, and it is why the historical route is also shown.
- Stress loss: **50,000**.

**Common mistakes:** calling VaR the maximum loss; using a 99% VaR and a 95% expected shortfall
together; scaling a one-day VaR to a year by multiplying by 365 instead of the square root of 365.

### 12. International parity

Spot 56 domestic per foreign; domestic rate 5%, foreign 3%; domestic inflation 4%, foreign 2%;
one year; declared forward 57.

- Relative PPP expected spot: **57.0980**.
- Covered interest parity forward: **57.0874**.
- Forward premium on the declared forward: **1.7857%** a year.
- Real rates: 0.9615% domestic, 0.9804% foreign.
- A 100,000 foreign-currency receivable hedged at 57 is worth **5,700,000**; at the expected spot
  of 57.5 it would be **5,750,000**, so the hedge gives up **50,000** against that expectation.

**Common mistakes:** quoting the rate the other way up; mixing a one-year rate with a six-month
horizon without adjusting the exponent; treating a parity value as a forecast; calling a hedge
that locks in less than the expected spot a "loss" without stating the expectation it is measured
against.

### 13. Leverage, EPS and Altman Z

EBIT 500,000, interest 100,000, tax 30%, debt 800,000, equity 1,200,000, 100,000 shares, plus the
six Altman figures.

- EPS: **2.80**; degree of financial leverage: **1.25**; interest cover: **5x**.
- Interest tax shield: **30,000**; debt-to-equity: **0.6667**.
- Altman Z: **4.135**, from terms 0.18 + 0.28 + 0.825 + 1.35 + 1.50.
- The alternative plan (200,000 interest, 60,000 shares) and the current plan report the same EPS
  of **1.75** at EBIT **350,000**. Above that EBIT the lower-share plan reports more, and at the
  declared 500,000 it reports **3.50** against 2.80.

**Common mistake:** reading the Z-score against a remembered cut-off. The app deliberately does
not apply the safe/grey/distress bands, because they are sample-specific; report the score and
its terms, and cite the cut-off you are using. A second mistake is treating the indifference EBIT
as a recommendation: it says where the EPS lines cross, not which plan is safer.

### 14. Scenario analysis

The same project as example 9, with a base rate of 10% and a declared range of 5% to 20%.

- NPV at 10%: **267.95**; at 5%: **418.38**; at 20%: **35.49**.
- Swing: **382.89**.
- Break-even (decision-flip) rate: **21.86%**, the project's IRR.

**Common mistake:** calling this a scenario analysis of the business. Only the discount rate
moves; revenue, costs and timing are fixed. A multi-input scenario or a simulation is not built.

## What the Finance shelf does not do

- **No retrieved data:** no share prices, bond quotes, option prices, peer multiples, exchange
  rates, inflation or risk-free series. Every such figure is your declaration.
- **No tax computation:** taxes are declared, and only `leverage_analysis` applies a declared rate
  to interest and pre-tax earnings.
- **No forecasting:** `trend_forecast` is the only forecasting tool, and it is a linear trend with
  an interval, not a financial model.
- **No common-size or trend analysis across many years**, no Monte Carlo, no real options,
  no American exercise, no spot/forward curve, no credit or liquidity risk, no multi-asset
  optimisation and no efficient frontier, and no comparison of more than two financing plans.
  These are recorded gaps, not hidden features. Common-size ratios and one declared prior-period
  comparison *are* built into `dupont_analysis`, and a two-plan EBIT-EPS indifference point is
  built into `leverage_analysis`.
- **Not a textbook:** the tools show the formula and the intermediate values, but they do not
  derive the theory, mark your working, or replace a lecturer's explanation.

## Practice set

Work these by hand, then check them in the app.

1. 50,000 today at 8% compounded annually for 3 years, with no payments. What is the future value?
2. A 120,000 loan at 12% a year for 4 years, paid quarterly. What is the quarterly payment?
3. A 5-year 6% bond, face 1,000, annual coupons, yield 8%. Is it at a premium or a discount, and why?
4. Risk-free 3%, market return 9%, beta 0.8. What is the cost of equity?
5. Revenue 50,000, net income 4,000, assets 25,000, equity 10,000. Compute the three-step ROE.
6. EBITDA 200,000, peers at 6x and 8x, net debt 150,000. What is the implied equity value?
7. Receivables 2,000, revenue 24,000, inventory 1,500, cost of sales 12,000, payables 1,000.
   Compute DSO, DIO, DPO and the cash conversion cycle.
8. A project costs 500 and returns 200 a year for three years at 10%. Compute NPV and PI.
9. Spot 50, domestic rate 6%, foreign rate 2%, one year. What forward does interest parity imply?
10. EBIT 300, interest 50, tax 25%, 1,000 shares. Compute EPS and the degree of financial leverage.

**Answer key (rounded):** 1) 62,985.60. 2) 9,553.30. 3) A discount: price 920.15, because the
coupon is below the yield. 4) 7.80%. 5) 8% x 2.0 x 2.5 = 40%. 6) 1,250,000. 7) DSO 30.42,
DIO 45.63, DPO 30.42, CCC 45.63 days. 8) NPV -2.63, PI 0.9947. 9) 51.96. 10) EPS 0.1875, DFL 1.20.
