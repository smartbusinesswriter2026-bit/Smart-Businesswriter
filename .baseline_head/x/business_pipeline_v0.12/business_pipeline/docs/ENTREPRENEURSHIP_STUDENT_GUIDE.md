# Entrepreneurship for students

This guide explains what the Entrepreneurship shelf is for, what level it assumes and how to use it on
the financial and market sections of a business plan or feasibility study. It is written for **senior
high school ABM** students building their first feasibility study and for **first- and second-year
undergraduate** students in an entrepreneurship or new-venture course. Every number below is produced
by the method named, from the figures shown, in PHP, and can be reproduced in the app. Where the tile
has a preset, the example uses that preset.

The shelf calculates only what you declare. It does not research a market, estimate a demand curve, or
decide whether a venture is a good idea. It is arithmetic, checks and an audit trail around **your**
figures, so the marker can see where every number came from.

## Reading the page

The page follows the sections of a business plan, not the difficulty of the arithmetic:

| Group | What it is for | Tiles |
|---|---|---|
| Market and customers | Size the market and describe the customers | market size, demand line, purchase intent, funnel, cohort retention, market concentration, trend forecast, elasticity, descriptive statistics, chi-square, power |
| Costs, pricing and break-even | Price the product and find the break-even | pricing, break-even, multi-product break-even, unit economics, cost curves, markup and Lerner index |
| Operations plan | Show how the business will deliver | capacity and bottleneck, inventory policy |
| Financial plan and return | Plan the sales, cash and capital, and appraise the return | sales from market share, projected statements, depreciation, sensitivity, financial ratios, sales projection, start-up capital, cash runway, ROI, NPV, IRR, discounted payback, project metrics, scenario analysis, trend analysis, working capital, tax |
| Funding and valuation | Cost and value the financing | cap table and dilution, loan amortization, DCF, multiples, equity bridge, currency conversion |
| Impact and options | Social return and choosing between alternatives | SROI, cost-benefit, cost per unit of impact, compare strategic options |

Below the tools sit the **worksheets**: the Business Model Canvas, Lean Canvas, Value Proposition
Canvas, the SWOT evidence review and a marketing plan for segmentation, targeting, positioning and the
marketing mix. A worksheet organizes evidence you supply; it computes nothing and scores nothing.

Each tile shows its level (intro, intermediate, advanced), the period convention (annual, per period,
monthly, point in time, per observation) and an expandable study note with the formula, the steps and
the mistakes that most often cost marks. The glossary at the foot of the page defines the terms.

## The business plan

The button at the top of the page opens the **business plan**, which is a paper, not a single
calculation. It follows the strict business-plan convention: business description, market analysis,
marketing, operations, management, a **Financial Plan with its computations as level-2 blocks**, risk
analysis, conclusion and references. Your own words stay yours; the market section quotes retrieved
evidence or names a gap.

The senior-high-school plan requires five computation blocks: sales from market share, break-even,
depreciation, projected statements and sensitivity. The college plan adds tax, the cap table and a
cost-per-unit-of-impact ratio. Every block is a frozen method: you declare the figures and the server
returns the recorded result and its checks. The **projected statements refuse an opening balance sheet
that does not balance**, and the export is blocked until every required field and block is complete;
the page names what is missing.

You can attach a brief as a PDF (text layer), Word `.docx`, TXT or an image when OCR is installed on
the machine, or paste the text. The reader says when a scan needs OCR rather than guessing the words.
Home opens the same plan in **open composition**, where you may leave an optional section out; the
facts, the figures and the gate do not change.

## Your assignment requirement, and the tool that answers it

