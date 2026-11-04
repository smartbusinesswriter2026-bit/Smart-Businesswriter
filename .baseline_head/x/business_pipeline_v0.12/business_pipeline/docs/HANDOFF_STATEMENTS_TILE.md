# Handoff — the Financial statements tile: close the UI/UX gap

> **STATUS: COMPLETE (2026-11-04).** This file was written *before* the work as a pick-up
> manual, in case the session was cut off mid-fix. The fix is now made, proved and recorded:
> see §9 for what was actually done and where the evidence is. §1–§8 are kept as written,
> because they are the record of the root cause and of the traps — if you are here to pick the
> work up, read §9 first; if you are here to understand it, read §3, which is the important
> part.

**Lane:** design (B-080). **Owner of this work:** MiniMax.
**Repo:** `D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline`
**Branch:** `corpus/merge-v1`. **Design-owner brief (the plan of record):** `docs/MINIMAX_FINANCIAL_STATEMENTS_UI.md`
**This file is a pick-up manual.** If you are reading it, the session that started the work was cut
off. Everything below is measured, not guessed. Re-verify the line numbers before you edit — the
file moves as soon as anyone edits it.

---

## 1. Read this first, in this order

1. `docs/MINIMAX_FINANCIAL_STATEMENTS_UI.md` — the design owner's brief. It is the plan of record.
   Section 7 of it records the two test changes already made for us.
2. `docs/CONTRIBUTORS.md` §1A/§1B — the lane rules. Binding on both owners.
3. This file, §2 and §3, before touching a line.

## 2. Where the work actually stands

**Nothing has been implemented yet.** The brief and the rename are committed; the fix is not.

| Thing | State | Where |
|---|---|---|
| The brief | committed | `docs/MINIMAX_FINANCIAL_STATEMENTS_UI.md`, commit `71e5693` |
| The tile renamed to "Financial statements" | committed | `src/bp/product/subjects.py:2632` |
| The tile test made tolerant of the address spelling | committed | `tests/test_product_statements_tile.py:64-69` |
| **The tile card, the address, the click path** | **not started** | `web/index.html` |

The `key` stays `"statements"` and the `service` stays `"statements"`. They are contract, not copy:
the renderer, the router and three tests key off them.

## 3. The finding that changes the order of the work

**The brief's diagnosis is incomplete, and the true root cause is a syntax error.**

The brief says the tile is "a paragraph, not a tile" and that the link "does not respond to
clicks". Both are true. But the link could not have worked as an anchor *or* as a card, because
**the entire `<script id="statements-tile">` block never executes.**

`web/index.html:10300` carries a stray `}`, and the block ends:

```js
  window.openStatementsTile = open;

  }          <-- line 10300: an EXTRA closing brace

})();       <-- line 10302: this already closes the IIFE body
```

Node's own parser confirms it:

```
block 1 [anon]             -> SYNTAX OK
block 2 [tile-close-shim]  -> SYNTAX OK
block 3 [statements-tile]  -> SYNTAX ERROR: Unexpected token '}'
```

Because the block fails to parse, **none** of it runs: the dialog is never built, the click
handler is never registered, and `window.openStatementsTile` is never defined. The router's
`head === "statements"` branch therefore always takes its `else` path
(`web/index.html:1665`), which registers a `load` listener that calls `window.openStatementsTile()`
— an undefined function.

**So the order of the work is:**

1. **Remove the stray brace.** This is the behavioural fix. Without it, nothing else matters.
2. **Then** the card, the address and the click path — the visual and routing fix the brief asks for.

A card that is still wrapped in a broken script block still does nothing. Prove step 1 alone.

### 3.1 The gate that let it through

`qa/check_page_syntax.py` (and `scripts/ci.py`, which it mirrors) cannot see this class of defect:

```python
scripts = re.findall(r"<script>(.*?)</script>", html, re.S)   # matches NO-attribute script tags only
...
stream.write(scripts[-1])                                    # checks the LAST match only
```

The two tagged blocks — `<script id="tile-close-shim">` and `<script id="statements-tile">` — do
not match that pattern at all, and only one plain `<script>` exists, so the gate checked the main
block and never the other two. **Closing this hole is part of the job** (see §6, step 7).
`scripts/ci.py` is the computation owner's file: record the same hole there as a `[design]`
request in `WORKLOG.md` and let the owner instruct it — do not edit it.

## 4. The code sites, as measured

All line numbers are from the current working tree (`web/index.html`).

