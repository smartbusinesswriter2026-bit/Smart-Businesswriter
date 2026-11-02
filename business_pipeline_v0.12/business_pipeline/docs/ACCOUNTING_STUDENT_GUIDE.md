# Accounting for students

This guide explains what the Accounting shelf is for, what level it assumes and how to use it on the
bookkeeping, statements, ratio and variance work an accounting course sets. It is written for **senior
high school ABM** students and **first- and second-year undergraduate** accounting students. Every
number below is produced by the method named, from the figures shown, in PHP, and can be reproduced in
the app.

The shelf keeps the books and computes declared figures. It does not decide the treatment, choose the
policy or audit the answer.

## Reading the page

| Group | What it is for | Tiles |
|---|---|---|
| Bookkeeping and statements | Keep the books and read the statements | Management accounts, trial-balance check, financial ratios |
| Cost and variance analysis | Explain cost and explain the difference from standard | Standard-cost variances, break-even, multi-product break-even |
| Working capital and financing | Cash tied up, borrowing and the trend | Working capital and EOQ, loan amortization, trend analysis |

Each tile carries a level, a period convention and an expandable study note with the formula, the steps
and the mistakes that most often cost marks. The glossary at the foot of the page defines the terms.

## Conventions

- **Every entry must balance.** Debits equal credits before anything is posted.
- **The statements are built from the journal**, not typed in. Assets = liabilities + equity, and the
  cash-flow statement is produced by two routes and checked against itself.
- **A trial balance that balances is not proof.** A wrong account still balances; that is why the
  check compares your trial balance with the one your own journal rebuilds, line by line.
- **A positive variance is unfavourable.** Every variance is actual cost less the standard cost of the
  output achieved.
- **Depreciation is an allocation, not a cash payment.** The cash-flow statement adjusts for it.
- **Rates and ratios are decimals** where the method asks for a rate, and are reported as percentages.

## Your assignment requirement, and the tool that answers it

| What the assignment asks for | Tool | What you supply |
|---|---|---|
| Record the transactions and prepare the statements | `management_accounts` | the period, chart of accounts, opening balances and dated entries |
| Check my trial balance against my journal | `trial_balance_check` | your trial balance and your journal |
| Compute liquidity, profitability, solvency and efficiency ratios | `ratio_analysis` | the statement figures |
| Explain the material, labour and overhead variances | `standard_cost_variances` | actual output, standards, actual quantities, hours and prices |
| What does each product really cost? | `abc_costing` | activity pools, driver quantities and product units |
| Why did revenue move against the budget? | `sales_variances` | budget and actual units and prices for two or more products |
| What is the tax charge on the declared income? | `tax_declared` | taxable income, the income tax rate, and optionally VAT and a deferred tax difference |
| Break-even for one product or a mix | `breakeven`, `multi_product_breakeven` | fixed cost, prices and variable costs |
| Cash conversion cycle and order quantity | `working_capital` | revenue, cost of sales, inventory, receivables, payables |
| Monthly payment and total interest on a loan | `loan_amortization` | principal, rate, term |
| How the figures moved over several years | `trend_analysis` | several years of income-statement figures |

## Worked examples

### 1. The books in miniature — `management_accounts`

Owner invests 50,000 cash; buy 20,000 of stock on credit; sell goods for 15,000 that cost 9,000.

- Dr Cash 50,000 / Cr Owner capital 50,000
- Dr Inventory 20,000 / Cr Trade payables 20,000
- Dr Cash 15,000 / Cr Sales 15,000, and Dr Cost of sales 9,000 / Cr Inventory 9,000
- Trial balance: debits and credits both 85,000. Assets (cash 65,000 + inventory 11,000) = 76,000;
  liabilities 20,000 + equity 50,000 + profit 6,000 = 76,000.

**Common mistake:** entering only the cash side of the sale. The engine will refuse an unbalanced entry
and name it.

### 2. Variances — `standard_cost_variances`

Output 4,800 units. Standard: 2 kg at 15 a kg, 1.5 hours at 40 an hour, variable overhead 10 an hour;
fixed overhead budget 240,000 over 8,000 hours. Actual: 9,800 kg at 15.50, 7,300 hours at 41, variable
overhead 70,000, fixed overhead 245,000.

