# Portfolio Lab for finance students

This guide teaches the **Portfolio Lab** by doing: four worked cases, each shaped like an
assignment a finance student actually brings, each with the exact buttons to press and the result
to expect. It assumes senior-high ABM, first-year undergraduate or intermediate investments level.
The method conventions (rates as decimals, returns per period) are in
`docs/FINANCE_STUDENT_GUIDE.md`; this guide is about the book, the evidence and the report.

> **What this page is.** A record of decisions and a sourced evidence workbench: you declare what
> you hold and why, the app stores each price with its date and source, the frozen core computes the
> valuation and the risk figures, and the report says where every number came from.
>
> **What it is not.** It does not recommend a stock, rank a "best" buy, forecast a price, or tell
> you what to do. A shortlist is evidence you interpret; a blank cell is a **named gap**, never a
> zero and never an estimate. Do not write "the app says to buy" in a paper: the app never says it.

## Before you start: four habits

1. **Declare, don't guess.** A holding is your decision, with a one-line reason. A price the app
   cannot source you read from a source you name and type in yourself.
2. **One date, one valuation.** A snapshot is immutable: it fixes the NAV and the weights for that
   date so a professor can re-check it later. To correct a book, take a new snapshot on a new date.
3. **Read a gap properly.** "n/a" plus a reason is information; hide it and you have invented data.
   Copy the gap into your paper's limitations paragraph.
4. **The calculator does the maths, not you.** Prefill fills the fields; you press `=` in the
   Business Calculator. Nothing is computed in the browser.

## Reading the page

**The landing page** (`Portfolio` in the rail) has, top to bottom:

- **Investment paper** / **Mock fund journal** — the two ways to start a book.
- **Your books** and **Create a book** — the stored books and the form for a new one
  (*Portfolio name*, *Base currency*, *Benchmark*, *Mode*, *Objective*, *Team*).
- **Before you buy → Find and screen candidates** — the lab itself, in three tabs:
  **Watch list and prices**, **Find candidates**, **Evaluate**.
- **How to choose what you hold** — the six-step guide (collapsed).
- **Learn by example** — these four cases, in the app.

**Inside a book** the tabs are **Overview**, **Find candidates**, **Holdings**,
**Prices and snapshot**, and — for a fund — **Journal and return**. The hero shows the latest
snapshot's **Net asset value**, **Invested**, **Cash**, **Top three** concentration and, for a fund,
the **Time-weighted return**. *Export the report* is on the hero.

---

## Case 1 — "Which stocks should I put in my portfolio paper?"

**The assignment.** *"Choose three listed companies for a paper portfolio and justify the choice
with sourced data."* The trap is picking from memory. The lab makes you look at the same criteria
for every candidate, and it shows what it could not source.

**You need:** nothing but the page. A quote key must be configured server-side for live prices (the
provider is shown at the top of the lab); SEC fundamentals need no key.

**Click by click**

1. Rail → **Portfolio**.
2. Scroll to **Before you buy → Find and screen candidates**. Under *Quote provider* keep
   **Alpha Vantage** (or choose **Massive** if that is the key configured).
3. Click the **Watch list and prices** tab.
4. In **Add symbols to the watch list**, type your candidates separated by commas, e.g.
   `AAPL, MSFT, VOO` — any quoteable ticker works, not just the reference list.
5. Click **Add symbols**. Each one is recorded at today's sourced price; the line under the box
   says *Added and recorded: …*, *Already on the watch list: …* or *Could not add: … (reason)*.
6. Click the **Find candidates** tab. Click **Use my watch list** to copy your tickers into
   *Symbols to screen*.
7. Choose **Sort by** (e.g. *market cap*, *P/E*, *one-day return*), tick **Include fundamentals**,
   leave *Derived (SEC + Massive)* and click **Screen these symbols**.

**You should see** a table headed *Shortlist (n) — sourced, not a recommendation*, one row per
symbol, with a **Gaps** column. From a live run on this machine (2026-11-02):

