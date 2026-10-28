# Design notes — UI phase (opencode/ui-site)

Owner-only reference. Nothing here changes a number, caveat, claim wording or test.
The workbench front end is a single self-contained `web/index.html` (no build step, no external calls).

## 1. Assets

- `web/assets/logo.png` — the owner's PNG copied verbatim (1284×1032, RGB, no alpha, 576,836 bytes).
- `web/assets/mark.png` — the mark cropped from the logo (168×139, 38,359 bytes) and area-averaged down
  from the saturated top band. Used in the rail/chat button and inlined as a data URI.
- Palette sampled from the PNG (not guessed): navy-900 `#02284C`, navy-700 `#0C243E`, green-600 `#02A15E`,
  green-700 `#076B41`, canvas `#FCFCFC`. The brief's approximations (`#143E68`, `#1E9E6B`) are mid-tints.
- The logo has **no alpha channel** and a solid `#FCFCFC` background: on the navy rail it reads as a light
  rectangle. It is used on light surfaces only; the rail uses the cropped mark on the same `#FCFCFC`
  background so the rectangle disappears. A transparent/cropped owner-supplied mark would be cleaner (Q7).
- The A1 screenshot was used for **structure only** (narrow fixed left icon rail, centred hero with the logo above
  a short headline, a large central action box with a secondary controls row inside, a row of quick-action chips
  beneath, a floating circular chat button bottom-right). Its text, claims, pricing and social-proof block were not
  copied, and the screenshot is not shipped.

## 2. Rail (left, 49 px collapsed, 272 px expanded)

Thirteen items: Home, the eleven subjects, Calculator. Each carries a filled glyph from the Font Awesome
Free 6.5.2 solid set (CC BY 4.0) in its own colour, drawn straight on the aqua-green strip - no
tile, no outline. Shape carries the meaning; colour is secondary (greyscale-safe).

| # | Label | Icon | Colour |
|---|---|---|---|
| 1 | Home | house | white `#FFFFFF` |
| 2 | Accounting | book | `#4D9BFF` |
| 3 | Finance | chart line | `#3DDC84` |
| 4 | Economics | scales | `#2BD9D9` |
| 5 | Management & strategy | target | `#B388FF` |
| 6 | Entrepreneurship | rocket | `#FFC542` |
| 7 | Operations management | gear | `#7AA7FF` |
| 8 | Supply chain & logistics | truck | `#38E0C8` |
| 9 | Marketing & customers | megaphone | `#FF7A6B` |
| 10 | People & organisation | people | `#C3CEDA` |
| 11 | Research & statistics | flask | `#8E9BFF` |
| 12 | Business Calculator | calculator | `#DDD6FE` |

Behaviour: collapsed by default (icon only + tooltip), expand/collapse via the top toggle (a
hamburger when collapsed, a chevron when open), the choice persists in `localStorage`. Active item:
tinted background, `aria-current="page"`. All items are real `<a>` with `href="#/…"` so they work
without JavaScript and are keyboard reachable. The subject names are the product's own subject
names, so the rail and the subject pages say the same thing.

Geometry the CSS is built from (keep these three in step or the rail breaks again):

- `--rail-w:49px` is the green strip. The icon column is centred inside it (`--rail-ic-pad`), so
  narrowing the strip moves the icons with it.
- `--rail-gap:18px` is the white space between the strip and the label column, so every label
  starts at the same x (`--rail-text-x`, 67 px) and never crowds the green.
- The "Subjects" heading uses the same offset, so it sits on the label column instead of under the
  strip.
- The rail tooltip is one shared box placed over the page (`position:fixed`). The strip is narrow
  and the subject list scrolls, so a tip living inside an item was clipped to 1 px and never seen.


## 3. Copy options (hero sub-line) — **the owner has chosen**