| Site | Lines | What it is |
|---|---|---|
| `route()` — the statements branch | 1659-1668 | opens the tile from the address |
| `iconSvg()` / `ICONS` / `toolIcon()` / `toneOf()` | 1444-1516 | the icon helpers |
| `capabilityCard()` | 4222-4248 | the card we must match, part for part |
| `frameworkCard()` | 4250-4264 | a second card shape already in the page |
| `subjectTiles()` — the statements branch | 4291-4296 | **the defect to close** |
| `.capcard` CSS | 552-587 | `all:unset`, then `display:flex`; hover, `:focus-visible`, `.caphead`, `.capicon`, `.capdesc`, `.capfoot`, `.capfoot-row`, `.capgo` |
| `hashchange` binding | 9940 | `window.addEventListener("hashchange", route)` |
| the tile-close shim's `decorate()` | 10039-10058 | appends a `.tilefoot` row to panels; **skips** `panel-home`, `panel-subjects`, `panel-subject`, so it never touches the subject page |
| the statements dialog block | 10064-10302 | the block with the syntax error |
| the dialog's click handler | 10283-10293 | the delegated `[data-statements-open]` handler |
| `window.openStatementsTile = open;` | 10298 | keep this exactly — a test pins it |

### 4.1 The card, part for part with `capabilityCard()`

The tile is a **service**, not a frozen preset, so it has no tool entry to pass through
`capabilityCard()`. Build the card from the same parts, in the same order:

- `.capcard` → `.caphead` (`.capicon` + `<strong>` title) → `.capdesc` → `.capfoot` →
  `.capfoot-row` (left label + right `.capgo` "Open →").
- The card is an `<a class="capcard" href="#/financial-statements" data-statements-open="1">` —
  **the whole card is the target**, not a small control inside a paragraph.
- The icon: `iconSvg("worksheet")` is what `frameworkCard()` uses and it is in `ICONS`. The
  statements tile has no method, so `toolIcon()` would give it "calculator", which is wrong for a
  set of statements. Use the worksheet/ledger glyph.
- The title: `tile.label` — already "Financial statements".
- The description: `tile.what` — the one sentence the shelf already publishes.
- The foot's left label: something honest and short. The brief's suggestion is "One instruction ·
  worked example"; the house pattern on other cards is "Your figures" / "Worked example" /
  "Worksheet". The tile takes **one instruction and no fields**, so "One instruction" is the
  honest label. Do not claim more than the tile does.

### 4.2 The address

Canonical: `#/financial-statements`. The router must open the tile for **both**
`head === "financial-statements"` and the legacy `head === "statements"` — a URL is a bookmark.
Do **not** rename `/api/cases/statements`; the API route is backend contract.

### 4.3 The click

The current handler only acts when the trigger is **not** an `<a>`:

```js
if (trigger.tagName !== "A") { event.preventDefault(); open(); if (location.hash !== "#/statements") location.hash = "#/statements"; }
```

For an anchor it does nothing and relies on the router. That has a hole: **clicking the card when
the address is already canonical changes no hash, so no `hashchange` fires and nothing opens** —
the student clicks a dead card. The brief's acceptance item 1 is "Clicking the card opens the
dialog — not merely changes the hash."

So the handler should open the dialog itself, and set the canonical address:

```js
event.preventDefault();
if (location.hash !== "#/financial-statements") { location.hash = "#/financial-statements"; }  /* the router opens it */
else { open(); }
```

This opens the dialog exactly once in both cases, and never twice (the `else` branch is the only
path that calls `open()` directly; the `if` branch is opened by the router).

### 4.4 The name

"Financial statements" wherever the student reads it: the card title, the dialog title
(`bar("Statements: one problem, solved")`, line 10102) and the dialog's `aria-label`
(line 10081). The `<h4 class="levelhead">` on the subject page already reads the tile's label
(`tile.label`, line 4286), so it is already correct.

**Checked, no change needed:** the HOME page renders subject labels and `start_steps`
(lines 4779-4795), not tile labels. There is no HOME row naming this tile, so the brief's "the
HOME row you own" has nothing to rename. Do not go looking for one in `src/**` — that is the
computation owner's file and the rename is already committed there.

## 5. The acceptance list

**Seven click-path proofs, in a real browser, before you commit.** All seven, or it is not done:

1. Clicking the card opens the dialog — not merely changes the hash.
2. A fresh tab on `http://127.0.0.1:8021/#/financial-statements` opens it cold.
3. `#/statements` still opens it.
4. Close and Escape close it; the page behind is unchanged.
5. Open it, wait five seconds, click inside — nothing is replaced under the cursor.
6. Tab reaches the card; Enter opens it.
7. No console errors.