| What the assignment asks for | Tool | What you must supply |
|---|---|---|
| How big is the market, and how much of it can we serve and win? | `market_sizing` | customers in the market, annual spend per customer, a serviceable share and an obtainable share |
| What will customers pay? | `pricing_decision` | unit cost, fixed cost, expected volume, a markup and (optionally) a target margin and profit |
| What revenue does our target market share imply? | `sales_from_market` | the market size, the share you plan to win and your price |
| What are the full projected statements, not just profit? | `proforma_statements` | revenue, margin, costs, depreciation, interest and principal (or opening loan terms), tax, working-capital days and opening balances |
| What is the depreciation charge and carrying amount? | `depreciation_schedule` | cost, salvage, life and method |
| How much does profit move if price or volume changes? | `sensitivity_table` | base price, units, unit cost, fixed cost and the changes to test |
| What is the tax charge on the declared income? | `tax_declared` | taxable income, the declared rate and, optionally, VAT and a temporary difference |
| What are our sales, costs and profit next year? | `sales_projection` | starting volume, price, unit cost, fixed cost per period and a growth rate |
| How many units must we sell to break even? | `breakeven` | fixed cost, price, variable cost, and optionally the expected volume and a profit target |
| What is the margin on each sale, and what does a customer return? | `unit_economics` | price, variable cost, acquisition cost, churn |
| Where do we lose customers before the sale? | `sales_funnel` | the stage counts in order and, optionally, the spend |
| How well do we keep the customers we win? | `cohort_retention` | each cohort's starting size and the count still buying in each period |
| What do our price and quantity observations imply? | `demand_curve` | price-quantity pairs from the same market |
| What share of the market intends to buy? | `purchase_intent` | survey counts, your weights, and optionally the population and price |
| How much capital must we raise to open? | `startup_capital` | set-up costs, working capital, contingency rate, owner equity, loan |
| How long will our cash last? | `cash_runway` | opening cash, monthly net cash flow, growth, horizon |
| What share does an investor get, and what do we give up? | `cap_table_round` | pre-money value, investment, existing shares, optional option pool |
| What is the return on the investment? | `return_on_investment` | total investment, net gain, holding period |
| Is the venture worth more than it costs? | `npv`, `irr`, `discounted_payback`, `project_metrics` | the forecast cash flows and your cost of capital |
| Which of two or three options should we choose? | `case_decision` | two to five alternatives, each with its own cash flows |
| A canvas for the idea itself | **worksheets**: Business Model Canvas, Lean Canvas, Value Proposition Canvas, marketing plan | your own evidence for each block, marked user / sourced / assumption |
| What if sales are lower than we hope? | `scenario_analysis` | the cash flows and a low and high discount rate |
| What is the social return? | `sroi`, `cost_benefit` | the investment, the benefits, the discount rate and the attribution assumptions |
| What do our survey respondents say? | `descriptive_stats`, `chi_square`, `reliability_alpha`, `power_analysis` | your survey data, coded exactly as collected |

If a requirement is not in the table, the shelf probably does not compute it: see **What is not built**
at the end rather than forcing a number into the nearest tool.

## Conventions used throughout

- **Rates are decimals**, not percentages: enter `0.06` for 6%, `0.30` for a 30% share.
- **Currency is declared once** for the run. All the figures in one run must be in that currency.
- **Break-even, pricing and unit economics are per period**; the period you declare is the period the
  fixed cost and the price belong to. Do not mix a monthly rent with a yearly price.
- **The runway is monthly.** Its opening cash, monthly net flow and growth are all monthly figures.
- **Market size is top-down and annual.** TAM is one year of spend by the customers you declare. A
  monthly spend or a multi-year market needs its own declared inputs.
- **No tax is computed.** The target profit, the net gain and the cash flows you enter are already
  after whatever tax you intend.
- **The margin of safety is against the volume you declared**, not against a budget the system invents.
- **The amount to raise is never negative.** When the declared sources exceed the requirement the
  surplus is reported separately.

## Worked examples

Every example below is the preset on the tile, in PHP.

### 1. Market size — `marketsize`

20,000 customers in the target market, spending 3,000 a year, a serviceable share of 0.25 and an
obtainable share of 0.20.

- TAM = 20,000 x 3,000 = **60,000,000**
- SAM = 60,000,000 x 0.25 = **15,000,000**
- SOM = 15,000,000 x 0.20 = **3,000,000**
- Customers in the SOM = 20,000 x 0.25 x 0.20 = **1,000**

**Common mistake:** calling the SOM "the market" in the plan. SOM is what you can realistically win;
TAM is the ceiling you are arguing from.

### 2. Break-even, margin of safety and target profit — `breakeven`

The tile's preset is fixed cost 1,000, price 20, variable cost 10; add an expected volume of 150 units
and a target profit of 500.

- Contribution margin = 20 - 10 = **10 per unit**; CM ratio = 10 / 20 = **0.50**
- Break-even units = 1,000 / 10 = **100 units**
- Break-even revenue = 100 x 20 = **2,000**
- Margin of safety = 150 - 100 = **50 units**, or **33.33%** of expected sales
- Units for the target profit = (1,000 + 500) / 10 = **150 units**

