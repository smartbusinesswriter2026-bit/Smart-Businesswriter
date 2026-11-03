# The statements render layer — brief for MiniMax

> **Status 2026-11-04 (build 1.96).** The computation lane is done for the shapes the tile supports:
> the ledger is always built in full, the request decides what is rendered, and the record carries
> the audit trail. What is missing is the **presentation**: today the spreadsheet export is a text
> dump (one string per line in a single sheet). This brief is the contract for turning it into a real
> workbook. Read `docs/TIPS_FINANCIAL_STATEMENTS.md` §5 first — it is the reasoning behind the rules
> below. Nothing here asks you to compute a figure.

---

## 1. What you own, and what you do not

You own:

- the **declarative line spec** renderer: a walk over account metadata that produces statement rows;
- the **Excel workbook** the student downloads (`.xlsx`), including its sheets, columns, number
  formats, subtotals and labels;
- the presentation of the working (journal, trial balance, checks) as a separate place from the
  submission view.

You do **not** own, and may not change:

- any number, sign, rounding, period, currency or label that came from the frozen record;
- which statements are rendered — that is the request (`record["requested"]`);
- the articulation rules — they already ran, and the record says which checks passed.

If something is missing, it is named as missing. It is never filled, estimated or plugged.

---

## 2. Where it plugs in today

`src/bp/product/spreadsheets.py` already builds `.xlsx` bytes **by hand** (`to_xlsx`, `export_xlsx`)
with a deterministic timestamp, so two exports of the same record are byte-identical. It has no
third-party dependency, and that is a hard constraint: `tests/test_product_boundary.py` fails if any
product module imports `openpyxl`, `xlsxwriter`, `pandas` or `docx`. The pattern to follow is already
there — `zipfile` plus XML strings.

What it does with a statements record today (`_accounting_rows`) is the gap:

```text
Statements sheet (one column, one string per line)
  INCOME STATEMENT
  2026-01-01 to 2026-12-31   USD
  Revenue
    Revenue                                                 9,000.00
  ...
```

That is a screenshot of text, not a spreadsheet. Replace it with typed cells, one row per line of the
statement, amounts in their own right-aligned column, and subtotal rows that are distinguishable from
detail rows.

---

## 3. The record you receive

The tile stores a frozen record (`format: "bp-statements/1"`, `verify.freeze()` adds a
`plan_hash`). The renderer reads it; it never reconstructs it.

```json
{
  "format": "bp-statements/1",
  "solved": true,
  "refusal": null,
  "instruction": "...", "instruction_hash": "sha256:...",
  "problem_type": "trial_balance | transactions | adjustments | incomplete_records",
  "why": "cue 'trial balance' in: ...",
  "reading": { "...": "the parsed reading, with quotes" },
  "reading_source": "parser | council | plan",
  "requested": ["IS", "RE", "BS", "CF"],
  "computed":  ["IS", "RE", "BS", "CF"],
  "hidden":    [],
  "warnings":  [],
  "core": { "scalars": { "...": "decimal strings" }, "appendix": { "...": "..." } },
  "statements": {
    "trial_balance": "...", "income_statement": "...", "balance_sheet": "...",
    "equity": "...", "notes": "...",
    "cash_flow": null, "cash_flow_withheld_because": "..."
  },
  "statements_only": "...",
  "working": { "journal": "...", "trial_balance": "...", "t_accounts": {},
               "derivations": [], "assumptions": [], "missing": [] },
  "diagnosis": { "...": "..." },
  "checks": [ { "name": "...", "ok": true, "detail": "..." } ],
  "ratios": null
}
```

Where the pieces live:

| You want | Read |
|---|---|
| the four statement **texts** (a reference rendering) | `record["statements"][key]`, and `appendix["statements_export"]` |
| the **typed** trial balance | `appendix["trial_balance"] = {"rows": [...], "total_debits": ..., "total_credits": ...}` |
| the **typed** journal | `appendix["journal"]` (list of entries with `date`, `description`, `lines[]`) |
| balance-sheet **groups and totals** | `appendix["balance_sheet_groups"] = {"groups": {...}, "totals": {...}}` |
| the cash flow, typed | `appendix["cash_flow"]` (see §6) |
| the equity roll, typed | `appendix["equity_statement"]` (`accounts`, `by_kind`, `total_opening`, `total_closing`, `total_movement`) |
| the checks the renderer must not contradict | `record["checks"]`, `appendix["checks"]`, `appendix["cash_flow"]["checks"]` |
| the account metadata | `record["spec"]["chart"]` (see §4) |
| the note text | `appendix["statements_export"]["notes"]` |

`statements_export` keys: `trial_balance`, `income_statement`, `balance_sheet`, `cash_flow`, `notes`,
`combined`. A key that is empty means the statement was not produced — not "zero".