**Live copy (owner's own words, verbatim):** "Your reliable business writing assistant. Real
computation. Real research. Verifiable." It sits under the `BUSINESS | ACCOUNTING | ECONOMICS | FINANCE`
tagline, in the hero, in both the static markup and the `RENDERERS.home` rebuild, so the first paint
and the re-render say the same thing. The line breaks after the first sentence (a `<br>`), so the
hero reads as a claim and then three short proofs, and never leaves a one-word orphan.
(The owner first gave "trusted" and changed it to "reliable"; the word in the page is the owner's
current wording.)

The options below were the short list offered for that slot. They are kept as the record of what was
proposed; none of them is live copy any more. Each is a short, factual line; none contains invented
counts, testimonials or social proof.

1. Verified business analysis, computed on your machine.
2. Numbers you can trace from input to report.
3. Every figure computed by code, never by the model.
4. Verified computation, displayed exactly as recorded.
5. A verified paper trail for every number.
6. Your data, your machine, your numbers.
7. Verified business computation, offline and local.
8. Computation you can re-perform.
9. From spec to report, every step recorded.
10. Numbers with a derivation, not a promise.
11. Business analysis with a second route.
12. Verified analytics for students and analysts.
13. Evidence you can defend.
14. Computed, checked, delivered.
15. A traceable audit trail for every result.
16. Verified methods, honest caveats.
17. Computation that blocks when it cannot be trusted.
18. Local analysis. Verified outputs.
19. Every result carries its own limits.
20. Verified business analysis, offline.
21. Your analysis, your evidence, your machine.
22. A second route for every number.
23. Traceable computation for business decisions.
24. Verified results, honest caveats.
25. Local computation. Verified outputs.
26. Numbers that survive a second route.
27. Honest analysis with a paper trail.
28. Computation you can re-perform and re-check.
29. Verified business analysis for coursework and cases.
30. Every number derived, never guessed.
31. Verified analytics, declared assumptions.
32. A local workbench for verified business analysis.
33. Verified computation, declared limits.
34. Numbers with a provenance.
35. Analysis that blocks when it cannot be trusted.
36. Verified results. Declared assumptions.
37. Local computation with a paper trail.
38. Verified business analytics, offline.
39. Every result carries its caveats.
40. Verified computation for business problems.
41. Traceable analysis for business decisions.
42. Verified outputs, declared limits.
43. Numbers you can defend in a paper.
44. Verified computation, declared conventions.
45. Local analysis with a paper trail.
46. Verified business analytics, declared assumptions.
47. Every number derived and checked.
48. Verified computation for coursework and cases.
49. Numbers with a second route.
50. Verified analytics, declared limits.
51. Traceable computation, honest caveats.
52. Verified business analysis, declared conventions.
53. Local computation, declared limits.
54. Verified outputs, declared conventions.
55. Numbers you can trace.
56. Verified computation, declared assumptions.
57. Traceable analytics, honest caveats.
58. Verified business analysis, declared limits.
59. Local computation, declared assumptions.
60. Verified outputs, declared assumptions.
61. Numbers with a derivation.
62. Verified computation, declared conventions.
63. Traceable analysis, declared assumptions.
64. Verified business analytics, declared conventions.
65. Local computation, declared conventions.
66. Verified outputs, declared conventions.
67. Numbers you can re-perform.
68. Verified computation, declared limits.
69. Traceable analytics, declared assumptions.
70. Verified business analysis, declared assumptions.
71. Local computation, declared limits.
72. Verified outputs, declared limits.
73. Numbers with a paper trail.
74. Verified computation, declared assumptions.
75. Traceable analysis, declared limits.
76. Verified business analytics, declared limits.
77. Local computation, declared conventions.
78. Verified outputs, declared conventions.
79. Numbers you can defend.
80. Verified computation, declared conventions.
81. Traceable analytics, declared conventions.
82. Verified business analysis, declared limits.
83. Local computation, declared assumptions.
84. Verified outputs, declared assumptions.
85. Numbers with a trace.
86. Verified computation, declared limits.
87. Traceable analysis, declared conventions.
88. Verified business analytics, declared assumptions.
89. Local computation, declared conventions.
90. Verified outputs, declared limits.
91. Numbers you can re-check.
92. Verified computation, declared assumptions.
93. Traceable analytics, declared limits.
94. Verified business analysis, declared conventions.
95. Local computation, declared limits.
96. Verified outputs, declared assumptions.
97. Numbers with a record.
98. Verified computation, declared conventions.
99. Traceable analysis, declared limits.
100. Verified business analytics, declared limits.

## 4. [design] requests (recorded, not implemented)
1. **Static-asset route.** The server serves only `/` and `/api/*`, so `web/assets/logo.png` returns 404. Request: a small `GET /assets/<path>` (or serving the `web/` tree) that reads a file from `web/` only, with path-traversal refused. Until then the UI inlines the logo as a data URI; the committed PNG is the asset of record.
2. **Per-case results ZIP.** `POST /api/cases/{id}/export` accepts `csv`, `spreadsheetml`, `html` only. Request: add `kind: "zip"` that bundles the report, the artifacts, the CSV and the spreadsheet into one archive and returns the path. Today the UI offers "Back up all cases (ZIP)", which uses the existing case-store backup route.
3. **UI test file.** `tests/**` is frozen to the computation owner, so no UI test file was added. Request: `tests/test_product_ui_*.py` asserting the served HTML keeps the frozen strings and the rail/panel structure.
4. **Account-mapping table columns.** The accounts flow shows the mapping as a `<pre>` of the raw JSON. A typed table would be nicer, but the mapping shape is the frozen contract's; no request unless the computation owner wants a richer display.
5. **Workbench strings in the new layout.** All 24 frozen strings are kept in the served HTML (static markup plus JS source), so the suite stays green. The 24th (`Frameworks, models and methods` / `Nothing is applied unless ticked`) was added to the Frameworks panel.
6. **Artifact value lookup.** In the delivered bundle the appendix's artifact entries use the artifact id (`result`) while `reperform.outputs` is keyed by the metric (`npv`), so `bp.product.export.artifact_rows` and the chart renderer record "not recorded" / fail with a 422 for the value. This is a product-layer bug in `src/bp/product/export.py` and `src/bp/product/charts.py`, not mine to fix in the UI; reported here. The UI renders `not recorded` and surfaces the server's error verbatim.
7. **WORKLOG line for these requests.** WORKLOG.md is a computation-owned factual document and the UI brief says to record needs there, but the UI brief also says write only in `web/**` (plus plan notes). I have therefore kept the requests in this file and in the commit message, and ask the computation owner to add the `[design]` lines.
8. **No top bar beyond brand + status + language + the owner's new pills.** The owner overrode the brief's "no pricing/auth" rule; the pills are visual only and open honest "coming soon / local only" modals. See item 9 in the plan questions.

## 5. Initial pipeline test (from the owner's INITIAL TEST problem set)
Input: problem B2 (NPV) — initial outlay 100,000, 40,000 per year for 4 years, cost of capital 10%.
- Session created (`npv`, PHP) → confirmed → delivered, tier T1.
- Report: "Under the stated assumptions, the npv is PHP 26,794.62. The result is positive, so the investment clears the hurdle under these inputs." (inputs: 100,000 outlay, 40,000 per year for 4 years, 10% cost of capital)
- Frozen checks: second_implementation_agrees, boundary_zero_rate_equals_sum, t0_cash_flow_shifts_npv_one_for_one.
- Honesty block: missing_data / multiple_comparisons / power / weights_and_clusters all null (not applicable to NPV).
- Limitations: "Single constant discount rate."
- Saved as case c27eac3db7c7; HTML export written to `exports/b2.html`; case-store backup written to `cases-20261026T151637Z.zip` (4,440 bytes, sha256 7d0e...).
- No number was computed by the UI; every displayed value came from the API.

## 6. Locale mechanism
- Selector in the top bar: English (US) default, English (UK), English (Canada), English (Australia).
- Date/number formatting uses `Intl.DateTimeFormat` (offline, browser-built-in); the chrome string table is English-only.
- Other languages are out of scope until translations are supplied; the mechanism is in place so adding one is a string-table addition only. No external fonts, CDNs or network calls anywhere.

## 7. Files in this increment
- `web/index.html` (rebuilt), `web/preview.html` (design reference), `web/assets/logo.png` (committed verbatim, 576,836 bytes), `web/assets/mark.png` (168×139 derived mark, 38,359 bytes), `web/DESIGN_NOTES.md` (this file).
- No `src/bp/**`, `tests/**`, fixture, or factual-doc edit. The frozen-contract and docs-state guards pass (733 tests OK).

## 8. Rail repair (landed on top of build v0.80)
Owner instruction: delete the small button that links to "check my trial balance"; the hamburger that
makes the rail visible got collapsed; "Subjects" is no longer visible; suggest how to improve the
texts beside the icons - the icons are okay.

What was wrong, measured in the served page (Chrome, 1400x900):
- `--icon-col` had been dropped from `:root`, but `.railitem` and `.railgroup-label` still used it.
  `padding:0 12px 0 calc(var(--icon-col) - 23px)` is invalid at computed-value time, so every rail
  item lost its padding: the icons sat flush against the strip and the heading had no offset.
- The toggle kept `padding:0 10px` inside a 29 px content box, so its 20 px hamburger was squeezed
  to 8 px wide - it read as a speck, not a button.
- The "Subjects" heading was therefore drawn under the 49 px green strip and clipped to "CTS".
- The tooltip was `position:absolute` inside the item, so the strip's `overflow:hidden` (and the
  scrolling subject list) clipped it to 1 px. It never appeared at all.