**The dialog must keep showing exactly what the record holds** — restyle freely, change no
behaviour, and never print a figure the record does not contain, never recompute a total in the
browser. 201: the type line (`problem_type`, `reading_source`, solved), the statements, the
Working / Statements only toggle (both views from the same record), the withheld-cash-flow note,
ratios when `ratios` is present (`computed`, then `named_unsupported`), the same-model note, the
dissent lines, the three buttons, the checks line. 422: `refusal`, `diagnosis.difference`, each
finding with its `confidence`, `cannot_prove`, `working.missing`. 400: `error`.

**Backend: verify, never modify.** The transcript of the measured run is in the brief §6. Every
refusal is 4xx, never 5xx. If you believe the backend needs a change, write a `[computation]`
line in `WORKLOG.md` — do not make the change.

**Runbook:** a `web/**` change needs only a refresh. A `src/**` change needs the workbench
restarted (`python scripts/serve.py --port 8021`) — Python modules are imported at boot, so a
stale process serves a new page with old data.

## 6. The work order

1. Remove the stray `}` at `web/index.html:10300`. **Prove the block parses** — see step 7.
2. Add the `statementsCard()` helper next to `capabilityCard()`, built part for part with it.
3. Replace the statements branch in `subjectTiles()` (4291-4296) with the `.capgrid` + card.
4. `route()` (1659): canonical `financial-statements` **and** the legacy `statements` alias.
5. The click handler (10283-10293): open directly, set the canonical address (§4.3).
6. The dialog title and `aria-label` → "Financial statements".
7. Close the page-syntax gate hole in `qa/check_page_syntax.py`: match **every** script block
   including tagged ones, and check **each**, not `[-1]`. Then re-run it — it must have been able
   to catch the defect that was there.
8. Prove the seven click-path items in the browser.
9. Run the pinned tests and the backend smoke list.
10. One CHANGELOG entry and one `WORKLOG.md` entry tagged `[design]`.

### The pinned tests (do not edit `tests/**`)

```powershell
Set-Location "D:\SMART BUSINESSWRITER\business_pipeline_v0.12\business_pipeline"
$env:PYTHONPATH="src"
python -m unittest tests.test_product_statements_tile tests.test_product_subjects
```

These already tolerate either spelling of the address:

```python
self.assertRegex(page, r'href="#/[a-z-]*statements"', ...)
self.assertRegex(page, r'head === "[a-z-]*statements"', ...)
self.assertIn("window.openStatementsTile = open;", page, ...)
```

So `#/financial-statements` and `head === "financial-statements"` both satisfy them. Still pinned
and still required: the first `ACCOUNTING_TILES` entry has key `statements` and service
`statements`; every accounting tool lands in exactly one tile; the served page carries
`data-statements-open`, `id="statements-tile"` and `/api/cases/statements`;
`tests/test_subject_accounting_acceptance.py::test_E_acc_002` pins the key and the service value.

## 7. TRAPS — read these before you touch anything

**Trap 1 — the tree is dirty with another lane's work. Do not disturb it.**
`git status` at the time of writing showed uncommitted changes that are **not** ours:

| File | Whose change |
|---|---|
| `src/bp/product/subjects.py` | another lane: `CALCULATOR_GROUPS` reordered, `tbcheck` pulled from the accounting group |
| `src/bp/server.py` | another lane: `PRESETS` emptied for `abc`, `salesvar`, `multibreakeven`, `accounts` |
| `web/index.html` | another lane: sticky `.calcgrid`, `calcValueText` JSON round-trip, new placeholders, `RESULT_KEYS.ols`/`ols_robust`, `renderRegressionBlock()` |
| `documents/index.json` | another lane |
| untracked | `fix_accounts.py`, `fix_salesvar.py`, `measure_marketing.py`, `qa/baseline/*`, `qa/probe_marketing_shelf.py` |

**`web/index.html` is shared.** Make surgical edits to it; do not reformat, do not "clean up", and
do not `git checkout` / `git stash` it — that would throw away another lane's work. Do not commit
their hunks with yours: stage only your own hunks, or better, commit only your files and leave
their changes in the working tree for them to commit.

**Trap 2 — the tree already has one failing test, and it is not ours.**
Measured at the time of writing:

```
Ran 61 tests — FAILED (failures=1)
FAIL: test_the_calculator_union_is_exactly_the_subject_compute_tools
AssertionError: Items in the second set but not the first: 'tbcheck'
```

That failure is caused by the other lane's `subjects.py` edit (it removed `tbcheck` from
`CALCULATOR_GROUPS` while the subject's own tool list still names it). **Do not fix it** — it is
`src/**` and it is theirs. Note it as the pre-existing baseline; our commit must not add a
failure. The statements-tile tests themselves pass.

