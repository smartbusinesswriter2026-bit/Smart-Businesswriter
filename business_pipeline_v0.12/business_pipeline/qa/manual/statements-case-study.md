# Case study — Ashgrove Supplies Ltd: preparing a full set of financial statements

**What this is.** A worked case for the **Financial statements** tile on the Accounting shelf, measured by
running it through the live workbench. Every figure below is the string the server returned; the page printed them and
did not compute one of them.

- **Tile:** Accounting → the first tile, *Financial statements* (`#/financial-statements`).
- **Backend:** `POST /api/cases/statements`, then `POST /api/cases/statements/{id}/export` for the download.
- **Record:** `95fe2965d8d7` (frozen, hash-checked, replayable).

> **Re-measured 2026-11-04**, on the tree that closed the reader's seams. What changed is stated at each place it
> changed, and §5 says what a careful reader should notice *now*. The first measurement of this case (2026-11-03,
> record `3221e482d95e`) is quoted where the two differ, so a reader can see the difference rather than take it on
> trust.

---

## 1. The case

Ashgrove Supplies Ltd is a small trading company. It buys equipment and resells it, and it is preparing its
first full set of financial statements for the year ended **31 December 2026**. Its bookkeeper has extracted the
trial balance at that date and pasted it, unchanged, into the tile.

**The instruction you paste** (17 lines, one account per line, credit balances marked `Cr`):

```
The following trial balance was extracted at 31 December 2026.
Equipment 30,000
Cash 15,900
Trade receivables 18,400
Inventory 22,600
Cost of sales 84,000
Wages 19,000
Rent 8,000
Utilities 3,200
Depreciation 3,000
Interest expense 1,200
Trade payables 14,800 Cr
Loan 12,000 Cr
Capital 20,000 Cr
Retained earnings 8,000 Cr
Sales 140,000 Cr
Other income 1,500 Cr
Accumulated depreciation 9,000 Cr
```

The tile read it with its **deterministic parser** (`problem_type: trial_balance`) and quoted the cue it acted on:
*"cue 'trial balance' in: The following trial balance was extracted at 31 December 2026."*

---

## 2. What the tile produced

### 2.1 The income statement

```
INCOME STATEMENT
2026-01-01 to 2026-12-31   USD
Revenue
  Other income                                            1,500.00
  Revenue                                               140,000.00
Total revenue                                           141,500.00
Expenses
  Cost of sales                                          84,000.00
  Depreciation                                            3,000.00
  Interest expense                                        1,200.00
  Rent expense                                            8,000.00
  Salaries expense                                       19,000.00
  Utilities expense                                       3,200.00
Total expenses                                          118,400.00
Net income                                               23,100.00
```

**Re-measured after the reader's seams were closed (2026-11-04, increment 1).** The figures are
identical to the first measurement — total expenses **118,400.00**, net income **23,100.00** — but the
expenses now arrive on their own lines instead of inside one "Operating expenses" line. The trial balance
named Wages, Rent, Utilities, Depreciation and Interest expense as five accounts, and the statement used to
print two lines for five accounts; it now prints five. Nothing about the arithmetic moved.

| Expense account in the trial balance | Printed as, before | Printed as, now |
|---|---|---|
| Wages 19,000 | Operating expenses 33,200.00 | Salaries expense 19,000.00 |
| Rent 8,000 | (same line) | Rent expense 8,000.00 |
| Utilities 3,200 | (same line) | Utilities expense 3,200.00 |
| Depreciation 3,000 | (same line) | Depreciation 3,000.00 |
| Interest expense 1,200 | Finance costs 1,200.00 | Interest expense 1,200.00 |

Reproduce with `python qa/manual/ashgrove-remeasure.py`.

### 2.2 The statement of changes in equity