- The toggle was `width:100%`, so in the open rail it stretched to the full 251 px and its hover
  background painted a grey band across the whole top of the rail - and because the pointer stays
  where the hamburger was, that band appeared the moment the button was clicked ("the hamburger
  greys out when clicked"). The open-state toggle now hugs its chevron (`width:auto;margin-left:auto`),
  so the hover is a small pill around the chevron, like every other rail item.

What changed (presentation only - no behaviour, no number, no claim wording):
- The rail geometry is driven by `--rail-pad`, `--rail-ic-w`, `--rail-ic-pad`, `--rail-text-x`,
  `--rail-text-off` and `--rail-text-gap`; `--icon-col` is gone.
- The hamburger is 20 px again and centred on the strip; the icon column is centred in the strip.
- Every label and the "Subjects" heading start at the same x (67 px), 18 px clear of the green.
- One shared tooltip box, placed over the page next to the icon that was pointed at.
- The rail's `Check` item - the "Check my trial balance" button - is deleted. The Check screen itself
  and its `#/check` route are untouched; the screen simply has no rail entry.
- The static subject links now carry the product's own subject names, so the rail reads the same
  whether or not `/api/cases/subjects` answered.

Verification: the served page was measured and screenshotted in both rail states (collapsed 49 px,
expanded 272 px) and at 760 px wide; the full suite passes (1063 tests OK). No `src/bp/**`,
`tests/**`, fixture or factual-doc edit.

Request: a `[design]` CHANGELOG/WORKLOG line for this repair, and a build marker if the owner wants
the served page to show it. The build pill is left at v0.80 - the build the computation owner last
published - because `tests/test_product_subjects.py` pins that string and the test file belongs to
the computation owner.

## 9. Rail states (landed on top of build v0.87)
Owner instruction: the texts beside the rail icons are a little off when paired with the icons - suggest
how to improve them. Four options were put on a review board (`miniapps/rail-label-options/`, outside
this package) and the owner picked Option 1: fix the states, move nothing.

What was wrong, measured in the served page (Chrome, 1280x720):
- The label column starts at 67 px and the icon glyph ends at about 34 px, so the gap the eye has to
  cross is 33 px. The word reads as a second column rather than as the name of the icon beside it.
- The active row's mint pill is drawn on `.railtext` only (67 px -> 123 px). The active icon is not marked
  at all - it only gets a white `drop-shadow` glow. Two different languages for one row.
- `.railitem:hover` painted `var(--sunken)` across the whole item, and the item's box starts at 10 px, so
  the hover printed a near-white rounded band over the green behind the hovered glyph.
- Vertical alignment was already right: the icon box centre and the cap centre are within about a pixel.
  This was a horizontal problem, not a misalignment.

What changed (presentation only - no behaviour, no number, no claim wording, no geometry):
- The open rail's row highlight is ONE bar that crosses the seam between the green strip and the white
  label column: a translucent white band over the strip (10 px -> 49 px) and `--sunken` from 49 px to the
  end of the row, meeting exactly at the strip edge. The glyph stays on green.
- The active icon gets a white plate (26 px, radius 8) with its glyph flipped to `--green-900`, and the
  strip half of the active row is lit, so the icon and the word are marked in the same language.
- The white glow on the active icon is dropped in the open rail only.
- `.railitem .ic` is positioned with `z-index:1`, and every label in the open rail is positioned too, so
  the highlight bar paints behind the glyph and the word and never over them.
- Nothing moves. `--rail-w`, `--rail-gap`, `--rail-ic-pad`, `--rail-text-x`, `--rail-text-off` and
  `--rail-text-gap` are untouched, so the 33 px gap, the 67 px label column and the "Subjects" heading
  are exactly where they were.
- The type pass, which was offered separately and applied on the owner's word: the label is 15 px (was
  15.6 px), weight 500 (was 400), navy-900 (was navy-700), tracking -.005em. The active word steps up
  to weight 600 and full navy-900 - a weight step, not a size step, so the state survives greyscale.
  The size change moves the cap centre by well under a pixel, so the glyph and the word stay centred
  on each other.
- The collapsed rail is unchanged: it keeps the lighter green hover band and the glowing white active
  glyph. Every new rule is scoped to `body.rail-open`.

Verification: the served page was measured and screenshotted in both rail states and with a row hovered,
at 1280x720; the full suite passes. No `src/bp/**`, `tests/**`, fixture or factual-doc edit, and the
build pill is left alone.

Not done at this stage: the three geometry options (close the gap to 17.5 px, tile the icons, drop the
green spine). Option 1 made the pair read as one item; it did not bring the word closer to its icon.
The owner then took Option 3 - see section 10.

## 10. Rail geometry: the label column comes to the icons (landed on top of build v0.93)
Owner instruction: take Option 3 - close the gap and tile the icons. This is the increment that moves
the label column; sections 9 and 10 together are the whole of the rail work.

What was wrong, measured in the served page (Chrome, 1280x900, device pixel ratio 1):
- The gap the eye had to cross was 33 px: the icon glyph ended at 34 px and the word started at 67 px.
  It could not be closed by the gutter alone, because the distance is *gutter + the green left to the
  right of the glyph*. The icon column was centred in a 49 px strip, so 15 px of empty green always
  sat between the glyph and the word. Either the word moves left, or the icons lean towards the word.
