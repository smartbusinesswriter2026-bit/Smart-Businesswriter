# Worklog — append-only record of what was done

## 2026-10-27 — [computation] Asset disposal: the one schedule that must read the books

**Ask.** Phase 1, fifth increment: an asset could be depreciated but never derecognised, so a disposal
had to be hand-written as a multi-line entry - exactly where the gain or loss gets invented.

**Did.** New schedule kind `disposal`. It produces one compound entry: Dr proceeds, Dr accumulated
depreciation, Cr the asset at cost, and the difference to a gain (credit) or a loss (debit), with net
book value = cost - accumulated and gain = proceeds - net book value. Zero-amount lines are omitted
because the ledger refuses them, and a line for nothing is noise. A scrapped asset (zero proceeds)
therefore posts only the accumulated-depreciation and loss lines.

**It is the only schedule given the journal.** `accounts.build` passes `journal=j` to this one kind, and
the declared `cost` and `accumulated` are **cross-checked against the ledger**; a mismatch is refused
("the ledger holds 3000 on 1200, but the disposal declares a cost of 3500"). A disposal that cleared
more or less than the books actually hold would leave a residue on the asset or on its accumulated
depreciation and quietly break A = L + E. The check is a refusal, never a correction: the owner must
say which figure is wrong.

**Two bugs I wrote and caught.** The first version emitted a zero-amount proceeds line for a scrap, which
the ledger refuses; and the schedule raised `ScheduleError` straight out of `build`, so callers saw an
inconsistent exception type - it is now wrapped as `EngagementError`, matching the rest of the account
layer.

**Revaluation is deliberately NOT included.** It needs a declared policy - whether accumulated
depreciation is restated proportionally or eliminated against the gross carrying amount, and where the
surplus goes (revaluation surplus in equity, or through profit or loss). Two standard treatments exist
and the choice changes the statements, so it is an owner decision rather than something to invent. It is
queued, not forgotten.

**Verified.** 819 tests OK, including 13 new ones: the gain entry (proceeds 2,500 on NBV 2,200 gives a
300 credit), the loss entry, the break-even case with no gain or loss line, a scrapped asset taking the
full net book value as a loss, the statement still balancing after a disposal, both ledger cross-checks
refused, four input refusals, and a trap showing that clearing the wrong accumulated figure leaves a
residue of exactly 300 while the schedule path refuses that same input.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** the remaining adjusting-entry types (prepayment and its release, deferred income,
bad-debt allowance), then the statements block.

## 2026-10-27 — [computation] Depreciation beyond straight-line: reducing balance and units of production

**Ask.** Phase 1, fourth increment: `schedules.py` could only do straight-line, so any case with an
asset depreciated against its carrying amount, or against how much it actually produced, could not be
represented at all.

**Did.** `depreciation(spec)` now dispatches on a declared `method`: `straight_line` (the default, so
every existing spec is unchanged), `reducing_balance` and `units_of_production`. All three keep the
two guarantees the straight-line implementation already made - the charge never takes the carrying
amount below the declared residual, and the schedule sums exactly to cost minus residual with the
final charge absorbing the rounding remainder - and all three emit the same Dr expense / Cr
accumulated-depreciation shape, so nothing downstream changes.

- **Reducing balance** charges a declared per-period `rate` against the carrying amount. The rate is
  declared, never derived: the choice of rate is the owner's estimate, not a fact the engine can find.
- **Units of production** spreads the depreciable amount over a declared `total_units` and charges each
  period's own usage. The rounding remainder is absorbed by the **last period that actually produced**,
  not by a trailing idle period - dumping it into a month with no production would misstate both.

**Refused:** an unknown method; a rate outside `(0, 1)`; a charge that rounds to zero while the asset is
still above its residual; units summing to more than `total_units`; negative units; all-zero units; and
`changes` on a non-straight-line method, because a revised useful life has no defined meaning there.
Refusing is deliberate - silently ignoring `changes` would post a schedule the owner did not ask for.

**A now-false claim, corrected.** `KNOWN_LIMITATIONS.md` stated that schedules cover "straight-line
depreciation ... only; no declining-balance or units-of-production depreciation". That sentence became
false the moment this landed, so it was rewritten in the same commit - the same discipline the
catalogue correction applied earlier today.

**Verified.** 806 tests OK, including 19 new ones: all three methods sum to cost minus residual and
never dip below the residual; reducing balance charges 4000/2400/1440/1160 on a 10,000 asset at 40%;
units of production charges per usage and puts the remainder in the last producing period; every
refusal above is exercised; a trap test shows the new methods genuinely differ from straight-line; and
two integration tests post a reducing-balance and a units schedule through a **full engagement**,
confirming the balance sheet still balances, the expense closes to nil and net income carries the charge.

**No unfreeze.** `management_accounts` keeps its eleven `test_names`; the frozen fixture is untouched.

**Still not done, and now clearly queued:** asset disposal and revaluation (a disposal closes the
accumulated depreciation against the asset and recognises the gain or loss), then the remaining
adjusting-entry types.

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

## 2026-10-27 — [computation] Reversing entries: a correction you can see, not a balance you adjust

**Ask.** Phase 1, third increment: bookkeeping corrections were only possible by hand-writing the
mirror of an earlier entry, which is exactly where a sign error hides.

**Did.** An entry may now carry `ref` (a unique name) and another entry may declare `reverses: <ref>`
instead of `lines`. `accounts.resolve_reversals` expands the reversal into the **exact mirror** of its
target - same accounts, debits and credits swapped - on the declared date, with
`reversal of <ref>` as the default description. The kernel therefore receives two ordinary balanced
entries, and both are visible in the journal and in every T-account they touch.

**Refused before anything is posted** (`_reversal_errs`): an entry that declares both `lines` and
`reverses` (which one did the ledger receive?), a duplicate `ref`, an unknown target, a **forward**
reference, and a self-reference. Forward references are refused deliberately: resolving only backwards
means the expansion always completes in one pass and can never depend on itself.

**A correction, in the accounting sense,** is a reversal plus a new entry. Both primitives now exist;
no separate `corrects` keyword was invented for it.

**Verified.** 787 tests OK, including 11 new ones: the mirror keeps the same accounts and swaps every
debit for a credit; it moves the closing cash balance by exactly the negated amount; it uses the
declared date and generates the description; it is visible in the affected T-account; all five invalid
links are refused by `validate_spec` and a refused link never reaches the ledger; and a trap test
confirms the reversal actually changes the balances, so the mirror test is not testing nothing.

**No unfreeze.** Spec-level input, not a method contract change: `management_accounts` keeps its
eleven `test_names` and the frozen fixture is untouched.

**No build number** - no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** depreciation beyond straight-line (reducing balance, units of production) and
asset disposal, then the remaining adjusting-entry types.

## 2026-10-27 — [computation] The journal itself: the audit trail behind every balance

**Ask.** Phase 1, second increment, in the order agreed: the ledger engine should let a reader see
the entries, not just the totals derived from them. T-accounts showed one account's movements;
nothing showed the double entry that produced them.

**Did.**

- `ledger.journal_view(j)` — every entry in posting order as data: date, description, opening and
  closing flags, each line named and sided with its debit or credit, the entry's own debit and credit
  totals, and the entry hash from the chain `verify_chain` checks.
- `report.journal(j)` — the same journal as deterministic plain text, marking opening and closing
  entries and printing each entry's totals so a line that did not balance could never read as though
  it had.
- `accounts.build` now exposes `journal` (serialised) and `journal_export` (rendered) in the appendix.
  The existing `export` field is untouched.

**Why the totals are in the view.** The kernel already refuses to post an unbalanced entry, so the
totals are redundant for the engine. They are not redundant for a *reader*: an audit trail that shows
lines without proving the entry balances asks to be trusted rather than checked.

**Verified.** 776 tests OK, including 7 new ones: the view matches the journal entry for entry
(dates, descriptions, hashes) and the chain verifies; every entry balances in the view; rebuilding
every account's debits and credits **from the view** agrees exactly with `j.balances()`, which is what
the statements are built from; every line names a chart account; opening and closing entries are
marked, never both; and a trap test that drops one entry and shows the recomputation stops agreeing.

**No unfreeze.** The method contract is untouched: `management_accounts` keeps its eleven `test_names`
and the frozen fixture is unchanged. This is additive appendix data.

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

**Next in order:** reversing and correcting entries (a declared reversal in the spec, with validation),
then depreciation beyond straight-line, then the remaining adjusting-entry types.

## 2026-10-27 — [computation] T-accounts: the ledger can now be read one account at a time

**Ask.** Phase 1 of the accounting build, first increment: the owner named "no T-tree balancing" as a
missing capability, and nothing in the engine could show a single account's movement — only a trial
balance total and derived statements. Layout first, wiring later; this is the computation side.

**B-032 closed (owner instruction, this session).** The ledger engine is the **custom kernel for
management accounts v1**, as the provisional recommendation already on record. The Beancount arm was
never run and is recorded as not run; the decision note records that it can be revisited if an external
engine is ever wanted. Phase 1 sits directly on this decision, which is why it was closed first.

**Did.**

- `ledger.account_ledger(j, code)` — one account as a T-account: opening balance (from the opening
  entry), every period posting in **date order** with the **running balance on the account's normal
  side**, the movement totals, and the closing balance. Closing entries are included and marked, so an
  income account that reads zero explains why instead of hiding the close.
- `ledger.account_ledgers(j)` — every chart account, in chart order, including accounts with no
  postings (an empty account is information).
- `report.t_account(lg)` / `report.t_accounts(...)` — deterministic plain-text rendering, same
  conventions as the other statement exports (fixed width, parentheses for negatives). It renders the
  numbers it is given and recomputes nothing.
- `accounts.build` now emits `ledgers` (serialised) and `t_accounts_export` (rendered text per account)
  in the appendix, so the workbench can show a T-account without ever computing a balance itself.

**Two design decisions worth recording.**

1. The running balance is computed **in the core, not the page**, because it is a reading of the account
   rather than a presentation choice. A design-layer balance would be a derived business number, which
   §1A forbids.
2. The **frozen contract was deliberately not touched.** `management_accounts` is T2 with eleven
   `test_names` pinned in `tests/fixtures/frozen_contract.json`; adding a twelfth invariant to
   `check_invariants` would have forced a fixture change for no gain. The footing property is instead
   proven by `tests/test_t_account_ledger.py`, which rebuilds the journal and compares every account's
   debit and credit totals against `j.balances()`.

**A bug I wrote and caught.** The first version read `l.opening` (a line attribute that does not exist)
instead of `e.opening`, and started the running balance at zero rather than at the opening balance. Both
were caught by the new tests before any commit.

**Verified.** 769 tests OK, including 8 new ones:
every account foots to the trial balance; opening + movement = closing; the running balance recomputes
from its own rows; postings read chronologically; the close is visible and zeroes an income account; a
contra asset stays credit-normal and still reduces its section; an unposted account is present and
empty; and a trap test showing a ledger that omits the opening balance would **not** foot — so the
footing assertion can actually fail.

**Still not fixed, carried forward:** `multi_product_breakeven` does not flag a negative-contribution
product (needs an unfreeze because it changes `test_names`).

**No build number** — no served markup changed and the pill is pinned at `v0.73` by a test.
**Not pushed** to GitHub.

## 2026-10-27 — [computation] The server told browsers to cache a page it recomputes every time

**Found while verifying the catalogue fix.** After correcting the catalogue and restarting
the server, the browser still rendered the old statuses. The API was already right on the wire;
the browser had reused its cached copy. `src/bp/server.py` sent no caching header at all —
no `Cache-Control`, no `Pragma` — although CHANGELOG 0.69 states *"The page now declares
`Cache-Control: no-store` / `Pragma: no-cache`"*. That sentence was never true in the code.

**Why it matters beyond one stale row.** The build pill is the only "which page am I looking at"
signal, and it is useless until the page has actually reloaded. A cached page with an old pill
and old data is indistinguishable from a current one. This is the same failure mode as the
wrong-folder-on-8021 confusion: the owner sees something that is not what the code says.

**Did.** `_send` — the single exit point for every response — now adds `Cache-Control: no-store`
and `Pragma: no-cache` alongside the existing `X-Content-Type-Options`. Added
`tests/test_cache_headers.py` (2 tests) which starts the real `ThreadingHTTPServer` and asserts
both headers on the workbench document and on `/api/health`. The test fails on the old code:
the headers were observably absent from the live server before this change.

**Verified.** 761 tests OK. Live server confirmed sending `no-store` on both routes.

**Still no build number, for the same reason as the entry below:** no served markup changed and
the pill is pinned at `v0.73` by `tests/test_product_subjects.py`.

## 2026-10-27 — [computation] The catalogue told students that built accounting methods did not exist

**Ask.** Phase 0 of the accounting build: "correct those that are erroneous" before adding
anything. The owner had seen the Accounting page say *"Management accounting — not implemented"*
while `management_accounts` was running on that same page.

**Found.** The subject pages derive every record's `implementation_status` from
`METHOD_LINK_RULES` in `src/bp/registry.py` — a six-rule table that matches a record's *summary*
and returns its linked methods plus a hand-written note. Only six rules existed, all written
before IRR, discounted payback, ratio analysis, the valuation family, the ledger engagement, unit
economics and most of the statistics library shipped. Everything unmatched falls through to
`"not implemented"`. Consequences verified against the live API:

