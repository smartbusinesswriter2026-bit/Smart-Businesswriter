# Case study — Ashgrove Supplies Ltd: preparing a full set of financial statements

**What this is.** A worked case for the **Financial statements** tile on the Accounting shelf, measured by
running it through the live workbench on 2026-11-04. Every figure below is the string the server returned; the
page printed them and did not compute one of them.

- **Tile:** Accounting → the first tile, *Financial statements* (`#/financial-statements`).
- **Backend:** `POST /api/cases/statements`, then `POST /api/cases/statements/{id}/export` for the download.
- **Record:** `3221e482d95e` (frozen, hash-checked, replayable).

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

The tile read it with its **deterministic parser** (`reading_source: parser`, `problem_type: trial_balance`) and
quoted the cue it acted on: *"cue 'trial balance' in: The following trial balance was extracted at 31 December
2026."*

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
  Finance costs                                           1,200.00
  Operating expenses                                     33,200.00
Total expenses                                          118,400.00
Net income                                               23,100.00
```

### 2.2 The statement of changes in equity

```
STATEMENT OF CHANGES IN EQUITY
Capital
  Opening balance                                             0.00
  2026-12-31  capital                      20,000.00  the trial balance as given
  Closing balance                                        20,000.00

Retained earnings
  Opening balance                                             0.00
  2026-12-31  other                         8,000.00  the trial balance as given
  2026-12-31  profit for the period       141,500.00  closing: income to retained earnin (closing)
  2026-12-31  profit for the period     (118,400.00)  closing: expenses to retained earn (closing)
  Closing balance                                        31,100.00

Total opening                                                 0.00
Total movement                                           51,100.00
Total closing                                            51,100.00
```

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

Two further checks are **not applicable** and say so rather than passing silently: the cash-flow agreement
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
| current_ratio | 3.844594594594594594594594595 | current assets / current liabilities |
| quick_ratio | 2.317567567567567567567567568 | (current assets - inventory) / current liabilities |
| cash_ratio | 1.074324324324324324324324324 | cash / current liabilities |
| gross_margin | 0.4063604240282685512367491166 | (revenue - cost of sales) / revenue |
| net_margin | 0.1632508833922261484098939929 | net income / revenue |
| return_on_assets | 0.2965340179717586649550706033 | net income / total assets |
| return_on_equity | 0.4520547945205479452054794521 | net income / equity |
| debt_to_equity | 0.5244618395303326810176125245 | total liabilities / equity |
| equity_multiplier | 1.524461839530332681017612524 | total assets / equity |
| asset_turnover | 1.816431322207958921694480103 | revenue / total assets |
| receivables_days | 47.46289752650176678445229681 | receivables / revenue x 365 |
| inventory_days | 98.20238095238095238095238094 | inventory / cost of sales x 365 |
| payables_days | 64.30952380952380952380952381 | payables / cost of sales x 365 |

| ratio | why it is not computed |
|---|---|
| operating_margin | missing input: operating_profit |
| interest_cover | missing input: operating_profit, interest_expense |

A ratio the figures cannot support is **named and left out**, never estimated, and never shown as a zero.

### 2.7 The working

The **Working** toggle shows the full working behind the same record: the journal (the trial balance posted as
one period entry, then the closing entry), the trial balance, the account T-accounts with their movement and
closing balance, the derivations, the assumptions, and what was missing. The **Statements only** toggle shows the
three statements and nothing else. **Both views come from the same record** — the toggle chooses which recorded
text is shown and cannot change a number.

### 2.8 Downloading it

**Download the statements** posts to the server's own export endpoint:

```
POST /api/cases/statements/3221e482d95e/export  {"format": "statements_only"}
-> 200  {"format": "text", "view": "statements_only", "filename": "statements-3221e482d95e.txt", "text": "…2684 characters…"}
```

The page says so: *"Download the statements: statements-3221e482d95e.txt is ready."* **Download the working**
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

That is the tile's own instruction line. The parser saw a line with a number in it, could not place it as an
account, and **named it rather than dropping it silently**. It is correct behaviour and it is also the visible
edge of the preflight defect in §5.

---

## 5. What a careful reader should notice

Two things in the output above are defects, not features. Both are in `src/**` — the computation lane's — and
both are recorded as `[computation]` requests in `docs/WORKLOG.md`:

1. **The ratios print at 28 decimals.** `current_ratio: 3.844594594594594594594594595`. The core's own
   declared precision for a ratio is **3 dp** (`_ratio_typing` → `("ratio", 3)`), and every other shelf prints
   ratios at 3 dp. The statements record stores the **raw float** from the method's output rather than the
   formatted value, so the tile shows more decimals than the method declares. The page must not round it — the
   browser never rounds a figure — so the fix belongs where the record is packed.
2. **The brought-forward retained earnings is labelled "other."** In §2.2 the 8,000 movement line reads
   `2026-12-31  other  8,000.00  the trial balance as given`. It is the retained earnings brought forward, and
   the equity roll-forward could name it. The closing lines are also truncated mid-word (`retained earnin`).

Neither changes a number. Both change what a student reads.

---

## 6. The limits of this case, stated plainly

- **One trial balance, one period, USD.** The tile read this with its deterministic parser. A transaction
  narrative, an adjusting-entry problem, a cash-flow problem or an exam question with a preamble in front of the
  figures needs the model reader, and `bp/server.py` says it plainly: *"no model is configured (set
  BP_OPENGO_API_KEY), so only a trial balance can be read."* Measured: a single-year transactions narrative is
  refused as "more than one period", an adjustments sentence as "a comparative", and an exam question's own
  words are read as account rows. The reproductions are in `docs/WORKLOG.md`.
- **No cash flow statement** from a trial balance, by design — see §2.5.
- **The file is a `.txt`**, not a Word document. The export endpoint returns text; it is the server's contract.