```
STATEMENT OF CHANGES IN EQUITY
Capital
  Opening balance                                             0.00
  2026-12-31  capital                      20,000.00  the trial balance as given
  Closing balance                                        20,000.00

Retained earnings
  Opening balance                                             0.00
  2026-12-31  brought forward               8,000.00  the trial balance as given
  2026-12-31  profit for the period       141,500.00  closing: income to retained earnings (closing)
  2026-12-31  profit for the period     (118,400.00)  closing: expenses to retained earnings (closing)
  Closing balance                                        31,100.00

Total opening                                                 0.00
Total movement                                           51,100.00
Total closing                                            51,100.00
```

**Two lines changed since the first measurement**, and both were defects then:

| line | first measurement (2026-11-03) | now |
|---|---|---|
| the brought-forward movement | `2026-12-31  other  8,000.00` | `2026-12-31  brought forward  8,000.00` |
| the closing lines | `closing: income to retained earnin (closing)` — cut mid-word | `closing: income to retained earnings (closing)` |

### 2.3 The balance sheet

```
BALANCE SHEET
As at 2026-12-31   USD
Current assets
  Cash                                                   15,900.00
  Trade receivables                                      18,400.00
  Inventory                                              22,600.00
Total current assets                                     56,900.00
Non-current assets
  Property, plant and equipment                          21,000.00
Total non-current assets                                 21,000.00
Total assets                                             77,900.00
Current liabilities
  Trade payables                                         14,800.00
Total current liabilities                                14,800.00
Non-current liabilities
  Borrowings                                             12,000.00
Total non-current liabilities                            12,000.00
Total liabilities                                        26,800.00
Equity
  Capital                                                20,000.00
  Retained earnings                                      31,100.00
Total equity                                             51,100.00
Total liabilities and equity                             77,900.00
```

**Read it and check it yourself:** total assets **77,900.00** = total liabilities and equity **77,900.00**.
The property, plant and equipment line is **net** of the accumulated depreciation (30,000 − 9,000 = 21,000),
the retained earnings line carries the brought-forward 8,000 plus the 23,100 profit, and the current/non-current
split is the tile's own.

### 2.4 The checks — 11 of 11, with 2 not applicable

```
[ok] trial_balance_debits_equal_credits
[ok] assets_equal_liabilities_plus_equity
[ok] net_income_agrees_across_routes
[ok] opening_balances_equal_prior_closing
[ok] statement_lines_foot_to_totals
[ok] journal_hash_chain_intact
[ok] cash_flow_agrees_across_routes
[ok] retained_earnings_rollforward
[ok] income_expense_and_dividends_zero_after_closing
[ok] statement_internally_consistent
[ok] opening_balances_agree
```

The record carries the count as numbers: `checks_total: 11`, `checks_passed: 9`, `checks_na: 2`. Two further
checks are **not applicable** and say so rather than passing silently: the cash-flow agreement
checks, because a trial balance carries no flows.

### 2.5 The cash flow statement is withheld, and says why

> a cash flow statement needs the period's flows or a prior balance sheet, and the instruction supplies one
> trial balance; it is not presented rather than shown as a figure that would be wrong

That is the tile refusing to print a cash flow statement it cannot support. It is not a missing feature
dressed up: the whole cash balance would otherwise read as a period inflow.

### 2.6 The ratios — the "related problems" part

Add one line to the same instruction — `Also compute the liquidity ratios.` — and the tile computes **13
ratios** and names **2 it cannot**, with the reason:

| ratio | value | how it is computed |
|---|---|---|
| current_ratio | 3.845 | current assets / current liabilities |
| quick_ratio | 2.318 | (current assets - inventory) / current liabilities |
| cash_ratio | 1.074 | cash / current liabilities |
| gross_margin | 0.406 | (revenue - cost of sales) / revenue |
| net_margin | 0.163 | net income / revenue |
| return_on_assets | 0.297 | net income / total assets |
| return_on_equity | 0.452 | net income / equity |
| debt_to_equity | 0.524 | total liabilities / equity |
| equity_multiplier | 1.524 | total assets / equity |
| asset_turnover | 1.816 | revenue / total assets |
| receivables_days | 47.5 | receivables / revenue x 365 |
| inventory_days | 98.2 | inventory / cost of sales x 365 |
| payables_days | 64.3 | payables / cost of sales x 365 |