---

## 4. The account metadata is the contract

Every line a statement shows comes from a chart account. The chart is `record["spec"]["chart"]`, one
entry per account:

```json
{"code": "1510", "name": "Accumulated depreciation", "type": "asset",
 "line": "Property, plant and equipment", "role": "", "section": "non_current",
 "activity": "", "contra": true}
```

| Field | Meaning for the renderer |
|---|---|
| `code` | the account's identity; never invent one |
| `name` | the account name; a statement line uses `line`, not `name` |
| `type` | `asset`, `liability`, `equity`, `income`, `expense` — decides the statement |
| `line` | the **statement line** the account rolls into ("Property, plant and equipment") |
| `role` | `cash`, `capital`, `retained_earnings` or empty; `cash` drives the CF endpoints, `retained_earnings` drives the equity roll |
| `section` | `current` / `non_current` for assets and liabilities; empty elsewhere. An empty section on an asset or liability is refused, because it would silently misclassify the cash flow |
| `activity` | `operating`, `investing`, `financing` or empty — **this is the cash-flow bucket** (Tip 4's `cf_bucket`); empty falls back to the type default |
| `contra` | true for accumulated depreciation; the line is presented net of it |

So the IS is `type in (income, expense)` grouped by `line`; the BS sections are `section`, ordered
`current` then `non_current`, with `contra` accounts netted into their line; the CF buckets are
`activity`; the equity roll is accounts whose `type` is `equity` or whose `line` is a retained-earnings
line. **No per-statement hardcoded account list anywhere.** If a rule needs an account name to work, the
rule is wrong.

---

## 5. The four statements, as line specs

Each statement is an ordered list of rows. A row is one of:

| Kind | Rendered as |
|---|---|
| heading | the statement title, the period, the currency |
| group | a section heading ("Current assets", "Expenses") |
| detail | a label from `line` and an amount, indented |
| subtotal | a bold label and an amount, ruled above |
| total | double-ruled, bold |
| blank | a spacer, no content |
| note | a pointer, not a number ("see note 3") — only if the record carries one |

**Income statement** (`IS`): heading → `Revenue` group → revenue lines → `Total revenue` →
`Expenses` group → expense lines → `Total expenses` → `Net income`. Costs of sales and operating
expenses are separate lines only if the chart's `line` distinguishes them; do not invent a split.

**Statement of changes in equity** (`RE`, record key `equity`): opening balance → movements by kind
(capital introduced, net income, dividends, brought forward) → closing balance. Use
`appendix["equity_statement"]`; `by_kind` is already the grouping. The brought-forward movement is
labelled "brought forward" — build 1.90 fixed it; do not reintroduce "other".

**Balance sheet** (`BS`): `As at <period end>` → current assets → total → non-current assets →
total → total assets → current liabilities → total → non-current liabilities → total → total
liabilities → equity lines → total equity → total liabilities and equity. The accounting equation must
visibly hold: `total_assets == total_liabilities + total_equity`. If the record says
`assets_equal_liabilities_plus_equity` failed, do not render a balance sheet at all — the record will
already be a refusal.

**Cash flow** (`CF`): `operating`, `investing`, `financing` sections, each with a total; then
`Net change in cash`; then opening cash, closing cash. The indirect reconciliation (net income →
adjustments → working-capital movement → operating cash) is present in
`appendix["cash_flow"]["detail"]` and must be shown in the working, not invented.

A statement that the record did not render (`statements[key]` empty, or `cash_flow` null) is **not a
sheet**. It may appear only inside the working, clearly labelled as withheld, with
`cash_flow_withheld_because` verbatim.

---

## 6. The three cash-flow reconciliations

These already ran in `bp.statement_plan.articulation()` and `ledger` before the record was frozen. The
renderer's job is to show them, and to refuse to print a cash-flow sheet whose reconciliations are not
all true.

1. **CFO + CFI + CFF = the change in cash.** `operating + investing + financing == net_direct` and
   `== net_indirect`.
2. **That change equals the balance-sheet cash movement.** Closing cash on the BS minus opening cash
   (the opening is the trial balance's cash opening; with none, it is zero and the record says so).
3. **Ending cash in the statement equals the cash line on the balance sheet.** The account whose
   `role` is `cash`.

The typed evidence is `appendix["cash_flow"]`:

```json
{"operating": "7000", "investing": "0", "financing": "0",
 "net_direct": "7000", "net_indirect": "7000",
 "detail": [{"date": "...", "description": "...", "activity": "operating", "amount": "7000"}],
 "checks": [["cash_flow_agrees_across_routes", true, "direct 7000, indirect 7000"]],
 "flags": [{"kind": "mixed_classification", "entry": "...", "detail": "..."}]}
```

If any check in `checks` is false, the sheet is not written and the workbook says why, using the same
wording the record uses. A `flags` entry (`mixed_classification`, `cash_to_cash_transfer`) is shown in
the working, not on the statement — it is provenance, not a figure.

---

## 7. Partial requests

`record["requested"]` is the rendered set. `record["computed"]` is everything the ledger had to
compute. `record["hidden"]` is `computed - requested` and explains itself.

- The workbook contains one sheet per **requested** statement. Nothing else.
- The Working sheet may show the full journal and trial balance (they are always computed), but it
  must not promote a hidden statement to a statement sheet. A hidden BS on an IS-only request is
  `hidden: ["RE", "BS"]`; rendering its text as a fourth sheet would contradict `verify_output()` and
  the student's instruction.
- A withheld CF (`cash_flow: null`) that was requested appears as a named gap in the Working sheet
  with its reason. It never appears as an empty cash-flow sheet.

Default behaviour stays the full set (`requested` = all four); partial rendering is opt-in.

---

## 8. What you may not change

Hard list, enforced by review and by tests:

1. **No recomputation.** Every cell is copied from the record. The browser and the workbook never do
   arithmetic; nor does the renderer. A subtotal is taken from the record, not summed from the cells
   (a SUM formula is acceptable only when it is over exactly the cells shown *and* equals the stored
   total — write the stored value if in doubt).
2. **No sign flipping.** Signs are settled at the trial-balance boundary. An amount is written as the
   record holds it. Contra accounts are netted by the record's own grouping, not by the renderer.
3. **No rounding changes.** `record["spec"]["places"]` (or the record's value strings) decide the
   decimals. Do not re-quantise; do not drop trailing zeros; do not switch to whole units.
4. **No invented rows.** No "other", no plug, no balancing line, no "miscellaneous". A gap is named.
5. **No relabelling.** Statement lines are the chart's `line`. The notes text is the record's.
6. **No currency or locale drift.** The record is USD with neutral places; do not add a symbol the
   record does not carry, and do not localise number separators.
7. **No template instructions in the file.** No "insert your figure here", no "replace with your
   company name". A student downloads a finished statement or a named refusal.
8. **No third-party dependency.** `zipfile` + XML, as `to_xlsx` already does.
9. **Byte-stability.** Two exports of the same record must be identical, as today (fixed zip
   timestamp). A renderer that embeds `now()` breaks the replay tests.

---

## 9. Format rules that make it a spreadsheet

- One sheet per requested statement, named after it (`Income statement`, `Balance sheet`,
  `Changes in equity`, `Cash flow`), then `Working`, then `Notes`.
- Column A is the label, column B the amount (right-aligned). A third column for note references only
  when the record has them.
- Detail rows indent one level; group headings are bold; subtotals bold with a top border; totals bold
  with a double bottom border. Use the workbook's `styles.xml`, not per-cell inline styling.
- Amounts are **numbers**, formatted with the record's decimal places and a thousands separator; a
  negative is `-1,234.00` or `(1,234.00)` — pick one and use it everywhere.
- A blank row between sections, never between a subtotal and its total.
- Freeze the header row; set column A width from the longest label (bounded); do not merge cells.
- The Working sheet: journal (date, description, account, debit, credit), trial balance (account,
  debit, credit, totals), checks (name, PASS/FAIL, detail).
- The Notes sheet: the record's notes text, verbatim.

---

## 10. Acceptance

The work is done when, for the fixture engagement in `tests/test_product_statements.py`:

- [ ] each requested statement is its own sheet, with one row per statement line and amounts as
      numbers;
- [ ] `income_statement` rows sum to the record's `net_income`; `balance_sheet` totals equal the
      record's `total_assets` and `total_liabilities + total_equity`;
- [ ] the CF sheet is absent when `cash_flow` is null, and the Working sheet carries the reason;
- [ ] an IS-only request produces exactly one statement sheet;
- [ ] exporting the same record twice yields identical bytes;
- [ ] no product module imports a third-party package (`tests/test_product_boundary.py`);
- [ ] a new test reads the produced workbook back (unzip + parse the sheet XML) and asserts the three
      cash-flow reconciliations against the record's own checks;
- [ ] the workbook contains no figure that is not in the record (a scan of numeric cells against the
      record's value strings).

A test that only asserts a file exists is not an acceptance test.

---

## 11. Out of scope

- Comparatives, multi-period columns, consolidated statements, OCI depth (§8 of the tips doc).
- Plug mode — the tile never invents a balancing figure.
- PDF, Word or HTML renderings of the statements; the workbook is the deliverable.
- Editing the record shape. If the record needs a field, ask the computation lane for it; the renderer
  does not add fields to a frozen record.