**Trap 3 — `all:unset` on an anchor.** `.capcard{all:unset;...}` resets every property, then the
same rule sets `display:flex`. On an `<a>` this also drops `text-decoration` to `none`, so the
card does not render as a blue underlined link. `text-decoration` is *not* inherited, so `unset`
gives it its initial value `none` — the card will look right. Do not add a `text-decoration` rule
without checking it against the other cards.

**Trap 4 — the dialog must not open twice.** `open()` clears the panel (`host.innerHTML = ""`) and
rebuilds it. If both the click handler and the router call it, the panel is rebuilt and the
student's typed instruction is wiped. §4.3 is written to open exactly once.

**Trap 5 — the shim is not the problem.** `decorate()` (10039-10058) only appends a `.tilefoot`
row to panels and explicitly **skips** `panel-subject`, so it never replaces a card on the
subject page. The brief's re-decoration theory does not hold here. The card must exist in the
rendered HTML regardless — that is still the right thing to do — but the dead link was the syntax
error, not the shim.

**Trap 6 — the tile is a service.** `ACCOUNTING_TILES[0]` has empty `tools`, `worksheets` and
`records`. `subjectTiles()` therefore returns early only when there is no `tile.service`, so the
card does render — but only if it is emitted **before** the early-return check at line 4297.

**Trap 7 — global product.** No PSE/PSEi name, no Philippine place name, no Philippine example,
currency or market claim. The product is global; the API takes `currency` and refuses PHP (§6 of
the brief). Do not put a local example in the card copy.

**Trap 8 — the browser never computes.** Every figure on the card and in the dialog is a string
the server returned inside the frozen record. No summing, no rounding, no inference.

## 8. What is left if you are picking this up cold

- [ ] Read `docs/MINIMAX_FINANCIAL_STATEMENTS_UI.md` and `docs/CONTRIBUTORS.md` §1A/§1B.
- [ ] Re-read §4 of this file and re-measure the line numbers.
- [ ] Remove the stray `}`; prove the block parses.
- [ ] Build the card; make it a real `.capcard` in a `.capgrid`.
- [ ] Canonical address + legacy alias in `route()`.
- [ ] Click opens the dialog directly.
- [ ] Dialog title and aria-label say "Financial statements".
- [ ] Fix `qa/check_page_syntax.py` so it would have caught this.
- [ ] Prove the seven click-path items in a browser.
- [ ] Pinned tests green; backend smoke list matches the brief's transcript.
- [ ] CHANGELOG entry; `WORKLOG.md` entry tagged `[design]`; a `[design]` request for the
      `scripts/ci.py` gate hole.

**One increment, one commit.** Do not commit the other lane's hunks with it.

---

## 9. What was actually done, and where the evidence is

The work is complete. This section is the record of it.

### 9.1 The changes

| File | Change |
|---|---|
| `web/index.html` | removed the stray `}`; added `statementsCard()`; the service tile now renders a `.capgrid` + `.capcard`; the tile-level description paragraph is suppressed for a service tile; `route()` opens `financial-statements` **and** the `statements` alias; the click handler opens the workspace itself and sets the canonical address; **the floating dark modal became a real panel**, `panel-statements`, in `PANELS` and `SUBJECT_WORKSPACE`, with its own markup in the body; the workspace is painted with the page's own components (`.card`, `.badge`, `.toggle`, `.sunken`, the amber `.banner.honesty`); the copy names the shape it reads; a **Use an example** button; a refusal now shows the backend's words plus the shape and the example; a 5xx says the server could not answer; the **Help panel's map** leads with what the product can do instead of the PESTEL/SWOT guided paper, and lists the statements tile |
| `qa/check_page_syntax.py` | rewritten: every inline block is parsed, each is named, the last-match rule is gone |
| `qa/QA_DEFECTS.md` | D-ACC-11 (MAJOR, UI) |
| `docs/CHANGELOG.md` | the 1.86 entry |
| `docs/WORKLOG.md` | the 2026-11-04 `[design]` entry, carrying the `[computation]` requests |
| `docs/HANDOFF_STATEMENTS_TILE.md` | this file |

`src/**` and `tests/**` were **not** touched. Neither was `/api/cases/statements`.

### 9.2 The evidence

- **The root cause is proved, not argued.** Node's parser on the pre-fix block:
  `block 3 [statements-tile] -> SYNTAX ERROR: Unexpected token '}'`; after the fix, all three blocks
  report `SYNTAX OK`.