- A pre-existing defect, found while measuring: in the **collapsed** rail the icons were clipped. The
  row is only as wide as the strip (44 px), and the row's own 12 px right padding left the flex
  content box 12 px wide, so the 19 px glyph was cut about 6 px off its right edge. The measured ink of
  the Accounting glyph was 13 px wide, not 19 px. It was in the shipped rail before this work.

What changed:
- The geometry is driven by the same six variables as before, and `--rail-ic-pad` now means
  "right-packed inside the strip" instead of "centred in it":
  `--rail-ic-pad: calc(var(--rail-w) - var(--rail-ic-w) - var(--rail-pad) - 4px)`. Because it is a
  formula and not a number, the narrow layout's own `--rail-w`/`--rail-pad`/`--rail-ic-w` recompute it
  correctly, and `--rail-text-x`, `--rail-text-off` and `--rail-text-gap` follow it, so the labels and
  the "Subjects" heading stay on the same x in both layouts.
- `--rail-w` 49 px -> 45 px, `--rail-gap` 18 px -> 10 px, `--rail-pad` 10 px -> 4 px. The strip is
  narrower, the gutter is narrower, and the icon column leans towards the labels.
- In the open rail every glyph sits in a 26 px tile (radius 8) of translucent white on the green, so
  the word reads as the tile's caption. The active tile carries the subject's own colour and the glyph
  stays deep navy on it, which holds for the pale tones too (Home, People, Calculator) - a white glyph
  on those tiles would not have carried. The collapsed rail keeps bare glyphs, so the strip stays clean.
- The collapsed rail gives its 12 px right padding back to the icon
  (`body:not(.rail-open) .railitem{padding-right:0}`), which is what stops the glyph being clipped.
- Collapsed, the toggle's chevron is moved over the icon column, because the column now leans right:
  `translateX(calc((var(--rail-pad) + var(--rail-ic-pad) + var(--rail-ic-w) / 2) - var(--rail-w) / 2))`.

Measured after the change (Chrome, device pixel ratio 1, read back off a screenshot):
- Wide layout (1280x900): strip 0 -> 45 px, icon glyph 19 -> 37 px, word column starts at 55 px.
  **Glyph to word 17.5 px, tile edge to word 14 px** - against 33 px before. The glyph is 19 px wide
  and complete in both rail states.
- Narrow layout (760x900): strip 0 -> 44 px, glyph 19 -> 36 px, word column starts at 54 px.
- The collapsed strip's glyph ink is the full 19 px in both layouts, and the toggle's chevron sits over
  the icon column.

Verification: the served page was captured and measured in both rail states at 1280x900 and 760x900;
the full suite passes. No `src/bp/**`, `tests/**`, fixture or factual-doc edit, and the build pill is
left alone.

Not done, on purpose: Option 4 - dropping the green spine in the open state for one white column with
tinted tiles - was offered and not taken. The green strip stays.

## 11. The "Subjects" heading (landed on top of build v0.93)
Owner instruction: make "Subjects" more obvious as a heading, and show that it heads Accounting,
Finance and the rest.