| ratio | why it is not computed |
|---|---|
| operating_margin | missing input: operating_profit |
| interest_cover | missing input: operating_profit |

A ratio the figures cannot support is **named and left out**, never estimated, and never shown as a zero.

**The first measurement printed these at 28 decimals** — `current_ratio: 3.844594594594594594594594595` — while
the core's own declared precision for a ratio is 3 dp. Two things changed, and they are worth naming separately:

- the ratio now prints at the precision the method declares (3 dp);
- **the instruction now reaches the trial-balance route.** It used to reach the balance-sheet-analysis route, which
  reads the same figures as *balances*: it printed **total assets 86,900** where the trial-balance route prints
  **77,900** — because the analysis route does not net the accumulated depreciation — and it hid the income
  statement and the statement of changes in equity. The same trial balance, two answers, nothing to say which was
  right. A trial balance is a trial balance even when the student also asks for ratios, and the more specific
  reading wins. That routing was changed on 2026-11-04; on the tree before it, the same input produced a different
  balance sheet.

### 2.7 The working

The **Working** toggle shows the full working behind the same record: the journal (the trial balance posted as
one period entry, then the closing entry), the trial balance, the account T-accounts with their movement and
closing balance, the derivations, the assumptions, and what was missing. The **Statements only** toggle shows the
three statements and nothing else. **Both views come from the same record** — the toggle chooses which recorded
text is shown and cannot change a number.

The record also carries the **notes**, in its own words:

```
NOTES
Reporting framework: US_GAAP
Basis: management accounts prepared from the entries you declared; not GAAP or IFRS statements and not assurance.
Net income for the period: 23,100.00
Declared policy changes: none
```

### 2.8 Downloading it

**Download the statements** posts to the server's own export endpoint:

```
POST /api/cases/statements/95fe2965d8d7/export  {"format": "statements_only"}
-> 200  {"format": "text", "view": "statements_only", "filename": "statements-95fe2965d8d7.txt",
         "text": "…2891 characters…"}
```

The page says so: *"Download the statements: statements-95fe2965d8d7.txt is ready."* **Download the working**
does the same with `{"format": "working"}`. A third button replays the record and reports whether it reproduces
exactly — the frozen record's own hash check.

---

## 3. The same case, with an error in it

Change one figure — cash 15,900 becomes 13,300, so the trial balance is out by 2,600 — and the tile refuses:

```
422 the accounts do not build: entries[0]: entry 'the trial balance as given' on 2026-12-31
    does not balance: debits 202700, credits 205300
```

and diagnoses it:

> **Out by: 2,600** — *(likely)* Your trial balance does not balance: debits 202,700.00, credits 205,300.00, a
> difference of 2,600.00.

Under it, the tile states what the check **cannot** prove, in its own words:

> It cannot tell you which of the two figures is right when both are declared. · It cannot catch an error of
> principle if the journal itself encodes the wrong treatment. · It cannot check amounts against source
> documents. · It corrects nothing.

No figure is produced for a problem it cannot solve. The diagnosis is a finding, not a fix.

---

## 4. What the tile names as missing

Even on a solved case, the record carries one named gap:

> **Not in the instruction:** The following trial balance was extracted at 31 December 2026. — *this line carries
> no account I can place, so it is shown here and left out of the statements*

That is the tile's own instruction line. It is shown and left out rather than dropped silently, which is the
behaviour that matters.

**What changed on 2026-11-04 is why it is left out.** The reader now recognises a *sentence* before it tries to
read it as an account name. Before, that line reached the account matcher and was refused because no account could
be placed; now it is recognised as a sentence — it opens with "The", carries no figure, and describes the
instruction rather than an account — and it is never posted. That is the same rule that stops "The owner invested
50,000 cash in the business" being posted as a Capital account, which would have counted the same money twice.