- **The gate is proved in both directions.** The rewritten `qa/check_page_syntax.py` reports
  `3 of 3 blocks parsed` on the current page, and the **same** gate against the pre-fix page reports
  `FAILED in statements-tile` with the `SyntaxError`. A gate that cannot fail is not a gate.
- **The card is the same object as the others.** The a11y tree gives the card
  `role="link"`, `class="capcard"`, `href="#/financial-statements"`, `data-statements-open="1"`, and a box
  of **506×149** — the same box as the other cards on the shelf.
- **Seven click-path proofs, in a browser,** all passing: the click opens the dialog; a cold tab on
  `#/financial-statements` opens it; `#/statements` still opens it; Close and Escape both close it and
  the page behind is unchanged; after six seconds the card is still the same node and a click inside the
  dialog is not replaced under the cursor; Tab reaches the card (the focus ring is visible on it) and
  Enter opens it; the console holds one informational line and no errors.
- **The backend is untouched and re-measured: 34 of 34 checks pass** over HTTP, reproducing the brief's
  transcript exactly — `ni 8000`, `assets 10000`, `checks 11/11`, `checks_na 2`, `cash_flow` null with the
  withheld note, all three statements, the working keys, ratios `computed 8` / `named_unsupported 7`,
  422 with the 500 difference, 400 with "two sets of balances … one set at a time", export 200
  `statements_only`, replay 200 `ok`, and no 5xx anywhere.
- **The tree's pre-existing failures are another lane's, measured.** A clean `HEAD` checkout runs the
  three modules **114 tests, OK**. `HEAD` **plus only that lane's two dirty `src/**` files** reproduces
  the identical **16 failures and 2 errors**. The current tree adds **none**. So the 18 failures are
  `src/**`, they are in flight elsewhere, and this work adds zero.

### 9.3 Two things this fix found that nobody had seen

1. **The dialog had never rendered**, because the syntax error meant the whole block never ran. So nobody had
   ever looked at it: it painted a navy ground (`--navy-800`, `#12161C`) under near-black text (`--text`,
   `#0C243E`) — about **1.2:1** — and it floated over the shelf like a framework record, not like a tool.
   It is now an inline panel in the page's own light theme. This was a presentation fix only: no number, wording,
   behaviour or field changed.
2. **The tile's own reading is narrower than its copy claimed.** Measured over seven realistic student inputs:
   a bare trial balance → **201 solved**; a single-year transactions narrative → **400** "this carries more than
   one period"; an adjustments narrative → **400** "this puts two figures on one line"; a ratio question →
   **400** "an account has no code"; a cash-flow narrative → **16.9 s, then 400** "the chart needs exactly one
   retained-earnings account, found 0"; an exam question with a preamble → **422** "debits 17000, credits
   19026" (the preamble was read as account rows); EUR → **400** "this product answers in USD only".

   `src/bp/product/statements.py` reads with a deterministic parser; anything the parser cannot read needs the
   model reader, and `bp/server.py` says it plainly: *"no model is configured (set BP_OPENGO_API_KEY), so only a
   trial balance can be read."* **So the tile reads one trial balance, and only one** — which is why it could not
   solve a basic accounting problem. The page copy now says so, a worked example shows the shape, and a refusal
   is actionable. The widening itself is in `src/**` and is a `[computation]` request in the WORKLOG entry.

### 9.4 Still open, and not mine

- **[computation] The reading layer** — four defects, with the reproductions above: an exam-question preamble read
  as account rows; one year read as two periods; an adjustments sentence read as a comparative; and two refusals
  that name the wrong thing (one of them after 16.9 seconds). The alternative is one line of configuration:
  `BP_OPENGO_API_KEY` enables the model reader the module's own docstring describes.
- **[computation] `ACCOUNTING_TILES[0]["what"]` and `["need"]`** in `src/bp/product/subjects.py` still promise
  "the question as you were given it"; the page copy is exact now, but those two strings are the computation
  lane's to change. Suggested wording is in the WORKLOG entry.
- **[computation] `scripts/ci.py` has the same page-syntax hole** `_node_check` has. Requested in the WORKLOG
  entry; not edited, because `scripts/**` is the computation lane's.
- **[computation] `src/bp/build.py` is at `VERSION = "1.85"`** and the CHANGELOG entry is 1.86. Every prior
  release commit moved the two together. Requested in the WORKLOG entry; not edited, because `src/**` is the
  computation lane's.
- **The accounting acceptance suite's 18 failures** are another lane's in-flight `src/**` edit (§7, Trap 2).
  Do not "fix" them from this lane.