- `QNT-FIN-01` claimed IRR and payback were missing — both are T1 methods
- `QNT-FIN-02` claimed "break-even only" — `multi_product_breakeven` also exists
- `QNT-FIN-03`, `QNT-FIN-04`, `QNT-FIN-05`, `QNT-FIN-06` each read **"not implemented"** while
  `ratio_analysis`, `wacc`/`dcf_valuation`/`equity_bridge`, `management_accounts` and
  `unit_economics` respectively run
- `QNT-STA-03` claimed chi-square and ANOVA were missing; `QNT-STA-04` claimed logistic
  regression was missing — all present

Two of 36 methods were claimed by the catalogue; the other 34 were reachable only through the
Calculator.

**Did.** Rewrote `METHOD_LINK_RULES` so each rule matches on its record's summary prefix and
carries an accurate note and the real method list, then regenerated the committed slice with
`scripts/generate_subjects.py` — the documented single source of truth. `QNT-FIN-07` (pricing and
demand) stays `not implemented` because it genuinely is. `currency_convert` was deliberately **not**
claimed against `QNT-FIN-04`, whose summary does not mention currency: fixing an underclaim must
not create an overclaim.

Added `tests/test_catalogue_truth.py` (6 tests): every linked method id resolves; no record both
links methods and says "not implemented"; the accounting, finance and regression records claim the
methods the engine registers; every compute tool resolves to a real preset. Updated the test count
in `HOME.md`, `HANDOFF.md` and `CONTRIBUTORS.md` from 753 to 759.

**Verified.** 759 tests OK. Corrected rows confirmed from the live API
(`/api/cases/subjects/accounting`), not from the module.

**Not fixed, recorded as findings:**

1. `multi_product_breakeven` accepts a product with negative contribution and reports a
   break-even without flagging that one product loses money on every unit. The arithmetic is
   right under the declared mix; the absence of a warning is the gap. Adding a check would change
   `test_names` and needs an unfreeze.
2. `server.py` sends **no** `Cache-Control`/`Pragma` header, although CHANGELOG 0.69 claims it
   does. A browser served a stale catalogue during this very session until the server restarted.
   Next increment.

**No build number.** This changes API data, not page markup, and `tests/test_product_subjects.py`
pins the served pill at `v0.73`. Bumping the changelog without changing the pill would make the
documents disagree with the page the owner checks.

**Lane note.** The correction touches `src/bp/product/subjects.py`, which is the design owner's
file, because the wrong text was a *factual claim about the engine* — computation-owned content
(§1A). It was regenerated from the core rule rather than hand-edited, and the guard test lives in
`tests/`. If the design owner disagrees with that call, the revert is local and this entry records
why it was made.

## 2026-10-27 — [product] Clean Home: logo + unchanged slogan + chat box only (build 0.70)

**Ask:** the owner rejected the 0.69 Home as regressed and over-filled: it should be clean and contain only the chat box and its logo; the side rail is already fine; do not change the slogan; do not act without permission. Confirmed scope: remove the dropdowns too; the chat box is only the text area and up arrow.

**Did:** removed from Home the extra sentence under the slogan, the preset/method/currency selects, the preset chips, the Examples card, "Your cases", "Or choose a subject", the "Two ways in" note and the Enter hint. Kept the logo, wordmark, the tagline exactly as written, the text area and the up-arrow. Side rail, Calculator, Status pill, top bar, subject pages and backend untouched. Guarded the absence of the removed elements; guarded `startFromHome` against the removed selects (it now toasts to the rail/Calculator because Home has no method control).

**Files:** `web/index.html`, `tests/test_product_subjects.py`, docs: `CHANGELOG.md` (0.70), `DECISIONS.md` (B-094), `DISCUSSION_NOTEBOOK.md` (entry + Status line), `HOME.md`, `HANDOFF.md`, this entry.

**Verified:** 753 tests OK; `node --check`; `<section>` counts equal; no Home markup for `preset`/`method`/`currency`/`data-example`/`hero-sub`/case or subject shelves. No computation, API, side rail or business number changed.

**Open/next:** the Home arrow cannot launch without a method; method choice lives in the subject rail and Calculator. `loadHomeShelf` is now unused. If the slogan meant the sentence under the tagline, it must be restored verbatim on request.

## 2026-10-27 — [product] Static-first expandable subject rail, centred chat, up-arrow Enter control (build 0.68)

**Ask:** another agent's served copy lost the subject rail; re-implement it, ensure the rail is expandable, centre the big Home chatbox with even side space without changing its length, and move Run to the right as an up arrow suggesting Enter.

**Did:** wrote the ten subject links and icons as static markup in `#railsubjects` so the rail renders before `/api/cases/subjects` and survives its absence; the live call still replaces them with full labels/counts, and a failure now appends a note instead of wiping the list. Reworked the rail toggle (hamburger collapsed, chevron + "Collapse" open, `aria-expanded`, label, title, persisted state). Added `main{margin:0 auto}` so the action box centres in the content column at unchanged width. Moved `#run` from the left of the action row to the right and replaced it with a circular up-arrow button; added Enter-to-start / Shift+Enter-newline and an inline hint. Added three static-markup presence guards in `tests/test_product_subjects.py`.

**Files:** `web/index.html`, `tests/test_product_subjects.py`, docs: `CHANGELOG.md` (0.68), `DECISIONS.md` (B-093), `DISCUSSION_NOTEBOOK.md` (new dated entry + Status line), `UI_BRIEF.md` note, `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, this entry.

**Verified:** 753 tests OK; `node --check` on the extracted page script; `<section>` counts equal; the static rail has all ten subject ids; the panels removed in 0.67 are still absent. No computation, frozen module, fixture, API route or business number changed.

**Open/next:** static labels are shorter than the live ones and only the ten known ids are guarded. The static rail is navigation, not capability: with an old backend the subject page still 404s. The chat centring is within the content column (the rail offsets the visual centre by ~32px). No browser test exists.

## 2026-10-27 — [product] Catalogue and Assistant panels deleted from the UI (build 0.67)

**Ask:** "whats the use of catalogue, assistant and status? are they needed? or okay to be deleted?" followed by **"go"** for the recommendation: delete Catalogue and Assistant from the UI, keep Status behind the health pill, keep all backend routes and tests.

**Did:** removed `panel-frames` and `panel-assistant` markup, `RENDERERS.frames`, `searchFrameworks`, `loadTemplate`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, the subject-page "Browse the full method catalogue" button, the drawer's Assistant tab, the `/api/assist/config` boot call, the `state.assist` field and the unused `.dtab` CSS. The chat button now opens a single Help & about drawer; the health pill still opens Status. Kept `/api/frameworks`, `/api/frameworks/{id}`, `/api/templates`, `/api/assist` and their tests; subject catalogue-only tables, worksheet tiles and the Calculator are unchanged.

**Files:** `web/index.html`, docs: `CHANGELOG.md` (0.67), `DECISIONS.md` (B-092), `BACKEND_CONTRACT.md` §6, `DISCUSSION_NOTEBOOK.md` (new dated entry + Status line), `UI_BRIEF.md` note, `HOME.md`, `HANDOFF.md`, this entry.

**Verified:** 750 tests OK; `node --check` on the extracted page script; zero remaining references to `panel-frames`, `panel-assistant`, `RENDERERS.frames`, `RENDERERS.assistant`, `challengeAnalysis`, `fillAssistantDrawer`, `dtab`, `state.assist` or `api/assist`; `<section>` open/close counts equal. Three UI-presence assertions in `test_assist`, `test_framework_flow` and `test_templates` were retargeted to the new surface (no backend test or assertion changed). No frozen module, fixture, route or business number changed.

**Open/next:** the backend assistant and framework/template routes are now reachable only by direct API/test call. If a provider is configured later, the assistant UI must be re-surfaced **and fixed** (use `critique`, supply facts/alternatives, send `consent`). Status remains a dev-facing panel behind the pill.

## 2026-10-27 — [product] Subject rail, capability tiles and Home reconciliation (build 0.66)

**Ask:** the owner's rail instruction — enumerate the subjects (Accounting, Finance, Economics, Management, ..., now Entrepreneurship) with icons; clicking one shows its capabilities in the centre as clickable tiles; reconcile with Home chat; delete Case, Catalogue, Assistant and Status from the rail and keep Calculator at the bottom.

**Did:** (1) `bp.product.subjects`: added Entrepreneurship as a combination shelf (8 frozen compute tools, the existing STR-18 SWOT worksheet, 5 catalogue-only canvas/innovation records) and a unique presentation `icon` key on all 10 subjects, exposed by the gallery and detail routes; added an Entrepreneurship group to the Calculator groups. (2) `web/index.html`: rail rebuilt as Home + the 10 subjects (icon, label, native tooltip, aria-current on the active subject) + Calculator pinned at the foot; the Case/Catalogue/Assistant/Status rail items removed, with their existing panels kept reachable from Home/subject pages, the subject catalogue button, the chat drawer and the health pill. (3) A subject click renders a capability **tile grid** (one tile per frozen method or worksheet, with description, preset/typed-input footer and kind icon) instead of a vertical row list; stored cases and the catalogue-only table follow. (4) Home-chat reconciliation: copy states the two routes, the same subject cards remain under the box, and every subject page links to the chat. (5) Hash routing now supports `#/subject/<id>`. (6) Two guard tests: rail order/unique icons/icon round-trip, and Entrepreneurship's tool/worksheet/canvas composition.

**Files:** `src/bp/product/subjects.py`, `web/index.html`, `tests/test_product_subjects.py`, `tests/test_product_server.py`, docs: `CHANGELOG.md` (0.66), `DECISIONS.md` (B-091), `BACKEND_CONTRACT.md` §6, `DISCUSSION_NOTEBOOK.md` (dated entry + Status line), `HOME.md`, `HANDOFF.md`, `CONTRIBUTORS.md`, this entry.

**Verified:** full suite **750 tests OK**; `node --check` on the extracted page script; a live server smoke test returned the 10-subject gallery with icons, the Entrepreneurship page (8 tools, 1 worksheet, 5 catalogue records), the 8 Calculator groups and HTTP 200 for the page. No frozen module, frozen fixture, existing route contract or business number changed.

**Open/next:** the same open items as build 0.65 (C1 multi-run cases, per-subject workbenches, free-form arithmetic, owner decisions in notebook section J). A browser-level UI test is still absent; the rail/tile checks are catalogue guards plus a JS syntax check.

## 2026-10-26 — [product] Subject-first navigation and the Calculator launcher (build 0.65)

**Ask:** "read discussion notebook and implement it" — the notebook's build brief (section G, Increment 1) plus the owner's rail Calculator instruction (section N).

**Did:** implemented the first increment, not the whole four-increment plan. **Product catalogue:** new `src/bp/product/subjects.py` is a committed, testable index of 9 subjects (Accounting, Finance, Economics, Management & strategy, Operations, Supply chain & logistics, Marketing & customers, People & organisation, Research & statistics as a cross-cutting shelf). Each subject maps to the frozen preset ids / method ids it can actually launch, the three existing T4 worksheets (STR-01 Five Forces, STR-07 and STR-18 SWOT) as structure-only, and the registry records it can only read or structure with the registry's own `implementation_status` wording. A generation helper (`scripts/generate_subjects.py`) writes the registry slice; `tests/test_product_subjects.py` re-reads the frozen fixture and registry as data and fails on any drift. **Routes (additive, `/api/cases` only):** `GET /api/cases/subjects`, `GET /api/cases/subjects/{id}`, `GET /api/cases/calculator`, and `GET /api/cases?subject=<id>` (stored cases filtered by the methods the subject can launch). **Calculator:** seven business-function groups (Finance, Accounting, Statistics, Economics, Operations, Marketing, People) built from the same compute tools; it arranges inputs and calls the existing create-then-confirm pipeline. No client-side formula, no product-layer arithmetic, no new arithmetic path; free-form expressions are named as unsupported rather than silently absent. **Served UI (`web/index.html`):** seven-item rail Home | Subjects | Calculator | Case | Catalogue | Assistant | Status; Home is a case shelf (stored cases + subject cards + the existing objective box); subject pages show tools, worksheets, stored cases and an explicit catalogue-only table; a searchable Calculator; the "Draft work plan" destination is replaced by a one-button tool screen ("Apply figures and calculate" performs the same two calls), while the phrase survives honestly in the recorded-metadata panel the frozen test asserts; `framework_suggestions` is finally rendered (informational only); the hero sub-line is no longer "To be supplied"; a malformed `</section` in the served HTML was fixed. **Not implemented, deliberately:** C1 `bp-case/2` multi-run cases, the Accounting/Finance workbenches, and the remaining subject workbenches (Increments 2–4); the Home copy says a run is still saved as a one-run case.

**Files:** `src/bp/product/subjects.py` (new), `scripts/generate_subjects.py` (new), `src/bp/product/api.py` (imports, subject/calculator routes, subject filter), `tests/test_product_subjects.py` (new, 14 tests), `tests/test_product_server.py` (one HTTP route test), `web/index.html`, `docs/DISCUSSION_NOTEBOOK.md` (new dated entry + brief Status line), `docs/CHANGELOG.md` (0.65), `docs/DECISIONS.md` (B-090), `docs/BACKEND_CONTRACT.md` §6 + test count, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, this entry.