| Symbol | Price | 1-day | Mkt cap | P/E | ROE | Gaps |
|---|---|---|---|---|---|---|
| AAPL | 344.63 | -1.23% | 5.03T | 44.90 | 1.5191 | mean, volatility and Sharpe need at least three recorded returns; … |
| MSFT | 521.91 | n/a | 3.88T | n/a | n/a | the change needs a previous close, which this quote did not carry; … |
| VOO | 694.81 | -1.77% | n/a | n/a | n/a | fundamentals not reported for a fund; … |

Your numbers will differ with the provider and the date — that is the point of the source line.

**Write this in your paper.** For each chosen holding, the criterion you used, the sourced value and
its date, and **the gap**. Example sentence: *"AAPL traded at 344.63 on 2026-10-30 (Alpha Vantage
quote); its P/E of 44.90 is derived from SEC net income and Massive market cap, not a vendor
profile. One-day return is not reported for MSFT because the provider returned no previous close."*

**Then, to make it a book:** *Holdings* tab → **Add a holding** (symbol, shares, cost basis,
**Why you hold it**) for each name; the reason is printed in the report under *Holdings and
rationale*. Add a price for each on **Prices and snapshot**, then **Create the snapshot**.

**What it does not do.** It will not tell you which of the three is "best", and a listing in the
reference list is not a recommendation. Ranking is yours; the app only ranks on the criterion you
declare.

---

## Case 2 — "Value my portfolio on one date and hand in the report"

**The assignment.** *"State your holdings, value them on a date, report the weights and comment on
concentration."* This is the `portfolio_valuation` method: NAV, invested value, cash, weights and
the top-three concentration, plus twelve pass/fail checks behind the numbers.

**You need:** the holdings (symbol, shares, cost basis), one price per holding for the valuation
date, and the cash balance you declare.

**Click by click**

1. Rail → **Portfolio**. Under **Create a book**: *Portfolio name* e.g.
   `Investment paper — consumer stocks`, *Base currency* `USD`, *Benchmark* optional (`S&P 500`),
   *Mode* = **Paper portfolio (one valuation)**, then click **Create portfolio**.
2. The book opens on **Overview**. Click **Add holdings** (or the **Holdings** tab).
3. **Add a holding** four times, e.g. `AAPL` 20 shares cost 150 — *Why you hold it:* "Services
   exposure; largest position, about half the book"; `MSFT` 8 shares cost 300 — "Cloud and
   enterprise software"; `VOO` 5 shares cost 400 — "Diversified index core".
4. Click the **Prices and snapshot** tab. Set **Snapshot date** to the valuation date. Enter
   **Cash (USD)**, e.g. `0`.
5. Either type each price in the **Declared prices** row, or click **Fetch prices (Alpha Vantage)**
   (it tries Alpha Vantage, then Massive, then QVeris — still check each price). You can also paste
   `SYMBOL,PRICE` rows into **Paste or import prices** and click **Import prices**.
6. Click **Create the snapshot**. A banner confirms *Snapshot created*; the page re-renders with the
   valuation.

**You should see** (live example, 2026-11-02, USD 0 cash):

- **Net asset value USD 14,541.93**; **Invested 14,541.93**; **Cash 0**; **Top three 1**.
- A *Valuation* table: AAPL 20 × 344.63 = 6,892.60 (weight 0.4740); MSFT 8 × 521.91 = 4,175.28
  (0.2871); VOO 5 × 694.81 = 3,474.05 (0.2389).
- **Download the report (.docx)** at the bottom of the **Prices and snapshot** tab, and
  **Export the report** on the hero.

**Write this in your paper.** NAV and its date, the weights, the **top-three concentration of 1**
(100% — with three holdings the top three *are* the book, so it says nothing about diversification;
it matters when you hold more), and the checks the report publishes. State the conventions: one base
currency, long-only, no FX, no fees, tax or dividends, and the snapshot is a valuation, not a sale
price.

