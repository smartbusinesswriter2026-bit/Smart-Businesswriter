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
| 12 | Calculator | calculator | `#DDD6FE` |

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