- Material price = 9,800 x (15.50 - 15) = **4,900 U**; usage = 15 x (9,800 - 9,600) = **3,000 U**
- Labour rate = 7,300 x (41 - 40) = **7,300 U**; efficiency = 40 x (7,300 - 7,200) = **4,000 U**
- Variable overhead spending = 70,000 - 73,000 = **3,000 F**; efficiency = 10 x 100 = **1,000 U**
- Fixed overhead spending = 5,000 U; volume = 240,000 - (7,200 x 30) = **24,000 U**
- Total = **46,200 U**

**Common mistake:** using budgeted output in the usage variance. The standard quantity is allowed for the
output actually produced.

### 3. Ratios from the statements — `ratio_analysis`

Current assets 500,000 (including inventory 200,000), current liabilities 200,000: current ratio
**2.50**; quick ratio (500,000 - 200,000) / 200,000 = **1.50**. A high current ratio with slow
inventory is not automatically good; read the cash conversion cycle beside it.

### 4. Activity-based costing — `abc_costing`

Setup pool 50,000 over 100 driver units (40 for X, 60 for Y); inspection pool 30,000 over 30 (20 for X,
10 for Y). X makes 1,000 units, Y 500.

- Setup rate 500; inspection rate 1,000
- X = 40 x 500 + 20 x 1,000 = **40,000**, or **40 a unit**
- Y = 60 x 500 + 10 x 1,000 = **40,000**, or **80 a unit**
- Total allocated **80,000**, exactly the pools

**Common mistake:** leaving an activity with a cost and no driver quantity. The method refuses it rather
than hiding the unallocated cost.

### 5. Sales price, mix and yield — `sales_variances`

Budget: 100 X at 10 and 100 Y at 20. Actual: 120 X at 11 and 80 Y at 18.

- Budget revenue 3,000; actual 2,760; total **-240**
- Price: 120 x 1 + 80 x (-2) = **-40**
- Mix: 10 x 20 + 20 x (-20) = **-200**
- Yield: **0**
- Check: -40 - 200 + 0 = **-240**

**Common mistake:** calling the whole revenue fall a price effect. Most of it here is the mix moving
towards the cheaper product.

### 6. Tax on declared rates — `tax_declared`

Taxable income 1,000,000 at 25%; output VAT 144,000 and input VAT 84,000; temporary difference 100,000
at 25%.

- Income tax = **250,000**; after-tax income **750,000**
- VAT payable = 144,000 - 84,000 = **60,000**
- Deferred tax = 100,000 x 0.25 = **25,000**
- Total tax charge = **275,000**

**Common mistake:** treating this as a tax return. The method applies the rates you declare; it knows
nothing about credits, thresholds, NOLCO or filing rules.

## Practice set

1. Output 1,000 units. Standard 2 kg at 10 a kg and 1 hour at 20 an hour. Actual 2,100 kg at 11, 950
   hours at 21. Find the four variances and the total.
2. Annual demand 8,000 units, order cost 250, holding cost 20 a unit-year. Find the EOQ and the orders
   per year.
3. A single server takes 15 customers an hour; 9 arrive. Find utilisation, the average queue and the
   average wait.
4. Two resources: 6 hours at 4 minutes a unit and 6 hours at 6 minutes a unit, demand 54. Find each
   capacity, the bottleneck, the utilisation and the gap.

### Answer key

1. Price 2,100 U; usage 1,000 U; rate 950 U; efficiency -1,000 F (favourable); total **3,050 U**.
2. EOQ = sqrt(2 x 8,000 x 250 / 20) = **447.21**; orders = 8,000 / 447.21 = **17.89** a year.
3. Utilisation **0.60**; queue = 0.36 / 0.40 = **0.90** customers; wait = 0.90 / 9 = **0.10** periods.
4. Capacities **90** and **60**; bottleneck the second at **60**; utilisation 54 / 60 = **0.90**;
   gap **6** units.

## What is not built

- **No jurisdiction tax rules.** `tax_declared` applies the rates and taxable income you declare; it does
  not implement credits, exemptions, thresholds, NOLCO, withholding or filing. A taxation course needs
  the statute and your instructor's format.
- **No audit opinion or audit sampling, and no group consolidation.** Those need judgment or a declared
  group-accounting policy (goodwill and non-controlling interest), so they are named gaps rather than
  approximated.
- **No target or life-cycle costing, and no budget, planning or idle-capacity variances.** Activity-based
  costing and sales price/mix/yield variances are built; target costing and budget variances are not.
- **No standards setting.** The standard quantities and prices are yours; the method cannot say whether
  they are attainable.
- **No PDF, scan or image ingestion.** A CSV, TSV or XLSX file can be read; a scanned ledger cannot.

If your assignment requires one of these, say so in the limitations and show the working by hand.