**What it does not do.** It does not fetch a price silently — every stored price keeps its date and
source, and a missing price blocks the snapshot with the symbols named. Re-creating a snapshot on a
date that already exists is refused: the record is the product.

---

## Case 3 — "Run a mock fund for the semester and report a time-weighted return"

**The assignment.** *"Run a paper fund for several weeks, record your decisions and report the
time-weighted return, with a benchmark if you declared one."* This is where the lab exceeds a
one-shot chat answer: it keeps the **weeks**, the **flows** and an **immutable dated record**.

**You need:** a fund-mode book, at least **two dated snapshots**, a journal entry per period with
the external **flow** you declare, and (optionally) the benchmark level for each period.

**Click by click**

1. Rail → **Portfolio** → **Mock fund journal** (or set *Mode* = **Mock fund (weekly journal)** in
   the form) and click **Create portfolio**. Declare the benchmark (`S&P 500`) if you will report one.
2. Each week: **Holdings** to change positions → **Prices and snapshot** → set that week's
   **Snapshot date** → enter prices (or **Fetch prices**) → **Create the snapshot**.
3. After each snapshot, open **Journal and return** and fill **Period ends**, **Flow** (money you
   added or withdrew — the app treats it as occurring at the start of the period), **Benchmark
   level** (optional) and **Your note** (what you did and why) → **Save the entry**.
4. Repeat weekly. When two snapshots exist, click **Compute the return**.

**You should see** (live example, four snapshots 2026-10-16 → 2026-11-03, one 500 deposit):

- **Time-weighted return -0.10235** — printed as a **ratio**, so this means **-10.235%** across
  **3 periods**.
- *Start NAV 15,700 | final NAV 14,541.93 | flow 500*, then a *Periods* table with each period's
  start NAV, end NAV, flow, period return and benchmark return.
- `best_period 0.0204`, `worst_period -0.1203`: the two weeks to discuss in your paper.
- The conventions line: the flow sits at the start of its period, period return is
  `(end − start − flow) / (start + flow)`, the TWR chains those returns, no fees/tax/dividends, no
  forecast.

**Write this in your paper.** The TWR *as a ratio and as a percentage*, the number of periods, the
NAV path, the flows (with the dates you added or withdrew), the best and worst period with the
decision note you wrote at the time, and the benchmark comparison *only* if you declared benchmark
levels for every period. Note the convention that flows sit at period start.

**What it does not do.** It does not decide the trades, and it does not annualise the TWR or apply
fees, tax or dividends — you state the convention you used. Missing journal entries are treated as a
zero flow, which is a declaration you should make explicit in the paper.

---

## Case 4 — "Compute the risk and return of my stock (and a two-asset portfolio)"

**The assignment.** *"For your chosen stock, report the mean return, standard deviation, Sharpe
ratio and a VaR at 95%; then do the same for a two-asset portfolio."* Those are frozen methods
(`risk_metrics`, `portfolio_analysis`). The lab's job is to build the **returns series** and hand
exact inputs to the calculator — it never runs the method for you.

**You need:** recorded prices. One snapshot is one price; a returns series needs several. **Seed 30
days** pulls daily bars where the provider has them; or click **Record price** once per day/week.
Risk metrics need **at least 3 returns** (4 prices); `portfolio_analysis` needs **3 returns on
shared dates** (4 shared snapshot dates).

**Click by click**

1. Rail → **Portfolio** → **Before you buy → Find and screen candidates**.
2. **Watch list and prices** tab → add your ticker(s) → for each, click **Seed 30 days** (30 daily
   bars) or **Record price** on the days you meet. The row shows *history* and *risk-ready*.
3. Click the **Evaluate** tab.
4. *Single asset risk*: choose the **Instrument** (it lists your tracked series), set **Risk-free
   rate (decimal)** — e.g. `0.02` for 2% — and click **Prefill single-asset risk**.