**Common mistake:** dividing fixed cost by the price instead of the contribution margin. That gives
50 units, which is not break-even.

### 3. Pricing rules — `pricing`

Unit cost 15, fixed cost 45,000, expected volume 6,000, markup 0.60, target margin 0.375 and target
profit 20,000.

- Total cost = 15 x 6,000 + 45,000 = **135,000**
- Cost-plus price = 15 x 1.60 = **24.00**
- Break-even price = 135,000 / 6,000 = **22.50**
- Target-margin price = 15 / (1 - 0.375) = **24.00**
- Target-return price = (135,000 + 20,000) / 6,000 = **25.83**

**Common mistake:** treating a 37.5% margin as a 37.5% markup. A markup on cost always gives a lower
price than the same margin on price.

### 4. Start-up capital and the amount to raise — `startupcapital`

Set-up costs 350,000, working capital 120,000, contingency 0.10, owner equity 150,000, loan 200,000.

- Base = 350,000 + 120,000 = **470,000**
- Contingency reserve = 470,000 x 0.10 = **47,000**
- Total funding requirement = **517,000**
- Declared sources = 150,000 + 200,000 = **350,000**
- Amount to raise = 517,000 - 350,000 = **167,000**

**Common mistake:** leaving out working capital. The business then opens with equipment and no cash to
pay its first bills.

### 5. Cash runway and funding gap — `cashrunway`

Opening cash 300,000, monthly net cash flow -40,000, no growth, a nine-month horizon.

- Runway = 300,000 / 40,000 = **7.5 months**
- Cash after seven months = 20,000; after eight = -20,000; after nine = -60,000
- Lowest balance within nine months = **-60,000**
- Funding gap over the horizon = **60,000**

**Common mistake:** entering profit instead of cash. A sale on credit is revenue, not money in the
bank, and the runway ends sooner than the income statement suggests.

### 6. Return on investment — `roi`

Total investment 500,000, net gain 125,000 over three years.

- ROI = 125,000 / 500,000 = **25.00%**
- Annualised ROI = (1.25)^(1/3) - 1 = **7.72%**

**Common mistake:** entering the final value (625,000) instead of the net gain (125,000). That reports
a 125% return.

## Practice set

Work these before looking at the answers.

1. Fixed cost 90,000, price 50, variable cost 30, expected volume 6,000, target profit 30,000.
   Find the break-even units and revenue, the margin of safety and the target-profit volume.
2. 20,000 customers, annual spend 3,000, serviceable share 0.25, obtainable share 0.20.
   Find TAM, SAM, SOM and the customers in the SOM.
3. Unit cost 40, fixed cost 60,000, expected volume 4,000, markup 0.50, target margin 0.20, target
   profit 20,000. Find the cost-plus, break-even, target-margin and target-return prices.
4. Set-up costs 250,000, working capital 80,000, contingency 0.12, owner equity 100,000, loan 150,000.
   Find the total funding requirement and the amount to raise.
5. Opening cash 180,000, monthly net cash flow -45,000, no growth, a six-month horizon. Find the
   runway, the lowest balance and the funding gap.
6. Investment 250,000, net gain 75,000 over two years. Find the ROI and the annualised ROI.

### Answer key

1. CM = 20; break-even = 4,500 units and 225,000; margin of safety = 1,500 units (25%); target-profit
   volume = (90,000 + 30,000) / 20 = 6,000 units.
2. TAM = 60,000,000; SAM = 15,000,000; SOM = 3,000,000; customers = 1,000.
3. Total cost = 220,000; cost-plus = 60.00; break-even = 55.00; target-margin = 50.00;
   target-return = (220,000 + 20,000) / 4,000 = 60.00.
4. Base = 330,000; reserve = 39,600; requirement = 369,600; sources = 250,000; amount to raise =
   119,600.
5. Runway = 4 months; cash after six months = 180,000 - 270,000 = -90,000, so the lowest balance is
   -90,000 and the funding gap is 90,000.
6. ROI = 30.00%; annualised = (1.30)^(1/2) - 1 = 14.02%.

## Planning and analytics examples

### 7. Sales and profit projection — `salesprojection`

300 units in month one, price 120, unit variable cost 55, fixed cost 12,000 a month, volume
growth 5% a month, twelve months.

