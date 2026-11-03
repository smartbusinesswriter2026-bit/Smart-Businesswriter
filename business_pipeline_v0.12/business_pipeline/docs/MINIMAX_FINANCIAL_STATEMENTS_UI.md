# MiniMax brief — the Financial statements tile: close the UI/UX gap

**Lane:** design (B-080). **Repo:** `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline`
**Read first:** `docs/CONTRIBUTORS.md` §1A/§1B, `docs/BACKEND_CONTRACT.md` §4, `docs/STATEMENTS_TILE_PLAN.md` §1–§3, §8, §10.

## 0. Hard boundaries

1. You own `web/**` and presentation copy. You do **not** edit `src/**`, `tests/**`, the factual
   content of `docs/**`, any route, any record field, or any number.
2. The browser never adds, sums, rounds or infers a figure. Every number on the card is a string the
   server returned inside the frozen record.
3. The backend is finished and verified (transcript in §5). If you believe it needs a change, write a
   `[computation]` line in `WORKLOG.md` — do not make the change.

## 1. Done already (do not redo)

- The tile is **renamed**: `ACCOUNTING_TILES[0]["label"]` is now **"Financial statements"**
  (`src/bp/product/subjects.py`). The `key` stays `"statements"` and `service` stays `"statements"`:
  the renderer, the router and three tests key off them, so they are contract, not copy.
- The backend is built, tested (41 tests) and verified live (§5).
- The tile already has an address and a router branch, and the dialog is built (§4).

## 2. The defect to close: it is a paragraph, not a tile

Today, in `subjectTiles()` (`web/index.html`, the `tile.service === "statements"` branch), the tile
renders as an `<h4>`, a description, and `<p><a class="btn">Open the statements tile</a></p>`.
**That link does not respond to clicks** in the running workbench. The owner asked for it to be
*"a tile similar to other sections"*, and that is the fix:

- Render a **`.capgrid` with one card built exactly like `capabilityCard()`**: `.capcard` >
  `.caphead` (`.capicon` + `<strong>` title) + `.capdesc` + `.capfoot` (left: a short honest label
  such as *"One instruction"*; right: `.capgo` "Open →").
- The card is an **`<a class="capcard" href="#/financial-statements" data-statements-open>`** — the
  whole card is the target, not a small control inside a paragraph.
- Keep `data-statements-open` on the card, and keep `window.openStatementsTile` exposed in the
  `<script id="statements-tile">` block.
- Do **not** let the `setInterval(decorate, 200)` shim (the `#tile-close-shim` block) be what
  creates or replaces the card. It must exist in the rendered HTML, so a click never lands on a node
  that is about to be swapped.

## 3. The name

Use **"Financial statements"** wherever the student reads it: the card title, the dialog title, and
the HOME row you own. The API route stays `/api/cases/statements` — that is backend contract.

## 4. The address, and the click path you must prove

- **Canonical address:** `#/financial-statements`. In `route()` (≈1639) open the tile for
  `head === "financial-statements"` **and** keep the legacy `head === "statements"` as an alias — a
  URL is a bookmark, and anything already pasted must keep working.
- The card's `href` is `#/financial-statements`; the router calls `window.openStatementsTile()`.

**Prove all seven, in a browser, before you commit:**

1. Clicking the card opens the dialog — not merely changes the hash.
2. A fresh tab on `http://127.0.0.1:8021/#/financial-statements` opens it cold.
3. `#/statements` still opens it.
4. Close and Escape close it; the page behind is unchanged.
5. Open it, wait five seconds, click inside — nothing is replaced under the cursor.
6. Tab reaches the card; Enter opens it.
7. No console errors.

## 5. The dialog: restyle freely, change no behaviour

The dialog exists (`<script id="statements-tile">`). It must keep showing, **only** what the record
holds:

| When | What to show |
|---|---|
| **201** | the type line (`problem_type`, `reading_source`, solved); the statements; the **Working / Statements only** toggle — both views from the same record, so the toggle can never change a figure; the withheld-cash-flow note (`statements.cash_flow_withheld_because`); ratios when `ratios` is present (`computed`, then `named_unsupported`); the same-model note; the dissent lines (`rejected`); **Download the statements**, **Download the working**, **Replay this record**; the checks line (`checks` ok count, and `core.scalars.checks_na` as "not applicable") |
| **422** | `refusal`; `diagnosis.difference` ("Out by: 500"); each `diagnosis.findings[]` with its `detail` and `confidence`; `diagnosis.cannot_prove`; and `working.missing` |
| **400** | `error` |

Never print a figure the record does not contain. Never recompute a total in the browser.

## 6. The backend, verified live on 8021 (this is the transcript, not a description)

```
201  balanced trial balance     solved=True type=trial_balance checks=11/11 na=2 NI=8000 assets=10000
                                cash flow: null, and the withheld reason is present
                                statements_only: INCOME STATEMENT + BALANCE SHEET + STATEMENT OF CHANGES IN EQUITY
                                working keys: journal, trial_balance, t_accounts, derivations, assumptions, missing
201  same + "Also compute the liquidity ratios."
                                ratios: computed=8, named_unsupported=7
201  "Cash 5,000 / Bank 1,000 / Capital 6,000"
                                solved=True assets=6000   (two accounts on one statement line)
422  out of balance by 500       refusal: the accounts do not build …
                                difference 500, finding submitted-does-not-balance (likely)
400  two entities pasted together
                                "the account 'Cash' appears twice, and a trial balance lists each account once.
                                 Two sets of balances … solve one set at a time."
400  two figures on one line     "this puts two figures on one line ('Cash 5,000 7,000'), which is a comparative."
400  consolidated               "this mentions 'consolidated' … solve one entity's own books."
400  PHP                        "'PHP' is a currency or a place this product does not use. It works in USD …"
```

Contract, for reference:

| Route | Answers |
|---|---|
`POST /api/cases/statements` | `{instruction, currency?, framework?, ratios?}` → **201** solved, **422** refusal record (with the diagnosis), **400** unreadable |
`GET /api/cases/statements/{id}` | the stored record (`bp-statements/1`) |
`POST /api/cases/statements/{id}/export` | `{format: "statements_only" \| "working"}` → `{view, text, filename}`; **409** if the record is a refusal |
`POST /api/cases/statements/{id}/replay` | `{ok, statements_match, record_hash_match}` |

**Every refusal is a 4xx. Never a 5xx.** (A test asserts this over eight malformed shapes.)

**Runbook:** a `web/**` change needs only a refresh. A `src/**` change needs the workbench
restarted: `python scripts/serve.py --port 8021`. Only the HTML is served fresh — Python modules are
imported at boot, which is why a stale process serves a new page with old data.

## 7. Tests: do not edit, and what I changed for you

`tests/**` is mine. I have already made the tile test **tolerant of the address spelling**, so your
commit is green on its own:

```python
self.assertRegex(page, r'href="#/[a-z-]*statements"', "the tile link must carry the address")
self.assertRegex(page, r'head === "[a-z-]*statements"', "the router must open the tile from that address")
self.assertIn("window.openStatementsTile = open;", page, "the tile must expose the opener the router calls")
```

Still pinned, and still required of you: the first `ACCOUNTING_TILES` entry has key `statements` and
`service` `statements`; every accounting tool lands in exactly one tile; the served page carries
`data-statements-open`, `id="statements-tile"` and `/api/cases/statements`;
`tests/test_subject_accounting_acceptance.py::test_E_acc_002` pins the key and the service value.

## 8. Acceptance for your commit

- The card is visually and behaviourally the same object as the other tiles: same grid, same card
  markup, same hover, focus and keyboard behaviour.
- Clicking anywhere on it opens the dialog; the address becomes `#/financial-statements`.
- `#/financial-statements` opens it cold; `#/statements` still works.
- The name reads "Financial statements" everywhere.
- No number, wording or behaviour of the dialog changes.
- `python -m unittest tests.test_product_statements_tile tests.test_product_subjects` green.
- One CHANGELOG entry and one `WORKLOG.md` entry tagged `[design]`.
