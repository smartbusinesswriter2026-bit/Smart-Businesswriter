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

## 2. Rail (left, 64 px collapsed, 232 px expanded)

Nine items, each with a distinct colour and an inline SVG glyph (stroke 1.6, 20×20, `currentColor`).
Shape carries the meaning; colour is secondary (greyscale-safe).

| # | Label | Icon | Colour |
|---|---|---|---|
| 1 | Home / New analysis | house with a spark | navy `#02284C` |
| 2 | Cases | stacked folders | green `#02A15E` |
| 3 | Data | table with an arrow | teal `#0E8C8C` |
| 4 | References | open book | indigo `#3A5BA0` |
| 5 | Deliverables | document with a down-arrow | forest `#147A4E` |
| 6 | Accounts | ledger book | ochre `#9A6A16` |
| 7 | Frameworks & templates | 2×2 grid | violet `#6B4E9B` |
| 8 | Assistant & method info | chat bubble | slate `#4A5A6A` |
| 9 | Status | pulse line | moss `#4E7A2E` |

Behaviour: collapsed by default (icon only + tooltip), expand/collapse via the top toggle, the choice persists in
`localStorage`. Active item: tinted background, navy left bar, `aria-current="page"`. All items are real `<a>` with
`href="#/…"` so they work without JavaScript and are keyboard reachable.

## 3. Copy options (hero sub-line — owner to choose; until then the UI shows "To be supplied")

Each option is a short, factual line. None is live copy until the owner picks one and I edit the markup.
None contains invented counts, testimonials or social proof.

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