- Month one: revenue 300 x 120 = **36,000**; contribution 300 x 65 = 19,500; profit **7,500**
- Month two: 315 units, revenue **37,800**
- Twelve months: **4,775.14 units**, revenue **573,016.55**, variable cost **262,632.59**,
  fixed cost **144,000**, profit **166,383.97**

**Common mistake:** growing revenue while holding volume constant. The projection grows volume, so
revenue and variable cost move together.

### 8. One funding round — `captable`

Pre-money 4,000,000, investment 1,000,000, founders' shares 1,000,000, post-money option pool 10%.

- Post-money = 4,000,000 + 1,000,000 = **5,000,000**
- Price per share = 4,000,000 / 1,000,000 = **4.00**
- New shares = 1,000,000 / 4 = **250,000**
- Option pool = 10% of the fully diluted company = **138,888.89 shares**
- Investor **18.00%**, founders **72.00%**, pool **10.00%**; founder dilution **28.00%**

**Common mistake:** quoting the investor's share without the option pool. The pool dilutes the
founders and the investor together, and the percentage changes.

### 9. Funnel, retention, demand and intent

- **Funnel** — 10,000 visits, 2,500 inquiries, 500 purchases: 25%, then 20%, overall **5%**, and at
  25,000 spend the acquisition cost is **50.00** per customer.
- **Cohorts** — the preset's three cohorts give first-period retention 100%, then **73.58%**,
  **57.55%** and **41.51%**, an average lifetime of **2.73 periods**.
- **Demand line** — prices 20 to 40 with quantities 400 down to 160 give a slope of **-12**, an
  intercept of 640, R-squared 1, elasticity at the mean **-1.29**, and a revenue-maximising price of
  **26.67** on the fitted line (revenue 8,533.33 at 320 units).
- **Purchase intent** — 120 definitely, 80 probably, 150 maybe and 50 never, with the declared
  weights, give **33.75%**; applied to 20,000 people that is **6,750 buyers**, or **1,687,500** of
  revenue at 250.

**Common mistake:** reading the demand line as an identified demand curve, or the intent rate as
sales. Both are arithmetic on what you declared, and the report says so.

## Handing it in

Every run produces a report with the declared inputs, the results, the **verification checks** that ran,
the **limitations** the method states, and the citation of how the number was produced. Choose
**Assignment submission** as the artefact and export it as Word or print-ready HTML. The checks and
limitations block is part of the submission on purpose: an answer that hides its assumptions is not a
better answer.

If you are comparing versions of the same case, save each run as a case version, then use the compare
view. The comparison copies stored values verbatim and reports a metric that a version did not compute
as "not computed for this version" instead of filling it in.

## What is not built

These gaps are stated rather than faked, and they are the places where an assignment needs something
the shelf does not do:

- **No market-data retrieval or demand identification.** `demand_curve` fits a line to your own pairs;
  `purchase_intent` weights your own survey. Nothing retrieves census, industry or competitor data, and
  nothing identifies a causal demand curve.
- **No term sheet, liquidation preference, anti-dilution, vesting or multi-round cap table.**
  `cap_table_round` prices one ordinary-share round and its dilution; the negotiated clauses are a
  lawyer's document, not arithmetic, and are not modelled.
- **No survival model, conjoint analysis or Monte Carlo.** Cohort retention is pooled arithmetic;
  scenario analysis moves the discount rate only.
- **No market-share, penetration, RFM, Kano or SERVQUAL method**, and no customer-journey worksheet.
  The marketing plan worksheet covers STP and the mix, not these instruments.
- **Blue Ocean/ERRC and the diffusion theory record** are still catalogue-only ("not implemented"), as
  is the catalogue's market-share and penetration lane.
- **Plan-level methods use annual periods, one product and one currency.** The projected statements
  are arithmetic on your declared drivers, not a demand forecast, and they do not apply a
  jurisdiction's tax law, model disposals or consolidate a group. The sensitivity table changes price
  and volume only.
- **The business plan's market analysis is retrieval, not market research.** A dimension with no
  returned source is a named gap; the plan never fills it.
- **Brief upload reads text, not scans.** A PDF text layer, `.docx` and TXT work without extras; a
  scanned PDF or image needs a local Tesseract and reports `ocr_required` when it is absent.

If your assignment requires one of these, say so in the limitations section and show the arithmetic you
did by hand. That is honest, and it is what the tool's own limitations block is for.