**Verified:** full suite **748 tests OK**; `node --check` on the extracted page script; the subject drift guard confirms every launch id exists in the frozen fixture and every catalogue id in the registry; the product boundary test still shows no core import and no product-layer arithmetic. No frozen module, frozen fixture or existing test was edited.

**Commit:** `this commit`.

**Open/next:** the owner decisions in notebook section J remain open, especially (2) whether one case should hold many subject analyses (the C1 decision) and (4)/(5) whether the 131 catalogue-only records should stay visible and whether B-028 should add worksheets. Increment 2 (C1), the Accounting workbench and the Finance/DCF sheet are the next build steps, not part of this increment.

---


## 2026-10-21 — [documentation] Website UI brief for the design owner (plan mode)

**Ask:** write the instruction for MiniMax/OpenCode to build the website: A1.jpg as inspiration, the owner's logo as the site logo, colored feature icons on the left rail, remove the API/Enterprise top-right items, delete the "Trusted by 11 million" block and the university row, retain the circular chat button restyled to the brand, UI sans-serif except generated document text (Times New Roman), and **plan mode first** so MiniMax can ask clarifying questions before building.
**Did:** wrote `docs/UI_BRIEF.md` as the authoritative instruction: assets and where they live (logo copied into `web/assets/`, A1 as inspiration only, never shipped); the A1 structure to imitate (fixed left icon rail, centered hero with logo, large action box with an inner controls row, quick-action chips, floating chat button) and the exact removals (top-right API/Enterprise/Pricing/Login/Sign-up; the trusted-by block and university logos; no invented social proof); the nine real features for the rail mapped to the actual API routes (Home/New analysis, Cases, Data, References, Deliverables, Accounts, Frameworks & templates, Assistant & method info, Status); typography (sans-serif system stack for UI; Times New Roman for generated document text, with the note that `export.py` is a computation-owner file and must not be edited); the non-negotiables (display API values verbatim, no client-side computation, never hide caveats/honesty/limitations/tier labels, no invented content, offline/no CDNs, `web/**` write scope, backend needs requested rather than invented) and the frozen workbench strings the suite asserts. The brief's first deliverable is a **plan** (IA, screen map, wireframes, design tokens sampled from the logo, component inventory, responsive/accessibility, phased build, test-impact statement, and questions for the owner) with no code until approved.
**Files:** `docs/UI_BRIEF.md` (new), `docs/HOME.md` (spine row + build digit), `docs/HANDOFF.md` (build digit), `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **733 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** MiniMax replies in plan mode with its plan/questions; the owner reviews; after approval the UI is built in `web/**` on its own branch. Nothing UI has been started by the computation lane.

---

## 2026-10-21 — [computation] Product slice 2c: charts, spreadsheets and business graphics (B-089)

**Ask:** "do 1" — the last backend item: the graphics/spreadsheets addition (B-087), then stop before the UI.
**Did:** three new product modules, all deterministic and stdlib-only, with **no model in the rendering path**. **`charts.py`**: a declarative `bp-chart/1` spec renders SVG for bar, line, stacked bar, waterfall, pie, sparkline and table; every series names a stored artifact (metric or id), a missing artifact / no recorded value / non-numeric value is refused with a reason, the spec's text fields (title, labels, axis labels, note) **may not contain digits** so only stored value strings can appear, and geometry scaling never alters the strings; same bundle + spec → byte-identical SVG. **`spreadsheets.py`**: CSV of the artifact table (LF endings) and a SpreadsheetML 2003 workbook with Case/Artifacts/Report sheets where every cell is a string (so `50.00` never becomes `50.0`). **`diagrams.py`**: structure-only (T4) SVG templates — process, 2x2 matrix, pyramid, funnel, tree — from owner-supplied digit-free labels; nothing is scored or ranked. `export_html` now embeds charts/diagrams; routes `POST /api/cases/{id}/render` (SVG preview) and `POST /api/cases/{id}/export` (`csv` / `spreadsheetml` / `html`).
**Files:** `src/bp/product/charts.py`, `.spreadsheets.py`, `.diagrams.py` (new), `src/bp/product/export.py`, `src/bp/product/api.py`, `tests/test_product_charts.py`, `tests/test_product_diagrams.py`, `tests/test_product_spreadsheets.py` (new), `tests/test_product_routes.py` (extended), docs (B-089, CHANGELOG 0.63, BACKEND_CONTRACT §6, PRODUCT_BACKEND_PLAN 2c, README, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **733 tests OK** including the frozen-contract and docs-state guards; SVG validated as well-formed XML, determinism and number-fidelity tested (a chart cannot print a number that is not a stored value), spreadsheets checked cell-by-cell as strings, and the render/export routes exercised through the dispatch.
**Commit:** `this commit`.
**Status:** the backend product sequence is **complete** (2a, 2b, 2c). Per the owner's instruction I am **stopping before any UI/homepage/interface work** and waiting for the special UI instructions. Remaining non-backend items are decision-gated (D3 disclosure, REW R1–R10/B-082, tax B-052, ledger B-032, templates B-028, reviewers B-005, frontier stats B-075).

---

## 2026-10-21 — [computation] Product slice 2b: ops surface and the local launcher (B-088)

**Ask:** continue the backend sequence, and the owner asked "will you also build the server? i notice there is no server yet". Answer: the server already exists (`src/bp/server.py`, stdlib HTTP, `python -m bp.server`, serving the workbench and API, wired to the product routes since B-085); what was missing was the operational/deployment surface, which is this slice.
**Did:** new `src/bp/product/ops.py` — `health()` (case-store counts, state dir, request-log status, checks, ok/degraded), `log_request()` (JSONL: timestamp, method, query-free path, status, duration only; never a body/title/input/report; `BP_REQUEST_LOG=""` disables; best-effort), `backup()` (zip of the case store's JSON documents + manifest + SHA-256; state/logs/prior archives excluded), `restore()` (zip-slip/drive/non-JSON refusal, staging then copy, refuses overwrite unless asked), `list_backups()`. Additive core instrumentation in `server.py`: a timing hook feeding the request log, `GET /api/health` (merging sandbox/model flags), and startup lines for URL/health/log — no existing route, output or claim changed (frozen guard still passes). New `scripts/serve.py` launcher as the single local run path: `--port`, `--host`, `--no-sandbox`, and `--check` dry-run printing the resolved config; it adds `src` to `sys.path` so a clean checkout needs no install. Product routes `POST /api/cases/backup`, `POST /api/cases/restore`, `GET /api/cases/backups`.
**Files:** `src/bp/product/ops.py` (new), `src/bp/product/api.py`, `src/bp/server.py` (additive instrumentation), `scripts/serve.py` (new), `tests/test_product_ops.py`, `tests/test_launcher.py`, `tests/test_product_server.py` (extended), docs (B-088, CHANGELOG 0.62, BACKEND_CONTRACT §6, PRODUCT_BACKEND_PLAN 2b, README, HOME, HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **714 tests OK** (frozen-contract and docs-state guards included); health/backup/restore and the launcher were exercised over a real HTTP server; the request-log test asserts no report text, input body or title reaches the log.
**Commit:** `this commit`.
**Open/next:** Phase 2c (deterministic charts/SpreadsheetML/diagram templates, B-087) is the last backend task before the UI; after it I stop, per the owner's instruction to hold the interface until special instructions.

---

## 2026-10-21 — [computation] Product slice 2a: case versions, comparison and sign-off (B-086)

**Ask:** "continue on the sequence of backend product building. do it yourself the job you are delegating because you will not accept cline's work and still edit it." Plus the important addition about spreadsheets/charts (recorded as B-087 and planned as Phase 2c; nothing in this slice draws graphics).
**Did:** implemented slice 2a directly, in the product layer, with no frozen module touched. **`versions.py`** — an immutable version chain per case (`<BP_CASES_DIR>/<id>/vNNN.json`), a canonical-JSON `bundle_hash` recorded in each envelope, legacy flat cases adopted as version 1, corrupt/tampered versions refused on read, delete removes the chain. **`compare.py`** — Option-A comparison over stored versions: same-method rule enforced, artifact rows aligned by metric, stored values copied verbatim, a metric absent from a version reported as "not computed for this version", differences in `spec_hash`/`outputs_hash`/`method_version` listed, a disclosure naming each compared version's `bundle_hash`/`outputs_hash`, deterministic stdlib HTML rendering. **`signoff.py`** — append-only sign-off records carrying the owner-approved Option-A signature text, reviewer name/role/scope/decision, the signed version hashes and a tamper-evident integrity check. **Routes** added to the pure dispatch (already reachable through the server delegation, so no core edit): `GET/POST /api/cases/{id}/versions`, `GET /api/cases/{id}/versions/{n}`, `GET /api/cases/{id}/compare`, `POST/GET /api/cases/{id}/signoff`. Tests: `tests/test_product_versions.py`, `tests/test_product_compare.py`, `tests/test_product_signoff.py`, `tests/test_product_routes.py` plus an HTTP extension in `tests/test_product_server.py` (22 new tests).
**Files:** `src/bp/product/versions.py`, `src/bp/product/compare.py`, `src/bp/product/signoff.py`, `src/bp/product/api.py`, new product tests, docs (B-086/B-087, CHANGELOG 0.61, BACKEND_CONTRACT §6, PRODUCT_BACKEND_PLAN 2a/2c, README, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **702 tests OK** including the frozen-contract and docs-state guards; the version chain, comparison rules, sign-off wording and tamper cases are all tested; the routes were exercised over HTTP.
**Commit:** `this commit`.
**Open/next:** Phase 2b (ops/observability, offline packaging) then Phase 2c (deterministic charts/SpreadsheetML, B-087), then **stop before the UI** per the owner's instruction.

---

## 2026-10-21 — [review] Product slice 1 reviewed, wired in, and two defects fixed (B-085)

**Delivered by:** MiniMax/OpenCode on branch `opencode/product-slice-1`, commit `b411083`: new `src/bp/product/**` (case store, route dispatch, stdlib HTML export) + 51 product tests + the §6 rows and count/version/changelog/worklog docs.
**Review verdict: accepted with fixes.** The design is right: a local case store that treats the frozen bundle as an opaque document (atomic write via temp+rename+fsync, 12-hex id validation, path-traversal refusal, corrupt-bundle refusal, opaque load), a pure `handle(method, path, body) -> (status, payload)` dispatcher with no server edit, and an HTML export that copies the stored report and artifact values. The product tests set/restore `BP_CASES_DIR` properly and the package imports only the standard library.
**Defects found and fixed in this integration commit:**
1. **Tautological check.** `test_the_product_layer_computes_no_number` compared a set with itself (`recorded` and `shown` were the same expression), so it could never fail. Replaced with a real check: the numbers returned by the dispatch and shown by the HTML export are compared against the numbers in the bundle actually written to the store, so an invented/rounded/recomputed value now fails.
2. **Double-encoded text in four factual docs.** The slice rewrote CHANGELOG/HANDOFF/HOME/WORKLOG with cp1252→UTF-8 mojibake (e.g. `â€”` for an em dash, `Â§` for a section sign). Repaired to proper UTF-8; this is why the review diff looked much larger than the intended count/version edits.
3. **Registry portability bug (pre-existing, found because the slice was tested in a fresh worktree).** `catalogue_import` hashed raw catalogue bytes, and git's Windows checkout (`core.autocrlf=true`) turns committed LF into CRLF, so a fresh worktree hashed different bytes and `test_shipped_registry_equals_fresh_import` failed there while passing in the main checkout. The hash is now computed over LF-normalised bytes and the shipped registry was regenerated (records unchanged); a new test imports a CRLF copy and asserts the same hash.
**Wiring (the core edit the plan delegated to me):** added `from .product import api as product_api`, a GET/POST branch and a new `do_DELETE` in `src/bp/server.py`, all delegating to the product dispatcher; the product POST branch parses the body without `parse_float=Decimal` so bundles round-trip exactly. The frozen route fixture is unchanged — the product surface is tracked in `BACKEND_CONTRACT.md` §6. New `tests/test_product_server.py` (3 HTTP tests) covers list/post/get/delete, 404/422 refusals, and that existing routes are unchanged.
**Files:** `src/bp/server.py`, `src/bp/catalogue_import.py`, `src/bp/data/registry_v0_2.json`, `tests/test_product_boundary.py` (fixed check), `tests/test_product_server.py` (new), `tests/test_registry.py` (new EOL test), docs (B-085, CHANGELOG 0.60, BACKEND_CONTRACT §6, HOME/HANDOFF/CONTRIBUTORS digits, this entry).
**Verified:** full suite **680 tests OK** including the frozen-contract and docs-state guards; the four repaired docs render correctly; the wired routes were exercised over HTTP.
**Commit:** `this commit`.
**Open/next:** delegate slice 2 (reviewer sign-off record with the Option-A wording, multi-period comparatives + case versions per Option A, ops/observability, offline packaging) to MiniMax; DOCX/XLSX export remains a later slice behind a declared product dependency.

---

## 2026-10-21 — [product] Product slice 1: durable case store, case routes, HTML export

**Ask:** owner instruction "let minimax do the product backend" (B-080) and "let's do your recommended sequence of finishing the backend product before finally doing the UI" (B-081): the first product slice over the frozen core (B-079), in the design owner's lane.
**Did:** added the new product package `src/bp/product/` — a local durable case store (one JSON bundle per case under `BP_CASES_DIR`, default `cases/`; atomic writes; ids refused unless 12 lowercase hex characters; path traversal refused; a corrupt bundle refuses to load with a clear message), a pure additive route dispatch for `GET /api/cases`, `POST /api/cases`, `GET /api/cases/{id}` and `DELETE /api/cases/{id}` (no `server.py` edit — the computation owner wires it after review), and a self-contained HTML export of a stored bundle with the delivered report text and the artifact table copied exactly. The bundle is opaque: the product layer stores, lists, copies and renders what was recorded, imports nothing from the frozen core, and computes no business number.
**Files:** `src/bp/product/__init__.py`, `src/bp/product/cases.py`, `src/bp/product/api.py`, `src/bp/product/export.py` (new), `tests/product_fixtures.py`, `tests/test_product_cases.py`, `tests/test_product_api.py`, `tests/test_product_export.py`, `tests/test_product_boundary.py` (new), `docs/BACKEND_CONTRACT.md` (§6 rows only), `docs/CHANGELOG.md` (0.59), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md` (count/version digits only). No frozen core module, test, fixture or factual document was edited.
**Verified:** full suite (frozen-contract guard + docs-state guard + 51 product tests) **676 tests OK**; the product boundary is checked by a test that parses the product sources and fails if they import anything but the standard library, import or shadow a frozen core module, reference a third-party package, or show a number that was not recorded.
**Commit:** `this commit`.
**Open/next:** the route dispatch still needs the computation owner to wire it into `src/bp/server.py` (an additive route table; the frozen route surface is unchanged until they do); the DOCX/XLSX export needs dependencies that are not in this slice, so it is not in this commit.

---

## 2026-10-21 — [computation] Sign-off wording and multi-period Option A resolved (B-084)

**Ask:** owner answered D4 and the multi-period question: **"a."** (sign-off Option A) and **"option a"** (multi-period Option A); also noted the workspace-root `A1.jpg` is a website reference for later and the logo is to be left alone.
**Did:** recorded both choices as B-084 and updated the plan: **D4 = Option A** — the stored signature text is now fixed and quoted in Phase 2 ("I reviewed the named case bundle and its disclosed limitations. This signature records that review; it does not assert that the inputs are true or that the analysis is correct."). **Multi-period comparatives and case versioning = Option A** — product-layer, no unfreeze, moved from the unfreeze queue (Phase 3) into the delegated Phase 2 slice: one frozen session per period, immutable case versions (monotonic version, spec/output hashes, method id+version), side-by-side comparison of stored bundles under declared comparability rules, missing periods shown as "not computed" and never filled, every displayed number byte-identical to its stored bundle, no arithmetic in the product layer. Phase 3 now holds only PDF/OCR ingestion and any core-lane export. Recorded `A1.jpg` as the owner's UI-phase website reference (outside the repo, not committed; logo untouched).
**Files:** `docs/DECISIONS.md` (B-084; B-083's D4 status updated), `docs/PRODUCT_BACKEND_PLAN.md` (Phase 0/2/3/5 + definition of done), `docs/BACKEND_CONTRACT.md` (§6 planned surface), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** MiniMax's slice 1 (case store + dispatch + HTML export) to review; then delegate slice 2 (sign-off record, multi-period Option A comparison, ops/packaging). D3 disclosure remains deferred by choice.

---

## 2026-10-21 — [computation] Phase-0 answers, slice-1 rescope and the multi-period proposal (B-083)

**Ask:** owner answered the plan's four Phase-0 questions and said "okay do the things while waiting for minimax".
**Did:** recorded the answers as B-083 and amended the plan: **D1 accepted** (local single-user v1, to be improved after it is seen working), **D2 accepted** (cases kept until the owner deletes them, no outbound transfer, model assistance off by default), **D3 deferred** — the AI-use disclosure export is removed from slice 1 and returns later as its own separately-decided slice, **D4 open** — explanation requested; sign-off stays in Phase 2 and its record schema does not depend on the wording. Rescoped slice 1 accordingly: local case store + additive route dispatch + **stdlib HTML export** of the delivered report verbatim (no disclosure, no third-party dependency; DOCX/XLSX deferred behind a declared product-layer dependency). Wrote `docs/proposals/MULTI_PERIOD_VERSIONING.md`: multi-period comparatives and case versioning split into **Option A** (product layer, no unfreeze — one existing session per period stored as an immutable case version, compared side by side under declared comparability rules, recommendation) and **Option B** (core multi-period delivery: single spec with N periods, per-period artifacts and a deterministic in-delivery diff — a genuine unfreeze), with acceptance criteria and the owner questions.
**Files:** `docs/DECISIONS.md` (B-083), `docs/PRODUCT_BACKEND_PLAN.md`, `docs/BACKEND_CONTRACT.md` (§6 planned surface), `docs/proposals/MULTI_PERIOD_VERSIONING.md` (new), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** D4 wording choice (owner); A-vs-B choice for multi-period (owner); MiniMax's slice 1 to review — the delegation addendum says item 3 (disclosure) is deferred and must not be committed. My next computation-owner work while waiting: review slice 1 and wire the product dispatch into the server once it passes.

---

## 2026-10-21 — [computation] REW manual inventory refresh (v0.4, from the review queue)

**Ask:** queue item from the decision-briefs review (appendix B items 2-4): the ratified REW manual's "what exists in code today" table had gone stale.
**Did:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` §13 refreshed to match the code and bumped to v0.4: the durable append-only retrieval log with fail-closed writes and `reverify` (B-058), Crossrefâ†’OpenAlex failover with recorded attempts and the manual drift sweep (B-064), the full verified-method library and applied methods, CSV/TSV + XLSX ingestion with sheet selection and a declared merged-cell policy (B-065/B-071/B-076), APA/Harvard citation formatting (B-059), and the AI-use disclosure export listed as a planned product-backend item (B-081). §16 change log records the refresh. The stage list, checkpoints, screening log and manuscript assembly remain **not built**, and R1-R10 remain proposals — the refresh changes only the factual inventory, not any status claim.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md`, `docs/proposals/DECISION_BRIEFS.md` (appendix B items marked fixed), `docs/CHANGELOG.md`, `docs/HOME.md`, `docs/HANDOFF.md`, `docs/WORKLOG.md`.
**Verified:** docs-only; full suite (frozen-contract + docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** owner answers to the plan's D1-D4 (or acceptance of the defaults); MiniMax's Phase-1 product slice. The two register-hygiene items from the briefs were fixed in this same increment: the duplicate B-031 row is marked SUPERSEDED, and the R1-R10 ratification now has the open decision row **B-082** (the row tracks it; the owner still decides it).

---

## 2026-10-21 — [computation] Product-backend sequence and delegation boundary (B-081)

**Ask:** "let's do your recommended sequence of finishing the backend product before finally doing the UI. delegate some work to minimax when you dont have to do it."
**Did:** wrote the sequence down as a working plan instead of ad-hoc instructions, and fixed the file-level boundary that lets both owners work in the same repo in parallel. New `docs/PRODUCT_BACKEND_PLAN.md`: **Phase 0** four owner questions (deployment model, case retention/privacy, disclosure audience, sign-off semantics) each with a slice-1-safe default; **Phase 1** delegated to MiniMax - local durable case store (`src/bp/product/**` as new files + additive `/api/cases` routes, opaque JSON bundles with atomic writes, export/restore/delete), AI-use disclosure export from recorded metadata, DOCX/XLSX export of the delivered report verbatim; **Phase 2** delegated - reviewer sign-off record, ops/observability counters (no case content in logs), offline packaging; **Phase 3** computation-owner unfreeze requests, ordered (multi-period comparatives/versioning, then PDF/OCR + SPSS ingestion, core-lane exports only if the product layer cannot host them); **Phase 4** owner-gated tracks (REW ratification, retrieval sources, tax/ledger/templates/reviewers, real-case evaluation); **Phase 5** the UI only after 1-2 are accepted. Boundary rules recorded in B-081 and in `BACKEND_CONTRACT.md` §4: product code and product tests are new files (`src/bp/product/**`, `tests/test_product_*.py`); per increment MiniMax may update only count/version digits in HOME/HANDOFF/CONTRIBUTORS plus one CHANGELOG and one WORKLOG `[product]` entry; the frozen core, existing tests/fixtures, `DECISIONS.md` and claim wording stay untouched; both guards must pass.
**Files:** `docs/PRODUCT_BACKEND_PLAN.md` (new), `docs/BACKEND_CONTRACT.md` (§4/§6), `docs/DECISIONS.md` (B-081), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only increment; full suite (including the frozen-contract and docs-state guards) **625 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** owner answers to D1-D4 (or acceptance of the defaults); MiniMax's Phase-1 slice to review; the queued REW inventory refresh is the next computation-owner item.

---

## 2026-10-21 — [review] Decision briefs draft (MiniMax task 3), reviewed and merged

**Delivered by:** MiniMax/OpenCode on branch `opencode/decision-briefs`, commit `566a6af`: `docs/proposals/DECISION_BRIEFS.md` (369 lines) with five briefs for the open owner decisions — B-005 reviewers, B-028 next templates, B-032 ledger engine, B-052 taxation, REW R1-R10 — each giving "what it blocks today" citations, the state of the code, options with costs, one clearly labelled MiniMax recommendation, plus an OPEN-items appendix and an appendix of contradictions it found between repository documents.
**Review:** substantive and useful. I verified 55 of its `path:line` citations against the code and docs: 37 exact at master, 13 shifted by under 30 lines (later increments added lines) and 5 shifted materially by B-077's new section — the cited content was found in every case and **no factual claim was contradicted**. Re-checked the contradiction list: #1 (two B-031 rows with different statuses), #2-#4 (the REW manual's inventory still says "no durable log yet" / Excel ingestion not built / statistics library without the later methods), #6 (ledger engine pre-empted by B-044) and #7 (R1-R10 has no decision id of its own) are real; #5 is a wording matter (B-052 is deferred but deliberately kept on the gate list); #8 (SOURCE_INVENTORY.md missing from the HOME spine) was real and is already fixed in `5023aa4`. Annotated the draft rather than rewriting it: a review-status block states the drafting base (`c06c61f`) and that line numbers are as-of that base, the B-066 citation is fixed, #8 is marked fixed, A12 is marked resolved. The stale REW inventory (#2-#4) is **queued** as a separate REW manual refresh (not done here — it edits the ratified manual). The file stays a **DRAFT** in `docs/proposals/`: it changes no decision, no number and no test.
**Files:** `docs/proposals/DECISION_BRIEFS.md` (new), `docs/HOME.md` (proposals row + version), `docs/HANDOFF.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** docs-only increment; full suite **625 tests OK**; docs links resolve; docs-state guard passes.
**Commit:** `this commit`.

---

## 2026-10-21 — [review] Docs-state sync guard (MiniMax task 1), reviewed and merged

**Delivered by:** MiniMax/OpenCode on branch `opencode/docs-sync`, commit `264fee1` "Add docs-state sync tests": a 335-line `tests/test_docs_sync.py` (7 tests) plus count updates in HOME/HANDOFF/CONTRIBUTORS.
**Review:** the design is sound and the non-tautology requirement is met — every expectation is read from somewhere other than the document being checked (test count from a real `TestLoader().discover`, build from the newest CHANGELOG bullet, method ids from the imported `LIBRARY`, decision rows from `DECISIONS.md`, spine coverage from the `docs/*.md` listing), a missing pattern raises instead of silently skipping, and test 7 proves the parsers actually move when a document's own digits change. I re-ran the claimed proof independently: changing `**625 tests**` to `**626 tests**` in HOME made it fail with `docs/HOME.md says 626 tests, but the suite holds 625 tests`; restoring it went green.
**What I had to reconcile:** the branch was based before B-077/B-078/B-079, so its counts (622) and build (0.51) were stale; on merge the guard correctly failed on 618 vs 625 and on one genuine gap — `docs/SOURCE_INVENTORY.md` had no row in the HOME documentation spine (exactly the kind of drift the guard exists to catch). Fixed the spine row and bumped the docs to build **0.53** / **625 tests**; no assertion was weakened.
**Files:** `tests/test_docs_sync.py` (new), `docs/HOME.md`, `docs/HANDOFF.md`, `docs/CONTRIBUTORS.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** 7 new tests; full suite **625 tests OK**; mutation proof above; docs links resolve.
**Commit:** `this commit`.

---

## 2026-10-21 — [computation] Freeze the core deterministic backend, delegate the product backend (B-079, B-080)

**Ask:** "freeze the core deterministic backend. let minimax do the product backend."
**Did:** two things. **(1) Freeze, with a guard.** New `docs/BACKEND_CONTRACT.md` states exactly what is frozen (stage/flow contract, spec + hash, the 36 method contracts — id, tier, metric, unit, `test_names` order, claim ceiling, category, input names — the 38 presets, the 12 API route families, the delivery shape and the verification invariants), the unfreeze policy (owner approval â†’ computation owner writes the B-decision, changes code + tests, updates the fixture in the same commit; bug fixes restoring declared behaviour need a trap test but no unfreeze) and the product-backend lane rules. The freeze is **enforced**, not just declared: `tests/test_frozen_contract.py` compares the live library/presets/server source against `tests/fixtures/frozen_contract.json` and fails with a message naming the freeze. **(2) Ownership.** Recorded the owner directive that the product backend is the design owner's lane (B-080) — additive routes/modules/storage/workflows over the frozen core, with the hard boundary that MiniMax may not edit frozen modules, tests, the fixture or factual docs, may not compute or adjust any number/threshold/rating/caveat/honesty notice/claim wording, and new endpoints must delegate computation to the frozen method library (never reimplement a formula). A needed core change is an unfreeze request handled by the computation owner under B-079.
**Files:** `tests/test_frozen_contract.py` (new), `tests/fixtures/frozen_contract.json` (new), `docs/BACKEND_CONTRACT.md` (new), `docs/DECISIONS.md` (B-079, B-080), `docs/CONTRIBUTORS.md` (§1B, stop-and-ask, fact map), `docs/HANDOFF.md`, `docs/HOME.md`, `README.md`, `docs/CHANGELOG.md`, `docs/WORKLOG.md`.
**Verified:** 3 new contract tests (methods/presets/routes match the frozen fixture; route count still 12); full suite **618 tests OK**; docs links resolve.
**Commit:** `this commit`.
**Open/next:** nothing computation-side is unblocked now — the lane is drained and frozen. The next phase is the design owner's product backend (B-080). Open owner decisions remain B-005 (reviewers), B-028 (templates), B-032 (ledger engine), B-052 (tax), REW R1–R10 (ratification), plus the frontier-model lane parked in B-075. MiniMax's docs-sync test and decision-brief drafts are still awaiting the owner's go for review/merge.

---

## 2026-10-21 — [computation] Equity bridge and mid-year DCF timing (B-078)

**Ask:** "go" for the valuation completion — the last unblocked computation item.
**Did:** two linked valuation pieces. New T2 **`equity_bridge`**: takes a declared enterprise value and subtracts declared net debt (debt minus cash), minority interest and preferred equity to report an equity value, plus a per-share value only when `shares_outstanding` is declared (no dilution, options or treasury method). Negative bridge components are refused as sign errors; a non-positive share count is refused; a **negative equity value is reported** because an EV that does not cover the declared claims is a real finding, not an input error. `dcf_valuation` gained a declared **mid-year timing convention** as an optional enum (`timing: end|mid`, default `end`): under `mid`, explicit flow t and the terminal value are discounted at exponent tâˆ’0.5 / nâˆ’0.5, so every flow is assumed mid-period; the default leaves every existing output, golden fixture and re-performance bundle unchanged. Five frozen checks for the bridge, a sixth check for the mid-year DCF path; presets `dcfmid`/`equitybridge`; sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-078, changelog 0.51, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 6 new tests — bridge arithmetic against an independent float route (equity value 1570939.14; net debt 150000; per-share 15.7093914), frozen checks declared and passing with and without a share count, refusals for negative components and bad share counts, pipeline delivery (9 artifacts, USD), mid-year DCF against an independent half-period loop, mid > end, invalid timing refused, presets and determinism. Full suite **615 tests OK**.
**Commit:** `this commit`.
**Open/next:** this drains the unblocked computation lane. What remains is owner-gated (open decisions B-005/B-028/B-032/B-052, REW R1–R10), frontier-model parked (B-075), or backend features that need a B-decision before build (AI-use disclosure export, reviewer workflow, case workspace/retention, versioning, model pinning/drift gate). The workbench UI is the design owner's domain (B-066) and the backend contract (routes, presets, JSON) is stable for it.

---

## 2026-10-21 — [computation] IRR and discounted payback (B-077)

**Ask:** "now what's next for you to do?" — with the docs-sync guardrail at MiniMax and the decision briefs also delegated, the next unblocked computation item was the gap map's capital-budgeting completion.
**Did:** two T1 methods, both on the `npv` timing convention (first cash flow at t=0, end-of-period after that). **`irr`**: the discount rate at which the declared cash flows have zero NPV, found by bracketing the NPV function over the declared range -99.99% to 1000% and bisecting (reference route: Newton-Raphson). A cash flow that never changes sign has no IRR and is refused; a cash flow with several sign changes can have several IRRs, so the method **refuses and lists the roots** rather than choosing one. **`discounted_payback`**: cumulative present values until the initial outlay is recovered, with the recovery interpolated linearly inside the recovering period; a positive first cash flow is refused and an outlay never recovered within the horizon blocks instead of reporting a number; `rate` is optional and defaults to 0 (ordinary payback). Both have declared-unit templates (IRR as a percentage), presets `irr`/`dpayback`, sandbox CASES and session input-map entries.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_investment.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-077, changelog 0.50, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — IRR matches its independent Newton route and the NPV-zero identity, crosses zero at the root, is scale-free; signless and multi-root cash flows refused; discounted payback matches the float route, equals the ordinary payback at rate 0, cannot shorten when the rate rises, is scale-free, and blocks when never recovered; pipeline delivery for both (percentage rendering; artifacts/test-set parity); presets and determinism. Full suite **609 tests OK**.
**Commit:** `this commit`.
**Open/next:** valuation completion remains the natural next unblocked item (equity bridge from enterprise to equity value, mid-year convention in `dcf_valuation`); everything else unblocked is either parked for the frontier-model lane (B-075) or gated on an owner decision (B-005/B-028/B-032/B-052, REW R1–R10).

---

## 2026-10-21 — [computation] XLSX sheet selection and merged-cell policy (B-076)

**Ask:** "do number 2" — the XLSX hardening item (multi-sheet selection + a declared merged-cell policy) from the proposed next-three list.
**Did:** `read_xlsx`/`read_table` now take `sheet` (exact case-sensitive name or 1-based position; default still the first sheet; unknown names/numbers refused listing the workbook's sheets) and report `sheets` + `sheet_index` on every XLSX table. Merged cells are **refused by default** with the ranges named and the declared alternative offered, because repeating an anchor across its range or blanking it would fabricate or lose data; `merged="top_left"` expands each range from its anchor, skips blank anchors, refuses overlapping/nested merges as malformed, and records `merged_cells` plus a provenance-note sentence calling the repetition a declared convention. `sheet`/`merged` are XLSX-only and refused for CSV/TSV. Wired through `POST /api/ingest` as optional fields and the CLI as `--sheet`/`--merged`. **Also fixed a latent bug:** the workbook relationship id was looked up with a malformed namespace, so every workbook silently fell back to `sheet1.xml` — harmless while only the first sheet was read, fatal for sheet selection; the fallback now applies only to the first sheet when the relationship is genuinely absent.
**Files:** `src/bp/ingest.py`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-076, changelog 0.49, limitations, gap map, HOME, HANDOFF, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests — select-by-name/index with metadata, unknown/invalid sheet refusals, CSV option refusals, default merged refusal naming the range, declared expansion (values + `merged_cells` + provenance note), malformed and overlapping merge refusals, merged-header duplicate refusal, API sheet selection and merged policy (including an invalid policy); CLI exercised by hand for default/sheet-by-name/sheet-by-number/unknown-sheet/merged-refuse/merged-top_left; full suite **598 tests OK**.
**Commit:** `this commit`.
**Open/next:** **[design]** the workbench ingestion card still sends only filename+base64 — exposing the new optional `sheet`/`merged` fields is presentation work for the design owner (B-066). Remaining ingestion gaps stay refused/declared: PDF/OCR/SPSS, and reading several sheets into one table (needs a declared concatenation rule).

---

## 2026-10-21 — [documentation] Parked frontier-model queue, and a truthful HANDOFF

**Ask:** "on those computations that require deepseek pro, write or park it in the manual or notes, as we will get back to them when we have enough credits."
**Did:** created `docs/PARKED_QUEUE.md` — the register for the six heavy statistics items reserved for the DeepSeek Pro lane (Tukey/Dunnett/Games-Howell, unbalanced two-way/ANCOVA/three-way, repeated measures, k-means, factor analysis, non-linear time series). Each row states the blocker, the offline oracle already installed for goldens, and the output that would be accepted; the file also separates the *non*-frontier items (imputation, standards/filings/tax retrieval, PDF/OCR/SPSS ingest, breadth templates, REW) so they are not mistaken for the parked lane, and states the un-park trigger: an explicit owner grant of the frontier lane, not a general "continue". Recorded as B-075. **Fixed the stale handoff**: `HANDOFF.md` still said build 0.40 / 510 tests and listed as unbuilt everything finished since (paired/one-sample t, factorial/post-hoc, valuation, economics, appraisal, logistic/alpha, ingestion mapping); it now reports 0.48 / 588, carries the full method list, marks section A done, restates section C with what is built vs parked, and adds section H pointing at the parked queue. `HOME.md` gained the parked-queue rows and lost its stale "DCF/WACC … not built" line; `CONTRIBUTORS.md` links the queue and lists un-parking under "stop and ask".
**Files:** `docs/PARKED_QUEUE.md` (new), `docs/HANDOFF.md`, `docs/HOME.md`, `docs/CONTRIBUTORS.md`, `docs/DECISIONS.md` (B-075), `docs/WORKLOG.md`.
**Verified:** documentation-only increment; no code, test or fixture touched. Relative links in the new/edited files resolve; the suite is unchanged at **588 tests OK**.
**Commit:** `this commit`.
**Open/next:** the computation lane is caught up on everything buildable without the frontier model or an owner decision. Remaining work is owner-gated: parked queue (B-075, needs credits), B-005 reviewers, B-028 templates, B-032 ledger engine, B-052 taxation, REW R1–R10 ratification. Design/presentation is MiniMax's domain (B-066).

---

## 2026-10-21 — [computation] Logistic regression and Cronbach's alpha (B-074)

**Ask:** "correction, finish those you can do" — the remaining statistics items that do not need a frontier model or a new distribution.
**Did:** two T1 methods. `logistic_regression`: binary 0/1 outcome with up to five numeric predictors, Newton-Raphson (IRLS) at 1e-10 tolerance, no regularisation, Wald standard errors/p-values, odds ratios, log-likelihood, null log-likelihood and McFadden pseudo R-squared; non-convergence/separation, single-class outcomes, non-0/1 codes and collinear designs are refused. `reliability_alpha`: Cronbach's alpha from an items column map, listwise deletion with the excluded count, the classic k/(k-1)(1 âˆ’ Î£item variances / total variance) formula. Goldens for the logistic model generated from `statsmodels.Logit` offline; five frozen checks each; presets `logit`/`alpha`; sandbox and session coverage.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_logit_reliability.py`, `tests/fixtures/logistic_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-074, changelog 0.48, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 9 new tests — all statsmodels goldens matched (coefficients, SEs, p-values, log-likelihood, pseudo RÂ²), frozen checks, separation/single-class/bad-code refusals, alpha against an independently coded classic formula, refusals for single-item and zero-variance cases, pipeline delivery for both, contract/preset, determinism. **588 tests OK.**
**Commit:** `this commit`.
**Open/next (for the frontier model):** k-means clustering, factor analysis, unbalanced/ANCOVA/repeated-measures designs, Tukey/Dunnett/Games-Howell, non-linear time series. The offline oracles for these are installed (sklearn, factor_analyzer, statsmodels AnovaRM, scipy studentized_range/dunnett).

---

## 2026-10-21 — [computation] CBA, cost-effectiveness and SROI (B-073)

**Ask:** "go on: … CBA/CEA/SROI."
**Did:** three T2 appraisal methods. `cost_benefit`: discounted present values of declared costs and benefits, NPV and benefit-cost ratio (omitted when PV costs are zero); five frozen checks. `cost_effectiveness`: ICER for each option against the first-listed comparator, with incremental cost/effect and dominance flags; refuses a single option, negative costs and a zero effect difference. `sroi`: present value of declared social benefits over the declared investment, with net value; refuses a non-positive investment. All three are arithmetic on owner valuations — no effect is monetised by the system, no deadweight/additionality adjustment is invented, and no willingness-to-pay threshold is assumed.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_appraisal.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-073, changelog 0.47, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — present values against an independently written discounting loop, ICER/dominance arithmetic, SROI ratio identity, frozen checks, refusals for mismatched lengths, zero-effect comparators and non-positive investments, pipeline delivery for all three, contract/preset, determinism; sandbox and session coverage. **579 tests OK.**
**Commit:** `this commit`.
**Open/next:** remaining from the batch — ANCOVA / repeated measures / unbalanced designs, Tukey–Dunnett–Games-Howell, logistic regression, reliability/factor analysis, clustering, non-linear time series. The first three groups need either a ratified SS/design convention or distributions the standard library lacks (studentized range, multivariate t); logistic regression, reliability and clustering are feasible with declared conventions.

---

## 2026-10-21 — [computation] Ingestion mapping, unit economics and multi-product break-even (B-071, B-072)

**Ask:** "go on: … unit economics / multi-product break-even … ingestionâ†’method mapping helper."
**Did:** `ingest.to_method_inputs` maps named columns into a method's declared inputs — `value_list`/`code_list` from one column, `column_map` from an object of name â†’ column, cleaned through the method's own `validate_inputs` and `profile` so a bad mapping is refused before running; only list-shaped inputs (a scalar rate cannot come from a column), and the provenance note says the file hash identifies the source, not that the data is verified. Exposed as an optional `map` on `POST /api/ingest`. Then two T1 finance methods: `unit_economics` (margin, margin rate, payback, optional period-value LTV and LTV/CAC) and `multi_product_breakeven` (mix-weighted contribution margin, break-even units and revenue, per-product units), each with five frozen checks and declared assumptions (constant churn, fixed mix, no tax/discounting).
**Files:** `src/bp/ingest.py`, `src/bp/server.py`, `src/bp/methods.py`, `tests/test_economics.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-071/B-072, changelog 0.46, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — columnâ†’method mapping (value and column_map shapes), refusals for text/unknown/scalar/unmapped inputs, unit-economics arithmetic and refusals, multi-product break-even arithmetic (break-even 2000 units; 1500 coffee / 500 cake; revenue 10500) and refusals, frozen checks, pipeline delivery, contract/preset, determinism; sandbox and session coverage. **568 tests OK.**
**Commit:** `this commit`.
**Open/next:** CBA/CEA/SROI, reliability (Cronbach's Î±), logistic regression, clustering, non-linear time series; ANCOVA/repeated-measures/unbalanced designs and Tukey/Dunnett/Games-Howell need distributional work (studentized range / multivariate t) not in the standard library.

---

## 2026-10-21 — [computation] Factorial two-way ANOVA and post-hoc pairwise tests (B-070)

**Ask:** "go: factorial ANOVA + post-hoc pairwise tests."
**Did:** added two T1 methods. `two_way_anova`: balanced two-way factorial ANOVA on one numeric response — both main effects and the interaction, sums of squares, mean squares, F tests, degrees of freedom and partial eta-squared. Unbalanced designs and empty cells are **refused** (the SS type would be an unratified convention). Five frozen checks: independent float route, SS decomposition, F = MS/MS_error, shift invariance, scale equivariance of F. `posthoc_pairwise`: every unordered pair of independent groups compared with a Welch t-test, reporting the difference, raw p and adjusted p under a **declared** correction (Holm default, Bonferroni, or explicitly `none`), with `n_pairs`, `n_rejected` and the pair design recorded. Five frozen checks: independent float route, adjusted â‰¥ raw, declared correction reproduced step by step, pair count = k(kâˆ’1)/2, reversing group order negates differences and keeps p. Goldens generated offline with numpy/scipy; both wired into sandbox CASES, the session input map and presets `factorial`/`posthoc`; a `records` input type was added for the factorial design.
**Files:** `src/bp/methods.py` (records input type, both methods and contracts), `src/bp/server.py` (presets), `tests/test_factorial_posthoc.py`, `tests/fixtures/two_way_golden.json`, `tests/fixtures/posthoc_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-070, changelog 0.45, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 12 new tests — goldens against numpy/scipy for a main-effects and an interaction design, hand-computable exact SS/F values (8/32/0/8, F 4/16/0), frozen checks declared and passing, unbalanced/broken-design refusals, Welch+Holm goldens, adjustment-method behaviour, invalid-group refusals, full pipeline delivery for both, contract/preset assertions, determinism. **557 tests OK.**
**Commit:** `this commit`.
**Open/next:** unbalanced/ANCOVA/repeated-measures designs and Tukey/Dunnett procedures; then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 — [computation] Multi-currency: ISO 4217 registry, per-currency precision, declared-rate conversion (B-069)

**Ask:** "also allow it to use multi-currencies that include dollar, euro, and chinese yuan and other currencies of the world."
**Did:** `src/bp/currency.py` — a declared ISO 4217 table of 160+ currencies with their **minor units** (0 for JPY/KRW/VND/ISK, 3 for KWD/BHD/OMR, 4 for CLF, 2 for USD/EUR/CNY and most others), code normalisation and validation, and exact Decimal conversion at a rate the owner **declares** (with provenance `user`/`sourced`/`assumption`, a mandatory source for `sourced`, and an optional declared date). Wired into the computation layer: unknown currency codes are refused at intake; money artefacts default to the currency's minor units when the request states no precision (JPY prints no cents, KWD prints three); a management-accounts spec takes its `places` default from its currency; new T1 method `currency_convert` with five frozen checks (float second route, reciprocal-rate round trip, zero, sign symmetry, linearity); `GET /api/currencies` lists the registry; preset `currency`. No exchange rate is fetched, hard-coded or verified, and one engagement stays single-currency (no consolidation or translation).
**Files:** `src/bp/currency.py`, `src/bp/methods.py` (currency and text input types + method), `src/bp/orchestrator.py` (intake validation, per-currency precision), `src/bp/accounts.py` (currency validation, places default), `src/bp/server.py` (catalog endpoint, preset), `tests/test_currency.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-069, changelog 0.44, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 14 new tests — major/zero/three/four-decimal currencies, 160+ code coverage, normalisation and unknown refusals, conversion arithmetic, same-currency rule, provenance rules, invalid amounts/rates, pipeline delivery with the appendix recording codes/rate/provenance/date, per-currency precision through npv (JPY 0, KWD 3, USD 2), unknown-currency intake refusal, accounts `places` defaults, `/api/currencies`, contract/preset, determinism; sandbox and session coverage via the shared maps. **545 tests OK.**
**Commit:** `this commit`.
**Open/next:** FX retrieval/verification and statement translation/consolidation remain out (they need a rate source and a translation standard); statistics backlog resumes with factorial ANOVA + post-hoc, then unit economics / CBA.

---

## 2026-10-21 — [computation] Valuation: WACC and DCF (B-068)

**Ask:** "go. automate everything" — continue the computation backlog without waiting for instruction.
**Did:** two valuation methods. `wacc` (T1): weighted average cost of capital from declared market values of equity and debt and declared costs of equity and **after-tax** debt; reports the WACC and both weights; five frozen checks (float second route, weights sum to one, WACC between the two costs, scaling both values changes nothing, a higher cost of equity raises the WACC); no tax is computed. `dcf_valuation` (T2): declared end-of-period free cash flows discounted at a declared rate, optional Gordon-growth terminal value on the last flow; reports explicit PV, terminal PV, terminal value, enterprise value, terminal share and the inputs; five frozen checks (second route, linear scaling in the cash flows, higher rate lowers value, terminal value equals the Gordon formula, no growth means no terminal value); refuses growth at or above the rate, a rate at or below -100% and an empty forecast. Both wired into sandbox `CASES`, the session input map and presets `wacc`/`dcf`.
**Files:** `src/bp/methods.py`, `src/bp/server.py`, `tests/test_valuation.py`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-068, changelog 0.43, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 11 new tests — arithmetic against an independently written discounting loop, five frozen checks each, refusals for invalid capital structures and DCF assumptions, full pipeline delivery for both with percentage/currency rendering, contract/preset assertions, determinism; sandbox parity and session coverage. **531 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA + post-hoc pairwise tests (using the existing `multiple_comparison`), then unit economics / multi-product break-even and CBA/CEA/SROI.

---

## 2026-10-21 — [computation] Inference completion 1: paired and one-sample t-tests (B-067)

**Ask:** "go. automate everything" — work the computation backlog autonomously.
**Did:** added two T1 methods that close the manual's 9B.2 paired/one-sample gap. `paired_t`: within-pair differences (first column minus second), a pair dropped and counted when either side is missing, with mean difference, sd/se, t, df, two-sided p, confidence interval, Cohen's dz and both column means; five frozen checks (independent float route, swapping columns negates the difference and t but keeps p, shift/scale behaviour, row-order invariance, missing pairs dropped not imputed). `one_sample_t`: one mean against a declared reference `mu0`, with sd/se, t, df, p, CI, Cohen's d and excluded count; five frozen checks (second route, shift invariance, positive scale equivariance, row-order invariance, missing entries excluded not valued). Both default to two-sided, refuse constant data through the profile, and are wired into the sandbox `CASES` test, the session input map and workbench presets `paired`/`onesample`; goldens generated offline with scipy (test fixtures only).
**Files:** `src/bp/methods.py` (both methods + contracts), `src/bp/server.py` (presets), `tests/test_inference_more.py`, `tests/fixtures/inference_golden.json`, `tests/test_sandbox.py`, `tests/test_session_api.py`, docs (B-067, changelog 0.42, limitations, gap map, HOME, README, CONTRIBUTORS, WORKLOG).
**Verified:** 10 new tests — scipy goldens to 1e-9, frozen checks declared and passing, constant-data and missing-reference refusals, full pipeline delivery for both, contract/preset assertions, determinism; sandbox parity and session coverage via the shared maps. **520 tests OK.**
**Commit:** `this commit`.
**Open/next:** factorial ANOVA and post-hoc pairwise tests (using the existing `multiple_comparison`), then DCF + WACC.

---

**Newest first. Never rewrite an entry.** One entry per increment (not per message): the ask, what changed, what verified it, the commit, and what is next. Link to the source of truth rather than restating it — `CHANGELOG.md` has the build detail, `DECISIONS.md` the reasoning, this file the narrative and the sequence.

---

## 2026-10-21 — 9B.3 upgrade: power and minimum-effect planning (B-061)

**Ask:** "go" — continue closing the open statistics items (after multiple-comparison correction).
**Did:** added the T1 method `power_analysis` for a two-sample or one-sample comparison of means under the **normal approximation**: power for a stated effect, and the smallest effect that reaches a declared target power, plus standard error, non-centrality and the z critical value. Inputs declare design, effect, sample sizes, standard deviations, alpha (default 0.05), tails (two-sided default) and target power (default 0.8); one-sample designs refuse `n2`/`sd2`; invalid numbers, alpha or sizes are refused at intake. Five frozen checks: erfc-based independent second route agrees to 1e-9, zero effect gives power = alpha, power rises with effect size and with sample size, minimum effect falls with sample size. The normal approximation and its limits (no noncentral t, no proportions, no clustering/weights/repeated measures, no multiplicity) are declared in the template, caveats and appendix. Golden fixture generated offline with `scipy.stats.norm`; no scipy at runtime. The draft-audit claim checker caught the first template draft using "effect of" (intervention language) — reworded rather than weakening the checker.
**Files:** `src/bp/methods.py` (core, reference route, checks, profile, typing, caveats, template, contract), `src/bp/server.py` (preset `power`), `tests/test_power.py`, `tests/fixtures/power_golden.json`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-061, changelog 0.36, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-061.
**Verified:** 8 new tests — scipy golden values (three designs) to 1e-9 relative, zero-effect = alpha, one-sided vs two-sided ordering, sample-size movements, five invalid-input refusals, full pipeline delivery with licensed report, contract/preset, determinism; sandbox parity and session coverage via shared maps. **465 tests OK.**
**Commit:** `this commit`.
**Open/next:** missing-data mechanism modelling and survey weights are the last 9B.3 items and need a declared convention choice (extreme-bounds vs imputation; design vs frequency weights); then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 — [computation] Model-ownership split: computation vs design (B-066)

**Ask:** "we will divide the job… keep the computation part here; design/aesthetics goes to MiniMax. Put this rule in the manual that models can read that computation are exclusively your domain."
**Did:** recorded the division of labour as a binding rule in the two documents every model reads first: `docs/CONTRIBUTORS.md` **§1A** (new section) and `docs/HANDOFF.md` §2.9. Computation is exclusively the computation owner's (DeepSeek) domain — `src/bp/**`, `tests/**` and fixtures, the factual docs, every number/statistic/accounting figure, verification and audit logic, citation rules, type inference, claim ceilings and asserted wording, and any prompt affecting what is produced or validated. Design/aesthetics is exclusively the design owner's (MiniMax) domain — the workbench's presentation and look (`web/**` layout, CSS, typography, colour, spacing, iconography, responsiveness, component styling, visual report design) and behaviour-neutral interaction affordances. Boundary rules: design may not change numbers/claims/checks/schemas/tests; computation may not silently restyle (functional wiring only); neither owner edits the other's files, and cross-domain needs are noted here tagged `[computation]`/`[design]`; cross-domain features land as a computation commit then a design commit; conflicts escalate to the owner; the verification non-negotiables bind both.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md` (B-066), `docs/CHANGELOG.md` (0.41). No code changed.
**Verified:** docs only; test suite untouched at 510 tests.
**Commit:** `this commit`.
**Open/next:** the computation backlog is now the only work in this conversation — next increment is the paired/one-sample t-test pair, then DCF + WACC.

---

## 2026-10-21 — Ingestion first slice: CSV/TSV and XLSX to a typed table with provenance (B-065)

**Ask:** "go" — the other P0 gatekeeper: ingestion.
**Did:** added `src/bp/ingest.py`, standard library only. CSV/TSV (delimiter sniffed; UTF-8/CP1252/Latin-1) and XLSX (first sheet, read as a zip of XML parts — `zipfile` + `xml.etree`, no third-party library) become a typed table: column names, inferred `number`/`date`/`text`/`mixed` types, present and missing counts, sample values, rows, and a table-level provenance pointer (file, SHA-256, data row i and column j, sheet) stating that nothing is imputed or retyped. Declared conventions: first non-empty row is the header; headers must be non-empty and unique; a mixed number/text column is labelled `mixed` rather than coerced; formula cells use the cached value the file stores; XLSX dates are normalised with the workbook date system (1900 leap-year adjustment); caps of 5 MB / 1000 rows / 50 columns are **refused, not truncated**. **PDF, scans, images and SPSS `.sav` are refused with explicit messages** — no OCR or PDF text extraction exists, so pretending to read them would be invention. Wired as `POST /api/ingest` (base64, 422 on refusal, separate request-size limit), a workbench "Data ingestion" card with file picker and summary, and `python -m bp.ingest <file>`.
**Files:** `src/bp/ingest.py`, `src/bp/server.py` (route, body size), `web/index.html`, `tests/test_ingest.py`, `tests/test_ingest_api.py`, docs (B-065, changelog 0.40, limitations, gap map, REW §8, HOME, README, CONTRIBUTORS).
**Decisions:** B-065.
**Verified:** 14 new tests — typed CSV with missing/date columns, delimiter and encoding detection, mixed-column labelling, header refusals, row cap, XLSX shared strings/numbers/date styles, corrupt and empty workbook refusals, PDF/PNG/SPSS refusals, API decoder validation, endpoint 200/422, UI card; CLI smoke printed the summary; **510 tests OK**.
**Commit:** `this commit`.
**Open/next:** ingestion remains partial by design — PDF/scan/OCR and SPSS are refused, multi-sheet/merged-cell handling and automatic columnâ†’method-input mapping are not built. Elsewhere: imputation and complex-design inference, standards/filings/tax retrieval sources, and the owner gates (B-005 reviewers, B-028 templates, B-032 ledger engine).

---

## 2026-10-21 — Retrieval failover and drift sweep (B-064)

**Ask:** "go" — close the retrieval extras (declared source priority/failover, drift monitoring).
**Did:** two pieces. **(a) Source priority and failover**: the declared order is Crossref then OpenAlex, the API's default source is now `auto`, and every attempt is recorded in the retrieval log as `resolved` / `not_found` / `error` with the error detail. A source error is never swallowed silently; the next source is tried; if **every** source errors the lookup fails closed (502) instead of labelling the DOI "unverified". **(b) Drift sweep**: `drift_check` re-verifies the most recent logged retrievals and reports `hash_match` / `hash_differs` / `unresolvable_now` / `unreachable` per entry with a summary, flagging changed citations for human re-check and never rewriting the log. Exposed as `GET /api/literature/drift?limit=` (cap 25), a workbench "Check drift" button, and `python -m bp.literature drift [log] [limit]`.
**Files:** `src/bp/literature.py` (failover resolver, attempts in log records, `drift_check`, CLI), `src/bp/server.py` (auto source, sources listing with declared priority, drift endpoint, validation), `web/index.html` (drift button and output), `tests/test_literature_failover.py`, `tests/test_literature_api.py`, docs (B-064, changelog 0.39, limitations, gap map, REW §9 + Q7, HOME, README, WORKLOG, CONTRIBUTORS).
**Decisions:** B-064.
**Verified:** 12 new tests — failover on error and on not-found, all-not-found stays unverified, all-error fails closed, attempts recorded in the log, drift hash_match/hash_differs/unresolvable/unreachable, empty log, drift source order, API auto-source response, drift endpoint and limit validation, UI button; live smoke resolved a real DOI through `default_sources()` with the attempt logged and the drift sweep returning `hash_match`, plus the CLI printing the summary. **496 tests OK.**
**Commit:** `this commit`.
**Open/next:** standards/filings/tax source families (needs a source/licensing decision, not code) and extra scholarly APIs; then ingestion (the other P0), and imputation / complex-design inference for the statistics.

---

## 2026-10-21 — 9B.3 upgrade: weighted summaries with a declared weight kind (B-063)

**Ask:** "go" — close the last statistics item on the open list.
**Did:** added the T1 method `weighted_summary`: weighted mean, weighted standard deviation, total weight, **effective sample size** `(Î£w)Â²/Î£wÂ²` and **design effect** `n/n_eff`, with an overridable weight kind — `reliability` (default; unbiased weighted variance) or `frequency` (observations counted). One positive weight per value including missing entries (a missing value's weight drops with it); zero, negative, mismatched-length and blank weights are refused. **No inference**: no standard error, interval or test, because that needs a declared complex design (stratification, clustering, replicate weights) that is not implemented — and the honesty layer now says exactly that for this method instead of the generic "weights unsupported" line. Five frozen checks: float second route agrees, unit weights reproduce the ordinary sample summary, the mean is invariant to weight scaling, extra weight on larger values raises the mean, and the design effect is 1 for equal weights. The draft-audit claim checker again caught a template phrasing ("design effect of"); the template was reworded rather than the checker weakened.
**Files:** `src/bp/methods.py` (impl, stats helper, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty wording for the weighted method), `src/bp/server.py` (preset `weighted`), `tests/test_weighted.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, docs (B-063, changelog 0.38, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-063.
**Verified:** 9 new tests — exact weighted mean and reliability/frequency sds, equal weights equal the ordinary summary, missing values drop their weights, all frozen checks, five invalid-input refusals, full delivery with the design disclaimer, contract/preset, determinism; sandbox parity and session coverage via shared maps. **484 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 row is closed except imputation and complex-design inference (each needs its own declared model/design). Next: retrieval extras (standards/filings/tax source families, automatic failover, drift monitoring) and ingestion (the other P0).

---

## 2026-10-21 — 9B.3 upgrade: missing-data bounds with a declared mechanism (B-062)

**Ask:** "go" — continue closing the open 9B.3 statistics items.
**Did:** added the T1 method `missing_data_bounds`. It reports how much of a variable is missing and **bounds** the complete-data mean by the extreme-case convention — every missing value at the observed minimum (lower bound) or maximum (upper bound) — alongside the observed mean, observed range and bound width. The missing-data mechanism (`unknown`/`mcar`/`mar`/`mnar`) is an input the owner **declares**; it is recorded with an explicit note that the system cannot verify it from the data, and it changes no bound. No imputation and no probabilistic missing-data model. Five frozen checks: bounds bracket the observed mean, independently recomputed extreme cases agree, adding missing entries cannot narrow the bounds, the reported share is missing/total, and with no missing values the bounds collapse to the observed mean. The generic honesty layer used to append its listwise-deletion warning to this method — which contradicted the method's own stronger convention — so that notice is now suppressed for it, and the method's own disclaimer is what the delivery carries.
**Files:** `src/bp/methods.py` (impl, checks, profile, typing, caveats, template, contract), `src/bp/orchestrator.py` (honesty suppression), `src/bp/server.py` (preset `missing`), `tests/test_missing.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-062, changelog 0.37, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-062.
**Verified:** 10 new tests — exact bound arithmetic, missing codes and blanks both counted, zero-width when nothing is missing, declared mechanism changes no number and is labelled, all frozen checks, three invalid-input refusals, full delivery without the contradictory notice, contract/preset, determinism; sandbox parity and session coverage via shared maps. **475 tests OK.**
**Commit:** `this commit`.
**Open/next:** survey weights are the last 9B.3 item; then retrieval extras (source families, failover, drift monitoring) and ingestion.

---

## 2026-10-21 — 9B.3 upgrade: multiple-comparison correction (B-060)

**Ask:** "go on the still open, close them" — the statistical upgrades the honesty layer was only disclosing.
**Did:** closed the multiple-comparison item with a new T1 method `multiple_comparison`. It applies a declared correction to one family of raw p-values: **Holm** step-down (sort ascending, multiply the i-th smallest by kâˆ’i+1, running maximum, cap at 1) or **Bonferroni** (k·p capped at 1). Outputs are `p_adj_1..k`, `n_tests`, `n_rejected` at the declared alpha, with an appendix carrying the raw and adjusted values and the written definition. Five frozen checks: adjusted â‰¥ raw, bounded in [0,1], matches the declared definition (Holm monotone/Bonferroni formula), independent second route agrees to 1e-12, and order-invariance. Invalid p-values, alpha outside (0,1), an unknown method or a family of fewer than two values are refused at intake; a new `enum` input type covers declared method choices. The honesty layer now says a correction is available instead of only "not applied", and OLS's family-wise notice points to it. Existing methods and their goldens are untouched — no reported p-value changed silently.
**Files:** `src/bp/methods.py` (impl, checks, profile, caveats, template, contract, `enum` validation), `src/bp/orchestrator.py` (honesty wording for the correction method and OLS pointer), `src/bp/server.py` (preset `multicomp`), `tests/test_multicomp.py`, `tests/test_sandbox.py` CASES, `tests/test_session_api.py` input map, `tests/test_honesty.py`, docs (B-060, changelog 0.35, limitations, gap map, REW §10, HOME, README, CONTRIBUTORS).
**Decisions:** B-060.
**Verified:** 10 new tests — published Holm example reproduced exactly (0.03/0.06/0.06/0.02), Bonferroni formula, order-invariance, all frozen checks, alpha-driven rejection counts, four invalid-input refusals, full pipeline delivery with licensed report and honesty block, contract/preset, determinism; sandbox parity and session-input coverage via the shared maps. **457 tests OK.**
**Commit:** `this commit`.
**Open/next:** power/MDE calculation, missing-data mechanism modelling and survey weights are the remaining 9B.3 items and need their own declared conventions (they change what is estimated or the input contract); retrieval still lacks standards/filings/tax source families, automatic failover and drift monitoring; ingestion is the other P0.

---

## 2026-10-21 — Citations: APA 7 and Harvard ratified and implemented (B-059)

**Ask:** "citation styles will be apa and harvard" — close the open citation item.
**Did:** replaced the provisional layout with the two ratified styles. Sources now map the bibliographic metadata the citation needs: Crossref supplies structured family/given names, volume, issue, pages, publisher and type; OpenAlex supplies volume/issue/pages and a type mapping but only display names. APA 7 renders `Family, I. (Year). Title. Journal, volume(issue), pages. https://doi.org/...` with APA's `&`/serial comma; Harvard renders `Family, I. and … (Year) 'Title', Journal, volume(issue), pp. pages. doi: ...`. Books have their own layout; any other source type gets a labelled generic layout instead of pretending it is fully styled. Rendering limits are declared in every citation's notice (plain text has no italics; titles are not case-converted; names are inverted only when the source supplies family/given, with a note when it does not). Unverified references stay prefixed `[unverified user-supplied…]` in both styles. API `cite` now accepts `apa`/`harvard`, the sources endpoint exposes both notices and the reference payload carries the new bibliographic fields; the workbench has a style selector and "Get citation".
**Files:** `src/bp/literature.py` (reference fields, source mappings, APA/Harvard formatters), `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-059, CHANGELOG 0.34, KNOWN_LIMITATIONS, REW manual §9 + Q9, HOME, README, CONTRIBUTORS, WORKLOG).
**Decisions:** B-059 (RESOLVED).
**Verified:** 5 new/updated tests — Crossref and OpenAlex field mapping, exact APA and Harvard strings, book and generic layouts, non-inverted-name note, unverified labelling in both styles, ratified style list, unknown style refused, API style selection; live smoke against Crossref rendered a real eight-author APA and Harvard citation. **447 tests OK.**
**Commit:** `this commit`.
**Open/next:** the 9B.3 statistical upgrades (multiple-comparison correction, power/MDE, missing-data mechanism modelling, survey weights), the remaining retrieval items (standards/filings/tax source families, failover policy, drift monitoring) and ingestion.

---

## 2026-10-21 — Retrieval layer second slice: durable log and provisional citation (B-058)

**Ask:** "GO" after the 9B.3 honesty layer — continue down the gap order at the P0 gatekeeper.
**Did:** two halves of the retrieval layer. **(a) Durable retrieval log**: every retrieval that reaches a source is appended to a local newline-delimited JSON file (source, DOI, supplied and resolved title, status, authors, year, container, UTC retrieval time, response SHA-256), flushed to disk **before** the reference is returned — an unwritable log raises and the retrieval fails closed, so an unaudited citation cannot be produced. `read_log` refuses a corrupt or unknown-format log; `reverify` re-checks a logged entry against the source and reports `hash_match` / `hash_differs` / `unresolvable_now`. **(b) Provisional citation layout**: one declared author-date format (authors as returned, year, title, container, DOI) with an explicit PROVISIONAL notice — no institutional style is claimed, because none has been ratified (REW Q9). Unverified references are formatted only with the `[unverified user-supplied…]` prefix and never as if checked. Wired into the API (`cite` parameter, `GET /api/literature/log`), the workbench (citation line, retrieval-log panel with the new "Get provisional citation" and "Show retrieval log" controls), and `.gitignore` so the runtime log cannot be committed. `BP_RETRIEVAL_LOG` sets the path; empty disables it.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `.gitignore`, `tests/test_literature_log.py`, `tests/test_literature_api.py`, docs (DECISIONS B-058, CHANGELOG 0.33, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, REW manual §9 + Q9/Q10, HOME, README, CONTRIBUTORS).
**Decisions:** B-058.
**Verified:** 17 new tests — log fields and single-line records, unverified retrievals logged honestly with resolved title, no logging without a retrieval, unwritable log fails closed, empty/corrupt/unknown-format log handling, append-only ordering, `reverify` states, citation structure and provisional notice, unverified labelling and mismatch note, placeholders instead of invented authors/years, unknown style refused, determinism; API tests for citation, style validation, log endpoint, limit validation and disabled state; UI strings asserted. **442 tests OK.** Live smoke: real Crossref retrieval logged with a genuine sha256, citation correctly labelled unverified for a deliberately wrong title, `reverify` returned `hash_match`.
**Commit:** `this commit`.
**Open/next:** retrieval-layer remainder — standards/filings/tax source families, source priority and failover, a ratified citation style (Q9) and drift monitoring; then the actual 9B.3 statistical upgrades or the next gap-map item.

---

## 2026-10-21 — 9B.3 honesty layer: disclosure and refusal, no numbers changed (B-057)

**Ask:** the other half of Slice 1 as agreed — the 9B.3 honesty pass on existing statistical outputs.
**Did:** scoped it honestly rather than overclaiming. The layer **discloses** what the system does not do, in every delivery: (a) missing values are excluded listwise and the missing-data mechanism (MCAR/MAR/MNAR) was not established; (b) multiple hypotheses are not corrected, with the family-wise exposure named for OLS coefficients and "one omnibus, no post-hoc comparisons" for ANOVA/Kruskal-Wallis; (c) no power or minimum-detectable-effect is reported, so precision must be read from the interval; (d) survey weights, clustering and repeated measures are unsupported, so every observation is treated as independent. These are both machine-readable (`appendix.honesty`) and plain sentences in the report. Separately, inputs that name an unsupported structure (`weights`, `strata`, `cluster(s)`, `repeated`, `id`, `time`, `pair(s)`) are now refused with a specific reason instead of a generic unknown-input error — a weighted or clustered dataset can no longer be passed in and silently analysed as independent observations. **No number changed.** The actual upgrades (Holm/Bonferroni, power/MDE, missing-data modelling, survey weights) are recorded as still open, so the layer cannot be mistaken for the fix.
**Files:** `src/bp/orchestrator.py` (honesty helper, appendix block, report sentences), `src/bp/methods.py` (unsupported-structure refusal in `validate_inputs`), `tests/test_honesty.py`, docs (DECISIONS B-057, CHANGELOG 0.32, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, REW manual §10, CONTRIBUTORS count).
**Decisions:** B-057.
**Verified:** 10 new tests — appendix block present for every delivered method, descriptive/omnibus/OLS disclosures, NPV and ratio methods report not-applicable rather than blank, determinism and JSON-safety, refusal of weights/clusters/strata with the specific reason, generic unknown-input message preserved; **425 tests OK** (no existing test changed behaviour).
**Commit:** this commit.
**Open/next:** the actual 9B.3 statistical upgrades are still the open row (correction, power, missing-data modelling, weights); the P0 gatekeeper (retrieval + citation: durable retrieval log + citation formatting) is the next build target.

---

## 2026-10-21 — Ratio analysis: the safe half of Slice 1

**Ask:** after the documentation spine, continue with Slice 1 as agreed — the risk-paired first gap closures (honesty upgrades + statement ratios).
**Did:** added the T1 method `ratio_analysis` (B-056). Fifteen declared ratios across liquidity (current, quick, cash), profitability (gross/operating/net margin, return on assets, return on equity), solvency (debt to equity, equity multiplier, interest cover) and efficiency (asset turnover, receivables/inventory/payables days) computed in Decimal from figures the owner supplies. Each ratio reports its definition, inputs and unit; a ratio with a missing figure or a zero denominator is listed in the appendix as not computed **with its reason** and never estimated; a negative denominator is computed and flagged; the balance-sheet identity is checked when assets, liabilities and equity are all supplied; supplied figures are verified to be used exactly as given. No benchmark, industry average, cut-off or good/bad verdict is applied — the manual forbids inventing ratings. The independent second route is exact rational arithmetic (`fractions.Fraction`), and the golden fixture is generated by a separately written Fraction re-implementation, not by the method itself. Added the `ratios` workbench preset; the `days` unit is no longer given a currency in the orchestrator.
**Files:** `src/bp/methods.py` (catalogue, impl, checks, profile, caveats, template, contract), `src/bp/orchestrator.py` (unit exemption), `src/bp/server.py` (preset), `tests/test_ratio.py`, `tests/fixtures/ratio_golden.json`, `tests/test_sandbox.py` `CASES`, `tests/test_session_api.py` input map, README, docs (DECISIONS B-056, CHANGELOG 0.31, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, HOME, CONTRIBUTORS count).
**Decisions:** B-056.
**Verified:** 15 new tests covering golden values, every frozen check, scale invariance, sign behaviour, missing-figure disclosure, zero denominators, negative equity, balance-sheet identity (holds / fails / not applicable), Decimal outputs, determinism, intake blocking, preset reachability and a full pipeline delivery with a licensed report; sandbox parity via the shared `CASES` test; **415 tests OK**.
**Commit:** this commit.
**Open/next:** the other half of Slice 1 — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison correction, power/precision statements, missing-data mechanism declaration, survey-weight/cluster detection), then retrieval + citation (P0 gatekeeper).

---

## 2026-10-21 — Documentation spine: contributors' manual, home map, this worklog

**Ask:** after the gap discussion, the owner asked for a log that traces the work, a manual for any model that will touch or fix the files, and an Obsidian-like map to find things — then "go".
**Did:** added three documents and wired them in: `docs/CONTRIBUTORS.md` (ten non-negotiables, the add-a-method checklist, bug-fix rules, boundary-change rules, the testing contract, environment traps, "where each fact belongs", rejection list, stop-and-ask list), `docs/HOME.md` (task view, module map, capability status, documentation spine, map conventions), and this `docs/WORKLOG.md`. Design choices confirmed with the owner: `CONTRIBUTORS.md` is a repo-level bridge (not part of the authority manual), `HOME.md` uses plain Markdown links rather than Obsidian wikilinks, and the worklog starts now with a backfill pointer rather than reconstructing history.
**Files:** `docs/CONTRIBUTORS.md`, `docs/HOME.md`, `docs/WORKLOG.md`, `README.md`, `docs/CHANGELOG.md`, `docs/DECISIONS.md` (B-055).
**Verified:** docs only; suite unaffected (400 tests OK run in the previous increment). Links checked against the files present in the repo.
**Commit:** this commit.
**Open/next:** Slice 1 of the gap plan — the 9B.3 honesty pass on existing statistical outputs (multiple-comparison, power/precision, missing-data mechanism, weights/clusters) as the risky half, paired with the safe half: financial-statement ratio analysis (T1 arithmetic on the ledger artifacts).

---

## 2026-10-21 — Retrieval audit: response SHA-256 and UTC time per reference

**Ask:** "okay do 3 first" — the cheapest REW increment, Q10 in the living manual: make the hash-audit claim true.
**Did:** `CrossrefSource`/`OpenAlexSource` capture the raw response bytes and record `response_hash` (SHA-256 of those exact bytes) plus `retrieved_at` (UTC, `YYYY-MM-DDTHH:MM:SSZ`) on every resolved retrieval; the fields travel through `POST /api/literature/verify` and show in the workbench References panel. A reference that never reached a source (no DOI, 404, source error) carries neither, fail-closed. Clock is injectable for deterministic tests. Hash is byte-level on purpose: the same semantic record received with different whitespace hashes differently, so the audit pins what was served.
**Files:** `src/bp/literature.py`, `src/bp/server.py`, `web/index.html`, `tests/test_literature.py`, `tests/test_literature_api.py`, docs (REW manual v0.3, DECISIONS B-054, CHANGELOG 0.29, KNOWN_LIMITATIONS, PRODUCT_GAP_MAP, README).
**Decisions:** B-054 (PROVISIONAL); REW manual Q10 marked answered.
**Verified:** five new tests (byte-level pin vs parsed record, injected clock, audit survives a title mismatch, no audit without retrieval, OpenAlex parity) plus API/UI assertions; **400 tests OK**; live smoke against Crossref recorded a real sha256 for DOI `10.1038/nature12373`.
**Commit:** `3189816`.
**Open/next:** no durable retrieval log yet (documented); citation formatting is still `[OPEN]` Q9.

---

## 2026-10-21 — Owner ratifies R11: the REW living manual is the working authority

**Ask:** "yes to R11".
**Did:** ratified R11. The manual (`docs/RESEARCH_EVIDENCE_WORKFLOW.md`) is now the working authority for the Research & Evidence Workflow; B-035 (blocked on the missing Smart Researcher manuals) is closed and B-053 resolved. Manual to v0.2, stating explicitly that R11 ratifies the **document**, not its proposals — R1–R10 (stage list, checkpoints, tiers, taxonomy, etc.) remain unratified.
**Files:** REW manual, `docs/DECISIONS.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Decisions:** B-053 RESOLVED; B-035 SUPERSEDED.
**Verified:** docs only; no code changed.
**Commit:** `7d73b6d`.
**Open/next:** cheap code increment that makes the manual honest — the retrieval audit (Q10).

---

## 2026-10-21 — Living manual for the research workflow (REW), replacing "Stage 7"

**Ask:** the owner believed Stage 7 had already been built; asked "what are these: reviewers, next templates, ledger engine, Stage 7 manuals?" and "create a living stage 7 manual and probably, rename that appropriately".
**Did:** explained the four owner asks (B-005 reviewers, B-028 next templates, B-032 ledger engine, B-035 missing research-pipeline manuals) and corrected the record: what existed was the Stage 7 **blocker** document plus the literature retrieval/verification boundary, not the workflow definition. Created `docs/RESEARCH_EVIDENCE_WORKFLOW.md` as a living manual, renamed the capability **Research & Evidence Workflow (REW)** — "Stage 7" was a build-order label, not a product name. Merged and removed `STAGE7_BLOCKER.md` and `STAGE7_API_DATABASE_PLAN.md`; updated every reference. The manual refuses to pretend it is the lost Smart Researcher manual: every section is tagged `[OWNER]`, `[REPO]`, `[2ND]`, `[PROPOSAL]` (R1–R11) or `[OPEN]` (Q1–Q12), with stages R0–R8 proposed, three mandatory checkpoints, feasibility tiers, study taxonomy, retrieval/citation rules, claim rules, synthetic-data and AI-use policy, an honest inventory, and a ratification register.
**Files:** `docs/RESEARCH_EVIDENCE_WORKFLOW.md` (new), two Stage 7 docs (removed), `README.md`, `docs/DECISIONS.md` (B-035 superseded, B-040 pointer, B-053), `docs/KNOWN_LIMITATIONS.md`, `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`, `src/bp/literature.py` docstring.
**Decisions:** B-053 created; B-035 superseded.
**Verified:** docs only; **395 tests OK**.
**Commit:** `896372e`.
**Open/next:** owner ratification of the register (R11 asked first).

---

## 2026-10-21 — Product gap map

**Ask:** "what else in business have we overlooked?" (after the taxation discussion).
**Did:** wrote `docs/PRODUCT_GAP_MAP.md`: what the catalogue/manual call for versus what is built, ordered P0 gatekeepers (retrieval+citation, ingestion, decision dependencies), P1 statistics completion and finance/valuation, P2 catalogue breadth, plus the non-computational gaps in manual §15B/§16; with tier/verification notes and a recommended order.
**Files:** `docs/PRODUCT_GAP_MAP.md`, `docs/CHANGELOG.md`.
**Verified:** docs only; cross-checked against `DECISIONS.md` and module inventory.
**Commit:** `8c71814`.
**Open/next:** decide which gap to close first (the recommended order was discussed, not started).

---

## 2026-10-21 — Taxation recorded as deferred

**Ask:** "does the jobs you did in creating the pipeline include taxation?" â†’ no; "put it in your memory".
**Did:** recorded **B-052 DEFERRED**: the manual makes tax a non-goal and a jurisdiction-specific area to keep out of the autonomous path or gate behind retrieved sources; resume conditions (VAT/GST, income tax in the accounts, after-tax appraisal, filing) and the evidence lines from the manual are in the decision.
**Files:** `docs/DECISIONS.md`, `docs/CHANGELOG.md`.
**Decisions:** B-052.
**Verified:** read-only analysis against `docs/sources/business_pipeline_v0_3.md` and `src/bp/methods.py`.
**Commit:** `efa9404`.
**Open/next:** product gap map.

---

## Backfill — earlier increments (v0.13 … 0.25)

Earlier work predates this log. The full ordered record is `docs/CHANGELOG.md` (0.13–0.25) and the stage reports; do not duplicate it here. In short: deterministic pipeline + spec/freeze (Stage 0–4), method library and golden fixtures (Stage 5), catalogue registry and T4 templates (Stage 6), model-provider boundary with evaluation scaffold (B-031/B-036/B-038/B-039), literature retrieval boundary (B-040), statistics increments (B-042), forecasting (B-043), and the Stage 8 accounting chain — schedules, two-route cash flow, closing/rollforward, declarative engagement, reconciliation, account-mapping checkpoint, policy changes, statement exports (B-044–B-051). The first commit in this repository is `1ab1d05`; the last pre-worklog increment is `efa9404`.