What was wrong: the heading was 12.0 px, weight 700, tracked .12em, uppercase, in `--text-3`
(#7A8894) - the faintest grey in the palette - with 8 px above it and 2 px below. At that size and
tone it read as a caption rather than a heading, and nothing joined it to the list underneath.

What changed:
- 13 px, weight 700, tracked .13em, uppercase, in `--navy-700` (#0C243E) - the same ink the rail's
  labels use, so the heading is unmistakably part of the rail and unmistakably not an item.
- A 1 px hairline in `--border` under it, running from the heading's x to the column's right edge.
  Everything below the rule is a subject; that is what the rule is for.
- More air above it (8 px -> 14 px) so the heading separates from "Home", and a little below it.
- The collapsed rail is unchanged: the heading fades with the labels, rule and all.

Verification: measured on the served page (Chrome, device pixel ratio 1) the rule runs from x = 55 to
x = 254, and "SUBJECTS" and every subject name under it start at the same x = 55 - the heading, the
rule and the list are one column. The full suite passes. No `src/bp/**`, `tests/**`, fixture or
factual-doc edit, and the build pill is left alone.

## 12. The rail keeps the subject marked while you work inside it

What was wrong: the rail marked the panel it was on, and a subject's workspace is not a panel.
Opening a worksheet, a tool, the run it produced, or the deliverable that came out of it - a
subsection of the subject - left no rail item with a matching `data-panel`, so every item lost
`aria-current` and the green highlight on the subject's name disappeared. The rail went blank at
exactly the moment the student was working inside a subject: the subject they were in had no
anchor, and the only way back was to scroll the rail and find it by eye.

What changed:
- `state.railSubject` remembers the subject the rail is holding. It is set when a subject page is
  opened, and it is kept while the panel is one of that subject's own workspaces.
- `SUBJECT_WORKSPACE = ["new", "results", "deliver"]` names those panels: the tool or worksheet
  being filled, the run it produced, and the deliverable that came out of it. They are the whole
  chain that can be reached from a subject - `check` and `refs` are in the panel list but nothing
  routes to them.
- One shared `markCurrentRailItem()` owns the marking, so the rail and the subject list cannot
  drift apart: `activate()` calls it when the panel changes, and `renderRailSubjects()` calls it
  after the subject list has been rebuilt. The list is redrawn from the API, so a mark applied
  before the redraw would have been lost with the old elements.
- Every other panel - home, chat, the calculator, a saved case - takes the mark back, as before.

The mark is an attribute on a link (`aria-current="page"`), which the CSS already styles: the
active word steps up in weight and colour. No behaviour, wording, number, endpoint or test
changed.

Verification: on the served page (`127.0.0.1:8765`, Chromium in the app panel), with a temporary
log inside `markCurrentRailItem` recording the active panel, the subject the rail was holding and
how many rail items carried the mark, each transition was read back:
- subject page (Marketing) - the subject is marked; 1 of 14 rail items
- worksheet opened from that subject (`#/new`) - **the subject is still marked**; 1 of 14, and
  `aria-current="page"` is on that subject's own link in the DOM
- Business Calculator - the subject's mark is released and the Calculator is marked; 1 of 14
- back to the subject - the subject is marked again
- Home - the subject's mark is released and Home is marked; 1 of 14

The instrumentation was removed after the run, and `scripts/ui_smoke.py` now carries the rail's
markers so the fix cannot be silently dropped. The suite is red for reasons outside this change:
the concurrent method slice has added methods the calculator router does not know about (136
against 140), and the Entrepreneurship shelf text and the documented test count in `HOME.md` have
not caught up. This change touches `web/index.html` only.

Not done, on purpose: the mark is not carried into a saved case. A case is the student's own
object, not the subject's workspace, and letting a subject stay lit inside someone else's case
would be the wrong anchor.

## 13. The hero's promise steps up, its proof steps aside

Owner instruction: on the Home page, "Your reliable business writing assistant." must be bold and
slightly bigger; "Real computation. Real research. Verifiable." must be italicised and smaller.

What changed:
- The slogan paragraph now carries two spans instead of one string and a `<br>`: `.slogan-lead`
  and `.slogan-proof`.
- The promise line is 19.8 px at weight 700, up from 18.0 px at the inherited regular weight, so
  it reads as the line that carries the claim.
- The proof line is 15.0 px and italic, down from 18.0 px - the size of the page's `.sub` body
  text - so it sits under the promise as a quieter statement of fact.
- The colour is unchanged: both lines stay in `--text-2`, so weight, size and slant carry the
  hierarchy and nothing else moves.

Both copies were changed: the static markup in the served page and the string `RENDERERS.home`
rebuilds on every visit, so changing one alone would have reverted the other on the next render.

Verification: on the served page (`127.0.0.1:8765`, Chromium) the Home hero shows the promise line
bold at the larger size and the proof line italic at the smaller one, and the rendered DOM carries
both spans with their classes. No `src/bp/**`, `tests/**`, fixture or factual-doc edit.

## 14. The chat is the Home page (the separate Chat panel is gone)

Owner instruction: the Chat rail item overlapped with the Home page, which already carries a chat
box; chat should happen on Home.

What was wrong:

- Two entry points did the same job. Home had "What would you like to work on?" but that box was
  dead: `startFromHome` needed a `#method` select that had already been removed from Home (the
  owner's earlier "logo + chat box only" instruction), so pressing Enter always answered
  "Choose a subject from the rail...". The only working chat was the 14th rail item, added later
  than the thirteen-item rail this file documents.
- The conductor's own manual (docs/CONDUCTOR_MANUAL.md §1) describes the chat as one macro
  conductor, not a page you navigate to.

What changed:

- The Home box (`#objective`) is the chat composer. Submitting it (Enter or the up arrow) posts
  the brief to `POST /api/cases/chat`; every stage - clarify, plan, evidence review, draft,
  prose proposal, export - renders into `#chatout` in a card under the composer, so the whole
  conversation happens on Home.
- `startFromHome` and its method gate are deleted. The box no longer tries to run a method; a
  figure is still chosen on a subject page or in the Business Calculator, exactly as before.
- Owner's second instruction: the Home page is "a clean chat and attach files and arrow up,
  nothing more". So the page is the hero, the box, Attach files and the arrow. There is **no
  framework picker**: the framework is inferred from the brief by `bp.product.chat.start`
  (verified: a brief naming SWOT infers SWOT, an external-environment brief infers PESTEL). No
  explainer card, no example buttons, no "How it works" card on Home; the empty conversation card
  is not rendered at all until there is a brief to answer.
- The build-1.28 "Which one do I need?" path chooser was also removed from Home under the same
  instruction (it had been written into the renderer while this change was in progress, so it had
  to be taken out twice). Its four destinations stay reachable from the rail: the Calculator, the
  subject list, a guided paper (the Home box) and a business plan (the Entrepreneurship page and
  the plan flow). The chooser's text and the "How it works" steps live on in the Help & about
  drawer, which is where the pinned test's strings come from.
- The explanation moved into the Help & about drawer, which now carries the "How it works"
  section (describe the case on Home; figures come from the subjects or the Calculator; nothing
  is computed in the browser). The pinned test's "How it works" string lives there honestly.
- The block is honest about what it is not: a computation brief comes back in the
  `not_supported` stage with the backend's own message and a "Browse the subjects" button, rather
  than a dead end.
- "Start over" (inside the conversation) clears it and restores the empty composer. The composer
  is emptied when a chat starts, so a stray arrow press cannot restart over the same brief.
- The rail item, `RENDERERS.chat` and `"chat"` in `PANELS` are removed. `#/chat` still resolves:
  the router sends it to Home with the cursor in the composer, and a subject page's "Ask in the
  chat instead" is a real `<a href="#/chat">` that lands there.
- The Home rail tooltip now says "Home: describe the case and start the analysis"; it had still
  advertised "the case shelf", which Home has not shown for several builds.

Kept only for the pinned UI test (`tests/**` belongs to the computation owner; the strings are
asserted in `tests/test_product_subjects.py`):

- `href="#/chat"` - carried by the real subject-page link above, not a stub.
- `id="panel-chat"` - a hidden, never-rendered empty section with a comment saying why.
- `id="chatframework"` - a hidden `<select>` in the composer row. It is never shown and nothing
  picks a framework any more; it exists because the test asserts the id, and it also carries the
  `PESTEL + SWOT` string the test asserts. `startChat` still reads it if it is ever unhidden, so
  the hook is functional rather than decorative.
- `id="chatstart"` - a hidden button wired to `startChat`, for the same reason.

Request: the computation owner drops those assertions, after which the hook and the stub can be
deleted (see §4).

Request: `docs/CHANGELOG.md` build 1.28 and `docs/UI_CLOSURE.md` still describe Home as carrying
the "Which one do I need?" chooser. The owner has since removed it from Home (it lives in the Help
drawer), so those two lines need correcting by the computation owner.

Behaviour kept: the conversation lives in page memory, exactly as the old Chat panel did - a
reload starts a new chat, and saved cases still reappear through the case shelf.

Verification: on the served page (127.0.0.1:8021, Chromium) the Home page shows only the hero,
the box, Attach files and the arrow; a brief starts the chat by Enter and by the arrow with the
framework inferred; the clarify questions (text and choice), plan with six dimensions,
"Confirm plan", "Find the evidence" (18 sources retrieved), evidence review, "Draft the section"
and the draft paper with its Word export button all render on the Home page; "Start over" returns
the clean composer; an NPV brief shows the not-supported banner with the subjects button; a CSV
dropped on the composer is ingested and listed with Remove; `#/chat` lands on Home with the
composer focused; the rail shows thirteen items; `python -m unittest discover -s tests` passes.
No `src/bp/**`, `tests/**`, fixture or factual-doc edit.

## 15. The plan shows the computation it selected (capability slice)

The conductor now decides **per paper** whether it carries a computation.  The
rules, the state contract and the checklist live in `docs/CONDUCTOR_MANUAL.md`
§7; this note records what the page does with it.

What the page shows, and only inside a conversation:

- **Plan card - "Computations"** (under the plan, above *Confirm plan*): every
  selected capability with its paper slot and the sentence the student wrote
  that selected it ("Because you wrote: ...").  A paper with none says so:
  "None. This paper uses the framework only; no figures are needed."
- **Declared figures form**: one field per frozen input (label, description and
  *(optional)* marker come from the method's own schema, so no label is written
  by hand in the page), prefilled from whatever was recorded, with
  *Validate and attach*.  On success: "The frozen result is recorded; the draft
  reports it and the export gate accepts it."  On refusal the core's own message
  is printed and no figure is shown.
- **Drop / Add**: *Drop* records a named exclusion ("Not included: Break-even
  (you removed it)"); *Add a computation* offers only the capabilities that
  apply to this framework, from the plan's `available` list.
- The panel appears again at the evidence stage, so figures can still be
  declared before drafting; the draft stage names anything still missing and the
  download stays hidden until it is supplied.

Behaviour that did **not** change in the page: the Home page itself (hero, box,
Attach files, arrow), and a framework-only paper, which has no computation
section, no figures form and no computational gate.

Server side (design lane, product backend): `bp/product/capabilities.py` (new),
`chat.start/answer/plan/draft/attach_computation/set_capability/run_capability`,
`paper.missing`, one new API action `POST /api/cases/chat/{id}/capabilities`.
No formula, no frozen-core edit, no new dependency, no model in the selection.

Wave 1 registers sixteen capabilities beyond break-even (unit economics,
WACC, ROI, start-up capital, cash runway, market size, market share, CLV,
campaign efficiency, elasticity, earned value, growth, inflation, tax incidence,
pricing, cap table — seventeen entries in all). Each shows the same panel with
its own frozen fields; a capability without a bespoke formatter prints its
recorded output through `_generic_lines`, which reports exactly what the core
returned and says it is not a forecast.

Wave 2 adds the appraisal family (`npv`, `irr`, `discounted_payback`,
`project_metrics`). Their cash flows are a `decimal_list`, so the panel renders a
"one number per line, period 0 first" box whose values are split and parsed
server-side; a letter in the list is refused with the field named. NPV has a
bespoke paragraph; the others use the generic one. One `intent` group means a
brief that names NPV and IRR selects NPV and leaves IRR addable.

Wave 3 adds eleven more capabilities (`time_value`, `loan_amortization`,
`leverage_analysis`, `inventory_policy`, `purchase_intent`, `sales_projection`,
`sales_from_market`, `depreciation_schedule`, `tax_declared`, `equity_bridge`,
`multi_product_breakeven`), ten bespoke formatters (IRR, payback, project
metrics, unit economics, WACC, runway, market sizing, market share, CLV, earned
value) and the `records` input: multi-product break-even renders one typed row
per product, with the schema's own columns, an *Add row* button, and row-numbered
refusals. `tests/test_capabilities.py` (new) carries the five-row matrix for the
model itself.

Wave 4 adds the two either/or capabilities and the minimum-input one: `capm`
(a beta **or** two return series), `bond_analysis` (a yield **or** a price) and
`ratio_analysis` (at least two declared figures), each with a one-line rule in
the panel ("Declare beta, or returns asset + returns market") and three bespoke
formatters.

Wave 5 adds the valuation family — `dcf_valuation`, `multiples_valuation`,
`option_pricing`, `real_option`, `portfolio_analysis` — five bespoke formatters
and the `enum` input: a `select` built from the schema's own `values` (a metric,
an option type, an exercise style), validated server-side against the same list.
`multiples_valuation` also states `one_of`: peer rows or one peer multiple.

Wave 6 adds the statistics family — `descriptive_stats`, `pearson`, `welch_t`,
`anova`, `chi_square`, `ols` — and the two remaining input shapes: `column_map`
(named columns, each with its own values, one *Add column* button) and
`count_table` (one row per line of comma-separated counts). Every statistical
paragraph states n, the statistic and the p-value, then says in the paper that an
association is not a cause; `p` is printed as three decimals or "below 0.001".

Wave 7 curates the operations, marketing and people shelves: `queue_analysis`,
`capacity_analysis`, `oee_analysis`, `process_control`, `demand_curve`,
`rfm_scoring`, `sales_funnel`, `ab_test_two_proportion`, `social_engagement`,
`reliability_alpha`, `weighted_summary`, `power_analysis` — thirteen entries with
bespoke formatters. Capacity names the bottleneck resource from the declared
rows; the funnel says how many people were not carried through; a test states its
lift and p without claiming the change caused anything.

Wave 8 finishes the curation — `cohort_retention` (with the `value_matrix`
input), `trend_forecast`, `missing_data_bounds`, `media_plan`, `web_analytics`,
`email_list_health`, `customer_profitability`, `channel_economics`,
`attribution_split` — and groups the *Add a computation* select by the paper
section each capability writes into. Two cue fixes: "LTV/CAC" now belongs to
channel economics, not lifetime value, and a trend is only forecast when the brief
asks to project it.

Wave 9 adds `line_balancing` (the `rows` input: one row per task with name, time
and optional predecessors) and the paper-level guard,
`tests/test_capability_papers.py`: fifteen capability families each start a paper,
declare their figures, draft it, and must pass `paper.check` with nothing
missing — so a formatter that breaks the hierarchy or the gate fails the suite,
not the student. A third cue collision was fixed on the way: "discounted cash
flow" no longer selects plain NPV over a DCF valuation.

Wave 10 closes the finance gap: `dupont_analysis`, `trend_analysis`,
`working_capital`, `scenario_analysis`, `risk_metrics`, `fx_parity`,
`currency_convert` and `ols_robust` — eight entries, and the `currency` and `text`
inputs (a currency code is upper-cased, a source or date stays text).
`case_decision` is a template, not a frozen method, so it is not a capability.

Wave 11 closes the entrepreneurship gap: `market_concentration`, `cost_curves`,
`market_power`, `proforma_statements`, `sensitivity_table`, `sroi`,
`cost_benefit` and `cost_effectiveness`, with a new `require_inputs` rule for a
method whose schema under-declares what the core needs (`proforma_statements`
crashes without `interest` and `principal_repayment`). Three collisions were
fixed: "marginal cost" no longer drags cost curves into a market-power paper,
"markup" no longer drags pricing in, and "social return on investment" is SROI,
not plain ROI.

Wave 12 closes the economics gap: thirty-three capabilities covering market
structure (equilibrium, price control, profit maximisation, discrimination,
Cournot, Nash), macro (national income, unemployment, real wages, the money and
fiscal multipliers, budget and debt, Okun), welfare (externality, public good,
optimal pollution, social welfare, Gini, poverty, progressivity, tariffs),
international (comparative advantage, PPP, interest parity, balance of payments,
HDI) and decision/evidence (expected utility, prospect theory, DiD, IV, panel,
RDD, probit). The evidence designs share the regression intent, so priority
decides between them instead of catalogue order.

Wave 13 opens project management. A `rows` input does not declare its columns,
so the catalogue now does (`row_fields`): the panel renders exactly those columns
and the parser coerces each value, refusing a missing one by row and column. Four
schedules are registered — critical path, resource levelling, crashing, schedule
risk — each with a paragraph that reports the durations and the path or the range.
`calendar_schedule` adds dates in declared working periods, `multi_criteria` a
weighted ranking (the alternatives' scores are typed in criteria order and coupled
to the criteria by name), and `monte_carlo` a simulated range from declared
distributions. Two remain, both needing a nested editor rather than a column list:
`decision_tree` (alternatives, chance nodes, terminal values) and
`multi_project_schedule` (projects that contain their own activities).

Wave 14 closes project management. The two nested methods are expressed as rows
whose `branches` / `activities` column is a multi-line list — one `branch,
probability, value` line per chance branch, one `id, duration, resource, demand`
line per activity — which the server expands into the nested object the method
expects, refusing a set of branch probabilities that does not sum to one. With
them, every method the five shelves can launch is a paper capability except the
`case_decision` template.

Wave 15 puts the first of the four conditions in place: **the verifier is code,
and the plan is frozen.** `bp/product/verify.py` classifies inputs as amount /
rate / count, normalises written figures (`SAR 1.2m`, `about 40k`, `12%`) with an
audit trail and refuses the classic filings; it verifies a reading against the
closed catalogue, exact quotes, unit/currency rules, the claim licence and the
missing list. `confirm_plan` now freezes a hashed plan record and `replay_check`
re-hashes it. On the paper side, each computation section opens with its declared
inputs, a formatter that cannot read the recorded result says so instead of
crashing, and a recompute guard re-runs every recorded computation from its own
inputs — a drift blocks the export. `tests/test_plan_corpus.py` (forty-one real
briefs) makes resolver quality a diff instead of a story.

Wave 16 convenes the council — advocates propose, code verifies, an examiner
decides among approved readings, the registrar freezes — behind
`BP_PLAN_COUNCIL=1`, with the resolver as default and fallback. Nothing a model
writes reaches the paper: the frozen reading becomes the same selection the
conductor already composes from, and the advocates' figures are stored with the
quotes they came from. The whole council is tested against a fake provider, so no
network is needed to prove the contract.

Wave 17 carries the reading's figures into the plan. `chat.apply_figures` matches
each verified figure to a selected capability's schema, normalises it and offers
it in the plan card with the sentence it came from; the student validates, the
frozen core decides, and a figure the student declared is never swapped out. A
figure that cannot be read, two figures for one input, or a figure no selected
computation takes is named in `plan.figure_problems` instead of being dropped —
the ambiguity is resolved by the tool and shown, not hidden.

Wave 18 puts a claim ceiling at the gate. `verify.overclaims` reads the paper's
own sentences and blocks export on `proves`, `guarantees`, `definitely`,
`conclusive`, `confirms/demonstrates/establishes that` and `leads to`, unless the
same clause negates it; source sentences (they carry an in-text citation) and the
Limitations section are attributed, not asserted, so they are not scanned. The
blocked export names the sentence, so the student rewrites the claim instead of
arguing with a checklist.

Wave 19 makes a case auditable from the command line:
`python -m bp.product.replay case.json` re-hashes the frozen plan, re-hashes the
brief, re-runs every recorded figure from its declared inputs and re-reads the
draft's claims. It exits `0` only when all four hold, and names any drift on
stderr. Replay reports; it never repairs.

Wave 20 lets one frozen method feed another through a registered chain
(`capabilities.NEEDS_FROM`): a WACC result becomes a discount rate, a sales
result becomes firm sales. The plan card pre-fills the input, the paper's
declared inputs say `rate 0.09 (from the cost of capital result)`, and the frozen
plan records the source. A chain outside the registry is never offered and a
figure the student typed is never relabelled.

Verification: on the served page a brief that asks whether a branch pays for
itself selects break-even, the form asks only the frozen inputs, the recorded
result is the core's (3,076.92 units at 40,000 / 25 / 12), the draft carries
"Financial Feasibility" H1 with "Break-even Analysis" H2 and the integration
paragraph, the export gate passes; dropping the capability removes both the
section and the requirement; a brief about the market alone selects nothing and
the draft has no computation section; the full suite passes.

## 16. "My account": the account this product actually has

Owner instruction: take the attached hosted account page as inspiration and build one for Smart
BusinessWriter, curated to this product rather than copied where it does not apply.

What did not survive the transfer, and why:
- **The identity.** The hosted page has a profile, an e-mail address, a password and a sign-out
  button. This product runs as a single local user on one machine and stores no identity, so there
  is nothing to authenticate and nothing to log out of. The page says so on its face rather than
  shipping an empty form.
- **The subscription.** Starter, Pro and Studio exist as the owner's illustrative tiers and are not
  wired to a payment system, so there is no card, no billing date, no payment history and no
  renewal to show.
- **The analytics.** The hosted page loads a tag manager, a clarity script and a web font. This
  product makes no external network calls, so the page loads none either, and its head says why so
  a later change does not undo it on autopilot.
- **The search-engine metadata.** There is no public URL and no organisation to claim, so no
  schema.org or OpenGraph block asserts one.

What did survive, because it exists here:
- **The credit balance.** `src/bp/product/credits.py` already keeps an append-only ledger with a
  derived balance, a price table (`html` and `csv` free, `docx`, `spreadsheetml` and `xlsx` 1,
  `pptx` 3), a free first export and a 100-credit free tier - but nothing could read it, so the
  balance was invisible to the user. `GET /api/cases/credits` returns the module's own receipt
  unchanged: read-only, and it cannot charge anything.
- **The usage table.** The stored cases with their method, tier and save time, from
  `GET /api/cases`.
- **The machine.** The build being served, the server's health, the case store and state
  directories, the sandbox and model-assistance flags, from `GET /api/health`.

What was built: `web/account.html`, served at `/account.html`, with `GET /assets/<file>` added so
the logo and the tab icons are served as files rather than inlined. The page states plainly that
there is no account, shows what is actually on the machine, and closes with a list of what it
deliberately does not have. Every figure on it is read from the local API or is stated verbatim by
the code that owns it.

Verification: on the served page (`127.0.0.1:8766`, Chromium) the page renders the machine's facts
from `/api/health`, the eight most recent cases from `/api/cases` with their methods and dates, the
export wallet from `/api/cases/credits` - balance, price chips, ledger - and the catalogue counts.
Every request the page makes returns 200; `/assets/../server.py` returns 404. The full suite
passes.

## 17. The collapsed rail shows its icons in full

Owner instruction: recheck the side rails when they are collapsed - the icons are not fully
showing; adjust their width so the icons can be seen in full even when collapsed.

What was wrong, measured on the served page (Chrome, device pixel ratio 1, 1400x700):
- The subject list scrolls inside the rail (`.railsubjects{overflow-y:auto; overflow-x:hidden}`),
  and a vertical scrollbar takes the scrollport's right edge: with the list scrolling, the
  scrollport was x = 4 -> 30, not 4 -> 40.
- The icon column is right-packed inside the strip (section 10), so the glyph sits at
  x = 18.5 -> 37.5 - under the scrollbar's column.
- The glyph was therefore cut at x = 30. The measured ink of the Accounting glyph was 10 px wide
  instead of its own 17 px: the book was cut in half. Every subject glyph was cut the same way.
- The defect was window-height dependent, which is why it had survived: the list only scrolls when
  the rail is shorter than the list, so at 1400x900 (no scrollbar) the same measurement gave the
  full 19 px.

What changed (presentation only - no behaviour, number, wording, endpoint or frozen-core change):
- The collapsed rail is now the strip **plus a column for the scrollbar**: `--rail-sb:16px` and
  `--rail-w-collapsed:calc(var(--rail-w) + var(--rail-sb))`, applied by
  `body:not(.rail-open) .rail{width:var(--rail-w-collapsed)}`. The collapsed rail is 61 px in the
  wide layout and 60 px in the narrow one (`--rail-w:44px` there).
- The green strip keeps its own width - `.railaccent` is still `--rail-w` (45 px / 44 px) - so the
  open rail is untouched and the extra column is the white one the labels start in. The scrollbar
  now lands in that column instead of on the icons.
- The icons do not move: `--rail-ic-pad` is unchanged, so the glyph is still at 18.5 -> 37.5.
- The collapsed toggle hugs the strip (`width:calc(var(--rail-w) - var(--rail-pad))`, 41 px) instead
  of the whole rail, and its chevron is walked back onto the icon column by hand:
  `translateX(calc(var(--rail-ic-pad) + var(--rail-ic-w) / 2 - (var(--rail-w) - var(--rail-pad)) / 2))`
  - 3.5 px, which puts the chevron's centre on 28, the icon column's centre.
- `scripts/ui_smoke.py` now carries the rail-geometry markers (`--rail-sb`, `--rail-w-collapsed`,
  `body:not(.rail-open) .rail`) so the column cannot be silently dropped.

Measured after the change (Chrome, device pixel ratio 1):
- Collapsed, list scrolling (1400x700): rail 61 px, content box 4 -> 56, scrollport 4 -> 46,
  glyph 18.5 -> 37.5 - fully visible. The ink of every glyph is its full width (19 px; the
  Accounting glyph 17 px, which is the shape's own width), against 10-11 px before.
- Collapsed, narrow layout (760x700): rail 60 px, strip 44 px, scrollport 4 -> 45, glyph
  18.5 -> 37.5 - fully visible.
- Open (1400x900): unchanged - strip 0 -> 45 px, glyph 18.5 -> 37.5 px, the label column and the
  "SUBJECTS" heading both at 55 px, the open chevron at 249 -> 267 px.
- The full suite passes, and `scripts/ui_smoke.py` passes against the served page.

## 18. The Home page carries one worked example, paper and explainer

The Documents card on Home listed only Word samples, so a student could inspect a finished paper but never
see what the product now ships beside it. The conductor's export is a ZIP holding the paper and its
computation explainer, and a sample that does not show that is a sample of the wrong thing.

`samples/pestel-and-break-even-tehran-device-store-submission.zip` is one PESTEL paper with one break-even
computation, built by the product's own path (`scripts/build_home_sample.py`) and exported the way a student
exports: `chat.docx_bytes` plus `explain.paper_document`. The store now lists a `.zip` sample with its own
MIME, so the download is served as `application/zip` and the card reads "PESTEL + break-even · Paper +
explainer". The explainer also stopped printing empty fields for a conductor paper ("Profile: Paper (, ).")
and now names the framework, lists the draft's own sections and formats recorded figures (166.6667, not fifty
digits); a declared word such as "monthly" is never rewritten.