5. If the card says *Inputs ready to confirm*, click **Open in the Business Calculator**, then press
   `=` in the calculator to run `risk_metrics`.
6. *Two-asset portfolio*: choose **Asset A**, **Asset B** and, if you have one, a **Benchmark**;
   click **Prefill two-asset portfolio**, then **Open in the Business Calculator** and press `=`.

**You should see** a ready single-asset prefill (live example: AAPL, 24 recorded returns,
`confidence 0.95`) listing the exact `returns` array and `confidence` that `risk_metrics` will use.
For the two-asset portfolio before enough shared dates, a **named gap** instead of invented inputs:

> *"portfolio_analysis needs at least three returns, so at least four shared snapshot dates; 1 shared
> so far"* and *"returns_market is required: track a benchmark symbol and pass its id as market"*.

**Write this in your paper.** The method id and its tier, the exact inputs (paste the array from the
prefill card), the risk-free rate you declared, the number of returns (and that they are **per
period**, not annual), and the gap if it is not ready. In the Calculator result, the honesty banner
lists what was not done — quote it.

**What it does not do.** It does not annualise, impute missing prices, or substitute a shorter window
silently. A short series stays a named gap; you either record more prices or say the metric is not
reported.

---

## How to read a gap (never a zero)

| What you see | What it means | What to do |
|---|---|---|
| "the change needs a previous close, which this quote did not carry" | one quote cannot show a change | record another day's price, or omit the row |
| "mean, volatility and Sharpe need at least three recorded returns" | too short a history | **Seed 30 days** or record more days |
| "fundamentals not reported for a fund" | P/E and ROE belong to companies | leave them blank in the paper |
| "portfolio_analysis needs at least three returns, so at least four shared snapshot dates" | the two series do not overlap enough | record both on the same dates |
| "returns_market is required" | CAPM/market comparison needs a benchmark | track a benchmark symbol, choose it as *Benchmark* |
| "a snapshot for <date> already exists" | snapshots are immutable | take the next date |

## What a professor can verify in your submission

- Each price carries a **date and a source**; each retrieval carries a **response hash**.
- The snapshot is **dated and immutable**, and the DOCX report reproduces the stored valuation.
- The **checks** (6 for valuation, 6 for performance) are published, pass/fail, in the report.
- The **decision journal** records what you did and why, in the week you did it.
- Every **gap** you report is the gap the app showed, not a rounded-over blank.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Could not add: X (… key is configured)" | the quote provider key is not set server-side; tell the operator, or record prices manually |
| "Symbols to screen" is empty on **Find candidates** | click **Use my watch list**, or type tickers |
| **Create the snapshot** refuses with missing prices | fill every holding's price (or **Fetch prices**), then retry |
| **Open in the Business Calculator** is missing | the prefill is not ready — read the gap card above the inputs |
| Wrong weights on the hero | the snapshot was taken before a holding change; take a new snapshot on a new date |
| Report will not export | a snapshot is required first; the button is disabled until one exists |

## What the lab cannot do

No advice, no ranking or price target, no forecast. No FX conversion (one base currency), no fees, tax,
dividends or corporate actions, long-only, and no short selling. It does not value a private company
or a market with no free official feed — enter those figures manually and say where they came from.
The watch list is one list for the whole machine, not one per book.

## Glossary

- **Book / portfolio** — the declared holdings, cash and base currency you are valuing.
- **Watch list** — tracked symbols with their recorded price history; shared across books.
- **Snapshot** — an immutable dated valuation of a book (NAV, weights, concentration, checks).
- **Benchmark** — the level you declare per period for comparison; optional, and never inferred.
- **Flow** — money you added to or withdrew from the fund; treated as occurring at period start.
- **TWR** — time-weighted return: the chained product of period returns, printed as a ratio.
- **Named gap** — a value the app will not invent, printed with the reason it is missing.
- **Prefill** — the exact calculator inputs built from your recorded series; it never runs the method.