---

## 5. What a careful reader should notice

**The two defects this case carried on 2026-11-03 are both fixed, and they are worth reading anyway** — they are
what the output *used* to say:

1. ~~**The ratios print at 28 decimals.**~~ Fixed on 2026-11-04. The ratios print at the precision the core
   declares, 3 dp, and the instruction reaches the route that carries the statements as well (§2.6).
2. ~~**The brought-forward retained earnings is labelled "other."**~~ Fixed on 2026-11-04. It is labelled
   `brought forward`, and the closing lines are no longer cut mid-word (§2.2).

**What is still worth noticing, measured on 2026-11-04:**

- **The cash flow is withheld, not guessed.** A trial balance carries no flows, so the tile says so in its own
  words rather than showing the whole cash balance as an inflow (§2.5).
- **One line is named as unplaceable** rather than dropped (§4).
- **A ratio the figures cannot support is named and left out** — `operating_margin` and `interest_cover`, both for
  the same missing input (§2.6).
- **The tile reads one account per line.** A ratio question written as a prose list ("cash 5,000, trade
  receivables 2,000, …") is refused; the same figures one per line are solved. This is the shape the page's own
  copy shows, and it is a shape, not a limit.
- **An adjustments narrative, and any narrative the deterministic reader does not recognise, still needs a model.**
  §6 says which.

---

## 6. The limits of this case, stated plainly

**One trial balance, one period, USD.** The tile read this with its deterministic parser, and no model was
configured when it was measured.

**What the tile can read without a model, measured on 2026-11-04** (posted to `POST /api/cases/statements`, no
model configured):

| the student pastes | what came back |
|---|---|
| this trial balance | **201 solved** — 11 checks, all three statements, cash flow withheld and named |
| this trial balance + "Also compute the liquidity ratios." | **201 solved** — the same three statements and 13 ratios |
| a five-clause transactions narrative | **201 solved** — 11 checks, the period taken from the text's own dates, rent and salaries on their own lines |
| an exam question with a preamble before the figures | **201 solved** — the preamble is named as a line it could not place, and the figures are read |
| a ratio question, one account per line | **201 solved** — the balance-sheet-analysis engine |
| an adjustments narrative (depreciation + accrual) | **400** "no model is configured, so only a trial balance can be read. Set DEEPSEEK_API_KEY (or BP_LLM_PROVIDER + BP_LLM_MODEL)." |
| a cash-flow narrative | **400** "closing with abnormal balances needs a human decision: 1500 (Property, plant and equipment)" |
| a trial balance in EUR | **400** "this product answers in USD only" (a deliberate rule) |

**What that table means.** The reader reads a **trial balance** and a **transaction narrative**, with no model at
all. It does **not** derive the adjusting entries — depreciation, prepaid amortisation, tax — because that is the
model's job in the plan layer, and a tile with no model configured says so rather than guessing. The cash-flow
narrative is refused by name: the figures it states do not close, and the refusal names the account that is
wrong.

**The first measurement of this case (2026-11-03) said the opposite**, and the difference is the increment this
case documents. Then: a single-year transactions narrative was refused as "more than one period", an adjustments
sentence as "a comparative", a ratio question as "an account has no code", a cash-flow narrative as "the chart
needs exactly one retained-earnings account" (after 16.9 seconds), and an exam preamble was read as account rows —
and the tile's own copy said it read "one trial balance, and only one". None of those five refusals is a refusal
now, and the copy no longer says it.

- **No cash flow statement** from a trial balance, by design — see §2.5.
- **The file is a `.txt`**, not a Word document. The export endpoint returns text; it is the server's contract.
- **The numbers are only as good as the trial balance.** The tile reads balances; it does not know whether the
  bookkeeper's figure is right. That is the check it says it cannot do (§3).

---

*Reproduce the whole case: `python qa/manual/ashgrove-remeasure.py` (the statements) and
`python qa/manual/reader-seams-probe.py` (the reader's seams).*
